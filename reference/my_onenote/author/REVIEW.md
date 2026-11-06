# Review of the 66 own-notes rules (2026-11-05)

Scope: the 66 untracked `rules/*.json` files, their `StrategyGeneratorTS` twins,
their CATALOG rows, and the two `lag` amendments. No rule file was edited.

Mechanical checks, all 66: every rule has a TS twin, names match, the type and the
input names and defaults are identical in both twins, and each rule has exactly one
CATALOG row. No twin puts a stateful call in a condition. The only function calls
inside EL conditions are the fresh `Average`/`StdDev` in `BollingerWidthBelowAverage`
and `TrueRangeCoefficientOfVariation`, which hold no state.

## 1. Duplicates within the batch

| Pair | Finding | Action |
|---|---|---|
| `BreakoutDirectionShare` / `ConsecutiveUpsideBreakouts` | The event scans are character-identical. CUB(N) equals BDS(N, `minShare` 1) exactly, because `upN >= N` with `upN <= seen = N` means `upN == N`. | None. Brian kept both. |
| `NewExtremeFrequency` / `BreakoutDirectionShare` | Distinct. NEF counts, over a fixed window, the bars whose high is `>=` the `extremeBars` window ending at that bar. Highs and lows are counted independently and there is no ambiguity skip. BDS walks a variable span with strict breaks against the prior window, skips two-sided bars, and stops at `eventCount`. No parameter maps one onto the other. | Keep. |
| `SwingHighClusterDecisiveBreak` / `LevelPairPivotBreakout` | Distinct. SHCDB fires on a CLOSE at least Y ATR above M clustered highs, with no earlier significant close. LPPB fires on the confirmation bar of a PIVOT high at least 1 ATR above a level pair. They can co-fire, but neither is the other at any setting. | Keep. |
| `UpperBandTouchBarBreak` / `BandHighThenMidlineRetrace` | Opposite intents. UBTBB is continuation: the first close above the touch bar's high. BHTMR is a pullback: the low reaches avg − k·sd after a band high. | Keep. |
| `FastEmaAboveSlowEma` / corpus | No EMA-order state rule exists. `MovingAverageCross` is the SMA crossing event, `AwesomeOscillatorSlope` is the slope of an SMA difference, and there is no MACD-sign rule. The EMA recursion is `CloseBeyondEma`'s verified form. | Keep. |
| `MomentumLadder` / `Momentum`, `DualMomentum` | The first link is `Momentum(stepBars)`. The links between lagged closes cannot be placed, because neither rule has a lag input. | Keep. |
| `RsiTightBandExitBarColour` / `RsiBandBreakThenOppositeBar` | They never fire on the same bar for the same break. TBEBC fires ON the break bar. RBBTOB needs the break at bb >= 1 and no green bar since it. | Keep. |
| `LevelBodyDominated` / `LevelRejectedFromAbove` | The complement is exact: the same visit scan, `el_lt` against `el_ge` on the same body edges, so upper + lower + body = visits. | None. This is pane 1 against pane 2. |
| `BreakoutClearsByHalfBar` / `RangeOutsidePriorRangeFraction` | Overlap, not a duplicate. A BCBHB long implies ROPRF(0.5) on the same window, but ROPRF has no direction, sums both sides and uses `>=`. | Keep. |
| `EmaInvertedBarsAboveSlow` / `FastEmaAboveSlowEma` + `EmaGapBarRun` | Not composable. The fast<slow order must hold on every bar of the run, not just the current one. | Keep. |

## 2. Duplicates against the pre-existing corpus

No exact duplicates were found. Two pairs are near, and both differ only on edge cases:

- **`SwingStructureTrend` vs `HigherSwingLow`** (CATALOG line 517). The long side is
  `HigherSwingLow` AND `HigherSwingLow` flipped and negated, at the same strength
  and `maxBarsBack`. The flipped, negated placement gives `!(hi1 < hi2)`, which is
  `hi1 >= hi2`. The difference is confined to equal pivot prices and to a missing
  pivot: negation passes when `haveHi` is false. The row's phrase "cannot supply
  the second by flip or negation" overstates this. **Action:** keep the rule, since
  the strict test and the existence guard on all four pivots are real differences.
  Reword the row to "near: `HigherSwingLow` plus its flipped and negated
  placement, differing on tied pivots and missing pivots."
