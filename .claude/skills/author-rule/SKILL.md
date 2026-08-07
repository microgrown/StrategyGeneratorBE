---
name: author-rule
description: Turn human-language descriptions of trading rules into rules/<Name>.json for StrategyGeneratorBE. Use when asked to add, write, or import one or more rules from prose — including rule text produced by another LLM. Also use when the user simply states trading conditions with no other framing, e.g. "enter long when momentum is positive and volume is below average, exit after 10 bars" or a pasted list of such conditions; in this repo that is always a request to author rules. Handles decomposing compound descriptions into atomic Entry/Exit/Switch rules, checking for behavioral duplicates against the existing corpus, keeping the C++ easy to hand-translate to EasyLanguage, and validating before saving.
---

# Authoring rules from prose

`README.md` §"Writing rules" and §"The `ctx` API" (lines 93–224) document the
schema, the price aliases, the reserved names, and what each field becomes. Read
them; do not restate them here. This skill covers only what they don't: how to
decide *what is one rule*, how to avoid re-adding a rule the corpus already has,
and how to stay inside the EasyLanguage-translatable subset.

Work in five passes. On a batch, finish each pass across **all** candidates
before starting the next — batch dedup matters, because two sources in one batch
will restate each other.

---

## 1. Triage — turn prose into atomic briefs

Assign a role first:

- **Entry** — when to get *in*.
- **Exit** — when to get *out* of an open position.
- **Switch** — a global condition that blocks entries and forces flat.

Then split. Ask: is this one condition, or several wearing a trenchcoat?

- Describes both getting in *and* getting out → **split** into separate rules.
- Independent conditions joined at the top level by "and also" / "plus" /
  "while" → **split**. The panes already AND entries and OR exits, so a compound
  rule is strictly *worse* than two rules: it can't be independently
  parameterized, flipped, negated, or recombined with anything else.

Two conjunctions in the corpus are legitimate, and they mark the shape of the
exception — the halves are not independently meaningful:

- **A crossing.** `MomentumChange` is
  `close[0] > close[lookback] && !(close[1] > close[lookback + 1])` — "true now,
  false last bar" is inherently two-bar. Never split a crossing.
- **Two readings of one position's history.** `ProfitProtector` is
  `ctx.MaxPositionProfit() > maxProfit && ctx.OpenPositionProfit() < retracement * ctx.MaxPositionProfit()`
  — a retracement is only meaningful as the pair, peak and now.

Reject, with the reason stated plainly:

- Needs data the engine doesn't have — fundamentals, order book, options data,
  another symbol, sub-bar data.
- Needs randomness or the wall clock. Strategies must be deterministic
  (`README.md:191`).
- References a future bar.

**Role sanity check.** An Entry that reads `ctx.OpenPositionProfit()`,
`ctx.BarsSinceEntry()`, or `ctx.EntryPrice()` is almost certainly an Exit. An
Exit that reads no position state at all is almost certainly an Entry.

**Every tunable constant becomes an input.** A magic number in a condition can't
be optimized, which defeats the tool. "Breaks out over 50 bars" → `lookback(50)`,
not a literal `50`. Only `0`, `1`, and structural constants stay literal.

**Sides.** Mirror the long condition for the short one when the rule is
directional (`>`↔`<`, highest↔lowest — see `Breakout`). Use identical text for
both when the rule is direction-agnostic — anything phrased in profit, volume,
elapsed bars, or absolute range (see `StopLoss`, `VolumeBelowAverage`). Copying
the long condition into the short slot *without* flipping a directional rule is
the single most common error here.

---

## 2. Check for duplicates

Read `rules/CATALOG.md`, then open the full JSON for anything plausible. Compare
on **behavior, not wording** — sources restate each other constantly. Three tests
catch most of it:

- **Would it fire on the same bars?** `Momentum` is `close[0] > close[lookback]`,
  so a "rate of change is positive" rule is the same rule.
- **Is it an existing rule negated or flipped?** Both are per-placement toggles
  in the GUI, so such a rule is redundant *by construction*.
- **Is it an existing rule at a fixed parameter?** `MomentumConsecutiveBars` with
  `consecutiveBars=1` is `MomentumChange`.

On a suspected match, report it and **stop for a decision**. Never silently skip
and never overwrite an existing `rules/<Name>.json`.

---

## 3. Write the JSON

Schema: `rule.py:74-98`. Filename is the rule name, PascalCase, naming the
*condition* (`VolumeBelowAverage`) not a strategy (`MyVolumeSystem`).

Conventions the corpus follows that the README doesn't spell out:

- Inputs are always `double`, so cast loop bounds: `for (int i = 0; i < (int)lookback; ++i)`.
- `volume` needs `(double)` before arithmetic — see `VolumeBelowAverage`.
- Locals persist across bars, so **reset scratch locals at the top of
  `preConditionHook`** (`atr = 0.0;` before the accumulation loop).
- Avoid identifiers that collide with common C++ names — `BarRangeAboveStd` uses
  `rrange`, not `range`.
