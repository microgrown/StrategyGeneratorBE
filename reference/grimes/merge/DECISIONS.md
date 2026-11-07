# Grimes merge: decisions already taken (pasted into later merge prompts)

## From indicators_bands (2026-09-21)

1. Keltner centre line is EXPONENTIAL (book p68 verbatim: "2.25 multiples of the ATR around a
   20-period exponential moving average"). The catalog's CloseBeyondEma / EmaGapBar /
   CloseWithinAtrOfEma family implements EMA plus ATR margin; KeltnerChannelCross stays the
   simple-average cross variant. A single close outside the Keltner band is CloseBeyondEma at
   emaLength 20 / marginAtr 2.25 / atrLookback 20 (duplicate, do not re-author). A "free bar"
   is EmaGapBar plus new marginAtr/atrLookback inputs (A, parameterization).
2. 3/10 oscillator: osc = Average(close,3) - Average(close,10), signal = Average(osc,16), all
   simple averages; el_words is `Average`, never `MACD`. Zero cross of the fast line equals
   MovingAverageCross at 3/10 (duplicate). Derived series: zero-seeded ring buffer, guard warm-up.
3. Momentum divergence is detected by WINDOW MAXIMA, not swing pivots:
   `high[0] >= Highest(high, divLookback)[1] && osc[0] < Highest(osc, divLookback)[1]`
   (same shape as the catalog's VolumeDivergenceAfterClimax). Key: MomentumDivergenceAtSwingExtreme (B).
4. Higher-timeframe approximation: multiply lookbacks by 5 (Grimes: neighbouring timeframes
   relate by 3 to 5). No new input; e.g. the HTF band read is CloseBeyondEma at 100/100/2.25.
5. Moving-average slope trend filter equals the catalog's EmaSlope (slopeAtr > 0 gives the
   flat dead zone). Do not re-author.
6. Stochastic-based Anti stays C (FastK/SlowK unregistered, though the register has a
   VERIFIED `stochastic` row and StochasticCross exists); Grimes's price-structure Anti is the
   one to carry.

## From ranges_levels_tests (2026-09-21)

7. A support/resistance LEVEL defaults to the one-bar-shifted N-bar window extreme
   (`Lowest(low, N)[1]`); use a confirmed swing pivot of strength S only when the level must
   persist from a break to a later retest or counted touches. Tolerance is always an ATR
   fraction (0.1 to 0.25; 0.5 for magnets), never ticks. No candidate needs to stay C on this.
8. TRADING RANGE test: the catalog's RangeWidthBelowAtrMultiple (20 bars / 4.0 loose, 15 / 1.2
   tight; negate for trending), plus new NetMoveBelowAtrMultiple for Grimes's random-walk
   reading. Not ADX.
9. Accumulation vs distribution is NOT authored as a composite: RangeWidthBelowAtrMultiple +
   EmaFlat + Momentum with a new `lag` input (PriorLegDirection), three panes.
10. Consolidation length = consecutive-bar run of RangeWidthBelowAtrMultiple (new
    `consecutiveBars` input, default about 18).
11. Spring/upthrust is ONE mirrored rule (SpringWithMinimumPenetration); Grimes's
    minimum-penetration floor sits beside Brooks's SmallBreakoutTrapReversal cap.
12. Polarity: the negate toggle gives "not A", never the mirror side, so a fade rule and a
    momentum rule on the same statistic are different rules. Author a second file when there
    is real machinery; add a boolean input when it is a one-line ratio.
13. FailureTest is B (key FailureTest). Already-catalog duplicates in this area:
    FailedBreakoutReversal, FailedBreakoutBeyondExtreme, DistanceAboveRecentLow,
    CloseInRangePosition, LevelTouchCount, BreakoutLevelRetest, ShrinkingConsecutiveRanges,
    ExpandingTrianglePattern, OppositeLargeBarsInWindow, LargeRangeBarInWindow.

## From swing_structure / context_regime / bar_anatomy (2026-09-21)

