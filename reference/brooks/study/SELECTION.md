# Brooks platinum-validation study: rule selection

This is the selection for repeating the platinum-validation test on Al Brooks's
rules, so the results can be set against the Kevin Davey run (`templates/202608 BAS-*.json`).
The hypothesis being tested is that Davey's ideas decayed because they were
published. So this arm holds faithful, distinctively-Brooks price-action setups,
and it avoids anything that restates a Davey entry. Nothing here generates a
template. `pools.json` is the machine-readable form of this file, and
`drawStudy.py` turns it into `assignment.json`.

## Run shape this has to fit

- Dates come from `clonePlatinumSpecs.py`: WF 2007-01-01 -> 2019-04-01, incubation
  -> 2020-01-01, held-out OOS -> 2023-01-01. The `202608` specs then drop ETH and
  BTC, leaving 43 symbols.
- Timeframes are those of the 202608 platinum specs: 30, 60, 120, 180, 240, 360,
  480, 720 and 1440 minutes. Selection uses `trade_count` with `min_trades: 30`, so
  M1440 is the binding case: about 3,270 daily bars from 2007 to 2020.
- Max Bars Back is 250. The deepest reach in any pool is `HighVolatilitySwitch`
  (avgLookback 100) and `TrendFilterSwitch` (99). The deepest setup reach is about 63
  (three-push, lookbackBars 60 + swingStrength 3).
- Families tagged **intraday-only** (3 of 50) run on the **full** timeframe set like every other family (Brian, 2026-11-05; the tag now only steers the draw constraints).
  On M720 and M1440 their session logic degenerates: every daily bar is the
  session's first bar.

## Universe

The candidates are every Brooks rule on disk in **both** `rules/` and
`StrategyGeneratorTS/rules/`. That is 373 rules (306 Entry, 65 Exit, 2 Switch), taken
from all the `reference/brooks/author/rows/*.md` slices (A, B, T01-T08, 15_ema_*,
X1). The A_KEYS/B_KEYS tables alone give 236 Entry and 44 Exit. They leave out the
slice-15 EMA rules (`EmaTouchRecovery`, `EmaGapBarBreakoutEntry`, `EmaSlope`, ...), all
of T_KEYS (`MajorTrendReversal`, `DoubleExtremePullback`, `StopBeyondSignalBar`,
`SwingPointTrailingStop`, ...) and `CountertrendScalpAtrTarget`. Without them the EMA
and swing buckets would be nearly empty. **Judgement call 1.**

## Pane structure and version arithmetic

| Pane | Type | Groups | Count |
|---|---|---|---|
| 1 | Entry | setup \| reverse (each setup placement with Flip toggled; Flip is left alone on `same`-sided rules) | 2 |
| 2 | Entry | empty \| context 1 \| context 2 \| signal-bar condition | 4 |
| 3 | Exit | empty \| money/volatility stop \| structural stop | 3 |
| 4 | Exit | empty \| exit 1 \| exit 2 \| exit 3 \| exit 4 | 5 |
| 5 | Switch | empty \| switch 1 \| switch 2 | 3 |

Versions per template = 2 x 4 x 3 x 5 x 3 = **360**, the same for every family
(min = max = 360). The Davey 202608 families had 90-162. The version where panes 3,
4 and 5 are all empty is **pure stop-and-reverse**: no exit and no switch, and entries
auto-reverse. Every template contains it twice, once per pane-1 group, and each
time with all four pane-2 options. Pane 2's empty group is the bare setup.

Budget (design-grid: at most 3 optimized inputs and at most 100 iterations, judged
on the worst version):

- Setup: at most 2 optimized inputs and at most 25 iterations. The largest setup
  grid is 12.
- Pane 2, pane 3 (stops) and pane 5 (switches) are all **pinned**.
- Each pane-4 exit has at most 1 optimized input with at most 4 values. A version
  holds only one pane-4 group, so it can never carry two optimized exits.
- Worst version = 12 x 4 = **48 iterations**, with 3 optimized inputs. That leaves
  room to give switches 2 values later (96).

## Pane 1: the 50 setup families

The grids below are as first drawn. Fifteen were changed by the trial runs; see
"Trial runs (2026-11-05)" at the end, and `pools.json` for the values in force.

`~` = flipped and `!` = negated. Every input not listed is pinned at the rule's
default; the exact pins are in `pools.json`. For the fades (`~`), the authored long
side is the bullish pattern, so the Brooks trade is the flipped placement and the
reverse group is the unflipped one. The M1440 column is an analytical estimate at
mid-grid: signals per daily bar per side, before pane 2. No prior run used any of
these rules, so there is no empirical trade-count data (see "Trade-count evidence").

