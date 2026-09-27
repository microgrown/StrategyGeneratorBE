"""Clone every generated walkforward spec of a family into a calendar-period
twin: the same strategy, symbols, timeframes, dates, criterion, Max Bars Back
and selection chain, with only the schedules changed from trading days to
MultiWalk's calendar periods (and the calendar_alignment those need).

    python cloneCalendarSpecs.py                       every s_<yyyymm>_bas_<n> family
    python cloneCalendarSpecs.py s_202608_bas_13       one family (name or stem)
    python cloneCalendarSpecs.py --dry-run             print the plan, write nothing
    python cloneCalendarSpecs.py --list                one clone stem per line, nothing else

Why: TradeStation's historical corrections add and remove whole sessions, and a
trading-day schedule counts sessions, so one correction shifts every later
window boundary and re-picks every later window. Calendar periods anchor on
dates instead; the engine reproduces MultiWalk's calendar windows exactly
(BacktestEngine CLAUDE.md, measured 2026-09-19). The existing trading-day runs
stay put: the twin is a NEW family, <stem>_cal, with its own specs
(specs/generated/<stem>_cal_v<n>.json) and its own runs (runs/<stem>_cal_v<n>),
so `python runBatch.py <stem>_cal --prune` runs it like any other family.

The trading-day lengths map to MultiWalk's standard periods:

    126 -> 6M    252 -> 1Y    504 -> 2Y    756 -> 3Y

so the six standard schedules become 3Y/2Y, 3Y/1Y, 3Y/6M, 2Y/1Y, 2Y/6M, 1Y/6M.
A length outside the table is an error, never a guess: extend
TRADING_TO_CALENDAR when a family with other schedules appears.

Every clone is built in memory and validated before a single file is written,
so a bad spec anywhere aborts with nothing written. A clone that already exists
with the same content is left alone (the tool is idempotent, which is what lets
the second test machine produce byte-identical clones from the same script);
one that exists with different content is an error unless --force. Original
specs are never modified. specs/generated is gitignored, so the clones are not
committed -- each machine runs this script. runCalendarFamilies.cmd runs it
first and then loops over `--list`, so nothing about the family set is written
down anywhere but specs/generated itself.

Exit 0 on success, 2 on an error (one line on stderr).
"""

import argparse
import json
import os
import re
import sys

import config
from runBatch import REPORT_JSON, discoverSpecs, resolveStem, runsDir
from specWriter import specOutputDir
from strategyWriter import GenerationError

DEFAULT_SUFFIX = "_cal"
DEFAULT_ALIGNMENT = "month_start"
ALIGNMENTS = ("none", "month_start")  # the engine's calendar_alignment values

# Trading-day lengths -> MultiWalk calendar periods (the cheat sheet's standard
# in/out pairs: 3Y/2Y, 3Y/1Y, 3Y/6M, 2Y/1Y, 2Y/6M, 1Y/6M).
TRADING_TO_CALENDAR = {126: "6M", 252: "1Y", 504: "2Y", 756: "3Y"}

# The families this tool clones by default: the generated "20260x BAS-n"
# families, never their own clones (_cal), rerun scratch specs (__rerun) or
# the hand-made validation/quicktest stems.
FAMILY_STEM = re.compile(r"^s_\d{6}_bas_\d+$")

RUNNER = "runCalendarFamilies.cmd"


# --- pure pieces -------------------------------------------------------------

def calendarPeriod(specName, side, days):
    """'3Y' for 756 trading days; a GenerationError for a length with no twin."""
    try:
        length = int(days)
    except (TypeError, ValueError):
        raise GenerationError(f"{specName}: schedule {side} '{days}' is not a trading-day count.")
    if length not in TRADING_TO_CALENDAR:
        raise GenerationError(
            f"{specName}: no calendar twin for {length} trading days ({side}); "
            f"extend TRADING_TO_CALENDAR in cloneCalendarSpecs.py.")
    return TRADING_TO_CALENDAR[length]


def calendarSchedule(specName, entry):
    """{is_days, oos_days} -> {is, oos}; anything else is an error."""
    if not isinstance(entry, dict) or set(entry) != {"is_days", "oos_days"}:
        raise GenerationError(
            f"{specName}: schedule {json.dumps(entry)} is not a trading-day "
            f"schedule {{is_days, oos_days}}; only trading-day families are cloned.")
    return {"is": calendarPeriod(specName, "is_days", entry["is_days"]),
            "oos": calendarPeriod(specName, "oos_days", entry["oos_days"])}


def calendarSpec(spec, stem, version, suffix=DEFAULT_SUFFIX, alignment=DEFAULT_ALIGNMENT):
    """The calendar twin of one generated spec: name renamed to the clone
    family, schedules mapped, calendar_alignment inserted right after them,
    every other key passed through in its original order."""
    if alignment not in ALIGNMENTS:
        raise GenerationError(
            f"calendar_alignment '{alignment}' is not one of {', '.join(ALIGNMENTS)}.")
    expected = f"{stem}_v{version}"
    if spec.get("name") != expected:
        raise GenerationError(
            f"{expected}.json: spec name is '{spec.get('name')}', expected '{expected}'.")
    if "schedules" not in spec:
        raise GenerationError(f"{expected}.json: spec has no schedules.")
    if "calendar_alignment" in spec:
        raise GenerationError(f"{expected}.json: spec already carries calendar_alignment.")
    out = {}
    for key, value in spec.items():
        if key == "name":
            out[key] = f"{stem}{suffix}_v{version}"
        elif key == "schedules":
            out[key] = [calendarSchedule(expected, entry) for entry in value]
            out["calendar_alignment"] = alignment
        else:
            out[key] = value
    return out


