import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mainGUI
from mainGUI import ENGINE_MARKER, REBUILD_COMMAND, engineDirProblem, summaryText
from specWriter import SpecResult
from strategyWriter import GenerationResult


def result(entries=(("Momentum Clone V1", "Gen_Momentum_Clone_V1"),)):
    return GenerationResult(
        headerPath=r"C:\engine\src\bt\strategies\generated\gen_momentum_clone.h",
        headersIncPath=r"C:\engine\src\bt\strategies\generated\headers.inc",
        registryIncPath=r"C:\engine\src\bt\strategies\generated\registry.inc",
        generatedDir=r"C:\engine\src\bt\strategies\generated",
        entries=list(entries),
    )


def specs(paths=(r"C:\engine\specs\generated\momentum_clone_v1.json",),
          removed=(), maxBarsBack=100):
    return SpecResult(
        paths=list(paths),
        removed=list(removed),
        outputDir=r"C:\engine\specs\generated",
        maxBarsBack=maxBarsBack,
    )


class TestEngineDirProblem(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def testBlankIsRejected(self):
        self.assertIsNotNone(engineDirProblem(""))
        self.assertIsNotNone(engineDirProblem("   "))
        self.assertIsNotNone(engineDirProblem(None))

    def testMissingDirectoryIsRejected(self):
        problem = engineDirProblem(os.path.join(self.dir, "nope"))
        self.assertIn("does not exist", problem)

    def testDirectoryWithoutTheMarkerIsRejected(self):
        problem = engineDirProblem(self.dir)
        self.assertIn(ENGINE_MARKER, problem)

    def testRealEngineLayoutIsAccepted(self):
        os.makedirs(os.path.join(self.dir, ENGINE_MARKER))
        self.assertIsNone(engineDirProblem(self.dir))

    def testSurroundingWhitespaceIsIgnored(self):
        os.makedirs(os.path.join(self.dir, ENGINE_MARKER))
        self.assertIsNone(engineDirProblem(f"  {self.dir}  "))

    def testTheRealEngineRepoPasses(self):
        # Guards the marker path against an engine-side reorganization.
        engine = r"C:\Users\brian\source\repos\BacktestEngine"
        if not os.path.isdir(engine):
            self.skipTest("BacktestEngine not present")
        self.assertIsNone(engineDirProblem(engine))


class TestSummaryText(unittest.TestCase):
    def testNamesEveryArtifact(self):
        text = summaryText("Momentum Clone", result(), specs())
        self.assertIn("gen_momentum_clone.h", text)
        self.assertIn("Momentum Clone V1  ->  Gen_Momentum_Clone_V1", text)
        self.assertIn("momentum_clone_v1.json", text)

    def testVersionCountIsSingularForOne(self):
        text = summaryText("Momentum Clone", result(), specs())
        self.assertIn("1 version generated", text)

    def testVersionCountIsPluralForMany(self):
        entries = [(f"S V{i}", f"Gen_S_V{i}") for i in (1, 2, 3)]
        text = summaryText("S", result(entries), specs())
        self.assertIn("3 versions generated", text)

    def testEveryRegistryEntryIsListed(self):
        entries = [(f"S V{i}", f"Gen_S_V{i}") for i in (1, 2, 3)]
        text = summaryText("S", result(entries), specs())
        for name, cls in entries:
            self.assertIn(f"{name}  ->  {cls}", text)

    def testMaxBarsBackIsShownWithItsWarning(self):
        text = summaryText("S", result(), specs(maxBarsBack=250))
        self.assertIn("Max Bars Back: 250", text)
        self.assertIn("largest lookback", text)
        self.assertIn("not computed from your rule", text)

    def testRebuildCommandIsIncluded(self):
        text = summaryText("S", result(), specs())
        self.assertIn(REBUILD_COMMAND, text)

    def testPrunedSpecsAreReportedWhenPresent(self):
        text = summaryText(
            "S", result(), specs(removed=[r"C:\engine\specs\generated\s_v2.json"])
        )
        self.assertIn("Removed 1 spec(s)", text)
        self.assertIn("s_v2.json", text)

    def testNothingIsSaidAboutPruningWhenNoneHappened(self):
        self.assertNotIn("Removed", summaryText("S", result(), specs()))


class TestModuleSurface(unittest.TestCase):
    def testMultiWalkIsGone(self):
        # The MW export and everything it dragged in was dropped for this port.
        for name in ("_makeMWInputs", "_pasteMWCode", "_showMWResult"):
            self.assertFalse(hasattr(mainGUI.mainGUI, name), name)


class TestTemplateState(unittest.TestCase):
    """Round-trips through a real (hidden) window, so the template format is
    checked against the widgets rather than against the source text."""

    def setUp(self):
        self.gui = mainGUI.mainGUI()
        self.gui.withdraw()
        self.addCleanup(self.gui.destroy)

    def testMaxBarsBackSurvivesSaveAndLoad(self):
        self.gui.strategyNameVar.set("Momentum Clone")
        self.gui.maxBarsBackVar.set("250")
        state = self.gui._serializeState()
        self.assertEqual(state["maxBarsBack"], "250")

        self.gui.maxBarsBackVar.set("")
        self.gui._applyState(state)
        self.assertEqual(self.gui.maxBarsBackVar.get(), "250")
        self.assertEqual(self.gui.strategyNameVar.get(), "Momentum Clone")

    def testPanesAndModifiersSurviveSaveAndLoad(self):
        self.gui._addPane("Entry")
        pane = self.gui.panes[0]
        item = mainGUI.RuleItem("Momentum")
        item.flipped = True
        item.params = {"Length": {"start": "5", "stop": "50", "step": "5"}}
        pane.items.extend([item, mainGUI.DELIMITER, mainGUI.RuleItem("Momentum")])

        state = self.gui._serializeState()
        self.gui._applyState(state)

        self.assertEqual(len(self.gui.panes), 1)
        restored = self.gui.panes[0]
        self.assertEqual(restored.ruleType, "Entry")
        self.assertEqual(len(restored.items), 3)
        self.assertTrue(restored.items[0].flipped)
        self.assertFalse(restored.items[0].negated)
        self.assertEqual(
            restored.items[0].params, {"Length": {"start": "5", "stop": "50", "step": "5"}}
        )
        self.assertEqual(restored.items[1], mainGUI.DELIMITER)

    def testEveryTopFieldExists(self):
        for attr in ("strategyNameVar", "engineDirVar", "specTemplateVar",
                     "maxBarsBackVar"):
            self.assertTrue(hasattr(self.gui, attr), attr)


if __name__ == "__main__":
    unittest.main()
