"""Draw pane 2 (or the classic pane-1 entries), the stops, exits and switches for
the own-rules platinum-validation study from pools.json, and write
assignment.json.

    python drawOwnStudy.py               draw, write assignment.json, print a summary
    python drawOwnStudy.py --markdown    print the assignment as a Markdown table

Two family kinds (Brian, 2026-11-06), 360 versions each:

  setup families (one per own pane-1 entry), OWN-01..
    pane 1  setup | reverse
    pane 2  (empty) | own trend condition | own regime condition | classic filter
  condition families (one per own pane-2 condition), after the setup families
    pane 1  classic trend entry | its reverse | classic mean-reversion entry | its reverse
    pane 2  condition | condition flipped (mirrored) or negated (same-sided); no empty group
  both
    pane 3  (empty) | money/volatility stop | structural stop
    pane 4  (empty) | four exits from >= 3 categories
    pane 5  (empty) | two switches

Orientation: a trend condition is placed as authored for with-trend and breakout
setups and flipped for reversal and range setups; a reversal-context condition
the other way round; regime (same-sided) conditions are never flipped.

The draw is seeded and stratified exactly as reference/brooks/study/drawStudy.py:
least-used-first per pool, seeded tie-breaks, best of 200 attempts by total
count spread. The same pools.json always gives the same assignment.json.
"""

import argparse
import copy
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPTS = 200
PREFIX_ID = "OWN-"


class DrawError(Exception):
    pass


def pick(rng, usage, candidates):
    if not candidates:
        raise DrawError("no eligible candidate")
    low = min(usage[c["id"]] for c in candidates)
    best = [c for c in candidates if usage[c["id"]] == low]
    choice = best[rng.randrange(len(best))]
    usage[choice["id"]] += 1
    return choice


def toggled(p, key):
    q = copy.deepcopy(p)
    q[key] = not q.get(key, False)
    return q


def oriented(member, setupType):
    """The member's placement, flipped when its kind runs against the setup type."""
    p = copy.deepcopy(member["placement"])
    if member.get("sides") != "mirrored":
        return p, False
    fade = setupType in ("reversal", "range")
    flip = (member["kind"] == "trend" and fade) or (member["kind"] == "reversal-context" and not fade)
    if flip:
        p["flipped"] = not p["flipped"]
    return p, flip


def familyIds(pools):
    n = len(pools["setupFamilies"])
    ids = [f"{PREFIX_ID}{i + 1:02d}" for i in range(n + len(pools["conditionFamilies"]))]
    return ids[:n], ids[n:]


def drawExitsAndSwitches(pools, rng, usage, setupType, usedRules):
    intradayLeft = 1
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
        taken = {x["placement"]["name"] for x in exits + stops} | usedRules
        cands = [e for e in pools["exitPool"]
                 if e["placement"]["name"] not in taken
                 and (not e["intradayOnly"] or intradayLeft > 0)
                 and (not needNew or e["category"] not in cats)]
        e = pick(rng, usage, cands)
        intradayLeft -= e["intradayOnly"]
        exits.append(e)

    switches = []
    banned = set(pools["drawConstraints"]["switchBySetupType"].get(setupType or "", []))
    for _ in range(2):
        kinds = {w["kind"] for w in switches}
        intra = sum(w["intradayEffective"] for w in switches)
        cands = [w for w in pools["switchPool"]
                 if w["id"] not in banned and w["id"] not in {x["id"] for x in switches}
                 and not (w["kind"] in ("equity-profit", "equity-loss") and w["kind"] in kinds)
                 and not (w["intradayEffective"] and intra >= 1)]
        switches.append(pick(rng, usage, cands))
    return stops, exits, switches


def drawOnce(pools, rng):
    setupIds, condIds = familyIds(pools)
    work = [("setup", fid, f) for fid, f in zip(setupIds, pools["setupFamilies"])]
    work += [("condition", fid, f) for fid, f in zip(condIds, pools["conditionFamilies"])]
    rng.shuffle(work)

    own = pools["pane2Own"]
    trendPool = [m for m in own if m["kind"] in ("trend", "reversal-context")]
    regimePool = [m for m in own if m["kind"] == "regime"]
    usage = {}
    for members in (own, pools["classicFilters"], pools["classicEntries"]["trend"],
                    pools["classicEntries"]["meanReversion"], pools["stopPool"],
                    pools["exitPool"], pools["switchPool"]):
        for m in members:
            usage[m["id"]] = 0

    out = {}
    for kind, fid, fam in work:
        if kind == "setup":
            usedRules = {p["name"] for p in fam["setup"]}
            conflicts = set(fam.get("pane2Conflicts", []))
            pane2 = []
            for pool in (trendPool, regimePool, pools["classicFilters"]):
                cands = [m for m in pool if m["placement"]["name"] not in usedRules
                         and m["id"] not in conflicts]
                m = pick(rng, usage, cands)
                usedRules.add(m["placement"]["name"])
                pl, flip = oriented(m, fam["setupType"])
                pane2.append({"id": m["id"] + ("~" if flip else ""), "member": m, "placement": pl})
            stops, exits, switches = drawExitsAndSwitches(pools, rng, usage, fam["setupType"], set())
            out[fid] = dict(kind=kind, pane2=pane2, stops=stops, exits=exits, switches=switches)
        else:
            t = pick(rng, usage, pools["classicEntries"]["trend"])
            m = pick(rng, usage, pools["classicEntries"]["meanReversion"])
            usedRules = {fam["placement"]["name"], t["placement"]["name"], m["placement"]["name"]}
            stops, exits, switches = drawExitsAndSwitches(pools, rng, usage, None, set())
            out[fid] = dict(kind=kind, entries=[t, m], stops=stops, exits=exits, switches=switches)
    return out, usage


