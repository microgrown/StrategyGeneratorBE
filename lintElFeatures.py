"""Check every rule's EasyLanguage feature use against `rules/EL_FEATURES.md`.

    python lintElFeatures.py            # lint the whole corpus
    python lintElFeatures.py Momentum   # lint named rules only

Exit 0 when every feature both libraries reach for is VERIFIED, ACCEPTED or
ASSUMED; 1 when any is UNKNOWN or unregistered.

WHY THIS EXISTS

The engine reproduces TradeStation and MultiWalk bit-for-bit, and almost every
EasyLanguage feature the corpus has reached for turned out to behave differently
from the obvious reading -- `Volume` is up-ticks not total, `BarsSinceExit`
wants an index, `WFSafe_AvgTrueRange` is a rolling accumulator and a *different
function* from the built-in it resembles. Thirteen rules took seventeen probe
runs to pin down, and every one was found AFTER a MultiWalk disagreement. A
corpus ten times the size cannot be debugged that way, so an unmeasured feature
must fail loudly at authoring time instead.

WHAT IT CANNOT DO -- read this before trusting a clean run

This checks that a feature is DECLARED AND REGISTERED. It does not check that
the hand-rolled C++ is CORRECT. `BarRangeAboveStd` calls no `ctx` accessor at
all, because EL's `Average`/`StdDev` became a ring buffer and two loops; nothing
here can tell a right loop from a wrong one. Only the probe and the test that
locks it establish that.

`scripts/compare_el_strategy.py` learned this the hard way: it asserted that
"EL has no MarketPosition guard on entries" was equivalent to the C++ guards,
and so reported `rule mismatches: 0` across a real behavioural difference for
months. A whole-block comparison asserts that two spellings mean the same thing
and reports silence if they do not. Treat a clean lint the same way.

HOW FEATURES ARE EXTRACTED

*The EasyLanguage twin is the primary source*, because EL names its features
literally where the C++ has already hand-rolled them into loops. For each TS
rule we take every identifier in the code fields and subtract that rule's own
inputs and locals, the EL language keywords, and numeric literals. What is left
is the EL surface -- exact on the live corpus, because StrategyGeneratorTS
builds its `variables:` block only from `localVariables`, so the JSON declares
every non-EL name in the file.

*The C++ twin is scanned at ANCHORS only*, never by bare identifier: the rules
are full of `hi`, `lo`, `out`, `kk`, `i`. Every EL-facing thing in the C++
arrives through `ctx.X(`, `ctx.Ticks[`, a price alias subscript, an `el_*`
helper, or a named engine helper. That catches the case which has cost the most
-- the EL side calls a `WFSafe_` override while the C++ hand-rolled the plain
built-in -- and touches no loop variable.

Both sides are stripped of comments and string literals first. That is not
optional: `AtrProfitTarget`'s preConditionHook carries a twenty-line comment
naming `WFSafe_AvgTrueRange`, `Summation` and `MaxBarsBack` in prose, and
scanning it would register features the code never calls.
"""

import json
import os
import re
import sys

REGISTRY_NAME = "EL_FEATURES.md"
RULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules")

CODE_FIELDS = ("classMembersHook", "startOfFileHook", "preConditionHook",
               "longCondition", "shortCondition", "postConditionHook",
               "endOfFileHook")
CONDITION_FIELDS = ("longCondition", "shortCondition")

# EasyLanguage's own vocabulary -- syntax, not features to be measured.
EL_KEYWORDS = frozenset("""
    if then else begin end for to downto while and or not true false
    inputs variables vars input var
""".split())

# Engine-side accessors with no EasyLanguage twin. LotCount exists only to make
# EntryPrice(lot) addressable, so there is nothing about EL for a row to record.
ENGINE_ONLY = frozenset({"lotcount"})

# C++ helpers that implement an EL word, mapped to the word they implement.
CPP_HELPERS = {"civil_from_days": "month", "day_of": "month"}

VERIFIED, ACCEPTED, ASSUMED, UNKNOWN = "VERIFIED", "ACCEPTED", "ASSUMED", "UNKNOWN"
STATUSES = (VERIFIED, ACCEPTED, ASSUMED, UNKNOWN)
# Statuses that let authoring proceed. ASSUMED is debt, not a block: the seeded
# corpus carries a few, and a gate that ships red is a gate that gets switched
# off. The whole-corpus unittest fails on ASSUMED so the debt stays visible.
PASSING = (VERIFIED, ACCEPTED, ASSUMED)

