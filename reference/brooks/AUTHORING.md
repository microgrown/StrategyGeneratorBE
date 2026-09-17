# Authoring the Brooks A list

Brief for every authoring agent. Read it fully, then read
`.claude/skills/author-rule/SKILL.md` fully; that skill is the procedure and this
file only says what is specific to this batch.

## Inputs

- Your slice: `reference/brooks/author/slices/NN_<family>.json`. Each entry is a
  merged rule: `key` (the intended rule name), `role`, `description`, `pseudocode`
  (long side, corpus dialect), `sides`, `parameters` (input name → default),
  `complexity`, `catalog_match`, `sources` (mined candidate ids, for citation),
  `merge_notes`, `variants_kept_separate`, `depends_on_keys`, `el_words`.
- `reference/brooks/author/A_KEYS.md`: every key in every slice, for the
  cross-slice duplicate check.
- `rules/CATALOG.md`, `rules/EL_FEATURES.md`, `README.md` §"Writing rules" and
  §"The `ctx` API", per the skill.
- If a merged rule's pseudocode is unclear, the mined candidate is in
  `reference/brooks/mined/**/*.json` (grep its id) with the book quote and page.

## Both twins, every rule

Every rule is two files with the same name and the same inputs:

- `rules/<Key>.json` — the C++ rule (schema `rule.py:74-98`; examples
  `rules/Breakout.json`, `rules/Momentum.json`, `rules/BarRangeAboveStd.json`,
  `rules/MonthlyProfitTarget.json`).
- `C:/Users/brian/source/repos/StrategyGeneratorTS/rules/<Key>.json` — the
  EasyLanguage twin (same field names minus `classMembersHook`; conditions are EL
  expressions, e.g. `Close = Highest(Close, lookback)`; see the TS `Breakout.json`
  next to the BE one). Write the EL twin first: EasyLanguage's behaviour is the
  specification, and the lint reads the EL twin as the primary feature source.

Translate the merged `pseudocode` into EL first, then mirror it in C++ exactly
per the skill's translation table (`el_gt`/`el_lt`/`el_eq` for comparisons,
loops into locals for `Highest`/`Lowest`/`Average`, `WFSafe_AvgTrueRange` rolling
form for ATR, population standard deviation, zero-initialized mirrored buffers
for variable history). Every merged `parameters` entry becomes an input with the
merged default. `sides` says whether the short side is mirrored or identical.

## Per-rule gate

For each rule, in order:

1. Duplicate check (skill §2) against `rules/CATALOG.md` **and**
   `reference/brooks/author/A_KEYS.md`. The merge pass already set
   `catalog_match`; re-check it against the actual JSON of the named rule. On a
   `duplicate`, do not write the rule; record it in your report. On a suspected
   duplicate the merge pass missed, stop for that rule and report it; author the
   rest.
2. Feature check (skill §4): every EL word the twin uses must be VERIFIED or
   ACCEPTED in `rules/EL_FEATURES.md`. Your slice was pre-filtered, but the
   translation may reach for something new (`MaxList`, `AbsValue`, `CountIF`
   are registered; `XAverage`, `SwingHigh`, `MinMove`, `TLValue` are not). If a
   rule needs an unregistered word after all, do not write it; report it as
   blocked on that word. Do not write probes and do not edit EL_FEATURES.md.
3. `validateRule` (skill §5), then `python lintElFeatures.py <Key>`. Both must
   pass before the files stay.
4. Deepest bar index reached, as an expression over inputs, for the catalog row.

## What you may write

- `rules/<Key>.json` and `StrategyGeneratorTS/rules/<Key>.json` for keys in your
  slice only. Never overwrite an existing file of either name.
- `reference/brooks/author/rows/NN_<family>.md`: your CATALOG rows, one per rule
  written, in the exact `rules/CATALOG.md` table format
  (`| Rule | Type | Sides | Reaches back | Inputs | Fires when |`), plus a
  `## Not written` list (key, reason: duplicate of X / blocked on word W /
  suspected duplicate of Y / not translatable because Z).

Do **not** edit `rules/CATALOG.md` or `rules/EL_FEATURES.md`; the orchestrator
appends the rows so parallel agents do not collide. Do not commit.

## Naming and inputs

- Use the merged `key` as the name unless it collides with an existing rule; then
  pick a name that says how it differs and note it.
- Input names are the merged parameter names; if a merged pseudocode hard-codes a
  number that Brooks tunes (a tick count, a bar count, a fraction), promote it to
  an input with that default.
