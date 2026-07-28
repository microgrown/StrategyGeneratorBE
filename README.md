# StrategyGeneratorBE

Builds BacktestEngine strategies combinatorially from reusable Entry/Exit/Switch
rules. It is the [BacktestEngine](../BacktestEngine) analog of
[StrategyGeneratorTS](../StrategyGeneratorTS), which did the same job for
TradeStation: same pane / delimiter / flip / negate workflow, but it emits **C++
strategy classes** instead of EasyLanguage, and there is no MultiWalk export.

You write small rules once. The generator crosses them into every combination
you asked for, emits one `bt::Strategy` subclass per combination, registers them
all, and clones a walkforward spec for each. Then you rebuild the engine.

```
python main.py
```

---

## Setup

`config.json` holds the machine-level settings. The first three are also fields
in the main window; the last two are file-only knobs.

| Key | Meaning |
|---|---|
| `engineDir` | BacktestEngine repo root. Must contain `src/bt/strategies`. |
| `specTemplate` | An existing spec JSON to clone per version. |
| `maxBarsBack` | Blank leaves the template's value alone. |
| `generatedSubdir` | Where headers are written. Default `src/bt/strategies/generated`. |
| `specOutputSubdir` | Where specs are written. Default `specs/generated`. |

The engine needs a one-time change (already committed) so `registry.cpp`
includes the two generated `.inc` files. See PLAN.md §1.

## The workflow

1. **Create/Modify Rule** — write a rule once; it is saved to `rules/<name>.json`.
2. **Add panes** — one per rule role. Drop rules into them.
3. **Delim** — a delimiter splits a pane into alternative *groups*. The set of
   generated versions is the cross-product of every pane's groups, so two panes
   with two groups each produce four versions. An empty group is legal and means
   "contribute nothing".
4. **Params** — per-placement Start/Stop/Step for a rule's inputs. Blank Stop or
   Step pins the input to a single value.
5. **Make Strategy** — writes the header, updates the registry, writes one spec
   per version, and auto-saves the setup as a template named after the strategy.
6. **Rebuild the engine** — nothing takes effect until you do:
   ```
   .\scripts\build.ps1 -Config Release
   ```
7. `bt_walkforward --spec specs/generated/<name>_v1.json`

**Flip** swaps a placement's long and short conditions. **Negate** wraps both in
`!( ... )`. Both are per-placement; the saved rule is never modified.

---

## Writing rules

Rule code is **C++**, compiled into the engine. It is not checked until you
rebuild, so the editor validates what it can at save time.

### Fields

| Field | Becomes |
|---|---|
| Input Variables | `DeclareInput` in the constructor; optimizable |
| Local Variables | Class members — they persist across bars |
| Class Members Hook | Raw C++ at class scope (helper methods) |
| Start of Bar Hook | Top of `OnBarClose` |
| Pre-Condition Hook | Before this rule's condition lines |
| Long / Short Condition | A C++ **expression** |
| Post-Condition Hook | After this rule's condition lines |
| End of Bar Hook | Bottom of `OnBarClose`, after orders are placed |

### Conditions are expressions; hooks are statements

A condition is pasted into a larger expression, so it must have **no semicolon**
and no statements:

```cpp
close[0] > close[Length]          // yes
close[0] > close[Length];         // no - will not compile
```

Hooks are the opposite: raw C++ statements, semicolons and all.

### Price aliases

These are in scope at the top of every `OnBarClose`:

```cpp
open  high  low  close  volume        // EL-indexed: [0] is the just-closed bar
ctx                                   // the Context itself, always available
```

`close[1]` is the bar before last. Index further back than **Max Bars Back** and
the engine throws at runtime.

### Hooks run every bar

There is no one-time init hook — the whole body runs per bar, as in EasyLanguage.
For one-time setup use the bar counter:

```cpp
if (ctx.CurrentBar() == 1) { highWater = 0.0; }
```

### Input variables

`name(default)`, e.g. `Length(20)`. Always `double` in C++ (that is what the
optimizer grid stores), so using one as a subscript truncates — which is fine and
intended:

```cpp
close[Length]        // Length is a double; the narrowing is deliberate
```

The default is used when a placement has no Params row.

### Local variables

`name(type, initial)`, e.g. `ii(int, 0)`, `done(bool, false)`. They become class
members, so **they keep their value across bars** (like EL `variables:`). Reset
them yourself if you want per-bar scratch space. `int`/`double`/`bool` are the
expected types; anything else saves after a confirmation.

### Class Members Hook

The engine has no indicator library, so a rule needing something like ATR must
define its own helper. That is only expressible at class scope:

