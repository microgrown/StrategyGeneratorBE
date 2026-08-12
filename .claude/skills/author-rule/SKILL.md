---
name: author-rule
description: Turn human-language descriptions of trading rules into rules/<Name>.json for StrategyGeneratorBE. Use when asked to add, write, or import one or more rules from prose — including rule text produced by another LLM. Also use when the user simply states trading conditions with no other framing, e.g. "enter long when momentum is positive and volume is below average, exit after 10 bars" or a pasted list of such conditions; in this repo that is always a request to author rules. Handles decomposing compound descriptions into atomic Entry/Exit/Switch rules, checking for behavioral duplicates against the existing corpus, keeping the C++ easy to hand-translate to EasyLanguage, and validating before saving.
---

# Authoring rules from prose

`README.md` §"Writing rules" and §"The `ctx` API" document the schema, the price
aliases, the reserved names, and what each field becomes. Read them; do not
restate them here. `rules/EL_FEATURES.md` says which EasyLanguage words have
actually been measured — §4 turns on it. This skill covers only what neither
does: how to decide *what is one rule*, how to avoid re-adding a rule the corpus
already has, and how to stay inside the EasyLanguage-translatable subset.

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

**Read the feature register before writing a condition.** Every EasyLanguage
word this corpus relies on has a row in `rules/EL_FEATURES.md`: its status, what
was measured, the probe that measured it, and the test that holds it. Check the
row for every word the rule needs.

- `VERIFIED` or `ACCEPTED` — write the rule.
- `ASSUMED` — write the rule, and say in the report which assumption it now
  depends on.
- `UNKNOWN`, or **no row at all** — **stop, and do not save the rule.**

Seventeen probes exist because every surprise below was found *after* a
MultiWalk disagreement rather than before one; `WFSafe_AvgTrueRange` alone took
four. On an unmeasured word:

1. Copy `<engineDir>/EL_Probe_Template.txt` to
   `<engineDir>/EL_<Feature>_Probe.txt` and fill it in — which rule needs the
   word, what the engine would otherwise assume, the exact chart setup, and what
   each outcome would prove. The template carries the rubric.
2. Add the row to `rules/EL_FEATURES.md` with status `UNKNOWN`, citing that
   probe.
3. Report the rule as **blocked on `<Feature>`** and hand Brian the probe.

The rule is written when the finding is recorded, not before. If several rules
in a batch need the same word, write one probe and block all of them on it. The
full loop is `<engineDir>/docs/EL_VERIFICATION.md`.

Four ways this has gone wrong before, all of them silent:

- **A MultiWalk `WFSafe_` override is a DIFFERENT function from the EL built-in
  it resembles, and it wins.** If the EasyLanguage twin calls
  `WFSafe_AvgTrueRange`, `WFSafe_SummationFC` or any other `WFSafe_` wrapper,
  the C++ must reproduce *that*, not the plain built-in. Measured: WFSafe's
  series functions keep a **rolling accumulator** — seeded with a fresh N-term
  sum on the study's first calculated bar, then
  `S = S[1] + value - value[Length]` — while EasyLanguage's own `Average` and
  `StdDev` recompute from scratch every bar. Where MultiWalk provides no
  override, follow plain EL. `rules/AtrProfitTarget.json` is the reference for
  the rolling form; `rules/BarRangeAboveStd.json` for the fresh one.

  Two details in that reference are load-bearing and easy to lose:
  the accumulator **re-seeds when the length changes** (what makes it
  "walkforward safe"), and the update is **two statements**, `S += in; S -= out;`
  — EL evaluates `S[1] + Price - Price[Length]` left to right, and folding it to
  `S += in - out` is a different rounding that lands on the other side of a
  threshold.


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
grow one — that is a cheaper and safer change than a clever hook, and a new
`ctx` built-in is a new register row held to the same standard.

Everything in this table has a clean counterpart, and a row in the register
saying how it was measured:

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

Two different kinds of "not in the table", with different answers:

- **A C++ construct with no EasyLanguage counterpart** — `std::` *containers*,
  lambdas, `auto`, ternaries, pointers/references, or a `classMembersHook` doing
  something no EasyLanguage builtin covers. Flag it in the summary. This is a
  note for Brian to weigh, not a refusal.
- **An EasyLanguage word with no register row** — that *is* a refusal. Stop and
  write the probe, as above. The difference matters: the first is a translation
  question Brian can answer by reading it, the second is a claim about what
  TradeStation does that nobody can answer without running it.

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

Once both twins are written, run the feature gate over them:

```
cd C:/Users/brian/source/repos/StrategyGeneratorBE && python lintElFeatures.py <Name>
```

Errors block the save the same way `validateRule`'s do — and the same check runs
again at Make Strategy, so a rule that slips past here will not reach the engine.

Then update `rules/CATALOG.md` with a row per rule added, and report:

- Rules written, and for each: the role, and how a compound description was split.
- Duplicates suspected, with the existing rule named.
- Anything rejected, with the reason.
- **Rules blocked on an unmeasured EasyLanguage word**, naming the feature and
  the probe written for it.
- Any `ASSUMED` register row a new rule now leans on.
- Anything outside the EasyLanguage table.
- **Deepest bar index reached**, as an expression over inputs (e.g. `lookback + 1`).
  Max Bars Back is the strategy author's job (`README.md:275`) and this is its input.

Nothing is compiled until `.\scripts\build.ps1 -Config Release` runs in the
engine repo — that rebuild is the real check on the C++.
