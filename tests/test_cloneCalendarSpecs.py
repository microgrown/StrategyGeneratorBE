import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cloneCalendarSpecs as ccs
from strategyWriter import GenerationError

SIX = [{"is_days": 756, "oos_days": 504}, {"is_days": 756, "oos_days": 252},
       {"is_days": 756, "oos_days": 126}, {"is_days": 504, "oos_days": 252},
       {"is_days": 504, "oos_days": 126}, {"is_days": 252, "oos_days": 126}]

SIX_CALENDAR = [{"is": "3Y", "oos": "2Y"}, {"is": "3Y", "oos": "1Y"},
                {"is": "3Y", "oos": "6M"}, {"is": "2Y", "oos": "1Y"},
                {"is": "2Y", "oos": "6M"}, {"is": "1Y", "oos": "6M"}]


def spec(stem, version, schedules=None):
    """A generated spec in the generator's key order."""
    return {
        "name": f"{stem}_v{version}",
        "strategy": f"202608 BAS-13 V{version}",
        "symbols": ["AD", "GC"],
        "timeframes": [60, 1440],
        "wf_start": "2007-01-01",
        "wf_end": "2025-05-01",
        "incubation_end": "2026-02-01",
        "schedules": schedules if schedules is not None else [dict(s) for s in SIX],
        "criterion": "NetProfitOverAvgDD",
        "max_bars_back": 250,
        "selection": {"filters": [{"type": "most_average"}]},
    }


class TestCalendarSpec(unittest.TestCase):
    def testMapsTheSixStandardSchedulesAndInsertsTheAlignment(self):
        out = ccs.calendarSpec(spec("s_202608_bas_13", 7), "s_202608_bas_13", 7)
        self.assertEqual(out["name"], "s_202608_bas_13_cal_v7")
        self.assertEqual(out["schedules"], SIX_CALENDAR)
        self.assertEqual(out["calendar_alignment"], "month_start")
        keys = list(out)
        self.assertEqual(keys.index("calendar_alignment"), keys.index("schedules") + 1)
        self.assertEqual(keys, ["name", "strategy", "symbols", "timeframes", "wf_start",
                                "wf_end", "incubation_end", "schedules", "calendar_alignment",
                                "criterion", "max_bars_back", "selection"])

    def testEverythingElseIsUntouched(self):
        original = spec("s_202608_bas_13", 7)
        out = ccs.calendarSpec(original, "s_202608_bas_13", 7)
        for key in original:
            if key not in ("name", "schedules"):
                self.assertEqual(out[key], original[key], key)
        self.assertEqual(out["strategy"], "202608 BAS-13 V7")  # the compiled registry key
        self.assertEqual(original["schedules"], SIX)  # input not mutated

    def testSuffixAndAlignmentAreParameters(self):
        out = ccs.calendarSpec(spec("s_x", 1), "s_x", 1, suffix="_c", alignment="none")
        self.assertEqual(out["name"], "s_x_c_v1")
        self.assertEqual(out["calendar_alignment"], "none")
        with self.assertRaises(GenerationError):
            ccs.calendarSpec(spec("s_x", 1), "s_x", 1, alignment="quarter_start")

    def testUnknownLengthIsAnErrorNotAGuess(self):
        bad = spec("s_x", 2, [{"is_days": 252, "oos_days": 63}])
        with self.assertRaises(GenerationError) as ctx:
            ccs.calendarSpec(bad, "s_x", 2)
        self.assertIn("63", str(ctx.exception))
        self.assertIn("s_x_v2", str(ctx.exception))

    def testAlreadyCalendarEntryIsAnError(self):
        bad = spec("s_x", 1, [{"is": "1Y", "oos": "6M"}])
        with self.assertRaises(GenerationError):
            ccs.calendarSpec(bad, "s_x", 1)
        withAlignment = spec("s_x", 1)
        withAlignment["calendar_alignment"] = "none"
        with self.assertRaises(GenerationError):
            ccs.calendarSpec(withAlignment, "s_x", 1)

    def testNameMustMatchStemAndVersion(self):
        with self.assertRaises(GenerationError):
            ccs.calendarSpec(spec("s_x", 1), "s_x", 2)
        with self.assertRaises(GenerationError):
            ccs.calendarSpec(spec("s_y", 1), "s_x", 1)


