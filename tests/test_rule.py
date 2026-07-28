import os
import sys
import unittest
from dataclasses import asdict, fields

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rule
from rule import (
    LEGACY_LOCAL_TYPE,
    RULE_TYPES,
    TEXT_FIELDS,
    VARIABLE_FIELDS,
    Rule,
    formatField,
    formatInputVariables,
    formatLocalVariables,
    parseField,
    parseInputVariables,
    parseLocalVariables,
)


class TestSchema(unittest.TestCase):
    def testEveryTextFieldIsARuleAttribute(self):
        attrs = {f.name for f in fields(Rule)}
        for label, attr in TEXT_FIELDS:
            self.assertIn(attr, attrs, f"TEXT_FIELDS entry {label!r} has no Rule field")

    def testVariableFieldsAreTextFields(self):
        textAttrs = {attr for _, attr in TEXT_FIELDS}
        for attr in VARIABLE_FIELDS:
            self.assertIn(attr, textAttrs)

    def testClassMembersHookExists(self):
        self.assertEqual(Rule().classMembersHook, "")

    def testDefaultTypeIsEntry(self):
        self.assertEqual(Rule().type, RULE_TYPES[0])

    def testVariableDefaultsAreNotShared(self):
        a, b = Rule(), Rule()
        a.inputVariables["x"] = "1"
        self.assertEqual(b.inputVariables, {})


class TestParseInputVariables(unittest.TestCase):
    def testNameAndDefault(self):
        self.assertEqual(
            parseInputVariables("lookback(200), consecutiveBars(10)"),
            {"lookback": "200", "consecutiveBars": "10"},
        )

    def testBareNameHasEmptyDefault(self):
        self.assertEqual(parseInputVariables("lookback"), {"lookback": ""})

    def testBlankTextIsEmpty(self):
        self.assertEqual(parseInputVariables(""), {})
        self.assertEqual(parseInputVariables("   ,  , "), {})

    def testSurroundingWhitespaceIsIgnored(self):
        self.assertEqual(parseInputVariables("  a ( 1 ) ,b(2)  "), {"a": "1", "b": "2"})

    def testNegativeAndDecimalDefaults(self):
        self.assertEqual(
            parseInputVariables("floor(-2.5), ratio(0.75)"),
            {"floor": "-2.5", "ratio": "0.75"},
        )

    def testRoundTrip(self):
        text = "lookback(200), minADX(15)"
        self.assertEqual(formatInputVariables(parseInputVariables(text)), text)


class TestParseLocalVariables(unittest.TestCase):
    def testTypeAndInit(self):
        self.assertEqual(
            parseLocalVariables("conditionOne(bool, true), ii(int, 0)"),
            {
                "conditionOne": {"type": "bool", "init": "true"},
                "ii": {"type": "int", "init": "0"},
            },
        )

    def testCommaInsideParensDoesNotSplitTheList(self):
        # The StrategyGeneratorTS parser split on every comma, so "ii(int, 0)"
        # became two broken entries. This is the regression guard.
        parsed = parseLocalVariables("ii(int, 0), sum(double, 0.0)")
        self.assertEqual(list(parsed), ["ii", "sum"])

    def testInitializerMayContainCommas(self):
        self.assertEqual(
            parseLocalVariables("vals(int, {1, 2, 3})"),
            {"vals": {"type": "int", "init": "{1, 2, 3}"}},
        )

    def testTypeWithoutInitLeavesInitBlank(self):
        # Not valid to generate from, but must parse so the editor can flag it.
        self.assertEqual(parseLocalVariables("ii(int)"), {"ii": {"type": "int", "init": ""}})

    def testBareNameHasNeitherTypeNorInit(self):
        self.assertEqual(parseLocalVariables("ii"), {"ii": {"type": "", "init": ""}})

    def testEmptyInitAfterCommaIsPreserved(self):
        self.assertEqual(parseLocalVariables("ii(int,)"), {"ii": {"type": "int", "init": ""}})

    def testBlankTextIsEmpty(self):
        self.assertEqual(parseLocalVariables(""), {})

    def testRoundTrip(self):
        text = "done(bool, false), ii(int, 0), sum(double, 0.0)"
        self.assertEqual(formatLocalVariables(parseLocalVariables(text)), text)

    def testRoundTripWithBracedInitializer(self):
        text = "vals(int, {1, 2})"
        self.assertEqual(formatLocalVariables(parseLocalVariables(text)), text)

    def testTypeOnlyRoundTrips(self):
        self.assertEqual(formatLocalVariables(parseLocalVariables("ii(int)")), "ii(int)")


