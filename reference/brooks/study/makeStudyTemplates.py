"""Turn assignment.json into the 50 Brooks study templates, `202611 BRK-01` ..
`202611 BRK-50`, in templates/, in exactly the shape templateIO.py reads and
makeStrategy.py consumes.

    python makeStudyTemplates.py              write the templates, then verify them
    python makeStudyTemplates.py --check      verify the templates on disk, write nothing
    python makeStudyTemplates.py --assignment A --templates-dir D --prefix "202611 "

Shape. Each family becomes five panes, in assignment.json's order:

    1 Entry   setup | reverse                                  2 groups
    2 Entry   (empty) | context 1 | context 2 | signal bar     4 groups
    3 Exit    (empty) | money/volatility stop | structural stop 3 groups
    4 Exit    (empty) | exit 1 | exit 2 | exit 3 | exit 4       5 groups
    5 Switch  (empty) | switch 1 | switch 2                    3 groups

Groups are separated by the delimiter string; a leading delimiter is the empty
group (strategyWriter._templateGroups: N delimiters make N + 1 groups). Params
are strings, pinned inputs as {"start": X, "stop": "", "step": ""}. Max Bars
Back is the family's assignment.json value (250, the 202608 families' value).

Verification, per template, by the generator's own code: it loads through
templateIO, splits through strategyWriter._enumerateVersions into 360
versions, holds the pure stop-and-reverse combination (panes 3-5 all empty)
for every pane-1 x pane-2 pair, keeps every version within 3 optimized inputs
and 100 iterations (parameterGUI.rowIterations), and covers the deepest
CATALOG "Reaches back" of anything placed with its Max Bars Back.

Exit 0 when every template verifies, 1 otherwise.
"""

import argparse
import math
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)

import templateIO  # noqa: E402
import strategyWriter  # noqa: E402
from makeStrategy import panesFromTemplate  # noqa: E402
from parameterGUI import rowIterations  # noqa: E402

DELIMITER = "------------------------------"   # what the GUI's Delim button inserts
PREFIX = "202611 "
VERSIONS = 360
MAX_OPTIMIZED = 3
MAX_ITERATIONS = 100


def item(placement):
    return {
        "name": placement["name"],
        "flipped": bool(placement.get("flipped", False)),
        "negated": bool(placement.get("negated", False)),
        "params": {k: {"start": str(v.get("start", "")), "stop": str(v.get("stop", "")),
                       "step": str(v.get("step", ""))}
                   for k, v in placement.get("params", {}).items()},
    }


def paneItems(groups):
    items = []
    for i, group in enumerate(groups):
        if i:
            items.append(DELIMITER)
        items.extend(item(p) for p in group)
    return items


def familyTemplate(fam, prefix=PREFIX):
    return {
        "strategyName": prefix + fam["id"],
        "maxBarsBack": str(fam["maxBarsBack"]),
        "panes": [{"ruleType": p["ruleType"], "items": paneItems(p["groups"])} for p in fam["panes"]],
    }


# --- verification ----------------------------------------------------------

