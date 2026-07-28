import re
from dataclasses import dataclass, field, fields

# Allowed rule types. A "Switch" affects entries/exits globally
# (e.g. close all positions and stop entering once a monthly target is hit).
RULE_TYPES = ("Entry", "Exit", "Switch")

# (GUI label, Rule attribute) for every multi-line text field, in display order.
# This is the single source of truth used to build the GUI and to serialize.
TEXT_FIELDS = [
    ("Input Variables", "inputVariables"),
    ("Local Variables", "localVariables"),
    ("Class Members Hook", "classMembersHook"),
    ("Start of Bar Hook", "startOfFileHook"),
    ("Pre-Condition Hook", "preConditionHook"),
    ("Long Condition", "longCondition"),
    ("Short Condition", "shortCondition"),
    ("Post-Condition Hook", "postConditionHook"),
    ("End of Bar Hook", "endOfFileHook"),
]

# Fields whose text is a "name(...)" list rather than C++ code. Inputs become
# DeclareInput calls (always double); locals become class member variables, so
# they carry an explicit C++ type.
VARIABLE_FIELDS = ("inputVariables", "localVariables")

# Type assumed for locals imported from a StrategyGeneratorTS rule, where
# EasyLanguage inferred the type and none was recorded.
LEGACY_LOCAL_TYPE = "double"


# --- C++ naming vocabulary --------------------------------------------------
# Shared by the rule editor (which rejects bad variable names) and the strategy
# writer (which sanitizes strategy names into class names).

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

CPP_KEYWORDS = frozenset({
    "alignas", "alignof", "and", "and_eq", "asm", "auto", "bitand", "bitor",
    "bool", "break", "case", "catch", "char", "char8_t", "char16_t",
    "char32_t", "class", "compl", "concept", "const", "consteval", "constexpr",
    "constinit", "const_cast", "continue", "co_await", "co_return", "co_yield",
    "decltype", "default", "delete", "do", "double", "dynamic_cast", "else",
    "enum", "explicit", "export", "extern", "false", "float", "for", "friend",
    "goto", "if", "inline", "int", "long", "mutable", "namespace", "new",
    "noexcept", "not", "not_eq", "nullptr", "operator", "or", "or_eq",
    "private", "protected", "public", "register", "reinterpret_cast",
    "requires", "return", "short", "signed", "sizeof", "static",
    "static_assert", "static_cast", "struct", "switch", "template", "this",
    "thread_local", "throw", "true", "try", "typedef", "typeid", "typename",
    "union", "unsigned", "using", "virtual", "void", "volatile", "wchar_t",
    "while", "xor", "xor_eq",
})

# Names the emitter puts in scope inside OnBarClose. A rule variable with one of
# these names is fatal: the emitter's whole-word rename turns the rule's own
# "close[0]" into "E1_close[0]", silently detaching it from the ctx alias.
RESERVED_NAMES = frozenset({
    "open", "high", "low", "close", "volume", "ctx",
    "enterLong", "enterShort", "exitLong", "exitShort",
})

# Types a local is expected to use. Anything else still generates, so the editor
# only asks for confirmation rather than refusing.
LOCAL_TYPES = ("int", "double", "bool")


def isValidIdentifier(name):
    """True if name is syntactically a C++ identifier (says nothing about
    keywords or reserved names — callers check those separately)."""
    return bool(IDENTIFIER_RE.match(name))


@dataclass
class Rule:
    name: str = ""
    type: str = RULE_TYPES[0]
    # var name -> default value (str); optimizable, always double in C++
    inputVariables: dict = field(default_factory=dict)
    # var name -> {"type": str, "init": str}; becomes a class member variable
    localVariables: dict = field(default_factory=dict)
    classMembersHook: str = ""
    startOfFileHook: str = ""
    preConditionHook: str = ""
    longCondition: str = ""
    shortCondition: str = ""
    postConditionHook: str = ""
    endOfFileHook: str = ""

    @classmethod
    def from_dict(cls, data):
        valid = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in valid}
        if "inputVariables" in kwargs:
            kwargs["inputVariables"] = _normalizeInputs(kwargs["inputVariables"])
        if "localVariables" in kwargs:
            kwargs["localVariables"] = _normalizeLocals(kwargs["localVariables"])
        return cls(**kwargs)


