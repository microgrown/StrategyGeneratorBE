import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import specWriter as spw
from specWriter import DEFAULT_MAX_BARS_BACK, SpecResult
from strategyWriter import GenerationError

# The engine rejects any key outside this set (bt/wf/spec.cpp kKnownKeys), so a
# clone that grows a key would fail at load. This is the guard for that.
ENGINE_KNOWN_KEYS = {
    "name", "strategy", "symbols", "timeframes", "wf_start", "wf_end",
    "incubation_end", "schedules", "criterion", "max_bars_back", "selection",
}

TEMPLATE = {
    "name": "validation_momentum",
    "strategy": "MomentumReversal",
    "symbols": ["AD"],
    "timeframes": [67],
    "wf_start": "2021-07-22",
    "wf_end": "2026-07-21",
    "schedules": [{"is_days": 252, "oos_days": 126}],
    "criterion": "NetProfit",
    "max_bars_back": 100,
}


def readJson(path):
    with open(path) as f:
        return json.load(f)


class TestBuildSpec(unittest.TestCase):
    def testOnlyNameAndStrategyChange(self):
        spec = spw.buildSpec(TEMPLATE, "momentum_clone_v1", "Momentum Clone V1")
        self.assertEqual(spec["name"], "momentum_clone_v1")
        self.assertEqual(spec["strategy"], "Momentum Clone V1")
        for key, value in TEMPLATE.items():
            if key not in ("name", "strategy"):
                self.assertEqual(spec[key], value, key)

    def testNoKeysAreAddedOrDropped(self):
        spec = spw.buildSpec(TEMPLATE, "s", "S V1")
        self.assertEqual(set(spec), set(TEMPLATE))

    def testEmittedKeysAreAllKnownToTheEngine(self):
        spec = spw.buildSpec(TEMPLATE, "s", "S V1", override=200)
        self.assertEqual(set(spec) - ENGINE_KNOWN_KEYS, set())

    def testTemplateIsNotMutated(self):
        before = json.dumps(TEMPLATE, sort_keys=True)
        spw.buildSpec(TEMPLATE, "s", "S V1", override=999)
        self.assertEqual(json.dumps(TEMPLATE, sort_keys=True), before)

    def testKeyOrderIsPreserved(self):
        spec = spw.buildSpec(TEMPLATE, "s", "S V1")
        self.assertEqual(list(spec), list(TEMPLATE))

    def testOverrideReplacesMaxBarsBack(self):
        spec = spw.buildSpec(TEMPLATE, "s", "S V1", override=250)
        self.assertEqual(spec["max_bars_back"], 250)

    def testNoOverrideLeavesTheTemplateValue(self):
        spec = spw.buildSpec(TEMPLATE, "s", "S V1", override=None)
        self.assertEqual(spec["max_bars_back"], 100)

    def testOverrideAddsTheKeyWhenTheTemplateOmitsIt(self):
        template = {k: v for k, v in TEMPLATE.items() if k != "max_bars_back"}
        spec = spw.buildSpec(template, "s", "S V1", override=75)
        self.assertEqual(spec["max_bars_back"], 75)

    def testUnusualTemplateKeysStillPassThrough(self):
        template = dict(TEMPLATE, selection={"runs": 3}, incubation_end="2026-12-31")
        spec = spw.buildSpec(template, "s", "S V1")
        self.assertEqual(spec["selection"], {"runs": 3})
        self.assertEqual(spec["incubation_end"], "2026-12-31")


class TestParseMaxBarsBack(unittest.TestCase):
    def testBlankMeansNoOverride(self):
        for blank in ("", "   ", None):
            self.assertIsNone(spw.parseMaxBarsBack(blank))

    def testWholeNumberIsParsed(self):
        self.assertEqual(spw.parseMaxBarsBack("100"), 100)
        self.assertEqual(spw.parseMaxBarsBack(100), 100)
        self.assertEqual(spw.parseMaxBarsBack(" 250 "), 250)

    def testZeroIsAllowed(self):
        self.assertEqual(spw.parseMaxBarsBack("0"), 0)

    def testNonNumberIsRejected(self):
        with self.assertRaises(GenerationError):
            spw.parseMaxBarsBack("lots")

    def testDecimalIsRejected(self):
        # The engine's field is an int; "100.5" would silently truncate.
        with self.assertRaises(GenerationError):
            spw.parseMaxBarsBack("100.5")

    def testNegativeIsRejected(self):
        with self.assertRaises(GenerationError):
            spw.parseMaxBarsBack("-1")


class TestEffectiveMaxBarsBack(unittest.TestCase):
    def testOverrideWins(self):
        self.assertEqual(spw.effectiveMaxBarsBack(TEMPLATE, 250), 250)

    def testTemplateValueStandsWhenBlank(self):
        self.assertEqual(spw.effectiveMaxBarsBack(TEMPLATE, None), 100)

    def testEngineDefaultWhenNeitherIsSet(self):
        template = {k: v for k, v in TEMPLATE.items() if k != "max_bars_back"}
        self.assertEqual(
            spw.effectiveMaxBarsBack(template, None), DEFAULT_MAX_BARS_BACK
        )