- Tick offsets: a "ticks" parameter cannot be converted to price without
  `MinMove`/`PriceScale`, which are unregistered. Express such thresholds as a
  price-unit input (`offsetPoints`) or a fraction of ATR / bar range instead, and
  say so in the row. Rules in your slice were filtered to avoid tick units, but
  check.

## Report back

Under 30 lines: rules written (key, role, one phrase), rules not written with
reason, any `ASSUMED` register row a rule now leans on, anything outside the EL
translation table, and the path of your rows file. No JSON in the report.

## B-list addendum (2026-09-13, after the probes)

Slices for the B list live in `reference/brooks/author/slicesB/BNN_<family>.json`;
the key list is `reference/brooks/author/B_KEYS.md`; rows go to
`reference/brooks/author/rows/BNN_<family>.md`. The catalog now has 247 rules,
so the duplicate check is against `rules/CATALOG.md`, `rules/` on disk,
`author/rows/*.md` and `B_KEYS.md`. Everything above still applies. What is new:

**Measured primitives, with the reference implementation to copy:**

- Swing pivot: `rules/SwingHigh.json` (and its TS twin). The measured test is
  at-or-above the `strength` OLDER bars and STRICTLY above the `strength` NEWER
  bars, `el_ge`/`el_gt` inside the scan, lag exactly `strength`, `-1` sentinel
  guarded, history `lookback - 1 + strength`. Details in
  `reference/brooks/probes/SWING_FINDINGS.md` §4. Inline it; do not reference
  the rule file.
- EMA: `rules/EmaGapBar.json` carries the `WFSafe_Xaverage` mirror (price seed on
  the first calculated bar, `X = X[1] + SF*(P - X[1])`, `SF = 2/(Length+1)`).
  `emaLength` stays an input; since 2026-09-17 it MAY be optimized in grids
  (`WFSafe_Xaverage` recomputes SF on a length change, state carried; measured).
  **Lagged reads `ema(...)[k]`, k > 0, are MEASURED (2026-09-17):** the EL
  function's `[k]` history is exactly its own past values, and reads before the
  history exists (bars 1..k) return 0.0, not the seed. The C++ zero-initialized
  mirrored ring buffer is exact; every rule reading `ema[k]` guards its first k
  bars (`CurrentBar > k` in EL, the bar counter in C++) instead of comparing
  against that zero. See `reference/brooks/probes/XAVERAGE_LAG_FINDINGS.md`.
- Trend line: `TLValue` is a first-anchor two-point interpolation,
  `slope = (P2 - P1) / (B2 - B1); value = P1 + (target - B1) * slope`, older
  anchor first (zero-drift spelling), free extrapolation, and the equal-bar case
  returns 0.0 instead of halting, so every rule guards `B1 <> B2`. Details in
  `reference/brooks/probes/TLVALUE_FINDINGS.md` §4. Anchors are the two most
  recent CONFIRMED pivots at `strength`, per the merge decision.
- Tick size: the accessors exist. `MinMove`/`PriceScale` are VERIFIED and the
  engine now exposes `ctx.MinMove()`, `ctx.PriceScale()` and `ctx.TickSize()`
  (as of 2026-09-17), so a rule may be stated in ticks directly. Write the
  margin division-first in both twins:
  EL `ticks * (MinMove / PriceScale)`, C++
  `ticks * (ctx.MinMove() / ctx.PriceScale())` — `ctx.TickSize()` is that same
  division and the same double, but the paired form is what the corpus writes,
  so the C++ reads token for token against its EasyLanguage. A `ticks` input
  keeps its Brooks default; do not rescale it into price points or ATR
  fractions.

**Settled design decisions (apply, do not re-deliberate; cite the decision in
the row):**

- Always-in direction: a persistent state that flips on `consecutiveBars`
  (default 2) consecutive strong trend bars (body >= 0.6 of range, both tails
  <= 0.2), holds until the opposite flip, undefined until the first flip. No
  rule file exists for it yet; a B rule that needs it inlines this state machine
  in its hooks and names the decision in the row.
- Leg counting: the persistent H1/H2 counter of Ranges ch17 (`R17-01`): advance
  on a higher-high bar only after a new low since the last counted bar, reset on
  a fresh `resetLookback`-bar high, saturate at 4. The `leg_counting` slice
  authors `HighLowBarCount` first; other rules inline the same counter.
- Trading range: `highest(high,20) - lowest(low,20) <= 4 x ATR(14)`
  (`rules/RangeWidthBelowAtrMultiple.json`); tight range is the same at
  15 bars / 1.2 ATR; barbwire is `rules/Barbwire.json`.