def cloneStems(stems, cfg, suffix=DEFAULT_SUFFIX):
    """The clone stems of `stems` whose v1 clone spec exists, in order."""
    specDir = specOutputDir(cfg)
    return [f"{stem}{suffix}" for stem in stems
            if os.path.isfile(os.path.join(specDir, f"{stem}{suffix}_v1.json"))]


def discoverFamilies(specDir):
    """Sorted stems of every default family with a v1 spec in specDir."""
    stems = set()
    for fileName in os.listdir(specDir):
        match = re.match(r"^(.*)_v1\.json$", fileName)
        if match and FAMILY_STEM.match(match.group(1)):
            stems.add(match.group(1))
    return sorted(stems)


# --- planning and writing ----------------------------------------------------

def _loadJson(path):
    # utf-8-sig: hand-edited specs may carry a BOM, which the engine accepts
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def _writeSpec(path, spec):
    # Same writer as specWriter: 2-space JSON, trailing newline, platform line
    # endings, so a clone looks exactly like a generated spec.
    with open(path, "w") as f:
        json.dump(spec, f, indent=2)
        f.write("\n")


def planFamily(stem, cfg, suffix=DEFAULT_SUFFIX, alignment=DEFAULT_ALIGNMENT):
    """[(version, clonePath, cloneSpec, state)] for one family, state in
    {'write', 'exists', 'differs'}; raises before any I/O decision is acted on."""
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
        clone = calendarSpec(spec, stem, version, suffix, alignment)
        clonePath = os.path.join(specDir, f"{clone['name']}.json")
        state = "write"
        if os.path.exists(clonePath):
            try:
                state = "exists" if _loadJson(clonePath) == clone else "differs"
            except (OSError, ValueError):
                state = "differs"
        plan.append((version, clonePath, clone, state))
    return plan


def cloneFamilies(stems, cfg, suffix=DEFAULT_SUFFIX, alignment=DEFAULT_ALIGNMENT,
                  dryRun=False, force=False, echo=print):
    """Plan every family, then write. Returns {stem: (written, existing)}."""
    if not stems:
        raise GenerationError(f"No families to clone in {specOutputDir(cfg)}.")
    plans = {stem: planFamily(stem, cfg, suffix, alignment) for stem in stems}

    if not force:
        differing = [os.path.basename(p) for plan in plans.values()
                     for _, p, _, state in plan if state == "differs"]
        if differing:
            raise GenerationError(
                f"{len(differing)} existing clone(s) differ from what this tool would write "
                f"(first: {differing[0]}); nothing written. Re-run with --force to overwrite.")

    results = {}
    for stem, plan in plans.items():
        cloneStem = f"{stem}{suffix}"
        written = existing = 0
        for version, clonePath, clone, state in plan:
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
        echo(f"{stem} -> {cloneStem}: {written} {verb}, {existing} existing")
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Clone generated families into calendar-period twins "
                    "(<stem>_cal) with the schedules mapped 126/252/504/756 "
                    "trading days -> 6M/1Y/2Y/3Y.")
    parser.add_argument("stems", nargs="*",
                        help="family names or stems (default: every s_<yyyymm>_bas_<n> family)")
    parser.add_argument("--suffix", default=DEFAULT_SUFFIX,
                        help=f"clone stem suffix (default {DEFAULT_SUFFIX})")
    parser.add_argument("--alignment", default=DEFAULT_ALIGNMENT, choices=ALIGNMENTS,
                        help=f"calendar_alignment for the clones (default {DEFAULT_ALIGNMENT})")
    parser.add_argument("--dry-run", dest="dryRun", action="store_true",
                        help="print the plan, write nothing")
    parser.add_argument("--list", dest="listStems", action="store_true",
                        help="print the clone stems that exist (one per line) and exit; "
                             "what runCalendarFamilies.cmd loops over")
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
        stems = [resolveStem(s) for s in args.stems] or discoverFamilies(specOutputDir(cfg))
        if args.listStems:
            for cloneStem in cloneStems(stems, cfg, args.suffix):
                print(cloneStem)
            return 0
        results = cloneFamilies(stems, cfg, args.suffix, args.alignment,
                                dryRun=args.dryRun, force=args.force)
    except (GenerationError, OSError) as exc:
        print(f"cloneCalendarSpecs: {exc}", file=sys.stderr)
        return 2
    written = sum(w for w, _ in results.values())
    existing = sum(e for _, e in results.values())
    verb = "would be written" if args.dryRun else "written"
    print(f"{len(results)} families: {written} specs {verb}, {existing} already present.")
    if not args.dryRun and written:
        print(f"Next: {RUNNER} (python runBatch.py <stem>{args.suffix} --prune per family).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