# --- text <-> variable-dict conversion -------------------------------------

def _splitTopLevel(text):
    """Split on commas that are not inside brackets, so a local's own
    "name(type, init)" commas do not split the list."""
    tokens, depth, current = [], 0, []
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            tokens.append("".join(current))
            current = []
        else:
            current.append(ch)
    tokens.append("".join(current))
    return [t.strip() for t in tokens if t.strip()]


def _splitNameAndBody(token):
    """"name(body)" -> ("name", "body"). A bare "name" yields a None body,
    which callers distinguish from an empty one."""
    if "(" in token and token.endswith(")"):
        name, _, rest = token.partition("(")
        return name.strip(), rest[:-1].strip()
    return token.strip(), None


# "lookback(200), minADX(15)" <-> {"lookback": "200", "minADX": "15"}
def parseInputVariables(text):
    result = {}
    for token in _splitTopLevel(text):
        name, body = _splitNameAndBody(token)
        if name:
            result[name] = body if body is not None else ""
    return result


def formatInputVariables(variables):
    return ", ".join(f"{name}({value})" for name, value in variables.items())


# "done(bool, false), ii(int, 0)" <-> {"done": {"type": "bool", "init": "false"}, ...}
# The body splits on its FIRST comma only, so an initializer may contain commas
# (e.g. "vals(int, {1, 2})"); a type that contains a comma is not supported.
def parseLocalVariables(text):
    result = {}
    for token in _splitTopLevel(text):
        name, body = _splitNameAndBody(token)
        if not name:
            continue
        if body is None:
            result[name] = {"type": "", "init": ""}
            continue
        typeText, sep, initText = body.partition(",")
        result[name] = {
            "type": typeText.strip(),
            "init": initText.strip() if sep else "",
        }
    return result


def formatLocalVariables(variables):
    parts = []
    for name, spec in variables.items():
        typeText, initText = spec.get("type", ""), spec.get("init", "")
        if typeText and initText:
            body = f"{typeText}, {initText}"
        elif initText:
            body = f", {initText}"  # only reachable while a rule is incomplete
        else:
            body = typeText
        parts.append(f"{name}({body})")
    return ", ".join(parts)


_PARSERS = {
    "inputVariables": parseInputVariables,
    "localVariables": parseLocalVariables,
}
_FORMATTERS = {
    "inputVariables": formatInputVariables,
    "localVariables": formatLocalVariables,
}


def parseField(attr, text):
    """Parse a VARIABLE_FIELDS attribute's GUI text into its dict form."""
    return _PARSERS[attr](text)


def formatField(attr, variables):
    """Render a VARIABLE_FIELDS attribute's dict back to GUI text."""
    return _FORMATTERS[attr](variables)


# --- normalization of stored/legacy data -----------------------------------

def _normalizeInputs(value):
    if isinstance(value, str):  # legacy StrategyGeneratorTS string form
        return parseInputVariables(value)
    return {str(name): str(default) for name, default in value.items()}


def _normalizeLocals(value):
    if isinstance(value, str):
        # A StrategyGeneratorTS locals string is "name(initialValue)", not
        # "name(type, init)", so it is read as untyped and given the legacy type.
        return {
            name: {"type": LEGACY_LOCAL_TYPE, "init": init}
            for name, init in parseInputVariables(value).items()
        }
    result = {}
    for name, spec in value.items():
        if isinstance(spec, dict):
            result[str(name)] = {
                "type": str(spec.get("type", "")),
                "init": str(spec.get("init", "")),
            }
        else:  # legacy dict form: name -> initial value
            result[str(name)] = {"type": LEGACY_LOCAL_TYPE, "init": str(spec)}
    return result


# Backward-compatible aliases (these helpers originally served only inputs).
parseVariables = parseInputVariables
formatVariables = formatInputVariables