- **`NewWindowLowAboveLongerLow` vs `HighestHighBreakout`.** The rule is roughly
  HHB(lookback+1) flipped AND HHB(longFactor·lookback+1) flipped and negated. The
  differences are that HHB's short-window test is inclusive (`=` admits a tie with
  the prior low), which matters on tick-grid data, and that `longFactor` is a
  multiplier rather than a free length. **Action:** keep it as Brian's single pane-1
  rule. Optionally add "Not `HighestHighBreakout` pair: strict, ties excluded" to
  the row.

Other pairs checked and found distinct:

| New rule | Existing rule | How they differ |
|---|---|---|
| `SwingLowRejection` | `SwingPointTestHolds`, `FailedSwingBreakoutReversal` | SLR is two-sided and adds a wick test. |
| `EmaTouchAfterLongAbsence` | `TwentyGapBarPullbackEntry` | The gap is fixed in the old rule; the new one also trades through the EMA. |
| `MaSideFlipRun` | `ConsecutiveClosesBeyondEmaRun` | The old rule has no lag input. |
| `MaWickTouchesHoldSide` | `EmaTouchRecovery` | The new rule is persistent state across touches; the old one is a single bar. |
| `ExitOnReturnThroughBreakoutPoint` | `PullbackBeyondBreakoutPoint`, `ExitAtPriorRangeExtreme` | The old rules are an entry and a far-side target. |
| `TargetAtSignalBarOpen` | `EntryBarExtremeTarget` | Different targets. |
| `AdxFallingMomentumFade`, `AdxRisingExit` | `AdxBelowThreshold` | The old rule thresholds the ADX level and reads no ADX history. |
| `ConsolidationBreakoutFirstRetest`, `ConsolidationBreakoutBarHighClose` | `BreakoutPullbackEntry`, `BreakoutLevelRetest` | The breakout bar, the level and the retest are defined differently. |
| `FractalTrendlineBreak`, `SwingRegressionTrend` | `TrendLineBreak` | The old rule draws a two-point line; no regression rule existed. |
| `BollingerWidthBelowAverage`, `TrueRangeCoefficientOfVariation` | `AtrFastAboveSlow`, `TrueRangeAvgRatio` | No band-width or coefficient-of-variation rule existed. |
| `DonchianOutsizedBreakoutFade` | `AtrBandBreakout` | The new rule fades the break. |

## 3. Twin mismatches

**None found.** 32 of the 66 were read side by side, with comments stripped, for
comparisons and sides, tolerance placement, loop bounds, warm-up and zero-fill,
ring-buffer indexing and short-side mirroring:

- **Swing box:** `ChannelFailedSwingFromHitSide`, `ChannelInnerSwingBreakFade`,
  `InnerBoxFalseBreakReclaim`. The inlined ON-1-a box block is byte-identical
  across the three, in both languages.
- **Pivots and zones:** `DoubleSwingLevelBreakRetestFail`,
  `UndercutOfLowerSwingBelowLevelPair`, `SupportBreakResistanceThenReclaim`,
  `RedRunThroughStackedSupportFade`, `FractalBoxBreakout`, `LateFractalFade`,
  `FractalTrendlineBreak`, `SwingRegressionTrend`, `SwingStructureTrend`,
  `SwingLowRejection`, `SwingHighClusterDecisiveBreak`, `LevelPairPivotBreakout`.
- **Visit scan:** `LevelRejectedFromAbove`, `LevelBodyDominated`,
  `LevelForwardDrift`, `LevelWasTrending`, `LevelHighVolume`.
- **Breakouts:** `BreakoutDirectionShare`, `ConsecutiveUpsideBreakouts`,
  `NewExtremeFrequency`, `NewWindowLowAboveLongerLow`, `BreakoutClearsByHalfBar`,
  `ConsolidationBreakoutBar`, `ConsolidationBreakoutFirstRetest`.
- **Bands and oscillators:** `UpperBandTouchBarBreak`,
  `BandHighThenMidlineRetrace`, `BollingerWidthBelowAverage`,
  `TrueRangeCoefficientOfVariation`, `RsiTightBandExitBarColour`,
  `RsiBandBreakThenOppositeBar`, `AdxFallingMomentumFade`, `AdxRisingExit`.
- **Moving averages and momentum:** `FastEmaAboveSlowEma`,
  `EmaTouchAfterLongAbsence`, `MaWickTouchesHoldSide`, `MaSideFlipRun`,
  `MomentumLadder`.
