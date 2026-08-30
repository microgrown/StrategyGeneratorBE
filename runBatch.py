"""One-command batch runner for a generated strategy's walkforward specs.

    python runBatch.py "<strategy name or stem>" [--threads N] [--force]

Discovers every generated spec for the strategy (<stem>_v1.json, _v2.json, ...),
runs bt_walkforward for the versions that have no selection output yet, and
aggregates the per-version selection files into runs/<stem>/ (the individual
run names minus the version suffix).

The engine executes the selection filter chain — Monte Carlo included — inside
bt_walkforward, so a version whose run directory already holds a selection
report is never handed to the engine again: its stored verdict is aggregated
as-is. Re-invoking this tool on a finished batch is therefore pure file
aggregation. Use --force after editing selection thresholds in the specs;
nothing else ever recomputes an existing result.

--prune (explicit opt-in, never implied) reclaims disk as the batch goes:
after each version completes, the aggregate-so-far is refreshed and that
version's rejected candidates are pruned — first their whole unit dirs where
provably regenerable (needs v4 manifests plus a covering data epoch), then
the lossless wf-sweep of whatever unit-pruning refused — so disk never holds
much more than the survivors plus one full version. Everything deleted comes
back via `pruneRuns.py --regen`. A data epoch must already exist (python
snapshotData.py --snapshot); without one the batch fails up front, before any
engine time is spent. Failed versions are left unpruned so they can be re-run
intact, and cached versions (engine not invoked) are not pruned either — use
pruneRuns.py to reclaim an already-finished family. Prune detail (counts,
sizes) prints only under --verbose; the default is one pass/fail line.
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone

import config
import lintElFeatures
from specWriter import specOutputDir
from strategyWriter import (GenerationError, generatedDirFor, loadManifest,
                            sanitizeIdentifier)

WALKFORWARD_EXE = os.path.join("build", "release", "bt_walkforward.exe")
RUNS_SUBDIR = "runs"
SUMMARY_CSV = "selection_summary.csv"
REPORT_JSON = "selection_report.json"
RUN_LOG = "run.log"

# Ownership marker inside the aggregate report; also what lets the safety check
# tell our aggregate dir apart from a real engine run dir.
AGGREGATE_MARKER = "StrategyGeneratorBE runBatch"
AGGREGATE_FORMAT = "runBatch-aggregate-1"

REBUILD_COMMAND = r".\scripts\build.ps1 -Config Release"

_VERSION_SUFFIX = re.compile(r"_v\d+$")


def _echo(*args, end="\n"):
    """Banner lines must reach the console before the engine's own output, and
    the engine child process writes unbuffered while Python does not. end=""
    leaves the line open so the run's outcome can be appended to it."""
    print(*args, end=end, flush=True)


def _silent(*args, end="\n"):
    """Swallows prune detail lines when --verbose is not given."""


@dataclass
class RunOutcome:
    version: int
    specPath: str
    runDir: str
    returnCode: int = 0
    skipped: bool = False  # selection output already existed; engine not invoked

    @property
    def ok(self):
        return self.returnCode == 0


@dataclass
class BatchResult:
    stem: str
    outcomes: list = field(default_factory=list)
    aggregateDir: str = ""  # "" when nothing was aggregated
    aggregatedVersions: list = field(default_factory=list)  # run names
    warnings: list = field(default_factory=list)
    reports: dict = field(default_factory=dict)  # run name -> per-run report

    @property
    def failed(self):
        return [o for o in self.outcomes if not o.ok]


# --- discovery ---------------------------------------------------------------

def _engineDir(cfg):
    engineDir = (cfg.get("engineDir") or "").strip()
    if not engineDir:
        raise GenerationError("No BacktestEngine root is configured.")
    return engineDir


def runsDir(cfg):
    return os.path.normpath(os.path.join(_engineDir(cfg), RUNS_SUBDIR))


def resolveStem(nameOrStem):
    """Fold a strategy name (or an already-folded stem) into the spec stem.
    sanitizeIdentifier is idempotent under this composition, so both work."""
    return sanitizeIdentifier(nameOrStem).lower()


def discoverSpecs(stem, cfg):
    """[(version, specPath)] for v1..N until the first missing file — the same
    walk _pruneStaleSpecs uses, and the same f-string specStem produces."""
    specDir = specOutputDir(cfg)
    specs = []
    version = 1
    while True:
        path = os.path.join(specDir, f"{stem}_v{version}.json")
        if not os.path.exists(path):
            return specs
        specs.append((version, path))
        version += 1


