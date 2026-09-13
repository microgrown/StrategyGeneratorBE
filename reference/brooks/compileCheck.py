"""Reusable compile check for newly authored rules.

The author-rule skill only validates a rule's JSON shape; nothing about a rule
becomes C++ until it is PLACED in a template and run through
``makeStrategy.py``, and nothing is actually compiled until the engine repo's
``scripts/build.ps1`` runs. This script closes that loop for a batch of
freshly authored rules without touching ``rules/``, ``templates/``,
``rules/CATALOG.md`` or ``rules/EL_FEATURES.md``.

    python reference/brooks/compileCheck.py                      # rules changed since HEAD
    python reference/brooks/compileCheck.py --since <git-ref>
    python reference/brooks/compileCheck.py --rules RuleA,RuleB
    python reference/brooks/compileCheck.py --batch-size 25 --keep

WHAT IT DOES

1. Collects rule names to check: files under ``rules/*.json`` that are
   untracked or modified relative to ``--since`` (default ``HEAD``), via
   ``git status --porcelain rules/`` plus ``git diff --name-only <ref> --
   rules/``. ``--rules a,b,c`` overrides this entirely.

2. Groups the collected rules by their declared ``type`` (Entry/Exit/Switch)
   and, within each type, chunks them into batches of ``--batch-size`` (default
   40). For each batch it writes ONE scratch template (a temp file, never
   under ``templates/``) with a single pane of that type holding every rule in
   the batch as its OWN delimiter-separated group, pinned to its default
   inputs (blank params -- ``strategyWriter`` falls back to each input's
   declared default, with blank Stop/Step so it is pinned to one value, exactly
   the templateIO/GUI convention). Because groups cross-multiply only ACROSS
   panes, one pane with N one-rule groups yields N independent versions, no
   other-pane cross product -- so all N rules' C++ still lands in ONE
   generated header (one file per batch), each in its own class, with nothing
   from one rule able to hide a problem in another the way ANDing them into a
   single class body could.

3. Runs ``makeStrategy.py <template> --no-save-template`` headlessly for each
   batch (this is what actually turns the rule JSON into C++, writing a
   generated header + one spec per version into the engine repo -- see
   ``README.md``'s "Generating without the GUI" section). Strategy names are
   prefixed ``CompileCheck_`` so they are unmistakable and easy to find/delete.

4. Once every batch has been generated, builds the engine ONCE:
   ``powershell -File scripts/build.ps1 -Config Release`` from the engine
   repo (the real compile check per the author-rule skill). Compiler
   errors/warnings are parsed from MSVC's ``file(line): error CNNNN: msg``
   output and mapped back to a rule name by reading the generated header:
   each version is its own ``class Gen_<batch>_V<n> : public Strategy {``,
   immediately preceded by a comment ``// "<reg name>": entries|exits|switches
   <RuleName>`` (strategyWriter._classLines / _summaryComment) -- exactly one
   rule per class here, so the nearest preceding class-start line at or before
   the diagnostic's line number identifies the rule unambiguously. A
   diagnostic that falls before any class in one of our headers (e.g. a bad
   #include) is reported as a batch-level error instead of guessing a rule.

5. Prints a summary (rules checked, batches, build result, per-rule
   errors/warnings) and exits 1 on any error. Unless ``--keep``, every file
   this run created in the engine repo (generated headers, their specs) is
   removed and ``manifest.json``/``headers.inc``/``registry.inc`` are rewritten
   via ``strategyWriter.rebuildIncFiles`` to drop the now-missing headers --
   the same prune path a hand-deleted header already goes through.

This never modifies anything under ``rules/`` or ``templates/``; it only reads
rule JSON and writes into the engine repo's generated tree (cleaned up
afterward by default).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import config
import ruleIO
import strategyWriter

DELIM = "-" * 30
PREFIX = "CompileCheck_"
DEFAULT_BATCH_SIZE = 40
CLASS_RE = re.compile(r'^class (Gen_\w+) : public Strategy')
COMMENT_RE = re.compile(r'^// ".*?":\s*(?:entries|exits|switches)\s+(.+)$')
# MSVC: "<path>(<line>[,<col>]): error|warning CNNNN: <message>"
DIAG_RE = re.compile(
    r'^(?P<file>[A-Za-z]:[^():]+|[^():]+)\((?P<line>\d+)(?:,\d+)?\)\s*:\s*'
    r'(?P<sev>error|warning)\s+(?P<code>[A-Za-z0-9]+)\s*:\s*(?P<msg>.*)$'
)


def run(cmd, cwd=None, timeout=None):
    return subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, timeout=timeout)


# --- step 1: which rules -----------------------------------------------------

def _porcelainPaths(text):
    paths = []
    for line in text.splitlines():
        if not line.strip():
            continue
        # "XY path" or "XY old -> new" for renames; path may be quoted by git
        # if it contains unusual characters, which we do not need to handle
        # for rules/*.json names.
        rest = line[3:] if len(line) > 3 else line.lstrip("? MADRU").strip()
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[1]
        paths.append(rest.strip())
    return paths


def collectChangedRuleNames(since):
    status = run(["git", "status", "--porcelain", "rules/"], cwd=ROOT)
    diff = run(["git", "diff", "--name-only", since, "--", "rules/"], cwd=ROOT)
    candidates = set(_porcelainPaths(status.stdout))
    candidates.update(line.strip() for line in diff.stdout.splitlines() if line.strip())

    names = set()
    for p in candidates:
        p = p.replace("\\", "/")
        if not p.startswith("rules/") or not p.endswith(".json"):
            continue
        if "/" in p[len("rules/"):]:
            continue  # nested, not a top-level rule file
        names.add(os.path.basename(p)[:-len(".json")])
    return sorted(names)


def loadRules(names):
    """Returns (rulesByType, skipped). A rule that fails to load (e.g. a JSON
    file caught mid-write by a concurrent authoring pass) is skipped, not
    fatal -- it just was not there to check yet."""
    byType = {}
    skipped = []
    for name in names:
        try:
            rule = ruleIO.loadRule(name)
        except Exception as exc:
            skipped.append((name, str(exc)))
            continue
        byType.setdefault(rule.type, []).append(name)
    return byType, skipped


# --- step 2: scratch templates -----------------------------------------------

def chunk(seq, size):
    return [seq[i:i + size] for i in range(0, len(seq), size)]


def buildTemplate(strategyName, ruleType, ruleNames, maxBarsBack):
    items = []
    for i, name in enumerate(ruleNames):
        if i:
            items.append(DELIM)
        items.append({"name": name, "flipped": False, "negated": False, "params": {}})
    return {
        "strategyName": strategyName,
        "maxBarsBack": str(maxBarsBack or ""),
        "panes": [{"ruleType": ruleType, "items": items}],
    }


# --- step 3: generate ---------------------------------------------------------

class Batch:
    def __init__(self, strategyName, ruleType, ruleNames):
        self.strategyName = strategyName
        self.ruleType = ruleType
        self.ruleNames = ruleNames  # version 1..N order, index -> rule
        self.generated = False
        self.headerPath = None
        self.specPaths = []
        self.genError = None  # stderr text if makeStrategy failed


def generateBatch(batch, engineDir, tmpDir):
    cfg = config.load()
    templatePath = os.path.join(tmpDir, strategyWriter.sanitizeIdentifier(batch.strategyName) + ".json")
    data = buildTemplate(batch.strategyName, batch.ruleType, batch.ruleNames, cfg.get("maxBarsBack"))
    with open(templatePath, "w") as f:
        json.dump(data, f, indent=4)

    cmd = [sys.executable, os.path.join(ROOT, "makeStrategy.py"), templatePath,
           "--no-save-template"]
    if engineDir:
        cmd += ["--engine-dir", engineDir]
    proc = run(cmd, cwd=ROOT)

    dirCfg = dict(cfg, engineDir=engineDir or cfg.get("engineDir"))
    generatedDir = strategyWriter.generatedDirFor(dirCfg)
    if proc.returncode != 0:
        batch.genError = proc.stdout.strip()
        return

    batch.generated = True
    headerName = strategyWriter.headerFileName(batch.strategyName)
    batch.headerPath = os.path.join(generatedDir, headerName)

    specCfg = dict(cfg)
    if engineDir:
        specCfg["engineDir"] = engineDir
    try:
        import specWriter
        specDir = specWriter.specOutputDir(specCfg)
        for v in range(1, len(batch.ruleNames) + 1):
            batch.specPaths.append(
                os.path.join(specDir, strategyWriter.specStem(batch.strategyName, v) + ".json"))
    except Exception:
        pass  # cleanup best-effort; a missing spec dir is not a compile problem


# --- step 4: build + map diagnostics -----------------------------------------

def runEngineBuild(engineDir, timeoutSec):
    cmd = ["powershell", "-File", "scripts/build.ps1", "-Config", "Release"]
    try:
        proc = run(cmd, cwd=engineDir, timeout=timeoutSec)
        return proc.returncode, proc.stdout, False
    except subprocess.TimeoutExpired as exc:
        return 1, (exc.stdout or ""), True


def _headerClassRanges(headerPath):
    """[(startLine, ruleName)] in ascending line order, 1-based."""
    ranges = []
    try:
        with open(headerPath, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return ranges
    pendingComment = None
    for i, line in enumerate(lines, 1):
        m = COMMENT_RE.match(line.strip())
        if m:
            pendingComment = m.group(1).strip()
            continue
        if CLASS_RE.match(line.strip()):
            ranges.append((i, pendingComment or "?"))
            pendingComment = None
    return ranges


def ruleForLine(classRanges, lineNo):
    rule = None
    for startLine, name in classRanges:
        if startLine <= lineNo:
            rule = name
        else:
            break
    return rule


def parseDiagnostics(buildOutput, batches):
    """Returns (perRule: {rule: [(sev, msg)]}, batchLevel: {strategyName: [(sev, msg)]}).

    Matched by the header's BASENAME rather than a resolved path: cl.exe
    prints whatever path it was given on the command line, which under
    CMake/Ninja is typically relative to the build directory, not to
    engineDir -- but our generated header names (``gen_compilecheck_...h``)
    are unique enough that basename matching is unambiguous."""
    headerToBatch = {os.path.basename(b.headerPath).lower(): b
                     for b in batches if b.generated}
    classRangesCache = {}
    perRule = {}
    batchLevel = {}

    for line in buildOutput.splitlines():
        m = DIAG_RE.match(line.strip())
        if not m:
            continue
        base = os.path.basename(m.group("file")).lower()
        batch = headerToBatch.get(base)
        if batch is None:
            continue  # not one of ours -- pre-existing engine issue, not our concern
        lineNo = int(m.group("line"))
        sev = m.group("sev")
        msg = f'{m.group("code")}: {m.group("msg")}'
        if base not in classRangesCache:
            classRangesCache[base] = _headerClassRanges(batch.headerPath)
        rule = ruleForLine(classRangesCache[base], lineNo)
        if rule == "?":
            rule = None
        if rule:
            perRule.setdefault(rule, []).append((sev, msg))
        else:
            batchLevel.setdefault(batch.strategyName, []).append((sev, msg))
    return perRule, batchLevel


def attributeGenError(batch):
    """makeStrategy failed before/while writing the header (e.g. a bad
    optimizer grid, or lintElFeatures blocking an unmeasured EL feature).
    Both raise messages that name the offending rule -- lintElFeatures as
    "  RuleName: msg" lines, the grid validator as "Rule 'RuleName', ...".
    Fall back to batch-level if no name in the message matches."""
    text = batch.genError or ""
    hits = {}
    for name in batch.ruleNames:
        pat = re.compile(r'(?:^|\s)' + re.escape(name) + r"[:',\s]", re.M)
        if pat.search(text):
            hits.setdefault(name, []).append(("error", text))
    return hits


# --- step 5: cleanup ----------------------------------------------------------

def cleanupBatch(batch, engineDir):
    removed = []
    if batch.headerPath and os.path.exists(batch.headerPath):
        os.remove(batch.headerPath)
        removed.append(batch.headerPath)
    for p in batch.specPaths:
        if os.path.exists(p):
            os.remove(p)
            removed.append(p)
    return removed


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compile-check newly authored rules by generating throwaway "
                    "strategies and rebuilding the engine.")
    parser.add_argument("--since", default="HEAD",
                        help="git ref to diff rules/ against (default: HEAD)")
    parser.add_argument("--rules", help="comma-separated rule names, overrides git discovery")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        help="max rules per generated strategy (default: %(default)s)")
    parser.add_argument("--engine-dir", dest="engineDir", help="BacktestEngine root (default: config.json)")
    parser.add_argument("--build-timeout", type=int, default=900,
                        help="seconds to allow the engine build (default: %(default)s)")
    parser.add_argument("--keep", action="store_true",
                        help="keep the generated strategies/headers instead of removing them")
    args = parser.parse_args(argv)

    cfg = config.load()
    engineDir = args.engineDir or cfg.get("engineDir")

    if args.rules:
        names = [n.strip() for n in args.rules.split(",") if n.strip()]
    else:
        names = collectChangedRuleNames(args.since)

    if not names:
        print("No changed rules/*.json found to compile-check.")
        return 0

    byType, skipped = loadRules(names)
    for name, err in skipped:
        print(f"SKIP {name}: could not load ({err})")

    totalRules = sum(len(v) for v in byType.values())
    if totalRules == 0:
        print("No loadable rules among the collected names.")
        return 1 if skipped else 0

    batches = []
    for ruleType, ruleNames in sorted(byType.items()):
        for i, part in enumerate(chunk(sorted(ruleNames), args.batch_size), 1):
            strategyName = f"{PREFIX}{ruleType}_{i}"
            batches.append(Batch(strategyName, ruleType, part))

    print(f"Compile-checking {totalRules} rule(s) across {len(batches)} batch(es): "
          + ", ".join(f"{b.strategyName} ({len(b.ruleNames)} {b.ruleType})" for b in batches))

    tmpDir = tempfile.mkdtemp(prefix="compileCheck_")
    try:
        for batch in batches:
            generateBatch(batch, engineDir, tmpDir)
    finally:
        try:
            for f in os.listdir(tmpDir):
                os.remove(os.path.join(tmpDir, f))
            os.rmdir(tmpDir)
        except OSError:
            pass

    genErrorsByRule = {}
    genBatchLevel = {}
    for batch in batches:
        if batch.genError:
            hits = attributeGenError(batch)
            for name, entries in hits.items():
                genErrorsByRule.setdefault(name, []).extend(entries)
            if not hits:
                genBatchLevel.setdefault(batch.strategyName, []).append(("error", batch.genError))

    generatedBatches = [b for b in batches if b.generated]
    buildReturnCode = None
    timedOut = False
    perRule, batchLevel = {}, {}
    if generatedBatches:
        print(f"Building engine: powershell -File scripts/build.ps1 -Config Release  (cwd={engineDir})")
        buildReturnCode, buildOutput, timedOut = runEngineBuild(engineDir, args.build_timeout)
        perRule, batchLevel = parseDiagnostics(buildOutput, generatedBatches)
    else:
        print("No batch generated successfully; skipping engine build.")

    if not args.keep:
        for batch in batches:
            cleanupBatch(batch, engineDir)
        if generatedBatches and engineDir:
            generatedDir = strategyWriter.generatedDirFor(dict(cfg, engineDir=engineDir))
            try:
                strategyWriter.rebuildIncFiles(generatedDir)
            except Exception as exc:
                print(f"WARNING: cleanup could not rebuild manifest/inc files: {exc}")

    # --- summary ---
    allRuleErrors = dict(genErrorsByRule)
    for name, entries in perRule.items():
        allRuleErrors.setdefault(name, []).extend(entries)
    allBatchLevel = dict(genBatchLevel)
    for name, entries in batchLevel.items():
        allBatchLevel.setdefault(name, []).extend(entries)

    hasError = bool(skipped) or any(
        sev == "error" for entries in list(allRuleErrors.values()) + list(allBatchLevel.values())
        for sev, _ in entries
    ) or (buildReturnCode not in (None, 0))

    print()
    print("=== compileCheck summary ===")
    print(f"Rules checked: {totalRules}  Batches: {len(batches)}  "
          f"Build: {'not run' if buildReturnCode is None else ('TIMED OUT' if timedOut else ('OK' if buildReturnCode == 0 else f'FAILED (exit {buildReturnCode})'))}")
    if skipped:
        print(f"Skipped (could not load): {', '.join(n for n, _ in skipped)}")
    if not allRuleErrors and not allBatchLevel:
        print("No compiler errors or warnings attributed to checked rules.")
    for name in sorted(allRuleErrors):
        for sev, msg in allRuleErrors[name]:
            print(f"[{sev.upper()}] {name}: {msg}")
    for name in sorted(allBatchLevel):
        for sev, msg in allBatchLevel[name]:
            print(f"[{sev.upper()}] (batch {name}, not attributable to one rule): {msg}")

    return 1 if hasError else 0


if __name__ == "__main__":
    sys.exit(main())
