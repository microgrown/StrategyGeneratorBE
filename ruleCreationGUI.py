import re
import tkinter as tk
from tkinter import ttk, messagebox

import ruleIO
from widgets import AutocompleteName
from rule import (
    CPP_KEYWORDS,
    LOCAL_TYPES,
    RESERVED_NAMES,
    RULE_TYPES,
    TEXT_FIELDS,
    VARIABLE_FIELDS,
    Rule,
    formatField,
    isValidIdentifier,
    parseField,
)

# Characters that are illegal in Windows filenames (rule name becomes a filename).
_ILLEGAL_NAME_CHARS = re.compile(r'[\\/:*?"<>|]')

# The two fields that must be C++ expressions, not statements.
_CONDITION_FIELDS = ("longCondition", "shortCondition")

# EasyLanguage control-flow words that are not C++. They flag a StrategyGeneratorTS
# rule pasted in (or imported) without being rewritten. These words open and close
# EasyLanguage blocks, so they are never a call: the lookaheads keep C++ iterator
# calls like v.begin() / v.end() from tripping the check.
_EASYLANGUAGE_RE = re.compile(
    r"(?<![A-Za-z0-9_.])(?:begin|then)(?![A-Za-z0-9_]|\s*\()"
    r"|(?<![A-Za-z0-9_.])end\s*;",
    re.IGNORECASE,
)

