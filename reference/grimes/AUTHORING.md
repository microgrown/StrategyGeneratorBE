# Authoring the Grimes A list

Brief for every authoring agent. Read it fully, then read
`.claude/skills/author-rule/SKILL.md` fully; that skill is the procedure and this
file only says what is specific to this batch. The Brooks brief
`reference/brooks/AUTHORING.md` is the worked precedent; its B-list and tick-unit
addenda (measured primitives, settled Brooks decisions, double placement) apply
here verbatim and are summarized below.

## Inputs

- Your slice: `reference/grimes/author/slices/NN_<family>.json`. Each entry is a
  merged rule: `key` (the intended rule name), `role`, `is_filter`, `description`,
  `pseudocode` (long side, corpus dialect), `sides`, `parameters` (input name to
  default), `complexity`, `catalog_match` (`rule`, `relation`, `note`), `sources`
  (mined candidate ids, for citation), `merge_notes`, `variants_kept_separate`,
  `depends_on_keys`, `el_words`, `bucket`.
- `reference/grimes/author/A_KEYS.md`: every key in every slice, with its
  catalog_match, for the cross-slice duplicate check.
- `reference/grimes/author/rows/*.md`: rows already written by finished sibling
  slices. Check them too.
- `reference/grimes/merge/DECISIONS.md`: the 26 design decisions settled during
  the merge. Apply them; do not re-deliberate; cite the decision number in the
  row when a rule leans on one.
- `rules/CATALOG.md`, `rules/EL_FEATURES.md`, `README.md` "Writing rules" and
  "The `ctx` API", per the skill.
- If a merged rule's pseudocode is unclear, the mined candidate is in
  `reference/grimes/mined/grimes/*.json` (grep its id) with the book quote and
  page; the book is Adam Grimes, *The Art and Science of Technical Analysis*.

## Both twins, every rule

Every rule is two files with the same name and the same inputs:

- `rules/<Key>.json`: the C++ rule (schema `rule.py:74-98`; examples
  `rules/Breakout.json`, `rules/Momentum.json`, `rules/BarRangeAboveStd.json`,
  `rules/MonthlyProfitTarget.json`).
- `C:/Users/brian/source/repos/StrategyGeneratorTS/rules/<Key>.json`: the
  EasyLanguage twin (same field names minus `classMembersHook`; conditions are EL
  expressions). Write the EL twin first: EasyLanguage's behaviour is the
  specification, and the lint reads the EL twin as the primary feature source.

Translate the merged `pseudocode` into EL first, then mirror it in C++ exactly
per the skill's translation table (`el_gt`/`el_lt`/`el_eq` for comparisons,
loops into locals for `Highest`/`Lowest`/`Average`, `WFSafe_AvgTrueRange` rolling
form for ATR, population standard deviation, zero-initialized mirrored buffers
for variable history). Every merged `parameters` entry becomes an input with the
merged default. `sides` says whether the short side is mirrored or identical.

## Parameterizations: amend the existing rule, do not write a new one