class TestDiscoverFamilies(unittest.TestCase):
    def testPicksTheGeneratedBasFamiliesOnly(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ["s_202608_bas_13_v1", "s_202608_bas_13_v2", "s_202606_bas_1_v1",
                         "s_202608_bas_13_cal_v1", "s_202608_bas_1__rerun_v1",
                         "validation_202607_bas_2_v1", "quicktest_v1", "speedup_validation_v1",
                         "bas2_v4_kw_check", "s_202608_bas_3_v7"]:
                open(os.path.join(d, name + ".json"), "w").close()
            self.assertEqual(ccs.discoverFamilies(d), ["s_202606_bas_1", "s_202608_bas_13"])


class TestCloneFamilies(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engineDir = self.tmp.name
        self.specDir = os.path.join(self.engineDir, "specs", "generated")
        os.makedirs(self.specDir)
        self.cfg = {"engineDir": self.engineDir}
        self.lines = []

    def tearDown(self):
        self.tmp.cleanup()

    def writeFamily(self, stem, versions, schedules=None):
        for v in range(1, versions + 1):
            with open(os.path.join(self.specDir, f"{stem}_v{v}.json"), "w") as f:
                json.dump(spec(stem, v, schedules), f, indent=2)
                f.write("\n")

    def clonePath(self, stem, v):
        return os.path.join(self.specDir, f"{stem}_cal_v{v}.json")

    def clone(self, stems, **kw):
        return ccs.cloneFamilies(stems, self.cfg, echo=self.lines.append, **kw)

    def testWritesEveryVersionAndIsIdempotent(self):
        self.writeFamily("s_202608_bas_13", 3)
        results = self.clone(["s_202608_bas_13"])
        self.assertEqual(results, {"s_202608_bas_13": (3, 0)})
        self.assertEqual(self.lines, ["s_202608_bas_13 -> s_202608_bas_13_cal: 3 written, 0 existing"])
        for v in (1, 2, 3):
            with open(self.clonePath("s_202608_bas_13", v), encoding="utf-8") as f:
                text = f.read()
            self.assertTrue(text.endswith("\n"))
            self.assertEqual(json.loads(text),
                             ccs.calendarSpec(spec("s_202608_bas_13", v), "s_202608_bas_13", v))
        # originals untouched
        with open(os.path.join(self.specDir, "s_202608_bas_13_v2.json")) as f:
            self.assertEqual(json.load(f), spec("s_202608_bas_13", 2))

        mtimes = [os.path.getmtime(self.clonePath("s_202608_bas_13", v)) for v in (1, 2, 3)]
        self.lines.clear()
        self.assertEqual(self.clone(["s_202608_bas_13"]), {"s_202608_bas_13": (0, 3)})
        self.assertEqual(self.lines, ["s_202608_bas_13 -> s_202608_bas_13_cal: 0 written, 3 existing"])
        self.assertEqual(mtimes,
                         [os.path.getmtime(self.clonePath("s_202608_bas_13", v)) for v in (1, 2, 3)])

    def testDryRunWritesNothing(self):
        self.writeFamily("s_202608_bas_13", 2)
        self.assertEqual(self.clone(["s_202608_bas_13"], dryRun=True), {"s_202608_bas_13": (2, 0)})
        self.assertEqual(self.lines, ["s_202608_bas_13 -> s_202608_bas_13_cal: 2 would write, 0 existing"])
        self.assertFalse(os.path.exists(self.clonePath("s_202608_bas_13", 1)))

    def testADifferingCloneNeedsForce(self):
        self.writeFamily("s_202608_bas_13", 2)
        self.clone(["s_202608_bas_13"])
        edited = self.clonePath("s_202608_bas_13", 2)
        with open(edited, "w") as f:
            json.dump({"name": "s_202608_bas_13_cal_v2", "edited": True}, f)
        with self.assertRaises(GenerationError) as ctx:
            self.clone(["s_202608_bas_13"])
        self.assertIn("s_202608_bas_13_cal_v2.json", str(ctx.exception))
        with open(edited) as f:
            self.assertEqual(json.load(f)["edited"], True)  # nothing written

        # --force rewrites it, and warns when a run already sits on the old spec
        runDir = os.path.join(self.engineDir, "runs", "s_202608_bas_13_cal_v2")
        os.makedirs(runDir)
        open(os.path.join(runDir, "selection_report.json"), "w").close()
        self.lines.clear()
        self.assertEqual(self.clone(["s_202608_bas_13"], force=True), {"s_202608_bas_13": (1, 1)})
        self.assertTrue(any(l.startswith("Warning: s_202608_bas_13_cal_v2") for l in self.lines))
        with open(edited) as f:
            self.assertEqual(json.load(f)["schedules"], SIX_CALENDAR)

    def testABadSpecAnywhereAbortsBeforeAnythingIsWritten(self):
        self.writeFamily("s_202606_bas_1", 2)
        self.writeFamily("s_202608_bas_13", 3)
        with open(os.path.join(self.specDir, "s_202608_bas_13_v2.json"), "w") as f:
            json.dump(spec("s_202608_bas_13", 2, [{"is_days": 63, "oos_days": 21}]), f)
        with self.assertRaises(GenerationError) as ctx:
            self.clone(["s_202606_bas_1", "s_202608_bas_13"])
        self.assertIn("63", str(ctx.exception))
        self.assertEqual([n for n in os.listdir(self.specDir) if "_cal_" in n], [])

    def testUnknownFamilyIsAnError(self):
        with self.assertRaises(GenerationError):
            self.clone(["s_202608_bas_99"])

    def testListPrintsOnlyTheClonesThatExist(self):
        import io
        from contextlib import redirect_stdout
        self.writeFamily("s_202608_bas_13", 2)
        self.writeFamily("s_202606_bas_1", 1)
        self.clone(["s_202608_bas_13"])
        self.assertEqual(ccs.cloneStems(["s_202606_bas_1", "s_202608_bas_13"], self.cfg),
                         ["s_202608_bas_13_cal"])
        out = io.StringIO()
        with redirect_stdout(out):
            rc = ccs.main(["--engine-dir", self.engineDir, "--list"])
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue(), "s_202608_bas_13_cal\n")
        self.clone(["s_202606_bas_1"])
        out = io.StringIO()
        with redirect_stdout(out):
            ccs.main(["--engine-dir", self.engineDir, "--list"])
        self.assertEqual(out.getvalue().split(), ["s_202606_bas_1_cal", "s_202608_bas_13_cal"])

    def testMainAcceptsTheFamilyNameFormAndDiscoversByDefault(self):
        self.writeFamily("s_202608_bas_13", 1)
        self.writeFamily("s_202606_bas_1", 1)
        self.writeFamily("quicktest", 1)
        rc = ccs.main(["202608 BAS-13", "--engine-dir", self.engineDir, "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(self.clonePath("s_202608_bas_13", 1)))
        rc = ccs.main(["--engine-dir", self.engineDir])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(self.clonePath("s_202608_bas_13", 1)))
        self.assertTrue(os.path.exists(self.clonePath("s_202606_bas_1", 1)))
        self.assertFalse(os.path.exists(self.clonePath("quicktest", 1)))
        self.assertEqual(ccs.main(["--engine-dir", self.engineDir, "--suffix", ""]), 2)


if __name__ == "__main__":
    unittest.main()
