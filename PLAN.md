# StrategyGeneratorBE — Implementation Plan

## Context

Brian replaced the MultiWalk/TradeStation test platform with a personal C++ backtest engine (`C:\Users\brian\source\repos\BacktestEngine`). The existing rule-combination tool, `C:\Users\brian\source\repos\StrategyGeneratorTS` (Python 3 + Tkinter, stdlib only — "TS" = TradeStation), generates EasyLanguage strategies combinatorically from reusable Entry/Exit/Switch rules. This project builds its analog for BacktestEngine in the empty repo `C:\Users\brian\source\repos\StrategyGeneratorBE`: same pane/delimiter/flip/negate composition workflow, but emitting **C++ strategy classes** (plus registry entries and spec JSONs) instead of EasyLanguage, with **no MultiWalk export** ("Make MW Inputs" and everything it drags in is dropped).

Key architectural fact: BacktestEngine has no strategy file format. A strategy is a header-only C++ class subclassing `bt::Strategy` (`src/bt/sim/strategy.h`), declaring optimizable inputs via `DeclareInput(name, start, stop, step)` in the constructor and implementing `void OnBarClose(Context& ctx)`. Strategies are registered by name in a compile-time map in `src/bt/strategies/registry.cpp` and require a rebuild (`.\scripts\build.ps1 -Config Release`).

**User decisions (fixed):**
1. Integration via a **generated-registry include**: one-time engine change so `registry.cpp` includes generator-written `.inc` files; the generator writes directly into the engine tree.
2. Rule code is **C++ with EL-style aliases**: emitted `const auto& close = ctx.close;` etc. at the top of `OnBarClose`, so conditions read `close[0] > close[lookback]`. Conditions are expressions (no `;`); hooks are raw C++ statements. `ctx` also directly usable.
3. **Explicit local variable types**: Local Variables syntax becomes `name(type, initial)`, e.g. `ii(int, 0), done(bool, false)`; locals become class members (persist across bars = EL `variables:`).
4. **Spec JSONs emitted too**: generator clones a user-chosen template spec per version, filling `name`/`strategy` (and optionally `max_bars_back`).

Verified engine facts the design relies on:
- `registry.cpp:15-17` — map built in a braced initializer inside `registry()`; an `#include` inside the initializer is legal, trailing commas are legal, and an empty/comment-only `.inc` compiles.
- `grid.cpp:25` — `stop == start` returns 1 iteration *before* the `step == 0` check → fixed inputs emit as `DeclareInput(name, v, v, 0)`.
- `CMakeLists.txt:67` — `target_include_directories(btcore PUBLIC src)` → generated headers under `src/bt/strategies/generated/` need **no CMake changes** (compiled only into the `registry.cpp` TU; Ninja tracks header deps automatically).
- Engine `EnterLong` while long **pyramids**; TS no-pyramiding must be reproduced with `MarketPosition()` guards (as in `momentum_reversal.h`). `EnterLong` while short auto-reverses (matches TS `Buy`).
- Determinism constraint: no statics/globals/clock/RNG in strategies; fresh strategy object per optimizer iteration.

## Repo layout (StrategyGeneratorBE)

```
main.py                copy verbatim from StrategyGeneratorTS
mainGUI.py             copy; remove MW; rework top form + Make Strategy
ruleCreationGUI.py     copy; C++ validation
parameterGUI.py        copy verbatim (rowIterations already matches grid.cpp rules)
rule.py                adapt (new fields, paren-aware parser, typed locals)
ruleIO.py              copy verbatim
templateIO.py          copy verbatim
widgets.py             copy verbatim (AutocompleteName)
config.py              copy verbatim
config.json            new keys
strategyWriter.py      REWRITE: ported combinatorics + C++ emitter + manifest/.inc writer
specWriter.py          NEW: per-version spec cloning
rules/  templates/     created on demand (same as TS)
tests/                 test_rule.py, test_strategyWriter.py, test_specWriter.py
```

## 1. One-time BacktestEngine change — ✅ DONE (commit `c162d6a` on `master`)

Completed 2026-07-27. All sub-items below are in place; `.\scripts\build.ps1 -Config Release -Test` passes 494/494. Do not redo this step.

