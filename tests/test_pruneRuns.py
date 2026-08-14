import json
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pruneRuns as pr
import runBatch as rb
import snapshotData as sd
from specWriter import specOutputDir
from strategyWriter import GenerationError
from tests.test_snapshotData import writeSymbol


def quiet(*_args, **_kwargs):
    pass


def writeUnit(runDir, symbol, timeframe, wfBytes=100):
    """A minimal engine unit dir: manifest + bins + wf_results."""
    unit = os.path.join(runDir, f"{symbol}_M{timeframe}")
    os.makedirs(unit, exist_ok=True)
    for name in ("manifest.json", f"{symbol}.equity.bin", f"{symbol}.trades.bin"):
        with open(os.path.join(unit, name), "wb") as f:
            f.write(b"x" * 10)
    with open(os.path.join(unit, pr.WF_RESULTS), "wb") as f:
        f.write(b"x" * wfBytes)
    return unit


def writeRunReport(runDir, candidates):
    with open(os.path.join(runDir, rb.REPORT_JSON), "w") as f:
        json.dump({"format_version": 1, "candidates": candidates}, f)


def candidate(symbol, timeframe, tradeable):
    return {"symbol": symbol, "timeframe_minutes": timeframe,
            "tradeable": tradeable, "rejected_by": "" if tradeable else "mc",
            "wf_results": f"{symbol}_M{timeframe}/wf_results.json"}


class PruneWfTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = {"engineDir": self.tmp.name}
        self.runs = os.path.join(self.tmp.name, rb.RUNS_SUBDIR)

    def makeFamily(self, stem="fam", versions=1, tradeableSymbols=()):
        reports = {}
        for v in range(1, versions + 1):
            runDir = os.path.join(self.runs, f"{stem}_v{v}")
            candidates = []
            for symbol in ("AD", "CL"):
                writeUnit(runDir, symbol, 60)
                candidates.append(candidate(symbol, 60, symbol in tradeableSymbols))
            writeRunReport(runDir, candidates)
            reports[f"{stem}_v{v}"] = {"candidates": candidates}
        aggDir = os.path.join(self.runs, stem)
        os.makedirs(aggDir, exist_ok=True)
        with open(os.path.join(aggDir, rb.REPORT_JSON), "w") as f:
            json.dump({"aggregated_by": rb.AGGREGATE_MARKER, "runs": reports}, f)
        return stem

    def wfExists(self, stem, version, symbol):
        return os.path.isfile(os.path.join(
            self.runs, f"{stem}_v{version}", f"{symbol}_M60", pr.WF_RESULTS))

    def testDryRunDeletesNothing(self):
        stem = self.makeFamily(tradeableSymbols=("AD",))
        files, size = pr.pruneWf(stem, self.cfg, delete=False, echo=quiet)
        self.assertEqual(files, 1)  # only CL is rejected
        self.assertEqual(size, 100)
        self.assertTrue(self.wfExists(stem, 1, "AD"))
        self.assertTrue(self.wfExists(stem, 1, "CL"))

    def testDeleteRemovesOnlyRejectedWf(self):
        stem = self.makeFamily(versions=2, tradeableSymbols=("AD",))
        files, _size = pr.pruneWf(stem, self.cfg, delete=True, echo=quiet)
        self.assertEqual(files, 2)  # CL in both versions
        for v in (1, 2):
            self.assertTrue(self.wfExists(stem, v, "AD"))
            self.assertFalse(self.wfExists(stem, v, "CL"))
            # the cache and verdicts a regeneration needs must survive
            unit = os.path.join(self.runs, f"{stem}_v{v}", "CL_M60")
            self.assertTrue(os.path.isfile(os.path.join(unit, "manifest.json")))
            self.assertTrue(os.path.isfile(os.path.join(unit, "CL.equity.bin")))
            self.assertTrue(os.path.isfile(
                os.path.join(self.runs, f"{stem}_v{v}", rb.REPORT_JSON)))

    def testRefusesWithoutAggregate(self):
        stem = self.makeFamily()
        os.remove(os.path.join(self.runs, stem, rb.REPORT_JSON))
        with self.assertRaises(GenerationError):
            pr.pruneWf(stem, self.cfg, delete=True, echo=quiet)

    def testRefusesForeignAggregate(self):
        """A report not written by runBatch (e.g. a real engine run named like
        the stem) must not count as the family aggregate."""
        stem = self.makeFamily()
        with open(os.path.join(self.runs, stem, rb.REPORT_JSON), "w") as f:
            json.dump({"format_version": 1, "candidates": []}, f)
        with self.assertRaises(GenerationError):
            pr.pruneWf(stem, self.cfg, delete=True, echo=quiet)

    def testSkipsIncompleteVersion(self):
        stem = self.makeFamily(versions=2)
        os.remove(os.path.join(self.runs, f"{stem}_v2", rb.REPORT_JSON))
        files, _size = pr.pruneWf(stem, self.cfg, delete=True, echo=quiet)
        self.assertEqual(files, 2)  # v1 only
        self.assertTrue(self.wfExists(stem, 2, "AD"))
        self.assertTrue(self.wfExists(stem, 2, "CL"))

    def testRefusesEscapingWfPath(self):
        stem = self.makeFamily()
        runDir = os.path.join(self.runs, f"{stem}_v1")
        bad = [candidate("AD", 60, False)]
        bad[0]["wf_results"] = "../escape/wf_results.json"
        writeRunReport(runDir, bad)
        outside = os.path.join(self.runs, "escape")
        os.makedirs(outside, exist_ok=True)
        with open(os.path.join(outside, pr.WF_RESULTS), "w") as f:
            f.write("x")
        pr.pruneWf(stem, self.cfg, delete=True, echo=quiet)
        self.assertTrue(os.path.isfile(os.path.join(outside, pr.WF_RESULTS)))

    def testRefusesNonWfFilename(self):
        stem = self.makeFamily()
        runDir = os.path.join(self.runs, f"{stem}_v1")
        bad = [candidate("AD", 60, False)]
        bad[0]["wf_results"] = "AD_M60/manifest.json"
        writeRunReport(runDir, bad)
        pr.pruneWf(stem, self.cfg, delete=True, echo=quiet)
        self.assertTrue(os.path.isfile(
            os.path.join(runDir, "AD_M60", "manifest.json")))

    def testMissingFamilyErrors(self):
        with self.assertRaises(GenerationError):
            pr.pruneWf("nope", self.cfg, echo=quiet)

    def testAlreadyPrunedIsIdempotent(self):
        stem = self.makeFamily()
        pr.pruneWf(stem, self.cfg, delete=True, echo=quiet)
        files, size = pr.pruneWf(stem, self.cfg, delete=True, echo=quiet)
        self.assertEqual((files, size), (0, 0))


AD_CHUNKS = [("M60/2021.btck", 60, 18628, 18992, 0x111, 0xAAA)]
AD_SOURCE_HASH = sd.fnv1aBytes(struct.pack("<Q", 0x111))  # combined, one chunk


def writeManifest(unitDir, symbol, sourceHash, sessionHash, version=4):
    manifest = {"format_version": version, "strategy": "T",
                "timeframe_minutes": 60,
                "first_day": "2021-01-01", "last_day": "2021-12-31",
                "engine_build": "msvc-test",
                "symbols": [{"symbol": symbol, "bars": 10,
                             "first_ts": 1, "last_ts": 2,
                             "equity_file": f"{symbol}.equity.bin",
                             "trades_file": f"{symbol}.trades.bin"}]}
    if sourceHash:
        manifest["symbols"][0]["source_hash"] = sourceHash
        manifest["symbols"][0]["session_hash"] = sessionHash
    with open(os.path.join(unitDir, "manifest.json"), "w") as f:
        json.dump(manifest, f)


class PruneUnitsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = {"engineDir": self.tmp.name}
        self.runs = os.path.join(self.tmp.name, rb.RUNS_SUBDIR)
        self.dataRoot = os.path.join(self.tmp.name, sd.DATA_SUBDIR)
        # A store whose fingerprint the run manifests reference, snapshotted
        # into an epoch — the precondition for any unit deletion.
        writeSymbol(self.dataRoot, "AD", AD_CHUNKS)
        self.epochId = sd.snapshot(["AD"], self.cfg, echo=quiet)

    def makeRun(self, stem="fam", adSourceHash=AD_SOURCE_HASH, adSession=0xAAA):
        runDir = os.path.join(self.runs, f"{stem}_v1")
        adUnit = writeUnit(runDir, "AD", 60)
        writeManifest(adUnit, "AD", adSourceHash, adSession)
        clUnit = writeUnit(runDir, "CL", 60)
        writeManifest(clUnit, "CL", 0x999, 0xBBB)
        writeRunReport(runDir, [candidate("AD", 60, False),
                                candidate("CL", 60, True)])
        aggDir = os.path.join(self.runs, stem)
        os.makedirs(aggDir, exist_ok=True)
        with open(os.path.join(aggDir, rb.REPORT_JSON), "w") as f:
            json.dump({"aggregated_by": rb.AGGREGATE_MARKER, "runs": {}}, f)
        return stem, runDir

    def testDeleteRemovesCoveredUnitAndWritesLedger(self):
        stem, runDir = self.makeRun()
        units, size = pr.pruneUnits(stem, self.cfg, delete=True, echo=quiet)
        self.assertEqual(units, 1)
        self.assertGreater(size, 0)
        self.assertFalse(os.path.isdir(os.path.join(runDir, "AD_M60")))
        self.assertTrue(os.path.isdir(os.path.join(runDir, "CL_M60")))  # tradeable
        ledger = pr.loadLedger(runDir)
        entry = ledger["units"]["AD_M60"]
        self.assertEqual(entry["source_hash"], AD_SOURCE_HASH)
        self.assertEqual(entry["epoch"], self.epochId)
        self.assertEqual(entry["engine_build"], "msvc-test")

    def testDryRunDeletesNothing(self):
        stem, runDir = self.makeRun()
        units, _size = pr.pruneUnits(stem, self.cfg, delete=False, echo=quiet)
        self.assertEqual(units, 1)
        self.assertTrue(os.path.isdir(os.path.join(runDir, "AD_M60")))
        self.assertFalse(os.path.isfile(os.path.join(runDir, pr.PRUNE_LEDGER)))

    def testLegacyManifestIsRefused(self):
        stem, runDir = self.makeRun(adSourceHash=0)
        units, _size = pr.pruneUnits(stem, self.cfg, delete=True, echo=quiet)
        self.assertEqual(units, 0)
        self.assertTrue(os.path.isdir(os.path.join(runDir, "AD_M60")))

    def testUnmatchedFingerprintIsRefused(self):
        # The manifest was computed from data no epoch archives.
        stem, runDir = self.makeRun(adSourceHash=0xDEAD)
        units, _size = pr.pruneUnits(stem, self.cfg, delete=True, echo=quiet)
        self.assertEqual(units, 0)
        self.assertTrue(os.path.isdir(os.path.join(runDir, "AD_M60")))

    def testRefusesWithoutAnyEpoch(self):
        os.remove(sd.registryPath(self.cfg))
        stem, _runDir = self.makeRun()
        with self.assertRaises(GenerationError):
            pr.pruneUnits(stem, self.cfg, delete=True, echo=quiet)


class RegenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = {"engineDir": self.tmp.name}
        self.runs = os.path.join(self.tmp.name, rb.RUNS_SUBDIR)
        self.dataRoot = os.path.join(self.tmp.name, sd.DATA_SUBDIR)
        writeSymbol(self.dataRoot, "AD", AD_CHUNKS)
        self.runDir = os.path.join(self.runs, "fam_v1")
        os.makedirs(self.runDir)
        pr.saveLedger(self.runDir, {"format": "pruneRuns-ledger-1", "units": {
            "AD_M60": {"symbol": "AD", "timeframe_minutes": 60,
                       "first_day": "2021-01-01", "last_day": "2021-12-31",
                       "source_hash": AD_SOURCE_HASH, "session_hash": 0xAAA,
                       "engine_build": "msvc-test", "epoch": "20260101-000000",
                       "pruned_utc": "2026-01-01 00:00:00"}}})
        specDir = specOutputDir(self.cfg)
        os.makedirs(specDir, exist_ok=True)
        with open(os.path.join(specDir, "fam_v1.json"), "w") as f:
            json.dump({"name": "fam_v1"}, f)
        binDir = os.path.join(self.tmp.name, os.path.dirname(rb.WALKFORWARD_EXE))
        os.makedirs(binDir, exist_ok=True)
        open(os.path.join(self.tmp.name, rb.WALKFORWARD_EXE), "w").close()
        self.calls = []

    def fakeEngine(self, cmd, cwd=None):
        self.calls.append((cmd, cwd))
        os.makedirs(os.path.join(self.runDir, "AD_M60"), exist_ok=True)

        class Proc:
            returncode = 0
        return Proc()

    def testRegenVerifiesRunsEngineAndClearsLedger(self):
        pr.regen("fam_v1", self.cfg, echo=quiet, runner=self.fakeEngine)
        self.assertEqual(len(self.calls), 1)
        self.assertIn("--spec", self.calls[0][0])
        # The unit came back, so its ledger entry (and the empty ledger) went.
        self.assertFalse(os.path.isfile(os.path.join(self.runDir, pr.PRUNE_LEDGER)))

    def testRegenRefusesOnDriftedStore(self):
        writeSymbol(self.dataRoot, "AD",
                    [("M60/2021.btck", 60, 18628, 18992, 0x666, 0xAAA)])
        with self.assertRaises(GenerationError) as ctx:
            pr.regen("fam_v1", self.cfg, echo=quiet, runner=self.fakeEngine)
        self.assertIn("20260101-000000", str(ctx.exception))  # names the epoch
        self.assertEqual(self.calls, [])  # the engine must not run on wrong data

    def testRegenNeedsTheSpec(self):
        os.remove(os.path.join(specOutputDir(self.cfg), "fam_v1.json"))
        with self.assertRaises(GenerationError):
            pr.regen("fam_v1", self.cfg, echo=quiet, runner=self.fakeEngine)


class StatusTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = {"engineDir": self.tmp.name}
        self.runs = os.path.join(self.tmp.name, rb.RUNS_SUBDIR)

    def testStatusListsFamilies(self):
        runDir = os.path.join(self.runs, "fam_v1")
        writeUnit(runDir, "AD", 60)
        writeRunReport(runDir, [candidate("AD", 60, False)])
        lines = []
        pr.status([], self.cfg, echo=lambda *a: lines.append(" ".join(map(str, a))))
        joined = "\n".join(lines)
        self.assertIn("fam", joined)
        self.assertIn("NO", joined)  # no aggregate yet

    def testFamilyStemsFoldVersions(self):
        for name in ("fam_v1", "fam_v2", "other"):
            os.makedirs(os.path.join(self.runs, name))
        self.assertEqual(pr.familyStems(self.runs), ["fam", "other"])


class MainTest(unittest.TestCase):
    def testRequiresExactlyOneMode(self):
        with self.assertRaises(SystemExit):
            pr.main([])
        with self.assertRaises(SystemExit):
            pr.main(["--status", "--prune-wf", "fam"])

    def testPruneWfNeedsFamily(self):
        with self.assertRaises(SystemExit):
            pr.main(["--prune-wf"])


if __name__ == "__main__":
    unittest.main()
