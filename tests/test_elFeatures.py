"""The EasyLanguage feature gate.

This is the first test in the repo that loads anything in `rules/`. It is
deliberately two things at once: unit tests of the extractor against fixtures,
and a scan of the real corpus in both repos, because the extractor being right
on a fixture and right on `AtrProfitTarget`'s twenty-line comment are different
claims.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lintElFeatures as lef
import runBatch


REGISTRY = """# fixture
| Feature | Status | What is known | Evidence |
|---|---|---|---|
| `close` `high` | VERIFIED | fine | probe |
| `openpositionprofit` | VERIFIED | fine | probe |
| `average` | ACCEPTED | fine | - |
| `>` `<` | VERIFIED | the el_* helpers register as `>` | probe |
| `date` | ASSUMED | in use, unmeasured | - |
| `mod` | UNKNOWN | never measured | - |
"""


def writeRule(directory, name, **fields):
    path = os.path.join(directory, name + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(fields, fh)
    return path


class TestExtractionEl(unittest.TestCase):
    def testSubtractsOwnInputsAndLocals(self):
        rule = {"inputVariables": {"lookback": "20"},
                "localVariables": {"rrange": "0"},
                "preConditionHook": "rrange = high - low;",
                "longCondition": "rrange > average(rrange, lookback)"}
        self.assertEqual(lef.elFeaturesOfTsRule(rule), {"average", "high", "low"})

    def testSubtractsControlFlowKeywords(self):
        rule = {"localVariables": {"ii": "0", "hits": "0"},
                "preConditionHook": "For ii = 0 To 5 Begin If true Then hits = hits + 1; End;"}
        self.assertEqual(lef.elFeaturesOfTsRule(rule), set())

    def testFoldsCaseBecauseEasyLanguageIsCaseInsensitive(self):
        rule = {"longCondition": "Maxpositionprofit > maxpositionprofit"}
        self.assertEqual(lef.elFeaturesOfTsRule(rule), {"maxpositionprofit"})

    def testIgnoresBracedComments(self):
        rule = {"preConditionHook": "{ mirrors WFSafe_AvgTrueRange and Summation }\nx = 1;",
                "localVariables": {"x": "0"}}
        self.assertEqual(lef.elFeaturesOfTsRule(rule), set())


class TestExtractionCpp(unittest.TestCase):
    def testScansAnchorsNotBareIdentifiers(self):
        # hi, lo, kk and i are loop scaffolding and must not register.
        rule = {"preConditionHook": "for (int kk = 0; kk < 5; ++kk) { double hi = 0.0, lo = 1.0; }",
                "longCondition": "el_gt(ctx.OpenPositionProfit(), 0.0)"}
        found, _ = lef.elFeaturesOfBeRule(rule)
        self.assertEqual(found, {"openpositionprofit", ">"})

    def testPriceAliasSubscriptRegisters(self):
        rule = {"longCondition": "el_gt(close[0], close[20])"}
        found, _ = lef.elFeaturesOfBeRule(rule)
        self.assertIn("close", found)

    def testLeadingDotDoesNotRegisterAPhantomFeature(self):
        # civil_from_days(...).month must yield `month` once, from the helper --
        # never a second time from the member access.
        rule = {"preConditionHook": "m = civil_from_days(day_of(ctx.Time(0))).month;"}
        found, _ = lef.elFeaturesOfBeRule(rule)
        self.assertEqual(found, {"month", "time"})

    def testIgnoresCppComments(self):
        rule = {"preConditionHook": "// mirrors ctx.MaxPositionProfit()\n/* and close[0] */\nx = 1;"}
        found, _ = lef.elFeaturesOfBeRule(rule)
        self.assertEqual(found, set())

    def testBareRelationalInAConditionIsReported(self):
        rule = {"longCondition": "close[0] > close[20]"}
        _, raw = lef.elFeaturesOfBeRule(rule)
        self.assertEqual(raw, ["longCondition"])

    def testBareRelationalInAHookIsNotReported(self):
        rule = {"preConditionHook": "for (int i = 0; i < 5; ++i) {}",
                "longCondition": "el_gt(close[0], 0.0)"}
        _, raw = lef.elFeaturesOfBeRule(rule)
        self.assertEqual(raw, [])


class TestGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.be = os.path.join(self.tmp.name, "be")
        self.ts = os.path.join(self.tmp.name, "ts")
        os.makedirs(self.be)
        os.makedirs(self.ts)
        with open(lef.registryPath(self.be), "w", encoding="utf-8") as fh:
            fh.write(REGISTRY)

    def _lint(self, names=None):
        return lef.lint(names, rulesDir=self.be, tsDir=self.ts)

    def _errors(self, names=None):
        return [f for f in self._lint(names) if f[0] == "error"]

    def testRegisteredFeaturePasses(self):
        writeRule(self.be, "Ok", longCondition="el_gt(ctx.OpenPositionProfit(), 0.0)")
        writeRule(self.ts, "Ok", longCondition="openpositionprofit > 0")
        self.assertEqual(self._errors(), [])

    def testUnregisteredFeatureBlocks(self):
        writeRule(self.be, "Rsi", longCondition="el_lt(rsiValue, 30.0)",
                  localVariables={"rsiValue": {"type": "double", "init": "0.0"}})
        writeRule(self.ts, "Rsi", longCondition="RSI(Close, 14) < 30")
        errors = self._errors()
        self.assertTrue(any("`rsi`" in m for _, _, m in errors), errors)

    def testUnknownStatusBlocks(self):
        writeRule(self.be, "M", longCondition="el_gt(x, 0.0)",
                  localVariables={"x": {"type": "double", "init": "0.0"}})
        writeRule(self.ts, "M", longCondition="Mod(CurrentBar, 2) = 0",
                  localVariables={})
        errors = self._errors()
        self.assertTrue(any("`mod`" in m and "UNKNOWN" in m for _, _, m in errors), errors)

    def testAssumedWarnsButDoesNotBlock(self):
        writeRule(self.be, "D", longCondition="el_gt(ctx.OpenPositionProfit(), 0.0)")
        writeRule(self.ts, "D", longCondition="date > 0 and openpositionprofit > 0")
        self.assertEqual(self._errors(), [])
        self.assertTrue(any(s == "warning" and "`date`" in m for s, _, m in self._lint()))

    def testMissingEasyLanguageTwinBlocks(self):
        writeRule(self.be, "Orphan", longCondition="el_gt(close[0], 0.0)")
        self.assertTrue(any("twin" in m for _, _, m in self._errors()))

    def testLocalShadowingAnElWordBlocks(self):
        writeRule(self.be, "Shadow", longCondition="el_gt(average, 0.0)",
                  localVariables={"average": {"type": "double", "init": "0.0"}})
        writeRule(self.ts, "Shadow", longCondition="average > 0",
                  localVariables={"average": "0"})
        self.assertTrue(any("hide that feature" in m for _, _, m in self._errors()))

    def testScopingToNamedRulesIgnoresTheRest(self):
        writeRule(self.be, "Ok", longCondition="el_gt(ctx.OpenPositionProfit(), 0.0)")
        writeRule(self.ts, "Ok", longCondition="openpositionprofit > 0")
        writeRule(self.be, "Bad", longCondition="el_lt(v, 30.0)",
                  localVariables={"v": {"type": "double", "init": "0.0"}})
        writeRule(self.ts, "Bad", longCondition="RSI(Close, 14) < 30")
        self.assertEqual(self._errors(["Ok"]), [])
        self.assertTrue(self._errors(["Bad"]))

    def testEnforceRaisesOnError(self):
        writeRule(self.be, "Bad", longCondition="el_lt(v, 30.0)",
                  localVariables={"v": {"type": "double", "init": "0.0"}})
        writeRule(self.ts, "Bad", longCondition="RSI(Close, 14) < 30")
        with self.assertRaises(lef.LintError):
            lef.enforce(["Bad"], rulesDir=self.be, tsDir=self.ts)

    def testAMissingRegistryDegradesToAWarning(self):
        # A config problem must never read as a rule problem, or the gate gets
        # switched off for the wrong reason.
        os.remove(lef.registryPath(self.be))
        findings = self._lint()
        self.assertTrue(findings)
        self.assertTrue(all(s == "warning" for s, _, _ in findings))


class TestBatchPreflight(unittest.TestCase):
    """The downgrade path: headers generated while a feature looked settled,
    run after a probe came back and contradicted it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.gen = os.path.join(self.tmp.name, "src", "bt", "strategies", "generated")
        os.makedirs(self.gen)
        self.cfg = {"engineDir": self.tmp.name,
                    "generatedSubdir": "src/bt/strategies/generated"}

    def _manifest(self, entry):
        with open(os.path.join(self.gen, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"My Strategy": entry}, fh)

    def testDowngradedFeatureStopsTheBatch(self):
        self._manifest({"header": "gen_my_strategy.h", "entries": [],
                        "elFeatures": ["close", "mod"]})   # `mod` is UNKNOWN
        with self.assertRaises(runBatch.GenerationError) as ctx:
            runBatch.preflightFeatureGate("my_strategy", self.cfg, [])
        self.assertIn("mod", str(ctx.exception))

    def testSettledFeaturesPass(self):
        self._manifest({"header": "gen_my_strategy.h", "entries": [],
                        "elFeatures": ["close", "openpositionprofit"]})
        warnings = []
        runBatch.preflightFeatureGate("my_strategy", self.cfg, warnings)
        self.assertEqual(warnings, [])

    def testHeaderPredatingTheGateWarnsRatherThanFails(self):
        self._manifest({"header": "gen_my_strategy.h", "entries": []})
        warnings = []
        runBatch.preflightFeatureGate("my_strategy", self.cfg, warnings)
        self.assertTrue(any("unrecorded" in w for w in warnings), warnings)

    def testAnUnreadableSetupWarnsRatherThanFails(self):
        warnings = []
        runBatch.preflightFeatureGate("my_strategy", {"engineDir": ""}, warnings)
        self.assertTrue(warnings)


