# Own-rules platinum-validation study: families and pools

This is the selection for repeating the platinum-validation test (36-month held-out OOS)
on Brian's own rules (`reference/my_onenote/`). It runs alongside the Davey run
(`202608 BAS-*`) and the Brooks run (`202611 BRK-*`).

Files:
- `grids/A..D.json`: per-rule grids and roles, from four agents following `GRID_BRIEF.md`.
- `buildPools.py`: builds `pools.json`.
- `drawOwnStudy.py`: draws from `pools.json` into `assignment.json`.
- `makeOwnTemplates.py`: writes `templates/202611 OWN-01..64.json` and verifies them.

Re-running the three scripts gives byte-identical output. The seed is 20261106; the draw took attempt 0, with a total spread of 6.

## Shape (Brian, 2026-11-06)

Every family has 360 versions, and every template contains pure stop-and-reverse
(panes 3-5 empty) for each pane-1 x pane-2 pair.

| | Setup families OWN-01..50 | Condition families OWN-51..64 |
|---|---|---|
| Pane 1 | own setup \| reverse (2) | classic trend entry \| reverse \| classic mean-reversion entry \| reverse (4, pinned) |
| Pane 2 | empty \| own trend condition \| own regime condition \| classic filter (4, pinned) | condition \| flipped (mirrored) or negated (same-sided) (2, gridded). No empty group |
| Pane 3 | empty \| money/volatility stop \| structural stop | same |
| Pane 4 | empty \| 4 exits from at least 3 categories | same |
| Pane 5 | empty \| 2 switches | same |

Orientation:
- A trend condition is placed as authored for with-trend and breakout setups, and flipped (`~`) for reversal and range setups.
- `MaStackGapNarrowing` is a reversal-context condition (its long side is a downtrend losing steam), so it is oriented the other way round.
- Regime conditions are never flipped.

## Pools

- **Stops, exits and switches:** the Brooks study's pools unchanged, so both arms meet the same exits. The exit pool adds three:
  - `CalendarBoundaryExit` (pinned 7/6) and `ClosePercentileExit` (lookback 5..20/5), the two EEC/Davey exits Brian added back;
  - `AdxRisingExit` (compareBars 5..20/5), from Brian's notes.

  `TargetAtSignalBarOpen` and `ExitOnReturnThroughBreakoutPoint` stay out, because each depends on its own entry.
- **Own pane-2 conditions** (14):
  - 6 trend or reversal-context;
  - 8 regime.
- **Classic filters** (pinned):
  - `DaveyMomentum` (`Momentum` 50, pane 2 only, per Brian);
  - `CloseAboveSma` (100);
  - `AdxTrending` (ADX(14) at or above 25);
  - `AdxQuiet` (ADX(14) below 20);
  - `AtrExpanding` (ATR(15) above its 20-bar average).
- **Classic entries** (pinned):
  - trend-following: `Donchian20` (`HighestHighBreakout` 20) and `MaCross10x30`;
  - mean-reversion: `BollingerCross` (20/2), `KeltnerCross` (20/2) and `RsiExtreme` (14/30).

  The band-cross and MA-cross rows cite EEC terms. These are classic constructs, used where Brian said classic entries are fine.

Balance: each own trend condition appears 8-9 times and each regime condition 6-7. Each classic filter appears 10 times. Classic entries appear 7 times (trend) and 4-5 times (mean-reversion). Each exit appears 4-5 times, and each switch 9-10.

## Setup families

