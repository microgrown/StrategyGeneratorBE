import csv
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import runBatch as rb
from strategyWriter import GenerationError


def touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").close()


def writeSpec(specDir, stem, version, selection=True):
    spec = {"name": f"{stem}_v{version}", "strategy": f"Test V{version}"}
    if selection:
        spec["selection"] = {"filters": [{"type": "most_average"}]}
    path = os.path.join(specDir, f"{stem}_v{version}.json")
    with open(path, "w") as f:
        json.dump(spec, f)
    return path


DEFAULT_HEADER = ["symbol", "timeframe_minutes", "most_average", "tradeable", "rejected_by"]


def defaultRow(**overrides):
    row = {"symbol": "AD", "timeframe_minutes": "67", "most_average": "pass",
           "tradeable": "true", "rejected_by": ""}
    row.update(overrides)
    return row


def writeSelection(runDir, header=None, rows=None, report=None):
    """Fabricate what the engine leaves at a run root after selection."""
    os.makedirs(runDir, exist_ok=True)
    header = header or DEFAULT_HEADER
    rows = rows if rows is not None else [defaultRow()]
    with open(os.path.join(runDir, rb.SUMMARY_CSV), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, restval="")
        writer.writeheader()
        writer.writerows(rows)
    if report is None:
        report = {"format_version": 1,
                  "candidates": [{"symbol": "AD", "tradeable": True}],
                  "tradeable": [{"schedule": "252-126"}]}
    with open(os.path.join(runDir, rb.REPORT_JSON), "w") as f:
        json.dump(report, f)
    return report


class FakeProc:
    def __init__(self, returncode):
        self.returncode = returncode


class FakeRunner:
    """Records (cmd, cwd) per call; sideEffect(specPath) can fabricate the run
    dir the engine would have written."""

    def __init__(self, returnCodes=None, sideEffect=None):
        self.calls = []
        self.returnCodes = returnCodes or {}
        self.sideEffect = sideEffect

    def __call__(self, cmd, cwd=None):
        self.calls.append((cmd, cwd))
        specPath = cmd[cmd.index("--spec") + 1]
        if self.sideEffect:
            self.sideEffect(specPath)
        runName = os.path.basename(specPath)[:-len(".json")]
        return FakeProc(self.returnCodes.get(runName, 0))


def quiet(*_args, **_kwargs):
    pass


class BatchCase(unittest.TestCase):
    STEM = "momentum_clone"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.engineDir = self._tmp.name
        self.specDir = os.path.join(self.engineDir, "specs", "generated")
        os.makedirs(self.specDir)
        self.binary = os.path.join(self.engineDir, rb.WALKFORWARD_EXE)
        touch(self.binary)
        self.cfg = {"engineDir": self.engineDir}

    def runDirFor(self, version):
        return os.path.join(self.engineDir, "runs", f"{self.STEM}_v{version}")

    def engineSideEffect(self, specPath):
        runName = os.path.basename(specPath)[:-len(".json")]
        writeSelection(os.path.join(self.engineDir, "runs", runName))


class TestResolveStem(unittest.TestCase):
    def test_foldsStrategyName(self):
        self.assertEqual(rb.resolveStem("Momentum Clone"), "momentum_clone")

    def test_idempotentOnStem(self):
        self.assertEqual(rb.resolveStem("momentum_clone"), "momentum_clone")

    def test_digitLeadingGetsPrefix(self):
        self.assertEqual(rb.resolveStem("2Fast"), "s_2fast")

    def test_keywordRaises(self):
        with self.assertRaises(GenerationError):
            rb.resolveStem("class")


