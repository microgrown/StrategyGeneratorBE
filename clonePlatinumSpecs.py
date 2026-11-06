"""Clone every generated walkforward spec of a family into a platinum-validation
twin: the same strategy, timeframes, schedules, criterion and Max Bars Back,
re-dated so a 36-month out-of-sample segment ends on 2023-01-01, with the
crypto symbols dropped and the selection chain made uniform and extended to
record every figure the IS-vs-OOS study correlates.

    python clonePlatinumSpecs.py                       every s_<yyyymm>_bas/brk/own_<n> family
    python clonePlatinumSpecs.py --kind own            only the own-rules study (s_<yyyymm>_own_<n>)
    python clonePlatinumSpecs.py --kind own --range 33-64   only families 33..64 of it
    python clonePlatinumSpecs.py s_202608_bas_13       one family (name or stem)
    python clonePlatinumSpecs.py --dry-run             print the plan, write nothing
    python clonePlatinumSpecs.py --list                one clone stem per line, nothing else

Why: a Kevin Davey-style validation. Selection sees the walkforward and the
incubation exactly as it always has; the three years after incubation are held
out and only measured. The engine's `oos_end` does that in one bt_walkforward
run (BacktestEngine src/bt/wf/spec.h): the composites keep stepping through
it, every filter judges the curve clipped at incubation_end, and the segment
appears only in the selection report's metrics and candidate_metrics.csv --
for every candidate, rejected ones included, on the most-average schedule.
So `python runBatch.py <stem>_platinum_validation --prune` needs no OOS step:
the held-out figures are in the report before the rejects are pruned.

The dates, for every clone:

    WF            2007-01-01 -> 2019-04-01   (wf_start must already be 2007-01-01)
    incubation    2019-04-01 -> 2020-01-01   (9 months, as the originals)
    out of sample 2020-01-01 -> 2023-01-01   (36 months)

ETH and BTC are dropped: ETH's data begins 2021-02-08, inside the OOS, and
BTC's 2017-12-18 leaves too little before wf_end for the shortest schedule.

The selection chain is the standard one, with two changes:

- trade_count (min 30) is appended where it is missing (the 202606/202607
  families predate it), so every family is judged by the same chain --
  passing_categories.py already holds those families to it;
- a record_only monte_carlo bootstrap over all six criteria is appended. It
  records each criterion's bootstrap average for every candidate but can
  never reject; its bounds only colour the recorded pass/fail.

Retired families (s_202608_bas_37) are skipped unless named explicitly.

Every clone is built in memory and validated before a single file is written,
so a bad spec anywhere aborts with nothing written. A clone that already exists
with the same content is left alone (idempotent, so the tool can be re-run
after adding families); one that exists with different content is an error
unless --force. Original specs are never modified. specs/generated is
gitignored, so the clones are not committed -- each machine runs this script.

Exit 0 on success, 2 on an error (one line on stderr).
"""

import argparse
import copy
import os
import re
import sys

import config
from cloneCalendarSpecs import _loadJson, _writeSpec
from runBatch import REPORT_JSON, discoverSpecs, resolveStem, runsDir
from specWriter import specOutputDir
from strategyWriter import GenerationError

DEFAULT_SUFFIX = "_platinum_validation"

EXPECTED_WF_START = "2007-01-01"
WF_END = "2019-04-01"
INCUBATION_END = "2020-01-01"
OOS_END = "2023-01-01"

DROPPED_SYMBOLS = ("ETH", "BTC")

RETIRED_FAMILIES = ("s_202608_bas_37",)
PLATINUM_FAMILY_STEM = re.compile(r"^s_\d{6}_(bas|brk|own)_(\d+)$")
KINDS = ("bas", "brk", "own")

TRADE_COUNT_FILTER = {"type": "trade_count", "min_trades": 30}

# Recorded, never enforced. Every criterion of the engine's library is listed so
# the report carries all six bootstrap averages; the bounds mirror the standard
# chain's thresholds where one exists and are otherwise "not losing".
MONTE_CARLO_FILTER = {
    "type": "monte_carlo",
    "runs": 1000,
    "seed": 1,
    "criteria": [
        {"criterion": "NetProfit", "min": 0.0},
        {"criterion": "MaxDrawdown", "max": 25000.0},
        {"criterion": "AvgDrawdown", "max": 3500.0},
        {"criterion": "NetProfitOverMaxDD", "min": 0.0},
        {"criterion": "NetProfitOverAvgDD", "min": 0.0},
        {"criterion": "ModifiedSharpe", "min": 0.0},
    ],
    "record_only": True,
}


# --- pure pieces -------------------------------------------------------------

