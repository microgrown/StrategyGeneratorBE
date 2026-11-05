"""Draw the per-family context conditions, exits and switches for the Brooks
platinum-validation study from pools.json, and write assignment.json.

    python drawStudy.py                  draw, write assignment.json, print a summary table
    python drawStudy.py --markdown       print the assignment as a Markdown table (for SELECTION.md)
    python drawStudy.py --pools P --out O

The draw is seeded (pools.json "seed") and fully reproducible: the same pools
file always produces the same assignment.json. It is stratified: every pool is
filled least-used-first, ties broken by the seeded RNG, so across the families
each member of a pool appears a near-equal number of times. Of 200 seeded
attempts (each a different family order and tie-break stream) the one with
the smallest total count spread is kept; ties keep the earliest attempt.

Constraints (pools.json "drawConstraints"):
  - nothing is drawn twice within a family, and pane 2 never reuses a rule
    already placed in the family's setup (pane 1);
  - pane 2: two conditions from the setup type's pool, one from the
    signal-bar pool;
  - pane 3 (stops): one money/volatility stop and one structural stop;
  - pane 4 (exits): four exits covering at least three categories;
  - families tagged "any" get at most one intraday-only exit across panes 3
    and 4 and at most one intraday-effective switch;
  - at most one equity-profit and one equity-loss switch per family;
  - switches excluded by setup type (TrendFilterSwitch for reversals,
    LowAdxSwitch and TightRangeBlocksEntries for range setups).

Nothing here generates a template; assignment.json is the input a later
template generator consumes.
"""

import argparse
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPTS = 200


class DrawError(Exception):
    pass


def pick(rng, usage, candidates):
    """Least-used member of candidates; ties broken by rng."""
    if not candidates:
        raise DrawError("no eligible candidate")
    low = min(usage[c["id"]] for c in candidates)
    best = [c for c in candidates if usage[c["id"]] == low]
    choice = best[rng.randrange(len(best))]
    usage[choice["id"]] += 1
    return choice


def drawOnce(pools, rng):
    families = list(pools["families"])
    rng.shuffle(families)
    p2pools = pools["pane2Pools"]
    fill = pools["pane2Fill"]
    excl = pools["drawConstraints"]["switchBySetupType"]

    usage = {}
    for members in list(p2pools.values()) + [pools["stopPool"], pools["exitPool"], pools["switchPool"]]:
        for m in members:
            usage[m["id"]] = 0

    out = {}
    for fam in families:
        setupRules = {p["name"] for p in fam["setup"]}
        anyTf = fam["timeframeTag"] == "any"

        # pane 2
        typePool = p2pools[fill["typePool"][fam["setupType"]]]
        usedRules = set(setupRules)
        pane2 = []
        for pool, n in ((typePool, fill["fromTypePool"]), (p2pools["signalBar"], fill["fromSignalBarPool"])):
            for _ in range(n):
                cands = [m for m in pool if m["placement"]["name"] not in usedRules]
                m = pick(rng, usage, cands)
                usedRules.add(m["placement"]["name"])
                pane2.append(m)

        # pane 3 and pane 4 share the intraday cap
        intradayLeft = 1 if anyTf else 99
        stops = []
        for cat in ("stop-money/volatility", "stop-structural"):
            cands = [s for s in pools["stopPool"] if s["category"] == cat
                     and (not s["intradayOnly"] or intradayLeft > 0)]
            s = pick(rng, usage, cands)
            intradayLeft -= s["intradayOnly"]
            stops.append(s)

        exits = []
        for slot in range(4):
            cats = {e["category"] for e in exits}
            needNew = (3 - len(cats)) >= (4 - slot)
            cands = [e for e in pools["exitPool"]
                     if e["id"] not in {x["id"] for x in exits}
                     and e["placement"]["name"] not in {x["placement"]["name"] for x in exits + stops}
                     and (not e["intradayOnly"] or intradayLeft > 0)
                     and (not needNew or e["category"] not in cats)]
            e = pick(rng, usage, cands)
            intradayLeft -= e["intradayOnly"]
            exits.append(e)

        switches = []
        banned = set(excl.get(fam["setupType"], []))
        for _ in range(2):
            kinds = {w["kind"] for w in switches}
            intra = sum(w["intradayEffective"] for w in switches)
            cands = [w for w in pools["switchPool"]
                     if w["id"] not in banned and w["id"] not in {x["id"] for x in switches}
                     and not (w["kind"] in ("equity-profit", "equity-loss") and w["kind"] in kinds)
                     and not (anyTf and w["intradayEffective"] and intra >= 1)]
            switches.append(pick(rng, usage, cands))

        out[fam["id"]] = dict(pane2=pane2, stops=stops, exits=exits, switches=switches)
    return out, usage