class TestDiscoverSpecs(BatchCase):
    def test_findsVersionsInOrder(self):
        paths = [writeSpec(self.specDir, self.STEM, n) for n in (1, 2, 3)]
        self.assertEqual(
            rb.discoverSpecs(self.STEM, self.cfg),
            [(1, paths[0]), (2, paths[1]), (3, paths[2])],
        )

    def test_stopsAtFirstGap(self):
        writeSpec(self.specDir, self.STEM, 1)
        writeSpec(self.specDir, self.STEM, 3)
        versions = [v for v, _ in rb.discoverSpecs(self.STEM, self.cfg)]
        self.assertEqual(versions, [1])

    def test_emptyDir(self):
        self.assertEqual(rb.discoverSpecs(self.STEM, self.cfg), [])

    def test_honorsSpecOutputSubdir(self):
        other = os.path.join(self.engineDir, "sg")
        os.makedirs(other)
        writeSpec(other, self.STEM, 1)
        cfg = dict(self.cfg, specOutputSubdir="sg")
        self.assertEqual(len(rb.discoverSpecs(self.STEM, cfg)), 1)

    def test_blankEngineDirRaises(self):
        with self.assertRaises(GenerationError):
            rb.discoverSpecs(self.STEM, {"engineDir": " "})


class TestRunSpecs(BatchCase):
    def test_commandShapeAndCwd(self):
        specs = [(1, writeSpec(self.specDir, self.STEM, 1))]
        runner = FakeRunner()
        rb.runSpecs(specs, self.STEM, self.cfg, 7, False, runner, quiet)
        (cmd, cwd), = runner.calls
        self.assertEqual(cmd, [self.binary, "--spec", specs[0][1], "--threads", "7",
                               "--quiet"])
        self.assertEqual(cwd, self.engineDir)

    def test_verboseDropsQuiet(self):
        """The engine's own progress is one --verbose away when a run needs
        watching; its run.log carries it either way."""
        specs = [(1, writeSpec(self.specDir, self.STEM, 1))]
        runner = FakeRunner()
        rb.runSpecs(specs, self.STEM, self.cfg, 0, False, runner, quiet, verbose=True)
        (cmd, _), = runner.calls
        self.assertNotIn("--quiet", cmd)

    def test_oneLinePerVersionCarryingTheOutcome(self):
        specs = [(n, writeSpec(self.specDir, self.STEM, n)) for n in (1, 2)]
        runner = FakeRunner(returnCodes={f"{self.STEM}_v1": 2})
        echoed = []

        def record(*args, end="\n"):
            echoed.append((" ".join(str(a) for a in args), end))

        rb.runSpecs(specs, self.STEM, self.cfg, 0, False, runner, record)
        # Two versions: each opens a line and closes it with its outcome.
        self.assertEqual([end for _, end in echoed], ["", "\n", "", "\n"])
        self.assertIn(f"{self.STEM}_v1", echoed[0][0])
        self.assertIn("FAILED (exit 2)", echoed[1][0])
        self.assertIn(f"{self.STEM}_v2", echoed[2][0])
        self.assertTrue(echoed[3][0].startswith("OK "))

    def test_skipsVersionsWithSelectionOutput(self):
        specs = [(n, writeSpec(self.specDir, self.STEM, n)) for n in (1, 2)]
        writeSelection(self.runDirFor(1))
        runner = FakeRunner()
        outcomes = rb.runSpecs(specs, self.STEM, self.cfg, 0, False, runner, quiet)
        self.assertEqual(len(runner.calls), 1)
        self.assertIn(f"{self.STEM}_v2", runner.calls[0][0][2])
        self.assertTrue(outcomes[0].skipped)
        self.assertTrue(outcomes[0].ok)
        self.assertFalse(outcomes[1].skipped)

    def test_forceRunsEverything(self):
        specs = [(n, writeSpec(self.specDir, self.STEM, n)) for n in (1, 2)]
        writeSelection(self.runDirFor(1))
        runner = FakeRunner()
        outcomes = rb.runSpecs(specs, self.STEM, self.cfg, 0, True, runner, quiet)
        self.assertEqual(len(runner.calls), 2)
        self.assertFalse(any(o.skipped for o in outcomes))

    def test_runDirWithoutSelectionStillRuns(self):
        specs = [(1, writeSpec(self.specDir, self.STEM, 1))]
        os.makedirs(self.runDirFor(1))  # engine ran before, but no selection block
        runner = FakeRunner()
        rb.runSpecs(specs, self.STEM, self.cfg, 0, False, runner, quiet)
        self.assertEqual(len(runner.calls), 1)

    def test_continuesPastFailure(self):
        specs = [(n, writeSpec(self.specDir, self.STEM, n)) for n in (1, 2)]
        runner = FakeRunner(returnCodes={f"{self.STEM}_v1": 2})
        outcomes = rb.runSpecs(specs, self.STEM, self.cfg, 0, False, runner, quiet)
        self.assertEqual(len(runner.calls), 2)
        self.assertEqual([o.returnCode for o in outcomes], [2, 0])

    def test_fullyCachedBatchNeedsNoBinary(self):
        os.remove(self.binary)
        specs = [(1, writeSpec(self.specDir, self.STEM, 1))]
        writeSelection(self.runDirFor(1))
        runner = FakeRunner()
        outcomes = rb.runSpecs(specs, self.STEM, self.cfg, 0, False, runner, quiet)
        self.assertEqual(runner.calls, [])
        self.assertTrue(outcomes[0].skipped)

    def test_missingBinaryRaisesWithBuildHint(self):
        os.remove(self.binary)
        specs = [(1, writeSpec(self.specDir, self.STEM, 1))]
        with self.assertRaises(GenerationError) as ctx:
            rb.runSpecs(specs, self.STEM, self.cfg, 0, False, FakeRunner(), quiet)
        self.assertIn("build.ps1", str(ctx.exception))