def _catalogReaches():
    reaches = {}
    with open(os.path.join(ROOT, "rules", "CATALOG.md"), encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("| `"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                reaches[cells[0].strip("`")] = cells[3]
    return reaches


def placementReach(it, reaches):
    """Deepest bar index per CATALOG, every input at its stop value (else its
    start, else the rule default)."""
    expr = reaches.get(it.name)
    if expr is None:
        raise ValueError(f"{it.name}: no CATALOG row")
    with open(os.path.join(ROOT, "rules", it.name + ".json"), encoding="utf-8") as fh:
        rule = json.load(fh)
    env = {}
    for k, v in rule.get("inputVariables", {}).items():
        try:
            env[k] = float(v)
        except ValueError:
            pass
    for k, v in it.params.items():
        env[k] = float(v["stop"] if v.get("stop") and v.get("step") else v["start"])
    terms = re.findall(r"`([^`]*)`", expr) or [expr.split("(")[0].strip() or "0"]
    vals = []
    for term in terms:
        try:
            vals.append(float(eval(term.replace("−", "-"),
                                   {"__builtins__": {}, "max": max, "min": min,
                                    "ceil": math.ceil, "floor": math.floor}, dict(env))))
        except Exception:
            continue
    if not vals:
        raise ValueError(f"{it.name}: cannot evaluate Reaches back {expr!r}")
    return max(vals)


def verify(path, reaches):
    """[problem, ...] for one template file; empty when it passes."""
    problems = []
    data = templateIO.loadTemplateFile(path)
    panes = panesFromTemplate(data)
    groups = [strategyWriter._templateGroups(p.items) for p in panes]
    versions = strategyWriter._enumerateVersions(panes)
    if len(versions) != VERSIONS:
        problems.append(f"{len(versions)} versions, expected {VERSIONS}")
    if [len(g) for g in groups] != [2, 4, 3, 5, 3]:
        problems.append(f"group counts {[len(g) for g in groups]}, expected [2, 4, 3, 5, 3]")
    for k in (2, 3, 4):
        if groups[k] and groups[k][0]:
            problems.append(f"pane {k + 1}'s first group is not empty")
    stopAndReverse = sum(1 for _entries, exits, switches in versions if not exits and not switches)
    if stopAndReverse != len(groups[0]) * len(groups[1]):
        problems.append(f"{stopAndReverse} stop-and-reverse versions, expected "
                        f"{len(groups[0]) * len(groups[1])}")
    worst, worstIt = (0, 0), 1
    for entries, exits, switches in versions:
        rows = [rowIterations(v["start"], v["stop"], v["step"])
                for it in entries + exits + switches for v in it.params.values()]
        if any(r is None for r in rows):
            problems.append("an invalid start/stop/step row")
            break
        optimized = sum(1 for r in rows if r > 1)
        iterations = math.prod(rows)
        worst = max(worst, (optimized, iterations))
        worstIt = max(worstIt, iterations)
        if optimized > MAX_OPTIMIZED or iterations > MAX_ITERATIONS:
            problems.append(f"a version has {optimized} optimized inputs / {iterations} iterations")
            break
    mbb = int(data["maxBarsBack"])
    deepest, deepestName = 0.0, ""
    for pane in panes:
        for it in pane.items:
            if isinstance(it, str):
                continue
            r = placementReach(it, reaches)
            if r > deepest:
                deepest, deepestName = r, it.name
    if deepest > mbb:
        problems.append(f"{deepestName} reaches {deepest:g} bars back, Max Bars Back is {mbb}")
    return problems, dict(versions=len(versions), stopAndReverse=stopAndReverse,
                          worstOptimized=worst[0], worstIterations=worstIt,
                          maxBarsBack=mbb, deepest=deepest, deepestRule=deepestName)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--assignment", default=os.path.join(HERE, "assignment.json"))
    ap.add_argument("--templates-dir", dest="templatesDir", default=templateIO.templatesDir())
    ap.add_argument("--prefix", default=PREFIX)
    ap.add_argument("--check", action="store_true", help="verify only, write nothing")
    args = ap.parse_args(argv)

    with open(args.assignment, encoding="utf-8") as fh:
        assignment = json.load(fh)
    paths = []
    for fam in assignment["families"]:
        tpl = familyTemplate(fam, args.prefix)
        path = os.path.join(args.templatesDir, tpl["strategyName"] + ".json")
        if not args.check:
            with open(path, "w") as fh:      # templateIO.saveTemplate's format
                json.dump(tpl, fh, indent=4)
        paths.append((fam["id"], path))

    reaches = _catalogReaches()
    failed = 0
    for fid, path in paths:
        problems, s = verify(path, reaches)
        status = "ok" if not problems else "FAIL: " + "; ".join(problems)
        failed += bool(problems)
        print(f"{fid}: {s['versions']} versions, {s['stopAndReverse']} stop-and-reverse, worst "
              f"{s['worstOptimized']} optimized / {s['worstIterations']} it., MBB {s['maxBarsBack']} "
              f"covers {s['deepest']:g} ({s['deepestRule']}) -- {status}")
    print(f"{len(paths) - failed}/{len(paths)} templates verified"
          + ("" if args.check else f", written to {args.templatesDir}"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