# A leading `.` exclusion is load-bearing: without it `civil_from_days(...).month`
# registers a phantom EL `Month`. The digit exclusion stops `1e5` yielding `e5`.
_BOUNDARY = r"(?<![A-Za-z0-9_.])"
_IDENT = re.compile(_BOUNDARY + r"[A-Za-z_][A-Za-z0-9_]*")
_CTX_CALL = re.compile(r"\bctx\.([A-Za-z_]\w*)\s*\(")
_CTX_SERIES = re.compile(r"\bctx\.([A-Za-z_]\w*)\s*\[")
_PRICE_ALIAS = re.compile(_BOUNDARY + r"(open|high|low|close|volume)\s*\[")
_EL_HELPER = re.compile(r"\bel_(gt|lt|ge|le|eq|ne)\s*\(")
_CPP_HELPER = re.compile(_BOUNDARY + r"(" + "|".join(CPP_HELPERS) + r")\s*\(")
# A relational operator in a CONDITION must go through el_*; inside a hook a
# bare `<` is ordinary loop arithmetic and is left alone.
_RAW_RELATIONAL = re.compile(r"(?<![<>=!])(<=|>=|<|>|==|!=)(?!=)")
_REGISTRY_TOKEN = re.compile(r"`([^`]+)`")

_EL_COMMENT = re.compile(r"\{.*?\}", re.S)
_C_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT = re.compile(r"//[^\n]*")
_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


class LintError(Exception):
    """Raised by `enforce` so callers can fail a build with one message."""


def _strip(text, easylanguage):
    """Comments and string literals carry feature names in prose. Remove them."""
    if easylanguage:
        text = _EL_COMMENT.sub(" ", text)
    else:
        text = _C_BLOCK_COMMENT.sub(" ", text)
    text = _LINE_COMMENT.sub(" ", text)
    return _STRING.sub(' "" ', text)


def registryPath(rulesDir=RULES_DIR):
    return os.path.join(rulesDir, REGISTRY_NAME)


def loadRegistry(rulesDir=RULES_DIR):
    """token -> status, parsed from the markdown tables in EL_FEATURES.md.

    A row is `| `tok` `tok2` | STATUS | ... |`; the first cell may carry several
    tokens because some features are only meaningful as a set (the four price
    series, the six relational operators)."""
    path = registryPath(rulesDir)
    if not os.path.exists(path):
        raise LintError(f"No EasyLanguage feature registry at {path}.")
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.lstrip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2:
                continue
            status = cells[1].replace("*", "").strip().upper()
            if status not in STATUSES:
                continue
            for tok in _REGISTRY_TOKEN.findall(cells[0]):
                out[tok.strip().lower()] = status
    if not out:
        raise LintError(f"{path} parsed to zero features -- the table format "
                        "changed and the linter is now blind.")
    return out


def tsRulesDir(beRulesDir=RULES_DIR):
    """The EasyLanguage twin library, a sibling checkout by convention."""
    repoRoot = os.path.dirname(os.path.abspath(beRulesDir))
    cfg = os.path.join(repoRoot, "config.json")
    if os.path.exists(cfg):
        try:
            with open(cfg, encoding="utf-8-sig") as fh:
                override = (json.load(fh).get("tsRulesDir") or "").strip()
            if override:
                return os.path.normpath(override)
        except (OSError, ValueError):
            pass
    return os.path.normpath(
        os.path.join(os.path.dirname(repoRoot), "StrategyGeneratorTS", "rules"))


def gateMode(beRulesDir=RULES_DIR):
    """'block' (default), 'warn' or 'off' -- an escape hatch so a linter bug can
    never brick the tool."""
    cfg = os.path.join(os.path.dirname(os.path.abspath(beRulesDir)), "config.json")
    if os.path.exists(cfg):
        try:
            with open(cfg, encoding="utf-8-sig") as fh:
                return (json.load(fh).get("elFeatureGate") or "block").strip().lower()
        except (OSError, ValueError):
            pass
    return "block"


def _codeBlob(rule, easylanguage, fields=CODE_FIELDS):
    return _strip("\n".join(str(rule.get(f, "") or "") for f in fields), easylanguage)


def _ownNames(rule):
    names = set(rule.get("inputVariables") or {})
    names |= set(rule.get("localVariables") or {})
    return {n.lower() for n in names}


def elFeaturesOfTsRule(rule):
    """The EasyLanguage feature tokens one TS rule reaches for."""
    own = _ownNames(rule)
    return {t.lower() for t in _IDENT.findall(_codeBlob(rule, True))
            if t.lower() not in own and t.lower() not in EL_KEYWORDS}


def elFeaturesOfBeRule(rule):
    """(features, rawComparisonFields) for one BE rule, scanned at anchors."""
    blob = _codeBlob(rule, False)
    found = {m.lower() for m in _CTX_CALL.findall(blob)}
    found |= {m.lower() for m in _CTX_SERIES.findall(blob)}
    found |= {m.lower() for m in _PRICE_ALIAS.findall(blob)}
    found |= {CPP_HELPERS[m] for m in _CPP_HELPER.findall(blob)}
    found -= ENGINE_ONLY
    if _EL_HELPER.search(blob):
        found.add(">")
    raw = [f for f in CONDITION_FIELDS
           if _RAW_RELATIONAL.search(_strip(str(rule.get(f, "") or ""), False))]
    return found, raw


