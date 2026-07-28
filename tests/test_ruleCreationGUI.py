import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importing the module pulls in tkinter but creates no Tk root, so these tests
# run headless. Everything exercised here is a module-level pure function.
from ruleCreationGUI import (
    codeWarnings,
    validateName,
    validateRule,
    validateVariables,
    variableWarnings,
)


def titles(warnings):
    return [title for title, _ in warnings]


class TestValidateName(unittest.TestCase):
    def testBlankIsRejected(self):
        self.assertTrue(validateName(""))

    def testEveryIllegalFilenameCharIsRejected(self):
        for ch in '\\/:*?"<>|':
            self.assertTrue(validateName("Rule" + ch), f"{ch!r} should be rejected")

    def testOrdinaryNameIsClean(self):
        self.assertEqual(validateName("MomentumConsecutiveBars"), [])

    def testSpacesAreAllowed(self):
        self.assertEqual(validateName("Momentum Entry"), [])


class TestVariableNames(unittest.TestCase):
    def testMalformedIdentifiersAreRejected(self):
        for bad in ("2fast", "has-dash", "has space", "", "a.b"):
            self.assertTrue(
                validateVariables({bad: "1"}, {}), f"{bad!r} should be rejected"
            )

    def testValidIdentifiersAreAccepted(self):
        for good in ("_ok", "ok2", "lookback", "MinADX"):
            self.assertEqual(validateVariables({good: "1"}, {}), [])

    def testCppKeywordsAreRejected(self):
        for kw in ("class", "int", "template", "operator"):
            self.assertTrue(validateVariables({kw: "1"}, {}), f"{kw!r} should be rejected")

    def testReservedNamesAreRejectedAsInputs(self):
        for reserved in ("close", "ctx", "enterLong", "exitShort", "volume"):
            errors = validateVariables({reserved: "1"}, {})
            self.assertTrue(errors, f"{reserved!r} should be rejected")
            self.assertIn("reserved", errors[0])

    def testReservedNamesAreRejectedAsLocals(self):
        errors = validateVariables({}, {"close": {"type": "double", "init": "0"}})
        self.assertTrue(errors)
        self.assertIn("reserved", errors[0])

    def testReservedCheckIsCaseSensitive(self):
        # The emitter's rename is case-sensitive, so "Close" cannot shadow "close".
        self.assertEqual(validateVariables({"Close": "1"}, {}), [])


class TestInputDefaults(unittest.TestCase):
    def testNumericDefaultsAreAccepted(self):
        for value in ("200", "-2.5", "1e3", "0.75", "+4"):
            self.assertEqual(
                validateVariables({"x": value}, {}), [], f"{value!r} should be accepted"
            )

    def testBlankDefaultIsRejected(self):
        errors = validateVariables({"lookback": ""}, {})
        self.assertTrue(errors)
        self.assertIn("default", errors[0])

    def testNonNumericDefaultIsRejected(self):
        errors = validateVariables({"lookback": "abc"}, {})
        self.assertTrue(errors)
        self.assertIn("not a number", errors[0])


class TestLocalVariables(unittest.TestCase):
    def testTypeAndInitIsClean(self):
        self.assertEqual(validateVariables({}, {"ii": {"type": "int", "init": "0"}}), [])

    def testMissingTypeIsRejected(self):
        errors = validateVariables({}, {"ii": {"type": "", "init": "0"}})
        self.assertTrue(errors)
        self.assertIn("type", errors[0])

    def testMissingInitIsRejected(self):
        errors = validateVariables({}, {"ii": {"type": "int", "init": ""}})
        self.assertTrue(errors)
        self.assertIn("initial value", errors[0])

    def testBareLocalReportsBothProblems(self):
        self.assertEqual(len(validateVariables({}, {"ii": {"type": "", "init": ""}})), 2)


