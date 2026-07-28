import tkinter as tk


class AutocompleteName(tk.Frame):
    """An editable entry + dropdown arrow. As the user types, a floating list
    of matching names appears; selecting one fires onSelect(name).

    valuesProvider is a callable returning the current list of candidate names,
    so the dropdown always reflects what is on disk."""

    MAX_VISIBLE = 8
    _NAV_KEYS = {"Up", "Down", "Return", "Escape", "Left", "Right", "Tab",
                 "Shift_L", "Shift_R", "Control_L", "Control_R"}

    def __init__(self, parent, valuesProvider, onSelect):
        super().__init__(parent)
        self.valuesProvider = valuesProvider  # callable -> list[str]
        self.onSelect = onSelect              # callable(name)

        self.columnconfigure(0, weight=1)
        self.var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.arrow = tk.Button(self, text="▼", width=2, command=self._toggleAll)
        self.arrow.grid(row=0, column=1)

        self.popup = None
        self.listbox = None

        self.entry.bind("<KeyRelease>", self._onKey)
        self.entry.bind("<FocusOut>", lambda e: self.after(200, self._hideIfElsewhere))
        self.entry.bind("<Down>", lambda e: self._focusList())
        self.entry.bind("<Escape>", lambda e: self._hide())

    # --- public API used by the parent form ---
    def get(self):
        return self.var.get()

    def set(self, value):
        self.var.set(value)

    def refresh(self):
        """Re-filter and redraw the dropdown if it is currently open (e.g. after
        the candidate set changes underneath it)."""
        if self.popup is not None and self.popup.winfo_ismapped():
            self._show(self._matches(self.var.get()))

    # --- internals ---
    def _matches(self, typed):
        names = self.valuesProvider()
        if not typed:
            return names
        t = typed.lower()
        return [n for n in names if t in n.lower()]

    def _onKey(self, event):
        if event.keysym in self._NAV_KEYS:
            return
        self._show(self._matches(self.var.get()))

    def _toggleAll(self):
        if self.popup is not None and self.popup.winfo_ismapped():
            self._hide()
        else:
            self._show(self._matches(""))
            self.entry.focus_set()

    def _ensurePopup(self):
        if self.popup is not None:
            return
        self.popup = tk.Toplevel(self)
        self.popup.wm_overrideredirect(True)
        self.listbox = tk.Listbox(self.popup, exportselection=False)
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<ButtonRelease-1>", self._onPick)
        self.listbox.bind("<Return>", self._onPick)
        self.listbox.bind("<Escape>", lambda e: (self._hide(), self.entry.focus_set()))

    def _show(self, matches):
        if not matches:
            self._hide()
            return
        self._ensurePopup()
        self.listbox.delete(0, "end")
        for m in matches:
            self.listbox.insert("end", m)
        self.listbox.configure(height=min(self.MAX_VISIBLE, len(matches)))
        self.update_idletasks()
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        self.popup.wm_geometry(
            f"{self.entry.winfo_width()}x{self.listbox.winfo_reqheight()}+{x}+{y}"
        )
        self.popup.deiconify()
        self.popup.lift()

    def _focusList(self):
        if self.popup is not None and self.popup.winfo_ismapped() and self.listbox.size():
            self.listbox.focus_set()
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(0)
            self.listbox.activate(0)

    def _onPick(self, event=None):
        sel = self.listbox.curselection()
        idx = sel[0] if sel else self.listbox.index("active")
        value = self.listbox.get(idx)
        self.var.set(value)
        self._hide()
        self.entry.focus_set()
        self.entry.icursor("end")
        if self.onSelect:
            self.onSelect(value)

    def _hideIfElsewhere(self):
        # focus_get() can raise KeyError (e.g. 'popdown') when focus moves to a
        # widget Tk doesn't track, like a ttk Combobox's internal dropdown.
        # Any such case means focus left us, so hide.
        try:
            focused = self.focus_get()
        except KeyError:
            focused = None
        if focused in (self.entry, self.listbox):
            return
        self._hide()

    def _hide(self):
        if self.popup is not None:
            self.popup.withdraw()