| Rule | Type | Setup it. | M1440 estimate |
|---|---|---|---|
| ChannelFailedSwingFromHitSide | range | 9 | smoke 148 -> ~10 at default (5/30); strength 4 / anchor 20 corner looser (~15-20), 6/40 corner ~5 |
| ChannelInnerSwingBreakFade | range | 9 | smoke 9 -> ~0.6 at default; looser corner (3/20) maybe ~3-5; plainly rare |
| InnerBoxFalseBreakReclaim | range | 9 | smoke 7 -> ~0.5 at default; looser corner (3 / 1 ATR) maybe ~3-5; plainly rare |
| DoubleSwingLevelBreakRetestFail | breakout | 9 | smoke 8 -> ~0.6 at default (7/0.25); looser corner (3/0.75) maybe ~5; plainly rare |
| UndercutOfLowerSwingBelowLevelPair | range | 9 | smoke 6 -> ~0.4 at default; looser corner (0.75 / 0.5) maybe ~2-3; plainly rare |
| SupportBreakResistanceThenReclaim | range | 6 | smoke 14 -> ~1 at default (3/2); looser corner (2/1) maybe ~4-6; selective corner (3/3) plainly rare |
| RedRunThroughStackedSupportFade | reversal | 9 | smoke 74 -> ~5 at default; zoneSize 2 / run 15 corner maybe ~10; zoneSize 4 / run 5 corner ~1-2 |
| FractalBoxBreakout | breakout | 3 | smoke 149 -> ~10 at default (strength 2); strength 1 ~2-3x more, strength 3 ~5 |
| LateFractalFade | reversal | 9 | smoke 274 -> ~19 at default (2/2); 3/3 corner maybe ~5 |
| FractalOrderLowHighHigh | with-trend | 3 | smoke 655 -> ~45 at default; strength 4 maybe ~20 |
| FractalLegSlopeDecay | reversal | 3 | smoke 977 -> ~68 at default; strength 4 maybe ~30 |
| FractalMovePullbackContraction | with-trend | 9 | smoke 236 -> ~16 at default (4/0.5); 3/0.8 corner ~25, 5/0.4 corner ~6 |
| FractalTrendlineBreak | reversal | 6 | smoke 528 -> ~37 at default (3/0.8); selective corner 4/0.9 perhaps ~15-20 |
| SwingHighClusterDecisiveBreak | breakout | 6 | smoke 20 -> ~1.4 at default; looser grid (breakTol = Y, tol 0.5-1.0, strength 1) guess ~5-15; strength 2 / tol 0.5 corner still rare |
| SwingLowRejection | with-trend | 9 | smoke 1042 alone -> ~72; with HigherSwingLow roughly half, ~30-40 at centre; corner 0.15/0.45 perhaps ~15 |
| LevelPairPivotBreakout | breakout | 9 | smoke 38 -> ~2.6 at default (0.05/1.0); looser corner 0.3/0.5 guess ~15-20; selective corner 0.1/1.0 ~5 |
| LargeBarTightPauseNearHigh | with-trend | 9 | smoke 44 -> ~3 at default (3 bars, 2 ATR); 3/1.5 guess ~8; corner 5/2.0 ~1 |
| LargeBarHoldThenCloseThroughMidpoint | reversal | 9 | smoke 72 -> ~5 at default (5 bars, 2 ATR); looser corner 3/1.5 guess ~15; corner 5/2.0 ~5 |
| LargeBarAtExtremeNextBarExtendsWeakClose | breakout | 9 | smoke 126 -> ~9 at default (1.5 ATR, 20 bars); looser corner 1.0/10 guess ~25; corner 1.5/30 ~7 |
| HugeBarOppositeInsideBarThenResume | with-trend | 9 | smoke 43 -> ~3 at default (2 ATR, quarter shapes, 20); with nearFraction 0.333 and 1.5 ATR guess ~10; corner 2.0/30 ~3 |
| LargeBarInsideRunCloseBeyond | breakout | 9 | smoke 23 -> ~1.6 at default (2 bars, 1 ATR); 1/0.5 guess ~15; corner 3/1.0 ~1 |
| NewWindowLowAboveLongerLow | with-trend | 6 | smoke 370 -> ~26 at default (25 x 2); corner 40 x 3 guess ~12 |
| BearBarTopHalfUntouchedLong | reversal | 9 | smoke 281 -> ~20 at default (12, 0.6); corner 14/0.7 guess ~12 |
| BreakawayPullbackBreak | breakout | 9 | smoke 0 at default (k 1.0, f 0.25); looser grid unmeasured, guess ~5-15 at 0.5/0.5, corner 1.0/0.3 near 0 |
| ExtremePairRetraceEntry | with-trend | 9 | smoke 1005 -> ~70 at default (7, 0.5); corner 9/0.4 guess ~40 |
| DonchianOutsizedBreakoutFade | reversal | 5 | smoke 191 -> ~13 at default (20); N 10 guess ~30, N 30 ~8 |
| BreakoutClearsByHalfBar | breakout | 5 | smoke 417 -> ~29 at default (20); X 10 guess ~45, X 30 ~22 |
| ConsolidationBreakoutBar | breakout | 9 | smoke 330 bare (no zone gate) -> ~23; with the zone gate est ~5-10 at centre; tight corner (0.75 ATR margin, 3 ATR zone) ~2-3 |
| ConsolidationBreakoutFirstRetest | breakout | 9 | smoke 6 at default (20/3/0.5/10) -> ~0.4; loosened grid est ~1-2 at the 20/3 corner, ~5-10 at 10/5. Plainly rare |
| ConsolidationBreakoutBarHighClose | breakout | 9 | smoke 15 at default -> ~1; loosened grid est ~3 at 20/3, ~10-15 at 10/5. Rare |
| BreakoutCandleClassSequence | breakout | 6 | smoke 29 at lookback 50 -> ~2; lookback 10-30 makes breakout candles several times commoner, est ~5-15 at centre; the 30/minC 2 corner is rare |
| BreakoutDirectionShare | with-trend | 9 | smoke 331 -> ~23 at default; a persistent state, so flips fall slowly with breakoutBars/eventCount |
| ConsecutiveUpsideBreakouts | with-trend | 9 | smoke 407 -> ~28 at default (20/3) |
| RsiBandBreakThenOppositeBar | reversal | 6 | smoke 0 at default (40-60 held 50 bars). Est ~3-10 at 15/20; the 15/30 corner is rare. Count risk high |
| RsiTightBandExitBarColour | breakout | 6 | smoke 218 -> ~15 at default (5/5); 5/7 corner est ~8 |
| RsiDivergenceAtWindowExtreme | reversal | 5 | smoke 515 -> ~36 at default |
| AdxFallingMomentumFade | reversal | 5 | smoke 2700 -> ~190 (a state that flips often) |
| MomentumLadder | with-trend | 4 | smoke 165 -> ~11 at 20; est ~20 at 10, ~5 at 40 |
| UpperBandTouchHigherHigh | breakout | 9 | smoke 460 -> ~32 at default |
| UpperBandTouchBarBreak | breakout | 9 | smoke 484 -> ~34 at default |
| BandHighThenMidlineRetrace | with-trend | 3 | smoke 792 -> ~55 at default (middle band) |
| EmaInvertedBarsAboveSlow | breakout | 9 | smoke 189 -> ~13 at default; runBars 2 corner ~20, runBars 4 corner ~8 |
| DoubleEmaTouchRun | reversal | 3 | DoubleEmaTouchRun alone (same-sided) smoke 1130 -> ~78; with the flipped MA-order placement roughly half the touch runs, ~30-40 at runBars 3, ~15 at runBars 5 |
| MaDistanceRegime | with-trend | 9 | smoke 69 -> ~5 at default (= the tight corner 1.0/0.25); loose corner 0.5/0.75 perhaps ~20-30 |
| EmaTouchAfterLongAbsence | breakout | 12 | smoke 129 -> ~9 at default (200/3, the tight corner); loose corner 100/1.5 perhaps ~25 |
| BodyMaBandBreakout | breakout | 9 | smoke 1157 -> ~80 at default (a state; count ~ side changes); 2.0 corner well under half that |
| MaSideFlipRun | breakout | 9 | smoke 198 -> ~14 at default (3/10); 2/5 corner ~25+, 4/15 corner ~6-8 |
| LevelRejectedFromAbove | range | 9 | smoke 189 -> ~13 at default (5/0.6); loose corner 3/0.5 ~25, tight 7/0.7 ~5 |
| LevelForwardDrift | range | 9 | smoke 886 -> ~60 at default (10/0.5); tight 15/1.5 corner perhaps ~10 |
| LevelThinAir | breakout | 9 | smoke 618 -> ~43 at default (2/10); maxVisits 0 corner ~20-30 |