class TestMergeSummaryRows(unittest.TestCase):
    def test_identicalHeaders(self):
        perRun = [
            ("a_v1", ["x", "y"], [{"x": "1", "y": "2"}]),
            ("a_v2", ["x", "y"], [{"x": "3", "y": "4"}]),
        ]
        header, rows, divergent = rb.mergeSummaryRows(perRun)
        self.assertEqual(header, ["run", "x", "y"])
        self.assertEqual(rows, [{"run": "a_v1", "x": "1", "y": "2"},
                                {"run": "a_v2", "x": "3", "y": "4"}])
        self.assertEqual(divergent, [])

    def test_divergentHeadersUnion(self):
        perRun = [
            ("a_v1", ["x"], [{"x": "1"}]),
            ("a_v2", ["x", "extra"], [{"x": "2", "extra": "e"}]),
        ]
        header, rows, divergent = rb.mergeSummaryRows(perRun)
        self.assertEqual(header, ["run", "x", "extra"])
        self.assertEqual(divergent, ["a_v2"])
        self.assertNotIn("extra", rows[0])  # DictWriter restval fills the blank

    def test_deterministic(self):
        perRun = [("a_v1", ["x"], [{"x": "1"}])]
        self.assertEqual(rb.mergeSummaryRows(perRun), rb.mergeSummaryRows(perRun))


class TestBuildAggregateReport(unittest.TestCase):
    def test_shape(self):
        reports = {"a_v1": {"format_version": 1, "candidates": []},
                   "a_v2": {"format_version": 1, "candidates": [{"tradeable": True}]}}
        agg = rb.buildAggregateReport("a", reports)
        self.assertEqual(agg["aggregated_by"], rb.AGGREGATE_MARKER)
        self.assertEqual(agg["format"], rb.AGGREGATE_FORMAT)
        self.assertEqual(agg["stem"], "a")
        self.assertEqual(list(agg["runs"]), ["a_v1", "a_v2"])
        self.assertEqual(agg["runs"]["a_v2"], reports["a_v2"])  # verbatim

    def test_noTopLevelFormatVersion(self):
        # The engine GUI's report reader requires format_version/candidates at
        # top level; their absence makes it reject the aggregate cleanly
        # instead of half-parsing runs/<stem>/ as a run (run_browser.cpp).
        agg = rb.buildAggregateReport("a", {"a_v1": {"format_version": 1}})
        self.assertNotIn("format_version", agg)
        self.assertNotIn("candidates", agg)


