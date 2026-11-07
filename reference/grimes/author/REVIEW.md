# Grimes A-list review pass (2026-09-22)

> **2026-09-27:** the `Momentum` and `AtrAboveAverage` amendments audited below were reverted;
> their behaviour is now the new rules `MomentumBeyondAtrMultiple` and `AtrAboveAverageMultiple`
> (see `DECISIONS.md`). The audit is kept as the record of the 2026-09-22 state; 18 amendments stand.

## 1. Inertness audit — 20 amended rules, both twins. ALL INERT, NO FIXES NEEDED.

Confirmed inert at the new defaults, twins carrying identical inputs/defaults/behaviour:
`AtrAboveAverage` (`atrMultiple 1.0`, 1.0*x exact) · `ChannelLineBreakTrendBarClose`
(`breakMarginAtr 0`) · `CloseNearSessionExtreme` (`strengthMode 0` takes the original branch
verbatim) · `EmaGapBar` (`marginAtr 0`) · `ExitOnOppositeStrongTrendBar` (`scratchWindow 0`
short-circuits true) · `HigherSwingLow` (`legs 2`: the run reduces to `!el_le(lo1,lo2)` =
`el_gt(lo1,lo2)`, HEAD's exact test) · `InitialStopBeyondSwingAtEntry` (`pivotIndex 1`) ·
`LevelTouchCount` (`maxTouches 0` = unbounded) · `Momentum` (`lag/searchBars/minMoveAtr 0`: the
loop runs once at offset 0 with margin exactly 0.0) · `NumBarsIfLosing` (`profitThreshold 0`,
`el_lt` kept STRICT) · `OppositeBodyCountInWindow` (`minOpposite 0`, a count is never negative) ·
`PullbackDepthFromRecentHigh` (`maxRetracementFraction 1000`; with `pullbackLookback <= lookback`
the depth cannot exceed the leg height, incl. the zero-height leg) · `RangeWidthBelowAtrMultiple`
(`consecutiveBars 1`) · `ShavedTopBar` (`consecutiveBars 1`) · `StopBeyondExtremeSinceEntry`
(`preEntryBars 0`, loop body never runs) · `StopBeyondRecentRangeExtreme` (`confirmBars 1`,
`bufferAtrMultiple 0`) · `SwingPointTrailingStop` (`pivotIndex 1`, `maxRiskAtr 0` skips the floor
block) · `TrailArmedAfterProfitThreshold` (`stopOffsetAtr 0`) · `TrendLineBreak`
(`maxAnchorSpanBars 0` = unbounded, folded into `haveLoLine`) · `TrendLineSlopeFlattening`
(`steepenSense 0` selects the original disjunct).

Checked specifically: every flag-rewrite pairs `el_le`/`el_gt` (and `el_lt`/`el_ge`) as exact
complements, so `x = true; if (el_gt(..)) x = false;` reproduces HEAD's `el_le(..)` bit for bit;
no `0 * x` can make a NaN (every ATR local is a finite quotient with a nonzero divisor); no
warm-up guard was added to a rule that had none.

The three deliberate EL rewrites verify term for term against `EL_FEATURES` swinghigh/Extremes:
the hand-rolled scans use STRICT on the `kk < jj` (newer) side and at-or-beyond on the older
side, start at `jj = strength`, stop at `Length-1`, and guard on pivot COUNTS not the -1 price;
at `pivotIndex/legs` defaults the first pivot found newest-first is what `SwingLow(1,...)`
returned. The inlined `Highest`/`Lowest` and the nested Extremes loop return the same values
(only the value is taken; tie sense cannot change it).

**`stopTicks` signed — confirmed unblocked.** No `abs`/`fabs`/`max` in either twin; the
arithmetic is `stopLong - stopTicks * tickSize` / `stopShort + stopTicks * tickSize`, and
`parameterGUI.rowIterations` (both repos) accepts a negative Start provided Stop >= Start and
Step > 0, so a grid may run -4..4 step 1.

**Recorded, not a defect:** six rules deepened their reach by a new ATR read (`EmaGapBar`
0 -> `atrLookback+1`, `TrailArmedAfterProfitThreshold` 1 -> `atrLength+1`, plus `Momentum`,
`ChannelLineBreakTrendBarClose`, `StopBeyondRecentRangeExtreme`, `SwingPointTrailingStop`).
Every template pins `maxBarsBack` to 250 (53 templates), 100 (3) or 300 (3), so no placement is
affected and the EL rolling accumulators keep their seed bar. All 20 catalog rows' Inputs and
Reaches-back columns match the code.

## 2. Duplicate review — 42 new rules. NONE REMOVED.

Near-neighbours kept, one line each:
- `AcceleratingLegsClimax` vs `ParabolicAccelerationExit` — byte-identical body; kept because
  panes are TYPE-GATED (`mainGUI.RulePane` lists only its own type) and the corpus already
  carries the same role twin in `RangeWidthBelowAtrMultiple` / `TightRangeBlocksEntries`.
- `TrendRateAcceleration` vs `AcceleratingLegsClimax` — absolute per-bar rates over unequal
  nested windows vs a signed, mirrored, equal-window leg test; neither reaches the other.
- `NetMoveBelowAtrMultiple` vs `Momentum` — a two-sided band on |net move|, which negating a
  one-sided mirrored rule cannot produce.
- `SpringWithMinimumPenetration` vs `SmallBreakoutTrapReversal` — opposite bounds on one
  penetration (floor in ATRs vs cap in points), so neither is the other at any parameter.
- `BodyExceedsAverageBarRange` vs `BodyAboveAverageMultiple` — body measured against other bars'
  RANGES, and direction-agnostic where the other demands with-trend colour.
- `CloseChangeAboveStdDev` vs `BarRangeAboveStd` — close-to-close change vs bar range, and no
  mean term in the band.
- `OscillatorHook` vs `MomentumChange` — a three-bar slope inflection in the 3/10 oscillator vs a
  level crossing of close against close[n].
- `StalledPositionExit` / `FlatTradeScratchExit` vs `NumBarsIfLosing(+profitThreshold)` — the
  first adds a range-contraction term (exits OR, so the conjunction is not decomposable), the
  second tests MaxPositionProfit in ATR units, not open profit in currency.
- `StopAtLowNBarsAgo` vs `StopBeyondRecentRangeExtreme` — one bar's low at a fixed offset, a
  non-monotone level; the window minimum cannot express it above N=1.
- `LowTouchesRecentRangeLow` vs `TouchOfRecentExtreme` — kept, but the row's stated reason was
  WRONG and I corrected it in CATALOG.md: the FLIP toggle does swap the sides, so what actually
  keeps them apart is the tolerance metric (a fixed tick count cannot reproduce a
  volatility-scaled ATR band at any setting), plus the `lag` input.
- `BreakoutBarRangeAndVolumeExpansion` — a deliberate compound; NOT(range AND volume) is an OR
  that ANDed entry panes cannot rebuild.
- `ShrinkingConsecutiveBarRanges` vs the existing `ShrinkingConsecutiveRanges` — confusingly
  close NAMES, but bar-to-bar ranges vs the spans of two adjacent fixed-length windows.

Also checked across all 42: no C++ hook-scope declarations (every scratch is a `localVariables`
entry or sits inside a braced block / for-init), no brace or paren imbalance, and no
price-LEVEL dependence — the only `%` hits are `std::size_t` ring-buffer index arithmetic, and
there is no percent-of-price, price*volume, rounding, or price-versus-literal comparison.

## 3. Gates

- `validateRule` on all 62 touched rules: **0 errors**. Warnings are pre-existing conventions —
  `std::vector<double>` / `std::size_t` ring-buffer locals (12 rules, as HEAD's `AtrAboveAverage`
  already does) and uppercase EL words appearing only in COMMENTS (4 rules, verified comment-only).
- `python lintElFeatures.py` over the corpus: **505 rules scanned, 0 blocking, 0 warnings.**

## 4. Unresolved / for Brian

- `RangeWidthBelowAtrMultiple` gained `consecutiveBars`; its Switch-role twin
  `TightRangeBlocksEntries` did not, so a previously formula-identical pair has diverged.
- `AcceleratingLegsClimax` is now the corpus's only byte-identical rule body (505 rules, one
  collision). Legitimate under type-gating, but if role twins are to be allowed generally a
  role field on one file would be cheaper than duplicating bodies.