def binaryPath(cfg):
    path = os.path.join(_engineDir(cfg), WALKFORWARD_EXE)
    if not os.path.isfile(path):
        raise GenerationError(
            f"bt_walkforward.exe not found at {path}. "
            f"Build the engine first: {REBUILD_COMMAND}"
        )
    return path


def hasSelectionOutput(runDir):
    return os.path.isfile(os.path.join(runDir, REPORT_JSON))


# --- engine invocation -------------------------------------------------------

def runSpecs(specs, stem, cfg, threads, force, runner=subprocess.run, echo=_echo,
             verbose=False, onOutcome=None, jobs=1):
    """Run bt_walkforward for every version without selection output (all of
    them under --force). Sequential by default — the engine parallelizes
    internally; jobs > 1 runs that many versions at once for specs whose grids
    are too small to fill the machine on their own. Failures don't stop the
    batch; each outcome records its exit code. onOutcome, when given, is
    called with each outcome as it lands (skipped and failed ones included),
    always on the calling thread — the hook interleaved pruning hangs off.
    Outcomes come back in version order whatever order the runs finished in.

    One line per version: the engine runs under --quiet, so it prints only
    genuine errors (its run.log still records everything), and the line opened
    before a run is closed by that run's outcome. --verbose drops --quiet when
    a run needs watching. Concurrent runs cannot share the console, so under
    jobs > 1 each run's output is captured and only a failed run's is echoed,
    after its own status line."""
    engineDir = _engineDir(cfg)
    baseDir = runsDir(cfg)
    plans = []
    for version, specPath in specs:
        runDir = os.path.join(baseDir, f"{stem}_v{version}")
        skip = not force and hasSelectionOutput(runDir)
        plans.append((version, specPath, runDir, skip))

    # Resolve (and validate) the binary only if something actually runs, so a
    # fully cached batch aggregates fine on a machine without a built engine.
    binary = None
    if any(not skip for _, _, _, skip in plans):
        binary = binaryPath(cfg)

    if jobs > 1:
        return _runSpecsConcurrently(plans, stem, engineDir, binary, threads, verbose,
                                     runner, echo, onOutcome, jobs)

    outcomes = []
    for i, (version, specPath, runDir, skip) in enumerate(plans, 1):
        runName = f"{stem}_v{version}"
        if skip:
            echo(f"[{i}/{len(plans)}] {runName} — results exist, skipping")
            outcomes.append(RunOutcome(version, specPath, runDir, 0, True))
            if onOutcome:
                onOutcome(outcomes[-1])
            continue
        echo(f"[{i}/{len(plans)}] {runName} ... ", end="")
        command = [binary, "--spec", specPath, "--threads", str(threads)]
        if not verbose:
            command.append("--quiet")
        started = time.monotonic()
        proc = runner(command, cwd=engineDir)  # engine paths are relative to it
        elapsed = time.monotonic() - started
        status = "OK" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})"
        echo(f"{status} {elapsed:.1f}s")
        outcomes.append(RunOutcome(version, specPath, runDir, proc.returncode))
        if onOutcome:
            onOutcome(outcomes[-1])
    return outcomes