```cpp
double AvgRange(Context& ctx, int n) const {
    double sum = 0.0;
    for (int i = 0; i < n; ++i) sum += ctx.high[i] - ctx.low[i];
    return sum / n;
}
```

### Names are prefixed, so some are reserved

Every input and local is renamed with the placement's prefix (`E1_`, `X1_`,
`S1_`), which is what lets the same rule appear twice in one strategy. That means
a variable named `close` would turn your own `close[0]` into `E1_close[0]` and
silently detach it from the alias. So these names are rejected outright:

```
open  high  low  close  volume  ctx  enterLong  enterShort  exitLong  exitShort
```

C++ keywords are rejected too. The rename is **case-sensitive** — `Close` is a
legal variable name, but it will not compile against the lowercase alias, so the
editor warns about it.

### Strategies must be deterministic

One fresh strategy object per optimizer iteration, run in parallel. No statics,
no globals, no clock, no RNG.

---

## The `ctx` API

```cpp
// Price series, EL-indexed
ctx.open[n]  ctx.high[n]  ctx.low[n]  ctx.close[n]  ctx.volume[n]
ctx.Time(n)                 // bar close timestamp
ctx.CurrentBar()            // 1 on the first OnBarClose call

// Position state
ctx.MarketPosition()        // +1 long, 0 flat, -1 short
ctx.CurrentContracts()      // total open contracts
ctx.EntryPrice()            // contract-weighted average; 0.0 when flat
ctx.EntryPrice(lot)         // per entry, lot 0 = oldest open (FIFO)
ctx.LotCount()
ctx.BarsSinceEntry()        // from the oldest open lot; -1 when flat
ctx.BarsSinceExit()         // from the most recent exit fill; -1 if none
ctx.OpenPositionProfit()    // gross of costs, marked at the last close
ctx.NetProfit()             // cumulative net P&L of all closed trades
ctx.BigPointValue()         // $ per full point per contract

// Orders (fill at the NEXT bar's open)
ctx.EnterLong(size)  ctx.EnterShort(size)  ctx.Exit()  ctx.Exit(size)
```

You rarely call the order methods yourself — the generator emits them from your
conditions.

---

## What gets generated

Per Make Strategy click, into `engineDir`:

| File | Contents |
|---|---|
| `src/bt/strategies/generated/gen_<name>.h` | One class per version |
| `src/bt/strategies/generated/headers.inc` | One `#include` per generated header |
| `src/bt/strategies/generated/registry.inc` | One registry entry per version |
| `src/bt/strategies/generated/manifest.json` | Which entries belong to which header |
| `specs/generated/<name>_v<n>.json` | One spec per version |

A strategy named `Momentum Clone` yields class `Gen_Momentum_Clone_V1`, registry
name `"Momentum Clone V1"`, and spec/run name `momentum_clone_v1` — so results
land in `runs/momentum_clone_v1/`.

Several strategies coexist: each run replaces only its own batch and prunes
batches whose header you deleted by hand. Everything under `generated/` is
committed to the engine repo, so a run's results tie to exact strategy code.

### How versions are combined

Within a version, per bar:

```
enterLong  = true,  enterShort = true
exitLong   = false, exitShort  = false

Entries:   enterLong = enterLong && (condition)      // AND
Exits:     exitLong  = exitLong  || (condition)      // OR
Switches:  enterLong = enterLong && !(condition)     // block entries
           exitLong  = exitLong  ||  (condition)     // and force an exit

if (enterLong  && MarketPosition() <= 0) EnterLong(1);
if (enterShort && MarketPosition() >= 0) EnterShort(1);
if (exitLong   && MarketPosition() >  0) Exit();
if (exitShort  && MarketPosition() <  0) Exit();
```

The `MarketPosition()` guards reproduce TradeStation's no-pyramiding default
(this engine would otherwise pyramid); entering the opposite side auto-reverses,
matching EL `Buy`/`SellShort`. An empty condition is skipped, since AND-true and
OR-false are identities.

**Carried-over quirk:** a version with no entry rules enters every bar. That is
StrategyGeneratorTS behavior, kept deliberately for parity, and the generated
header says so in a comment.

## Max Bars Back is your responsibility

It must cover the largest lookback any rule in the strategy can reach, or the
engine throws mid-run. It cannot be computed from arbitrary C++, so the generator
does not try — it just shows the effective value in the summary. Blank leaves the
template's value; the engine's own default is 50.

## Tests

```
python -m unittest discover -s tests -t .
```

`tests/__init__.py` must exist — Python 3.14 refuses a non-importable start
directory.