14. SWING PIVOT: every Grimes pivot is the measured EL `SwingHigh`/`SwingLow(strength)`.
    First-order pivot = strength 1; pivot ORDER maps onto `strength` (second-order about 2,
    third-order 3 to 5), so second-order pivots are NOT a distinct rule and no pivot-of-pivots
    scan is authored. The ATR zigzag pivot is REJECTED (no fixed confirmation lag; would fork
    every pivot rule onto an incompatible series). Pivot-to-pivot reads use the corpus's
    newest-first three-pivot scan, which caps "last N legs" at 2 per series.
15. TREND TEST: the catalog's EmaSlope (emaLength 20, slopeLookback 5, slopeAtr as the
    optimizer input; 0 = bare slope). HIGHER TIMEFRAME trending = the same rule placed again
    at emaLength x 5. Structural HTF reads use the 5x multiplier on a window rule
    (TouchOfRecentExtreme, RangeWidthBelowAtrMultiple, CloseAbovePriorHighestHigh). Never
    raise "the higher time frame is trending" as a fresh C. SwingTrendHigherHighsAndLows
    (B) is the pivot alternative, not the default.
16. SWITCHES: MaxTradesPerSession already implements the per-period trade cap (D). The daily
    loss limit is the MonthlyProfitTarget construction with the boundary at Date<>Date[1] and
    the comparison on the loss side (B, key DailyLossLimit); no new engine accessor.
17. Parameterizations decided: `maxAnchorSpanBars` on TrendLineBreak (micro trend line at
    strength 1); `maxRiskAtr` on SwingPointTrailingStop. Catalog duplicates: SwingHigh,
    SwingPointUndercut, TrendLineTouch, SwingPivotTarget, BarsBeyondEmaCount, InsideBar,
    CloseRangePosition.

## From pullbacks_continuation (2026-09-21)

18. The PULLBACK primitive is already on disk: depth = PullbackDepthFromRecentHigh, duration =
    PullbackDurationBars, legs = HighLowBarCount / LegCountAtLeast, no-new-extreme =
    BarsSinceExtremeExceeds. Never author a new pullback primitive.
19. A BAND-shaped filter (both bounds on one quantity) is a new input on the rule that computes
    it, never a second file (precedents PullbackNearMissesEntryPrice, ShallowDipBelowPriorBarLow).
20. Grimes's pullback trigger "trend-line failure and recover" = break-and-recover of the
    pullback's shifted window extreme (key LevelBreakAndRecover); the projected-line form is
    TrendLineBreak, a different rule.
21. Named templates carried as B composites with depends_on_keys: Pullback,
    PullbackLowerTimeframeBreakout, ComplexPullback, Anti. The Anti is Grimes's price-structure
    form; the stochastic form stays C.

## From exits_stops / exits_targets (2026-09-21)

22. Minimum stop distance (never closer than one average bar range) is a GRID FLOOR for the
    design-grid pass, not a per-rule clamp input (ORed exits cannot clamp one another).
23. No time-stop tightening curve rule: place ParabolicSarTrailingStop (B, the only new exit
    machinery) with NumBarsIfBelowProfitThreshold as the hard time stop.
24. Partial profit taking is not expressible: each risk-multiple tranche is a full exit
    placement (ProfitTargetAtRiskMultiple with stopDistance in points); fractions in notes only.
25. "Stop INSIDE the tested extreme" = InitialStopBeyondSwingAtEntry with a NEGATIVE stopTicks;
    that input becomes signed (precedent: SwingHighProfitTarget.offsetTicks) and its grid runs
    below zero.
26. AtrTrailingStop IS the chandelier (MaxPositionProfit - OpenPositionProfit reduces to
    highest-high-since-entry minus close). Grimes adds no target mechanism the catalog lacks
    (LegOneEqualsLegTwoTarget, PatternHeightMeasuredMoveTarget, SwingPivotTarget,
    ChannelLineTargetExit cover them all).