def _loadJson(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def lint(names=None, rulesDir=RULES_DIR, tsDir=None):
    """[(severity, ruleName, message)] -- severity is 'error' or 'warning'.

    A registry or twin-library that cannot be read degrades to a warning: a
    config problem must never read as a rule problem, or the gate gets
    switched off for the wrong reason."""
    try:
        registry = loadRegistry(rulesDir)
    except LintError as exc:
        return [("warning", "-", f"{exc} The EL feature gate did not run.")]

    tsDir = tsDir or tsRulesDir(rulesDir)
    if not os.path.isdir(tsDir):
        return [("warning", "-",
                 f"No EasyLanguage rule library at {tsDir}; the EL feature gate "
                 "did not run. Set `tsRulesDir` in config.json.")]

    findings = []
    wanted = {n.lower() for n in names} if names else None
    for fn in sorted(os.listdir(rulesDir)):
        if not fn.endswith(".json"):
            continue
        name = fn[:-5]
        if wanted and name.lower() not in wanted:
            continue

        beRule = _loadJson(os.path.join(rulesDir, fn))
        beFeatures, rawFields = elFeaturesOfBeRule(beRule)

        tsPath = os.path.join(tsDir, fn)
        if os.path.exists(tsPath):
            tsRule = _loadJson(tsPath)
            tsFeatures = elFeaturesOfTsRule(tsRule)
        else:
            tsRule, tsFeatures = None, set()
            findings.append(("error", name,
                             "no EasyLanguage twin. The twin is what declares the "
                             "EL surface; a C++ emulation loop declares nothing."))

        for feature in sorted(tsFeatures | beFeatures):
            status = registry.get(feature)
            side = "EL" if feature in tsFeatures else "C++"
            if status is None:
                findings.append(("error", name,
                                 f"`{feature}` ({side}) is not in {REGISTRY_NAME}. "
                                 "Write a probe from EL_Probe_Template.txt, add an "
                                 "UNKNOWN row, and run it -- see "
                                 "BacktestEngine/docs/EL_VERIFICATION.md."))
            elif status == UNKNOWN:
                findings.append(("error", name,
                                 f"`{feature}` ({side}) is UNKNOWN in {REGISTRY_NAME}: "
                                 "its EasyLanguage behaviour has never been measured."))
            elif status == ASSUMED:
                findings.append(("warning", name,
                                 f"`{feature}` ({side}) is ASSUMED in {REGISTRY_NAME} "
                                 "-- in use but never measured. A probe is warranted."))

        # A rule variable named after an EL word would hide that word from this
        # gate entirely, because own-names are subtracted before lookup.
        for own in sorted(_ownNames(beRule) | (_ownNames(tsRule) if tsRule else set())):
            if registry.get(own):
                findings.append(("error", name,
                                 f"declares `{own}`, which is an EasyLanguage word. "
                                 "Rename it: it would hide that feature from this gate."))

        for field in rawFields:
            findings.append(("warning", name,
                             f"{field} uses a bare relational operator. EasyLanguage's "
                             "carry an absolute 2.22e-12 tolerance -- use el_gt/el_lt/etc."))
    return findings


def featuresOfRules(names, rulesDir=RULES_DIR, tsDir=None):
    """The union of EL features the named rules reach for, both sides.

    `strategyWriter` records this in the generated manifest so a batch can be
    re-checked later against a registry that may since have downgraded one of
    them. Never raises: a header that cannot be described is still a header."""
    tsDir = tsDir or tsRulesDir(rulesDir)
    found = set()
    for name in names or ():
        bePath = os.path.join(rulesDir, name + ".json")
        if os.path.exists(bePath):
            try:
                beFeatures, _ = elFeaturesOfBeRule(_loadJson(bePath))
                found |= beFeatures
            except (OSError, ValueError):
                pass
        tsPath = os.path.join(tsDir, name + ".json")
        if os.path.exists(tsPath):
            try:
                found |= elFeaturesOfTsRule(_loadJson(tsPath))
            except (OSError, ValueError):
                pass
    return found


def enforce(names=None, rulesDir=RULES_DIR, tsDir=None):
    """Raise LintError on any error-severity finding. For build-path callers.

    `names` scopes the check to the rules actually being used: one half-finished
    rule in the corpus must never block an unrelated strategy."""
    mode = gateMode(rulesDir)
    if mode == "off":
        return []
    findings = lint(names, rulesDir, tsDir)
    errors = [f for f in findings if f[0] == "error"]
    if errors and mode == "block":
        lines = "\n".join(f"  {rule}: {msg}" for _, rule, msg in errors)
        raise LintError(
            f"{len(errors)} unmeasured EasyLanguage feature(s):\n{lines}\n"
            f"Record each in rules/{REGISTRY_NAME} once a probe has settled it.")
    return findings


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    findings = lint(argv or None)
    errors = [f for f in findings if f[0] == "error"]
    warnings = [f for f in findings if f[0] == "warning"]
    for severity, rule, msg in findings:
        print(f"{severity.upper():7} {rule}: {msg}")
    scanned = len([f for f in os.listdir(RULES_DIR) if f.endswith(".json")])
    print(f"\n{scanned} rules scanned, {len(errors)} blocking, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
