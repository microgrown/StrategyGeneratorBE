"""Re-run a finished family's candidates on a few symbols and splice the new
verdicts into the family, leaving every other candidate untouched.

    python rerunSymbols.py <stem> --symbols ETH,BTC,MBT,MET [options]

Why this exists: a symbol's bars can change under a finished family (the
2026-09-02 crypto session-anchor fix re-ingested ETH/BTC/MBT/MET). The family
is pruned to its tradeable units, so `runBatch --force` would re-simulate
everything. Selection is per candidate -- each filter narrows one candidate's
own schedule set, Monte Carlo streams are keyed on (seed, run index), and
`most_average` looks only at a candidate's own schedules -- so a spec narrowed
to the affected symbols yields bit-identical rows for those candidates, and
only their rows need replacing.

Per version it:
  1. clones specs/generated/<stem>_v<n>.json with `symbols` narrowed to the
     list (same timeframes, dates, schedules, selection) as <stem>_v<n>__rerun
     and runs bt_walkforward on it;
  2. splices the narrowed run into runs/<stem>_v<n>/: candidates[] and
     tradeable[] entries for those symbols are replaced in selection_report.json
     (the original is kept once as selection_report.pre_rerun.json), rows are
     replaced in selection_summary.csv (and candidate_metrics.csv when present),
     the old unit directories for those symbols are deleted and the new ones
     moved in, and their prune-ledger entries are dropped (the epoch bytes
     they name are no longer what the row was computed from);
  3. records the splice in rerun_symbols.json (so a re-invocation skips it);
then rebuilds the family aggregate runs/<stem>/ and, with --prune, unit-prunes
each spliced version exactly as runBatch --prune does.

Options:
    --symbols SYM,SYM       required; engine symbol names
    --versions 7,19         only these versions (default: every version with a run dir)
    --threads N             engine threads (default 0 = all cores)
    --prune                 prune each spliced version's rejects afterwards
    --force                 re-splice versions already marked as done
    --dry-run               print the plan, run nothing
    --engine-dir DIR        BacktestEngine root (default config.json)

Exit 0 on success, 1 on any error (one line on stderr).
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

import config
import pruneRuns
import runBatch
from runBatch import REPORT_JSON, RUN_LOG, SUMMARY_CSV, WALKFORWARD_EXE, RunOutcome, runsDir
from specWriter import specOutputDir
from strategyWriter import GenerationError

RERUN_SUFFIX = "__rerun"
PRE_RERUN_REPORT = "selection_report.pre_rerun.json"
RERUN_MARKER = "rerun_symbols.json"
CANDIDATE_METRICS_CSV = "candidate_metrics.csv"


# --- pure pieces -------------------------------------------------------------

def narrowedSpec(spec, symbols):
    """The family spec with `symbols` cut down to the list, named for the
    scratch run. None when the spec touches none of them."""
    keep = [s for s in spec.get("symbols", []) if s in symbols]
    if not keep:
        return None
    out = dict(spec)
    out["name"] = spec["name"] + RERUN_SUFFIX
    out["symbols"] = keep
    return out


def _isTarget(entry, symbols):
    return entry.get("symbol") in symbols


def _spliceList(old, new, symbols, key):
    """Replace the target-symbol entries of `old` with those of `new`, in place:
    the new entries take the position of the first old target entry (or the
    end), so untouched entries keep their order."""
    newEntries = [e for e in new if _isTarget(e, symbols)]
    seen = set()
    for e in newEntries:
        k = key(e)
        if k in seen:
            raise GenerationError(f"duplicate entry {k} in the narrowed run")
        seen.add(k)
    out = []
    inserted = False
    for e in old:
        if _isTarget(e, symbols):
            if not inserted:
                out.extend(newEntries)
                inserted = True
            continue
        out.append(e)
    if not inserted:
        out.extend(newEntries)
    return out


def _candidateKey(e):
    return (e.get("symbol"), int(e.get("timeframe_minutes", 0)))


def _tradeableKey(e):
    return (e.get("symbol"), int(e.get("timeframe_minutes", 0)), e.get("schedule"))


_V2_ONLY_CANDIDATE_KEYS = ("incubation_end", "incubation_end_day", "oos_end", "oos_end_day",
                           "wf_end", "wf_end_day")


def _v1Segment(segment):
    """A format-2 segment block -> the format-1 criteria map it nests."""
    if "criteria" not in segment:
        raise GenerationError("format-2 segment block without 'criteria'; cannot downgrade")
    return dict(segment["criteria"])


def downgradeReport(report):
    """A format-2 selection report re-shaped as format 1, numerically identical:
    format 2 (commit 9bea3be) nests the six criteria under `<segment>.criteria`
    alongside segment counts, adds an `incubation` segment and puts the run's
    split days on each candidate; format 1 carried only `wf_range` / `full_curve`
    criteria maps. Verified bit-exact on a real family (NG, 202608 BAS-13 V7).
    Reports already in format 1 come back unchanged."""
    if report.get("format_version") == 1:
        return report
    if report.get("format_version") != 2:
        raise GenerationError(f"cannot downgrade report format {report.get('format_version')}")
    out = dict(report)
    out["format_version"] = 1
    cands = []
    for c in report.get("candidates", []):
        d = {k: v for k, v in c.items() if k not in _V2_ONLY_CANDIDATE_KEYS}
        if c.get("tradeable"):
            # format 1 carried a tradeable candidate's metrics only in tradeable[]
            d.pop("metrics", None)
        else:
            d["metrics"] = [{"full_curve": _v1Segment(m["full_curve"]), "schedule": m["schedule"],
                             "wf_range": _v1Segment(m["wf_range"])} for m in c.get("metrics", [])]
        cands.append(d)
    out["candidates"] = cands
    trads = []
    for t in report.get("tradeable", []):
        d = dict(t)
        d["metrics"] = {"full_curve": _v1Segment(t["metrics"]["full_curve"]),
                        "wf_range": _v1Segment(t["metrics"]["wf_range"])}
        trads.append(d)
    out["tradeable"] = trads
    return out


def spliceReport(old, new, symbols):
    """The old selection report with the target symbols' candidates[] and
    tradeable[] taken from the narrowed run's report. Everything else (spec
    name, filters, format, timestamp) stays the old report's; the filter chains
    must agree or the narrowed verdicts are not comparable. A format-2 narrowed
    report is downgraded into a format-1 family; the reverse cannot happen (the
    engine only ever writes the newer format)."""
    if old.get("filters") != new.get("filters"):
        raise GenerationError("filter chains differ between the family run and the "
                              "narrowed run; refusing to splice")
    if old.get("format_version") == 1 and new.get("format_version") == 2:
        new = downgradeReport(new)
    if old.get("format_version") != new.get("format_version"):
        raise GenerationError(
            f"report format {old.get('format_version')} vs {new.get('format_version')}; "
            "refusing to splice across formats")
    out = dict(old)
    out["candidates"] = _spliceList(old.get("candidates", []), new.get("candidates", []),
                                    symbols, _candidateKey)
    out["tradeable"] = _spliceList(old.get("tradeable", []), new.get("tradeable", []),
                                   symbols, _tradeableKey)
    return out


def spliceCsvRows(oldHeader, oldRows, newHeader, newRows, symbols, keyFields):
    """Same replacement for a CSV: rows keyed by `keyFields`."""
    if list(oldHeader) != list(newHeader):
        raise GenerationError(f"CSV columns differ: {oldHeader} vs {newHeader}")
    return _spliceList(oldRows, newRows, symbols, lambda r: tuple(r.get(k) for k in keyFields))


def _readCsv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def _writeCsv(path, header, rows):
    with open(path + ".tmp", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, restval="")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(path + ".tmp", path)


def spliceLedger(ledger, symbols):
    units = {name: entry for name, entry in ledger.get("units", {}).items()
             if entry.get("symbol") not in symbols}
    out = dict(ledger)
    out["units"] = units
    return out


def unitDirsFor(runDir, symbols):
    """<SYM>_M<tf> directories of the target symbols present under runDir."""
    out = []
    for entry in sorted(os.listdir(runDir)):
        path = os.path.join(runDir, entry)
        if not os.path.isdir(path) or "_M" not in entry:
            continue
        sym = entry.rsplit("_M", 1)[0]
        if sym in symbols:
            out.append(entry)
    return out


def tradeableUnits(report, symbols):
    return sorted({_tradeableKey(e) for e in report.get("tradeable", []) if _isTarget(e, symbols)})


# --- per-version work --------------------------------------------------------

def _loadJson(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def _dumpJson(path, data):
    with open(path + ".tmp", "w") as f:
        json.dump(data, f, indent=1)
        f.write("\n")
    os.replace(path + ".tmp", path)


def spliceVersion(runDir, narrowDir, symbols, echo=print):
    """Splice the narrowed run at narrowDir into the version run at runDir.
    Returns (oldTradeable, newTradeable) for the target symbols."""
    old = _loadJson(os.path.join(runDir, REPORT_JSON))
    new = _loadJson(os.path.join(narrowDir, REPORT_JSON))
    before = tradeableUnits(old, symbols)
    spliced = spliceReport(old, new, symbols)

    # summary csv (required) and candidate metrics csv (v2 runs)
    oldHeader, oldRows = _readCsv(os.path.join(runDir, SUMMARY_CSV))
    newHeader, newRows = _readCsv(os.path.join(narrowDir, SUMMARY_CSV))
    summaryRows = spliceCsvRows(oldHeader, oldRows, newHeader, newRows, symbols,
                                ("symbol", "timeframe_minutes"))
    metrics = None
    metricsPath = os.path.join(runDir, CANDIDATE_METRICS_CSV)
    if os.path.isfile(metricsPath):
        newMetricsPath = os.path.join(narrowDir, CANDIDATE_METRICS_CSV)
        if not os.path.isfile(newMetricsPath):
            raise GenerationError(f"{runDir} has {CANDIDATE_METRICS_CSV} but the narrowed run does not")
        mh, mr = _readCsv(metricsPath)
        nh, nr = _readCsv(newMetricsPath)
        metrics = (mh, spliceCsvRows(mh, mr, nh, nr, symbols, ("symbol", "timeframe_minutes", "schedule")))

    # Everything validated; now write. Report first (kept once, pre-splice).
    preserved = os.path.join(runDir, PRE_RERUN_REPORT)
    if not os.path.exists(preserved):
        shutil.copyfile(os.path.join(runDir, REPORT_JSON), preserved)
    _dumpJson(os.path.join(runDir, REPORT_JSON), spliced)
    _writeCsv(os.path.join(runDir, SUMMARY_CSV), oldHeader, summaryRows)
    if metrics is not None:
        _writeCsv(metricsPath, *metrics)

    # unit dirs: out with the old, in with the new
    for entry in unitDirsFor(runDir, symbols):
        shutil.rmtree(os.path.join(runDir, entry))
    moved = 0
    for entry in unitDirsFor(narrowDir, symbols):
        shutil.move(os.path.join(narrowDir, entry), os.path.join(runDir, entry))
        moved += 1

    ledgerPath = os.path.join(runDir, pruneRuns.PRUNE_LEDGER)
    if os.path.isfile(ledgerPath):
        ledger = spliceLedger(pruneRuns.loadLedger(runDir), symbols)
        if ledger["units"]:
            pruneRuns.saveLedger(runDir, ledger)
        else:
            os.remove(ledgerPath)

    after = tradeableUnits(spliced, symbols)
    marker = {"format": "rerunSymbols-1", "symbols": sorted(symbols),
              "spliced_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
              "units_moved": moved,
              "tradeable_before": [list(k) for k in before],
              "tradeable_after": [list(k) for k in after]}
    _dumpJson(os.path.join(runDir, RERUN_MARKER), marker)
    echo(f"    spliced {moved} unit dir(s); tradeable {len(before)} -> {len(after)}")
    return before, after


def alreadyDone(runDir, symbols):
    path = os.path.join(runDir, RERUN_MARKER)
    if not os.path.isfile(path):
        return False
    try:
        marker = _loadJson(path)
    except ValueError:
        return False
    return set(marker.get("symbols", [])) >= set(symbols)


def rerunVersion(stem, version, symbols, cfg, threads=0, runner=subprocess.run, echo=print):
    """Run the narrowed spec for one version and splice it in. Returns
    (before, after) tradeable unit lists, or None when the spec has none of
    the symbols."""
    engineDir = runBatch._engineDir(cfg)
    runName = f"{stem}_v{version}"
    runDir = os.path.join(runsDir(cfg), runName)
    specPath = os.path.join(specOutputDir(cfg), f"{runName}.json")
    if not os.path.isfile(specPath):
        raise GenerationError(f"no spec at {specPath}")
    if not os.path.isfile(os.path.join(runDir, REPORT_JSON)):
        raise GenerationError(f"{runName} has no {REPORT_JSON}; nothing to splice into")
    spec = _loadJson(specPath)
    narrowed = narrowedSpec(spec, symbols)
    if narrowed is None:
        return None

    narrowSpecPath = os.path.join(specOutputDir(cfg), narrowed["name"] + ".json")
    narrowDir = os.path.join(runsDir(cfg), narrowed["name"])
    if os.path.isdir(narrowDir):
        shutil.rmtree(narrowDir)  # a previous attempt; the engine would reuse its units
    _dumpJson(narrowSpecPath, narrowed)
    binary = os.path.join(engineDir, WALKFORWARD_EXE)
    if not os.path.isfile(binary):
        raise GenerationError(f"{binary} not found; build the engine first")
    try:
        proc = runner([binary, "--spec", narrowSpecPath, "--threads", str(threads), "--quiet"],
                      cwd=engineDir)
        if proc.returncode != 0:
            raise GenerationError(
                f"bt_walkforward failed on {narrowed['name']} (exit {proc.returncode}); "
                f"see {os.path.join(narrowDir, RUN_LOG)}")
        if not os.path.isfile(os.path.join(narrowDir, REPORT_JSON)):
            raise GenerationError(f"{narrowed['name']} produced no {REPORT_JSON}")
        result = spliceVersion(runDir, narrowDir, symbols, echo=echo)
    finally:
        try:
            os.remove(narrowSpecPath)
        except OSError:
            pass
    shutil.rmtree(narrowDir, ignore_errors=True)
    return result


# --- family driver -----------------------------------------------------------

def familyVersions(stem, cfg):
    """[(version, runDir)] for every version whose run dir has a report."""
    out = []
    for version, _ in runBatch.discoverSpecs(stem, cfg):
        runDir = os.path.join(runsDir(cfg), f"{stem}_v{version}")
        if os.path.isfile(os.path.join(runDir, REPORT_JSON)):
            out.append((version, runDir))
    return out


def rerunFamily(stem, symbols, cfg, versions=None, threads=0, prune=False, force=False,
                dryRun=False, runner=subprocess.run, echo=print):
    allVersions = familyVersions(stem, cfg)
    if not allVersions:
        raise GenerationError(f"no finished versions of '{stem}' under {runsDir(cfg)}")
    todo = [(v, d) for v, d in allVersions if versions is None or v in versions]
    if versions is not None:
        missing = sorted(set(versions) - {v for v, _ in todo})
        if missing:
            raise GenerationError(f"no finished run for version(s) {missing}")
    skipped = [(v, d) for v, d in todo if not force and alreadyDone(d, symbols)]
    todo = [(v, d) for v, d in todo if (v, d) not in skipped]

    echo(f"{stem}: {len(allVersions)} finished version(s); re-running {len(todo)} on "
         f"{','.join(sorted(symbols))}" + (f"; {len(skipped)} already spliced" if skipped else ""))
    if dryRun:
        for v, d in todo:
            echo(f"  v{v}: {d}")
        return {"reran": [], "skipped": [v for v, _ in skipped], "deltas": {}}

    deltas = {}
    registry = pruneRuns.requireEpochs(cfg) if prune else None
    for i, (v, d) in enumerate(todo, 1):
        echo(f"[{i}/{len(todo)}] {stem}_v{v}")
        result = rerunVersion(stem, v, symbols, cfg, threads=threads, runner=runner, echo=echo)
        if result is None:
            echo("    spec has none of the symbols; nothing to do")
            continue
        deltas[v] = result

    if deltas or force:
        outcomes = [RunOutcome(version=v, specPath="", runDir=d) for v, d in allVersions]
        warnings = []
        aggDir, names, _ = runBatch.writeAggregate(stem, outcomes, cfg, warnings)
        for w in warnings:
            echo(f"  Warning: {w}")
        echo(f"aggregate rebuilt: {aggDir} ({len(names)} version(s))")
        if prune:
            for v in sorted(deltas):
                pruneRuns.pruneVersion(stem, v, cfg, registry, echo=lambda *a: None)
            echo(f"pruned {len(deltas)} version(s)")

    gained = sum(len(set(a) - set(b)) for b, a in deltas.values())
    lost = sum(len(set(b) - set(a)) for b, a in deltas.values())
    kept = sum(len(set(a) & set(b)) for b, a in deltas.values())
    echo(f"tradeable on {','.join(sorted(symbols))}: kept {kept}, gained {gained}, lost {lost}")
    for v in sorted(deltas):
        b, a = deltas[v]
        for k in sorted(set(a) - set(b)):
            echo(f"  + v{v} {k[0]} M{k[1]} {k[2]}")
        for k in sorted(set(b) - set(a)):
            echo(f"  - v{v} {k[0]} M{k[1]} {k[2]}")
    return {"reran": sorted(deltas), "skipped": [v for v, _ in skipped], "deltas": deltas}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stem")
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--versions", default="")
    parser.add_argument("--threads", type=int, default=0)
    parser.add_argument("--prune", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", dest="dryRun", action="store_true")
    parser.add_argument("--engine-dir", dest="engineDir")
    args = parser.parse_args(argv)
    cfg = config.load()
    if args.engineDir:
        cfg["engineDir"] = args.engineDir
    symbols = {s.strip() for s in args.symbols.split(",") if s.strip()}
    versions = {int(v) for v in args.versions.split(",") if v.strip()} or None
    try:
        rerunFamily(runBatch.resolveStem(args.stem), symbols, cfg, versions=versions,
                    threads=args.threads, prune=args.prune, force=args.force, dryRun=args.dryRun)
        return 0
    except (GenerationError, OSError, ValueError) as exc:
        print(f"rerunSymbols: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