# EasyLanguage is case-insensitive, so TS rules write "Close[0]". C++ is not, and
# the emitter's aliases are lowercase, so any other casing fails the build.
_MISCASED_RESERVED_RE = re.compile(
    r"(?<![A-Za-z0-9_.])(?:" + "|".join(sorted(RESERVED_NAMES)) + r")(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

# Bracket pairs checked for balance in code fields.
_BRACKETS = {"(": ")", "[": "]", "{": "}"}

# Values that reveal a local typed "double" is really a bool (legacy import).
_BOOL_LITERALS = ("true", "false")

_LABELS = dict((attr, label) for label, attr in TEXT_FIELDS)


# --- validation (pure; no widgets, so it is unit-testable) ------------------

def validateName(name):
    """Errors for the rule's name, which becomes the JSON filename."""
    if not name:
        return ["Name is required."]
    if _ILLEGAL_NAME_CHARS.search(name):
        return ['Name cannot contain any of: \\ / : * ? " < > |']
    return []


def _nameErrors(name, what):
    if not isValidIdentifier(name):
        return [f"{what} '{name}' is not a valid C++ name "
                "(letters, digits and _ only, not starting with a digit)."]
    if name in CPP_KEYWORDS:
        return [f"{what} '{name}' is a C++ keyword."]
    if name in RESERVED_NAMES:
        return [f"{what} '{name}' is reserved by the generator "
                "(" + ", ".join(sorted(RESERVED_NAMES)) + ")."]
    return []


def validateVariables(inputVariables, localVariables):
    """Errors that would make the generated C++ invalid or silently wrong.
    Inputs and locals share one namespace because the emitter renames them
    together."""
    errors = []

    for name, default in inputVariables.items():
        errors += _nameErrors(name, "Input variable")
        if not default:
            errors.append(f"Input variable '{name}' needs a default value.")
        else:
            try:
                float(default)
            except ValueError:
                errors.append(
                    f"Input variable '{name}' default '{default}' is not a number."
                )

    for name, spec in localVariables.items():
        errors += _nameErrors(name, "Local variable")
        if not spec.get("type"):
            errors.append(f"Local variable '{name}' needs a type, e.g. {name}(double, 0).")
        if not spec.get("init"):
            errors.append(f"Local variable '{name}' needs an initial value.")

    clash = sorted(set(inputVariables) & set(localVariables))
    if clash:
        errors.append("These names are both an input and a local: " + ", ".join(clash))

    return errors


def variableWarnings(localVariables):
    """Non-fatal (title, message) pairs about local variable types."""
    warnings = []

    unusual = [
        f"{name} ({spec['type']})"
        for name, spec in localVariables.items()
        if spec.get("type") and spec["type"] not in LOCAL_TYPES
    ]
    if unusual:
        warnings.append((
            "Unusual local type",
            "These locals do not use one of " + "/".join(LOCAL_TYPES) + ": "
            + ", ".join(unusual)
            + ".\n\nThey will be emitted as written, so the type must be valid C++.",
        ))

    # Rules imported from StrategyGeneratorTS get every local typed double,
    # because EasyLanguage recorded no type. A bool initializer gives it away.
    legacy = [
        name
        for name, spec in localVariables.items()
        if spec.get("type") == "double" and spec.get("init", "").lower() in _BOOL_LITERALS
    ]
    if legacy:
        warnings.append((
            "Local typed double holds a bool",
            "These locals are typed double but initialized to true/false: "
            + ", ".join(legacy)
            + ".\n\nAn imported StrategyGeneratorTS rule types every local double; "
            "these are probably meant to be bool.",
        ))

    return warnings


def _unbalanced(text):
    """True if the bracket pairs in text do not nest and close cleanly.
    String and char literals are not excluded, hence a warning rather than an
    error."""
    stack = []
    closers = {v: k for k, v in _BRACKETS.items()}
    for ch in text:
        if ch in _BRACKETS:
            stack.append(ch)
        elif ch in closers:
            if not stack or stack.pop() != closers[ch]:
                return True
    return bool(stack)


def codeWarnings(codeFields):
    """Non-fatal (title, message) pairs about the C++ code fields.
    codeFields maps a Rule attribute to its text."""
    warnings = []

    semis = [
        _LABELS[attr]
        for attr in _CONDITION_FIELDS
        if ";" in codeFields.get(attr, "")
    ]
    if semis:
        warnings.append((
            "Semicolon in condition",
            "Semicolons found in: " + ", ".join(semis)
            + ".\n\nLong/Short conditions are combined into a larger C++ expression "
            "and must not contain semicolons — the generated header will not compile.",
        ))

    unbalanced = [
        _LABELS[attr] for attr, text in codeFields.items() if _unbalanced(text)
    ]
    if unbalanced:
        warnings.append((
            "Unbalanced brackets",
            "Brackets do not balance in: " + ", ".join(unbalanced)
            + ".\n\nThis will fail the engine rebuild.",
        ))

    legacy = sorted({
        m.group(0)
        for text in codeFields.values()
        for m in _EASYLANGUAGE_RE.finditer(text)
    })
    if legacy:
        warnings.append((
            "EasyLanguage syntax",
            "These EasyLanguage words appear in the code: " + ", ".join(legacy)
            + ".\n\nRule code must be C++ — an imported StrategyGeneratorTS rule "
            "needs its hooks and conditions rewritten.",
        ))

    miscased = sorted({
        m.group(0)
        for text in codeFields.values()
        for m in _MISCASED_RESERVED_RE.finditer(text)
        if m.group(0) not in RESERVED_NAMES
    })
    if miscased:
        warnings.append((
            "Wrong case for a generator name",
            "These look like generator names spelled with the wrong case: "
            + ", ".join(miscased)
            + ".\n\nC++ is case-sensitive; the emitted names are "
            + ", ".join(sorted(RESERVED_NAMES)) + ".",
        ))

    return warnings


def validateRule(name, inputVariables, localVariables, codeFields):
    """(errors, warnings) for a whole rule. Errors block the save; each warning
    is a (title, message) pair the caller confirms."""
    errors = validateName(name) + validateVariables(inputVariables, localVariables)
    warnings = variableWarnings(localVariables) + codeWarnings(codeFields)
    return errors, warnings


class ruleCreationGUI(tk.Toplevel):
    COLLAPSED_HEIGHT = 4
    EXPANDED_HEIGHT = 14

    def __init__(self, master=None):
        super().__init__(master)
        self.title("Rule Creation")
        self.geometry("700x900")

        self.textWidgets = {}
        self._buildScrollableBody()
        self._buildFields()

    # A canvas-backed scrollable frame so the tall form fits any screen.
    def _buildScrollableBody(self):
        outer = tk.Frame(self)
        outer.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(outer, borderwidth=0, highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.body = tk.Frame(self.canvas)
        self._bodyWindow = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self._bodyWindow, width=e.width),
        )
        # Scope the wheel to this window only (so it doesn't hijack other windows).
        self.bind(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units"),
        )

    def _buildFields(self):
        b = self.body
        b.columnconfigure(1, weight=1)
        row = 0

        # Name: type-ahead autocomplete over existing rules of the selected type;
        # select to prepopulate. The provider reads the current Type each keystroke.
        tk.Label(b, text="Name").grid(row=row, column=0, sticky="w", padx=8, pady=6)
        self.nameWidget = AutocompleteName(
            b, lambda: ruleIO.listRuleNames(self.typeVar.get()), self._loadRule
        )
        self.nameWidget.grid(row=row, column=1, sticky="ew", padx=8, pady=6)
        row += 1

        # Type
        tk.Label(b, text="Type").grid(row=row, column=0, sticky="w", padx=8, pady=6)
        self.typeVar = tk.StringVar(value=RULE_TYPES[0])
        typeBox = ttk.Combobox(
            b, textvariable=self.typeVar, values=list(RULE_TYPES), state="readonly"
        )
        typeBox.grid(row=row, column=1, sticky="ew", padx=8, pady=6)
        # Re-filter the open Name dropdown the instant the Type changes.
        typeBox.bind("<<ComboboxSelected>>", lambda e: self.nameWidget.refresh())
        row += 1

        for label, key in TEXT_FIELDS:
            row = self._buildTextField(b, row, label, key)

        btnFrame = tk.Frame(b)
        btnFrame.grid(row=row, column=0, columnspan=2, sticky="e", padx=8, pady=12)
        tk.Button(btnFrame, text="Save", width=10, command=self._save).pack(
            side="left", padx=4
        )
        tk.Button(btnFrame, text="Exit", width=10, command=self.destroy).pack(
            side="left", padx=4
        )

    # Label + scrollable Text that grows while focused and shrinks when it loses focus.
    def _buildTextField(self, parent, row, label, key):
        tk.Label(parent, text=label).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(10, 2)
        )
        frame = tk.Frame(parent)
        frame.grid(row=row + 1, column=0, columnspan=2, sticky="ew", padx=8)
        frame.columnconfigure(0, weight=1)

        txt = tk.Text(frame, height=self.COLLAPSED_HEIGHT, wrap="word", undo=True)
        vsb = tk.Scrollbar(frame, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=vsb.set)
        txt.grid(row=0, column=0, sticky="ew")
        vsb.grid(row=0, column=1, sticky="ns")

        txt.bind("<FocusIn>", lambda e, t=txt: t.configure(height=self.EXPANDED_HEIGHT))
        txt.bind("<FocusOut>", lambda e, t=txt: t.configure(height=self.COLLAPSED_HEIGHT))
        txt.bind("<Escape>", self._collapseText)
        # Let the wheel scroll the text itself (not the page) when hovering a box.
        txt.bind("<MouseWheel>", self._textWheel)

        self.textWidgets[key] = txt
        return row + 2

    @staticmethod
    def _textWheel(event):
        event.widget.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    def _collapseText(self, event):
        event.widget.configure(height=self.COLLAPSED_HEIGHT)
        return "break"

    def _loadRule(self, name):
        rule = ruleIO.loadRule(name)
        self.typeVar.set(rule.type if rule.type in RULE_TYPES else RULE_TYPES[0])
        for _, key in TEXT_FIELDS:
            value = getattr(rule, key)
            if key in VARIABLE_FIELDS:
                value = formatField(key, value)
            widget = self.textWidgets[key]
            widget.delete("1.0", "end")
            widget.insert("1.0", value)

    def _fieldText(self, key):
        return self.textWidgets[key].get("1.0", "end-1c")

    def _save(self):
        name = self.nameWidget.get().strip()
        inputVars = parseField("inputVariables", self._fieldText("inputVariables"))
        localVars = parseField("localVariables", self._fieldText("localVariables"))
        codeFields = {
            key: self._fieldText(key)
            for _, key in TEXT_FIELDS
            if key not in VARIABLE_FIELDS
        }

        errors, warnings = validateRule(name, inputVars, localVars, codeFields)
        if errors:
            messagebox.showerror("Error", "\n".join(errors))
            return
        for title, message in warnings:
            if not messagebox.askyesno(title, message + "\n\nSave anyway?"):
                return

        if name in ruleIO.listRuleNames():
            if not messagebox.askyesno(
                "Overwrite?", f"Rule '{name}' already exists. Overwrite it?"
            ):
                return

        rule = Rule(name=name, type=self.typeVar.get())
        for _, key in TEXT_FIELDS:
            text = self._fieldText(key)
            setattr(rule, key, parseField(key, text) if key in VARIABLE_FIELDS else text)
        ruleIO.saveRule(rule)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    win = ruleCreationGUI(root)
    win.protocol("WM_DELETE_WINDOW", win.destroy)
    win.wait_window()
    root.destroy()
