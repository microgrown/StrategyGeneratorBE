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
7. `python runBatch.py "<strategy name>"` — runs every version and aggregates
   the verdicts (or run one spec by hand:
   `bt_walkforward --spec specs/generated/<name>_v1.json`).

**Flip** swaps a placement's long and short conditions. **Negate** wraps both in
`!( ... )`. Both are per-placement; the saved rule is never modified.

## Generating without the GUI

`makeStrategy.py` is the Make Strategy button as a command: it loads a saved
template from `templates/` (or any template `.json` path) and runs the same
pipeline — header, registry `.inc` files, manifest, one spec per version, and
the template re-saved under the strategy name. Output is byte-identical to the
GUI's.

```
python makeStrategy.py "202608 BAS-12"
.\scripts\build.ps1 -Config Release          # in the engine repo
python runBatch.py s_202608_bas_12 --prune
```

Everything defaults to the template and `config.json`; flags override for that
run only and never write `config.json` back:

| Flag | Meaning |
|---|---|
| `--name NAME` | Strategy name (default: the template's `strategyName`). |
| `--max-bars-back N` | Max Bars Back (default: the template's value, then `config.json`). |
| `--engine-dir DIR` | BacktestEngine root. |
| `--spec-template PATH` | Spec JSON to clone per version. |
| `--no-save-template` | Skip re-saving `templates/<name>.json`. |

Exit code 0 on success, 1 on any error with one line on stderr. A template is
just the JSON the GUI's Save Template writes, so you can also author or edit
one by hand (or from a script) and feed it straight in.

## Running a batch

```
python runBatch.py "Momentum Clone"      # name or stem (momentum_clone) both work
```

Discovers every generated spec for the strategy (`<stem>_v1.json`, `_v2`, ...),
runs `bt_walkforward` for each version **that has no selection results yet**,
and writes the combined verdicts to `runs/<stem>/`:

| File | Contents |
|---|---|
| `runs/<stem>/selection_summary.csv` | Every version's summary rows, with a leading `run` column — filter on `tradeable` |
| `runs/<stem>/selection_report.json` | Every version's full report, keyed by run name — metrics for ranking survivors |

The engine computes selection (Monte Carlo included) inside `bt_walkforward`,
so each version pays for it exactly once. A version whose run directory already
holds `selection_report.json` is never handed to the engine again — re-invoking
`runBatch.py` on a finished batch is pure file aggregation and touches nothing.
The one exception is `--force`, which re-runs the engine for every version;
use it after editing selection thresholds in the specs, since stored verdicts
are otherwise final. `--threads N` limits the engine's cores per run (default
0 = all; versions always run sequentially).

Exit codes mirror the engine: 0 all versions ok, 1 some version failed
(details and the `run.log` path are in the summary), 2 usage/config error.

Two prerequisites: the spec template must contain a `"selection"` block
(otherwise the runs produce no verdicts and there is nothing to aggregate —
the tool warns), and the engine must be rebuilt after Make Strategy. The
engine GUI's run browser will list `runs/<stem>` with a report-format error;
that is expected — the aggregate is deliberately not readable as a run.

---

## Managing run disk space

Runs are large (hundreds of MB to GB per version). Three tools keep the
footprint manageable without ever losing a verdict. **Nothing prunes unless
you ask**: every prune is a dry run until you add `--delete`, tradeable
candidates are never touched, and the one shortcut —
`runBatch.py <strategy> --prune`, which prunes each version's rejects as
soon as that version completes (units where provably regenerable, then the
wf-sweep; ~99% of a failing family), so a large family never accumulates
more than its survivors plus one full version — only acts because you typed
the flag on that invocation. It needs a data epoch to exist and fails up
front, before any engine time is spent, when there is none; failed versions
are left unpruned so they can be re-run intact.

```
python pruneRuns.py --status                       # per-family footprint
python pruneRuns.py --prune-wf <family> --delete   # lossless: ~79% of a run
python pruneRuns.py --prune-units <family> --delete# rejected units, whole dirs
python pruneRuns.py --regen <stem>_v3              # bring pruned data back
python snapshotData.py --snapshot [SYM ...]        # archive store data (epoch)
python snapshotData.py --verify                    # detect store drift
python ingestData.py ingest --file X --symbol AD   # snapshot-then-ingest
```

The lifecycle: run → select → aggregate → `--prune-wf` (immediately safe:
`wf_results.json` is derived from the unit's `.bin` cache and manifest, and
any engine pass rebuilds it byte-identically with no re-simulation) → for cold
families, `--prune-units` (deletes rejected candidates' whole unit dirs,
optimizer caches included) → `--regen` on demand.

`--prune-units` is gated on provable reproducibility: a unit is only deletable
when its manifest records data-provenance hashes (engine manifest v4 — older
runs don't have them; use `--prune-wf` or archive those) **and** a
`snapshotData.py` epoch archives bar data matching those hashes. What was
deleted is recorded in the run's `prune_ledger.json`; `--regen` re-verifies
the live store against that ledger before invoking `bt_walkforward` — on a
mismatch it names the epoch to restore instead of running, because the engine
is deterministic (bit-identical results) only over identical data.

That is also why ingest goes through `ingestData.py`: `bt_ingest`/
`bt_resample` destructively rewrite a symbol's store directory, so the wrapper
snapshots the current state first. The engine's bulk path is protected too —
`scripts\ingest_all.ps1` snapshots every affected symbol into one epoch before
rewriting anything (and refuses to proceed if the snapshot fails;
`-SkipSnapshot` bypasses deliberately). The selection report stays a complete
record even for rejected candidates — the engine evaluates every filter for
every candidate (values recorded, marked informational after the deciding
failure; `"evaluate_all_filters": false` in a spec's selection block turns
this off) and writes their full metric set, so pruned raw data never takes
answers with it.

Note that `--regen` re-invokes the engine on that version's spec: cached units
are reused as-is, deleted ones are re-optimized, and the selection chain is
re-evaluated (deterministically, to the same verdicts). That is the one
sanctioned way to recompute — `runBatch.py`'s skip logic still never does.

---

## Writing rules

Rule code is **C++**, compiled into the engine. It is not checked until you
rebuild, so the editor validates what it can at save time.

**EasyLanguage is the specification.** Every rule here has a twin in
`StrategyGeneratorTS/rules/<Name>.json` that emits EasyLanguage for MultiWalk,
and the whole point of the engine is to reproduce MW's numbers. So a rule must
reproduce what EL *does*, not merely the formula it writes down. The two have
come apart repeatedly, always silently, and it has taken a TradeStation probe to
settle each one — `rules/EL_FEATURES.md` records which EasyLanguage features
have been measured, which have not, and what each measurement found. **Check it
before using a feature that is not already in the corpus.** Three examples, to
show the shape of the problem:

- an EL **variable** holds its initial `0` for bars before the strategy's first
  evaluated one, so `average(v, n)`/`stddev(v, n)` read zeros through warm-up
  (`rules/BarRangeAboveStd.json` mirrors that history deliberately);
- EL's standard deviation is the **population** form, dividing by N;
- position built-ins reset **per position**, and a reversal opens a new one
  without ever passing through flat — which is why `ctx.MaxPositionProfit()`
  exists and must not be hand-rolled.

Prefer a `ctx` built-in to a local emulation; the engine can grow one. After
touching a rule, `BacktestEngine/scripts/compare_el_strategy.py` diffs a
generated header against its EasyLanguage twin version by version.

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
ctx.BarsSinceEntry()        // from the oldest open lot; 0 on the fill bar, 0 while flat
ctx.BarsSinceExit()         // from the most recent exit fill; 0 before any exit
ctx.OpenPositionProfit()    // NET of the entry side's costs, marked at the last close
ctx.NetProfit()             // cumulative net P&L of all closed trades
ctx.BigPointValue()         // $ per full point per contract; NOT currency-converted

// Orders (fill at the NEXT bar's open)
ctx.EnterLong(size)  ctx.EnterShort(size)  ctx.Exit()  ctx.Exit(size)
```

**Four of those comments are measured, not assumed** — they were each wrong once
and cost a walkforward comparison to find:

- `BarsSinceEntry()` / `BarsSinceExit()` return **0**, never a `-1` sentinel.
  TradeStation returned 0 across 13,630 flat bars and across the 45 bars before
  a chart's first exit. A sentinel reads as "no entry" but *compares* as smaller
  than any threshold, so `BarsSinceEntry() >= n` disagreed with EL for every
  `n <= 0`.
- `OpenPositionProfit()` is **net of the entry side's** commission, slippage and
  accrued swap — one side, not the round turn. Every profit target, stop and
  equity switch thresholds on it, so a gross value fires targets early and stops
  late.
- `BigPointValue()` is **not** currency-converted while the profit accessors
  are. That is TradeStation's own inconsistency, preserved deliberately.

`BacktestEngine/CLAUDE.md` is the source of truth for all of these, and
`rules/EL_FEATURES.md` records which EasyLanguage features have been measured
and which have not.

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

if (enterLong)                           EnterLong(1);
if (enterShort)                          EnterShort(1);
if (exitLong   && MarketPosition() >  0) Exit();
if (exitShort  && MarketPosition() <  0) Exit();
```

**Entries are unguarded; exits are guarded.** That is statement for statement
what the EasyLanguage twin emits, and it is not a stylistic choice:

- TradeStation applies "allow up to N entries in the same direction" at **fill**
  time, after that bar's exits — not at signal time. So an entry emitted while a
  position is open still fires when an exit closes that position at the same
  fill: TS books the close and re-opens in the same direction at the same price.
  MultiWalk's own trade export does this 11 times in one NG M480 unit.
- A `MarketPosition()` guard on an entry is a **signal-time** test and is a
  different rule. Adding one suppressed that re-entry and held the BAS-2
  family's net profit within tolerance on only 11% of its 120,960
  unit-schedules.
- The cap therefore lives where the chart property does,
  `SimOptions::max_entries_per_direction` (TradeStation's default is 1, and
  MultiWalk leaves it there).

Entering the opposite side auto-reverses, matching EL `Buy`/`SellShort`. An
empty condition is skipped, since AND-true and OR-false are identities.

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