- `LowTouchesRecentRangeLow` would have been cleaner as `tolAtr`/`atrLength`/`lag` inputs on
  `TouchOfRecentExtreme` (all inert at 0) plus the flip toggle, per AUTHORING "Parameterizations".
  Left as a separate file; it is not reachable from the existing rule, so it is not a duplicate.

# Grimes B/C-list review pass (2026-09-22)

## 1. Twin consistency — 25 rules. FOUR DEFECTS FIXED, all in the For-guard family.

All 25 carry identical name, type, inputs, defaults and input ORDER across the twins (checked
mechanically). `validateRule`: **0 errors** on the whole 530-rule corpus; the only warnings on the 25 are
the corpus's `std::vector<double>` / `std::size_t` ring-buffer locals (4 rules).
`python lintElFeatures.py`: **530 rules scanned, 0 blocking, 0 warnings.**

- **FIXED, EL twins, pivot scans in 6 rules** (`UpLegsLongerThanDownLegs`, `SwingLegExceedsAverageLeg`,
  `ThreePushSymmetry`, `TrendLegCountAboveMax`, `AscendingTriangleIntoLevel`, `Anti`):
  `for kk = jj - strength to jj - 1` was unguarded, so at `strength` 0 EL counts DOWN and at `jj` 0 reads
  `High[-1]`, a FUTURE bar, where the C++ loop does not run at all. Both neighbourhood loops are now
  wrapped in `if <strength> >= 1 then begin ... end;`. Inert at every strength >= 1.
