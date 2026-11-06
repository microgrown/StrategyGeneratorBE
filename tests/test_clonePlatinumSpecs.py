import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import clonePlatinumSpecs as cps
from strategyWriter import GenerationError

SIX = [{"is_days": 756, "oos_days": 504}, {"is_days": 756, "oos_days": 252},
       {"is_days": 756, "oos_days": 126}, {"is_days": 504, "oos_days": 252},
       {"is_days": 504, "oos_days": 126}, {"is_days": 252, "oos_days": 126}]

STANDARD_CHAIN = [
    {"type": "most_average"},
    {"type": "legacy_mw_monte_carlo", "runs": 2500, "min": 0.75, "max": 1.5},
    {"type": "annual_net_profit", "min": 500.0},
    {"type": "scaled_avg_drawdown", "min_annual_net_profit": 5000.0,
     "max_annual_net_profit": 15000.0, "max": 3500.0},
    {"type": "scaled_max_drawdown", "min_annual_net_profit": 5000.0,
     "max_annual_net_profit": 15000.0, "max": 25000.0},
    {"type": "incubation_efficiency", "min_ratio": 0.0},
    {"type": "trade_count", "min_trades": 30},
]


def spec(stem, version, filters=None, symbols=None):
    """A generated spec in the generator's key order."""
    return {
        "name": f"{stem}_v{version}",
        "strategy": f"202608 BAS-13 V{version}",
        "symbols": symbols if symbols is not None else ["AD", "BTC", "ETH", "GC"],
        "timeframes": [60, 1440],
        "wf_start": "2007-01-01",
        "wf_end": "2025-05-01",
        "incubation_end": "2026-02-01",
        "schedules": [dict(s) for s in SIX],
        "criterion": "NetProfitOverAvgDD",
        "max_bars_back": 250,
        "selection": {"filters": [dict(f) for f in (filters or STANDARD_CHAIN)]},
    }