def childThreads(threads, jobs):
    """Engine threads for each of `jobs` concurrent runs: an explicit count
    passes through; 0 (all cores) is split so the runs share the machine
    instead of each claiming all of it."""
    if threads or jobs <= 1:
        return threads
    return max(1, (os.cpu_count() or 1) // jobs)


def _runSpecsConcurrently(plans, stem, engineDir, binary, threads, verbose, runner, echo,
                          onOutcome, jobs):
    total = len(plans)
    echoLock = threading.Lock()
    perRun = childThreads(threads, jobs)

    def run(i, version, specPath, runDir):
        runName = f"{stem}_v{version}"
        with echoLock:
            echo(f"[{i}/{total}] {runName} started")
        command = [binary, "--spec", specPath, "--threads", str(perRun)]
        if not verbose:
            command.append("--quiet")
        started = time.monotonic()
        proc = runner(command, cwd=engineDir, stdout=subprocess.PIPE,
                      stderr=subprocess.STDOUT, text=True)
        elapsed = time.monotonic() - started
        status = "OK" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})"
        with echoLock:
            echo(f"[{i}/{total}] {runName} {status} {elapsed:.1f}s")
            output = getattr(proc, "stdout", None)
            if proc.returncode != 0 and output:
                echo(output.rstrip())
        return RunOutcome(version, specPath, runDir, proc.returncode)

    # Everything that touches shared state -- outcomes, the caller's hook --
    # happens here on the calling thread; the workers only run the engine.
    outcomes = []
    for i, (version, specPath, runDir, skip) in enumerate(plans, 1):
        if skip:
            echo(f"[{i}/{total}] {stem}_v{version} — results exist, skipping")
            outcomes.append(RunOutcome(version, specPath, runDir, 0, True))
            if onOutcome:
                onOutcome(outcomes[-1])
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = [pool.submit(run, i, version, specPath, runDir)
                   for i, (version, specPath, runDir, skip) in enumerate(plans, 1)
                   if not skip]
        for future in as_completed(futures):
            outcomes.append(future.result())
            if onOutcome:
                onOutcome(outcomes[-1])
    outcomes.sort(key=lambda o: o.version)
    return outcomes


def preflightSelectionWarning(specs, warnings):
    """The whole point of the batch is the pass/fail verdicts, which only exist
    if the specs carry a selection block — warn up front when they don't."""
    try:
        # utf-8-sig: hand-edited specs may carry a BOM, which the engine accepts
        with open(specs[0][1], encoding="utf-8-sig") as f:
            spec = json.load(f)
    except (OSError, ValueError):
        warnings.append(f"Could not read {specs[0][1]} to check for a selection block.")
        return
    if "selection" not in spec:
        warnings.append(
            'The specs have no "selection" block, so the engine runs the '
            "walkforward only and there are no pass/fail results to aggregate. "
            "Point specTemplate at a spec with a selection block and re-run "
            "Make Strategy."
        )


def preflightFeatureGate(stem, cfg, warnings):
    """Re-check this batch's EasyLanguage features against the register.

    `strategyWriter.generate` already gated these when the header was written.
    This catches the other direction: a feature DOWNGRADED since — a row moved
    to UNKNOWN because a probe came back and contradicted what we assumed — on
    headers that were generated while it still looked settled. Running a whole
    batch on that is what the register exists to prevent.

    Raises GenerationError on a blocking feature; everything else is a warning,
    because a batch must never fail for a reason that is not about the batch."""
    try:
        manifest = loadManifest(generatedDirFor(cfg))
        registry = lintElFeatures.loadRegistry()
    except (GenerationError, lintElFeatures.LintError, OSError, ValueError) as exc:
        warnings.append(f"Could not re-check EasyLanguage features: {exc}")
        return

    recorded, described = set(), False
    for name, entry in manifest.items():
        if sanitizeIdentifier(name).lower() != stem:
            continue
        features = entry.get("elFeatures")
        if features is None:
            warnings.append(
                f"'{name}' was generated before the EasyLanguage feature gate "
                "existed, so its features are unrecorded. Re-run Make Strategy "
                "to record them.")
            continue
        described = True
        recorded |= set(features)

    if not described:
        return
    blocking = sorted(f for f in recorded
                      if registry.get(f, lintElFeatures.UNKNOWN) == lintElFeatures.UNKNOWN)
    if blocking:
        raise GenerationError(
            f"Batch '{stem}' uses EasyLanguage feature(s) whose behaviour is not "
            f"established: {', '.join(blocking)}. They were settled when the "
            "headers were generated and have since been downgraded in "
            f"rules/{lintElFeatures.REGISTRY_NAME}. Re-run Make Strategy after "
            "the probe settles them.")


# --- aggregation -------------------------------------------------------------

def loadRunSelection(runDir, runName, warnings):
    """(fieldnames, rows, report) for one run's selection output, or None when
    the run has none. Unreadable files are warned about and treated as absent."""
    reportPath = os.path.join(runDir, REPORT_JSON)
    if not os.path.isfile(reportPath):
        return None
    try:
        with open(reportPath, encoding="utf-8-sig") as f:
            report = json.load(f)
    except (OSError, ValueError):
        warnings.append(f"{runName}: unreadable {REPORT_JSON}; excluded from the aggregate.")
        return None

    fieldnames, rows = [], []
    csvPath = os.path.join(runDir, SUMMARY_CSV)
    if os.path.isfile(csvPath):
        try:
            with open(csvPath, newline="") as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames or [])
                rows = list(reader)
        except OSError:
            warnings.append(f"{runName}: unreadable {SUMMARY_CSV}; its rows are "
                            "missing from the aggregate.")
    else:
        warnings.append(f"{runName}: no {SUMMARY_CSV}; its rows are missing "
                        "from the aggregate.")
    return fieldnames, rows, report