- **FIXED, `NoMomentumDivergenceInWindow` (EL)**: `For ii = 0 To sinceDivergenceBars - 1` read `High[-1]` /
  `osc[-1]` at 0 — guarded at `>= 1`; the inner `For jj = 2 To divLookback` guarded at `>= 2`.
- **FIXED, `MomentumDivergenceAtSwingExtreme` (EL)**: `For ii = 2 To divLookback` ran BACKWARDS below 2 —
  guarded at `>= 2`.
- **FIXED, `Anti` (C++)**: the spike scan lacked the EL twin's `spikeBars >= 1` guard, so at `spikeBars` 0
  the empty inner loop left both spike flags TRUE and armed a trigger EL never arms.
  `if ((int)spikeBars < 1) break;` added — the rule's own `failBars` / `lookback` idiom.

Checked clean: (b) no hook-scope C++ declarations anywhere in the 25 — every scratch is a `localVariables`
entry or loop/block-scoped, braces balanced. (c) shift test — the only `%` hits are ring-buffer index
arithmetic; no round numbers, percent-of-price, price x volume, or sign-test-on-a-price, and every `-1.0`
price sentinel is guarded by a bool or a pivot COUNT, never by comparing the price. (d) every pivot scan is
`SwingHigh.json`'s measured form: at-or-beyond the `strength` OLDER bars (`k > j`, `el_ge` / `el_le`),
STRICTLY beyond the NEWER ones (`k < j`, `el_gt` / `el_lt`), `j` starting at `strength` so the lag is
exactly `strength`, stopping at `lookback - 1`; Occurrence 3+ is hand-rolled wherever it is needed.
(e) the 3/10 blocks in `MomentumDivergenceAtSwingExtreme`, `NoMomentumDivergenceInWindow`,
`OscillatorArtifactWindowBlock` and `Anti` are `OscillatorAboveZero.json`'s computation verbatim; the three
that read `osc[k]` mirror the variable's zero-filled history with a re-seeding ring buffer at exactly the
depth the scan reaches. (f) `ParabolicSarTrailingStop` is Wilder's — seed EP/SAR on the fill bar,
`sar += af * (ep - sar)`, clamp to `low[1]` / `low[2]` (mirrored short), THEN update EP and step AF by
`afStep` to `afMax`; all state reset on `BarsSinceEntry == 0`, stop not live on the fill bar; twins
statement for statement. (g) `FailedBreakoutTemplate`'s `Ticks[kk + jj]`: `ctx.Ticks` is a
`SeriesView<int64_t>` (`BacktestEngine/src/bt/sim/strategy.h`) whose `operator[]` takes any bars-back
inside MaxBarsBack, so the indexed read is supported, and it is cast to `double` before arithmetic. The
`ticks` register row is VERIFIED for the QUANTITY (up + down) and is silent on indexing; indexing a data
series is not a separate measured behaviour, and the corpus already reads the sibling `volume` series at
offsets (`VolumeDivergenceAfterClimax`). The C++ mirrors the EL term for term, both windows
`kk+1 .. kk+lookback`.