- `<cmath>` is already included by the emitter, so `std::sqrt` is fine.

Four rules cover the range of the corpus; read the closest one before writing:

| Shape | Example |
|---|---|
| Bare condition, no state | `rules/Momentum.json` |
| Loop over a window of prices into locals | `rules/Breakout.json` |
| Mirror of an EL variable's own history | `rules/BarRangeAboveStd.json` |
| Switch with cross-bar state | `rules/MonthlyProfitTarget.json` |

---

## 4. Stay EasyLanguage-translatable — and behaviourally identical

Every rule here has a twin in `StrategyGeneratorTS/rules/<Name>.json` that emits
EasyLanguage for MultiWalk, and the two are compared unit by unit against real
MW runs. **EasyLanguage's behaviour is the specification.** Matching the formula
is not enough; match what EL actually does, including warm-up and reset timing.
Where EL's behaviour is unknown, say so and ask — do not pick the more
defensible numerical choice.

Three ways this has gone wrong before, all of them silent:

- **Warm-up.** An EL *variable* holds its initial `0` for every bar before the
  strategy's first evaluated bar, so `average(v, n)` and `stddev(v, n)` read
  zeros while the window fills. Recomputing the same statistic from `close[i]`
  instead uses bars EL never saw. Mirror the variable's history in a
  zero-initialized buffer — `rules/BarRangeAboveStd.json` is the reference.
  EL *functions* of price (`TrueRange`) are not affected: they have real
  history, so a loop over `high[i]`/`low[i]` is right for them.
- **Standard deviation is the population form** (divide by N). That is EL's
  definition; do not "fix" it to N-1.
- **Per-position state.** A position built-in resets when a new position opens,
  and a reversal opens one *without ever passing through flat*. Do not hand-roll
  this: `ctx.MaxPositionProfit()` gets it right, and a `MarketPosition() == 0`
  reset does not.

Prefer a `ctx` built-in over local emulation whenever one exists. The engine can
grow one — that is a cheaper and safer change than a clever hook.

Everything in this table has a clean counterpart:

| EasyLanguage | C++ rule field |
|---|---|
| `Close`, `Close[n]` | `close[0]`, `close[n]` |
| `AND` / `OR` / `NOT` | `&&` / `\|\|` / `!` |
| `<>` | `!=` |
| `Highest(Close, n)` / `Lowest` | loop in `preConditionHook` into a local |
| `Average(X, n)` / `StdDev(X, n)` | accumulation loop into a local — population form, and over a mirrored variable history when `X` is a variable |
| `AvgTrueRange(n)` / MW's `WFSafe_AvgTrueRange(n)` | loop into a local (`AtrProfitTarget`); the WFSafe variant is the same mean, with a length allowed to change mid-run |
| `SquareRoot`, `AbsValue`, `Mod` | `std::sqrt`, `std::fabs`, `%` or `std::fmod` |
| `MarketPosition` | `ctx.MarketPosition()` |
| `OpenPositionProfit` / `NetProfit` | `ctx.OpenPositionProfit()` / `ctx.NetProfit()` |
| `MaxPositionProfit` | `ctx.MaxPositionProfit()` — never emulate it |
| `BarsSinceEntry` / `CurrentBar` | `ctx.BarsSinceEntry()` / `ctx.CurrentBar()` |
| `EntryPrice` / `BigPointValue` | `ctx.EntryPrice()` / `ctx.BigPointValue()` |
| `Month(Date)` | `civil_from_days(day_of(ctx.Time(0))).month` |

**The `=` trap.** EasyLanguage `Close = Highest(Close, lookback)` becomes
`close[0] >= highestClose` — **`>=`, not `==`**. Float equality never holds.
`rules/Breakout.json` is the reference.

Flag, in the summary, anything with no row above: `std::` *containers*, lambdas,
`auto`, ternaries, pointers/references, or a `classMembersHook` doing something
no EasyLanguage builtin covers. This is a note for Brian to weigh, not a refusal.

---

## 5. Validate and report

`validateRule` is pure and imports headlessly — no display needed:

```
cd C:/Users/brian/source/repos/StrategyGeneratorBE && python -c "
import ruleCreationGUI as g
print(g.validateRule('Name',
  {'lookback':'20'},                                    # inputVariables
  {},                                                   # localVariables
  {'longCondition':'...', 'shortCondition':'...'}))     # code fields
"
```

Errors block the save — fix and re-run. Warnings (semicolon in a condition,
unbalanced brackets, EasyLanguage leftovers, miscased `Close`) go in the report.

Then update `rules/CATALOG.md` with a row per rule added, and report:

- Rules written, and for each: the role, and how a compound description was split.
- Duplicates suspected, with the existing rule named.
- Anything rejected, with the reason.
- Anything outside the EasyLanguage table.
- **Deepest bar index reached**, as an expression over inputs (e.g. `lookback + 1`).
  Max Bars Back is the strategy author's job (`README.md:275`) and this is its input.

Nothing is compiled until `.\scripts\build.ps1 -Config Release` runs in the
engine repo — that rebuild is the real check on the C++.