def mergeSummaryRows(perRun):
    """perRun: [(runName, fieldnames, rows)] -> (header, rows, divergentRuns).
    Union of columns by name in first-seen order behind a leading "run" column,
    so rows can never misalign even if versions disagree about columns (they
    shouldn't — every spec clones one template)."""
    header, first, divergent, outRows = ["run"], None, [], []
    for runName, fieldnames, rows in perRun:
        if first is None:
            first = list(fieldnames)
        elif list(fieldnames) != first:
            divergent.append(runName)
        for name in fieldnames:
            if name not in header:
                header.append(name)
        for row in rows:
            merged = {"run": runName}
            merged.update(row)
            outRows.append(merged)
    return header, outRows, divergent


def buildAggregateReport(stem, reports):
    """reports: {runName: per-run report}, version order. Per-run payloads are
    embedded verbatim, so every tradeable entry keeps its full metrics. The
    top level deliberately has no "format_version"/"candidates" keys — the
    engine GUI's report reader then rejects this file cleanly instead of
    half-parsing the aggregate dir as a run."""
    return {
        "aggregated_by": AGGREGATE_MARKER,
        "format": AGGREGATE_FORMAT,
        "stem": stem,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "runs": reports,
    }


def readAggregateMarker(reportPath):
    """The "aggregated_by" value of an aggregate report, or None when the file
    is unreadable or does not start with that key. buildAggregateReport writes
    it as the first key precisely so this needs only a prefix: the aggregate
    embeds every version's report and runs to gigabytes on big families, so a
    full json.load here is minutes (and a MemoryError) per call — and --prune
    calls it once per version."""
    try:
        with open(reportPath, encoding="utf-8-sig") as f:
            head = f.read(4096)
    except OSError:
        return None
    match = re.match(r'\s*\{\s*"aggregated_by"\s*:\s*"((?:[^"\\]|\\.)*)"', head)
    if match is None:
        return None
    try:
        return json.loads(f'"{match.group(1)}"')
    except ValueError:
        return None


def checkAggregateDirSafety(aggDir):
    """runs/<stem>/ must not be a real engine run (a spec named exactly <stem>
    would put one there) or hold files some other tool wrote."""
    if not os.path.isdir(aggDir):
        return
    if os.path.exists(os.path.join(aggDir, RUN_LOG)):
        raise GenerationError(
            f"'{aggDir}' looks like a real engine run ({RUN_LOG} present), so a "
            "spec is named exactly like the aggregate. Rename the strategy or "
            "move that run; refusing to overwrite."
        )
    for entry in os.listdir(aggDir):
        if os.path.isfile(os.path.join(aggDir, entry, "wf_results.json")):
            raise GenerationError(
                f"'{aggDir}' contains engine results ({entry}); refusing to "
                "overwrite a real run directory."
            )
    reportPath = os.path.join(aggDir, REPORT_JSON)
    if os.path.exists(reportPath):
        if readAggregateMarker(reportPath) != AGGREGATE_MARKER:
            raise GenerationError(
                f"'{reportPath}' was not written by runBatch; refusing to overwrite."
            )