class TestNamespaceClash(unittest.TestCase):
    def testSameNameAsInputAndLocalIsRejected(self):
        errors = validateVariables(
            {"lookback": "200"}, {"lookback": {"type": "int", "init": "0"}}
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("lookback", errors[0])

    def testDistinctNamesAreClean(self):
        self.assertEqual(
            validateVariables({"lookback": "200"}, {"ii": {"type": "int", "init": "0"}}),
            [],
        )


class TestVariableWarnings(unittest.TestCase):
    def testUnusualTypeWarnsButDoesNotError(self):
        local = {"ii": {"type": "long", "init": "0"}}
        self.assertEqual(validateVariables({}, local), [])
        self.assertEqual(titles(variableWarnings(local)), ["Unusual local type"])

    def testWhitelistedTypesDoNotWarn(self):
        self.assertEqual(
            variableWarnings({
                "a": {"type": "int", "init": "0"},
                "b": {"type": "double", "init": "0.0"},
                "c": {"type": "bool", "init": "false"},
            }),
            [],
        )

    def testLegacyDoubleHoldingABoolWarns(self):
        # How every StrategyGeneratorTS import lands: EL recorded no type.
        warnings = variableWarnings({"ConditionOne": {"type": "double", "init": "true"}})
        self.assertEqual(titles(warnings), ["Local typed double holds a bool"])

    def testDoubleHoldingANumberDoesNotWarn(self):
        self.assertEqual(variableWarnings({"sum": {"type": "double", "init": "0"}}), [])


class TestCodeWarnings(unittest.TestCase):
    def testSemicolonInConditionWarns(self):
        warnings = codeWarnings({"longCondition": "close[0] > close[20];"})
        self.assertEqual(titles(warnings), ["Semicolon in condition"])
        self.assertIn("Long Condition", warnings[0][1])

    def testSemicolonInAHookDoesNotWarn(self):
        self.assertEqual(codeWarnings({"preConditionHook": "int i = 0;"}), [])

    def testUnbalancedBracketsWarn(self):
        warnings = codeWarnings({"longCondition": "close[0 > x"})
        self.assertEqual(titles(warnings), ["Unbalanced brackets"])

    def testMismatchedBracketsWarn(self):
        self.assertEqual(
            titles(codeWarnings({"preConditionHook": "if (x] {}"})),
            ["Unbalanced brackets"],
        )

    def testBalancedNestedBracketsDoNotWarn(self):
        self.assertEqual(
            codeWarnings({"preConditionHook": "if (close[0] > close[n]) { sum = {1, 2}; }"}),
            [],
        )

    def testEasyLanguageLeftoversWarn(self):
        text = (
            "For ii = 0 To consecutiveBars - 1 Begin\n"
            "    If Close[ii] <= Close[ii + lookback] Then\n"
            "        ConditionOne = false;\n"
            "End;"
        )
        self.assertIn("EasyLanguage syntax", titles(codeWarnings({"preConditionHook": text})))

    def testCppEndCallDoesNotWarn(self):
        # "End" only counts when it closes an EasyLanguage block ("End;").
        self.assertEqual(
            codeWarnings({"classMembersHook": "auto it = std::find(v.begin(), v.end(), x);"}),
            [],
        )

    def testMiscasedAliasWarns(self):
        # How the other ten StrategyGeneratorTS rules land: EL is case-insensitive.
        warnings = codeWarnings({"longCondition": "Close[0] > Close[lookback]"})
        self.assertEqual(titles(warnings), ["Wrong case for a generator name"])
        self.assertIn("Close", warnings[0][1])

    def testCorrectlyCasedAliasDoesNotWarn(self):
        self.assertEqual(codeWarnings({"longCondition": "close[0] > close[lookback]"}), [])

    def testMemberAccessIsNotFlagged(self):
        self.assertEqual(codeWarnings({"preConditionHook": "double x = bar.Close;"}), [])

    def testCleanCppProducesNoWarnings(self):
        self.assertEqual(
            codeWarnings({
                "classMembersHook": "double Half(double x) const { return x / 2.0; }",
                "startOfFileHook": "if (ctx.CurrentBar() == 1) { sum = 0.0; }",
                "preConditionHook": "",
                "longCondition": "close[0] > close[Length]",
                "shortCondition": "close[0] < close[Length]",
                "postConditionHook": "",
                "endOfFileHook": "",
            }),
            [],
        )


class TestValidateRule(unittest.TestCase):
    def testValidMomentumRuleIsClean(self):
        errors, warnings = validateRule(
            "Momentum",
            {"Length": "20"},
            {},
            {
                "longCondition": "close[0] > close[Length]",
                "shortCondition": "close[0] < close[Length]",
            },
        )
        self.assertEqual((errors, warnings), ([], []))

    def testErrorsAndWarningsAreReportedTogether(self):
        errors, warnings = validateRule(
            "",
            {"close": "abc"},
            {"ii": {"type": "long", "init": "0"}},
            {"longCondition": "close[0] > x;"},
        )
        self.assertEqual(len(errors), 3)  # blank name, reserved input, bad default
        self.assertEqual(titles(warnings), ["Unusual local type", "Semicolon in condition"])


if __name__ == "__main__":
    unittest.main()
