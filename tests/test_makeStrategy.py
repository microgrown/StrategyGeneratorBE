import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import makeStrategy as ms
import templateIO
from mainGUI import ENGINE_MARKER
from strategyWriter import GenerationError

DELIM = "------------------------------"

# A real rule from rules/ so the end-to-end test exercises the actual pipeline.
TEMPLATE = {
    "strategyName": "Headless Probe",
    "maxBarsBack": "120",
    "panes": [
        {
            "ruleType": "Entry",
            "items": [
                {"name": "AtrBandBreakout", "flipped": False, "negated": False,
                 "params": {"lookback": {"start": "50", "stop": "", "step": ""},
                            "atrLookback": {"start": "15", "stop": "", "step": ""},
                            "atrMultiple": {"start": "1", "stop": "3", "step": "1"}}},
                DELIM,
                {"name": "AtrBandBreakout", "flipped": True, "negated": False,
                 "params": {"lookback": {"start": "30", "stop": "", "step": ""},
                            "atrLookback": {"start": "15", "stop": "", "step": ""},
                            "atrMultiple": {"start": "1", "stop": "", "step": ""}}},
            ],
        }
    ],
}

SPEC_TEMPLATE = {
    "name": "validation_momentum",
    "strategy": "Momentum V1",
    "max_bars_back": 50,
    "symbols": ["@ES"],
}


class TestPanesFromTemplate(unittest.TestCase):
    def testItemsAndDelimitersRoundTrip(self):
        panes = ms.panesFromTemplate(TEMPLATE)
        self.assertEqual(len(panes), 1)
        self.assertEqual(panes[0].ruleType, "Entry")
        items = panes[0].items
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0].name, "AtrBandBreakout")
        self.assertFalse(items[0].flipped)
        self.assertEqual(items[0].params["atrMultiple"]["stop"], "3")
        self.assertEqual(items[1], DELIM)
        self.assertTrue(items[2].flipped)

    def testMissingFieldsTakeGuiDefaults(self):
        panes = ms.panesFromTemplate({"panes": [{"items": [{"name": "X"}]}]})
        self.assertEqual(panes[0].ruleType, "Entry")
        item = panes[0].items[0]
        self.assertFalse(item.flipped)
        self.assertFalse(item.negated)
        self.assertEqual(item.params, {})

    def testNoPanes(self):
        self.assertEqual(ms.panesFromTemplate({}), [])


class TestEffectiveConfig(unittest.TestCase):
    CFG = {"engineDir": "E", "specTemplate": "S", "maxBarsBack": "250"}

    def testTemplateMaxBarsBackBeatsConfig(self):
        cfg = ms.effectiveConfig(self.CFG, {"maxBarsBack": "120"})
        self.assertEqual(cfg["maxBarsBack"], "120")

    def testBlankTemplateValueLeavesConfig(self):
        cfg = ms.effectiveConfig(self.CFG, {"maxBarsBack": ""})
        self.assertEqual(cfg["maxBarsBack"], "250")

    def testExplicitOverridesWin(self):
        cfg = ms.effectiveConfig(self.CFG, {"maxBarsBack": "120"},
                                 engineDir="E2", specTemplate="S2", maxBarsBack="7")
        self.assertEqual((cfg["engineDir"], cfg["specTemplate"], cfg["maxBarsBack"]),
                         ("E2", "S2", "7"))

    def testInputIsNotMutated(self):
        cfg = dict(self.CFG)
        ms.effectiveConfig(cfg, {"maxBarsBack": "1"}, engineDir="Z")
        self.assertEqual(cfg, self.CFG)