def writeAggregate(stem, outcomes, cfg, warnings, cache=None):
    """Aggregate whatever selection output exists across the batch — including
    from failed or skipped versions. Returns (aggregateDir, runNames, reports);
    aggregateDir is "" when there was nothing to aggregate.

    cache, when given, is a {runName: loaded} dict that outlives this call:
    a version's selection output is read from disk once and reused by every
    later call sharing the dict. --prune rewrites the aggregate after every
    version, and without the cache each rewrite re-parses every finished
    version's report — quadratic in the family size. Only successful loads
    are cached, so a version with unreadable output is retried (and warned
    about) on each call, exactly as without the cache."""
    perRun = []  # (runName, fieldnames, rows, report, encodedReport)
    for outcome in outcomes:
        runName = f"{stem}_v{outcome.version}"
        loaded = cache.get(runName) if cache is not None else None
        if loaded is None:
            loaded = loadRunSelection(outcome.runDir, runName, warnings)
            if loaded is not None:
                # Encoded once: the report is embedded verbatim, so its JSON
                # text never changes between rewrites.
                loaded = loaded + (json.dumps(loaded[2]),)
                if cache is not None:
                    cache[runName] = loaded
        if loaded is not None:
            perRun.append((runName,) + loaded)
    if not perRun:
        warnings.append("No selection results exist, so no aggregate was written.")
        return "", [], {}

    aggDir = os.path.join(runsDir(cfg), stem)
    checkAggregateDirSafety(aggDir)
    os.makedirs(aggDir, exist_ok=True)

    header, rows, divergent = mergeSummaryRows(
        [(name, fields, rws) for name, fields, rws, _, _ in perRun]
    )
    if divergent:
        warnings.append(
            "Summary columns differ across versions ("
            + ", ".join(divergent)
            + "); the aggregate CSV is a union with blanks."
        )
    # Written whole-or-not: with versions running concurrently the aggregate
    # is rewritten while a later version's prune may read it back, and a
    # torn file would trip checkAggregateDirSafety.
    summaryPath = os.path.join(aggDir, SUMMARY_CSV)
    with open(summaryPath + ".tmp", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, restval="")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(summaryPath + ".tmp", summaryPath)

    reports = {name: report for name, _, _, report, _ in perRun}
    reportPath = os.path.join(aggDir, REPORT_JSON)
    # Streamed from the per-version encodings, byte-identical to
    # json.dump(buildAggregateReport(stem, reports), f): the envelope is
    # dumped with an empty "runs" and its closing "}}" replaced by the
    # cached run entries. Compact on purpose — this file is read by machines
    # only (the engine's report reader rejects it by its first key;
    # readAggregateMarker reads a 4 KB prefix), and re-encoding gigabytes,
    # pretty-printed, was most of every rewrite under --prune.
    envelope = json.dumps(buildAggregateReport(stem, {}))
    assert envelope.endswith('"runs": {}}')
    with open(reportPath + ".tmp", "w") as f:
        f.write(envelope[:-2])
        for i, (name, _, _, _, encoded) in enumerate(perRun):
            f.write(f'{", " if i else ""}{json.dumps(name)}: {encoded}')
        f.write("}}\n")
    os.replace(reportPath + ".tmp", reportPath)
    return aggDir, [name for name, _, _, _, _ in perRun], reports


# --- orchestration -----------------------------------------------------------

def runBatch(nameOrStem, cfg, threads=0, force=False, runner=subprocess.run, echo=_echo,
             verbose=False, prune=False, jobs=1):
    stem = resolveStem(nameOrStem)
    specs = discoverSpecs(stem, cfg)
    if not specs:
        message = (f"No specs found for '{stem}' in {specOutputDir(cfg)}. "
                   "Run Make Strategy first.")
        if _VERSION_SUFFIX.search(stem):
            base = _VERSION_SUFFIX.sub("", stem)
            message += (f" Did you mean '{base}'? runBatch takes the strategy "
                        "stem without the version suffix.")
        raise GenerationError(message)

    warnings = []
    preflightSelectionWarning(specs, warnings)
    preflightFeatureGate(stem, cfg, warnings)

    # Opt-in only: pruning happens strictly because --prune was typed on this
    # invocation. It is interleaved — each version's rejects are pruned as soon
    # as that version succeeds, so disk never accumulates the whole family —
    # which is why the epoch check must fail HERE, before any engine time is
    # spent, rather than after the first version has already run.
    registry = None
    if prune:
        import pruneRuns  # deferred: pruneRuns imports this module
        registry = pruneRuns.requireEpochs(cfg)

    seen = []
    loadedSelections = {}  # runName -> loaded selection output, read once

    def afterVersion(outcome):
        seen.append(outcome)
        if not (prune and outcome.ok and hasSelectionOutput(outcome.runDir)):
            return  # failed versions stay intact for their re-run
        if outcome.skipped:
            return  # cached: the engine produced nothing new, so nothing to prune
        runName = f"{stem}_v{outcome.version}"
        try:
            # Roll the verdicts up before touching data: the aggregate-so-far
            # is what makes the finished versions' results safe to prune (the
            # final writeAggregate below re-derives it with warnings kept).
            writeAggregate(stem, sorted(seen, key=lambda o: o.version), cfg, [],
                           cache=loadedSelections)
            # The per-file counts and sizes only appear under --verbose; the
            # default console gets a single pass/fail line per version.
            detail = echo if verbose else _silent
            if verbose:
                echo(f"Pruning {runName} rejects (--prune):")
            pruneRuns.pruneVersion(stem, outcome.version, cfg, registry, echo=detail)
            echo(f"Pruned {runName} rejects (--prune).")
        except GenerationError as exc:
            echo(f"Pruning {runName} rejects failed (--prune).")
            warnings.append(f"--prune ({runName}) failed: {exc}")

    outcomes = runSpecs(specs, stem, cfg, threads, force, runner, echo, verbose,
                        onOutcome=afterVersion if prune else None, jobs=jobs)
    aggregateDir, aggregated, reports = writeAggregate(stem, outcomes, cfg, warnings,
                                                       cache=loadedSelections)

    if prune:
        if any(not o.ok for o in outcomes):
            warnings.append("--prune: failed version(s) were left unpruned; "
                            "prune manually with pruneRuns.py once they pass.")
        if not aggregateDir:
            warnings.append("--prune skipped: no aggregate was written.")

    return BatchResult(stem, outcomes, aggregateDir, aggregated, warnings, reports)


