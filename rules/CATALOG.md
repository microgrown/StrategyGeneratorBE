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
| `StopLoss` | Exit | same | 0 | `stopLoss(1000)` | Open loss exceeds X dollars |
| `TakeProfit` | Exit | same | 0 | `takeProfit(1000)` | Open profit exceeds X dollars |
| `AtrProfitTarget` | Exit | same | `lookback` | `lookback(15)`, `multiple(3)` | Open profit exceeds K × the N-bar average true range, converted to dollars |
| `ProfitProtector` | Exit | same | 0 | `maxProfit(1500)`, `retracement(0.5)` | Open profit peaked above X, then gave back to a fraction of that peak |
| `NumBars` | Exit | same | 0 | `numBarsExit(50)` | The position has been open N bars or more |
| `MonthlyProfitTarget` | Switch | same | 0 | `ProfitTarget(5000)` | Equity gained since the start of the calendar month exceeds the target — blocks entries and forces flat |

## Keeping this current

Append a row whenever a rule is added to `rules/`. It is maintained by hand (and
by `/author-rule`); nothing reads it at runtime, so a stale row costs nothing but
a missed duplicate.
