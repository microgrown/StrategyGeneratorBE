"""Turn assignment.json into the own-rules study templates, `202611 OWN-01` ..,
in templates/, in exactly the shape templateIO.py reads.

    python makeOwnTemplates.py            write the templates, then verify them
    python makeOwnTemplates.py --check    verify the templates on disk, write nothing

Template writing and the CATALOG reach evaluation are the Brooks study's own
(reference/brooks/study/makeStudyTemplates.py). Verification, per template, by
the generator's code: 360 versions; group counts [2, 4, 3, 5, 3] for a setup
family and [4, 2, 3, 5, 3] for a condition family; empty first groups where
the shape has them (pane 2 of a setup family, panes 3-5 always) and NO empty
group in a condition family's pane 2; pure stop-and-reverse (panes 3-5 empty)
for every pane-1 x pane-2 pair; every version within 3 optimized inputs and
100 iterations; Max Bars Back covering the deepest CATALOG "Reaches back".

Exit 0 when every template verifies, 1 otherwise.
"""

import argparse
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BROOKS_STUDY = os.path.normpath(os.path.join(HERE, "..", "..", "brooks", "study"))
sys.path.insert(0, BROOKS_STUDY)

import makeStudyTemplates as mst  # noqa: E402  (puts the generator root on sys.path)
import templateIO  # noqa: E402
import strategyWriter  # noqa: E402
from makeStrategy import panesFromTemplate  # noqa: E402
from parameterGUI import rowIterations  # noqa: E402

PREFIX = "202611 "
VERSIONS = 360
SHAPES = {"setup": [2, 4, 3, 5, 3], "condition": [4, 2, 3, 5, 3]}


def reach(it, reaches):
    """mst.placementReach, falling back to a leading integer for rows such as
    CalendarBoundaryExit's "1 (the `Date` series)", whose backticked term is a
    series name rather than an expression."""
    try:
        return mst.placementReach(it, reaches)
    except ValueError:
        m = re.match(r"\s*(\d+)", reaches.get(it.name, ""))
        if not m:
            raise
        return float(m.group(1))


def verify(path, kind, reaches):
    problems = []
    data = templateIO.loadTemplateFile(path)
    panes = panesFromTemplate(data)
    groups = [strategyWriter._templateGroups(p.items) for p in panes]
    versions = strategyWriter._enumerateVersions(panes)
    if len(versions) != VERSIONS:
        problems.append(f"{len(versions)} versions, expected {VERSIONS}")
    if [len(g) for g in groups] != SHAPES[kind]:
        problems.append(f"group counts {[len(g) for g in groups]}, expected {SHAPES[kind]}")
    emptyFirst = (1, 2, 3, 4) if kind == "setup" else (2, 3, 4)
    for k in emptyFirst:
        if groups[k] and groups[k][0]:
            problems.append(f"pane {k + 1}'s first group is not empty")
    for k in range(len(groups)):
        if k not in emptyFirst and any(not g for g in groups[k]):
            problems.append(f"pane {k + 1} has an empty group")
    sar = sum(1 for _e, exits, switches in versions if not exits and not switches)
    if sar != len(groups[0]) * len(groups[1]):
        problems.append(f"{sar} stop-and-reverse versions, expected {len(groups[0]) * len(groups[1])}")
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
        if optimized > mst.MAX_OPTIMIZED or iterations > mst.MAX_ITERATIONS:
            problems.append(f"a version has {optimized} optimized inputs / {iterations} iterations")
            break
    mbb = int(data["maxBarsBack"])
    deepest, deepestName = 0.0, ""
    for pane in panes:
        for it in pane.items:
            if isinstance(it, str):
                continue
            r = reach(it, reaches)
            if r > deepest:
                deepest, deepestName = r, it.name
    if deepest > mbb:
        problems.append(f"{deepestName} reaches {deepest:g} bars back, Max Bars Back is {mbb}")
    return problems, dict(versions=len(versions), stopAndReverse=sar, worstOptimized=worst[0],
                          worstIterations=worstIt, maxBarsBack=mbb, deepest=deepest, deepestRule=deepestName)


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
        tpl = mst.familyTemplate(fam, args.prefix)
        path = os.path.join(args.templatesDir, tpl["strategyName"] + ".json")
        if not args.check:
            with open(path, "w") as fh:      # templateIO.saveTemplate's format
                json.dump(tpl, fh, indent=4)
        paths.append((fam["id"], fam["kind"], path))

    reaches = mst._catalogReaches()
    failed = 0
    for fid, kind, path in paths:
        problems, s = verify(path, kind, reaches)
        status = "ok" if not problems else "FAIL: " + "; ".join(problems)
        failed += bool(problems)
        print(f"{fid} {kind:9s}: {s['versions']} versions, {s['stopAndReverse']} stop-and-reverse, worst "
              f"{s['worstOptimized']} optimized / {s['worstIterations']} it., MBB {s['maxBarsBack']} "
              f"covers {s['deepest']:g} ({s['deepestRule']}) -- {status}")
    print(f"{len(paths) - failed}/{len(paths)} templates verified"
          + ("" if args.check else f", written to {args.templatesDir}"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
