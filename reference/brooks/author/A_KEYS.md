# Unblocked A-list keys (all slices)

Check for behavioural duplicates against these as well as against rules/CATALOG.md; a sibling slice may be authoring the same behaviour under another key.

| key | role | bucket | slice | description |
|---|---|---|---|---|
| AverageBarOverlapWindow | Entry | bar_anatomy_inside_outside | 01 | The mean overlap between consecutive bars over the last N bars, as a fraction of each prior bar's range, is at least a threshold. |
| BarOverlapFraction | Entry | bar_anatomy_inside_outside | 01 | The current bar's range overlaps at least a fraction of the prior bar's range, Brooks's one-bar trading-range clue. |
| BarOverlapIncreasing | Entry | bar_anatomy_inside_outside | 01 | The current bar overlaps its predecessor by a larger fraction than the bar N bars ago overlapped its own predecessor. |
| BarOverlapWithPriorRange | Entry | bar_anatomy_inside_outside | 01 | The current bar overlaps the combined high-low range of the prior N bars by at most a fraction of that range. |
| ConsecutiveInsideBars | Entry | bar_anatomy_inside_outside | 01 | N consecutive inside relations ending at the bar N bars ago: insideBarCount 2 is Brooks's ii, 3 is iii. |
| InsideBarInclusive | Entry | bar_anatomy_inside_outside | 01 | The bar N bars ago is inside the bar before it, using Brooks's inclusive at-or-beyond boundary. |
| InsideBodyBar | Entry | bar_anatomy_inside_outside | 01 | The bar's body (open-to-close) nests inside the prior bar's body even though its tails may extend beyond the prior bar's range. |
| IoiPattern | Entry | bar_anatomy_inside_outside | 01 | Inside bar, then an outside bar, then an inside bar over three consecutive bars ending at the bar N bars ago. |
| LargeOrCentredIoiInsideBar | Entry | bar_anatomy_inside_outside | 01 | An ioi pattern completed one bar ago whose final inside bar is large relative to the outside bar or whose midpoint sits near the outside bar |
| LargeOutsideBar | Entry | bar_anatomy_inside_outside | 01 | The bar N bars ago is an outside bar whose range is at least a multiple of the mean bar range over the preceding window. |
| NarrowRangeBar | Entry | bar_anatomy_inside_outside | 01 | The bar's high-low range is at most a fraction of the mean bar range over the last N bars. |
| OioPattern | Entry | bar_anatomy_inside_outside | 01 | Outside bar, then an inside bar, then an outside bar over three consecutive bars ending at the bar N bars ago. |
| OutsideBarInMidRange | Entry | bar_anatomy_inside_outside | 01 | The bar N bars ago is an outside bar whose midpoint sits in the middle band of the recent M-bar high-low range. |
| SpikePauseBar | Entry | bar_anatomy_inside_outside | 02 | The bar either failed to make a higher high or closed below its open, the pause that Brooks says ends a bull spike (mirrored for a bear spik |
| ThinAreaLowBarOverlap | Entry | bar_anatomy_inside_outside | 02 | Every one of the last N bar pairs overlaps by at most a fraction of the earlier bar's range, Brooks's thin one-sided breakout area. |
| AverageUpperTailFraction | Entry | bar_anatomy_reversal_signal | 02 | The mean upper-tail fraction over the last N bars is below a threshold - as a long filter, the absence of persistent selling pressure (mirro |
| BarRangeBelowAverageMultiple | Entry | bar_anatomy_reversal_signal | 02 | The signal bar's high-low range is no more than K times the average bar range of the last N bars - an oversized signal bar would put the ent |
| BreakoutBarLargeBodyLargeRange | Entry | bar_anatomy_reversal_signal | 02 | The bar has a body that is a large fraction of its own range AND a range at or above the recent average range - the book's 'strong breakout  |
| BullReversalBarAtNewLow | Entry | bar_anatomy_reversal_signal | 02 | The bar makes a new low over the prior N bars yet closes up and in the upper part of its own range - a bull reversal bar that actually rever |
| BullReversalBarShape | Entry | bar_anatomy_reversal_signal | 02 | A strong bull reversal bar by body/tail shape: bull close, body at least a fraction of the bar's range, and BOTH tails at most a fraction of |
| BullReversalBarWithTail | Entry | bar_anatomy_reversal_signal | 02 | A bull reversal bar by close position and rejection tail: bull close, close in the upper part of the bar's range, and a lower tail of at lea |
| CloseInRangePosition | Entry | bar_anatomy_reversal_signal | 02 | The close sits in the bottom (long) / top (short) fraction of the N-bar high-low range - fading a range extreme with no reversal-bar require |
| ExhaustionBarAfterLargeTrendBar | Entry | bar_anatomy_reversal_signal | 02 | After a bear trend bar, the current bar's body shrinks to a fraction of that prior body and it shows a lower tail of at least a fraction of  |
| GrowingTopTails | Entry | bar_anatomy_reversal_signal | 02 | This bar has a nonzero top tail and that tail is larger than the prior bar's top tail - tails starting to form and grow at the top of a move |
| LargeOppositeTailWeakensReversal | Entry | bar_anatomy_reversal_signal | 02 | Block a bull reversal entry when the bar has a large tail on TOP, unless its body is still reasonably strong (mirror: a bear reversal bar wi |
| LowHoldsPriorClose | Entry | bar_anatomy_reversal_signal | 02 | The bar's low never traded more than a few ticks below the previous bar's close (mirror: the high never traded more than a few ticks above i |
| OpenNearHighCloseNearLow | Entry | bar_anatomy_reversal_signal | 03 | The bar opened near its low and closed near its high (mirror: opened near its high and closed near its low) - the shape of a trend day read  |
| PullbackNotAfterStrongOppositeReversalBar | Entry | bar_anatomy_reversal_signal | 03 | The bar that started the current pullback (the last up-close bar before the run of down closes) was NOT a strong bear reversal bar that made |
| ReversalBarFailure | Entry | bar_anatomy_reversal_signal | 03 | The bar after a bull reversal bar breaks out of the WRONG side - it trades below the reversal bar's low instead of above its high. The trapp |
| ReversalBarLowOverlap | Entry | bar_anatomy_reversal_signal | 03 | The bar's range overlaps the prior bar's range by no more than a fraction of that prior bar's range - a reversal bar that mostly overlaps it |
| ReversalBarMinimum | Entry | bar_anatomy_reversal_signal | 03 | The floor test for a bull reversal signal bar: the bar closes above its own open OR above its own midpoint (mirror for a bear reversal bar). |
| ReversalBarReversesPriorBars | Entry | bar_anatomy_reversal_signal | 03 | Strength gauge for a reversal bar: its close is above the closes of each of the last N bars AND its high is above the highs of each of the l |
| ReversalBarStrongerThanBreakoutBar | Entry | bar_anatomy_reversal_signal | 03 | A bear breakout bar (a bear trend bar closing below the N-bar lowest low) is immediately followed by a bull bar whose body is at least K tim |
| ReversalBarTailFraction | Entry | bar_anatomy_reversal_signal | 03 | Quality marker of a strong bull reversal bar: its lower tail is between a third and a half of the bar's range, and its upper tail is small o |
| SignalBarBodyMatchesTradeDirection | Entry | bar_anatomy_reversal_signal | 03 | The signal bar closed in the trade direction - buy only above bull bars, short only below bear bars. A blanket gate on every stop-entry setu |
| SmallBodyLargeOppositeTailBar | Entry | bar_anatomy_reversal_signal | 03 | Sign of weakness in a bull bar: only a modest body plus a prominent tail on TOP, against the direction the bar closed (mirror for a bear bar |
| SmallTailsBar | Entry | bar_anatomy_reversal_signal | 03 | Both tails of the bar are small relative to its range - a decisive bar showing urgency, direction-agnostic. |
| SmallWeakSignalBarBlock | Entry | bar_anatomy_reversal_signal | 03 | Block an entry when the signal bar is BOTH much smaller than recent bars AND small-bodied; a small bar with a strong body still passes. |
| StopRunReversalBar | Entry | bar_anatomy_reversal_signal | 03 | One or more bars break below the recent N-bar low, then the next bar closes back above that level with a bull body - a stop run that reverse |
| StrongBodyBarCountInWindow | Entry | bar_anatomy_reversal_signal | 04 | At least K of the last N bars had a strong body in one direction - cumulative buying or selling pressure, without needing one dramatic bar. |
| TwoBarReversal | Entry | bar_anatomy_reversal_signal | 04 | A bear trend bar immediately followed by a bull trend bar of comparable size that closes back above the bear bar's midpoint - the pair acts  |
| TwoBarReversalBreakoutEntry | Entry | bar_anatomy_reversal_signal | 04 | After a bear-bar/bull-bar two-bar reversal pair, enter only when a later bar closes beyond the HIGHER of the two bars' highs (mirror: below  |
| UpperTailCountInWindow | Entry | bar_anatomy_reversal_signal | 04 | At least K of the last N bars had an upper tail of at least a fraction of that bar's range - repeated selling pressure at a level (mirror: l |
| AverageTailFractionBelow | Entry | bar_anatomy_trend_doji | 04 | The average tail fraction of the last N bars - the part of each bar's range that is not body - is at or below a threshold: urgency, bars wit |
| BarRangeAboveAtrMultiple | Entry | bar_anatomy_trend_doji | 04 | The bar's high-low range is at least K times the N-bar ATR: an outsized bar. Identical both sides; negate the placement for the 'small bar'  |
| BarRangeHighestOfWindow | Entry | bar_anatomy_trend_doji | 04 | This bar's high-low range is the largest of the last N bars. Identical both sides. |
| BodyAboveAverageMultiple | Entry | bar_anatomy_trend_doji | 04 | A bull bar (short: bear) whose body is at least K times the average absolute body of the last N bars - a body that dominates its recent peer |
| BullBearBodyDominanceInWindow | Entry | bar_anatomy_trend_doji | 04 | Over the last N bars, the total size of the up bodies exceeds K times the total size of the down bodies (short: mirrored) - buying pressure  |
| ConsecutiveTrendBars | Entry | bar_anatomy_trend_doji | 04 | Each of the last N bars is a bull trend bar (long) / bear trend bar (short): body at least a fraction of its own range, closing in the same  |
| DojiBar | Entry | bar_anatomy_trend_doji | 04 | The bar's body is at most a small fraction of its own high-low range: a doji, Brooks's one-bar trading range. Identical both sides; negate t |
| DojiCountInWindow | Entry | bar_anatomy_trend_doji | 04 | At least K of the last N bars are doji bars - a sign of two-sided trading. Identical both sides; negate for 'few dojis', Brooks's strong-tre |
| LargeBarCountInWindow | Entry | bar_anatomy_trend_doji | 04 | At least K of the last N bars have a range of at least M times the recent average range - outsized bars are present, regardless of direction |
| LargeTrendBarCountInWindow | Entry | bar_anatomy_trend_doji | 05 | At least K of the last N bars are bull trend bars whose range is also at least M times the ATR (short: bear trend bars) - counting big with- |
| LargestBearBodyVsAverageBullBody | Entry | bar_anatomy_trend_doji | 05 | The largest down body of the last N bars is smaller than K times the average up body over the same window (short: mirrored) - no outsized co |
| MicroGapAroundTrendBar | Entry | bar_anatomy_trend_doji | 05 | The previous bar was a bull trend bar and this bar's low is at or above the high of the bar before it (short: mirrored): a three-bar micro g |
| OpenNearBarLow | Entry | bar_anatomy_trend_doji | 05 | The bar's open sits in the bottom fraction of its own range (long) / the top fraction (short): little or no wick before the move began, a si |
| ShavedBothEndsBar | Entry | bar_anatomy_trend_doji | 05 | A bull bar that opens within X ticks of its low AND closes within X ticks of its high (short: opens near its high and closes near its low):  |
| ShavedTopBar | Entry | bar_anatomy_trend_doji | 05 | The close is within X ticks of the bar's high (long) / of its low (short): a shaved top, no tail at the far end. |
| ShrinkingBodies | Entry | bar_anatomy_trend_doji | 05 | Each of the last barCount bars closed up (short: down) and each body is smaller than the one before - the with-trend bodies are shrinking, a |
| TrendBarBody | Entry | bar_anatomy_trend_doji | 05 | The bar closed up (long) / down (short) and its body is at least a fraction of its own high-low range: Brooks's trend bar. |
| TrendBarCountDominanceInWindow | Entry | bar_anatomy_trend_doji | 05 | Over the last N bars, bull trend bars outnumber bear trend bars by at least a margin (short: mirrored). |
| TrendBarCountInWindow | Entry | bar_anatomy_trend_doji | 05 | At least K of the last N bars are bull trend bars (long) / bear trend bars (short) - they need not be consecutive. |
| TrendingDojiRun | Entry | bar_anatomy_trend_doji | 05 | The last N bars are all doji bars, yet each closes above the one before it and neither its high nor its low is below the previous bar's (sho |
| ClimaxBarAfterTrendRunExit | Exit | bar_anatomy_trend_doji | 05 | Exit the long when this bar is a bull trend bar whose range exceeds K times the ATR and at least M of the last N bars were also bull trend b |
| ConsecutiveTrendBarsClimaxExit | Exit | bar_anatomy_trend_doji | 05 | Exit the long when the last N bars are all bull trend bars and the position is profitable (short: N bear trend bars): a climactic-exhaustion |
| TrendBarFailsExit | Exit | bar_anatomy_trend_doji | 05 | Exit the long on the first bar that is not another bull trend bar (short: not another bear trend bar) - the spike has stopped. |
| KeyTimeProximity | Entry | breakouts_other | 06 | The bar's close time is within one bar of any of a short list of scheduled clock times (the book's PST list: 7:00, 7:30, 11:00, 11:30, 12:00 |
| NarrowRangeWidth | Entry | breakouts_other | 06 | The N-bar window ending one bar ago is narrow: its high-low width is at or below a multiple of the ATR. A width test, not a trading-range cl |
| EntryPriceRetest | Entry | breakouts_pullback_retest | 06 | Price comes back to within a few ticks of the open position's entry price -- a probe of the resting breakeven stops from that entry -- and h |
| FailedBreakoutReversal | Entry | breakouts_pullback_retest | 06 | Price closed beyond the extreme of the prior N bars (a breakout) and within a few bars closes back inside that range: the breakout failed, t |
| FailedFailureResumption | Entry | breakouts_pullback_retest | 06 | A breakout failed and the failure itself failed: after breakout bar, reversal bar, and a bar reversing back the original way, enter in the o |
| ShallowPullbackLimitBelowPriorHigh | Entry | breakouts_pullback_retest | 06 | During a strong spike, buy on a limit a couple of ticks below the most recent completed bar's high, anticipating only a very shallow pullbac |
| SmallBreakoutTrapReversal | Entry | breakouts_pullback_retest | 06 | Price breaks below a recent swing low or N-bar low by no more than a small capped margin and then closes back above it -- a trapped-seller b |
| SpikeWithoutPullback | Entry | breakouts_pullback_retest | 06 | Over the last N bars the market has risen and at most one bar closed down, with no two consecutive down closes -- a spike that ran without a |
| ThirdBarConfirmsFailedBreakout | Entry | breakouts_pullback_retest | 06 | When the breakout bar and the reversal bar that follows it are about equally strong, wait one more bar: buy when the third bar trades above  |
| WeakFollowThroughBarRequiresPullback | Entry | breakouts_pullback_retest | 06 | Block the close-of-bar entry when the follow-through bar after a strong breakout bar is weak (a small body relative to its range) -- wait fo |
| BreakevenRetestExit | Exit | breakouts_pullback_retest | 06 | Exit the position with a limit order back at the entry price once the market retraces to retest the level the trade was entered from. |
| FailedScalpExit | Exit | breakouts_pullback_retest | 06 | The with-trend entry never got more than N ticks past its trigger and the next bar has fallen back through the signal bar's low: a failed sc |
| AvgBodyBelowRangeFraction | Entry | breakouts_signal_strength | 07 | Over the last N bars, the average body is a small fraction of the average range — a weak spike ('bars with small bodies and tails'), as oppo |
| BarOpensAbovePriorClose | Entry | breakouts_signal_strength | 07 | The bar opens above the prior bar's close (long) / below it (short) — a gap open inside a spike, another of Brooks's spike-quality signs. |
| BodyAboveAverageBody | Entry | breakouts_signal_strength | 07 | Each of the last N bars is a with-trend bar whose body is at least the average body size of the preceding M bars — Brooks's follow-through t |
| ClosePositionInPriorBarRange | Entry | breakouts_signal_strength | 07 | The close sits in the upper part of the PRIOR bar's range (long) / the lower part (short) — Brooks's 'especially if the bear close is in the |
| ConsecutiveBarsLittleOverlap | Entry | breakouts_signal_strength | 07 | Each of the last N consecutive bar pairs overlaps by no more than a fraction of the smaller bar's range — the 'little or no pulling back' ha |
| FailedFollowThroughCount | Entry | breakouts_signal_strength | 07 | At least K times in the last N bars, an against-trend bar was immediately followed by a with-trend bar — the opposing side keeps failing to  |
| LargeRangeBarInWindow | Entry | breakouts_signal_strength | 07 | At least one of the last W bars had a range at least K times the average range of the N bars before it. Negated, it is Brooks's 'wait one to |
| LargeTailedBarCount | Entry | breakouts_signal_strength | 07 | At least K of the last N bars were both large (range at or above the window average) and tailed (body no more than a fraction of range) — th |
| LastTradeWasWinner | Entry | breakouts_signal_strength | 07 | The most recently closed position was profitable — Brooks: 'whenever a breakout trade results in a profit, it is a sign that the trend is st |
| NonOppositeClose | Entry | breakouts_signal_strength | 07 | The bar does not close against the direction: close at or above its open (long) / at or below it (short). Brooks's stated MINIMUM requiremen |
| OppositeLargeBarPair | Entry | breakouts_signal_strength | 07 | Two ADJACENT bars are both large relative to ATR and closed in opposite directions — 'big up + big down = big confusion = trading range'. |
| OppositeLargeBarsInWindow | Entry | breakouts_signal_strength | 07 | Within the last N bars there was at least one large bull trend bar AND at least one large bear trend bar — two spikes in opposite directions |
| PriorBarStrongTrendDay | Entry | breakouts_signal_strength | 08 | The previous bar was a huge with-trend bar — range well above the recent average, closing in the top fraction of its own range — so this bar |
| StrongTrendBar | Entry | breakouts_signal_strength | 08 | The bar is a strong trend bar: a with-trend body that is at least F of the bar's range, and both tails no larger than T of the range. Brooks |
| StrongTrendBarRun | Entry | breakouts_signal_strength | 08 | The last N bars are ALL strong trend bars in the same direction — the bucket's mechanized definition of a Brooks 'spike'. At N=2 it is the a |
| BarRangeAtrMultiple | Entry | breakouts_volume_gap | 08 | The bar's high-low range is at least K times the N-bar average true range — a climax- or spike-sized bar, identical both sides. |
| BodyGapBar | Entry | breakouts_volume_gap | 08 | The bar opens beyond the prior bar's close in the trend direction — open above the prior close (long) / below it (short): a body-to-body gap |
| BreakoutTestNoOverlap | Entry | breakouts_volume_gap | 08 | The pullback since the breakout has not traded back below the breakout bar's high: the lowest low of the last N bars is at or above the high |
| ConsecutiveBodyGapTrendBars | Entry | breakouts_volume_gap | 08 | Each of the last N bars is a bull trend bar (close above open) that also opened above the prior bar's close — a run of body gaps; mirrored f |
| LargeGapVsAverageRange | Entry | breakouts_volume_gap | 08 | The bar gaps and the gap is larger than a fraction of the recent average bar range — Brooks's second 'large gap' test. |
| LargeGapVsRecentGaps | Entry | breakouts_volume_gap | 08 | The bar gaps and its gap is at least as large as the largest gap of the prior N bars — Brooks's first 'large gap' test. |
| LimitEntryAtMicroGapEdge | Entry | breakouts_volume_gap | 08 | The prior bar left a micro gap (its low above the high of the bar before it) and this bar pulls back to within X ticks of that gap's lower e |
| MicroMeasuringGap | Entry | breakouts_volume_gap | 08 | Around a strong bull trend bar, the bar after it does not overlap the bar before it — this bar's low is at or above the high of two bars ago |
| TrueGapBar | Entry | breakouts_volume_gap | 08 | The bar's range does not overlap the reference bar's range at all: low is above the high of the bar N bars ago (long) / high below its low ( |
| GapFilledExit | Exit | breakouts_volume_gap | 08 | Exit the long when the close falls back below the lower edge of the most recent bull gap inside the lookback (the high of the bar before the |
| PullbackNearMissesEntryPrice | Entry | exits_stops | 09 | The pullback comes down to within a few ticks of the entry price but misses it by at least a tick: the bulls defended their breakeven stops, |
| PullbackReachesEntryPrice | Entry | exits_stops | 09 | The pullback trades back to the position's own entry price, where the breakeven stops sit. Brooks reads it as weakness; negate the placement |
| BreakevenStop | Exit | exits_stops | 09 | Once the trade has shown a minimum profit, move the protective stop to the entry price (optionally a few ticks worse) and exit if price come |
| StopAtSignalBarRangeMultiple | Exit | exits_stops | 09 | Size the protective stop to a multiple of the signal bar's own high-low range rather than to a fixed tick amount: big bars get wide stops, s |
| StopBeyondExtremeSinceEntry | Exit | exits_stops | 09 | Put the stop just beyond the worst price the trade has seen since entry: for a long, one tick below the lowest low since the position opened |
| StopBeyondRecentRangeExtreme | Exit | exits_stops | 09 | For a trade taken on a range breakout, put the protective stop well beyond the opposite side of the range so the repeated failed breakouts t |
| StopFractionOfSignalBarRisk | Exit | exits_stops | 09 | When the signal bar is too tall to risk its whole range, place the stop a fraction of the way up from the signal bar's low toward the entry  |
| TightenStopToEntryBarIfStrong | Exit | exits_stops | 09 | Once the entry bar has closed, if it closed as a trend bar in the trade's direction, move the protective stop in from the signal bar's extre |
| WeakEntryBarScratchExit | Exit | exits_stops | 09 | If the entry bar closes weak — a small body relative to its range, a doji — the setup lacked urgency: scratch the trade on that bar's close  |
| WiderStopForSmallSignalBarCapped | Exit | exits_stops | 09 | Widen the signal-bar stop when the signal bar is unusually small (a doji, which invites an outside-bar stop run), but cap the total distance |
| BreakoutMissesScalpTarget | Entry | exits_targets | 09 | Sign of weakness: the breakout above the prior swing high never travelled far enough to give a scalper's profit before the pullback began. |
| MinRewardToRiskFilter | Entry | exits_targets | 10 | Pre-trade gate: take the signal only if the planned reward is at least a multiple of the planned risk. Mechanized off the signal bar itself  |
| RoomToRangeTargetFilter | Entry | exits_targets | 10 | Gate: take the signal only if there is enough distance left to the far side of the recent range to make a scalper's profit -- do not buy jus |
| BarHeightMeasuredMoveTarget | Exit | exits_targets | 10 | The single-bar measured move: project one bar's own high-low height beyond that bar's far extreme and exit there. Brooks's second target aft |
| EntryBarExtremeTarget | Exit | exits_targets | 10 | First target after fading a countertrend bar: the signal/entry bar's own far extreme. Exit the long when the high reaches the high of the ba |
| ExitAtPriorRangeExtreme | Exit | exits_targets | 10 | Exit when price reaches the far extreme of the recent range -- the bottom of the channel that followed a spike, where a countertrend short i |
| ExitOnFirstOppositeBodyAfterRun | Exit | exits_targets | 10 | After a run of at least N consecutive bull-body bars, the first bear-body bar closes the long -- the bulls taking profits on the first bar t |
| ExitOnOppositeStrongTrendBar | Exit | exits_targets | 10 | Exit the long on a single strong bear trend bar -- a large body, small tails, closing against the position. It takes less to convince a trad |
| ExitOnWeakFollowThrough | Exit | exits_targets | 10 | After a large trend bar in the trade's favour, exit within a bar or two if the follow-through weakens -- the next bar is small relative to i |
| FailedTargetReversalExit | Exit | exits_targets | 10 | The trade came within a tick or two of its profit target, the limit never filled, and the market then closed beyond the prior bar's extreme: |
| GapMidpointMeasuredMoveTarget | Exit | exits_targets | 10 | The measuring-gap projection: a midpoint (of a breakout gap, or of the breakout bar itself when the gap is unclear) is treated as the middle |
| PatternHeightMeasuredMoveTarget | Exit | exits_targets | 10 | The workhorse Brooks measured move: capture a reference height at entry (the highest high minus the lowest low of the N bars that produced t |
| RewardRiskDeteriorationExit | Exit | exits_targets | 10 | Re-evaluate the trader's equation every bar against the live close: remaining reward is the distance from the close to the planned target, r |
| BlockEntriesAfterLosingMonth | Entry | context_regime_always_in | 11 | Net profit over the PRIOR completed calendar month was negative — block entries for the current month. Identical both sides. |
| BounceFromLowByAtr | Entry | context_regime_always_in | 11 | The close has bounced at least K x ATR above the lowest low of the last N bars (long) / fallen K x ATR below the highest high (short) — a bo |
| FailedCountertrendScalpReversal | Entry | context_regime_always_in | 11 | A three-bar trap: bar 2 was a bear signal bar (bear body), bar 1 triggered the short by trading below it, and bar 0 closes back above bar 2' |
| NoOppositeBarInLastN | Entry | context_regime_always_in | 11 | None of the last N bars closed against the trend: for the long side, no bar in the window closed below its own open. The trend has run N str |
| CountertrendScalpPercentTarget | Exit | context_regime_always_in | 11 | Take profit once open profit reaches a percentage of the entry price rather than a fixed dollar amount — the countertrend scalp target, sinc |
| Barbwire | Entry | context_regime_trading_range | 11 | Brooks's named barbwire pattern: three bars that largely overlap, at least one of them a doji. Measured as the merge brief's chosen form --  |
| BarsSinceExtremeExceeds | Entry | context_regime_trading_range | 11 | No new extreme for N bars: the highest high of the last N bars is below the highest high of the longer window behind it (mirrored for lows). |
| EntryBarClosedAgainstPosition | Entry | context_regime_trading_range | 11 | A position is open and the current bar closed against it (a bull bar while short, a bear bar while long) -- permission to reverse rather tha |
| OverlappingBarRun | Entry | context_regime_trading_range | 11 | Each of the last N bars overlaps the bar before it by at least fraction F of that earlier bar's range -- Brooks's bar-overlap reading of 'si |
| RangeExtremeFade | Entry | context_regime_trading_range | 11 | The close sits in the bottom fraction of the last N bars' range (long) / the top fraction (short) -- buy the low of a range, sell the high,  |
| RangeMidpointZone | Entry | context_regime_trading_range | 11 | The close sits in the middle band of the last N bars' range -- within F of the range height either side of its midpoint. Identical both side |
| RangeWidthBelowAtrMultiple | Entry | context_regime_trading_range | 11 | CANONICAL TRADING-RANGE CLASSIFICATION for the whole corpus: the height of the last N bars (highest high minus lowest low) is no more than K |
| RangeMidpointTarget | Exit | context_regime_trading_range | 11 | Exit when price reaches the midpoint of the prior N-bar range -- the magnetic middle a failed breakout is pulled back to. Mirrored: the long |
| TightRangeBlocksEntries | Switch | context_regime_trading_range | 11 | While the last N bars are unusually tight (height no more than K times the ATR), block all new entries whatever else the chart shows -- Broo |
| ConsecutiveTrendBarRun | Entry | context_regime_trend_strength | 11 | The last N bars are all trend bars in the same direction — each closes above its own open with a body at least `bodyFraction` of its range ( |
| StrongTrendBarCount | Entry | context_regime_trend_strength | 11 | At least K of the last N bars were strong trend bars in the trend's direction — the count form of the strong-trend read, which tolerates the |
| AverageBarOverlap | Entry | lines_channels_channels | 12 | The mean bar-to-bar overlap fraction over the last N bars is at or below T. Low overlap is a strong channel or spike; high overlap is a weak |
| CountertrendRunInWindow | Entry | lines_channels_channels | 12 | Somewhere in the last N bars there was a run of at least K consecutive bars each making a lower high (bull side) -- a broad swing inside the |
| MicroChannelBreakoutBar | Entry | lines_channels_channels | 12 | The first bar to violate a confirmed micro channel: the run counter stood at minBars or more on the prior bar and this bar's low is below th |
| MicroChannelFailedBreakoutEntry | Entry | lines_channels_channels | 12 | After a micro channel breaks, a bar within the next few bars closes back above the breakout bar's high -- the failed-breakout / high 1 buy t |
| MicroChannelRunLength | Entry | lines_channels_channels | 12 | A run of N or more consecutive bars none of which pulled back: every bar's low is at or above the prior bar's low (bull), every bar's high a |
| MicroChannelSameColorLowOverlap | Entry | lines_channels_channels | 12 | Over the last N bars every bar's body is the same colour and each consecutive pair overlaps by no more than a fraction of the later bar's ra |
| OppositeBodyCountInWindow | Entry | lines_channels_channels | 12 | The number of bars in the last N whose body is against the trend direction is at or below K -- few bear bodies in a bull channel means the c |
| PullbackFromRecentHigh | Entry | lines_channels_channels | 12 | The bar's low is at least K x ATR below the highest high of the last N bars -- Brooks's 'limit orders at fixed intervals below the most rece |
| TightChannel | Entry | lines_channels_channels | 12 | Over the last N bars the market made net progress of at least X x ATR while the deepest pullback from its running extreme stayed within Y x  |
| AtrAtExtreme | Entry | climax_reversal | 13 | The ATR is at its highest of the last extremeLookback bars -- a volatility extreme, which Brooks reads as the end of a bear trend being near |
| ClimaxBar | Entry | climax_reversal | 13 | A climax bar: a strong trend bar whose high-low range is at least climaxMultiple times the N-bar ATR. Long side is a large BULL trend bar (a |
| ConsecutiveClimaxBarCount | Entry | climax_reversal | 13 | At least minClimaxes climax bars in the same direction within the last windowBars, each separated from the previous one by at least one non- |
| LargestTrendBarOfTheRun | Entry | climax_reversal | 13 | This bar's range is the largest of the last runBars bars and it is a trend bar -- Brooks's 'the biggest bull trend bar of the trend' exhaust |
| EntryBarRangeStop | Exit | climax_reversal | 13 | Stop out when the open loss exceeds stopMultiple times the high-low range of the bar the position was entered on, rather than a fixed dollar |
| ParabolicAccelerationExit | Exit | climax_reversal | 13 | The move is accelerating: the net gain of the last legBars bars exceeds accelMultiple times the net gain of the legBars before that. A parab |
| DistanceAboveRecentLow | Entry | swing_structure | 13 | The close has risen at least resumeAtr x ATR above the lowest low of the last `lookback` bars (mirror: fallen that far below the recent high |
| HigherLowBar | Entry | swing_structure | 13 | The bar's low is above the prior bar's low (mirror: the bar's high is below the prior bar's high) - Brooks's plainest with-trend buy setup,  |
| HigherLowCount | Entry | swing_structure | 13 | At least minCount of the last `lookback` bar pairs made a higher low than the bar before (mirror: at least minCount made a lower high) - a c |
| PullbackDepthFromRecentHigh | Entry | swing_structure | 13 | The pullback from the recent high has reached at least retracementFraction of the current leg's range: legHigh - low[0] >= retracementFracti |
| TrendingHighsAndLows | Entry | swing_structure | 13 | Every one of the last `trendBars` bar pairs made BOTH a higher high and a higher low (mirror: both lower) - Brooks's 'trending highs and low |
| AverageRangeBelowDollarThreshold | Entry | misc | 14 | The instrument's recent average bar range is below a small dollar threshold -- avoid scalp-sized targets; price-action entries can still be  |
| CloseAboveHighestClose | Entry | misc | 14 | Close is at or above the highest close (long) / at or below the lowest close (short) of the N bars ending one bar ago. |
| DeepPullbackRetracementFilter | Entry | misc | 14 | Once the current pullback has retraced at least R percent of the leg's range (measured over a fixed lookback window, not a swing-pivot searc |
| OppositeCloseCountBelowThreshold | Entry | misc | 14 | Over the last N bars, fewer than K closed against the intended direction -- the pullback/rally is still mostly one-sided. |
| TrendingBarBodies | Entry | misc | 14 | Each of the last N bars has a body top and body bottom above (long) / below (short) those of the bar before it -- trending bodies, not just  |
| AdverseBodyCountExit | Exit | misc | 14 | Exit the position if N consecutive bars close against it -- a tighter tolerance than a full stop, meant for positions taken on a weak origin |
| HorizontalFlagWidthTest | Entry | three_push_patterns | 14 | The last N bars span less than K times the ATR — a flat, horizontal flag or triangle. Negated, it is the 'tall enough to fade the extremes'  |
| OutsideOutsidePattern | Entry | three_push_patterns | 14 | An outside bar is immediately followed by a larger outside bar that engulfs it — Brooks's 'oo' pattern, a miniature expanding triangle in tw |
| ShrinkingConsecutiveRanges | Entry | three_push_patterns | 14 | The last N bars span less than a fraction of the span of the N bars before them — two consecutive flags with the second one smaller, which B |
| MinimumAbsoluteVolume | Entry | volume | 14 | The bar's volume is at or above an absolute floor — a share or contract count, not a ratio. Brooks's liquidity / eligibility gate. Identical |
| VolumeBelowAverageFraction | Entry | volume | 14 | The bar's volume is at or below a fraction of its own N-bar average volume — Brooks's 'quiet, low-volume market' gate. Identical both sides. |
| PauseBarBroad | Entry | leg_counting | 14 | Brooks's BROAD pullback definition: any pause in the trend's momentum - the bar is an inside bar, OR a trend bar against the trend's directi |
| PriorSessionLevelTest | Entry | time_session | 14 | The bar trades into one of the prior session's four reference prices - yesterday's high, low, open or close - within a tick tolerance. Long  |
| FirstTradingDayOfMonthFilter | Entry | trade_management | 14 | The current bar falls within the first few trading days of the calendar month. |