class TestPlatinumSpec(unittest.TestCase):
    def testRedatesRenamesAndInsertsOosEnd(self):
        out = cps.platinumSpec(spec("s_202608_bas_13", 7), "s_202608_bas_13", 7)
        self.assertEqual(out["name"], "s_202608_bas_13_platinum_validation_v7")
        self.assertEqual((out["wf_start"], out["wf_end"], out["incubation_end"], out["oos_end"]),
                         ("2007-01-01", "2019-04-01", "2020-01-01", "2023-01-01"))
        self.assertEqual(list(out), ["name", "strategy", "symbols", "timeframes", "wf_start",
                                     "wf_end", "incubation_end", "oos_end", "schedules",
                                     "criterion", "max_bars_back", "selection"])

    def testDropsCryptoAndKeepsTheRestInOrder(self):
        out = cps.platinumSpec(spec("s_x", 1), "s_x", 1)
        self.assertEqual(out["symbols"], ["AD", "GC"])

    def testEverythingElseIsUntouched(self):
        original = spec("s_202608_bas_13", 7)
        out = cps.platinumSpec(original, "s_202608_bas_13", 7)
        for key in ("strategy", "timeframes", "wf_start", "schedules", "criterion",
                    "max_bars_back"):
            self.assertEqual(out[key], original[key], key)
        self.assertEqual(original, spec("s_202608_bas_13", 7))  # input not mutated

    def testAppendsARecordOnlyMonteCarloOverAllSixCriteria(self):
        out = cps.platinumSpec(spec("s_x", 1), "s_x", 1)
        filters = out["selection"]["filters"]
        self.assertEqual(filters[:-1], STANDARD_CHAIN)
        mc = filters[-1]
        self.assertEqual(mc["type"], "monte_carlo")
        self.assertIs(mc["record_only"], True)
        self.assertEqual({c["criterion"] for c in mc["criteria"]},
                         {"NetProfit", "MaxDrawdown", "AvgDrawdown", "NetProfitOverMaxDD",
                          "NetProfitOverAvgDD", "ModifiedSharpe"})
        for c in mc["criteria"]:
            self.assertTrue("min" in c or "max" in c, c)  # the engine needs a bound

    def testAddsTradeCountWhereTheOlderFamiliesLackIt(self):
        out = cps.platinumSpec(spec("s_x", 1, filters=STANDARD_CHAIN[:-1]), "s_x", 1)
        types = [f["type"] for f in out["selection"]["filters"]]
        self.assertEqual(types[-2:], ["trade_count", "monte_carlo"])
        self.assertEqual(out["selection"]["filters"][-2], {"type": "trade_count", "min_trades": 30})

    def testAnExistingMonteCarloIsAnError(self):
        filters = STANDARD_CHAIN + [{"type": "monte_carlo", "criteria": []}]
        with self.assertRaises(GenerationError):
            cps.platinumSpec(spec("s_x", 1, filters=filters), "s_x", 1)

    def testChainMustStartWithMostAverage(self):
        with self.assertRaises(GenerationError):
            cps.platinumSpec(spec("s_x", 1, filters=STANDARD_CHAIN[1:]), "s_x", 1)

    def testOtherWfStartIsAnError(self):
        s = spec("s_x", 1)
        s["wf_start"] = "2010-01-01"
        with self.assertRaises(GenerationError):
            cps.platinumSpec(s, "s_x", 1)

    def testAlreadyOosEndIsAnError(self):
        s = spec("s_x", 1)
        s["oos_end"] = "2027-01-01"
        with self.assertRaises(GenerationError):
            cps.platinumSpec(s, "s_x", 1)

    def testOnlyCryptoSymbolsIsAnError(self):
        with self.assertRaises(GenerationError):
            cps.platinumSpec(spec("s_x", 1, symbols=["ETH", "BTC"]), "s_x", 1)

    def testNameMustMatchStemAndVersion(self):
        with self.assertRaises(GenerationError):
            cps.platinumSpec(spec("s_x", 2), "s_x", 1)


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

    def writeSpec(self, name, content):
        with open(os.path.join(self.specDir, f"{name}.json"), "w") as f:
            json.dump(content, f, indent=2)
            f.write("\n")

    def writeFamily(self, stem, versions):
        for v in range(1, versions + 1):
            self.writeSpec(f"{stem}_v{v}", spec(stem, v))

    def clonePath(self, stem, v):
        return os.path.join(self.specDir, f"{stem}_platinum_validation_v{v}.json")

    def clone(self, stems, **kw):
        return cps.cloneFamilies(stems, self.cfg, echo=self.lines.append, **kw)

    def testWritesEveryVersionAndIsIdempotent(self):
        self.writeFamily("s_202608_bas_13", 3)
        self.assertEqual(self.clone(["s_202608_bas_13"]), {"s_202608_bas_13": (3, 0)})
        for v in (1, 2, 3):
            with open(self.clonePath("s_202608_bas_13", v)) as f:
                self.assertEqual(json.load(f)["oos_end"], "2023-01-01")
        self.assertEqual(self.clone(["s_202608_bas_13"]), {"s_202608_bas_13": (0, 3)})

    def testDryRunWritesNothing(self):
        self.writeFamily("s_202608_bas_13", 2)
        self.clone(["s_202608_bas_13"], dryRun=True)
        self.assertFalse(os.path.exists(self.clonePath("s_202608_bas_13", 1)))

    def testADifferingCloneNeedsForce(self):
        self.writeFamily("s_202608_bas_13", 1)
        self.writeSpec("s_202608_bas_13_platinum_validation_v1", {"name": "stale"})
        with self.assertRaises(GenerationError):
            self.clone(["s_202608_bas_13"])
        self.assertEqual(self.clone(["s_202608_bas_13"], force=True), {"s_202608_bas_13": (1, 0)})

    def testABadSpecAnywhereAbortsBeforeAnythingIsWritten(self):
        self.writeFamily("s_202608_bas_1", 1)
        bad = spec("s_202608_bas_2", 1)
        bad["wf_start"] = "2012-01-01"
        self.writeSpec("s_202608_bas_2_v1", bad)
        with self.assertRaises(GenerationError):
            self.clone(["s_202608_bas_1", "s_202608_bas_2"])
        self.assertFalse(os.path.exists(self.clonePath("s_202608_bas_1", 1)))

    def testDefaultFamiliesSkipRetiredTwinsAndClones(self):
        for stem in ("s_202608_bas_1", "s_202608_bas_37", "s_202608_bas_1_cal",
                     "s_202608_bas_1_platinum_validation"):
            self.writeSpec(f"{stem}_v1", spec(stem, 1))
        self.assertEqual(cps.defaultFamilies(self.specDir), ["s_202608_bas_1"])

    def testDefaultFamiliesIncludeTheBrooksStudy(self):
        for stem in ("s_202608_bas_1", "s_202611_brk_07", "s_202611_brk_07_cal",
                     "s_202611_brk_07_platinum_validation", "s_202611_brkx_1"):
            self.writeSpec(f"{stem}_v1", spec(stem, 1))
        self.assertEqual(cps.defaultFamilies(self.specDir),
                         ["s_202608_bas_1", "s_202611_brk_07"])

    def testDefaultFamiliesIncludeTheOwnStudy(self):
        for stem in ("s_202611_brk_07", "s_202611_own_01", "s_202611_own_64",
                     "s_202611_own_01_platinum_validation", "s_202611_ownx_1"):
            self.writeSpec(f"{stem}_v1", spec(stem, 1))
        self.assertEqual(cps.defaultFamilies(self.specDir),
                         ["s_202611_brk_07", "s_202611_own_01", "s_202611_own_64"])

    def testKindAndRangeSelectDefaultFamilies(self):
        for stem in ("s_202608_bas_40", "s_202611_brk_40", "s_202611_own_01",
                     "s_202611_own_33", "s_202611_own_40", "s_202611_own_64"):
            self.writeSpec(f"{stem}_v1", spec(stem, 1))
        self.assertEqual(cps.defaultFamilies(self.specDir, "own"),
                         ["s_202611_own_01", "s_202611_own_33", "s_202611_own_40", "s_202611_own_64"])
        self.assertEqual(cps.defaultFamilies(self.specDir, "own", (33, 40)),
                         ["s_202611_own_33", "s_202611_own_40"])
        self.assertEqual(cps.defaultFamilies(self.specDir, None, (40, 40)),
                         ["s_202608_bas_40", "s_202611_brk_40", "s_202611_own_40"])

    def testParseRange(self):
        self.assertEqual(cps.parseRange("33-64"), (33, 64))
        self.assertEqual(cps.parseRange("7"), (7, 7))
        for bad in ("", "a-b", "9-3", "1-2-3"):
            with self.assertRaises(GenerationError):
                cps.parseRange(bad)

    def testRetiredFamilyStillClonesWhenNamed(self):
        self.writeFamily("s_202608_bas_37", 1)
        self.assertEqual(self.clone(["s_202608_bas_37"]), {"s_202608_bas_37": (1, 0)})

    def testListPrintsOnlyTheClonesThatExist(self):
        self.writeFamily("s_202608_bas_1", 1)
        self.writeFamily("s_202608_bas_2", 1)
        self.clone(["s_202608_bas_1"])
        self.assertEqual(cps.cloneStems(["s_202608_bas_1", "s_202608_bas_2"], self.cfg),
                         ["s_202608_bas_1_platinum_validation"])


if __name__ == "__main__":
    unittest.main()