def platinumSelection(specName, selection):
    """The standard chain plus trade_count (when missing) and the record-only
    monte_carlo. Refuses a chain that already has a monte_carlo stage rather
    than guessing which one the study should read."""
    if not isinstance(selection, dict) or not isinstance(selection.get("filters"), list):
        raise GenerationError(f"{specName}: spec has no selection filter chain.")
    filters = copy.deepcopy(selection["filters"])
    types = [f.get("type") for f in filters]
    if not types or types[0] != "most_average":
        raise GenerationError(
            f"{specName}: the chain must start with most_average (it picks the "
            "schedule the recorded metrics describe).")
    if "monte_carlo" in types:
        raise GenerationError(f"{specName}: the chain already has a monte_carlo stage.")
    if "trade_count" not in types:
        filters.append(dict(TRADE_COUNT_FILTER))
    filters.append(copy.deepcopy(MONTE_CARLO_FILTER))
    out = dict(selection)
    out["filters"] = filters
    return out


def platinumSpec(spec, stem, version, suffix=DEFAULT_SUFFIX):
    """The platinum-validation twin of one generated spec: renamed, re-dated
    with oos_end inserted right after incubation_end, crypto dropped, chain
    extended; every other key passed through in its original order."""
    expected = f"{stem}_v{version}"
    if spec.get("name") != expected:
        raise GenerationError(
            f"{expected}.json: spec name is '{spec.get('name')}', expected '{expected}'.")
    for key in ("wf_start", "wf_end", "incubation_end", "symbols", "selection"):
        if key not in spec:
            raise GenerationError(f"{expected}.json: spec has no {key}.")
    if "oos_end" in spec:
        raise GenerationError(f"{expected}.json: spec already carries oos_end.")
    if spec["wf_start"] != EXPECTED_WF_START:
        raise GenerationError(
            f"{expected}.json: wf_start is {spec['wf_start']}, expected {EXPECTED_WF_START}; "
            "the platinum dates assume it.")
    symbols = [s for s in spec["symbols"] if s not in DROPPED_SYMBOLS]
    if not symbols:
        raise GenerationError(f"{expected}.json: no symbols left after dropping "
                              f"{', '.join(DROPPED_SYMBOLS)}.")
    out = {}
    for key, value in spec.items():
        if key == "name":
            out[key] = f"{stem}{suffix}_v{version}"
        elif key == "symbols":
            out[key] = symbols
        elif key == "wf_end":
            out[key] = WF_END
        elif key == "incubation_end":
            out[key] = INCUBATION_END
            out["oos_end"] = OOS_END
        elif key == "selection":
            out[key] = platinumSelection(expected, value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def parseRange(text):
    """'33-64' or '7' -> (lo, hi), inclusive family numbers."""
    match = re.match(r"^\s*(\d+)\s*(?:-\s*(\d+))?\s*$", text or "")
    if not match:
        raise GenerationError(f"--range '{text}': expected N or LO-HI.")
    lo = int(match.group(1))
    hi = int(match.group(2)) if match.group(2) else lo
    if hi < lo:
        raise GenerationError(f"--range '{text}': LO is above HI.")
    return lo, hi


def defaultFamilies(specDir, kind=None, numbers=None):
    """Every generated family with a v1 spec, retired ones excluded: the Davey
    families (s_<yyyymm>_bas_<n>), the Brooks study (s_<yyyymm>_brk_<n>) and
    the own-rules study (s_<yyyymm>_own_<n>). `kind` keeps one of them and
    `numbers` = (lo, hi) keeps family numbers lo..hi, so a study can be split
    across machines. Not cloneCalendarSpecs' FAMILY_STEM, which stays bas-only
    so the Brooks and own families get no calendar twins."""
    stems = set()
    for fileName in os.listdir(specDir):
        match = re.match(r"^(.*)_v1\.json$", fileName)
        family = match and PLATINUM_FAMILY_STEM.match(match.group(1))
        if not family:
            continue
        if kind and family.group(1) != kind:
            continue
        if numbers and not numbers[0] <= int(family.group(2)) <= numbers[1]:
            continue
        stems.add(match.group(1))
    return [s for s in sorted(stems) if s not in RETIRED_FAMILIES]


def cloneStems(stems, cfg, suffix=DEFAULT_SUFFIX):
    """The clone stems of `stems` whose v1 clone spec exists, in order."""
    specDir = specOutputDir(cfg)
    return [f"{stem}{suffix}" for stem in stems
            if os.path.isfile(os.path.join(specDir, f"{stem}{suffix}_v1.json"))]


# --- planning and writing ----------------------------------------------------

def planFamily(stem, cfg, suffix=DEFAULT_SUFFIX):
    """[(version, clonePath, cloneSpec, state)] for one family, state in
    {'write', 'exists', 'differs'}."""
    specs = discoverSpecs(stem, cfg)
    if not specs:
        raise GenerationError(f"No specs found for '{stem}' in {specOutputDir(cfg)}.")
    specDir = specOutputDir(cfg)
    plan = []
    for version, path in specs:
        try:
            spec = _loadJson(path)
        except (OSError, ValueError) as exc:
            raise GenerationError(f"{path}: unreadable spec ({exc}).")
        clone = platinumSpec(spec, stem, version, suffix)
        clonePath = os.path.join(specDir, f"{clone['name']}.json")
        state = "write"
        if os.path.exists(clonePath):
            try:
                state = "exists" if _loadJson(clonePath) == clone else "differs"
            except (OSError, ValueError):
                state = "differs"
        plan.append((version, clonePath, clone, state))
    return plan


def cloneFamilies(stems, cfg, suffix=DEFAULT_SUFFIX, dryRun=False, force=False, echo=print):
    """Plan every family, then write. Returns {stem: (written, existing)}."""
    if not stems:
        raise GenerationError(f"No families to clone in {specOutputDir(cfg)}.")
    plans = {stem: planFamily(stem, cfg, suffix) for stem in stems}

    if not force:
        differing = [os.path.basename(p) for plan in plans.values()
                     for _, p, _, state in plan if state == "differs"]
        if differing:
            raise GenerationError(
                f"{len(differing)} existing clone(s) differ from what this tool would write "
                f"(first: {differing[0]}); nothing written. Re-run with --force to overwrite.")

    results = {}
    for stem, plan in plans.items():
        written = existing = 0
        for _version, clonePath, clone, state in plan:
            if state == "exists":
                existing += 1
                continue
            if state == "differs":
                runDir = os.path.join(runsDir(cfg), clone["name"])
                if os.path.isfile(os.path.join(runDir, REPORT_JSON)):
                    echo(f"Warning: {clone['name']} already has a selection report; "
                         f"its run no longer matches the rewritten spec.")
            if not dryRun:
                _writeSpec(clonePath, clone)
            written += 1
        results[stem] = (written, existing)
        verb = "would write" if dryRun else "written"
        echo(f"{stem} -> {stem}{suffix}: {written} {verb}, {existing} existing")
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Clone generated families into platinum-validation twins "
                    f"(<stem>{DEFAULT_SUFFIX}): WF to {WF_END}, incubation to "
                    f"{INCUBATION_END}, held-out OOS to {OOS_END}.")
    parser.add_argument("stems", nargs="*",
                        help="family names or stems (default: every s_<yyyymm>_bas_<n>, _brk_<n> or _own_<n> "
                             "family except the retired ones)")
    parser.add_argument("--kind", choices=KINDS,
                        help="default families of one study only: bas (Davey), brk (Brooks), own")
    parser.add_argument("--range", dest="numberRange", metavar="LO-HI",
                        help="default families numbered LO..HI only (e.g. 33-64)")
    parser.add_argument("--suffix", default=DEFAULT_SUFFIX,
                        help=f"clone stem suffix (default {DEFAULT_SUFFIX})")
    parser.add_argument("--dry-run", dest="dryRun", action="store_true",
                        help="print the plan, write nothing")
    parser.add_argument("--list", dest="listStems", action="store_true",
                        help="print the clone stems that exist (one per line) and exit")
    parser.add_argument("--force", action="store_true",
                        help="overwrite clones whose content differs")
    parser.add_argument("--engine-dir", dest="engineDir",
                        help="BacktestEngine root (default config.json)")
    args = parser.parse_args(argv)

    cfg = config.load()
    if args.engineDir:
        cfg["engineDir"] = args.engineDir
    if not args.suffix:
        print("--suffix must not be empty: the clone would overwrite its own family.",
              file=sys.stderr)
        return 2
    try:
        if args.stems and (args.kind or args.numberRange):
            raise GenerationError("--kind/--range select default families; do not combine them "
                                  "with named families.")
        numbers = parseRange(args.numberRange) if args.numberRange else None
        stems = [resolveStem(s) for s in args.stems] or defaultFamilies(
            specOutputDir(cfg), args.kind, numbers)
        if args.listStems:
            for cloneStem in cloneStems(stems, cfg, args.suffix):
                print(cloneStem)
            return 0
        results = cloneFamilies(stems, cfg, args.suffix, dryRun=args.dryRun, force=args.force)
    except (GenerationError, OSError) as exc:
        print(f"clonePlatinumSpecs: {exc}", file=sys.stderr)
        return 2
    written = sum(w for w, _ in results.values())
    existing = sum(e for _, e in results.values())
    verb = "would be written" if args.dryRun else "written"
    print(f"{len(results)} families: {written} specs {verb}, {existing} already present.")
    if not args.dryRun and written:
        print(f"Next: python runBatch.py <stem>{args.suffix} --prune per family "
              "(runPlatinumFamilies.cmd runs them all).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
