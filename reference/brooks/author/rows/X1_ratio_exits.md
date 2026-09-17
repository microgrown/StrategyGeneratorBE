# CATALOG rows — slice X1_ratio_exits (one risk unit, R-multiple target)

Not a merged slice: Brian's spec of 2026-09-17, written to replace the two B09
rules that were blocked on a non-existent initial-risk accessor. Two keys, both
written, both twins each. Rows are in `rules/CATALOG.md` table format, ready to
append.

| Rule | Type | Sides | Reaches back | Inputs | Fires when |
|---|---|---|---|---|---|
| `StopLossTakeProfitDollar` | Exit | same | 0 | `stopDollars(1000)`, `rewardRisk(2)` | Open loss reaches `stopDollars`, or open profit reaches `rewardRisk × stopDollars` — Brooks's "risk one unit to make R units" management with the risk and the R multiple as the two inputs. It IS `TakeProfitWithRatioStop` re-parameterized stop-first (`target = rewardRisk × stopDollars`, `stopRatio = 1 / rewardRisk`), and exists because the grid axes Brian wants are the risk size and the reward-to-risk ratio, not a target and a stop fraction: the same iteration budget sweeps a different lattice of (stop, target) pairs, and the R multiple is the number Brooks actually quotes. It also replaces `StopAtInitialRiskMultiple` and `ProfitTargetAtInitialRiskMultiple` (B09 "Not written"), which wanted the entry-frozen initial risk the engine has no accessor for; a fixed dollar risk is the honest stand-in and needs no new accessor. Profit accessor, sign convention and the tolerance-carrying comparisons are `TakeProfitWithRatioStop`'s verbatim — `OpenPositionProfit` is close-marked and net of the ENTRY side's costs (VERIFIED), the stop leg is a strict `<` against a negated threshold, and there is no `MarketPosition` guard because both generators already gate an exit on the position at signal time, as `StopLoss` and `TakeProfitWithRatioStop` rely on. Direction-agnostic, so both sides are identical text |
| `StopLossTakeProfitATR` | Exit | same | `atrLength + 1` | `atrLength(14)`, `stopAtrMultiple(2)`, `rewardRisk(2)` | Open loss reaches `stopAtrMultiple × ATR(atrLength)` converted with `BigPointValue`, or open profit reaches `rewardRisk ×` that same distance — `StopLossTakeProfitDollar` with the risk unit sized by volatility instead of fixed in dollars. The risk is captured ONCE on the fill bar and frozen for the life of the trade, because Brooks's initial risk is fixed at entry: re-reading the ATR every bar would let a later volatility burst widen a stop that was already accepted. That makes it neither `AtrProfitTarget` (re-reads the ATR every bar and is a target only) nor `AtrTrailingStop` (trails from the position's PEAK profit), and one parameter drives BOTH legs, which is why it is one rule and not two. It replaces the same two blocked B09 keys: an ATR captured at the fill bar is the measurable stand-in for the entry-frozen initial risk. The capture is `StopAtSignalBarRangeMultiple`'s convention — `BarsSinceEntry = 0` is the fill bar and is also 0 while flat (VERIFIED, and it restarts through a reversal), so the capture re-arms on every flat bar and is never a `MarketPosition = 0` reset, which a reversal never reaches. `WFSafe_AvgTrueRange`, not `AvgTrueRange`: MultiWalk's override is a different function and wins — the rolling accumulator ported from `AtrProfitTarget`, seeded with a full N-term sum on the study's first calculated bar (MaxBarsBack + 1), re-seeded when the length changes, and updated as TWO statements because EL evaluates `S[1] + in − out` left to right. It is read unconditionally on every bar in both twins so the accumulator advances whatever the position is; only the capture is gated, which is also why "reaches back" is the ATR's own `atrLength + 1` and not the length of the longest trade. `BigPointValue` is the raw multiplier and is NOT currency-converted while `OpenPositionProfit` is, as in `AtrProfitTarget`. Direction-agnostic, so both sides are identical text |

## Not written

- `StopAtInitialRiskMultiple` — **superseded**, by Brian's decision of
  2026-09-17, by `StopLossTakeProfitDollar` (fixed-dollar risk unit) and
  `StopLossTakeProfitATR` (ATR risk unit frozen at the fill bar). It remains
  blocked as originally specified: there is still no accessor for the
  entry-to-initial-stop distance (`ctx.InitialStopPrice()`), and the B09 row
  stands as the engine request. The two rules above supply the same management
  — stop first, target at an R multiple of it — from risk units the engine can
  actually measure, so the engine change is no longer on this slice's path.
- `ProfitTargetAtInitialRiskMultiple` — **superseded** by the same two rules and
  the same decision. Its target leg is the `rewardRisk × risk` leg of both, and
  it needed the same missing accessor.