class TestWriteAggregate(BatchCase):
    def outcomes(self, versions):
        return [rb.RunOutcome(v, "spec", self.runDirFor(v)) for v in versions]

    def aggDir(self):
        return os.path.join(self.engineDir, "runs", self.STEM)

    def test_writesBothFiles(self):
        writeSelection(self.runDirFor(1))
        writeSelection(self.runDirFor(2), rows=[defaultRow(tradeable="false",
                                                           rejected_by="most_average")])
        warnings = []
        aggDir, names, reports = rb.writeAggregate(
            self.STEM, self.outcomes([1, 2]), self.cfg, warnings)
        self.assertEqual(aggDir, self.aggDir())
        self.assertEqual(names, [f"{self.STEM}_v1", f"{self.STEM}_v2"])
        self.assertEqual(warnings, [])
        with open(os.path.join(aggDir, rb.SUMMARY_CSV), newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["run"], f"{self.STEM}_v1")
        self.assertEqual(rows[1]["tradeable"], "false")
        with open(os.path.join(aggDir, rb.REPORT_JSON)) as f:
            text = f.read()
        self.assertTrue(text.endswith("\n"))
        agg = json.loads(text)
        self.assertEqual(set(agg["runs"]), set(names))
        self.assertEqual(reports[f"{self.STEM}_v1"], agg["runs"][f"{self.STEM}_v1"])

    def test_overwriteIsIdempotent(self):
        writeSelection(self.runDirFor(1))
        rb.writeAggregate(self.STEM, self.outcomes([1]), self.cfg, [])
        writeSelection(self.runDirFor(1), report={"format_version": 1,
                                                  "candidates": [], "changed": True})
        rb.writeAggregate(self.STEM, self.outcomes([1]), self.cfg, [])
        with open(os.path.join(self.aggDir(), rb.REPORT_JSON)) as f:
            agg = json.load(f)
        self.assertTrue(agg["runs"][f"{self.STEM}_v1"]["changed"])

    def test_refusesRealRunDirWithLog(self):
        writeSelection(self.runDirFor(1))
        touch(os.path.join(self.aggDir(), rb.RUN_LOG))
        with self.assertRaises(GenerationError):
            rb.writeAggregate(self.STEM, self.outcomes([1]), self.cfg, [])

    def test_refusesRealRunDirWithResults(self):
        writeSelection(self.runDirFor(1))
        touch(os.path.join(self.aggDir(), "AD_M67", "wf_results.json"))
        with self.assertRaises(GenerationError):
            rb.writeAggregate(self.STEM, self.outcomes([1]), self.cfg, [])

    def test_refusesForeignReport(self):
        writeSelection(self.runDirFor(1))
        os.makedirs(self.aggDir())
        with open(os.path.join(self.aggDir(), rb.REPORT_JSON), "w") as f:
            json.dump({"format_version": 1, "candidates": []}, f)
        with self.assertRaises(GenerationError):
            rb.writeAggregate(self.STEM, self.outcomes([1]), self.cfg, [])

    def test_skipsVersionsWithoutSelection(self):
        writeSelection(self.runDirFor(2))
        warnings = []
        _, names, _ = rb.writeAggregate(
            self.STEM, self.outcomes([1, 2]), self.cfg, warnings)
        self.assertEqual(names, [f"{self.STEM}_v2"])

    def test_nothingToAggregate(self):
        warnings = []
        aggDir, names, reports = rb.writeAggregate(
            self.STEM, self.outcomes([1]), self.cfg, warnings)
        self.assertEqual((aggDir, names, reports), ("", [], {}))
        self.assertFalse(os.path.exists(self.aggDir()))
        self.assertTrue(any("No selection results" in w for w in warnings))