class TestRealCorpus(unittest.TestCase):
    """The scan that matters. If this ever has a false positive on day one, the
    gate gets switched off by the end of the week."""

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(lef.tsRulesDir()):
            raise unittest.SkipTest("StrategyGeneratorTS rules not checked out")
        cls.findings = lef.lint()

    def testNoRuleUsesAnUnmeasuredFeature(self):
        errors = [f for f in self.findings if f[0] == "error"]
        self.assertEqual(errors, [], "\n".join(f"{r}: {m}" for _, r, m in errors))

    def testTheExtractorActuallySeesTheCorpus(self):
        # A clean run means nothing if the scan found nothing -- the same sanity
        # check every EL probe carries.
        rules = [f for f in os.listdir(lef.RULES_DIR) if f.endswith(".json")]
        seen = set()
        for fn in rules:
            with open(os.path.join(lef.RULES_DIR, fn), encoding="utf-8-sig") as fh:
                be = json.load(fh)
            found, _ = lef.elFeaturesOfBeRule(be)
            seen |= found
        self.assertGreaterEqual(len(rules), 13)
        self.assertIn("openpositionprofit", seen)
        self.assertIn("wfsafe_avgtruerange", lef.loadRegistry())

    def testAssumedDebtDoesNotGrowUnnoticed(self):
        # ASSUMED warns rather than blocks, so that the seeded debt does not
        # ship the gate red. This pins the debt to what is known, so a NEW
        # assumption fails here even though it would not block authoring.
        # Empty, for now: `date` and `and`/`or`/`not` were both seeded here and
        # both probes came back (EL_Date_Probe.txt, EL_LogicalEval_Probe.txt).
        # This is the assertion that makes NEW debt visible -- a feature added
        # as ASSUMED fails here even though it would not block authoring.
        expected = set()
        assumed = {tok for tok, status in lef.loadRegistry().items()
                   if status == lef.ASSUMED}
        self.assertEqual(assumed, expected,
                         "EL_FEATURES.md's ASSUMED set changed. If you added one, "
                         "it is unmeasured debt -- write the probe or update this list "
                         "deliberately.")


if __name__ == "__main__":
    unittest.main()