- **Exits:** `ExitOnReturnThroughBreakoutPoint`, `TargetAtSignalBarOpen`.

What was checked:

- **Pivot tests:** every hand-rolled scan uses the measured mixed test: strict
  against the newer bars, inclusive against the older ones.
- **Bars that are both a swing high and a swing low:** they are ordered correctly
  in both scan directions. A newest-first scan pushes the high first on a green
  bar; an oldest-first scan pushes the low first.
- **Regression slope signs:** consistent. `FractalTrendlineBreak` works in bars-ago
  slope, `SwingRegressionTrend` negates to a forward slope, and each catalog row
  matches its rule.
- **Ring buffers:** every one is read newest-first at the right lag
  (`ConsolidationBreakoutFirstRetest` reads ATR at [kk+1];
  `EmaTouchAfterLongAbsence` and `MaSideFlipRun` read EMA history).
- **Lagged indicators:** `atrPrev` and `atrVal[1]` both start at 0, and the RSI and
  ADX histories are zero-filled, as EL's are.

## 4. The two amendments

- **`RangeWidthBelowAtrMultiple`.** At `lag` 0 the C++ is numerically identical to
  HEAD.
  - The window starts at `high[0]`/`low[0]` and scans the same bars in the same
    order.
  - The ATR block is unchanged.
  - `atrLagged` comes from a one-slot ring and equals this bar's `atr`, so the
    conditions compare the same doubles with the same `el_le`.

  The EL moved `WFSafe_AvgTrueRange` out of the two conditions into one hook call,
  `atrVal`, read at `[lag]`. The TS writer evaluates every condition on every bar
  (`strategyWriter._entrySegment`, with no short-circuit). So the two old call
  sites and the new single site produce the same value on every bar.
  `Highest(...)[0]` is `Highest(...)`. Input names and defaults are unchanged, and
  `lag(0)` was added. The reaches-back expression is updated to
  `max(lag + rangeLookback - 1, atrLookback + 1)`.
- **`AvgBodyBelowRangeFraction`.** At `lag` 0 the C++ loop runs over
  `i = 0 .. lookback-1`, as before, and the EL `Average(...)[0]` is
  `Average(...)`. Input names and defaults are unchanged, and `lag(0)` was added.
  Reaches back to `lag + lookback - 1`.
- **Action:** none.

## 5. Other concerns

1. **`RedRunThroughStackedSupportFade` code and row disagree.** The row says "this
   bar is the first in the run to close below the lower zone's bottom". Both twins
   test only the previous bar: `(runK == 1 || el_ge(close[1], zLLo))` in the C++
   (BE json line 126 hook, long; short mirrored with `zUHi`), and the same test in
   the EL (TS json line 45). The two diverge when an earlier red bar in the run
   closed below the zone and a gapped-up red bar then closed back above it.
   **Action:** in both twins, loop over bars `1..runK-1` (Brian to confirm which
   reading he wants), or reword the row to "the previous bar closed at or above
   it".
2. **`ChannelFailedSwingFromHitSide`: the box anchors count as hits.** At latch, the
   hit scan covers bars `0..boxBarA`, which includes A, sitting on `boxLow`, and B,
   sitting on `boxHigh`. Until price touches a side again, the newer anchor (B)
   decides the "most recently hit side", and the inner-swing sequence may start
   from it. **Action:** Brian to confirm. If anchors should not count, start the
   scan below `boxBarB`. Either way, say it in the row.
3. **Warm-up of the `[lag]` reads is unmeasured.** This affects
   `Highest(...)[lag]`, `Lowest(...)[lag]` and `Average(...)[lag]` in the
   amendments, and `Highest(High, n)[1]` in several new rules, on the first `lag`
   bars after MaxBarsBack. The C++ reads real prices. If EL returns function
   history that is 0 before the first calculated bar, the twins differ during
   warm-up only. The same idiom is already in `BarRangeBelowAverageMultiple` and
   `StopBeyondRecentRangeExtreme`. **Action:** none now; it is a candidate for a
   later probe.
4. **`NewWindowLowAboveLongerLow`: a fractional `longFactor` is unsafe.** The C++
   truncates `(int)(longFactor*lookback)`, while EL passes a fractional Length. The
   row documents this. **Action:** keep `longFactor` on whole-number grids in every
   template.
