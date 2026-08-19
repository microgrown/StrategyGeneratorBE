import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

import config
import ruleIO
import templateIO
import strategyWriter
import specWriter
from strategyWriter import GenerationError
from widgets import AutocompleteName
from ruleCreationGUI import ruleCreationGUI
from parameterGUI import parameterGUI

DELIMITER = "------------------------------"

# What makes a directory recognizably the BacktestEngine repo rather than any
# other folder: it is where the generated headers have to land.
ENGINE_MARKER = os.path.join("src", "bt", "strategies")

REBUILD_COMMAND = r".\scripts\build.ps1 -Config Release"


# --- pure helpers (no widgets, so they can be unit-tested) ------------------

def engineDirProblem(path):
    """Why this path is not a usable BacktestEngine root, or None if it is."""
    path = (path or "").strip()
    if not path:
        return "Please enter the BacktestEngine root directory."
    if not os.path.isdir(path):
        return f"This directory does not exist:\n{path}"
    if not os.path.isdir(os.path.join(path, ENGINE_MARKER)):
        return (
            f"This does not look like the BacktestEngine repo:\n{path}\n\n"
            f"Expected to find {ENGINE_MARKER} inside it."
        )
    return None


def summaryText(strategyName, result, specResult):
    """The Make Strategy report. Pure so its content is testable."""
    versions = result.versionCount
    plural = "" if versions == 1 else "s"
    lines = [f"{strategyName}: {versions} version{plural} generated.", ""]

    lines.append("Header:")
    lines.append(f"    {result.headerPath}")
    lines.append("")

    lines.append("Registry entries:")
    for regName, cls in result.entries:
        lines.append(f"    {regName}  ->  {cls}")
    lines.append("")

    lines.append("Specs:")
    for path in specResult.paths:
        lines.append(f"    {path}")
    if specResult.removed:
        lines.append("")
        lines.append(f"Removed {len(specResult.removed)} spec(s) from a previous, "
                     "wider run:")
        for path in specResult.removed:
            lines.append(f"    {path}")
    lines.append("")

    # The engine throws at runtime if a series access reaches past this, and it
    # cannot be derived from arbitrary C++ rule code — so it is always shown.
    lines.append(f"Max Bars Back: {specResult.maxBarsBack}")
    lines.append("    This must cover the largest lookback any rule in this")
    lines.append("    strategy can reach. It is not computed from your rule")
    lines.append("    code: if it is too small the engine throws mid-run.")
    lines.append("")

    lines.append("Rebuild the engine to pick these up:")
    lines.append(f"    {REBUILD_COMMAND}")
    return "\n".join(lines)


class RuleItem:
    """One rule placed in a pane's list. Flip/Negate are display-level modifiers;
    the underlying saved rule is never changed. `params` holds per-instance input
    overrides set later by the Parameter GUI."""

    def __init__(self, name):
        self.name = name
        self.flipped = False
        self.negated = False
        self.params = {}

    def display(self):
        s = self.name
        if self.flipped:
            s += " (F)"
        if self.negated:
            s += " (N)"
        return s