class TestLoadTemplate(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def _write(self, text, name="template.json"):
        path = os.path.join(self.dir, name)
        with open(path, "w") as f:
            f.write(text)
        return path

    def testValidTemplateLoads(self):
        path = self._write(json.dumps(TEMPLATE))
        self.assertEqual(spw.loadTemplate(path), TEMPLATE)

    def testBlankPathIsRejected(self):
        with self.assertRaises(GenerationError):
            spw.loadTemplate("")

    def testMissingFileIsRejected(self):
        with self.assertRaises(GenerationError):
            spw.loadTemplate(os.path.join(self.dir, "nope.json"))

    def testMalformedJsonIsRejected(self):
        with self.assertRaises(GenerationError):
            spw.loadTemplate(self._write("{ not json"))

    def testNonObjectIsRejected(self):
        with self.assertRaises(GenerationError):
            spw.loadTemplate(self._write("[1, 2, 3]"))

    def testMissingStrategyIsRejected(self):
        template = {k: v for k, v in TEMPLATE.items() if k != "strategy"}
        with self.assertRaises(GenerationError) as cm:
            spw.loadTemplate(self._write(json.dumps(template)))
        self.assertIn("strategy", str(cm.exception))

    def testMissingBothNamesIsReportedTogether(self):
        template = {k: v for k, v in TEMPLATE.items() if k not in ("name", "strategy")}
        with self.assertRaises(GenerationError) as cm:
            spw.loadTemplate(self._write(json.dumps(template)))
        self.assertIn("name and strategy", str(cm.exception))


class TestWriteSpecs(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.engineDir = self._tmp.name
        self.addCleanup(self._tmp.cleanup)
        self.templatePath = os.path.join(self.engineDir, "validation_momentum.json")
        with open(self.templatePath, "w") as f:
            json.dump(TEMPLATE, f)
        self.cfg = {
            "engineDir": self.engineDir,
            "specTemplate": self.templatePath,
            "specOutputSubdir": "specs/generated",
            "maxBarsBack": "",
        }

    def outputDir(self):
        return os.path.join(self.engineDir, "specs", "generated")

    def testOneSpecPerVersion(self):
        result = spw.writeSpecs("Momentum Clone", 3, self.cfg)
        self.assertEqual(len(result.paths), 3)
        self.assertEqual(
            [os.path.basename(p) for p in result.paths],
            ["momentum_clone_v1.json", "momentum_clone_v2.json",
             "momentum_clone_v3.json"],
        )
        for path in result.paths:
            self.assertTrue(os.path.exists(path))

    def testSpecContentMatchesTheRegisteredStrategy(self):
        result = spw.writeSpecs("Momentum Clone", 2, self.cfg)
        first = readJson(result.paths[0])
        second = readJson(result.paths[1])
        self.assertEqual(first["name"], "momentum_clone_v1")
        self.assertEqual(first["strategy"], "Momentum Clone V1")
        self.assertEqual(second["name"], "momentum_clone_v2")
        self.assertEqual(second["strategy"], "Momentum Clone V2")

    def testWritesUnderTheConfiguredOutputDir(self):
        result = spw.writeSpecs("Momentum Clone", 1, self.cfg)
        self.assertEqual(result.outputDir, self.outputDir())

    def testDefaultOutputSubdirIsUsedWhenAbsent(self):
        cfg = dict(self.cfg)
        del cfg["specOutputSubdir"]
        result = spw.writeSpecs("Momentum Clone", 1, cfg)
        self.assertEqual(result.outputDir, self.outputDir())

    def testTemplateMaxBarsBackIsKeptWhenTheFieldIsBlank(self):
        result = spw.writeSpecs("Momentum Clone", 1, self.cfg)
        self.assertEqual(readJson(result.paths[0])["max_bars_back"], 100)
        self.assertEqual(result.maxBarsBack, 100)

    def testConfiguredMaxBarsBackOverridesTheTemplate(self):
        cfg = dict(self.cfg, maxBarsBack="250")
        result = spw.writeSpecs("Momentum Clone", 1, cfg)
        self.assertEqual(readJson(result.paths[0])["max_bars_back"], 250)
        self.assertEqual(result.maxBarsBack, 250)

    def testRegeneratingOverwritesInPlace(self):
        spw.writeSpecs("Momentum Clone", 1, self.cfg)
        result = spw.writeSpecs("Momentum Clone", 1, dict(self.cfg, maxBarsBack="300"))
        self.assertEqual(readJson(result.paths[0])["max_bars_back"], 300)

    def testShrinkingTheVersionCountPrunesStaleSpecs(self):
        wide = spw.writeSpecs("Momentum Clone", 3, self.cfg)
        narrow = spw.writeSpecs("Momentum Clone", 1, self.cfg)
        self.assertEqual(len(narrow.removed), 2)
        self.assertFalse(os.path.exists(wide.paths[1]))
        self.assertFalse(os.path.exists(wide.paths[2]))
        self.assertTrue(os.path.exists(narrow.paths[0]))

    def testPruningLeavesOtherStrategiesAlone(self):
        other = spw.writeSpecs("Other Strategy", 3, self.cfg)
        spw.writeSpecs("Momentum Clone", 1, self.cfg)
        for path in other.paths:
            self.assertTrue(os.path.exists(path), path)

    def testFileEndsWithANewline(self):
        result = spw.writeSpecs("Momentum Clone", 1, self.cfg)
        with open(result.paths[0]) as f:
            self.assertTrue(f.read().endswith("}\n"))

    def testBadTemplateStopsBeforeWritingAnything(self):
        cfg = dict(self.cfg, specTemplate=os.path.join(self.engineDir, "nope.json"))
        with self.assertRaises(GenerationError):
            spw.writeSpecs("Momentum Clone", 1, cfg)
        self.assertFalse(os.path.exists(self.outputDir()))

    def testBadMaxBarsBackStopsBeforeWritingAnything(self):
        with self.assertRaises(GenerationError):
            spw.writeSpecs("Momentum Clone", 1, dict(self.cfg, maxBarsBack="lots"))
        self.assertFalse(os.path.exists(self.outputDir()))

    def testMissingEngineDirIsRejected(self):
        with self.assertRaises(GenerationError):
            spw.writeSpecs("Momentum Clone", 1, dict(self.cfg, engineDir=""))


if __name__ == "__main__":
    unittest.main()
