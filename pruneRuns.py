"""Manually reclaim disk space from finished runs, without losing any verdict.

    python pruneRuns.py --status [family ...]
    python pruneRuns.py --prune-wf <family> [--delete]
    python pruneRuns.py --prune-units <family> [--delete]
    python pruneRuns.py --regen <stem>_v<n> [--threads N]

This tool is ONLY ever run by hand. Nothing in runBatch.py, the engine, or any
hook invokes it: deleting results is a deliberate human decision, and even then
the default is a dry run — nothing is removed without --delete.

--prune-wf deletes wf_results.json for the REJECTED candidates of completed
versions. That file is a pure derivation of the unit's manifest.json + .bin
cache + spec (the engine rewrites it unconditionally whenever bt_walkforward
touches the run, reusing the cache with no re-simulation), so this is lossless:
--regen restores every pruned file byte-identically. Tradeable candidates are
never touched, and the selection reports and aggregates that runBatch.py's
skip logic keys on are always preserved, so a pruned batch still aggregates
without recomputing.

--prune-units goes further for rejected candidates: it deletes their entire
<SYM>_M<tf> unit directories (.bin optimizer caches included), keeping only
the selection report's concise record. Regeneration then means re-optimizing —
bit-identical ONLY over the exact bar data the run saw — so a unit is
deletable strictly when its manifest carries data-provenance hashes (engine
manifest v4) AND a snapshotData.py epoch archives matching data. Each deleted
unit is recorded in the run's prune_ledger.json with its hashes and epoch, and
--regen re-verifies the live store against that ledger before invoking
bt_walkforward (which reuses every surviving unit and re-simulates only the
deleted ones); on a mismatch it names the epoch to restore instead of running.

A version is only eligible when its own selection_report.json exists and the
family aggregate runs/<stem>/ has been written — pruning never races a batch
that is still producing results.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone

import config
import snapshotData
from runBatch import (AGGREGATE_MARKER, REPORT_JSON, WALKFORWARD_EXE,
                      resolveStem, runsDir)
from specWriter import specOutputDir
from strategyWriter import GenerationError

WF_RESULTS = "wf_results.json"
MANIFEST_JSON = "manifest.json"
PRUNE_LEDGER = "prune_ledger.json"

_EPOCH_DATE = date(1970, 1, 1)


def _echo(*args):
    print(*args, flush=True)


# --- discovery ---------------------------------------------------------------

def versionDirs(stem, baseDir):
    """[(version, runDir)] for every runs/<stem>_v<n> directory on disk, in
    version order. Disk is the source of truth here, not the spec list: pruning
    operates on whatever results actually exist."""
    pattern = re.compile(re.escape(stem) + r"_v(\d+)$")
    found = []
    if not os.path.isdir(baseDir):
        return found
    for entry in os.listdir(baseDir):
        match = pattern.fullmatch(entry)
        path = os.path.join(baseDir, entry)
        if match and os.path.isdir(path):
            found.append((int(match.group(1)), path))
    return sorted(found)


def hasAggregate(stem, baseDir):
    """True when runs/<stem>/ holds a runBatch aggregate — the sign the family
    is finished and its verdicts are safely rolled up."""
    reportPath = os.path.join(baseDir, stem, REPORT_JSON)
    try:
        with open(reportPath, encoding="utf-8-sig") as f:
            report = json.load(f)
    except (OSError, ValueError):
        return False
    return isinstance(report, dict) and report.get("aggregated_by") == AGGREGATE_MARKER


def loadReport(runDir):
    """The run's own selection report, or None when the version is incomplete
    (still running, or failed before selection) — such versions are skipped."""
    try:
        with open(os.path.join(runDir, REPORT_JSON), encoding="utf-8-sig") as f:
            report = json.load(f)
    except (OSError, ValueError):
        return None
    return report if isinstance(report, dict) else None


# --- prune-wf ----------------------------------------------------------------

def rejectedWfPaths(runDir, report, warnings):
    """Absolute wf_results.json paths for the run's rejected candidates.

    Each candidate names its own file via a relative path; anything that does
    not resolve to a wf_results.json strictly inside the run directory is
    refused rather than guessed at — this tool deletes only what it can prove
    is the derived per-unit results file."""
    paths = []
    runDir = os.path.abspath(runDir)
    for candidate in report.get("candidates", []):
        if candidate.get("tradeable"):
            continue
        relative = candidate.get("wf_results", "")
        target = os.path.normpath(os.path.join(runDir, relative))
        inside = target.startswith(os.path.join(runDir, ""))
        if not relative or not inside or os.path.basename(target) != WF_RESULTS:
            warnings.append(
                f"{os.path.basename(runDir)}: candidate "
                f"{candidate.get('symbol')}_M{candidate.get('timeframe_minutes')} "
                f"has an unexpected wf_results path ({relative!r}); left alone.")
            continue
        paths.append(target)
    return paths


def pruneWf(family, cfg, delete=False, echo=_echo):
    """Dry-run (default) or delete wf_results.json for rejected candidates in
    every completed version of the family. Returns (files, bytes) affected."""
    stem = resolveStem(family)
    baseDir = runsDir(cfg)
    versions = versionDirs(stem, baseDir)
    if not versions:
        raise GenerationError(f"No run directories found for '{stem}' in {baseDir}.")
    if not hasAggregate(stem, baseDir):
        raise GenerationError(
            f"'{stem}' has no aggregate at {os.path.join(baseDir, stem)}; run "
            "runBatch.py to completion first. Pruning only touches finished, "
            "aggregated families.")

    warnings = []
    totalFiles = totalBytes = 0
    for version, runDir in versions:
        report = loadReport(runDir)
        runName = os.path.basename(runDir)
        if report is None:
            echo(f"  {runName}: no {REPORT_JSON}; skipped (incomplete version)")
            continue
        targets = [p for p in rejectedWfPaths(runDir, report, warnings)
                   if os.path.isfile(p)]
        size = sum(os.path.getsize(p) for p in targets)
        totalFiles += len(targets)
        totalBytes += size
        if delete:
            for path in targets:
                os.remove(path)
        verb = "deleted" if delete else "would delete"
        echo(f"  {runName}: {verb} {len(targets)} file(s), {size / 2**20:.1f} MB")
    for warning in warnings:
        echo(f"  Warning: {warning}")

    mode = "Deleted" if delete else "Dry run — would delete"
    echo(f"{mode} {totalFiles} wf_results.json file(s), "
         f"{totalBytes / 2**30:.2f} GB across {len(versions)} version(s).")
    if not delete and totalFiles:
        echo("Re-run with --delete to actually remove them. Restore any version "
             "later with: bt_walkforward --spec specs/<stem>_v<n>.json")
    return totalFiles, totalBytes


# --- prune-units / regen -----------------------------------------------------

def parseDay(iso):
    """Manifest first_day/last_day ("YYYY-MM-DD") -> day serial, None absent."""
    if iso is None:
        return None
    return (date.fromisoformat(iso) - _EPOCH_DATE).days


def selectChunks(chunks, timeframeMinutes, firstDay, lastDay):
    """The registry chunks a range-clipped load of this timeframe would read —
    the same overlap rule as bt::SymbolIndex::select."""
    return [c for c in chunks
            if c["timeframe_minutes"] == timeframeMinutes
            and (lastDay is None or c["first_day"] <= lastDay)
            and (firstDay is None or c["last_day"] >= firstDay)]


def matchEpoch(registry, symbol, timeframeMinutes, firstDay, lastDay,
               sourceHash, sessionHash):
    """Newest epoch whose archived data reproduces exactly the fingerprint a
    run manifest recorded, or None. Both hashes must match: the combined chunk
    hash proves the bars, the session hash proves the schedule they were
    ingested under."""
    for epoch in reversed(registry["epochs"]):
        if symbol not in epoch["symbols"]:
            continue
        chunks = epoch["symbols"][symbol]["chunks"]
        combined = snapshotData.combinedSourceHash(chunks, timeframeMinutes,
                                                   firstDay, lastDay)
        inRange = selectChunks(chunks, timeframeMinutes, firstDay, lastDay)
        if (combined == sourceHash and inRange
                and all(c["session_hash"] == sessionHash for c in inRange)):
            return epoch["id"]
    return None


def loadLedger(runDir):
    try:
        with open(os.path.join(runDir, PRUNE_LEDGER), encoding="utf-8-sig") as f:
            return json.load(f)
    except OSError:
        return {"format": "pruneRuns-ledger-1", "units": {}}
    except ValueError as exc:
        raise GenerationError(f"corrupt {PRUNE_LEDGER} in {runDir}: {exc}")


def saveLedger(runDir, ledger):
    with open(os.path.join(runDir, PRUNE_LEDGER), "w") as f:
        json.dump(ledger, f, indent=2)
        f.write("\n")


def dirSize(path):
    total = 0
    for root, _dirs, names in os.walk(path):
        for name in names:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                continue
    return total


def loadUnitManifest(unitDir):
    try:
        with open(os.path.join(unitDir, MANIFEST_JSON), encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def pruneUnits(family, cfg, delete=False, echo=_echo):
    """Delete whole unit directories for rejected candidates — strictly the
    ones whose manifest hashes are covered by a data epoch, so --regen can
    always reproduce them bit-identically. Returns (units, bytes) affected."""
    stem = resolveStem(family)
    baseDir = runsDir(cfg)
    versions = versionDirs(stem, baseDir)
    if not versions:
        raise GenerationError(f"No run directories found for '{stem}' in {baseDir}.")
    if not hasAggregate(stem, baseDir):
        raise GenerationError(
            f"'{stem}' has no aggregate at {os.path.join(baseDir, stem)}; run "
            "runBatch.py to completion first. Pruning only touches finished, "
            "aggregated families.")

    registry = snapshotData.loadRegistry(cfg)
    if not registry["epochs"]:
        raise GenerationError(
            "No data epochs exist. Snapshot the store first "
            "(python snapshotData.py --snapshot) so pruned units stay "
            "regenerable, then re-run.")

    warnings = []
    totalUnits = totalBytes = 0
    for _version, runDir in versions:
        report = loadReport(runDir)
        runName = os.path.basename(runDir)
        if report is None:
            echo(f"  {runName}: no {REPORT_JSON}; skipped (incomplete version)")
            continue

        eligible = []  # (unitName, unitDir, ledgerEntry, size)
        for candidate in report.get("candidates", []):
            if candidate.get("tradeable"):
                continue
            symbol = candidate.get("symbol")
            timeframe = candidate.get("timeframe_minutes")
            unitName = f"{symbol}_M{timeframe}"
            unitDir = os.path.join(runDir, unitName)
            if not os.path.isdir(unitDir):
                continue  # already pruned
            manifest = loadUnitManifest(unitDir)
            if manifest is None:
                warnings.append(f"{runName}/{unitName}: unreadable manifest; left alone.")
                continue
            entry = next((s for s in manifest.get("symbols", [])
                          if s.get("symbol") == symbol), None)
            sourceHash = (entry or {}).get("source_hash", 0)
            sessionHash = (entry or {}).get("session_hash", 0)
            if not sourceHash or not sessionHash:
                warnings.append(
                    f"{runName}/{unitName}: manifest has no data fingerprint "
                    "(pre-v4); not regenerable-by-proof — use --prune-wf or "
                    "archive instead.")
                continue
            firstDay = parseDay(manifest.get("first_day"))
            lastDay = parseDay(manifest.get("last_day"))
            epochId = matchEpoch(registry, symbol, timeframe, firstDay, lastDay,
                                 sourceHash, sessionHash)
            if epochId is None:
                warnings.append(
                    f"{runName}/{unitName}: no data epoch matches its fingerprint; "
                    f"snapshot first (python snapshotData.py --snapshot {symbol}).")
                continue
            eligible.append((unitName, unitDir, {
                "symbol": symbol,
                "timeframe_minutes": timeframe,
                "first_day": manifest.get("first_day"),
                "last_day": manifest.get("last_day"),
                "source_hash": sourceHash,
                "session_hash": sessionHash,
                "engine_build": manifest.get("engine_build", ""),
                "epoch": epochId,
                "pruned_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            }, dirSize(unitDir)))

        size = sum(s for _n, _d, _e, s in eligible)
        totalUnits += len(eligible)
        totalBytes += size
        if delete and eligible:
            ledger = loadLedger(runDir)
            for unitName, unitDir, entry, _size in eligible:
                ledger["units"][unitName] = entry
            saveLedger(runDir, ledger)  # the ledger lands before anything dies
            for _name, unitDir, _entry, _size in eligible:
                shutil.rmtree(unitDir)
        verb = "deleted" if delete else "would delete"
        echo(f"  {runName}: {verb} {len(eligible)} unit dir(s), {size / 2**20:.1f} MB")
    for warning in warnings:
        echo(f"  Warning: {warning}")

    mode = "Deleted" if delete else "Dry run — would delete"
    echo(f"{mode} {totalUnits} unit dir(s), {totalBytes / 2**30:.2f} GB across "
         f"{len(versions)} version(s).")
    if not delete and totalUnits:
        echo("Re-run with --delete to actually remove them. Regenerate later with: "
             "python pruneRuns.py --regen <stem>_v<n>")
    return totalUnits, totalBytes


def regen(runName, cfg, threads=0, echo=_echo, runner=subprocess.run):
    """Re-create a version's pruned data by invoking bt_walkforward directly
    (runBatch's skip never backfills). The engine reuses every surviving unit
    and re-simulates only the missing ones. Refuses to run when the live store
    no longer matches what a pruned unit was computed from, naming the epoch
    to restore — regeneration must be exact or not happen at all."""
    baseDir = runsDir(cfg)
    runDir = os.path.join(baseDir, runName)
    if not os.path.isdir(runDir):
        raise GenerationError(f"no run directory {runDir}")
    specPath = os.path.join(specOutputDir(cfg), f"{runName}.json")
    if not os.path.isfile(specPath):
        raise GenerationError(f"no spec at {specPath}; --regen needs the original spec.")

    ledger = loadLedger(runDir)
    dataRoot = snapshotData.dataDir(cfg)
    registry = snapshotData.loadRegistry(cfg)
    for unitName, entry in sorted(ledger["units"].items()):
        if os.path.isdir(os.path.join(runDir, unitName)):
            continue  # already back
        symbol = entry["symbol"]
        current = snapshotData.symbolFingerprint(dataRoot, symbol)
        firstDay = parseDay(entry.get("first_day"))
        lastDay = parseDay(entry.get("last_day"))
        combined = snapshotData.combinedSourceHash(current, entry["timeframe_minutes"],
                                                   firstDay, lastDay)
        inRange = selectChunks(current, entry["timeframe_minutes"], firstDay, lastDay)
        if (combined == entry["source_hash"] and inRange
                and all(c["session_hash"] == entry["session_hash"] for c in inRange)):
            continue
        raise GenerationError(
            f"{runName}/{unitName}: the live store no longer matches the data this "
            f"unit was computed from. Restore it first:\n"
            f"  python snapshotData.py --restore {entry['epoch']} {symbol}\n"
            "then re-run --regen. Regenerating over different data would produce "
            "different results.")

    engineDir = snapshotData._engineDir(cfg)
    binary = os.path.join(engineDir, WALKFORWARD_EXE)
    if not os.path.isfile(binary):
        raise GenerationError(f"bt_walkforward.exe not found at {binary}; build the engine.")
    echo(f"Regenerating {runName} (engine reuses surviving units)...")
    proc = runner([binary, "--spec", specPath, "--threads", str(threads)], cwd=engineDir)
    if proc.returncode != 0:
        raise GenerationError(f"bt_walkforward failed (exit {proc.returncode}); "
                              f"see {os.path.join(runDir, 'run.log')}")

    # Regenerated units come off the ledger; an empty ledger comes off disk.
    ledger["units"] = {name: entry for name, entry in ledger["units"].items()
                       if not os.path.isdir(os.path.join(runDir, name))}
    if ledger["units"]:
        saveLedger(runDir, ledger)
    else:
        try:
            os.remove(os.path.join(runDir, PRUNE_LEDGER))
        except OSError:
            pass
    echo(f"Regenerated {runName}.")


# --- status ------------------------------------------------------------------

def familyStems(baseDir):
    """Every family stem present under runs/, folding version dirs onto their
    stem. Aggregate dirs (no version suffix) count as their own stem too."""
    stems = set()
    if not os.path.isdir(baseDir):
        return []
    for entry in os.listdir(baseDir):
        if os.path.isdir(os.path.join(baseDir, entry)):
            stems.add(re.sub(r"_v\d+$", "", entry))
    return sorted(stems)


def dirStats(path):
    """(files, bytes, wfFiles, wfBytes) for one run directory tree."""
    files = size = wfFiles = wfBytes = 0
    for root, _dirs, names in os.walk(path):
        for name in names:
            try:
                fileSize = os.path.getsize(os.path.join(root, name))
            except OSError:
                continue
            files += 1
            size += fileSize
            if name == WF_RESULTS:
                wfFiles += 1
                wfBytes += fileSize
    return files, size, wfFiles, wfBytes


def status(families, cfg, echo=_echo):
    baseDir = runsDir(cfg)
    stems = [resolveStem(f) for f in families] or familyStems(baseDir)
    echo(f"{'family':<40} {'versions':>8} {'size GB':>8} {'wf GB':>8} {'aggregate':>9}")
    for stem in stems:
        versions = versionDirs(stem, baseDir)
        files = size = wfFiles = wfBytes = 0
        for _version, runDir in versions:
            f, s, wf, wb = dirStats(runDir)
            files += f
            size += s
            wfFiles += wf
            wfBytes += wb
        if not versions and not os.path.isdir(os.path.join(baseDir, stem)):
            echo(f"{stem:<40} {'-':>8} no run directories found")
            continue
        agg = "yes" if hasAggregate(stem, baseDir) else "NO"
        echo(f"{stem:<40} {len(versions):>8} {size / 2**30:>8.2f} "
             f"{wfBytes / 2**30:>8.2f} {agg:>9}")


# --- entry point -------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Manually prune derived data from finished runs. Dry-run by "
                    "default; nothing is deleted without --delete. Never run "
                    "automatically — this is a human-invoked tool only.")
    parser.add_argument("families", nargs="*",
                        help="strategy name(s) or stem(s) — or run name(s) like "
                             "<stem>_v3 for --regen")
    parser.add_argument("--status", action="store_true",
                        help="show per-family disk usage and prunable footprint")
    parser.add_argument("--prune-wf", action="store_true",
                        help="prune wf_results.json for rejected candidates in "
                             "completed, aggregated versions")
    parser.add_argument("--prune-units", action="store_true",
                        help="delete whole unit dirs for rejected candidates whose "
                             "data fingerprint is covered by a data epoch")
    parser.add_argument("--regen", action="store_true",
                        help="regenerate pruned data for the named run version(s) "
                             "via bt_walkforward, after verifying the store matches")
    parser.add_argument("--delete", action="store_true",
                        help="actually delete (default is a dry run)")
    parser.add_argument("--threads", type=int, default=0,
                        help="engine threads for --regen (0 = all cores)")
    args = parser.parse_args(argv)

    modes = [args.status, args.prune_wf, args.prune_units, args.regen]
    if sum(modes) != 1:
        parser.error("choose exactly one of --status, --prune-wf, --prune-units, --regen")
    if not args.status and not args.families:
        parser.error("this mode needs at least one family (or run name for --regen)")

    cfg = config.load()
    try:
        if args.status:
            status(args.families, cfg)
        elif args.regen:
            for runName in args.families:
                regen(runName, cfg, threads=args.threads)
        else:
            prune = pruneUnits if args.prune_units else pruneWf
            for family in args.families:
                _echo(f"{resolveStem(family)}:")
                prune(family, cfg, delete=args.delete)
    except GenerationError as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