class TestRunBatch(BatchCase):
    def test_endToEnd(self):
        for n in (1, 2):
            writeSpec(self.specDir, self.STEM, n)
        runner = FakeRunner(sideEffect=self.engineSideEffect)
        result = rb.runBatch("Momentum Clone", self.cfg, runner=runner, echo=quiet)
        self.assertEqual(result.stem, self.STEM)
        self.assertEqual(len(runner.calls), 2)
        self.assertEqual(result.aggregatedVersions,
                         [f"{self.STEM}_v1", f"{self.STEM}_v2"])
        self.assertEqual(result.failed, [])
        self.assertTrue(os.path.isfile(
            os.path.join(result.aggregateDir, rb.SUMMARY_CSV)))
        self.assertIn(f"{self.STEM}_v1", result.reports)

    def test_secondInvocationNeverTouchesEngine(self):
        for n in (1, 2):
            writeSpec(self.specDir, self.STEM, n)
        rb.runBatch(self.STEM, self.cfg,
                    runner=FakeRunner(sideEffect=self.engineSideEffect), echo=quiet)
        runner = FakeRunner()
        result = rb.runBatch(self.STEM, self.cfg, runner=runner, echo=quiet)
        self.assertEqual(runner.calls, [])
        self.assertTrue(all(o.skipped for o in result.outcomes))
        self.assertEqual(len(result.aggregatedVersions), 2)

    def test_zeroSpecsRaises(self):
        with self.assertRaises(GenerationError) as ctx:
            rb.runBatch("no_such_thing", self.cfg, runner=FakeRunner(), echo=quiet)
        self.assertIn("Make Strategy", str(ctx.exception))

    def test_versionSuffixInputGetsHint(self):
        writeSpec(self.specDir, self.STEM, 1)
        with self.assertRaises(GenerationError) as ctx:
            rb.runBatch(f"{self.STEM}_v1", self.cfg, runner=FakeRunner(), echo=quiet)
        self.assertIn(f"Did you mean '{self.STEM}'", str(ctx.exception))

    def test_noSelectionBlockWarns(self):
        writeSpec(self.specDir, self.STEM, 1, selection=False)
        result = rb.runBatch(self.STEM, self.cfg, runner=FakeRunner(), echo=quiet)
        self.assertTrue(any("selection" in w for w in result.warnings))
        self.assertEqual(result.aggregateDir, "")


class TestFormatSummary(BatchCase):
    def test_statusAndCounts(self):
        outcomes = [
            rb.RunOutcome(1, "s1", self.runDirFor(1)),
            rb.RunOutcome(2, "s2", self.runDirFor(2), skipped=True),
            rb.RunOutcome(3, "s3", self.runDirFor(3), returnCode=2),
        ]
        reports = {
            f"{self.STEM}_v1": {"candidates": [{"tradeable": True},
                                               {"tradeable": False}]},
            f"{self.STEM}_v2": {"candidates": [{"tradeable": False}]},
        }
        result = rb.BatchResult(self.STEM, outcomes,
                                os.path.join(self.engineDir, "runs", self.STEM),
                                list(reports), ["something odd"], reports)
        text = rb.formatSummary(result)
        self.assertIn("OK", text)
        self.assertIn("tradeable 1/2", text)
        self.assertIn("cached", text)
        self.assertIn("tradeable 0/1", text)
        self.assertIn("FAIL (exit 2)", text)
        self.assertIn("tradeable n/a", text)
        self.assertIn("rebuild the engine", text)
        self.assertIn(rb.SUMMARY_CSV, text)
        self.assertIn("Warning: something odd", text)


if __name__ == "__main__":
    unittest.main()