| Id | Pane-1 setup (grid) | Type | Bucket | TF | Setup it. | M1440 signals / count risk | Why |
|---|---|---|---|---|---|---|---|
| BRK-01 | `BullReversalBarAtNewLow` (lookback 5..20/5, closeFraction 0.5..0.7/0.1) | reversal | signal & reversal bars | any | 12 | ~1/30 bars/side / low | Brooks's reversal bar that actually reverses something: a new low plus a strong close, not a shape anywhere. |
| BRK-02 | `ThreeBarReversal` (sizeRatio 0.5..1.0/0.25, middleBarMaxFraction 0.4..0.8/0.2) | reversal | signal & reversal bars | any | 9 | ~1/30 / low | Named Brooks setup (two-bar reversal around a small middle bar); no Davey analogue. |
| BRK-03 | `ReversalBarFailure` (closePositionMin 0.6..0.8/0.1, lowerTailMin 0.1..0.3/0.1) | with-trend | signal & reversal bars | any | 9 | ~1/35 / low | Brooks's trap logic: a bear reversal bar that is immediately taken out traps the shorts. |
| BRK-04 | `PullbackEndReversalBar` (pullbackLookback 10..40/10, bodyFraction 0.5..0.6/0.1) | with-trend | signal & reversal bars | any | 8 | ~1/60 / moderate | With-trend pullback entry on a strong signal bar (high-1 proxy without the counter). |
| BRK-05 | `ExhaustionBarAfterLargeTrendBar` (bodyShrink 0.3..0.7/0.2, tailFraction 0.3..0.5/0.1) | reversal | signal & reversal bars | any | 9 | ~1/25 / low | Shrinking body plus a rejection tail after a trend bar: Brooks's exhaustion read. |
| BRK-06 | `TwoBarReversalBreakoutEntry` (bodyFraction 0.3..0.7/0.1) | reversal | signal & reversal bars | any | 5 | ~1/30 / low | Two-bar reversal with Brooks's entry beyond both bars (avoids the one-tick trap). |
| BRK-07 | `OutsideBar` + `ClosePositionInPriorBarRange` (threshold 0.6..1.0/0.2) | breakout | bar anatomy (inside/outside) | any | 3 | ~1/30 / low | Outside-bar breakout bar; the inside-bar variants are BAS-23 duplicates, the outside bar is not. |
| BRK-08 | `DojiAfterLargeOppositeTrendBar` (bigBarMultiple 0.75..1.5/0.25, dojiFraction 0.2..0.3/0.1) | reversal | bar anatomy (trend/doji) | any | 8 | ~1/30 at 1.0 ATR / moderate | Possible sell climax: a big bear trend bar met by a doji (Brooks's 'no follow-through'). Grid pulled below the 2.0-ATR default: at 2.0 x ATR the M1440 rate is ~1/160 per side. |
| BRK-09 | `MicroMeasuringGap` (bodyFraction 0.5..0.8/0.1) | with-trend | bar anatomy (gaps) | any | 4 | ~1/30 / low | Brooks-specific strength sign: the bar after a trend bar does not overlap the bar before it. |
| BRK-10 | `FirstPullbackAfterSpike` (spikeBars 2..3/1, maxWaitBars 2..6/2) | with-trend | leg counting | any | 6 | ~1/40 at 2 bars / moderate | Named Brooks setup: the high 1 of a strong spike. spikeBars 3 is the selective corner (~1/120 daily bars per side). |
| BRK-11 | `SpikePullbackLimitFade` (spikeBars 2..3/1, bodyFraction 0.5..0.7/0.1) | with-trend | bar anatomy (spikes) | any | 6 | ~1/50 / moderate | Brooks's 'buy below the low of a bull spike bar' limit-order fade of the first dip. |
| BRK-12 | `MicroChannelFailedBreakoutEntry` (minBars 3..6/1, maxWaitBars 2..4/1) | with-trend | trend lines & channels | any | 12 | ~1/60 / moderate | Brooks: the first break of a micro channel usually fails and the channel resumes. |
| BRK-13 | `TightChannel` (netAtr 1.5..2.5/0.5) + `PullbackFromRecentHigh` (pullbackAtr 0.5..1.0/0.25) | with-trend | trend lines & channels | any | 9 | ~1/25 / low | Buy the first meaningful dip of a tight channel (net progress, shallow pullbacks). |
| BRK-14 | `LargestTrendBarOfTheRun`~ (runBars 10..30/10, bodyFraction 0.5..0.7/0.1) | reversal | climaxes | any | 9 | ~1/60 / moderate | Brooks's 'biggest bull bar of the trend' exhaustion read; the setup is the fade, so it is placed flipped. |
| BRK-15 | `TrendBarRunEnded`~ (runBars 2..4/1, bodyFraction 0.5..0.6/0.1) | reversal | climaxes | any | 6 | ~1/40 / low | Fade the bar that ends a climactic run of trend bars; placed flipped (authored long = bull run ended). |
| BRK-16 | `ConsecutiveClimaxBarCount`~ (windowBars 20..40/10, climaxMultiple 1.5..2.5/0.5) | reversal | climaxes | any | 9 | ~1/50 at 1.5 ATR / moderate | Brooks: two or three separated buy climaxes bring a two-legged correction; placed flipped. |
| BRK-17 | `ClimaxBar`~ (climaxMultiple 1.25..2.25/0.5, bodyFraction 0.5..0.7/0.1) | reversal | climaxes | any | 9 | ~1/70 / moderate | A huge strong trend bar as a buy/sell climax; placed flipped. Grid sits below the 2-ATR default for daily counts. |
| BRK-18 | `SpikeReversedBySpike` (gapBars 0..2/1, bodyFraction 0.5..0.6/0.1) | reversal | climaxes | any | 6 | ~1/80 / moderate | Spike-and-opposite-spike reversal; authored orientation kept as the setup (see judgement calls). |
| BRK-19 | `FailedBreakoutReversal` (rangeBars 10..40/10, failBars 1..5/2) | range | breakouts & failed breakouts | any | 12 | ~1/40 / low | Brooks's most-stated idea: most breakouts fail; take the reversal back inside. |
| BRK-20 | `BreakoutPullbackEntry` (breakoutLookback 10..40/10, maxBarsSinceBreakout 5..15/5) | with-trend | breakouts & failed breakouts | any | 12 | ~1/50 / moderate | Three-stage breakout, pullback, resumption entry; not a Donchian breakout. |
| BRK-21 | `BreakoutLevelRetest` (lookback 20..60/20, maxWaitBars 3..9/3) | with-trend | breakouts & failed breakouts | any | 9 | ~1/70 / moderate | The pullback that tests a broken swing high and holds; ATR tolerance widened for daily bars. |
| BRK-22 | `TwiceFailedBreakoutAttempt` (attemptLookback 20..40/10, rangeBars 10..30/10) | range | trading ranges | any | 9 | ~1/60 / moderate | Brooks's second-attempt principle applied to range breakouts. |
| BRK-23 | `FirstPullbackDelay` (breakoutLookback 10..30/10, minBarsBeforePullback 2..6/2) | with-trend | leg counting | any | 9 | ~1/50 / moderate | Brooks's leading strength sign: the first pullback comes only after several bars. |
| BRK-24 | `HighLowBarCount` (resetLookback 10..50/10) | with-trend | leg counting | any | 5 | ~1/25 / low | The core Brooks setup, on the settled leg counter. |
| BRK-25 | `SecondSignal` (withinBars 5..20/5) | with-trend | leg counting | any | 4 | ~1/15 / low | Brooks's second-entry principle as a generic trigger. |
| BRK-26 | `FailedCountReversal` (countTarget 2..4/1, maxBarsSince 5..15/5) | reversal | leg counting | any | 9 | ~1/60 / moderate | A failed high 2/3/4 hands control to the other side. |
| BRK-27 | `ThreePushReversalEntry` (swingStrength 1..3/1, lookbackBars 30..60/15) | reversal | wedges & three pushes | any | 9 | ~1/50 / moderate | Brooks's wedge reversal on confirmed pivots. |
| BRK-28 | `ThreePushSwingBreakoutEntry` (swingStrength 1..3/1, lookbackBars 30..60/15) | reversal | wedges & three pushes | any | 9 | ~1/60 / moderate | The wedge entry on the break of the opposite swing. |
| BRK-29 | `ThreePushExtremeRetestFade` (swingStrength 2..3/1, tolAtr 0.1..0.3/0.1) | reversal | wedges & three pushes | any | 6 | ~1/90 / high | Double-top/bottom test of a wedge extreme; kept for the bucket despite the count risk. Row says keep swingStrength >= 2. |
| BRK-30 | `FinalFlagReversalBreakoutEntry` (flagBars 5..10/5, minTrendBars 20..40/10) | reversal | wedges & three pushes | any | 6 | ~1/90 / high | Named Brooks setup: the last flag of a mature trend breaks the wrong way. |
| BRK-31 | `TwentyGapBarPullbackEntry` (gapBarsRequired 5..20/5) | with-trend | EMA relations | any | 4 | ~1/60 at 10 bars / moderate | Brooks's '20 gap bar' first touch of the average; grid pulled down from 20 for daily counts. |
| BRK-32 | `EmaTouchRecovery` + `EmaSlope` (slopeAtr 0.25..1.0/0.25) | with-trend | EMA relations | any | 4 | ~1/25 / low | Touch and close back above a steep EMA; not an MA cross or MA-side rule. |
| BRK-33 | `EmaGapBarBreakoutEntry` (emaLength 10..30/5) | with-trend | EMA relations | any | 5 | ~1/20 / low | Brooks's MA gap bar: the bar beyond the EMA, then a break of its far extreme. |
| BRK-34 | `TrendLineTouch` (swingStrength 1..3/1, touchTolAtr 0.1..0.3/0.1) | with-trend | trend lines & channels | any | 9 | ~1/40 / low | With-trend buy at the bull trend line drawn through confirmed swing lows. |
| BRK-35 | `SecondTrendLineTest` (swingStrength 1..3/1, touchTolAtr 0.1..0.3/0.1) | with-trend | trend lines & channels | any | 9 | ~1/80 / moderate | Second-entry principle applied to a line test. |
| BRK-36 | `TrendLineBreak` (swingStrength 1..3/1, pivotLookback 20..60/20) | reversal | trend lines & channels | any | 9 | ~1/30 / low | First close through the opposite trend line; the first step of every Brooks reversal. |
| BRK-37 | `MajorTrendReversal` (tolTicks 5..85/40, swingStrength 1..3/1) | reversal | trend lines & channels | any | 9 | ~1/100 / high | The named Brooks MTR (line break, test of the extreme, reversal bar). Tick tolerance gridded wide. tolTicks 5/45/85 spans intraday to daily scale; the walkforward picks per unit. |
| BRK-38 | `MicroTrendLineFailedBreakout` (microLineBars 5..15/5, failureWindowBars 1..3/1) | with-trend | trend lines & channels | any | 9 | ~1/50 / moderate | Brooks: micro trend line breaks usually fail and become with-trend entries. |
| BRK-39 | `ChannelLineOvershootReversal` (pivotStrength 1..3/1, overshootBars 1..3/1) | reversal | trend lines & channels | any | 9 | ~1/60 / moderate | Brooks's most-repeated channel trade: fade an overshoot of the channel line. |
| BRK-40 | `ChannelLineBreakoutFailure` (pivotStrength 1..3/1, failBars 3..7/2) | range | trend lines & channels | any | 9 | ~1/60 / moderate | A close beyond a channel line that closes back inside runs to the opposite side. |
| BRK-41 | `ChannelStartRetestEntry` (pivotStrength 1..3/1, tolAtr 0.25..0.75/0.25) | range | trend lines & channels | any | 9 | ~1/70 / moderate | Brooks: a channel is commonly retraced to its start, which then holds. |
| BRK-42 | `CloseInRangePosition` (lookback 10..30/10, bottomFraction 0.1..0.3/0.1) + `RangeWidthBelowAtrMultiple` | range | trading ranges | any | 9 | ~1/30 / low | Buy low, sell high only inside a range; the range gate separates it from Davey's range-position rules. |
| BRK-43 | `SwingPointTestHolds` (strength 1..3/1, toleranceAtr 0.25..0.75/0.25) | range | swing structure | any | 9 | ~1/40 / low | A test of the last swing low that does not trade through: Brooks's higher-low / double-bottom test. |
| BRK-44 | `DoubleExtremePullback` (strength 1..2/1, matchTicks 4..84/40) | with-trend | swing structure | any | 6 | ~1/80 / moderate | Brooks's double-bottom pullback; the tick match gridded wide so daily pivots can qualify. matchTicks 4/44/84 for the same scale reason as MajorTrendReversal. |
| BRK-45 | `StopRunReclaimReentry` (swingStrength 1..3/1, lookbackBars 20..60/20) | reversal | swing structure | any | 9 | ~1/80 / moderate | Swing-low stop run that closes back above, entered above the reclaim bar. |
| BRK-46 | `FailedCountertrendScalpReversal` | with-trend | always-in / failed signals | any | 1 | ~1/40 / low | Three-bar trap: the countertrend signal triggers and immediately fails. |
| BRK-47 | `NearMeasuredMoveTargetFilter`~ (refBars 10..30/10, nearTargetAtr 0.25..0.75/0.25) | reversal | measured moves | any | 9 | ~1/20 / low | Measured-move targets as magnets; the setup is the fade at the target, so it is placed flipped. |
| BRK-48 | `FailedBreakoutOfPriorSessionExtreme` (maxBarsIntoSession 4..16/4) | range | session & time | intraday-only | 4 | n/a (intraday) / n/a | Brooks's failed breakout of yesterday's high/low early in the day. |
| BRK-49 | `SessionBarBreakout` (offsetBars 1..3/1, windowBars 1..3/1) | breakout | session & time | intraday-only | 9 | n/a (intraday) / n/a | Brooks's first-bar breakout (second or third bar of the day through bar 1). |
| BRK-50 | `FirstBarSessionTrendBarFailureReversal` (bodyFraction 0.5..0.7/0.1) | reversal | session & time | intraday-only | 3 | n/a (intraday) / n/a | Brooks's opening reversal: bar 2 reverses a strong first bar beyond its open. |

**Spread.** By bucket: trend lines & channels 10, signal & reversal bars 6, bar
anatomy 4 (inside/outside, doji, gaps, spikes), leg counting 5, climaxes 5, wedges &
three pushes 4, breakouts & failed breakouts 3, EMA relations 3, swing structure 3,
session & time 3, trading ranges 2, always-in / failed signals 1, measured moves 1.
Measured moves are mostly represented in the exit pool (seven measured-move and
projection targets). By setup type: 21 reversal, 20 with-trend, 7 range, 2
breakout. By count risk: 20 low, 24 moderate, 3 high (BRK-29, -30, -37), and the 3
intraday families.

### Trade-count evidence

No prior Brooks runs exist. `runs/` holds only Davey stems. The check is therefore
analytical. Two Davey platinum families give anchors, with M1440 trade counts per
case on the selected schedule taken from `runs/<stem>_platinum_validation/selection_report.json`:

- `BAS-23` (InsideBar + CloseAbovePriorHigh, a one-bar pattern of about 1/30):
  14,580 cases, median 78, 88% > 30, 67% > 50.
- `BAS-28` (2-bar pattern): median 67, 86% > 30.
- `BAS-27` (Harris 4-bar, a 4-condition pattern): median 13, 4% > 30.
- `BAS-24` (Harris 3-bar AND Momentum): median 9, 0% > 30.

So a setup at about 1/30 daily bars per side clears the filter comfortably, and one
at about 1/150 or rarer fails it. Grids were pulled toward frequency wherever a
Brooks default was rare on daily bars: `DojiAfterLargeOppositeTrendBar` 0.75-1.5 ATR
instead of 2.0, `ClimaxBar` from 1.25 ATR, `TwentyGapBarPullbackEntry` from 5 gap
bars, and `BreakoutLevelRetest` tolerance 0.25 ATR. The three "high" families are
kept for bucket coverage; expect many of their M1440 cases to fail `trade_count`.
*Offer, not action:* a one-version probe per high- or moderate-risk family, with
mid-grid pins, pane 2 empty and stop-and-reverse (pattern: `templates/quickTest.json`),
would replace these estimates with counts. Running it is Brian's call.

## Notable rejections

- **Davey near-duplicates.** `ConsecutiveInsideBars`, `IoiPattern`, `OioPattern`,
  `InsideBarInclusive` and `LargeOrCentredIoiInsideBar` with a breakout trigger are
  all BAS-23 (InsideBar + CloseAbovePriorHigh).
  `BreakoutClearsPriorExtremeByMargin`, `ReversalBarReversesPriorBars`,
  `CloseBeyondLastSwingPoint` and `MultiSessionPauseBreakout` are Donchian breakouts,
  the same as `Breakout`, `HighestHighBreakout` and `CloseAbovePriorHighestHigh`
  (BAS-16/18/19/25). `CloseCrossesEma` and `CloseBeyondEma` are the same as
  `MovingAverageCross` / `CloseAboveAverage` (BAS-2/3/31). `SpikeWithoutPullback`,
  `ConsecutiveBodyGapTrendBars`, `StrongTrendBarRun`, `ConsecutiveStrongTrendBars`
  and `TrendingHighsAndLows` are the same as `ConsecutiveUpBars`, `Momentum` and
  `LaggedHigherHigh` (BAS-3/4/5). `UpperTailCountInWindow` and
  `BullBearBodyDominanceInWindow` are BAS-41. Bare `CloseInRangePosition`,
  `ClosePositionInPriorBarRange` and `BullReversalBarWithTail` are the same as
  `CloseRangePosition`, `TwoBarRangePosition` and `ClosePercentileRank`
  (BAS-26/35/2). Two of these survive only inside clusters: `CloseInRangePosition`
  behind a trading-range gate (BRK-42) and `ClosePositionInPriorBarRange` with an
  outside bar (BRK-07).
- **Too rare on M1440** (estimated under 1/150 daily bars per side at mid-grid):
  `FailedFailureResumption`, `FailedThreePushReversalContinuation`,
  `SecondFailedSwingBreakoutReversal`, `IslandReversalRetest`,
  `HeadAndShouldersPattern`, `HeadAndShouldersNecklineBreakout` (whose shoulder
  symmetry is also a tick tolerance) and `ConsecutiveClimaxBars`.
- **Tick tolerances whose meaning changes with timeframe.** A 2-tick "equal low" is
  common on M30 and almost never true on M1440: `MarginalBreakoutThenReverse`,
  `MicroDoubleExtreme`, `Ledge`, `NearMissLevelReversal`, `DoubleExtremeBreakout`,
  `DoubleExtremeDipBreakout`, `MarginalThreePushBreakout` and
  `SpikeTrendBarsLowOverlap`. `MajorTrendReversal` and `DoubleExtremePullback` are
  kept, with a 3-value tick grid that spans both scales. **Judgement call 3.**
- **Price-point inputs that cannot carry across 43 symbols:**
  `ShallowPullbackLimitBelowPriorHigh`, `SmallBreakoutTrapReversal`,
  `LowHoldsPriorClose`, `ShavedTopBar`, `ShavedBothEndsBar`, `BuyLimitBelowRisingMA`,
  `LimitEntryAtMicroGapEdge`, `RoomToRangeTargetFilter` and `MinRewardToRiskFilter`.
  The exits `RewardRiskDeteriorationExit` and `WiderStopForSmallSignalBarCapped` are
  out for the same reason. Point tolerances on admitted exits are pinned at 0.
- **Entries that read position state** and so cannot act as a setup:
  `PullbackReachesEntryPrice`, `PullbackNearMissesEntryPrice`,
  `EntryBarClosedAgainstPosition`, `CounterSignalReversalPermission`,
  `ReenterAfterQuickStopOut`, `LastTradeWasWinner` and `BlockEntriesAfterLosingMonth`.
- **Direction-agnostic context** used as pane 1 would fire long and short on the same
  bar. `Barbwire`, `OverlappingBarRun`, `DojiBar`, `NarrowRangeBar`,
  `RangeWidthBelowAtrMultiple`, `EmaFlat`, `ExpandingTrianglePattern` and
  `OutsideOutsidePattern` go to the pane-2 pool or out.
- **Session rules beyond the three kept.** `OpeningRangeBreakout` is a generic ORB.
  `TrendFromOpenFlag`, `MorningLegDirection`, `SessionTrendDayDirection`,
  `TradingRangeDay` and `TrendResumptionDayContext` are day-type context. The gap
  rules (`SessionGapFirstBarReversalEntry`, `GapPullbackFailureEntry`,
  `GapReversalBar`) need real session gaps, which most 23-hour futures lack.
- **Not distinctively Brooks:** `FibonacciRetracementLevel` (Brooks dismisses Fib
  levels), `DailyPivotProximity`, and the volume rules (Davey's families already
  carry volume).
- **Exits:** `CalendarBoundaryExit` and `ClosePercentileExit` are Entry & Exit
  Confessions book rules, not Brooks and not general.

## Pane 2: context conditions

**Fill rule (recommended).** Pane 2 holds an empty group plus three single-condition
groups, all pinned:

- two conditions from the pool matched to the setup type: with-trend and breakout
  setups draw from **trend**, reversals from **reversal**, range setups from **range**;
- one condition from the **signal-bar** pool, which applies to every type.

Why match by type: Brooks's method is setup-in-context. A with-trend H2 needs a trend
to exist, and a reversal needs the trend line broken and must not fade a tight
channel. An unmatched draw would spend most groups on self-contradicting
combinations (an H2 gated by "trend line broken") that only add trials. The
mismatch control is still there: pane 1's reverse group meets the same context, and
the empty group is the unconditioned baseline. Pinning keeps every condition at
Brooks's stated value and leaves the whole optimizer budget to the setup and exit.
No condition may reuse a rule that is in the family's pane 1; this is why BRK-13,
which already uses `TightChannel`, never gets `InTightChannel`.

### Pane-2 pools (all pinned)

**trend** (9)

| Id | Placement | Reads |
|---|---|---|
| AlwaysInByEma | `BarsBeyondEmaCount` (lookback 10, minBarsBeyond 7, emaLength 20) | always-in stand-in: 7 of the last 10 closes beyond the 20 EMA |
| EmaSloping | `EmaSlope` (emaLength 20, slopeLookback 5, slopeAtr 0.5, atrLookback 14) | EMA rose >= 0.5 ATR in 5 bars |
| InTightChannel | `TightChannel` (windowBars 10, netAtr 2, pullbackAtr 1, atrLength 14) | tight channel: 2 ATR progress, pullbacks <= 1 ATR |
| HigherSwingLow | `HigherSwingLow` (strength 2, maxBarsBack 60) | last confirmed swing low above the one before |
| TrendBarsDominate | `TrendBarCountDominanceInWindow` (lookback 20, dominance 3, bodyFraction 0.6) | bull trend bars outnumber bear by >= 3 in 20 |
| NoTwoClosesBeyondEma | `NoTwoConsecutiveClosesBeyondEma` (emaLength 20, lookback 10) | no two consecutive closes on the wrong side of the EMA in 10 bars |
| ShallowPullbacksVsEma | `PullbackDepthBeyondEma` (emaLength 20, lookback 20, maxDepthAtr 1.0, atrLookback 14) | no close more than 1 ATR through the EMA in 20 bars |
| TrendLineIntact | `TrendLineBrokenRecently`~! (swingStrength 2, pivotLookback 20, withinBars 20, minBreaks 1) | the with-trend line has not been closed through in 20 bars (flipped + negated) |
| NotInTradingRange | `RangeWidthBelowAtrMultiple`! (rangeLookback 20, rangeAtrMultiple 4, atrLookback 14) | 20-bar height above 4 ATR (negated range test) |

**reversal** (7)

| Id | Placement | Reads |
|---|---|---|
| TrendLineBroken | `TrendLineBrokenRecently` (swingStrength 2, pivotLookback 20, withinBars 20, minBreaks 1) | Brooks's permission: the opposing trend line closed through in the last 20 bars |
| NotTightOpposingChannel | `TightChannel`~! (windowBars 10, netAtr 2, pullbackAtr 1, atrLength 14) | never fade a tight channel (flipped + negated) |
| NotStrongOpposingTrend | `ConsecutiveClosesBeyondEmaRun`~! (emaLength 20, strongBars 20) | not 20 straight closes on the other side of the EMA |
| LateTrend | `TrendDurationBars` (minTrendBars 30, consecutiveBars 2, bodyFraction 0.6, tailFraction 0.2) | always-in direction has held >= 30 bars |
| OpposingStairsShrinking | `ShrinkingStairs`~ (pivotStrength 2, pivotLookback 50, shrinkLegs 3) | the opposing trend's swings are shrinking |
| PriorMoveAgainst | `BarsBeyondEmaCount`~ (lookback 10, minBarsBeyond 7, emaLength 20) | the move being reversed: 7 of 10 closes on the other side of the EMA |
| HigherLowAfterExtreme | `HigherSwingLow` (strength 2, maxBarsBack 60) | MTR's higher low |

**range** (7)

| Id | Placement | Reads |
|---|---|---|
| InTradingRange | `RangeWidthBelowAtrMultiple` (rangeLookback 20, rangeAtrMultiple 4, atrLookback 14) | 20-bar height within 4 ATR |
| EmaFlat | `EmaFlat` (emaLength 20, slopeLookback 5, flatAtr 0.25, atrLookback 14) | EMA moved < 0.25 ATR in 5 bars |
| OverlappingBars | `OverlappingBarRun` (overlapBars 4, overlapFraction 0.5) | 4 bar pairs overlapping >= 50% |
| NotMidRange | `RangeMidpointZone`! (rangeLookback 20, midpointFraction 0.17) | not in the middle third of the 20-bar range |
| NotBarbwire | `Barbwire`! (barbwireOverlapFraction 0.5, dojiBodyFraction 0.2) | not barbwire |
| TwoSidedDojis | `DojiCountInWindow` (lookback 10, minCount 3, dojiFraction 0.2) | >= 3 dojis in 10 bars |
| HighBarOverlap | `AverageBarOverlap`! (lookback 10, maxAvgOverlap 0.5, epsilon 0.000001) | mean pairwise overlap above 50% (negated) |

**signalBar** (5)

| Id | Placement | Reads |
|---|---|---|
| SignalBarMinimum | `ReversalBarMinimum` | signal bar closes in the trade direction or beyond its midpoint |
| StrongSignalBar | `StrongTrendBar` (bodyFraction 0.6, tailFraction 0.15, lag 0) | signal bar is a strong trend bar in the trade direction |
| NotSmallWeakSignalBar | `SmallWeakSignalBarBlock` (smallRangeMultiple 0.6, rangeLookback 10, smallBodyFraction 0.4) | blocks small, weak-bodied signal bars |
| SignalBarNotOversized | `BarRangeBelowAverageMultiple` (avgRangeLookback 20, maxRangeMultiple 1.5) | signal bar range <= 1.5 x the 20-bar mean |
| NoLargeOpposingTail | `LargeOppositeTailWeakensReversal` (largeTailFraction 0.35, minBodyOverride 0.4) | no large tail against the trade unless the body is strong |

### Stop pool (pane 3, all pinned)

| Id | Category | Placement | Intraday-only | Notes |
|---|---|---|---|---|
| StopLoss5000 | stop-money/volatility | `StopLoss` (stopLoss 5000) |  | Existing. the Davey families' catastrophic stop, same value |
| SignalBarRange2x | stop-money/volatility | `StopAtSignalBarRangeMultiple` (stopRangeMult 2) |  | Brooks.  |
| RecentRangeStop | stop-money/volatility | `StopSizedToRecentRange` (runLookback 20, runFraction 1.0) |  | Brooks.  |
| AdrFractionStop | stop-money/volatility | `AvgDailyRangeFractionStop` (adrFraction 0.6, dayLookback 20, maxScanBars 500) |  | Brooks. daily-ok: on M1440 the ADR is the mean bar range |
| BracketAtr2R | stop-money/volatility | `StopLossTakeProfitATR` (atrLength 14, stopAtrMultiple 2, rewardRisk 2) |  | Brooks. bracket: 2 ATR stop, 2R target |
| BracketDollar2R | stop-money/volatility | `StopLossTakeProfitDollar` (stopDollars 2000, rewardRisk 2) |  | Brooks. bracket: $2000 stop, 2R target |
| BracketRatioStop | stop-money/volatility | `TakeProfitWithRatioStop` (target 3000, stopRatio 0.5) |  | Existing. bracket: $3000 target, $1500 stop |
| SessionAvgBarStop | stop-money/volatility | `SessionAvgBarRangeStop` (stopMultiple 1) | yes | Brooks. degenerates to one bar's range on M1440 |
| BeyondSignalBar | stop-structural | `StopBeyondSignalBar` (stopOffsetTicks 1) |  | Brooks.  |
| BeyondSwingAtEntry | stop-structural | `InitialStopBeyondSwingAtEntry` (pivotStrength 2, stopTicks 1, stopLookback 10) |  | Brooks.  |
| BeyondExtremeSinceEntry | stop-structural | `StopBeyondExtremeSinceEntry` (ratchetOffset 0) |  | Brooks. price-point offset pinned 0 (portable) |
| BeyondRecentRange | stop-structural | `StopBeyondRecentRangeExtreme` (rangeLookback 20, stopBuffer 0) |  | Brooks. price-point buffer pinned 0 (portable) |
| FractionOfSignalRisk | stop-structural | `StopFractionOfSignalBarRisk` (stopFraction 0.3) |  | Brooks.  |
| BeyondSpikeStart | stop-structural | `StopBeyondSpikeStart` (stopBufferTicks 1, strongBodyFraction 0.6, maxTailFraction 0.2, consecutiveBars 2) |  | Brooks.  |
| TightenToStrongEntryBar | stop-structural | `TightenStopToEntryBarIfStrong` (strongBodyFrac 0.6, stopOffset 0) |  | Brooks. price-point offset pinned 0 |

### Exit pool (pane 4)

| Id | Category | Placement (grid; other inputs at rule default unless noted) | Values | Intraday-only | Notes |
|---|---|---|---|---|---|
| TakeProfit | target | `TakeProfit` (takeProfit 1500..3000/500) | 4 |  | Existing.  |
| AtrProfitTarget | target | `AtrProfitTarget` (multiple 3..6/1) | 4 |  | Existing.  |
| CountertrendScalpAtr | target | `CountertrendScalpAtrTarget` (scalpAtr 0.5..2.0/0.5) | 4 |  | Brooks.  |
| BarHeightMM | target | `BarHeightMeasuredMoveTarget` (multiple 1..2/0.5) | 3 |  | Brooks.  |
| PatternHeightMM | target | `PatternHeightMeasuredMoveTarget` (refBars 10..40/10) | 4 |  | Brooks.  |
| LegOneEqualsLegTwo | target | `LegOneEqualsLegTwoTarget` (multiple 0.5..1.5/0.5) | 3 |  | Brooks.  |
| RangeHeightProjection | target | `RangeHeightProjectionTarget` (rangeLookback 10..40/10) | 4 |  | Brooks.  |
| SwingPivotTarget | target | `SwingPivotTarget` (pivotIndex 1..3/1) | 3 |  | Brooks.  |
| PriorRangeExtreme | target | `ExitAtPriorRangeExtreme` (channelBars 10..40/10) | 4 |  | Brooks.  |
| ChannelLineTarget | target | `ChannelLineTargetExit` (pivotStrength 1..3/1) | 3 |  | Brooks.  |
| RangeMidpoint | target | `RangeMidpointTarget` (rangeLookback 20..60/20) | 3 |  | Brooks.  |
| MovingAverageTarget | target | `MovingAverageTarget` (emaLength 10..30/10) | 3 |  | Brooks.  |
| PullbackSizedTarget | target | `PullbackSizedProfitTarget` (profitFraction 0.6..1.2/0.2) | 4 |  | Brooks.  |
| SwingHighProfitTarget | target | `SwingHighProfitTarget` (profitThreshold 500..2000/500) | 4 |  | Brooks.  |
| ChannelBounceFraction | target | `ChannelBounceFractionTarget` (bounceFraction 0.25..0.75/0.25) | 3 |  | Brooks.  |
| EntryBarExtreme | target | `EntryBarExtremeTarget` | 1 |  | Brooks. scalp to the signal bar's far extreme |
| GapMidpointMM | target | `GapMidpointMeasuredMoveTarget` | 1 |  | Brooks. daily-ok |
| RollingRangeMidpointMM | target | `RollingRangeMidpointTarget` | 1 |  | Brooks.  |
| SessionOpenPrice | target | `SessionOpenPriceTarget` | 1 | yes | Brooks.  |
| SessionMidpoint | target | `SessionMidpointTarget` | 1 | yes | Brooks.  |
| AtrTrailingStop | trail/breakeven/protect | `AtrTrailingStop` (multiple 3..6/1) | 4 |  | Existing.  |
| TrailingStop | trail/breakeven/protect | `TrailingStop` (trailStop 1000..2500/500) | 4 |  | Existing.  |
| ProfitProtector | trail/breakeven/protect | `ProfitProtector` (maxProfit 1500..3000/500) | 4 |  | Existing.  |
| ProfitProtectorRatio | trail/breakeven/protect | `ProfitProtectorRatio` (profitFloor 1500..3000/500) | 4 |  | Existing.  |
| TieredProfitProtector | trail/breakeven/protect | `TieredProfitProtector` | 1 |  | Existing.  |
| BreakevenStop | trail/breakeven/protect | `BreakevenStop` (activationProfit 500..2000/500) | 4 |  | Brooks.  |
| BreakevenAfterEmaRun | trail/breakeven/protect | `BreakevenStopAfterEmaHoldingRun` (barsAboveEma 2..8/2) | 4 |  | Brooks.  |
| BreakevenAfterAdverse | trail/breakeven/protect | `BreakevenExitAfterAdverseExcursion` (adverseDollars 250..1000/250) | 4 |  | Brooks.  |
| BreakevenSecondTest | trail/breakeven/protect | `BreakevenStopOnSecondEntryTest` | 1 |  | Brooks.  |
| BreakevenRetest | trail/breakeven/protect | `BreakevenRetestExit` | 1 |  | Brooks. exits on any return to the entry price: short trades |
| SwingPointTrail | trail/breakeven/protect | `SwingPointTrailingStop` (pivotStrength 1..3/1) | 3 |  | Brooks.  |
| TrailAfterProfit | trail/breakeven/protect | `TrailArmedAfterProfitThreshold` (armProfitDollars 500..2000/500) | 4 |  | Brooks.  |
| TrailAfterEmaBreak | trail/breakeven/protect | `TrailArmedAfterEmaCloseBreak` (emaLength 10..30/10) | 3 |  | Brooks.  |
| TrailBehindStrongBar | trail/breakeven/protect | `TrailStopBehindStrongBar` (strongBodyFraction 0.5..0.7/0.1) | 3 |  | Brooks.  |
| TrailToMicroGap | trail/breakeven/protect | `TrailStopToMicroMeasuringGap` | 1 |  | Brooks.  |
| DelayedSwingTrail | trail/breakeven/protect | `DelaySwingTrailUntilRetestAndNewExtreme` | 1 |  | Brooks.  |
| NumBars | time | `NumBars` (numBarsExit 5..20/5) | 4 |  | Existing.  |
| NumBarsIfProfitable | time | `NumBarsIfProfitable` (numBars 5..20/5) | 4 |  | Existing.  |
| NumBarsIfLosing | time | `NumBarsIfLosing` (numBars 5..20/5) | 4 |  | Existing.  |
| TimeOfDayExit | time | `TimeOfDayExit` | 1 | yes | Existing. fires every bar on M1440 (bar close = session close), as in the Davey families |
| WeakEntryBarScratch | time | `WeakEntryBarScratchExit` (weakBodyFrac 0.2..0.4/0.1) | 3 |  | Brooks.  |
| WeakEntryBarExit | time | `WeakEntryBarExit` (maxBars 1..3/1) | 3 |  | Brooks.  |
| FailedScalp | time | `FailedScalpExit` (failureDollars 250..1000/250) | 4 |  | Brooks.  |
| ConsecutiveCloseExit | pattern-structural | `ConsecutiveCloseExit` (consecutiveBars 2..4/1) | 3 |  | Existing.  |
| AdverseBodyCount | pattern-structural | `AdverseBodyCountExit` (adverseBars 2..4/1) | 3 |  | Brooks.  |
| OppositeStrongTrendBar | pattern-structural | `ExitOnOppositeStrongTrendBar` (bodyFraction 0.5..0.7/0.1) | 3 |  | Brooks.  |
| FirstOppositeBodyAfterRun | pattern-structural | `ExitOnFirstOppositeBodyAfterRun` (runBars 2..5/1) | 4 |  | Brooks.  |
| MicroChannelBreakout | pattern-structural | `ExitOnMicroChannelBreakout` (minBars 3..6/1) | 4 |  | Brooks.  |
| TrendBarFails | pattern-structural | `TrendBarFailsExit` (bodyFraction 0.5..0.7/0.1) | 3 |  | Brooks.  |
| ClimaxAfterTrendRun | pattern-structural | `ClimaxBarAfterTrendRunExit` (bigBarMultiple 1.5..2.5/0.5) | 3 |  | Brooks.  |
| ConsecutiveTrendBarsClimax | pattern-structural | `ConsecutiveTrendBarsClimaxExit` (climaxBars 3..6/1) | 4 |  | Brooks. daily-ok |
| ConsecutiveClimax | pattern-structural | `ExitOnConsecutiveClimax` | 1 |  | Brooks.  |
| ParabolicAcceleration | pattern-structural | `ParabolicAccelerationExit` (legBars 3..6/1) | 4 |  | Brooks.  |
| ShrinkingSwingIncrements | pattern-structural | `ShrinkingSwingIncrementsExit` (shrinkFraction 0.5..1.0/0.25) | 3 |  | Brooks.  |
| ThreePushCompletion | pattern-structural | `ThreePushCompletionExit` (swingStrength 1..3/1) | 3 |  | Brooks.  |
| OpposingCount | pattern-structural | `OpposingCountExit` (countTarget 1..2/1) | 2 |  | Brooks.  |
| FailedCountSetup | pattern-structural | `FailedCountSetupExit` | 1 |  | Brooks.  |
| GapFilled | pattern-structural | `GapFilledExit` (gapLookback 10..30/10) | 3 |  | Brooks.  |
| WeakFollowThrough | pattern-structural | `ExitOnWeakFollowThrough` | 1 |  | Brooks.  |
| FailedTargetReversal | pattern-structural | `FailedTargetReversalExit` (targetDollars 500..2000/500) | 4 |  | Brooks.  |

### Switch pool (pane 5, all pinned)

| Id | Kind | Placement | Intraday-effective | Notes |
|---|---|---|---|---|
| MaxTradesPerSession | session | `MaxTradesPerSession` (maxTradesPerDay 3) | yes | cap 3 trades/session (book 3-5); inert on M1440 where a session is one bar |
| MonthlyProfitTarget | equity-profit | `MonthlyProfitTarget` (ProfitTarget 3000) |  |  |
| TightRangeBlocksEntries | regime-range | `TightRangeBlocksEntries` (rangeLookback 15, tightAtrMultiple 1.2, atrLookback 20) |  | also forces flat (generator Switch semantics) |
| MonthlyLossLimit | equity-loss | `MonthlyLossLimit` (LossLimit 3000) |  |  |
| WeeklyProfitTarget | equity-profit | `WeeklyProfitTarget` (ProfitTarget 2000) |  |  |
| WeeklyLossLimit | equity-loss | `WeeklyLossLimit` (LossLimit 1500) |  |  |
| DailyLossLimit | equity-loss | `DailyLossLimit` (LossLimit 1000) | yes | a one-bar loss stop on M1440 |
| LowAdxSwitch | regime-range | `LowAdxSwitch` (lookback 14, threshold 20) |  | forces flat when ADX < 20 |
| HighVolatilitySwitch | regime-volatility | `HighVolatilitySwitch` (atrLookback 14, avgLookback 100, volMultiple 1.5) |  |  |
| DayOfWeekSwitch | calendar | `DayOfWeekSwitch` (blockDay 1) |  | blockDay pinned at Monday (default) |
| LosingStreakCooldown | equity-streak | `LosingStreakCooldown` (lossCount 3, cooldownBars 20) |  |  |
| TrendFilterSwitch | regime-trend | `TrendFilterSwitch` (maLength 100) |  | directional: blocks and flattens counter-MA trades |
| GapBarSwitch | regime-gap | `GapBarSwitch` (gapAtrMultiple 1, atrLookback 14, holdBars 1) |  |  |

## Exits and switches

**Categories.** Pane 3 holds protective stops: *money/volatility* (dollar, ATR,
signal-bar-range or recent-range sized, and the three brackets) and *structural*
(beyond the signal bar, swing, spike start or recent range). Pane 4 holds four
categories: *target* (fixed, ATR, measured-move, structural level),
*trail/breakeven/protect*, *time* (bar counts, the entry-bar scratch exits, time of
day), and *pattern-structural* (bar-pattern and count exits). Pool sizes: stops 8 + 7;
exits 20 targets, 16 trail/breakeven/protect, 7 time and 17 pattern-structural, 60
in all. 48 of the 60 exits are Brooks rules. Of the 15 stops, 11 are Brooks, two are
Brian's ratio brackets from the Brooks pass (`StopLossTakeProfitATR`/`Dollar`, X1),
and two are existing (`StopLoss`, `TakeProfitWithRatioStop`). The existing rules keep
the grids the Davey families used. All 13 switches are in the pool.

**Intraday-only or special conditions.**
- `TimeOfDayExit` fires on every M1440 bar, because the bar's close is the session
  close (the Davey families carried this too).
- `SessionAvgBarRangeStop`, `SessionOpenPriceTarget` and `SessionMidpointTarget`
  degenerate on daily bars.
- `AvgDailyRangeFractionStop`, `GapMidpointMeasuredMoveTarget` and
  `ConsecutiveTrendBarsClimaxExit` are "daily-ok".
- `BreakevenRetestExit` closes on any return to the entry price, so it gives very
  short trades.
- `MaxTradesPerSession` is inert on M1440, and `DailyLossLimit` becomes a one-bar
  loss stop there.
- `TightRangeBlocksEntries` and `LowAdxSwitch` also **force flat**. The generator
  ORs every Switch into the exits, so they are not block-only; the block-only
  reading is the negated entry rule (CATALOG rows).
- `TrendFilterSwitch` is directional.

## Draw constraints

`drawStudy.py` applies these, seeded with `pools.json` `seed` = 20261105:

1. Nothing appears twice within a family, and no pane-2 condition reuses a pane-1
   rule.
2. Pane 2: two conditions from the type-matched pool and one from the signal-bar pool.
3. Pane 3: exactly one money/volatility stop and one structural stop.
4. Pane 4: four distinct exits covering at least three categories. No rule appears
   in both pane 3 and pane 4.
5. Families tagged `any` get at most **one** intraday-only exit across panes 3 and 4,
   and at most **one** intraday-effective switch. So at most one exit group and one
   switch group per family degenerate on M720 and M1440. Intraday families are not
   capped.
6. Switches: at most one equity-profit switch (Monthly/Weekly target) and one
   equity-loss switch (Monthly/Weekly/Daily limit). Reversal setups never get
   `TrendFilterSwitch`, which would block exactly the countertrend trade. Range
   setups never get `LowAdxSwitch` or `TightRangeBlocksEntries`, which force flat in
   the regime the setup trades.
7. Balance: every pool is filled least-used-first, with ties broken by the seeded
   RNG and a seeded family order. Of 200 seeded attempts the one with the smallest
   total count spread is kept. Result (attempt 0, total spread 5):
   - stops: money/volatility 6-7 appearances each, structural 7-8;
   - exits: 3-4 each;
   - switches: 7-8 each;
   - pane-2 pools: trend 4-5, reversal 6, range 2, signal-bar 10.

   The pane-2 counts differ between pools only because the setup types differ in
   size.

Re-running `python drawStudy.py` rewrites a byte-identical `assignment.json`.

## Assignment (from `assignment.json`)

Every pane also has its empty group, which is not listed here. Ids are the
`pools.json` member ids. "Worst it." = setup iterations x the largest exit grid
drawn for the family.

| Family | Pane 2 (after empty) | Stops (after empty) | Exits (after empty) | Switches (after empty) | Worst it. |
|---|---|---|---|---|---|
| BRK-01 | LateTrend, PriorMoveAgainst, SignalBarMinimum | BracketRatioStop, TightenToStrongEntryBar | TrailBehindStrongBar, FirstOppositeBodyAfterRun, AtrTrailingStop, CountertrendScalpAtr | WeeklyLossLimit, MaxTradesPerSession | 48 |
| BRK-02 | TrendLineBroken, NotStrongOpposingTrend, SignalBarMinimum | BracketRatioStop, TightenToStrongEntryBar | OpposingCount, FailedTargetReversal, ChannelBounceFraction, BreakevenAfterEmaRun | TightRangeBlocksEntries, DailyLossLimit | 36 |
| BRK-03 | HigherSwingLow, InTightChannel, NoLargeOpposingTail | BracketAtr2R, BeyondRecentRange | BreakevenStop, BarHeightMM, AtrProfitTarget, ThreePushCompletion | LosingStreakCooldown, MonthlyProfitTarget | 36 |
| BRK-04 | NotInTradingRange, TrendBarsDominate, NoLargeOpposingTail | SessionAvgBarStop, FractionOfSignalRisk | DelayedSwingTrail, NumBars, ChannelLineTarget, TrendBarFails | GapBarSwitch, TrendFilterSwitch | 32 |
| BRK-05 | NotTightOpposingChannel, HigherLowAfterExtreme, NoLargeOpposingTail | BracketAtr2R, FractionOfSignalRisk | BreakevenStop, WeakEntryBarExit, MicroChannelBreakout, ClimaxAfterTrendRun | GapBarSwitch, DayOfWeekSwitch | 36 |
| BRK-06 | NotStrongOpposingTrend, HigherLowAfterExtreme, NotSmallWeakSignalBar | SignalBarRange2x, BeyondExtremeSinceEntry | TrendBarFails, TakeProfit, NumBarsIfLosing, TieredProfitProtector | HighVolatilitySwitch, GapBarSwitch | 20 |
| BRK-07 | EmaSloping, AlwaysInByEma, SignalBarNotOversized | AdrFractionStop, TightenToStrongEntryBar | BreakevenSecondTest, MicroChannelBreakout, ParabolicAcceleration, PriorRangeExtreme | LosingStreakCooldown, MonthlyLossLimit | 12 |
| BRK-08 | NotStrongOpposingTrend, HigherLowAfterExtreme, NotSmallWeakSignalBar | RecentRangeStop, BeyondSpikeStart | ProfitProtector, ConsecutiveClimax, EntryBarExtreme, ClimaxAfterTrendRun | DailyLossLimit, HighVolatilitySwitch | 32 |
| BRK-09 | AlwaysInByEma, ShallowPullbacksVsEma, NotSmallWeakSignalBar | SignalBarRange2x, FractionOfSignalRisk | AdverseBodyCount, SessionOpenPrice, RollingRangeMidpointMM, NumBarsIfLosing | MaxTradesPerSession, MonthlyProfitTarget | 16 |
| BRK-10 | EmaSloping, InTightChannel, NotSmallWeakSignalBar | RecentRangeStop, BeyondRecentRange | FailedCountSetup, CountertrendScalpAtr, AdverseBodyCount, TrailAfterProfit | MaxTradesPerSession, TrendFilterSwitch | 24 |
| BRK-11 | TrendBarsDominate, TrendLineIntact, NoLargeOpposingTail | AdrFractionStop, TightenToStrongEntryBar | PriorRangeExtreme, SwingHighProfitTarget, TimeOfDayExit, AtrTrailingStop | DayOfWeekSwitch, GapBarSwitch | 24 |
| BRK-12 | TrendBarsDominate, EmaSloping, SignalBarMinimum | StopLoss5000, BeyondRecentRange | TrailAfterProfit, CountertrendScalpAtr, NumBars, WeakEntryBarScratch | TrendFilterSwitch, LowAdxSwitch | 48 |
| BRK-13 | NoTwoClosesBeyondEma, NotInTradingRange, NotSmallWeakSignalBar | BracketAtr2R, BeyondSignalBar | GapFilled, TrailAfterEmaBreak, ConsecutiveClimax, LegOneEqualsLegTwo | WeeklyLossLimit, TightRangeBlocksEntries | 27 |
| BRK-14 | OpposingStairsShrinking, NotStrongOpposingTrend, SignalBarMinimum | AdrFractionStop, BeyondExtremeSinceEntry | SwingHighProfitTarget, TakeProfit, ConsecutiveClimax, NumBars | LowAdxSwitch, LosingStreakCooldown | 36 |
| BRK-15 | PriorMoveAgainst, LateTrend, StrongSignalBar | BracketDollar2R, FractionOfSignalRisk | SwingHighProfitTarget, AtrTrailingStop, TakeProfit, OppositeStrongTrendBar | MonthlyProfitTarget, TightRangeBlocksEntries | 24 |
| BRK-16 | OpposingStairsShrinking, PriorMoveAgainst, NoLargeOpposingTail | BracketDollar2R, FractionOfSignalRisk | MovingAverageTarget, NumBarsIfProfitable, BarHeightMM, ShrinkingSwingIncrements | WeeklyLossLimit, MonthlyProfitTarget | 36 |
| BRK-17 | NotStrongOpposingTrend, OpposingStairsShrinking, SignalBarMinimum | StopLoss5000, BeyondSpikeStart | RollingRangeMidpointMM, NumBarsIfLosing, NumBars, BreakevenSecondTest | DailyLossLimit, MonthlyProfitTarget | 36 |
| BRK-18 | PriorMoveAgainst, TrendLineBroken, SignalBarNotOversized | SignalBarRange2x, BeyondSignalBar | ThreePushCompletion, DelayedSwingTrail, PatternHeightMM, BreakevenStop | LosingStreakCooldown, TightRangeBlocksEntries | 24 |
| BRK-19 | TwoSidedDojis, OverlappingBars, NotSmallWeakSignalBar | StopLoss5000, TightenToStrongEntryBar | GapFilled, PriorRangeExtreme, DelayedSwingTrail, TrailAfterEmaBreak | MonthlyLossLimit, TrendFilterSwitch | 48 |
| BRK-20 | NoTwoClosesBeyondEma, TrendLineIntact, SignalBarMinimum | BracketAtr2R, TightenToStrongEntryBar | OpposingCount, BreakevenSecondTest, AtrProfitTarget, BreakevenRetest | TightRangeBlocksEntries, LosingStreakCooldown | 48 |
| BRK-21 | ShallowPullbacksVsEma, AlwaysInByEma, SignalBarNotOversized | BracketRatioStop, BeyondSwingAtEntry | BreakevenAfterAdverse, ProfitProtector, MicroChannelBreakout, GapMidpointMM | MaxTradesPerSession, WeeklyLossLimit | 36 |
| BRK-22 | NotBarbwire, NotMidRange, StrongSignalBar | SignalBarRange2x, BeyondSpikeStart | WeakFollowThrough, ShrinkingSwingIncrements, WeakEntryBarExit, DelayedSwingTrail | WeeklyLossLimit, HighVolatilitySwitch | 27 |
| BRK-23 | EmaSloping, NotInTradingRange, NoLargeOpposingTail | SignalBarRange2x, BeyondRecentRange | TrailingStop, ChannelBounceFraction, ConsecutiveCloseExit, PullbackSizedTarget | DailyLossLimit, MonthlyProfitTarget | 36 |
| BRK-24 | ShallowPullbacksVsEma, NoTwoClosesBeyondEma, SignalBarNotOversized | BracketRatioStop, BeyondRecentRange | ProfitProtectorRatio, BreakevenStop, BarHeightMM, AdverseBodyCount | LowAdxSwitch, TightRangeBlocksEntries | 20 |
| BRK-25 | ShallowPullbacksVsEma, AlwaysInByEma, StrongSignalBar | RecentRangeStop, BeyondRecentRange | WeakEntryBarScratch, SwingPivotTarget, FailedScalp, TrailToMicroGap | WeeklyProfitTarget, GapBarSwitch | 16 |
| BRK-26 | NotTightOpposingChannel, HigherLowAfterExtreme, SignalBarNotOversized | AdrFractionStop, BeyondRecentRange | RangeMidpoint, ParabolicAcceleration, SessionMidpoint, TrailingStop | LowAdxSwitch, DayOfWeekSwitch | 36 |
| BRK-27 | PriorMoveAgainst, NotTightOpposingChannel, StrongSignalBar | SessionAvgBarStop, BeyondExtremeSinceEntry | PullbackSizedTarget, NumBarsIfProfitable, TrailBehindStrongBar, MovingAverageTarget | LowAdxSwitch, LosingStreakCooldown | 36 |
| BRK-28 | TrendLineBroken, LateTrend, SignalBarNotOversized | BracketDollar2R, BeyondExtremeSinceEntry | FailedTargetReversal, ParabolicAcceleration, LegOneEqualsLegTwo, ProfitProtectorRatio | TightRangeBlocksEntries, HighVolatilitySwitch | 36 |
| BRK-29 | PriorMoveAgainst, NotTightOpposingChannel, StrongSignalBar | AdrFractionStop, BeyondSignalBar | RangeHeightProjection, SessionMidpoint, BreakevenRetest, WeakEntryBarScratch | LosingStreakCooldown, WeeklyLossLimit | 24 |
| BRK-30 | HigherLowAfterExtreme, LateTrend, SignalBarNotOversized | SignalBarRange2x, FractionOfSignalRisk | EntryBarExtreme, BreakevenRetest, SwingPivotTarget, FailedScalp | WeeklyProfitTarget, HighVolatilitySwitch | 24 |
| BRK-31 | NotInTradingRange, ShallowPullbacksVsEma, NotSmallWeakSignalBar | StopLoss5000, FractionOfSignalRisk | ConsecutiveCloseExit, TrendBarFails, WeakEntryBarScratch, TieredProfitProtector | GapBarSwitch, TrendFilterSwitch | 12 |
| BRK-32 | NoTwoClosesBeyondEma, TrendLineIntact, NotSmallWeakSignalBar | StopLoss5000, BeyondSwingAtEntry | SessionOpenPrice, SwingPivotTarget, GapFilled, TrailToMicroGap | DailyLossLimit, GapBarSwitch | 12 |
| BRK-33 | InTightChannel, HigherSwingLow, SignalBarNotOversized | SessionAvgBarStop, BeyondSwingAtEntry | RangeMidpoint, SwingPointTrail, WeakFollowThrough, ConsecutiveTrendBarsClimax | DailyLossLimit, DayOfWeekSwitch | 20 |
| BRK-34 | TrendLineIntact, NoTwoClosesBeyondEma, SignalBarMinimum | RecentRangeStop, BeyondExtremeSinceEntry | TrailToMicroGap, ConsecutiveTrendBarsClimax, RangeHeightProjection, SessionOpenPrice | DayOfWeekSwitch, LowAdxSwitch | 36 |
| BRK-35 | InTightChannel, HigherSwingLow, NoLargeOpposingTail | BracketDollar2R, BeyondSpikeStart | TrailingStop, TrailAfterProfit, NumBarsIfProfitable, AtrProfitTarget | DayOfWeekSwitch, WeeklyProfitTarget | 36 |
| BRK-36 | OpposingStairsShrinking, TrendLineBroken, NotSmallWeakSignalBar | BracketAtr2R, BeyondSwingAtEntry | TieredProfitProtector, BreakevenAfterAdverse, OpposingCount, PullbackSizedTarget | LowAdxSwitch, LosingStreakCooldown | 36 |
| BRK-37 | HigherLowAfterExtreme, LateTrend, StrongSignalBar | SessionAvgBarStop, BeyondSpikeStart | TrailingStop, ShrinkingSwingIncrements, ProfitProtectorRatio, AtrProfitTarget | WeeklyProfitTarget, MaxTradesPerSession | 36 |
| BRK-38 | TrendBarsDominate, EmaSloping, NoLargeOpposingTail | SessionAvgBarStop, BeyondSignalBar | ConsecutiveCloseExit, GapMidpointMM, SwingPointTrail, ThreePushCompletion | MaxTradesPerSession, TightRangeBlocksEntries | 27 |
| BRK-39 | OpposingStairsShrinking, TrendLineBroken, SignalBarNotOversized | BracketRatioStop, BeyondSpikeStart | WeakEntryBarExit, TrailAfterEmaBreak, BreakevenAfterEmaRun, WeakFollowThrough | DayOfWeekSwitch, WeeklyLossLimit | 36 |
| BRK-40 | TwoSidedDojis, InTradingRange, NoLargeOpposingTail | BracketDollar2R, BeyondSwingAtEntry | ChannelLineTarget, PatternHeightMM, FirstOppositeBodyAfterRun, SwingPointTrail | MonthlyLossLimit, WeeklyProfitTarget | 36 |
| BRK-41 | HighBarOverlap, EmaFlat, SignalBarMinimum | BracketAtr2R, BeyondExtremeSinceEntry | FailedTargetReversal, MovingAverageTarget, ShrinkingSwingIncrements, TrailBehindStrongBar | WeeklyProfitTarget, TrendFilterSwitch | 36 |
| BRK-42 | NotMidRange, EmaFlat, StrongSignalBar | RecentRangeStop, BeyondSignalBar | EntryBarExtreme, PatternHeightMM, ProfitProtector, ThreePushCompletion | MonthlyLossLimit, GapBarSwitch | 36 |
| BRK-43 | OverlappingBars, InTradingRange, StrongSignalBar | SignalBarRange2x, TightenToStrongEntryBar | PatternHeightMM, NumBarsIfLosing, LegOneEqualsLegTwo, FailedCountSetup | MaxTradesPerSession, WeeklyProfitTarget | 36 |
| BRK-44 | TrendBarsDominate, TrendLineIntact, SignalBarMinimum | StopLoss5000, BeyondSwingAtEntry | RollingRangeMidpointMM, FailedScalp, FirstOppositeBodyAfterRun, ChannelBounceFraction | HighVolatilitySwitch, TrendFilterSwitch | 24 |
| BRK-45 | OpposingStairsShrinking, NotTightOpposingChannel, NoLargeOpposingTail | SessionAvgBarStop, BeyondRecentRange | LegOneEqualsLegTwo, TrailToMicroGap, PullbackSizedTarget, AdverseBodyCount | MonthlyProfitTarget, WeeklyLossLimit | 36 |
| BRK-46 | HigherSwingLow, AlwaysInByEma, StrongSignalBar | BracketDollar2R, BeyondSignalBar | ClimaxAfterTrendRun, TakeProfit, OppositeStrongTrendBar, ProfitProtectorRatio | MonthlyLossLimit, HighVolatilitySwitch | 4 |
| BRK-47 | TrendLineBroken, NotTightOpposingChannel, StrongSignalBar | AdrFractionStop, BeyondSwingAtEntry | RangeHeightProjection, BreakevenAfterEmaRun, ChannelLineTarget, TimeOfDayExit | WeeklyProfitTarget, DailyLossLimit | 36 |
| BRK-48 | HighBarOverlap, NotBarbwire, NotSmallWeakSignalBar | BracketRatioStop, BeyondSpikeStart | TrailAfterProfit, SessionMidpoint, TrendBarFails, FailedCountSetup | HighVolatilitySwitch, MaxTradesPerSession | 16 |
| BRK-49 | HigherSwingLow, InTightChannel, SignalBarMinimum | SessionAvgBarStop, BeyondExtremeSinceEntry | CountertrendScalpAtr, TimeOfDayExit, RangeMidpoint, ConsecutiveTrendBarsClimax | MonthlyProfitTarget, MonthlyLossLimit | 36 |
| BRK-50 | LateTrend, NotStrongOpposingTrend, SignalBarNotOversized | RecentRangeStop, BeyondSignalBar | TieredProfitProtector, GapMidpointMM, BreakevenAfterAdverse, OppositeStrongTrendBar | MonthlyLossLimit, LowAdxSwitch | 12 |


## Judgement calls for Brian

1. **Universe**: every Brooks rule on disk (373), not only the A/B KEYS lists
   (236 Entry / 44 Exit). Without the T and slice-15 rules there would be no EMA,
   MTR or double-bottom families and no signal-bar or swing stops.
2. **Intraday-only families** (BRK-48/49/50) should run 30-480 only, not the full
   30-1440 spec list.
3. **Tick-scale grids**: `MajorTrendReversal` tolTicks 5/45/85 and
   `DoubleExtremePullback` matchTicks 4/44/84. These let the walkforward pick an
   intraday or a daily scale per unit, at the cost of one optimized input.
4. **Fade orientation**: BRK-14/15/16/17/47 take the flipped placement as "the
   setup". `SpikeReversedBySpike` (BRK-18) keeps its authored orientation. Its row
   says the long side's spelling came from the merged pseudocode, and that a
   placement's direction toggle decides how it is traded.
5. **Pinned dollar values**: `StopLoss` 5000 (the Davey value), `StopLossTakeProfitDollar`
   2000/2R, `MonthlyProfitTarget` 3000 (Davey had 1500 and 3000 as two groups),
   `MaxTradesPerSession` 3 (book value 3-5), `DayOfWeekSwitch` pinned at Monday.
   Every switch is pinned to keep the worst version at 48 iterations.
6. **Matched pane 2** (recommended) rather than drawing from one mixed pool.
7. **Force-flat switches** (`TightRangeBlocksEntries`, `LowAdxSwitch`) are kept, as
   the brief asks, even though Brooks wants only the entry block.
8. **Trade counts are estimates.** The 3 high-risk and 24 moderate-risk families
   would benefit from the probe offered above before the full 360-version runs.

## Trial runs (2026-11-05)

The probe offered under "Trade-count evidence" was run. Every moderate- and
high-risk family (27) plus the three intraday-only ones got a one-version probe:
pane 1 = the setup group only, every input pinned, no pane 2, no stops, exits or
switches (pure stop-and-reverse; the flip mirrors the setup, so its count is the
same). Specs were the platinum twin of `s_202608_bas_23` (45 symbols, 30-1440
minutes, WF 2007-01-01 -> 2019-04-01, incubation -> 2020-01-01, OOS -> 2023-01-01,
the full chain with `trade_count` min 30), so each figure below is the
`trade_count` filter's count on the case's most-average schedule. Three batches,
all since removed from the engine's `generated/`, registry and specs; the run
directories stay as evidence:

- `runs/s_202611_brk_probe` (37 versions): grid centres. Where an even-length
  integer grid has no integer centre, the two middle grid values.
- `runs/s_202611_brk_probe2` (118): every grid corner of the families that passed
  at centre, plus candidate fixes for those that failed.
- `runs/s_202611_brk_probe3` (21): the corners and centres of the proposed grids.

Rule applied: a family fails if its centre has a median under ~30 M1440 trades
(intraday-only families: on 30-480), or if its most selective corner is plainly
below that (median under ~20). For `DoubleExtremePullback` and `MajorTrendReversal`
the small tick value is the intraday option of judgement call 3 and is not held to
M1440. M1440 medians below; `%>30` in brackets. Stop-and-reverse is the floor for a
family's trade count: an exit only adds round trips.

### Passed unchanged

| Family | Centre | Most selective corner |
|---|---|---|
| BRK-04 | 46 (91%) | 34 (71%) at pullbackLookback 40, bodyFraction 0.6 |
| BRK-21 | 61 (96%) | 60 (96%). lookback and maxWaitBars barely move the count (60-61 at every corner); the grid is close to inert |
| BRK-23 | 106 (100%) | 74 (98%) |
| BRK-26 | 38 (84%) | 34 (73%) at countTarget 4, maxBarsSince 5 |
| BRK-27 | 51 (96%) | 27 (24%) at swingStrength 3, lookbackBars 30 |
| BRK-30 | 77-115 (100%) | 72 (100%). Rated high risk; it is not |
| BRK-35 | 165 (100%) | 56 (96%) |
| BRK-38 | 61 (96%) | 31 (58%) at microLineBars 5, failureWindowBars 1 |
| BRK-39 | 61 (96%) | 26 (27%) at pivotStrength 3, overshootBars 1 |
| BRK-40 | 50 (96%) | 24 (13%) at pivotStrength 3, failBars 3 (borderline) |
| BRK-41 | 101 (98%) | 34 (69%) |
| BRK-44 | 61-172 | 85 (89%) at strength 2, matchTicks 84; matchTicks 4 gives 5-18 on M1440 by design (judgement call 3) |
| BRK-48 | M30-M480 522-1220 | M30 179 at maxBarsIntoSession 4 |
| BRK-49 | M30-M480 1353-1456 | M30 647 |

### Grid changes (pools.json; rules untouched)

| Family | Was | Now | Evidence (M1440 median, %>30) |
|---|---|---|---|
| BRK-08 | bigBarMultiple 0.75..1.5/0.25 | 0.75..1.25/0.25 | corner at 1.5 / doji 0.2 = 16 (0%); new centre 1.0/0.25 = 66 (98%), new corner 1.25/0.2 = 30 (49%) |
| BRK-10 | spikeBars 2..3/1, maxWaitBars 2..6/2, bodyFraction 0.6 | spikeBars 1, maxWaitBars 6..10/2, bodyFraction 0.5 | spikeBars 2 = 3 (0%), 3 = 0; spikeBars 1/maxWait 8/body 0.5 = 45 (87%); 1/8/0.6 = 26, 1/4/0.6 = 19, so the 6-bar corner is interpolated (~35), not probed. **The "spike" is now one strong bar; see below** |
| BRK-11 | spikeBars 2..3/1, bodyFraction 0.5..0.7/0.1 | spikeBars 1, bodyFraction 0.5..0.7/0.1 | spikeBars 2 = 9 (0%) at body 0.6, 22 (13%) at 0.5; spikeBars 1 = 104 / 64 / 34 (98/96/60%) at body 0.5/0.6/0.7. Matches the family's own reading, "buy below the low of a bull spike bar" |
| BRK-12 | minBars 3..6/1, maxWaitBars 2..4/1 | minBars 2..4/1, maxWaitBars 2..4/1 | minBars 4 = 37, 5 = 19 (4%); new centre 3/3 = 61 (98%), corners 2/4 = 116, 4/2 = 28 (33%) |
| BRK-14 | runBars 10..30/10 | 10..20/5 | corner 30/0.7 = 20 (2%); new centre 15/0.6 = 48 (93%), corner 20/0.7 = 29 (40%) |
| BRK-16 | windowBars 20..40/10, climaxMultiple 1.5..2.5/0.5 | windowBars 30..40/10, climaxMultiple 1.5..1.75/0.125 | centre 30/2.0 = 8 (11%); 30/1.5 = 234, 30/1.625 = 91 (96%), 30/1.75 = 38 (67%), 20/1.75 = 9. windowBars 20 dropped: it is the selective side. 1.0 ATR fires almost every bar (1,561-3,930), so the floor stays 1.5 |
| BRK-17 | climaxMultiple 1.25..2.25/0.5 | 1.25..1.75/0.25 | corners at 2.25 = 7-9 (0%); new centre 1.5/0.6 = 70 (98%), corner 1.75/0.7 = 25 (27%) |
| BRK-20 | breakoutLookback 10..40/10, maxBarsSinceBreakout 5..15/5 | breakoutLookback 5..15/5, same maxBarsSince | centre 25/10 = 22 (13%); 5/10 = 69, 10/10 = 46 (93%), 15/5 = 29 (42%). maxBarsSince above 11 is moot under the pinned maxPullbackBars 10 |
| BRK-22 | attemptLookback 20..40/10, rangeBars 10..30/10 | attemptLookback 40..60/10, rangeBars 5..15/5 | centre 30/20 = 22 (0%); new centre 50/10 = 63 (96%), corner 40/15 = 33 (67%) |
| BRK-28 | swingStrength 1..3/1, lookbackBars 30..60/15 | swingStrength 1, lookbackBars 45 (both pinned) | swingStrength 2 = 24 (22%), 1 = 32 (58%); lookbackBars 30/45/60/90 give identical counts, so the grid was inert. Marginal: 32 is the best this setup does on M1440 |
| BRK-29 | swingStrength 2..3/1, tolAtr 0.1..0.3/0.1 | swingStrength 2, tolAtr 0.5..0.9/0.2 | swingStrength 3 = 5-16; at 2: tolAtr 0.2 = 13, 0.3 = 20, 0.5 = 28 (42%), 0.7 = 35 (73%), 0.9 = 39 (84%). lookbackBars 40 vs 80 identical. Still high risk |
| BRK-31 | gapBarsRequired 5..20/5 | 3..9/2 | 10 = 27 (24%), 15 = 16 (0%); 3 = 74, 6 = 46 (96%), 9 = 32 (60%). Far from Brooks's 20 |
| BRK-37 | tolTicks 5..85/40, swingStrength 1..3/1 | tolTicks 5..165/80, swingStrength 1..2/1 | centre 45/2 = 18 (24%), 5/3 = 1; 85/1 = 40 (58%), 85/2 = 32 (51%). 5 ticks stays as the intraday option, 85/165 cover daily scale |
| BRK-45 | swingStrength 1..3/1 | 2..3/1 | swingStrength 1 = 10 (0%), 2 = 53 (100%), 3 = 53-55 (96%); lookbackBars inert (20 = 60) |
| BRK-50 | bodyFraction 0.5..0.7/0.1 | 0.4..0.6/0.1 | intraday-only. 0.7 = 23-30 on M30-M240 (27-49%); 0.4 = 117-162, 0.5 = 95-103, 0.6 = 53-55 |

### Max Bars Back: `AvgDailyRangeFractionStop`

Not a trade-count change, found while checking every template's Max Bars Back
against CATALOG "Reaches back". `AdrFractionStop` pinned `maxScanBars` 500, a reach
of 501 against Max Bars Back 250, in BRK-07/11/14/26/29/47. The scan is guarded by
the session count, so the deep reads happen only where 20 sessions take more than
250 bars (M30 and M60 on 23-hour futures, M120 at the edge), and there the engine
throws. `maxScanBars` is now pinned at 249 (reach 250). On those timeframes the
stop never becomes ready and is inert, so its group duplicates the empty stop
group there; on M1440 nothing changes. The alternative was Max Bars Back 501 for
those six families, which would start them later than every other family.

### Not fixed: BRK-18

`SpikeReversedBySpike` cannot reach the floor in its Brooks form. spikeBars 2 gives
5 (centre), and the most generous form, gapBars 2 and bodyFraction 0.5, gives 15
(0%). spikeBars 1 gives 142-386, but it is then a two-bar reversal, which is BRK-06.
The rejection list holds no climax-bucket replacement (`ConsecutiveClimaxBars`, the
only one, was rejected as rarer still). BRK-18 is left as drawn and needs Brian's
call (accept it as a known low-count family, retag it, or name a replacement).

### Brian's call: one-bar spikes in BRK-10 and BRK-11

BRK-10 (`FirstPullbackAfterSpike`) and BRK-11 (`SpikePullbackLimitFade`) reach the
floor only with `spikeBars` 1, a single strong trend bar rather than a multi-bar
spike. For BRK-11 that is the family's own wording. For BRK-10, "the high 1 of a
strong spike", it is a looser reading, and the leg-counting bucket has no rejected
replacement. If one bar is not acceptable, the alternatives are to keep spikeBars
2..3 and accept a family that fails `trade_count` on M720-M1440 (and on most M240
cases), or to swap in a different rule.

`drawStudy.py` was re-run because `assignment.json` carries the setup grids. The
family set and pool ids did not change, and the draw came out the same: attempt 0,
total spread 5, identical usage, identical member ids in every family. Only setup
params, `setupIterations` and `worstVersionIterations` moved.

## Brian's decisions (2026-11-05)

These supersede the open questions above.

- **Every family runs on every timeframe** (30-1440). `pools.json` maps the
  `intraday-only` tag to the full set; the tag still feeds the draw constraints,
  so the draw is unchanged (attempt 0, identical member usage).
- **Low daily trade counts are acceptable.** BRK-18 stays as drawn (5-15 median
  M1440 trades). BRK-10's original grid is restored: spikeBars 2..3/1,
  maxWaitBars 2..6/2, bodyFraction 0.6 (6 iterations, 2 optimized inputs);
  the one-bar-spike variant from the trial runs is dropped. BRK-11 keeps its
  trial-run grid (one-bar spike, its own wording). BRK-28 and BRK-29 are fine.
- **`AdrFractionStop`**: Max Bars Back 500 for every family that draws it
  (BRK-07/11/14/26/29/47), with `maxScanBars` pinned at 499 so its reach
  (`maxScanBars + 1`) is exactly 500. The stop's pool entry carries
  `maxBarsBack: 500` and `drawStudy.py` gives each family the largest Max Bars
  Back among its drawn stops. All other families stay at 250.
- Templates regenerated; `makeStudyTemplates.py --check`: 50/50 verified.