**Validated by smoke test (throwaway strategy, since reverted):** a *populated* `registry.inc` compiles inside the braced initializer under MSVC, and `bt_optimize` reported the entry as registered (`known: MomentumReversal, SmokeTest V1`) — confirming both the include mechanism and that registry names containing spaces work. The smoke test also produced exactly the anticipated `C4244` double→int narrowing warning on `close[E1_len]`, confirming §3's `#pragma warning(disable: 4244)` in generated headers is required.

- Create `src/bt/strategies/generated/` with two committed comment-only stubs: `headers.inc`, `registry.inc`. (Committed stubs — not `__has_include` — so the header dependency exists from build one and later generator runs trigger a `registry.cpp` rebuild.)
- `registry.cpp`: add `#include "bt/strategies/generated/headers.inc"` at file scope (after the momentum_reversal include) and `#include "bt/strategies/generated/registry.inc"` inside the map's braced initializer (after the MomentumReversal row).
- Create `specs/generated/` (with a `.gitkeep` or just let the generator create it).
- Git policy: **track everything in `generated/`** (headers, incs, manifest) — small files, and versioning ties run results to exact strategy code.
- Verify `.\scripts\build.ps1 -Config Release -Test` passes with empty stubs.

## 2. rule.py

```python
RULE_TYPES = ("Entry", "Exit", "Switch")   # unchanged
TEXT_FIELDS = [
    ("Input Variables",     "inputVariables"),    # name(default) — doubles, optimizable
    ("Local Variables",     "localVariables"),    # name(type, initial) — persist across bars
    ("Class Members Hook",  "classMembersHook"),  # NEW: raw C++ at class scope (helper methods)
    ("Start of Bar Hook",   "startOfFileHook"),   # label renamed; JSON key kept for familiarity
    ("Pre-Condition Hook",  "preConditionHook"),
    ("Long Condition",      "longCondition"),
    ("Short Condition",     "shortCondition"),
    ("Post-Condition Hook", "postConditionHook"),
    ("End of Bar Hook",     "endOfFileHook"),
]
```

- `localVariables` value shape: `{"type": str, "init": str}`. `from_dict` tolerates the TS legacy forms (string field; locals `name -> value` → `{"type": "double", "init": value}`).
- `parseVariables` rewritten **paren-aware** (split on commas at paren depth 0 — the TS `text.split(",")` breaks on `ii(int, 0)`); locals split the paren contents on first comma into (type, init). `formatVariables` gains the typed-locals form.
- `classMembersHook` justification: no engine-side indicator library, so rules needing e.g. ATR must define a private helper method — only expressible at class scope.
- Hooks run **every bar** (as in EL, where the whole file body runs per bar); one-time init idiom is `if (ctx.CurrentBar() == 1) { ... }`.

## 3. strategyWriter.py — combinatorics ported, emitter rewritten

**Ported nearly verbatim from TS** (`C:\Users\brian\source\repos\StrategyGeneratorTS\strategyWriter.py`): `ILLEGAL_NAME_CHARS`, `_templateGroups` (delimiter split; empty group = no-op), `_enumerateVersions` (`itertools.product` across panes, bucketed into entries/exits/switches), `_occurrences`, `_indent`, `_Occ`. **Dropped**: everything MultiWalk (lines ~398–689, `_Occ.mwVars`, `_ensureSemicolons` — hooks are raw C++ now).

**Changes to the ported machinery:**
- Prefixes are per-occurrence within a version only: `E{n}_`, `X{n}_`, `S{n}_` (per-version classes eliminate cross-version collisions; no `V{v}` part).
- `_renameVars` becomes **case-sensitive** (C++), whole-word `(?<![A-Za-z0-9_])name(?![A-Za-z0-9_])`, longest-name-first, over inputs+locals as one namespace, applied to all code fields including `classMembersHook`.
- Negate wraps `!( ... )`; flip still swaps long/short text before renaming; empty conditions skipped (AND-true / OR-false identity).