## 2. Duplicate review — 25 rules, the skill's three tests. NONE REMOVED, NO CATALOG ROW DELETED.

- `TrendLegCountAboveMax` vs `LegCountAtLeast` — a pivot run vs the bar-by-bar pullback leg counter
  (different series, different reset, capped at 4 there and uncapped here). vs `HigherSwingLow(legs)` — its
  LONG is higher swing LOWS and its SHORT lower swing HIGHS; neither side, flipped or negated, is "higher
  swing HIGHS", and `NOT(falling-highs run)` is not `rising-highs run`.
- `SwingLegExceedsAverageLeg` vs `ShrinkingSwingIncrementsExit` — whole legs across BOTH series, expanding,
  Entry; vs pivot-to-pivot INCREMENTS on ONE series, shrinking, Exit.
- `MicroTrendLineReclaim` vs `MicroTrendLineFailedBreakout` — same line; a close back over the LINE vs a
  close over the POKING BAR's own extreme (a strictly higher bar), and any poke in the window vs the first.
  Closest pair in the batch; no parameter setting joins them.
- `TrendLineBreakConfirmedExit` vs `TrendLineBrokenRecently` — Exit vs Entry (panes are type-gated), an
  all-of-N consecutive run vs K-of-N over a window, and the LONG is paired with the BULL line here and the
  BEAR line there.
- `ExtensionLegExceedsSetupLeg` / `UpLegsLongerThanDownLegs` vs `SwingLegLengthAtLeast` — legs in PRICE
  compared against each other vs legs in BARS with a floor, direction-agnostic.
- `SwingTrendHigherHighsAndLows` vs `HigherSwingLow(legs)` placed twice — Dow needs BOTH series on the SAME
  side; the side assignment blocks it, the same obstruction `AscendingTriangleIntoLevel` carries.
- `NoSustainedPriorPenetration` vs `TwiceFailedBreakoutAttempt` — the longest RUN beyond ONE level read at
  bar 0 vs a COUNT of fresh failure EVENTS against a per-candidate extreme, and the opposite polarity.
- `BreakevenStopAfterFavorableCloseRun` vs `BreakevenStopAfterEmaHoldingRun` — at `emaLength` 1 the EMA
  collapses to `close[0]` and the arming test becomes `close[0] > close[0]`, never true, so no setting
  reproduces `close[0] > close[1]`.
- `GapAgainstPositionOpeningRangeBreakExit` vs `OpeningRangeMeasuredMoveTarget` — a target ABOVE the range
  for a long vs an exit BELOW it, plus a gap latch the target rule has no input for.