def formatSummary(result):
    lines = [f"Batch '{result.stem}': {len(result.outcomes)} version(s)"]
    for outcome in result.outcomes:
        runName = f"{result.stem}_v{outcome.version}"
        report = result.reports.get(runName)
        if report is not None:
            candidates = report.get("candidates", [])
            passing = sum(1 for c in candidates if c.get("tradeable"))
            tradeable = f"tradeable {passing}/{len(candidates)}"
        else:
            tradeable = "tradeable n/a"
        if outcome.skipped:
            status = "cached"
        elif outcome.ok:
            status = "OK"
        else:
            status = f"FAIL (exit {outcome.returnCode})"
        line = f"  {runName:<32} {status:<14} {tradeable}"
        if not outcome.ok:
            line += f" — see {os.path.join(outcome.runDir, RUN_LOG)}"
            if outcome.returnCode == 2:
                line += (f"; if it says 'unknown strategy', rebuild the engine "
                         f"({REBUILD_COMMAND})")
        lines.append(line)
    if result.aggregateDir:
        lines.append(f"Aggregate: {os.path.join(result.aggregateDir, SUMMARY_CSV)}")
        lines.append(f"           {os.path.join(result.aggregateDir, REPORT_JSON)}")
    for warning in result.warnings:
        lines.append(f"Warning: {warning}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run every generated walkforward spec for a strategy and "
                    "aggregate the selection results into runs/<stem>/."
    )
    parser.add_argument("strategy",
                        help='strategy name or stem, e.g. "Momentum Clone" or momentum_clone')
    parser.add_argument("--threads", type=int, default=0,
                        help="engine threads per run (0 = all cores, split evenly "
                             "across --jobs; default 0)")
    parser.add_argument("--jobs", type=int, default=1,
                        help="versions to run at once (default 1); worth raising "
                             "only for specs whose grids cannot fill the machine "
                             "on their own")
    parser.add_argument("--force", action="store_true",
                        help="re-run the engine even for versions that already "
                             "have selection results (recomputes their verdicts)")
    parser.add_argument("--verbose", action="store_true",
                        help="let the engine print its progress and warnings "
                             "instead of errors only (run.log has them either way)")
    parser.add_argument("--prune", action="store_true",
                        help="prune each version's rejected candidates as soon "
                             "as it completes: delete their unit dirs where "
                             "provably regenerable, then their remaining "
                             "wf_results.json (all restorable via pruneRuns.py "
                             "--regen); requires a data epoch (snapshotData.py "
                             "--snapshot) and never runs unless asked")
    args = parser.parse_args(argv)

    try:
        result = runBatch(args.strategy, config.load(),
                          threads=args.threads, force=args.force,
                          verbose=args.verbose, prune=args.prune,
                          jobs=max(1, args.jobs))
    except GenerationError as exc:
        print(exc, file=sys.stderr)
        return 2
    print(formatSummary(result))
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
