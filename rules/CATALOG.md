# Rule catalog

One line per rule in `rules/`. Read this before writing a new rule — it is the
cheap first pass of the duplicate check. Open the full JSON only for a rule that
looks like a plausible match.

**Sides** — `mirrored` means the short condition is the long condition reflected
(`>` becomes `<`, highest becomes lowest); `same` means the rule is direction-
agnostic and both sides are identical text, which is correct for anything phrased
in profit, volume, elapsed bars, or absolute range.

**Reaches back** — the deepest bar index the rule can touch, as an expression over
its inputs. Max Bars Back for a strategy must cover the largest of these across
every placement, evaluated at each input's *stop* value.

| Rule | Type | Sides | Reaches back | Inputs | Fires when |
|---|---|---|---|---|---|
| `Momentum` | Entry | mirrored | `lookback` | `lookback(200)` | Close is above the close N bars ago |
| `DualMomentum` | Entry | mirrored, one input per side | `max(longLookback, shortLookback)` | `longLookback(20)`, `shortLookback(20)` | Long side: close is above the close N bars ago. Short side: close is below the close M bars ago. `Momentum` with the two sides split onto separate inputs |
| `MomentumChange` | Entry | mirrored | `lookback + 1` | `lookback(50)` | Momentum turns positive *this* bar — above N bars ago now, but it was not on the previous bar |
| `MomentumConsecutiveBars` | Entry | mirrored | `lookback + consecutiveBars - 1` | `lookback(200)`, `consecutiveBars(10)` | Momentum has held positive for N consecutive bars |
| `Breakout` | Entry | mirrored | `lookback - 1` | `lookback(50)` | Close is at or above the highest close of the last N bars |
| `BarRangeAboveStd` | Entry | same | `lookback - 1` | `numDevs(2)`, `lookback(15)` | This bar's high−low range exceeds the N-bar mean range plus K standard deviations |
| `VolumeBelowAverage` | Entry | same | `lookback - 1` | `lookback(10)` | This bar's volume is below its own N-bar average |
| `AdxBelowThreshold` | Entry | same | `lookback` | `lookback(14)`, `threshold(25)` | The 14-bar ADX (MW's `WFSafe_ADX`, bit-exact port) is below the threshold — a low-trend regime filter, identical both sides |
| `AtrBandBreakout` | Entry | mirrored | `max(lookback - 1, atrLookback + 1)` | `lookback(20)`, `atrLookback(15)`, `atrMultiple(1)` | Close is at or beyond the ATR band around the Donchian midline: base = (highest high + lowest low of N bars)/2, long at close ≥ base + K×ATR, short at close ≤ base − K×ATR |
| `CloseAboveAverage` | Entry | mirrored | `lookback - 1` | `lookback(50)` | Close is above (long) / below (short) its own N-bar average |
| `ClosePercentileRank` | Entry | mirrored | `lookback - 1` | `percentile(10)`, `lookback(100)` | Close ranks in the top (long) / bottom (short) X% of the last N closes — ties share the better rank; at X ≈ 100/N the long side degenerates to `Breakout` |
| `ConsecutiveUpBars` | Entry | mirrored | `consecutiveBars - 1` | `consecutiveBars(3)` | Each of the last N bars closed above (long) / below (short) its own open — a tie bar fails both sides |
| `LaggedHigherHigh` | Entry | mirrored | `lookback + 1` | `lookback(1)` | The bar N bars ago made a higher high than the bar before it (long) / a lower low (short) |
| `CloseAbovePriorHigh` | Entry | mirrored | `lookback` | `lookback(1)` | Close is above the high (long) / below the low (short) of the bar N bars ago — at N=1, a close outside the prior bar's range |
| `AtrAboveAverage` | Entry | same | `atrLookback + 1` | `atrLookback(15)`, `lookback(20)` | The ATR exceeds its own N-bar average — a volatility-expansion filter; the average runs over the ATR variable's zero-padded warm-up history, so it passes easily early on |
| `AtrRising` | Entry | same | `max(atrLookback + 1, max(nearLag, farLag))` | `atrLookback(15)`, `nearLag(1)`, `farLag(10)` | The ATR as of X bars ago is above the ATR as of Y bars ago — a volatility-trend filter; both readings come from the ATR variable's zero-padded warm-up history, so for the first max(X, Y) evaluated bars the older reading is 0 and the rule passes trivially |
| `AtrFastAboveSlow` | Entry | same | `max(fastLookback, slowLookback) + 1` | `fastLookback(5)`, `slowLookback(20)` | The X-bar ATR exceeds the Y-bar ATR — a volatility-expansion filter from two independent `WFSafe_AvgTrueRange` call sites; identical both sides |
| `StopLoss` | Exit | same | 0 | `stopLoss(1000)` | Open loss exceeds X dollars |
| `TakeProfit` | Exit | same | 0 | `takeProfit(1000)` | Open profit exceeds X dollars |
| `AtrProfitTarget` | Exit | same | `lookback + 1` | `lookback(15)`, `multiple(3)` | Open profit exceeds K × the N-bar average true range, converted to dollars |
| `ProfitProtector` | Exit | same | 0 | `maxProfit(1500)`, `retracement(0.5)` | Open profit peaked above X, then gave back to a fraction of that peak |
| `TrailingStop` | Exit | same | 0 | `trailStop(1000)` | Open profit has fallen more than X dollars below the position's peak profit |
| `AtrTrailingStop` | Exit | same | `lookback + 1` | `lookback(15)`, `multiple(3)` | Open profit has fallen more than K × the N-bar average true range (in dollars) below the position's peak profit |
| `NumBars` | Exit | same | 0 | `numBarsExit(50)` | The position has been open N bars or more |
| `MonthlyProfitTarget` | Switch | same | 0 | `ProfitTarget(5000)` | Equity gained since the start of the calendar month exceeds the target — blocks entries and forces flat |
| `DayOfWeekEntry` | Entry | one input per side | 0 | `dayLong(4)`, `dayShort(3)` | Long when the bar's close date falls on weekday X, short on weekday Y — EL numbering, 0 = Sunday .. 6 = Saturday |
| `TrueRangeAvgRatio` | Entry | same | `lookback * slowFactor` | `lookback(30)`, `slowFactor(2)`, `multiple(1)` | The plain N-bar mean of True Range exceeds K × the plain (N × F)-bar mean — EL's fresh `Average(TrueRange, n)`, not the `WFSafe_` rolling sum, so not `AtrFastAboveSlow`; negate for the book's "volatility contraction" form |
| `VolumeAboveAverageMultiple` | Entry | same | `lookback - 1` | `lookback(35)`, `multiple(2)` | This bar's total ticks (up + down, `ctx.Ticks`, not the up-tick `volume` alias) exceed K × their own N-bar average; the average runs over an EL variable's zero-padded warm-up history |
| `BodyBelowAtrFraction` | Entry | same | `atrLookback + 1` | `atrLookback(14)`, `fraction(0.2)` | The bar's body, \|close − open\|, is smaller than F × the N-bar ATR (`WFSafe_AvgTrueRange` rolling form) — a narrow-body filter, identical both sides |
| `TakeProfitWithRatioStop` | Exit | same | 0 | `target(3000)`, `stopRatio(0.5)` | Open profit exceeds X dollars, or open loss exceeds R × X — one parameter drives both legs, which is why it is not `TakeProfit` + `StopLoss` |
| `RsiBelowThreshold` | Entry | mirrored | `lookback` | `lookback(14)`, `threshold(30)` | Long when the N-bar `WFSafe_RSI` of close is below T; short when above 100 − T (bit-exact port, `EL_WFSafeRsi_Probe.txt`) |
| `RsiRising` | Entry | mirrored | `lookback` | `lookback(14)` | Long when the N-bar `WFSafe_RSI` is above its previous-bar value; short when below — the previous value is the function's own series history, 0 on the first calculated bar |
| `CloseWithinAtrOfVwap` | Entry | mirrored | `atrLookback + 1` | `atrLookback(14)`, `multiple(0.5)` | Long when close is no more than K × ATR above the session VWAP (reset on each new date, `AvgPrice × Ticks` weighted, `AvgPrice` = (O+H+L+C)/4 or (H+L+C)/3 on a zero open); short when no more than K × ATR below it — the AI-book original's short side (`close + VWAP > …`) was degenerate and replaced by the mirror |

## Keeping this current

Append a row whenever a rule is added to `rules/`. It is maintained by hand (and
by `/author-rule`); nothing reads it at runtime, so a stale row costs nothing but
a missed duplicate.