class TestResolveTemplate(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def testPathIsLoadedDirectly(self):
        path = os.path.join(self.dir, "anything.json")
        with open(path, "w") as f:
            json.dump(TEMPLATE, f)
        self.assertEqual(ms.resolveTemplate(path)["strategyName"], "Headless Probe")

    def testUnknownNameIsRejected(self):
        with mock.patch.object(templateIO, "listTemplateNames", return_value=["a"]):
            with self.assertRaises(GenerationError) as cm:
                ms.resolveTemplate("nope")
        self.assertIn("nope", str(cm.exception))

    def testBlankIsRejected(self):
        with self.assertRaises(GenerationError):
            ms.resolveTemplate("  ")


class TestMakeStrategyEndToEnd(unittest.TestCase):
    """Drives the real generate/writeSpecs against a scratch engine tree, with
    the template store redirected so the auto-save never touches templates/."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.engineDir = os.path.join(self._tmp.name, "engine")
        os.makedirs(os.path.join(self.engineDir, ENGINE_MARKER))
        self.specPath = os.path.join(self._tmp.name, "spec.json")
        with open(self.specPath, "w") as f:
            json.dump(SPEC_TEMPLATE, f)
        self.templatesDir = os.path.join(self._tmp.name, "templates")
        patcher = mock.patch.object(templateIO, "TEMPLATES_DIR", self.templatesDir)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.cfg = ms.effectiveConfig(
            {"engineDir": self.engineDir, "specTemplate": self.specPath}, TEMPLATE)

    def testGeneratesHeaderSpecsAndTemplate(self):
        name, result, specResult = ms.makeStrategy(TEMPLATE, self.cfg)
        self.assertEqual(name, "Headless Probe")
        # Two delimiter groups -> two versions.
        self.assertEqual(result.versionCount, 2)
        self.assertTrue(os.path.exists(result.headerPath))
        self.assertTrue(os.path.exists(result.registryIncPath))
        self.assertEqual(len(specResult.paths), 2)
        with open(specResult.paths[1]) as f:
            spec = json.load(f)
        self.assertEqual(spec["strategy"], result.entries[1][0])
        self.assertEqual(spec["max_bars_back"], 120)
        self.assertEqual(specResult.maxBarsBack, 120)
        saved = templateIO.loadTemplate("Headless Probe")
        self.assertEqual(saved["maxBarsBack"], "120")
        self.assertEqual(saved["panes"], TEMPLATE["panes"])

    def testNameOverrideRenamesEverything(self):
        name, result, specResult = ms.makeStrategy(TEMPLATE, self.cfg, name="Other Name")
        self.assertEqual(name, "Other Name")
        self.assertIn("other_name", os.path.basename(result.headerPath))
        self.assertIn("other_name", os.path.basename(specResult.paths[0]))
        self.assertEqual(templateIO.listTemplateNames(), ["Other Name"])

    def testNoSaveTemplate(self):
        ms.makeStrategy(TEMPLATE, self.cfg, saveTemplate=False)
        self.assertFalse(os.path.isdir(self.templatesDir)
                         and templateIO.listTemplateNames())

    def testBadEngineDirIsAGenerationError(self):
        cfg = dict(self.cfg, engineDir=os.path.join(self._tmp.name, "nope"))
        with self.assertRaises(GenerationError):
            ms.makeStrategy(TEMPLATE, cfg)

    def testBadSpecTemplateWritesNoHeader(self):
        cfg = dict(self.cfg, specTemplate=os.path.join(self._tmp.name, "missing.json"))
        with self.assertRaises(GenerationError):
            ms.makeStrategy(TEMPLATE, cfg)
        generated = os.path.join(self.engineDir, "src", "bt", "strategies", "generated")
        self.assertFalse(os.path.exists(generated))

    def testMissingNameIsReported(self):
        data = dict(TEMPLATE, strategyName="")
        with self.assertRaises(GenerationError) as cm:
            ms.makeStrategy(data, self.cfg)
        self.assertIn("--name", str(cm.exception))

    def testCliRunsAndReportsPaths(self):
        path = os.path.join(self._tmp.name, "t.json")
        with open(path, "w") as f:
            json.dump(TEMPLATE, f)
        with mock.patch("config.load", return_value={}):
            import io
            import contextlib
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = ms.main([path, "--engine-dir", self.engineDir,
                                "--spec-template", self.specPath,
                                "--max-bars-back", "77", "--no-save-template"])
        self.assertEqual(code, 0)
        self.assertIn("2 versions generated", out.getvalue())
        self.assertIn("Max Bars Back: 77", out.getvalue())

    def testCliFailureIsExitOne(self):
        with mock.patch("config.load", return_value={}):
            import io
            import contextlib
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = ms.main(["does-not-exist"])
        self.assertEqual(code, 1)
        self.assertIn("does-not-exist", err.getvalue())


if __name__ == "__main__":
    unittest.main()