def spread(pools, usage):
    groups = {
        "pane2-trend": [m for m in pools["pane2Own"] if m["kind"] != "regime"],
        "pane2-regime": [m for m in pools["pane2Own"] if m["kind"] == "regime"],
        "classicFilters": pools["classicFilters"],
        "classicEntries-trend": pools["classicEntries"]["trend"],
        "classicEntries-meanReversion": pools["classicEntries"]["meanReversion"],
        "stops-money/volatility": [s for s in pools["stopPool"] if s["category"] == "stop-money/volatility"],
        "stops-structural": [s for s in pools["stopPool"] if s["category"] == "stop-structural"],
        "exits": pools["exitPool"],
        "switches": pools["switchPool"],
    }
    total, detail = 0, {}
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


def build(pools, best):
    score, attempt, out, usage, detail = best
    setupIds, condIds = familyIds(pools)
    base = int(pools["maxBarsBack"])
    fams = []

    def tail(a):
        return [
            {"ruleType": "Exit", "groups": [[]] + [[s["placement"]] for s in a["stops"]],
             "ids": [s["id"] for s in a["stops"]]},
            {"ruleType": "Exit", "groups": [[]] + [[e["placement"]] for e in a["exits"]],
             "ids": [e["id"] for e in a["exits"]]},
            {"ruleType": "Switch", "groups": [[]] + [[w["placement"]] for w in a["switches"]],
             "ids": [w["id"] for w in a["switches"]]},
        ]

    for fid, fam in zip(setupIds, pools["setupFamilies"]):
        a = out[fid]
        setup = fam["setup"]
        reverse = [toggled(p, "flipped") for p in setup]
        worstExit = max([1] + [e["iterations"] for e in a["exits"]])
        mbb = max([base, fam["maxBarsBack"]] + [s.get("maxBarsBack", 0) for s in a["stops"]]
                  + [m["member"].get("maxBarsBack", 0) for m in a["pane2"]])
        fams.append(dict(
            id=fid, kind="setup", label=fam["rule"], setupType=fam["setupType"],
            setupFlipped=fam["setupFlipped"], timeframes=pools["timeframes"], maxBarsBack=str(mbb),
            panes=[{"ruleType": "Entry", "groups": [setup, reverse], "ids": ["setup", "reverse"]},
                   {"ruleType": "Entry", "groups": [[]] + [[m["placement"]] for m in a["pane2"]],
                    "ids": [m["id"] for m in a["pane2"]]}] + tail(a),
            versions=2 * 4 * 3 * 5 * 3,
            worstVersionIterations=fam["iterations"] * worstExit))
    for fid, fam in zip(condIds, pools["conditionFamilies"]):
        a = out[fid]
        t, m = a["entries"]
        cond = fam["placement"]
        alt, altTag = (toggled(cond, "flipped"), "~") if fam["sides"] == "mirrored" else (toggled(cond, "negated"), "!")
        worstExit = max([1] + [e["iterations"] for e in a["exits"]])
        mbb = max([base, fam["maxBarsBack"]] + [s.get("maxBarsBack", 0) for s in a["stops"]])
        fams.append(dict(
            id=fid, kind="condition", label=fam["condition"], conditionKind=fam["kind"],
            timeframes=pools["timeframes"], maxBarsBack=str(mbb),
            panes=[{"ruleType": "Entry",
                    "groups": [[t["placement"]], [toggled(t["placement"], "flipped")],
                               [m["placement"]], [toggled(m["placement"], "flipped")]],
                    "ids": [t["id"], t["id"] + "~", m["id"], m["id"] + "~"]},
                   {"ruleType": "Entry", "groups": [[cond], [alt]],
                    "ids": [fam["condition"], fam["condition"] + altTag]}] + tail(a),
            versions=4 * 2 * 3 * 5 * 3,
            worstVersionIterations=fam["iterations"] * worstExit))
    counts = {k: v for k, v in usage.items()}
    return dict(seed=pools["seed"], attempt=attempt, attempts=ATTEMPTS, totalSpread=score,
                spreadByPool={k: {"min": v[0], "max": v[1]} for k, v in detail.items()},
                usage=counts, families=fams)


def markdown(result):
    lines = ["| Family | Pane 1 | Pane 2 | Stops | Exits | Switches | MBB | Worst it. |",
             "|---|---|---|---|---|---|---|---|"]
    for f in result["families"]:
        p = f["panes"]
        p1 = f["label"] if f["kind"] == "setup" else ", ".join(p[0]["ids"])
        p2 = ", ".join(p[1]["ids"]) if f["kind"] == "setup" else ", ".join(p[1]["ids"])
        lines.append(f"| {f['id']} | {p1} | {p2} | {', '.join(p[2]['ids'])} | {', '.join(p[3]['ids'])} | "
                     f"{', '.join(p[4]['ids'])} | {f['maxBarsBack']} | {f['worstVersionIterations']} |")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pools", default=os.path.join(HERE, "pools.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "assignment.json"))
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args(argv)
    try:
        with open(args.pools, encoding="utf-8") as fh:
            pools = json.load(fh)
        result = build(pools, draw(pools))
    except (OSError, ValueError, KeyError, DrawError) as e:
        print(f"drawOwnStudy: {e}", file=sys.stderr)
        return 2
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, indent=1)
        fh.write("\n")
    if args.markdown:
        print(markdown(result))
        return 0
    print(f"seed {result['seed']}, attempt {result['attempt']} of {result['attempts']}, "
          f"total spread {result['totalSpread']}")
    for k, v in result["spreadByPool"].items():
        print(f"  {k:30s} appearances {v['min']}..{v['max']}")
    worst = max(f["worstVersionIterations"] for f in result["families"])
    print(f"{len(result['families'])} families; worst version {worst} iterations")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