- `DailyLossLimit` vs `MonthlyProfitTarget` — A NEAR MISS worth recording: negated, at a negative
  `ProfitTarget`, `MonthlyProfitTarget` is exactly the loss test — but on the MONTH boundary, and no input
  moves that boundary. Kept for the boundary alone.
- The templates vs their inlined parts: `Pullback`, `PullbackLowerTimeframeBreakout`, `ComplexPullback`,
  `Anti` and `BreakoutBaseEntryTemplate` each carry at least one OR (two in `ComplexPullback`) plus shared
  level state, and `Anti` adds a cross-bar termination latch. `FailedBreakoutTemplate` has no OR but has
  the ORDERING constraint — the range and tick tests run at a breakout bar found by a backward scan while
  the body test runs on bar 0, and two entry panes both evaluate bar 0. None is a pure AND of on-disk
  panes. (`FailureTest` was never written: merge decision 13 keeps it as two panes.)

## 3. Three pre-existing hazards — ALL REAL. NOT FIXED; for Brian.

- **`rules/StochasticCross.json`, double placement.** `preConditionHook` declares FIVE scratch values at
  hook scope: `double hhWin`, `double llWin`, `double skSumN`, `double skSumD`, `double skSumK`. Hooks are
  emitted twice into one `OnBarClose` body, so a second placement is a C++ redefinition. Minimal fix: move
  those five into `localVariables` as `{"type": "double", "init": "0.0"}` and drop the `double ` prefix
  from the five statements — no behaviour change, each is fully assigned before it is read on every bar.
  The inner `{ int have; int take; int miss; }` blocks are already block-scoped and are fine. (The new
  `AntiStochasticSlopeDisagreement`, which ports the same chain, declares everything in `localVariables`.)
- **`TrendLineBrokenRecently`, EL twin.** `for kk = 0 to withinBars - 1` is unguarded, so at `withinBars` 0
  EL counts DOWN through `kk = -1` and reads `Close[-1]` and `TLValue(..., -1)` — a FUTURE bar. The worse
  of the two. Minimal fix: `if withinBars >= 1 then begin ... end;` around the loop.
- **`MicroTrendLineFailedBreakout`, EL twin.** `for kk = 1 to failureWindowBars` is unguarded, so at 0 EL
  runs `kk = 1` then `kk = 0` and folds the CURRENT bar into a window meant to exclude it. No negative
  index, so no lookahead — a twin divergence only. Minimal fix:
  `if failureWindowBars >= 1 then begin ... end;`.

## 4. Catalog

`rules/CATALOG.md`: **530 rows for 530 `rules/*.json`** — one row per file, no duplicate row, no row
without a file, no file without a row.

## 2026-09-23: the three pre-existing hazards fixed (orchestrator, at Brian's request)

- `rules/StochasticCross.json`: the five hook-scope C++ declarations (`hhWin`, `llWin`, `skSumN`,
  `skSumD`, `skSumK`) moved to `localVariables` as doubles initialised to 0.0; the hook assigns them.
  No behaviour change; validateRule 0 errors (pre-existing vector-type warning only); lint clean;
  compileCheck --double run.
- `StrategyGeneratorTS/rules/TrendLineBrokenRecently.json`: the `withinBars` loop wrapped in
  `if withinBars >= 1 then begin ... end;` (at 0 it read `Close[-1]` and `TLValue(..., -1)`, a future
  bar). EL twin only; the C++ loop already ran zero times. Lint clean.
- `StrategyGeneratorTS/rules/MicroTrendLineFailedBreakout.json`: the `failureWindowBars` loop wrapped
  in `if failureWindowBars >= 1 then begin ... end;` (at 0 it folded the current bar into the window).
  EL twin only. Lint clean.
- Grids for `withinBars` and `failureWindowBars` may now legitimately include 0 (the rule then never
  fires), though starting at 1 remains the sensible floor.
