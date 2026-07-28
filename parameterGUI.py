import tkinter as tk

import ruleIO


def _toNum(text):
    """Parse a numeric string to float, or None if blank/invalid."""
    text = text.strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def rowIterations(startStr, stopStr, stepStr):
    """Number of values a (start, stop, step) row will test.

    Returns an int, or None if the row is invalid. A blank Stop or Step, or a
    Stop equal to Start, means a single value (1 iteration)."""
    start = _toNum(startStr)
    if start is None:
        return None  # Start must be a number.

    stop, step = stopStr.strip(), stepStr.strip()
    if stop == "" or step == "":
        return 1

    nStop, nStep = _toNum(stop), _toNum(step)
    if nStop is None or nStep is None:
        return None
    if nStop == start:
        return 1
    if nStop < start or nStep <= 0:
        return None

    n = (nStop - start) / nStep
    if abs(n - round(n)) > 1e-9:  # span not divisible by step
        return None
    return int(round(n)) + 1


class parameterGUI(tk.Toplevel):
    """Edits Start/Stop/Step ranges for the input variables of a single placed
    rule instance (a RuleItem). Changes are written to ruleItem.params on Save."""

    def __init__(self, master, ruleItem):
        super().__init__(master)
        self.ruleItem = ruleItem
        self.title(f"Parameters - {ruleItem.name}")

        # Input variables (name -> default) come from the saved rule definition.
        try:
            self.inputVariables = ruleIO.loadRule(ruleItem.name).inputVariables
        except (OSError, ValueError):
            self.inputVariables = {}

        self.rows = []
        self._build()
        self._recompute()

    def _build(self):
        for col, text in enumerate(("Start", "Stop", "Step", "Iterations"), start=1):
            tk.Label(self, text=text).grid(row=0, column=col, padx=10, pady=8)

        for i, (name, default) in enumerate(self.inputVariables.items(), start=1):
            existing = self.ruleItem.params.get(name, {})
            startVar = tk.StringVar(value=existing.get("start", str(default)))
            stopVar = tk.StringVar(value=existing.get("stop", ""))
            stepVar = tk.StringVar(value=existing.get("step", ""))

            tk.Label(self, text=name).grid(row=i, column=0, sticky="e", padx=10, pady=4)
            for col, var in enumerate((startVar, stopVar, stepVar), start=1):
                tk.Entry(self, textvariable=var, width=14).grid(
                    row=i, column=col, padx=10, pady=4
                )
                var.trace_add("write", lambda *a: self._recompute())

            iterLabel = tk.Label(self, text="")
            iterLabel.grid(row=i, column=4, padx=10, pady=4)
            self.rows.append(
                {"name": name, "start": startVar, "stop": stopVar,
                 "step": stepVar, "iterLabel": iterLabel}
            )

        totalRow = len(self.inputVariables) + 1
        tk.Label(self, text="Total").grid(row=totalRow, column=0, sticky="e", padx=10, pady=8)
        self.totalLabel = tk.Label(self, text="")
        self.totalLabel.grid(row=totalRow, column=4, padx=10, pady=8)

        btnFrame = tk.Frame(self)
        btnFrame.grid(row=totalRow + 1, column=1, columnspan=4, sticky="e", padx=10, pady=10)
        self.saveBtn = tk.Button(btnFrame, text="Save", width=10, command=self._save)
        self.saveBtn.pack(side="left", padx=4)
        tk.Button(btnFrame, text="Exit", width=10, command=self.destroy).pack(
            side="left", padx=4
        )

    def _recompute(self):
        total = 1
        valid = True
        for row in self.rows:
            n = rowIterations(row["start"].get(), row["stop"].get(), row["step"].get())
            if n is None:
                row["iterLabel"].configure(text="N/A")
                valid = False
            else:
                row["iterLabel"].configure(text=str(n))
                total *= n
        self.totalLabel.configure(text=str(total) if valid else "N/A")
        self.saveBtn.configure(state="normal" if valid else "disabled")

    def _save(self):
        params = {}
        for row in self.rows:
            params[row["name"]] = {
                "start": row["start"].get().strip(),
                "stop": row["stop"].get().strip(),
                "step": row["step"].get().strip(),
            }
        self.ruleItem.params = params
        self.destroy()