def spread(pools, usage):
    total = 0
    detail = {}
    groups = dict(pools["pane2Pools"])
    groups["stops-money/volatility"] = [s for s in pools["stopPool"] if s["category"] == "stop-money/volatility"]
    groups["stops-structural"] = [s for s in pools["stopPool"] if s["category"] == "stop-structural"]
    groups["exits"] = pools["exitPool"]
    groups["switches"] = pools["switchPool"]
    for name, members in groups.items():
        counts = [usage[m["id"]] for m in members]
        detail[name] = (min(counts), max(counts))
        total += max(counts) - min(counts)
    return total, detail


def draw(pools):
    best = None
    for attempt in range(ATTEMPTS):
        rng = random.Random(f"{pools['seed']}:{attempt}")
        try:
            out, usage = drawOnce(pools, rng)
        except DrawError:
            continue
        score, detail = spread(pools, usage)
        if best is None or score < best[0]:
            best = (score, attempt, out, usage, detail)
    if best is None:
        raise DrawError("every attempt violated a constraint")
    return best


def strip(m, keys):
    return {k: m[k] for k in keys if k in m}


def build(pools, best):
    score, attempt, out, usage, detail = best
    fams = []
    for fam in pools["families"]:
        a = out[fam["id"]]
        worstExit = max([1] + [e["iterations"] for e in a["exits"]])
        fams.append(dict(
            id=fam["id"], label=fam["label"], bucket=fam["bucket"], setupType=fam["setupType"],
            timeframeTag=fam["timeframeTag"], timeframes=pools["timeframes"][fam["timeframeTag"]],
            maxBarsBack=str(max([int(pools["maxBarsBack"])] + [int(s.get("maxBarsBack", 0)) for s in a["stops"]])),
            panes=[
                {"ruleType": "Entry", "groups": [fam["setup"], fam["reverse"]]},
                {"ruleType": "Entry", "groups": [[]] + [[m["placement"]] for m in a["pane2"]],
                 "ids": [m["id"] for m in a["pane2"]]},
                {"ruleType": "Exit", "groups": [[]] + [[s["placement"]] for s in a["stops"]],
                 "ids": [s["id"] for s in a["stops"]]},
                {"ruleType": "Exit", "groups": [[]] + [[e["placement"]] for e in a["exits"]],
                 "ids": [e["id"] for e in a["exits"]]},
                {"ruleType": "Switch", "groups": [[]] + [[w["placement"]] for w in a["switches"]],
                 "ids": [w["id"] for w in a["switches"]]},
            ],
            versions=2 * 4 * 3 * 5 * 3,
            worstVersionIterations=fam["setupIterations"] * worstExit,
        ))
    counts = {}
    for name in ("pane2Pools", "stopPool", "exitPool", "switchPool"):
        src = pools[name]
        members = [m for v in src.values() for m in v] if isinstance(src, dict) else src
        for m in members:
            counts[m["id"]] = usage[m["id"]]
    return dict(seed=pools["seed"], attempt=attempt, attempts=ATTEMPTS, totalSpread=score,
                spreadByPool={k: {"min": v[0], "max": v[1]} for k, v in detail.items()},
                usage=counts, families=fams)


def markdown(result):
    lines = ["| Family | Pane 2 (after empty) | Stops (after empty) | Exits (after empty) | Switches (after empty) | Worst it. |",
             "|---|---|---|---|---|---|"]
    for f in result["families"]:
        p = f["panes"]
        lines.append("| {} | {} | {} | {} | {} | {} |".format(
            f["id"], ", ".join(p[1]["ids"]), ", ".join(p[2]["ids"]), ", ".join(p[3]["ids"]),
            ", ".join(p[4]["ids"]), f["worstVersionIterations"]))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pools", default=os.path.join(HERE, "pools.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "assignment.json"))
    ap.add_argument("--markdown", action="store_true", help="print the Markdown table instead of the summary")
    args = ap.parse_args(argv)
    try:
        with open(args.pools, encoding="utf-8") as fh:
            pools = json.load(fh)
        result = build(pools, draw(pools))
    except (OSError, ValueError, KeyError, DrawError) as e:
        print(f"drawStudy: {e}", file=sys.stderr)
        return 2
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, indent=2)
        fh.write("\n")
    if args.markdown:
        print(markdown(result))
        return 0
    print(f"seed {result['seed']}, attempt {result['attempt']} of {result['attempts']}, total spread {result['totalSpread']}")
    for k, v in result["spreadByPool"].items():
        print(f"  {k:24s} appearances {v['min']}..{v['max']}")
    worst = max(f["worstVersionIterations"] for f in result["families"])
    print(f"{len(result['families'])} families x {result['families'][0]['versions']} versions; worst version {worst} iterations")
    for f in result["families"]:
        p = f["panes"]
        print(f"{f['id']} {f['setupType'][:3]:3s} | {', '.join(p[1]['ids'])} | {', '.join(p[2]['ids'])} | "
              f"{', '.join(p[3]['ids'])} | {', '.join(p[4]['ids'])}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