> **Superseded in part, 2026-09-27 (Brian).** Do NOT amend an existing rule that any template in
> `templates/` places: even an inert default changes the MultiWalk code of every family that places
> it. Author the parameterization as a NEW rule under its merged key instead (both twins, the
> source's reading as the default). This pass's `Momentum` and `AtrAboveAverage` amendments were
> reverted that way (`MomentumBeyondAtrMultiple`, `AtrAboveAverageMultiple`). The procedure below
> still applies to a rule no template places.

About a third of this list has `catalog_match.relation == "parameterization"`:
the Grimes rule is an existing catalog rule plus one new input. For those:

1. Open both twins of the existing rule (`rules/<Existing>.json` and the TS
   twin). Confirm the merged pseudocode really is that rule plus the input the
   `catalog_match.note` / `merge_notes` name. If it is not, treat the rule as a
   variant and author it under the merged key instead; say so in the report.
2. Add the input to both twins with a default that preserves the existing
   behaviour **character for character** (a margin of 0, a count of 1, a
   boolean false, a lag of 0): every existing placement and every existing
   template must produce identical code with the input at its default. Grimes's
   value is recorded in the row and in the rule's description, not as the
   default.
3. Re-run `validateRule` and `python lintElFeatures.py <Existing>` on the
   amended rule. Update the rule's `description` to mention the new input.
4. In your rows file, put the **full replacement CATALOG row** for the existing
   rule under a `## Amended` heading (the orchestrator swaps the row in place).
   Do not create a `rules/<MergedKey>.json` for a parameterization.

Only one agent touches any given existing rule. Slice 04 owns `HigherSwingLow`
(two merged rules propose different inputs on it: `HigherSwingLowRun` and
`RisingSwingLowCount`; decide whether they are one input or two, or one is the
other). Slice 03 owns every stop rule it amends. If two rules in different
slices want to amend the same existing rule, the slice listed first in
`A_KEYS.md` owns it; the other reports it as deferred.

## Per-rule gate

For each rule, in order:

1. Duplicate check (skill section 2) against `rules/CATALOG.md`, `rules/` on
   disk, `reference/grimes/author/A_KEYS.md` and `author/rows/*.md`. The merge
   pass already set `catalog_match`; re-check it against the actual JSON of the
   named rule. On a `duplicate`, do not write the rule; record it in your
   report. On a suspected duplicate the merge pass missed, stop for that rule
   and report it; author the rest. Two known clusters are deliberately in one
   slice so the same agent decides: `LowTouchesRecentLow` /
   `LowTouchesRecentRangeLow` (slice 06) and `HigherSwingLowRun` /
   `RisingSwingLowCount` (slice 04).
2. Feature check (skill section 4): every EL word the twin uses must be
   VERIFIED or ACCEPTED in `rules/EL_FEATURES.md`. Your slice was pre-filtered,
   but the translation may reach for something new. If a rule needs an
   unregistered word after all, do not write it; report it as blocked on that
   word. Do not write probes and do not edit EL_FEATURES.md.
3. `validateRule` (skill section 5), then `python lintElFeatures.py <Key>`.
   Both must pass before the files stay.
4. Deepest bar index reached, as an expression over inputs, for the catalog row.

**Do not build the engine and do not run compileCheck.** validateRule and the
lint are your gate; the orchestrator runs `compileCheck.py --double` once per
wave. **Never stop, kill, or wait on any process**: a locked executable or a
busy repo is environmental, judge by diagnostics only.

## What you may write

- `rules/<Key>.json` and `StrategyGeneratorTS/rules/<Key>.json` for keys in your
  slice only. Never overwrite an existing file of either name except as an
  amendment under the parameterization procedure above.
- `reference/grimes/author/rows/NN_<family>.md`: your CATALOG rows, one per rule
  written, in the exact `rules/CATALOG.md` table format
  (`| Rule | Type | Sides | Reaches back | Inputs | Fires when |`); a
  `## Amended` section with full replacement rows for existing rules you gave a
  new input; and a `## Not written` list (key, reason: duplicate of X /
  suspected duplicate of Y / blocked on word W / not translatable because Z /
  deferred to slice NN).

Do **not** edit `rules/CATALOG.md` or `rules/EL_FEATURES.md`; the orchestrator
applies the rows so parallel agents do not collide. Do not commit.

## Settled primitives and decisions (apply, cite by number)

From `reference/grimes/merge/DECISIONS.md`; the measured reference
implementations are in the Brooks B-list addendum.

- **Swing pivot** (dec 14): `rules/SwingHigh.json`'s measured form, inlined:
  at-or-above the `strength` older bars, strictly above the `strength` newer
  bars, lag exactly `strength`, `-1` sentinel guarded as a bool, history
  `lookback - 1 + strength`. Pivot order maps onto `strength`.
- **EMA** (dec 1, 15): `rules/EmaGapBar.json`'s `WFSafe_Xaverage` mirror
  (price seed, `X = X[1] + SF*(P - X[1])`). Lagged reads guard the first k bars.
  The Keltner band is EMA(20) plus or minus 2.25 times ATR(20); a close outside
  it already exists as `CloseBeyondEma`, so band rules here are the free-bar,
  count, and switch forms only.
- **3/10 oscillator** (dec 2): `osc = Average(close,3) - Average(close,10)`,
  `signal = Average(osc,16)`, all simple averages recomputed from price each
  bar (EL `Average` is not rolling). `osc` is a variable, so its `[k]` history
  and any `Average`/`Highest` over it are the variable's own history: mirror
  with a zero-seeded ring buffer as `rules/AwesomeOscillatorSlope.json` and
  `AtrRising` do, re-seeded if depth changes, and guard warm-up. Never use the
  `MACD` word. Slice 01 authors the family; make the fast/slow/signal lengths
  inputs with 3/10/16 defaults on every rule.
- **Divergence** (dec 3): window maxima, `high[0] >= Highest(high, n)[1] and
  osc[0] < Highest(osc, n)[1]`; no pivot scan.
- **Higher timeframe** (dec 4, 15): the same rule at five times the length, a
  second placement; never a new rule or input.
- **Level** (dec 7): the one-bar-shifted N-bar window extreme, tolerance an ATR
  fraction, never ticks.
- **Trading range** (dec 8, 10): `rules/RangeWidthBelowAtrMultiple.json`;
  consolidation length is a `consecutiveBars` input on it (slice 05 owns that
  amendment via `TightRangeRunLength`).
- **Polarity** (dec 12): negate gives "not A", never the mirror side; a fade
  form is a second file when there is machinery, a boolean input when it is a
  one-line ratio.
- **Band-shaped filters** (dec 19): both bounds on one quantity is a new input
  on the rule that computes it, never a second file.
- **Stops** (dec 22 to 26): minimum stop distance is a grid floor, not an
  input; partial profits are separate full exits with a `stopDistance` input in
  price points (the engine has no initial-risk accessor; say so in the row);
  "stop inside the tested extreme" is a NEGATIVE `stopTicks` on
  `InitialStopBeyondSwingAtEntry`, so that input becomes signed (precedent
  `SwingHighProfitTarget.offsetTicks`); `AtrTrailingStop` is the chandelier.
- **Tick size**: `ctx.MinMove()`/`ctx.PriceScale()` exist and are VERIFIED;
  write margins as `ticks * (MinMove / PriceScale)` in EL and
  `ticks * (ctx.MinMove() / ctx.PriceScale())` in C++, computed once per bar
  into a local. A `ticks` input keeps its book default.
- **Session model**: a session starts when `Date[0] <> Date[1]`; running
  open/high/low and a bars-into-session counter in locals, reset on the date
  change; prior-session levels via `HighD(1)`/`LowD(1)`/`OpenD(1)`/`CloseD(1)`.
  Slice 05's two session rules use this.
- **Trend line / channel** (dec 20, and the Brooks channel decision): `TLValue`
  first-anchor form through the two latest confirmed pivots, guard `B1 <> B2`;
  channel line through the two latest swing highs, not parallel.
- **Shift test**: no rule may depend on the price level; every comparison is a
  difference, a ratio of differences, or ATR units. If a merged rule fails this
  on reading, do not write it; report it.

## Double placement

A rule can be placed twice in one strategy, so its hooks are emitted twice into
one class. Never declare C++ scratch at hook scope (`const int x = ...;`,
`double y = ...;` directly inside a hook); every scratch value is a
`localVariables` entry. A braced block `{ const int t = ...; }` is block-scoped
and acceptable, as `AwesomeOscillatorSlope` does. The orchestrator runs
`compileCheck.py --double` after each wave.

## Naming and inputs

- Use the merged `key` as the name unless it collides with an existing rule;
  then pick a name that says how it differs and note it.
- Input names are the merged parameter names; if a merged pseudocode hard-codes
  a number that Grimes tunes (a bar count, a fraction, an ATR multiple), promote
  it to an input with that default.
- Grimes's defaults: Keltner 20 / 2.25 / 20; oscillator 3 / 10 / 16;
  higher-timeframe multiplier 5; level tolerance 0.1 to 0.25 ATR.

## Report back

Under 30 lines: rules written (key, role, one phrase), existing rules amended
(rule, new input, inert default), rules not written with reason, any
`ASSUMED` register row a rule now leans on, anything outside the EL translation
table, and the path of your rows file. No JSON in the report.

## B and C list addendum (2026-09-22)

Slices live in `reference/grimes/author/slicesB/BNN_<family>.json`; the key list is
`reference/grimes/author/B_KEYS.md` (with each rule's `depends_on_keys`); rows go to
`reference/grimes/author/rows/BNN_<family>.md`. The catalog now has 505 rules, so the
duplicate check is against `rules/CATALOG.md`, `rules/` on disk, `author/rows/*.md`
and `B_KEYS.md`. Everything above still applies (twins, gate, parameterization
procedure, settled decisions, double placement, no builds, no killing processes).
What is specific to this list:

- **These rules are `hard` by design.** Nearly all need the measured swing-pivot scan
  (decision 14; inline `rules/SwingHigh.json`'s form; for a third or later pivot,
  hand-roll the scan as `SwingPivotTarget`, `ThreePushPattern` and the amended
  `HigherSwingLow` do, because `SwingHigh` Occurrence 3+ is unmeasured), the trend
  line (`TLValue` first-anchor form, guard `B1 <> B2`, see
  `reference/brooks/probes/TLVALUE_FINDINGS.md`), or the 3/10 oscillator ring buffer
  (copy `rules/OscillatorAboveZero.json` and its twin).
- **`depends_on_keys` may name keys that are not on disk.** Resolve each before you
  write: a key that is a merged `D` rule maps to the catalog rule its `catalog_match`
  names (see `reference/grimes/CANDIDATES.md` "Priority D"); a merged `A`
  parameterization maps to the amended catalog rule plus its new input
  (`CleanLevelTouchBand` = `LevelTouchCount` with `maxTouches`,
  `HiddenComplexPullbackBodyCount` = `OppositeBodyCountInWindow` with `minOpposite`,
  `HigherSwingLowRun` = `HigherSwingLow` with `legs`, `LowTouchesRecentLow` =
  `LowTouchesRecentRangeLow` at `lag` 0); a key found nowhere
  (`CountertrendSpikeStrongerThanPriorSwings`, `LowerTimeFrameBreakoutEntry`,
  `SupportResistanceBounceEntry`, `TrendTerminationPrecondition`) is a merge
  agent's working name for a candidate that was dropped or folded: grep the merged
  file's `dropped` reasons and the mined candidates
  (`reference/grimes/mined/grimes/*.json`) for the concept and inline the nearest
  on-disk rule or the mined pseudocode, saying which in the row.
- **Named templates (`Pullback`, `PullbackLowerTimeframeBreakout`, `ComplexPullback`,
  `Anti`, `FailureTest`, `BreakoutBaseEntryTemplate`, `FailedBreakoutTemplate`)** are
  carried as the book states them: keep `depends_on_keys` in the row text but inline
  the parts in code, as the corpus does for Brooks's named setups. Every part's
  tunable constant stays an input. Where a template's internal logic is an OR of
  alternatives (the breakout templates), that OR is the reason it exists as one file.
- **C rules, resolved:** `AntiStochasticSlopeDisagreement` is authorable: the
  register's `stochastic` row is VERIFIED (ratio-of-sums SlowK, seed-filled warm-up)
  and `rules/StochasticCross.json` is the measured port to copy; the lint maps
  FastK/SlowK onto that row. `OscillatorArtifactWindowBlock` uses merge decision 5
  (window length = slowLen bars anchored on the oscillator zero cross). `TimeDecayStopTightening` is NOT written
  (decision 23: ParabolicSarTrailingStop plus NumBarsIfBelowProfitThreshold cover
  it); list it under "Not written" with that reason.
- **`ParabolicSarTrailingStop`** is Wilder's literal recursion: extreme point, AF
  starting at `afStart`, stepping `afStep` to `afMax`, SAR never inside the prior
  two bars' range; all state in `localVariables`, initialized on the entry bar via
  `BarsSinceEntry = 0`, and it is an Exit so the position side is known.
- **`DailyLossLimit`** follows decision 16: the `rules/MonthlyProfitTarget.json`
  construction (latch period-start equity from NetProfit + OpenPositionProfit) with
  the boundary at `Date <> Date[1]` and the comparison on the loss side; a
  `periodSelect` input for day/week/month only if it costs nothing.
- **`GapAgainstPositionOpeningRangeBreakExit`** uses the session model (Date change,
  running session open/high/low in locals) and the corpus's opening-range rules
  (`OpeningRangeBreakout`, `OpeningRangeMeasuredMoveTarget`) as the form to copy.
- **Divergence** is decision 3 (window maxima, no pivots): `MomentumDivergenceAtSwingExtreme`
  and `NoMomentumDivergenceInWindow` share one computation; the second is the first
  absent over a window, stated positively.