class TestFieldDispatch(unittest.TestCase):
    def testParseFieldPicksTheTypedParserForLocals(self):
        self.assertEqual(
            parseField("localVariables", "ii(int, 0)"),
            {"ii": {"type": "int", "init": "0"}},
        )

    def testParseFieldPicksThePlainParserForInputs(self):
        self.assertEqual(parseField("inputVariables", "ii(0)"), {"ii": "0"})

    def testFormatFieldIsTheInverseForEveryVariableField(self):
        samples = {
            "inputVariables": "lookback(200)",
            "localVariables": "ii(int, 0)",
        }
        for attr in VARIABLE_FIELDS:
            text = samples[attr]
            self.assertEqual(formatField(attr, parseField(attr, text)), text)


class TestFromDict(unittest.TestCase):
    def testUnknownKeysAreIgnored(self):
        r = Rule.from_dict({"name": "R", "somethingElse": 1})
        self.assertEqual(r.name, "R")

    def testMissingKeysUseDefaults(self):
        r = Rule.from_dict({"name": "R"})
        self.assertEqual(r.type, RULE_TYPES[0])
        self.assertEqual(r.localVariables, {})
        self.assertEqual(r.classMembersHook, "")

    def testNewDictFormIsPreserved(self):
        r = Rule.from_dict(
            {"localVariables": {"ii": {"type": "int", "init": "0"}}}
        )
        self.assertEqual(r.localVariables, {"ii": {"type": "int", "init": "0"}})

    def testLegacyLocalsDictOfStringsGetsTheLegacyType(self):
        # A StrategyGeneratorTS rule stored locals as name -> initial value.
        r = Rule.from_dict({"localVariables": {"ConditionOne": "true", "ii": "0"}})
        self.assertEqual(
            r.localVariables,
            {
                "ConditionOne": {"type": LEGACY_LOCAL_TYPE, "init": "true"},
                "ii": {"type": LEGACY_LOCAL_TYPE, "init": "0"},
            },
        )

    def testLegacyLocalsStringFormGetsTheLegacyType(self):
        r = Rule.from_dict({"localVariables": "ConditionOne(true), ii(0)"})
        self.assertEqual(
            r.localVariables,
            {
                "ConditionOne": {"type": LEGACY_LOCAL_TYPE, "init": "true"},
                "ii": {"type": LEGACY_LOCAL_TYPE, "init": "0"},
            },
        )

    def testLegacyInputsStringForm(self):
        r = Rule.from_dict({"inputVariables": "lookback(200)"})
        self.assertEqual(r.inputVariables, {"lookback": "200"})

    def testNumericJsonValuesAreCoercedToStrings(self):
        # Hand-edited JSON can hold real numbers; the emitter formats strings.
        r = Rule.from_dict(
            {"inputVariables": {"lookback": 200},
             "localVariables": {"ii": {"type": "int", "init": 0}}}
        )
        self.assertEqual(r.inputVariables, {"lookback": "200"})
        self.assertEqual(r.localVariables, {"ii": {"type": "int", "init": "0"}})

    def testPartialLocalSpecIsFilledIn(self):
        r = Rule.from_dict({"localVariables": {"ii": {"type": "int"}}})
        self.assertEqual(r.localVariables, {"ii": {"type": "int", "init": ""}})

    def testAsdictRoundTrip(self):
        original = Rule(
            name="MomentumConsecutiveBars",
            type="Entry",
            inputVariables={"lookback": "200"},
            localVariables={"ii": {"type": "int", "init": "0"}},
            classMembersHook="double Helper(Context& ctx) { return 0.0; }",
            preConditionHook="for (int i = 0; i < 3; ++i) {}",
            longCondition="close[0] > close[lookback]",
            shortCondition="close[0] < close[lookback]",
        )
        self.assertEqual(Rule.from_dict(asdict(original)), original)


class TestLegacyAliases(unittest.TestCase):
    def testAliasesStillPointAtTheInputHelpers(self):
        self.assertIs(rule.parseVariables, parseInputVariables)
        self.assertIs(rule.formatVariables, formatInputVariables)


if __name__ == "__main__":
    unittest.main()
