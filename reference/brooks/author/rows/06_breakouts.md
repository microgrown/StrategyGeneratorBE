# CATALOG rows — slice 06, breakouts

Ten of twelve rules written; both twins each, `validateRule` and
`lintElFeatures.py` clean (0 blocking, 0 warnings).

| Rule | Type | Sides | Reaches back | Inputs | Fires when |
|---|---|---|---|---|---|
| `KeyTimeProximity` | Entry | same | `windowBars` | `keyTime1(700)`, `keyTime2(730)`, `keyTime3(1130)`, `windowBars(1)` | This bar's close time, or that of any of the previous `windowBars` bars, is one of three scheduled clock times (EL `Time`, HHMM, exchange clock) — Brooks's key inflection times, 7:00/7:30 PST report releases and 11:30. An OR of discrete instants, which `TimeWindow`'s one continuous band cannot express; repeat a time to use fewer, exactly as `DayOfWeekAnyOf` does with days. The book's window ("within a bar before or after") is in BARS, not minutes, and is backward-only: HHMM→minutes needs `Mod` (UNKNOWN) or `IntPortion` (unregistered), and the forward half would read the future. Intraday bars only |
| `FailedBreakoutReversal` | Entry | mirrored | `rangeBars + failBars` | `rangeBars(20)`, `failBars(3)` | Some bar in the last `failBars` bars closed below the lowest low of the `rangeBars` window ending one bar before it, and this bar closes back above that same level (long); mirrored on highs for the short — the breakout failed, take the other side. Not `CloseAbovePriorHighestHigh`, which fires ON the breakout. The per-candidate window extreme is open-coded in BOTH twins rather than written `Lowest(l, rangeBars)[kk + 1]`: that is a history reference on a function call at a VARIABLE offset, and `Extremes()` (which `Highest`/`Lowest` call) is EL source and is exactly this loop |
| `FailedFailureResumption` | Entry | mirrored | `breakoutLookback + 3` | `breakoutLookback(10)` | Three stages at fixed offsets: the bar 3 back is a bull bar closing above the highest high of the `breakoutLookback` bars before it, the bar 2 back is a bear bar (the failure), the bar 1 back is a bull bar (the failure's failure), and this bar closes above that bar's high — resume in the original breakout direction. Short is the mirror. `Highest(h, n)[4]`, a constant offset, so the built-in stands |
| `ShallowPullbackLimitBelowPriorHigh` | Entry | mirrored | 1 | `pullbackPoints(0.5)` | This bar's low reaches the prior bar's high minus X (long) / this bar's high reaches the prior bar's low plus X (short) — the shallow-pullback limit fill inside a spike, mechanized on the completed bar per the standing convention. X is in PRICE UNITS, instrument-specific, exactly as `CloseNearPriorLow`'s `threshold` is: the book's 2 ticks cannot be converted without `MinMove`/`PriceScale`, neither of which is registered. Not `BreakoutPullbackLimitEntry`, which fills below the prior bar's LOW |
| `SmallBreakoutTrapReversal` | Entry | mirrored | `lookback` | `lookback(20)`, `marginPoints(0.5)` | This bar's low breaks below the lowest low of the N bars ending one bar ago by no more than X, and the bar closes back above that level (long); mirrored on highs for the short — Brooks's capped "one-tick breakout" bear trap. The cap is what separates it from `FailedBreakoutReversal`, which needs no cap and fires a bar or more later. X is in PRICE UNITS (see `ShallowPullbackLimitBelowPriorHigh`) |
| `SpikeWithoutPullback` | Entry | mirrored | `spikeBars` | `spikeBars(5)`, `maxPullbackBars(1)` | Close is above the close N bars ago, at most `maxPullbackBars` of the last N bars closed below their own open, and no two such bars were adjacent (long); mirrored for the short — a spike that ran without a pullback. Not `ConsecutiveUpBars`, which allows no down bar at all. The count is EL `CountIF` over prices (real history, no zero-filled variable mirror). Kept whole: its first term is `Momentum(spikeBars)`, but Brooks's "spike" is the pair — net progress plus no pullback — and the count term alone is a different claim |
| `ThirdBarConfirmsFailedBreakout` | Entry | mirrored | 2 | `equalTol(0.3)`, `bodyFraction(0.6)` | The bar 2 back is a bear bar, the bar 1 back is a bull bar whose body is within `equalTol` of it in size, and this bar trades above that bar's high and closes as a bull trend bar whose body is at least `bodyFraction` of its range (short is the mirror) — the confirmation-timing variant of `FailedBreakoutReversal`: it fires a bar later and only when the two bars are comparably sized. Body tests are written as products, never quotients: EL raises a runtime divide-by-zero on a doji bar |
| `WeakFollowThroughBarRequiresPullback` | Entry | mirrored | 1 | `bodyFraction(0.6)`, `weakBodyFraction(0.3)` | The prior bar was a strong bull trend bar (body at least `bodyFraction` of its range) and this bar's body is under `weakBodyFraction` of its own range (short is the mirror) — weak follow-through after a breakout. Brooks uses it to BLOCK the close-of-bar entry, so the intended placement is NEGATED; written in the positive so the negate toggle reads naturally. Not `BodyBelowAtrFraction`, which measures the body against ATR and reads one bar |
| `BreakevenRetestExit` | Exit | mirrored | 0 | `tolerancePoints(0.25)` | Long and the bar's low comes back to the entry price plus X (short: high back to entry minus X) — the limit exit at breakeven when the market retests the level the trade was entered from. Not `TrailingStop`/`ProfitProtector`, which measure dollars from the peak. Near neighbour of slice 09's `BreakevenStop`, deliberately: that one arms on a minimum peak profit and triggers on the CLOSE at or below entry, this one is unarmed and triggers on the bar's LOW touching entry, so they fire on different bars. The `MarketPosition` guard is load-bearing, not decoration: `EntryPrice` is 0.0 when flat and a back-adjusted price can be negative. X is in PRICE UNITS (see `ShallowPullbackLimitBelowPriorHigh`) |
| `FailedScalpExit` | Exit | mirrored | 2 | `failureDollars(100)` | The position is at most 1 bar old, its peak profit never exceeded X dollars, and this bar trades below the signal bar's low (short: above its high) — a with-trend entry that never went anywhere. Not `NumBarsIfLosing`, which is a bar count plus a profit sign; this caps the PEAK (`MaxPositionProfit`, intrabar, net of the entry side) and adds a price level. The book's five-tick figure is expressed in DOLLARS: ticks need `MinMove`/`PriceScale`. The signal-bar offset `BarsSinceEntry + 1` is computed and CLAMPED to 2 in `preConditionHook` in both twins — EasyLanguage does not short-circuit, so left in the condition it would reach back `BarsSinceEntry + 1` bars on every bar of an open position |

## Not written

- **`NarrowRangeWidth`** — suspected duplicate of **`RangeWidthBelowAtrMultiple`**
  (slice 11, `context_regime_trading_range`), which the merge pass missed.
  Slice 11's rule is `highest(high, N) - lowest(low, N) <= K * atr(M)`; this one
  is the same arithmetic with both extremes read one bar back, i.e. the same
  statistic evaluated a bar late, which no per-placement toggle distinguishes
  and which nobody has measured as different. Slice 06's own merge note says the
  tight-range measure "is owned by context_regime_trading_range and must be
  referenced, not redefined here" — and then restates it. Slice 14's
  `HorizontalFlagWidthTest` is a third statement of the same test; the roll-up
  should keep one Entry-role rule (slice 11's), plus slice 11's Switch-role
  `TightRangeBlocksEntries`. If Brian wants the one-bar-back form kept, it is a
  three-line change to slice 11's rule (a `barsBack` input defaulting to 0).
- **`EntryPriceRetest`** — suspected duplicate of **`PullbackReachesEntryPrice`**
  (slice 09, `exits_stops`), which the merge pass missed. Slice 09's rule is
  `MarketPosition > 0 and Low <= EntryPrice + tol`; this rule is that same test
  AND a second, independently meaningful term, `Close >= EntryPrice - tol` ("and
  holds"). Entry panes already AND, so the compound is strictly worse than the
  pair, and the pair's first half already exists. The separable half — the close
  back at or above the entry price — is not in any slice; if it is wanted, it
  should be authored as its own one-term rule under a name that says so, not as
  `EntryPriceRetest`.