- Tight channel: `rules/TightChannel.json`. Spike: `rules/StrongTrendBarRun.json`
  and `StrongTrendBarCount`. Climax: `rules/ClimaxBar.json`.
- Session model: a session starts when `Date[0] <> Date[1]`; keep the session's
  running open/high/low and a bars-into-session counter in locals, reset on the
  date change. Prior-session levels use `HighD(1)`/`LowD(1)`/`OpenD(1)`/
  `CloseD(1)` (VERIFIED). A 1440-minute bar is still intraday per the register.
- Composites that are named Brooks setups keep `depends_on_keys` in the row
  text but inline the parts in code, as the corpus does.

**Reaches back** must include the pivot lag (`lookback - 1 + strength`), the
trend-line anchors, and any counter's reset lookback.

**Double placement (added 2026-09-13).** A rule can be placed twice in one
strategy, so its hooks are emitted twice into one class. Never declare C++
scratch at hook scope (`const int x = ...;`, `double y = ...;` inside a hook);
every scratch value is a `localVariables` entry. `AdxBelowThreshold` was fixed
for exactly this; `reference/brooks/compileCheck.py --double` checks it.

## Tick-unit list addendum (2026-09-17)

Slices live in `reference/brooks/author/slicesT/TNN_<family>.json`; the key list is
`reference/brooks/author/T_KEYS.md`; rows go to `reference/brooks/author/rows/TNN_<family>.md`.
The catalog now has 394 rules, so the duplicate check is against `rules/CATALOG.md`,
`rules/` on disk, `author/rows/*.md` and `T_KEYS.md`. Everything above still applies,
including the B-list addendum (measured primitives, settled decisions, double
placement). What is specific to this list:

- **These rules were held back only because they are stated in ticks.** The tick
  is now available in both twins (bullet "Tick size" above). Keep the merged `ticks`
  parameter names and Brooks defaults; convert at the comparison, never by
  rescaling the input: EL `high > high[1] + marginTicks * (MinMove / PriceScale)`,
  C++ `el_gt(high[0], high[1] + marginTicks * (ctx.MinMove() / ctx.PriceScale()))`.
  "Within N ticks" is `el_le(abs(a − b), n * tick)`; "at least N ticks beyond" is
  `el_ge(a − b, n * tick)`; "no more than N ticks" pairs `el_gt(…, 0)` with
  `el_le(…, n * tick)`. Compute the tick once per bar into a local (`tickSize`)
  in both twins; it is a per-symbol constant, so no history is needed.
- **Register check:** `minmove` and `pricescale` are VERIFIED; the lint maps
  `ctx.TickSize()` to those two words but the corpus writes the paired form.
- **Clusters that may collapse.** `T02_bar_offsets` holds `DipBelowPriorBarLowByTicks`,
  `DipBelowPriorBarLow`, `ShallowDipBelowPriorBarLow`, `ShallowDipBelowPriorLow`
  (from different buckets, kept apart by the merge): they are in one slice so
  the same agent decides which are one rule with a parameter; author the distinct
  ones, list the rest under "Not written: duplicate of X". `T05_stops` and
  `T06_targets_swings` share the swing-pivot scan (inline `rules/SwingHigh.json`'s
  measured form; occurrence 3+ is unmeasured, hand-roll the scan as
  `SwingPivotTarget` does).
- **Already on disk from earlier passes,** so compose with or defer to them, not
  re-author: `ThreePushPattern` (ATR tolerance), `SwingHigh`, `SwingPivotTarget`,
  `TightChannel`, `StrongTrendBarRun`, `ClimaxBar`, `HighLowBarCount`,
  `RangeWidthBelowAtrMultiple`, `Barbwire`, `StopLossTakeProfitDollar`,
  `StopLossTakeProfitATR`, `StopAtSignalBarRangeMultiple`, `SessionBarBreakout`.
  Trend line and channel construction follow the settled decision recorded in
  `reference/brooks/author/DECISIONS.md` (search "channel"): trend line through
  the two latest confirmed swing lows, channel line through the two latest swing
  highs, not parallel, `TLValue` first-anchor form, guard `B1 <> B2`.
- **Session rules** (`PremarketExtremeTest`, `SessionCloseStrengthBias`,
  `SessionOpenPriceTarget`): the session model in the B-list addendum; a premarket
  window is bars whose `Time` precedes the regular-session open input.
- `RoundNumberProximity` needs a rounding word: check `rules/EL_FEATURES.md` for
  `Round`, `IntPortion`, `Floor`, `Mod`; if none is VERIFIED/ACCEPTED, it stays
  blocked on that word — report it, do not write a probe.