Clusters:
- `DoubleEmaTouchRun` + `FastEmaAboveSlowEma`~ (both 25/50; note #39);
- `ConsolidationBreakoutBar` + `RangeWidthBelowAtrMultiple` (lag 1, 15/15; the consolidation zone);
- `SwingLowRejection` + `HigherSwingLow` (strength 2; note P13's higher swing low).

## Condition families

| Condition | Kind | Sides | Condition it. |
|---|---|---|---|
| SwingRegressionTrend | trend | mirrored | 9 |
| SwingStructureTrend | trend | mirrored | 3 |
| NewExtremeFrequency | trend | mirrored | 9 |
| RangeOutsidePriorRangeFraction | regime | same | 9 |
| QuietBodiesBeforeBar | regime | same | 9 |
| TrueRangeCoefficientOfVariation | regime | same | 9 |
| BollingerWidthBelowAverage | regime | same | 9 |
| FastEmaAboveSlowEma | trend | mirrored | 9 |
| MaStackGapNarrowing | reversal-context | mirrored | 9 |
| MaWickTouchesHoldSide | trend | mirrored | 9 |
| LevelBodyDominated | regime | same | 9 |
| LevelWasTrending | regime | same | 9 |
| LevelBigBars | regime | same | 9 |
| LevelHighVolume | regime | same | 9 |

## Assignment

| Family | Pane 1 | Pane 2 | Stops | Exits | Switches | MBB | Worst it. |
|---|---|---|---|---|---|---|---|
| OWN-01 | ChannelFailedSwingFromHitSide | FastEmaAboveSlowEma~, RangeOutsidePriorRangeFraction, AtrExpanding | BracketDollar2R, BeyondSignalBar | FailedTargetReversal, LegOneEqualsLegTwo, FailedCountSetup, NumBars | TrendFilterSwitch, DayOfWeekSwitch | 250 | 36 |
| OWN-02 | ChannelInnerSwingBreakFade | MaWickTouchesHoldSide~, LevelHighVolume, AtrExpanding | AdrFractionStop, BeyondExtremeSinceEntry | MicroChannelBreakout, EntryBarExtreme, ChannelLineTarget, TrailAfterEmaBreak | LosingStreakCooldown, DailyLossLimit | 500 | 36 |
| OWN-03 | InnerBoxFalseBreakReclaim | FastEmaAboveSlowEma~, TrueRangeCoefficientOfVariation, AdxTrending | BracketRatioStop, BeyondSpikeStart | DelayedSwingTrail, TrendBarFails, ChannelBounceFraction, SessionOpenPrice | GapBarSwitch, WeeklyProfitTarget | 250 | 27 |
| OWN-04 | DoubleSwingLevelBreakRetestFail | MaStackGapNarrowing~, LevelBigBars, AtrExpanding | BracketAtr2R, BeyondRecentRange | CalendarBoundaryExit, AtrTrailingStop, PriorRangeExtreme, OppositeStrongTrendBar | WeeklyLossLimit, HighVolatilitySwitch | 500 | 36 |
| OWN-05 | UndercutOfLowerSwingBelowLevelPair | MaStackGapNarrowing, LevelHighVolume, AdxQuiet | RecentRangeStop, FractionOfSignalRisk | BreakevenStop, SwingHighProfitTarget, EntryBarExtreme, OpposingCount | HighVolatilitySwitch, DayOfWeekSwitch | 500 | 36 |
| OWN-06 | SupportBreakResistanceThenReclaim | FastEmaAboveSlowEma~, QuietBodiesBeforeBar, CloseAboveSma~ | BracketAtr2R, BeyondSpikeStart | AtrTrailingStop, ConsecutiveClimax, GapFilled, TimeOfDayExit | HighVolatilitySwitch, MonthlyLossLimit | 250 | 24 |
| OWN-07 | RedRunThroughStackedSupportFade | MaWickTouchesHoldSide~, BollingerWidthBelowAverage, AtrExpanding | AdrFractionStop, BeyondExtremeSinceEntry | FailedScalp, ConsecutiveTrendBarsClimax, ProfitProtectorRatio, ClosePercentileExit | GapBarSwitch, WeeklyProfitTarget | 500 | 36 |
| OWN-08 | FractalBoxBreakout | SwingRegressionTrend, LevelHighVolume, AdxTrending | BracketRatioStop, BeyondSignalBar | ChannelBounceFraction, ClimaxAfterTrendRun, ProfitProtector, AdxRisingExit | DayOfWeekSwitch, DailyLossLimit | 500 | 12 |
| OWN-09 | LateFractalFade | MaStackGapNarrowing, RangeOutsidePriorRangeFraction, CloseAboveSma~ | StopLoss5000, BeyondSignalBar | ParabolicAcceleration, AtrProfitTarget, WeakEntryBarScratch, ClimaxAfterTrendRun | HighVolatilitySwitch, WeeklyLossLimit | 250 | 36 |
| OWN-10 | FractalOrderLowHighHigh | SwingRegressionTrend, LevelWasTrending, CloseAboveSma | BracketDollar2R, BeyondSwingAtEntry | BreakevenAfterAdverse, TrailAfterEmaBreak, PatternHeightMM, OppositeStrongTrendBar | TightRangeBlocksEntries, WeeklyLossLimit | 500 | 12 |
| OWN-11 | FractalLegSlopeDecay | NewExtremeFrequency~, QuietBodiesBeforeBar, AtrExpanding | SignalBarRange2x, TightenToStrongEntryBar | TrailAfterProfit, MovingAverageTarget, ThreePushCompletion, ConsecutiveTrendBarsClimax | MonthlyProfitTarget, MonthlyLossLimit | 250 | 12 |
| OWN-12 | FractalMovePullbackContraction | NewExtremeFrequency, LevelWasTrending, DaveyMomentum | SignalBarRange2x, BeyondSignalBar | OppositeStrongTrendBar, TrailAfterProfit, NumBarsIfLosing, WeakEntryBarExit | DayOfWeekSwitch, TrendFilterSwitch | 500 | 36 |
| OWN-13 | FractalTrendlineBreak | SwingStructureTrend~, LevelBigBars, AdxQuiet | RecentRangeStop, TightenToStrongEntryBar | ConsecutiveTrendBarsClimax, TieredProfitProtector, LegOneEqualsLegTwo, MovingAverageTarget | WeeklyProfitTarget, MaxTradesPerSession | 500 | 24 |
| OWN-14 | SwingHighClusterDecisiveBreak | NewExtremeFrequency, RangeOutsidePriorRangeFraction, AdxTrending | SessionAvgBarStop, BeyondSignalBar | OpposingCount, ParabolicAcceleration, PatternHeightMM, BreakevenAfterEmaRun | GapBarSwitch, WeeklyLossLimit | 250 | 24 |
| OWN-15 | SwingLowRejection | FastEmaAboveSlowEma, RangeOutsidePriorRangeFraction, DaveyMomentum | SessionAvgBarStop, BeyondSwingAtEntry | TrailingStop, ConsecutiveCloseExit, RollingRangeMidpointMM, FailedScalp | TightRangeBlocksEntries, LosingStreakCooldown | 250 | 36 |
| OWN-16 | LevelPairPivotBreakout | SwingRegressionTrend, LevelBigBars, DaveyMomentum | BracketRatioStop, BeyondSignalBar | RangeMidpoint, TrailBehindStrongBar, SessionOpenPrice, ShrinkingSwingIncrements | HighVolatilitySwitch, DailyLossLimit | 500 | 27 |
| OWN-17 | LargeBarTightPauseNearHigh | FastEmaAboveSlowEma, LevelHighVolume, AdxTrending | BracketRatioStop, BeyondRecentRange | ClimaxAfterTrendRun, BreakevenAfterAdverse, TrailBehindStrongBar, GapMidpointMM | WeeklyLossLimit, MaxTradesPerSession | 500 | 36 |
| OWN-18 | LargeBarHoldThenCloseThroughMidpoint | FastEmaAboveSlowEma~, QuietBodiesBeforeBar, AdxQuiet | RecentRangeStop, BeyondSpikeStart | ClimaxAfterTrendRun, EntryBarExtreme, RollingRangeMidpointMM, ProfitProtector | MonthlyLossLimit, MaxTradesPerSession | 250 | 36 |
| OWN-19 | LargeBarAtExtremeNextBarExtendsWeakClose | NewExtremeFrequency, LevelBodyDominated, AdxQuiet | SessionAvgBarStop, FractionOfSignalRisk | AtrProfitTarget, NumBarsIfLosing, BarHeightMM, TrailAfterEmaBreak | LosingStreakCooldown, TightRangeBlocksEntries | 500 | 36 |
| OWN-20 | HugeBarOppositeInsideBarThenResume | MaWickTouchesHoldSide, BollingerWidthBelowAverage, AtrExpanding | SignalBarRange2x, BeyondSpikeStart | BreakevenStop, SessionMidpoint, ChannelBounceFraction, WeakEntryBarScratch | MonthlyLossLimit, GapBarSwitch | 250 | 36 |
| OWN-21 | LargeBarInsideRunCloseBeyond | FastEmaAboveSlowEma, QuietBodiesBeforeBar, AdxTrending | StopLoss5000, TightenToStrongEntryBar | RangeHeightProjection, SwingPointTrail, ConsecutiveCloseExit, AdverseBodyCount | LowAdxSwitch, DailyLossLimit | 250 | 36 |
| OWN-22 | NewWindowLowAboveLongerLow | SwingStructureTrend, LevelBodyDominated, AdxQuiet | BracketAtr2R, TightenToStrongEntryBar | ProfitProtectorRatio, BarHeightMM, FailedCountSetup, WeakFollowThrough | MaxTradesPerSession, DayOfWeekSwitch | 500 | 24 |
| OWN-23 | BearBarTopHalfUntouchedLong | MaStackGapNarrowing, LevelHighVolume, AdxTrending | SignalBarRange2x, BeyondExtremeSinceEntry | BreakevenSecondTest, SwingHighProfitTarget, TimeOfDayExit, TrailAfterProfit | HighVolatilitySwitch, WeeklyProfitTarget | 500 | 36 |
| OWN-24 | BreakawayPullbackBreak | NewExtremeFrequency, LevelWasTrending, AtrExpanding | RecentRangeStop, BeyondRecentRange | ProfitProtectorRatio, AdxRisingExit, ConsecutiveTrendBarsClimax, TakeProfit | MaxTradesPerSession, LowAdxSwitch | 500 | 36 |
| OWN-25 | ExtremePairRetraceEntry | SwingStructureTrend, TrueRangeCoefficientOfVariation, AdxQuiet | BracketDollar2R, BeyondExtremeSinceEntry | TrendBarFails, BreakevenRetest, BreakevenAfterEmaRun, EntryBarExtreme | WeeklyLossLimit, GapBarSwitch | 500 | 36 |
| OWN-26 | DonchianOutsizedBreakoutFade | MaStackGapNarrowing, LevelBodyDominated, DaveyMomentum~ | BracketRatioStop, BeyondSwingAtEntry | ShrinkingSwingIncrements, PullbackSizedTarget, TrailingStop, ConsecutiveClimax | LosingStreakCooldown, DayOfWeekSwitch | 500 | 20 |
| OWN-27 | BreakoutClearsByHalfBar | MaStackGapNarrowing~, BollingerWidthBelowAverage, AdxTrending | BracketDollar2R, BeyondRecentRange | BreakevenStop, BreakevenAfterAdverse, ClosePercentileExit, PriorRangeExtreme | GapBarSwitch, HighVolatilitySwitch | 250 | 20 |
| OWN-28 | ConsolidationBreakoutBar | MaWickTouchesHoldSide, TrueRangeCoefficientOfVariation, AtrExpanding | StopLoss5000, BeyondRecentRange | BreakevenSecondTest, GapMidpointMM, TrendBarFails, WeakEntryBarScratch | MonthlyProfitTarget, TightRangeBlocksEntries | 250 | 27 |
| OWN-29 | ConsolidationBreakoutFirstRetest | MaWickTouchesHoldSide, LevelWasTrending, AtrExpanding | AdrFractionStop, BeyondExtremeSinceEntry | SwingPivotTarget, RangeHeightProjection, OpposingCount, BreakevenAfterAdverse | TrendFilterSwitch, WeeklyProfitTarget | 500 | 36 |
| OWN-30 | ConsolidationBreakoutBarHighClose | MaWickTouchesHoldSide, BollingerWidthBelowAverage, AdxQuiet | StopLoss5000, FractionOfSignalRisk | DelayedSwingTrail, TrailBehindStrongBar, AdxRisingExit, PatternHeightMM | MonthlyProfitTarget, TrendFilterSwitch | 250 | 36 |
| OWN-31 | BreakoutCandleClassSequence | SwingRegressionTrend, LevelWasTrending, AdxQuiet | BracketRatioStop, BeyondExtremeSinceEntry | SwingPointTrail, FailedTargetReversal, NumBars, AdxRisingExit | MonthlyProfitTarget, LowAdxSwitch | 500 | 24 |
| OWN-32 | BreakoutDirectionShare | SwingStructureTrend, LevelBigBars, AdxTrending | BracketAtr2R, TightenToStrongEntryBar | SwingHighProfitTarget, TrailAfterProfit, CountertrendScalpAtr, TimeOfDayExit | MonthlyLossLimit, MonthlyProfitTarget | 500 | 36 |
| OWN-33 | ConsecutiveUpsideBreakouts | SwingStructureTrend, LevelBodyDominated, AdxQuiet | BracketAtr2R, BeyondSwingAtEntry | ConsecutiveCloseExit, MovingAverageTarget, BarHeightMM, CalendarBoundaryExit | LowAdxSwitch, GapBarSwitch | 500 | 27 |
| OWN-34 | RsiBandBreakThenOppositeBar | NewExtremeFrequency~, TrueRangeCoefficientOfVariation, DaveyMomentum~ | BracketRatioStop, TightenToStrongEntryBar | LegOneEqualsLegTwo, ConsecutiveClimax, DelayedSwingTrail, PullbackSizedTarget | WeeklyProfitTarget, LosingStreakCooldown | 250 | 24 |
| OWN-35 | RsiTightBandExitBarColour | FastEmaAboveSlowEma, LevelBigBars, DaveyMomentum | AdrFractionStop, FractionOfSignalRisk | NumBarsIfLosing, WeakFollowThrough, TieredProfitProtector, BreakevenAfterEmaRun | TightRangeBlocksEntries, LosingStreakCooldown | 500 | 24 |
| OWN-36 | RsiDivergenceAtWindowExtreme | SwingStructureTrend~, RangeOutsidePriorRangeFraction, CloseAboveSma~ | BracketDollar2R, BeyondRecentRange | WeakEntryBarExit, NumBarsIfProfitable, TakeProfit, SwingPointTrail | HighVolatilitySwitch, TightRangeBlocksEntries | 500 | 20 |
| OWN-37 | AdxFallingMomentumFade | NewExtremeFrequency~, LevelBodyDominated, CloseAboveSma~ | RecentRangeStop, BeyondSpikeStart | BreakevenSecondTest, ThreePushCompletion, SessionOpenPrice, RollingRangeMidpointMM | DailyLossLimit, LosingStreakCooldown | 500 | 15 |
| OWN-38 | MomentumLadder | MaWickTouchesHoldSide, BollingerWidthBelowAverage, CloseAboveSma | SessionAvgBarStop, BeyondSignalBar | BreakevenSecondTest, BarHeightMM, RangeHeightProjection, FailedCountSetup | LowAdxSwitch, WeeklyLossLimit | 250 | 16 |
| OWN-39 | UpperBandTouchHigherHigh | MaStackGapNarrowing~, LevelWasTrending, CloseAboveSma | BracketDollar2R, BeyondSwingAtEntry | TakeProfit, SwingPointTrail, SwingHighProfitTarget, FailedTargetReversal | HighVolatilitySwitch, MaxTradesPerSession | 500 | 36 |
| OWN-40 | UpperBandTouchBarBreak | SwingRegressionTrend, TrueRangeCoefficientOfVariation, CloseAboveSma | BracketRatioStop, BeyondSpikeStart | AtrProfitTarget, PullbackSizedTarget, ThreePushCompletion, TrailBehindStrongBar | MonthlyLossLimit, LowAdxSwitch | 250 | 36 |
| OWN-41 | BandHighThenMidlineRetrace | NewExtremeFrequency, LevelWasTrending, DaveyMomentum | SessionAvgBarStop, TightenToStrongEntryBar | MovingAverageTarget, ParabolicAcceleration, TieredProfitProtector, TakeProfit | LowAdxSwitch, TightRangeBlocksEntries | 500 | 12 |
| OWN-42 | EmaInvertedBarsAboveSlow | SwingStructureTrend, RangeOutsidePriorRangeFraction, AdxTrending | SessionAvgBarStop, BeyondRecentRange | WeakEntryBarExit, PriorRangeExtreme, NumBarsIfProfitable, ConsecutiveCloseExit | MaxTradesPerSession, LosingStreakCooldown | 500 | 36 |
| OWN-43 | DoubleEmaTouchRun | SwingRegressionTrend~, LevelHighVolume, CloseAboveSma~ | RecentRangeStop, BeyondRecentRange | NumBarsIfProfitable, SwingPivotTarget, GapMidpointMM, FirstOppositeBodyAfterRun | MaxTradesPerSession, WeeklyProfitTarget | 500 | 12 |
| OWN-44 | MaDistanceRegime | SwingStructureTrend, QuietBodiesBeforeBar, DaveyMomentum | BracketDollar2R, BeyondSpikeStart | ConsecutiveClimax, LegOneEqualsLegTwo, TrailingStop, RangeMidpoint | DayOfWeekSwitch, DailyLossLimit | 500 | 36 |
| OWN-45 | EmaTouchAfterLongAbsence | SwingRegressionTrend, QuietBodiesBeforeBar, DaveyMomentum | AdrFractionStop, BeyondSwingAtEntry | ProfitProtector, ChannelLineTarget, WeakFollowThrough, OpposingCount | LowAdxSwitch, WeeklyProfitTarget | 500 | 48 |
| OWN-46 | BodyMaBandBreakout | MaStackGapNarrowing~, LevelBigBars, DaveyMomentum | StopLoss5000, BeyondExtremeSinceEntry | SwingPivotTarget, MicroChannelBreakout, PriorRangeExtreme, BreakevenStop | LosingStreakCooldown, MonthlyLossLimit | 500 | 36 |
| OWN-47 | MaSideFlipRun | MaWickTouchesHoldSide, BollingerWidthBelowAverage, AdxTrending | SessionAvgBarStop, FractionOfSignalRisk | ClosePercentileExit, GapMidpointMM, NumBars, AtrProfitTarget | DayOfWeekSwitch, LowAdxSwitch | 250 | 36 |
| OWN-48 | LevelRejectedFromAbove | SwingRegressionTrend~, RangeOutsidePriorRangeFraction, CloseAboveSma~ | AdrFractionStop, FractionOfSignalRisk | FailedScalp, BreakevenRetest, AdverseBodyCount, NumBarsIfLosing | GapBarSwitch, MonthlyProfitTarget | 500 | 36 |
| OWN-49 | LevelForwardDrift | NewExtremeFrequency~, LevelBodyDominated, AtrExpanding | StopLoss5000, BeyondSignalBar | CountertrendScalpAtr, ParabolicAcceleration, TrailAfterEmaBreak, OppositeStrongTrendBar | DailyLossLimit, MonthlyProfitTarget | 500 | 36 |
| OWN-50 | LevelThinAir | SwingRegressionTrend, TrueRangeCoefficientOfVariation, AdxQuiet | SignalBarRange2x, BeyondSwingAtEntry | TimeOfDayExit, CalendarBoundaryExit, ShrinkingSwingIncrements, AtrTrailingStop | GapBarSwitch, HighVolatilitySwitch | 500 | 36 |
| OWN-51 | MaCross10x30, MaCross10x30~, BollingerCross, BollingerCross~ | SwingRegressionTrend, SwingRegressionTrend~ | SessionAvgBarStop, BeyondSpikeStart | FirstOppositeBodyAfterRun, LegOneEqualsLegTwo, RangeHeightProjection, AtrTrailingStop | DailyLossLimit, TightRangeBlocksEntries | 250 | 36 |
| OWN-52 | MaCross10x30, MaCross10x30~, BollingerCross, BollingerCross~ | SwingStructureTrend, SwingStructureTrend~ | StopLoss5000, BeyondSignalBar | WeakFollowThrough, GapFilled, PatternHeightMM, TieredProfitProtector | WeeklyLossLimit, DayOfWeekSwitch | 500 | 12 |
| OWN-53 | Donchian20, Donchian20~, KeltnerCross, KeltnerCross~ | NewExtremeFrequency, NewExtremeFrequency~ | BracketDollar2R, BeyondSpikeStart | FailedTargetReversal, SessionMidpoint, FailedCountSetup, WeakEntryBarScratch | MonthlyLossLimit, DayOfWeekSwitch | 250 | 36 |
| OWN-54 | MaCross10x30, MaCross10x30~, KeltnerCross, KeltnerCross~ | RangeOutsidePriorRangeFraction, RangeOutsidePriorRangeFraction! | AdrFractionStop, BeyondRecentRange | RollingRangeMidpointMM, ProfitProtectorRatio, TrailToMicroGap, ClosePercentileExit | MaxTradesPerSession, GapBarSwitch | 500 | 36 |
| OWN-55 | MaCross10x30, MaCross10x30~, BollingerCross, BollingerCross~ | QuietBodiesBeforeBar, QuietBodiesBeforeBar! | RecentRangeStop, BeyondSwingAtEntry | MicroChannelBreakout, CountertrendScalpAtr, PullbackSizedTarget, BreakevenRetest | MonthlyLossLimit, WeeklyProfitTarget | 250 | 36 |
| OWN-56 | MaCross10x30, MaCross10x30~, RsiExtreme, RsiExtreme~ | TrueRangeCoefficientOfVariation, TrueRangeCoefficientOfVariation! | AdrFractionStop, BeyondExtremeSinceEntry | AdverseBodyCount, ShrinkingSwingIncrements, RangeHeightProjection, TrailToMicroGap | TrendFilterSwitch, MonthlyProfitTarget | 500 | 36 |
| OWN-57 | Donchian20, Donchian20~, RsiExtreme, RsiExtreme~ | BollingerWidthBelowAverage, BollingerWidthBelowAverage! | SignalBarRange2x, TightenToStrongEntryBar | TrendBarFails, BreakevenAfterEmaRun, AtrTrailingStop, ChannelLineTarget | MonthlyProfitTarget, LosingStreakCooldown | 250 | 36 |
| OWN-58 | MaCross10x30, MaCross10x30~, BollingerCross, BollingerCross~ | FastEmaAboveSlowEma, FastEmaAboveSlowEma~ | BracketAtr2R, TightenToStrongEntryBar | ChannelLineTarget, TakeProfit, ProfitProtector, GapFilled | DailyLossLimit, TrendFilterSwitch | 250 | 36 |
| OWN-59 | Donchian20, Donchian20~, RsiExtreme, RsiExtreme~ | MaStackGapNarrowing, MaStackGapNarrowing~ | SignalBarRange2x, FractionOfSignalRisk | RangeMidpoint, CountertrendScalpAtr, NumBarsIfProfitable, BreakevenRetest | WeeklyProfitTarget, DailyLossLimit | 250 | 36 |
| OWN-60 | Donchian20, Donchian20~, RsiExtreme, RsiExtreme~ | MaWickTouchesHoldSide, MaWickTouchesHoldSide~ | BracketAtr2R, FractionOfSignalRisk | SessionMidpoint, FailedScalp, FirstOppositeBodyAfterRun, AdverseBodyCount | TrendFilterSwitch, MaxTradesPerSession | 250 | 36 |
| OWN-61 | Donchian20, Donchian20~, KeltnerCross, KeltnerCross~ | LevelBodyDominated, LevelBodyDominated! | BracketAtr2R, BeyondSwingAtEntry | TrailingStop, TrailToMicroGap, ChannelBounceFraction, ThreePushCompletion | TightRangeBlocksEntries, TrendFilterSwitch | 500 | 36 |
| OWN-62 | Donchian20, Donchian20~, KeltnerCross, KeltnerCross~ | LevelWasTrending, LevelWasTrending! | StopLoss5000, FractionOfSignalRisk | TrailToMicroGap, SessionOpenPrice, CalendarBoundaryExit, FirstOppositeBodyAfterRun | WeeklyLossLimit, MonthlyProfitTarget | 500 | 36 |
| OWN-63 | MaCross10x30, MaCross10x30~, BollingerCross, BollingerCross~ | LevelBigBars, LevelBigBars! | RecentRangeStop, BeyondExtremeSinceEntry | DelayedSwingTrail, NumBars, SwingPivotTarget, SessionMidpoint | LowAdxSwitch, TrendFilterSwitch | 500 | 36 |
| OWN-64 | Donchian20, Donchian20~, KeltnerCross, KeltnerCross~ | LevelHighVolume, LevelHighVolume! | SignalBarRange2x, BeyondSpikeStart | MicroChannelBreakout, GapFilled, RangeMidpoint, WeakEntryBarExit | TightRangeBlocksEntries, MonthlyLossLimit | 500 | 36 |

## Brian's decisions (2026-11-06)

1. **Grids below the note's figures:** accepted as listed (box swing strength 3..5 / 4..6, `LargeBarHoldThenCloseThroughMidpoint` minHoldBars 3-4, `LargeBarInsideRunCloseBeyond` minRangeAtr 0.5-0.75, `LargeBarAtExtremeNextBarExtendsWeakClose` 1.0-1.25, `RsiBandBreakThenOppositeBar` 10-30 bar hold with 35-65/30-70 bands, `BreakawayPullbackBreak` pullback band 0.4-0.5).
2. **Low-count families:** accepted as they are, like BRK-18.
3. **Max Bars Back:** option (a). 500 wherever a drawn member needs it (40 of 64 families), 250 elsewhere.
4. **`BandHighThenMidlineRetrace`:** option (c), the middle line only. `retraceDevs` is pinned at 0 and `maxWaitBars` at the default 15; highBars 10..30/10 is the only optimized input (3 iterations). Reading the note's "middle line or lower line" as "whichever is reached first" gives the same rule, since price passes the middle line first.
5. **Setup types:** kept as drawn, including range for `LevelForwardDrift` and `LevelRejectedFromAbove`.
6. **`SwingLowRejection` + `HigherSwingLow`:** fine.

Re-running the draw after decision 4 left every family's members and the pool usage unchanged; only OWN-41's setup grid moved.