class RulePane(tk.Frame):
    """A column for building one rule list (entries, exits, or switches).
    `ruleType` is one of Entry/Exit/Switch and fixes which rules this pane lists."""

    def __init__(self, parent, ruleType, onRemove, onMove):
        super().__init__(parent, relief="solid", bd=1)
        self.ruleType = ruleType
        self.onRemove = onRemove          # callback(self)
        self.onMove = onMove              # callback(self, delta)
        self.items = []                   # list of RuleItem | DELIMITER

        self._buildHeader()
        self._buildList()
        ttk.Separator(self, orient="horizontal").pack(fill="x")
        self._buildButtons()
        self._updateButtonStates()

    def _buildHeader(self):
        header = tk.Frame(self)
        header.pack(fill="x", padx=4, pady=4)
        tk.Label(header, text=self.ruleType, font=("TkDefaultFont", 9, "bold")).pack(
            anchor="w"
        )
        self.nameWidget = AutocompleteName(
            header,
            valuesProvider=lambda: ruleIO.listRuleNames(self.ruleType),
            onSelect=self._addRule,
        )
        self.nameWidget.pack(fill="x")

    def _buildList(self):
        listFrame = tk.Frame(self)
        listFrame.pack(fill="both", expand=True, padx=4)
        self.listbox = tk.Listbox(listFrame, width=24, height=18, exportselection=False)
        vsb = tk.Scrollbar(listFrame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=vsb.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._updateButtonStates())
        self.listbox.bind("<Delete>", self._deleteSelected)
        self.listbox.bind("<BackSpace>", self._deleteSelected)

    def _buildButtons(self):
        bf = tk.Frame(self)
        bf.pack(fill="x", padx=4, pady=4)
        bf.columnconfigure(0, weight=1)
        bf.columnconfigure(1, weight=1)

        self.flipBtn = tk.Button(bf, text="Flip", width=7, command=self._flip)
        self.negateBtn = tk.Button(bf, text="Negate", width=7, command=self._negate)
        self.paramsBtn = tk.Button(bf, text="Params", width=7, command=self._params)
        self.delimBtn = tk.Button(bf, text="Delim", width=7, command=self._addDelimiter)
        self.flipBtn.grid(row=0, column=0, padx=2, pady=2)
        self.negateBtn.grid(row=0, column=1, padx=2, pady=2)
        self.paramsBtn.grid(row=1, column=0, padx=2, pady=2)
        self.delimBtn.grid(row=1, column=1, padx=2, pady=2)

        moveFrame = tk.Frame(bf)
        moveFrame.grid(row=2, column=0, sticky="w", padx=2, pady=(6, 2))
        tk.Button(moveFrame, text="◀", width=2, command=lambda: self.onMove(self, -1)).pack(
            side="left"
        )
        tk.Button(moveFrame, text="▶", width=2, command=lambda: self.onMove(self, 1)).pack(
            side="left", padx=(2, 0)
        )
        tk.Button(bf, text="X", width=2, command=lambda: self.onRemove(self)).grid(
            row=2, column=1, sticky="e", padx=2, pady=(6, 2)
        )

    # --- list helpers ---
    def _selectedIndex(self):
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def _selectedRuleItem(self):
        idx = self._selectedIndex()
        if idx is None:
            return None
        item = self.items[idx]
        return item if isinstance(item, RuleItem) else None

    def _refreshList(self, keep=None):
        self.listbox.delete(0, "end")
        for item in self.items:
            text = item if isinstance(item, str) else item.display()
            self.listbox.insert("end", text)
        if keep is not None and 0 <= keep < len(self.items):
            self.listbox.selection_set(keep)
        self._updateButtonStates()

    def _updateButtonStates(self):
        hasRule = self._selectedRuleItem() is not None
        state = "normal" if hasRule else "disabled"
        self.flipBtn.configure(state=state)
        self.negateBtn.configure(state=state)
        self.paramsBtn.configure(state=state)

    # --- button actions ---
    def _addRule(self, name):
        self.items.append(RuleItem(name))
        self.nameWidget.set("")  # clear so the next rule can be typed
        self._refreshList()

    def _addDelimiter(self):
        self.items.append(DELIMITER)
        self._refreshList()

    def _flip(self):
        idx = self._selectedIndex()
        item = self._selectedRuleItem()
        if item is not None:
            item.flipped = not item.flipped
            self._refreshList(keep=idx)

    def _negate(self):
        idx = self._selectedIndex()
        item = self._selectedRuleItem()
        if item is not None:
            item.negated = not item.negated
            self._refreshList(keep=idx)

    def _params(self):
        item = self._selectedRuleItem()
        if item is None:
            return
        win = parameterGUI(self.winfo_toplevel(), item)
        win.transient(self.winfo_toplevel())

    def _deleteSelected(self, event=None):
        idx = self._selectedIndex()
        if idx is not None:
            del self.items[idx]
            self._refreshList(keep=min(idx, len(self.items) - 1))
        return "break"


class mainGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Strategy Generator (BacktestEngine)")
        self.geometry("1200x900")

        self.panes = []
        self._buildTop()
        self._buildToolbar()
        self._buildPaneArea()
        self._buildBottom()

        self.protocol("WM_DELETE_WINDOW", self._exit)

    def _buildTop(self):
        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)
        top.columnconfigure(1, weight=1)

        tk.Label(top, text="Strategy Name").grid(row=0, column=0, sticky="w", pady=3)
        self.strategyNameVar = tk.StringVar()
        tk.Entry(top, textvariable=self.strategyNameVar).grid(
            row=0, column=1, columnspan=2, sticky="ew", padx=8, pady=3
        )

        tk.Label(top, text="BacktestEngine Root").grid(row=1, column=0, sticky="w", pady=3)
        self.engineDirVar = tk.StringVar(value=config.get("engineDir", ""))
        tk.Entry(top, textvariable=self.engineDirVar).grid(
            row=1, column=1, sticky="ew", padx=8, pady=3
        )
        tk.Button(top, text="Browse...", command=self._browseEngineDir).grid(
            row=1, column=2, padx=(0, 8), pady=3
        )

        tk.Label(top, text="Spec Template").grid(row=2, column=0, sticky="w", pady=3)
        self.specTemplateVar = tk.StringVar(value=config.get("specTemplate", ""))
        tk.Entry(top, textvariable=self.specTemplateVar).grid(
            row=2, column=1, sticky="ew", padx=8, pady=3
        )
        tk.Button(top, text="Browse...", command=self._browseSpecTemplate).grid(
            row=2, column=2, padx=(0, 8), pady=3
        )

        tk.Label(top, text="Max Bars Back").grid(row=3, column=0, sticky="w", pady=3)
        self.maxBarsBackVar = tk.StringVar(value=config.get("maxBarsBack", ""))
        tk.Entry(top, textvariable=self.maxBarsBackVar, width=12).grid(
            row=3, column=1, sticky="w", padx=8, pady=3
        )

    def _browseEngineDir(self):
        chosen = filedialog.askdirectory(
            title="BacktestEngine root", initialdir=self.engineDirVar.get() or "."
        )
        if chosen:
            self.engineDirVar.set(os.path.normpath(chosen))

    def _browseSpecTemplate(self):
        current = self.specTemplateVar.get()
        chosen = filedialog.askopenfilename(
            title="Spec template",
            filetypes=[("Spec JSON", "*.json"), ("All files", "*.*")],
            initialdir=os.path.dirname(current) if current else ".",
        )
        if chosen:
            self.specTemplateVar.set(os.path.normpath(chosen))

    def _buildToolbar(self):
        bar = tk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(0, 8))
        tk.Button(bar, text="Create/Modify Rule", command=self._createModifyRule).pack(
            side="left", expand=True, fill="x", padx=4
        )
        tk.Button(bar, text="Add Entry Pane", command=lambda: self._addPane("Entry")).pack(
            side="left", expand=True, fill="x", padx=4
        )
        tk.Button(bar, text="Add Exit Pane", command=lambda: self._addPane("Exit")).pack(
            side="left", expand=True, fill="x", padx=4
        )
        tk.Button(bar, text="Add Switch Pane", command=lambda: self._addPane("Switch")).pack(
            side="left", expand=True, fill="x", padx=4
        )

    def _buildPaneArea(self):
        area = tk.Frame(self)
        area.pack(fill="both", expand=True, padx=10)

        self.paneCanvas = tk.Canvas(area, borderwidth=0, highlightthickness=0)
        hsb = tk.Scrollbar(area, orient="horizontal", command=self.paneCanvas.xview)
        self.paneCanvas.configure(xscrollcommand=hsb.set)
        hsb.pack(side="bottom", fill="x")
        self.paneCanvas.pack(side="top", fill="both", expand=True)

        self.paneHolder = tk.Frame(self.paneCanvas)
        self.paneCanvas.create_window((0, 0), window=self.paneHolder, anchor="nw")
        self.paneHolder.bind(
            "<Configure>",
            lambda e: self.paneCanvas.configure(scrollregion=self.paneCanvas.bbox("all")),
        )

    def _buildBottom(self):
        bottom = tk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=10)
        tk.Button(bottom, text="Save Template", width=14, command=self._saveTemplate).pack(
            side="left", padx=4
        )
        tk.Button(bottom, text="Load Template", width=14, command=self._loadTemplate).pack(
            side="left", padx=4
        )
        tk.Button(bottom, text="Exit", width=14, command=self._exit).pack(
            side="right", padx=4
        )
        tk.Button(bottom, text="Make Strategy", width=16, command=self._makeStrategy).pack(
            side="right", padx=4
        )

    # --- actions ---
    def _createModifyRule(self):
        win = ruleCreationGUI(self)
        win.transient(self)

    def _addPane(self, ruleType):
        pane = RulePane(self.paneHolder, ruleType, self._removePane, self._movePane)
        pane.pack(side="left", fill="y", padx=6, pady=4)
        self.panes.append(pane)

    def _removePane(self, pane):
        self.panes.remove(pane)
        pane.destroy()

    def _movePane(self, pane, delta):
        idx = self.panes.index(pane)
        new = idx + delta
        if new < 0 or new >= len(self.panes):
            return
        self.panes[idx], self.panes[new] = self.panes[new], self.panes[idx]
        for p in self.panes:
            p.pack_forget()
            p.pack(side="left", fill="y", padx=6, pady=4)

    # --- templates (full GUI state: strategy name + every pane and its rules) ---
    def _serializeState(self):
        panes = []
        for pane in self.panes:
            items = []
            for item in pane.items:
                if isinstance(item, str):  # DELIMITER line
                    items.append(item)
                else:
                    items.append(
                        {
                            "name": item.name,
                            "flipped": item.flipped,
                            "negated": item.negated,
                            "params": item.params,
                        }
                    )
            panes.append({"ruleType": pane.ruleType, "items": items})
        # maxBarsBack travels with the template because it belongs to the
        # strategy's lookbacks, not to this machine (unlike the two paths).
        return {
            "strategyName": self.strategyNameVar.get(),
            "maxBarsBack": self.maxBarsBackVar.get(),
            "panes": panes,
        }

    def _applyState(self, data):
        # Replace the current panes wholesale with those from the template.
        for pane in list(self.panes):
            self._removePane(pane)
        self.strategyNameVar.set(data.get("strategyName", ""))
        self.maxBarsBackVar.set(data.get("maxBarsBack", ""))
        for paneData in data.get("panes", []):
            self._addPane(paneData.get("ruleType", "Entry"))
            pane = self.panes[-1]
            for raw in paneData.get("items", []):
                if isinstance(raw, str):
                    pane.items.append(raw)
                else:
                    item = RuleItem(raw.get("name", ""))
                    item.flipped = raw.get("flipped", False)
                    item.negated = raw.get("negated", False)
                    item.params = raw.get("params", {})
                    pane.items.append(item)
            pane._refreshList()

    def _saveTemplate(self):
        name = simpledialog.askstring("Save Template", "Template name:", parent=self)
        if name is None:
            return
        name = name.strip()
        if not name:
            messagebox.showerror("Save Template", "Please enter a template name.")
            return
        if strategyWriter.ILLEGAL_NAME_CHARS.search(name):
            messagebox.showerror(
                "Save Template", 'Name cannot contain any of: \\ / : * ? " < > |'
            )
            return
        if name in templateIO.listTemplateNames() and not messagebox.askyesno(
            "Overwrite?", f"Template '{name}' already exists. Overwrite it?"
        ):
            return
        try:
            templateIO.saveTemplate(name, self._serializeState())
        except Exception as exc:
            messagebox.showerror("Save Template", f"Failed to save template:\n{exc}")
            return
        messagebox.showinfo("Save Template", f"Template '{name}' saved.")

    def _loadTemplate(self):
        names = templateIO.listTemplateNames()
        if not names:
            messagebox.showinfo("Load Template", "There are no saved templates.")
            return
        name = self._chooseTemplate(names)
        if not name:
            return
        # Guard against silently discarding in-progress work (skip if nothing to lose).
        if any(pane.items for pane in self.panes) and not messagebox.askyesno(
            "Load Template",
            "Loading a template replaces the current setup. Discard it?",
        ):
            return
        try:
            data = templateIO.loadTemplate(name)
        except Exception as exc:
            messagebox.showerror("Load Template", f"Failed to load template:\n{exc}")
            return
        self._applyState(data)

    def _chooseTemplate(self, names):
        """Modal picker: a dropdown of existing template names. Returns the chosen
        name, or None if cancelled."""
        dialog = tk.Toplevel(self)
        dialog.title("Load Template")
        dialog.transient(self)
        dialog.resizable(False, False)
        tk.Label(dialog, text="Template:").grid(row=0, column=0, padx=8, pady=8, sticky="w")
        var = tk.StringVar(value=names[0])
        box = ttk.Combobox(dialog, textvariable=var, values=names, state="readonly", width=30)
        box.grid(row=0, column=1, padx=8, pady=8)

        chosen = {"name": None}

        def ok():
            chosen["name"] = var.get()
            dialog.destroy()

        btns = tk.Frame(dialog)
        btns.grid(row=1, column=0, columnspan=2, pady=(0, 8))
        tk.Button(btns, text="Load", width=10, command=ok).pack(side="left", padx=4)
        tk.Button(btns, text="Cancel", width=10, command=dialog.destroy).pack(
            side="left", padx=4
        )

        dialog.bind("<Return>", lambda e: ok())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        box.focus_set()
        dialog.grab_set()
        self.wait_window(dialog)
        return chosen["name"]

    def _persist(self):
        """Write the machine-level settings back to config.json in one pass, so
        the file-only knobs (generatedSubdir, specOutputSubdir) survive."""
        data = config.load()
        data["engineDir"] = self.engineDirVar.get().strip()
        data["specTemplate"] = self.specTemplateVar.get().strip()
        data["maxBarsBack"] = self.maxBarsBackVar.get().strip()
        config.save(data)
        return data

    def _makeStrategy(self):
        cfg = self._persist()

        if not self.strategyNameVar.get().strip():
            messagebox.showerror("Make Strategy", "Please enter a strategy name.")
            return
        problem = engineDirProblem(cfg["engineDir"])
        if problem:
            messagebox.showerror("Make Strategy", problem)
            return
        if not self.panes:
            messagebox.showerror("Make Strategy", "Add at least one pane before generating.")
            return

        name = self.strategyNameVar.get().strip()
        try:
            # Validate the spec inputs BEFORE generate() writes the header, so a
            # bad template or Max Bars Back cannot leave a header with no specs.
            specWriter.loadTemplate(cfg.get("specTemplate"))
            specWriter.parseMaxBarsBack(cfg.get("maxBarsBack"))
            result = strategyWriter.generate(name, self.panes, cfg)
            specResult = specWriter.writeSpecs(name, result.versionCount, cfg)
        except GenerationError as exc:
            messagebox.showerror("Make Strategy", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Make Strategy", f"Failed to generate strategy:\n{exc}")
            return

        saved = self._autoSaveTemplate(name)
        text = summaryText(name, result, specResult)
        if not saved:
            text += "\n\n(Template not saved.)"
        self._showSummary(text)

    def _showSummary(self, text):
        """Scrollable, selectable report — paths are long and worth copying."""
        dialog = tk.Toplevel(self)
        dialog.title("Make Strategy")
        dialog.transient(self)

        frame = tk.Frame(dialog)
        frame.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        txt = tk.Text(frame, width=100, height=24, wrap="none")
        vsb = tk.Scrollbar(frame, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=vsb.set)
        txt.insert("1.0", text)
        txt.configure(state="disabled")
        txt.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def copyRebuild():
            self.clipboard_clear()
            self.clipboard_append(REBUILD_COMMAND)

        btns = tk.Frame(dialog)
        btns.pack(fill="x", padx=8, pady=8)
        tk.Button(btns, text="Close", width=12, command=dialog.destroy).pack(
            side="right", padx=4
        )
        tk.Button(btns, text="Copy rebuild command", width=22, command=copyRebuild).pack(
            side="right", padx=4
        )

        dialog.grab_set()
        self.wait_window(dialog)

    def _autoSaveTemplate(self, name):
        """Save the current setup as a template named after the strategy, warning
        before overwriting an existing one. Returns True if it was saved. The name
        is already validated by the caller (non-empty, no illegal chars)."""
        if name in templateIO.listTemplateNames() and not messagebox.askyesno(
            "Overwrite template?",
            f"A template named '{name}' already exists. Overwrite it?",
        ):
            return False
        try:
            templateIO.saveTemplate(name, self._serializeState())
        except Exception as exc:
            messagebox.showerror("Make Strategy", f"Failed to save template:\n{exc}")
            return False
        return True

    def _exit(self):
        self._persist()
        self.destroy()


if __name__ == "__main__":
    mainGUI().mainloop()