**Generated output — one header per Make Strategy click, one class per version:**
- File: `<engineDir>/src/bt/strategies/generated/gen_<sanitized_lower>.h`; class `Gen_<Sanitized>_V<N>`; registry name `"<Strategy Name> V<N>"` (raw name is a fine map key and spec `strategy` value).
- `sanitizeIdentifier`: `re.sub(r"[^0-9A-Za-z]+", "_", name)`, strip edge `_`, prefix if starts with digit/empty, reject C++ keywords.
- Inputs → `DeclareInput` from per-placement `item.params`:
  - valid start/stop/step row → `DeclareInput(pfx+name, start, stop, step)`
  - start only / blank stop-step → `(start, start, 0)`; no params → `(default, default, 0)`
  - `rowIterations` invalid (span not divisible, stop < start) → **fail generation with a dialog** naming rule/variable, rather than emit code that makes `InputGrid::from_decls` throw.
- Input handles are members `<prefixed>_h_` (suffix chosen so `_renameVars` can't collide); read at top of `OnBarClose` as `const double E1_lookback = Input(E1_lookback_h_);` (double→int narrowing in subscripts is fine; wrap header in `#pragma warning(push/disable: 4100 4101 4189 4244 4456/pop)` for MSVC).

**Per-version class body (field → location mapping):**

| Rule field | Emitted where |
|---|---|
| inputVariables | `DeclareInput` in ctor; `const double` reads at top of `OnBarClose` |
| localVariables | brace-initialized members (`double E1_mom = 0;`) |
| classMembersHook | class `private:` section |
| startOfFileHook | top of `OnBarClose` (after aliases/input reads/signal init), entry→exit→switch order |
| pre/postConditionHook | inside the occurrence's segment, before/after its condition lines |
| endOfFileHook | bottom of `OnBarClose`, after order placement |

`OnBarClose` skeleton: alias block (`const auto& open/high/low/close/volume = ctx....;`) → input reads → `bool enterLong = true, enterShort = true; bool exitLong = false, exitShort = false;` (plain locals; auto-reset each bar) → start-of-bar hooks → Entries (`enterLong = enterLong && (cond);`) → Exits (`exitLong = exitLong || (cond);`) → Switches (`enter* = enter* && !(cond); exit* = exit* || (cond);`) → order placement → end-of-bar hooks.

Order placement (reproduces TS no-pyramiding + auto-reverse, symmetric):
```cpp
if (enterLong && ctx.MarketPosition() <= 0) ctx.EnterLong(1);
if (enterShort && ctx.MarketPosition() >= 0) ctx.EnterShort(1);
if (exitLong && ctx.MarketPosition() > 0) ctx.Exit();
if (exitShort && ctx.MarketPosition() < 0) ctx.Exit();
```
(Carried-over TS quirk, deliberate for parity: a version with no entry occurrences enters every bar.)

**Registry aggregation — manifest-driven** so multiple strategy batches coexist:
- `generated/manifest.json`: `{ "<Strategy Name>": { "header": "gen_x.h", "entries": [{"name": "...V1", "class": "Gen_X_V1"}] } }`.
- On generate: replace that strategy's batch, prune batches whose header no longer exists on disk, error-dialog on cross-batch registry-name collisions, rewrite both `.inc` files wholesale:
  - `headers.inc`: `#include "bt/strategies/generated/gen_x.h"` per batch
  - `registry.inc`: `{"X V1", [] { return std::make_unique<Gen_X_V1>(); }},` per version (every line comma-terminated)

API: `generate(strategyName, panes, cfg) -> GenerationResult` (paths + version count); pure-text `emitHeader(...)` for unit testing; `rebuildIncFiles(generatedDir)`.

## 4. specWriter.py

Per version: `json.load` the template spec, replace only `"name"` (→ `<sanitized_lower>_v<n>`, the run-dir stem) and `"strategy"` (→ registry name), override `"max_bars_back"` if the GUI field is non-blank; write `<engineDir>/specs/generated/<sanitized_lower>_v<n>.json`. Never add other keys (the loader rejects unknown keys; pass-through is safe).

max_bars_back: a `Max Bars Back` field in the main GUI (persisted in config + templates). Blank = template's value stands. Generation summary dialog always shows the effective value with a warning that it must cover the largest possible lookback or the engine throws at runtime (auto-computing it from arbitrary C++ is impossible — explicit field + warning is the right scope).

## 5. config.json

```json
{
  "engineDir": "C:\\Users\\brian\\source\\repos\\BacktestEngine",
  "generatedSubdir": "src/bt/strategies/generated",
  "specTemplate": "...\\BacktestEngine\\specs\\validation_momentum.json",
  "specOutputSubdir": "specs/generated",
  "maxBarsBack": "100"
}
```
`config.py` unchanged; subdirs are config-file-only knobs (not GUI fields).

## 6. GUI changes vs StrategyGeneratorTS

**mainGUI.py**
- Top form: keep `Strategy Name`; replace `Directory` with `BacktestEngine Root` (validated to contain `src/bt/strategies`); add `Spec Template` (entry + Browse) and `Max Bars Back`.
- Remove `Make MW Inputs` button + `_makeMWInputs`/`_pasteMWCode`/`_showMWResult`.
- `_makeStrategy`: validate name/engine dir/spec template (loads as JSON with `name`+`strategy`), call `strategyWriter.generate` + `specWriter`, then summary dialog: N versions, header path, registry entries, spec paths, effective max_bars_back warning, and reminder `Rebuild: .\scripts\build.ps1 -Config Release`.
- Panes/RuleItem/flip/negate/params/delims/templates/autosave-template: **unchanged**. `_serializeState`/`_applyState` additionally carry `maxBarsBack`.

**ruleCreationGUI.py** (generic field builder needs no change — driven by `TEXT_FIELDS`)
- Drop: EL scratch-slot warning (`Value0-99`/`Condition0-99`), semicolon auto-insertion expectations.
- Keep reworded: warn if `;` appears in Long/Short Condition (must be a C++ expression).
- Add hard errors: variable names must match `^[A-Za-z_][A-Za-z0-9_]*$`, not a C++ keyword, not emitter-reserved (`open high low close volume ctx enterLong enterShort exitLong exitShort`); input defaults must parse as float; locals need both type and initial.
- Local type whitelist `int`/`double`/`bool`; other types allowed behind a "Save anyway?" confirm.
- Keep: input/local name-clash check, overwrite confirm, illegal-filename-char check.

**parameterGUI.py** — unchanged (blank stop/step or stop==start ⇒ 1 iteration; span divisible by step — exactly matches `grid.cpp::axis_count`).

## Implementation order

1. ~~BacktestEngine one-time change (§1); build + tests green; commit there.~~ ✅ DONE — commit `c162d6a`. Start at step 2.
2. Scaffold StrategyGeneratorBE: copy verbatim files, new config.json.
3. `rule.py` + `tests/test_rule.py` (paren-aware parser round-trips, legacy tolerance).
4. `ruleCreationGUI.py` validations.
5. `strategyWriter.py` + golden-text tests (sanitization, case-sensitive rename, full emitted header for a 1-entry/1-exit/1-switch fixture, manifest merge/prune, `.inc` rebuild).
6. `specWriter.py` + tests.
7. `mainGUI.py` rework.
8. End-to-end acceptance + README (rule-authoring conventions: aliases, ctx API, conditions = expressions without `;`, hooks = raw C++, `CurrentBar()==1` init idiom, max_bars_back responsibility).

## Verification

1. `python -m unittest` in StrategyGeneratorBE.
2. Engine builds with empty stubs before any generation (`.\scripts\build.ps1 -Config Release -Test`).
3. **Acceptance gate — Momentum clone parity**: create Entry rule with input `Length(20)`, long `close[0] > close[Length]`, short `close[0] < close[Length]`; one Entry pane, params Length 5–50×5 (identical grid to hand-written `MomentumReversal`), Max Bars Back 100, template `specs/validation_momentum.json`. Generate → rebuild engine → run `bt_walkforward` on `specs/generated/momentum_clone_v1.json` vs `specs/validation_momentum.json` and diff `runs/<name>/` outputs — must be numerically identical apart from input/strategy names (`E1_Length` vs `Length`), since the generated guards reproduce `MomentumReversal` exactly (always-in, no-pyramiding, auto-reverse; equal closes do nothing).
