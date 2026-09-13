# Slice 15 — EMA relations and the swing-pivot primitive

CATALOG rows for the rules written from `A_QUEUE_2.json`, keys `xaverage` and
`other`. Table format is `rules/CATALOG.md`'s.

| Rule | Type | Sides | Reaches back | Inputs | Fires when |
|---|---|---|---|---|---|
| `EmaGapBar` | Entry | mirrored | 0 | `emaLength(20)` | The bar does not touch the N-bar EMA: its low is above the average (long) / its high below it (short) — Brooks's "moving average gap bar", ten restatements of one single-bar test. Not `CloseAboveAverage`, which compares the CLOSE with its own SIMPLE average; this reads the bar's extreme against an EXPONENTIAL one, so it fires on different bars. The EMA is `WFSafe_Xaverage`, MEASURED bit-identical to the plain `XAverage` built-in at a fixed length (`(wf − xa) · 1e12` exactly 0 on all 17,785 probed bars), seeded with the PRICE on the study's first calculated bar, recurrence `x + sf·(p − x)` as ONE statement with `sf = 2/(emaLength+1)`, and no warm-up hole. Reaches back 0 because the EMA is recursive state, not a window — but it never forgets its seed, so Max Bars Back and the chart start are part of the specification. `emaLength` MUST BE PINNED in the grid: the walkforward length-change behaviour of the wrapper is unmeasured |
| `EmaTouch` | Entry | same | 0 | `emaLength(20)` | The bar's range contains the N-bar EMA — the average is tested this bar. T18-01's exact straddle test, chosen over the 1-2 tick tolerance forms because `MinMove`/`PriceScale` are unregistered. Direction-agnostic, so both sides are the same text. The higher-timeframe average is this rule at a longer `emaLength` on the same series, not a resampling problem (Brooks's own arithmetic: 90 bars on 1-minute stands in for the 5-minute 20-bar EMA, 240 for the 60-minute), which is why `EmaTouch(90)` and `EmaTouch(240)` are placements and not rules. Same measured `WFSafe_Xaverage` mirror as `EmaGapBar`; `emaLength` pinned |
| `EmaTouchRecovery` | Entry | mirrored | 0 | `emaLength(20)` | The bar traded down to or through the N-bar EMA and closed back above it (long); mirrored on the short side. Not `EmaTouch`, which only asks whether the average is inside the bar's range and is direction-agnostic; this also reads where the bar CLOSED. Not `CloseBeyondEma`, which never looks at the low. The source's after-11:30 gate is `TimeWindow` in a separate pane. Same measured `WFSafe_Xaverage` mirror as `EmaGapBar`; `emaLength` pinned |
| `CloseBeyondEma` | Entry | mirrored | `atrLookback + 1` | `emaLength(20)`, `marginAtr(0)`, `atrLookback(14)` | The close is above the N-bar EMA plus K ATRs (long) / below it minus K (short). At the default `marginAtr = 0` this is the bare close-beyond test four chapters give as the canonical use of "the moving average". Not `CloseAboveAverage`: that uses EL's fresh N-bar SIMPLE `Average`, this uses `XAverage`. The margin is in ATRs rather than the source's 4 ticks because `MinMove`/`PriceScale` are unregistered. ATR is `WFSafe_AvgTrueRange`'s rolling accumulator, one call site in the hook. Same measured `WFSafe_Xaverage` mirror as `EmaGapBar`; `emaLength` pinned |
| `CloseWithinAtrOfEma` | Entry | same | `atrLookback + 1` | `emaLength(20)`, `nearAtr(0.5)`, `atrLookback(14)` | The close is no further than K ATRs from the N-bar EMA, measured symmetrically — "at the moving average"; negate the placement for "enough room to the moving average to be worth the trade", which is the same band read from the other side. `CloseWithinAtrOfVwap` is the template, with the session VWAP swapped for an EMA and symmetric rather than one-sided per side. Book values for the band disagree (0.5 ATR, 4 / 3 / 2 ticks), so `nearAtr` is an optimizer input in ATRs. The SIGNED reading is this rule ANDed with `CloseBeyondEma` negated, not a rule. Same measured `WFSafe_Xaverage` mirror as `EmaGapBar`; `emaLength` pinned |
| `SwingHigh` | Entry | mirrored | `lookback - 1 + strength` | `strength(2)`, `lookback(20)` | The bar `strength` bars ago is a CONFIRMED swing high (short: swing low) — the corpus's pivot primitive, detection only. MEASURED (`EL_Swing_Probe.txt`): the pivot test is MIXED, at or above the `strength` OLDER bars and STRICTLY above the `strength` NEWER bars, so a flat top yields exactly ONE pivot, the later of the equal bars — this refutes the merged pseudocode's `>=`-on-both-sides, taken from Brooks's symmetric glossary wording, and it changes every flat-top / double-top / pivot-counting rule that follows. Confirmation lag is exactly `strength` bars, so the rule is lookahead-safe; `lookback` is EL's `Length`, candidate offsets `0..lookback-1` inclusive, with the −1 SENTINEL (guarded explicitly) when no pivot lies in the window and no fallback to an older one; the neighbourhood test reaches `strength` bars PAST the window, which is why the depth is `lookback - 1 + strength` rather than `lookback - 1`. Comparisons carry the 2.22e-12 tolerance (`el_gt`/`el_ge`), which on the probe's tolerance series changes WHICH bar is the pivot. The low side's tie sense is the mirror of the measured high-side rule, not an observation. There is no `WFSafe_SwingHigh`, so plain EL governs |
| `BreakoutLevelRetest` | Entry | mirrored | `max(lookback - 1 + strength, maxWaitBars, atrLookback + 1)` | `strength(2)`, `lookback(20)`, `maxWaitBars(3)`, `toleranceAtr(0.1)`, `maxOvershootAtr(0.2)`, `atrLookback(14)` | A close within the last `maxWaitBars` bars broke above the most recent confirmed swing high in the window, and this bar pulls back to that level and holds it: the low comes to within `toleranceAtr` ATRs of the level but no more than `maxOvershootAtr` ATRs through it (short mirrored on a swing low). The level is a confirmed pivot rather than the merged pseudocode's `highest(high, lookback)` one bar before the breakout bar — the same idea with the noise filtered by `strength`, and the form the rest of the corpus will use; the pivot scan is INLINED rather than referencing `SwingHigh.json`. `kk < pivotHighBar` keeps the breakout strictly newer than the pivot. `toleranceTicks(2)` became `toleranceAtr(0.1)`: `MinMove`/`PriceScale` are unregistered and the sources give 0.1-0.2 ATR for the same test, so both bands are ATR fractions, as in `PriorSessionLevelTest`. Not `BreakoutTestNoOverlap`, which requires the pullback NEVER to trade back into the level — close to this rule's opposite; not `CloseAbovePriorHighestHigh`, which is only the breakout leg |

## Not written

- `CloseCrossesEma` — blocked on `xaverage` lagged read. Pseudocode is `close[1] <= ema[1] && close[0] > ema[0]`, which needs `XAverage(...)[1]`; the register row records lagged reads as UNMEASURED. See the note below: a `crosses above` formulation would avoid the lag but is a different rule.
- `EmaGapBarBreakoutEntry` — blocked on `xaverage` lagged read (`ema[1]`).
- `ConsecutiveClosesBeyondEmaRun` — blocked on `xaverage` lagged read (`ema[i]`, i over `0..strongBars-1`).
- `BarsBeyondEmaCount` — blocked on `xaverage` lagged read (`ema[i]` inside a `CountIF` over `0..lookback-1`; `countif`'s counted condition is a true SERIES, so every counted bar reads the EMA at its own offset).
- `NoTwoConsecutiveClosesBeyondEma` — blocked on `xaverage` lagged read (`ema[k]` and `ema[k+1]` across the window).
- `EmaSlope` — blocked on `xaverage` lagged read (`ema[slopeLookback]`).
- `EmaFlat` — blocked on `xaverage` lagged read (`ema[slopeLookback]`).
- `PullbackDepthBeyondEma` — blocked on `xaverage` lagged read (the EMA at every lag in the window), and separately needs an EL `Lowest` over a COMPUTED series (`close - ema`), which is the zero-filled-variable-history hazard the `average` row records; it needs its own look independent of the EMA probe.
- `BuyLimitBelowRisingMA` — blocked on `xaverage` lagged read (`ma[maSlopeLookback]`), and separately is a limit-order entry, which the corpus's completed-bar convention does not express.
- The whole `tick` list in `A_QUEUE_2.json` — out of scope for this slice; waiting on an engine tick-size accessor.

## Notes for the orchestrator

- `CloseCrossesEma` vs the catalog's `MovingAverageCross`: NOT a duplicate, and
  the near-miss is worth recording. `MovingAverageCross` crosses two SIMPLE
  averages of the close against each other; at `fastLength = 1`,
  `Average(Close, 1)` is the close, so it degenerates to "the close crosses the
  N-bar SIMPLE average" — still simple, not exponential, exactly the
  `CloseAboveAverage` / `EmaGapBar` distinction one level up. The two rules fire
  on different bars for any real series.
- A design decision `CloseCrossesEma` needs before it is written: the merged
  pseudocode is a two-bar test and therefore needs `XAverage(...)[1]`, but EL's
  `crosses above` is a VERIFIED state machine that reads only the CURRENT value
  of both series and would unblock the rule today. It is not the same rule —
  `crosses` bridges equality runs and looks back to the most recent NON-equal
  relation, which can be many bars — so it is a spec change, not a translation
  choice, and it is left to the orchestrator rather than taken silently.
- All five EMA rules lean on the `xaverage` / `wfsafe_xaverage` rows' in-row
  caveat rather than on an ASSUMED status: both rows are VERIFIED, but the
  walkforward LENGTH CHANGE is unmeasured, so `emaLength` must be PINNED in
  every grid these rules appear in. The gate cannot enforce a caveat inside a
  VERIFIED row; this is the authoring pass carrying it.
- `swinglow` / `swinglowbar` carry one inferred item: the low-side TIE sense is
  the mirror of the measured high-side rule, not an observation. Both `SwingHigh`
  and `BreakoutLevelRetest` depend on it on their short sides.
- The measured pivot sense retires `PullbackDepthFromRecentHigh`'s standing note
  that "`SwingHigh`/`SwingLow` are unregistered, and the window is the standin",
  and it changes the flat-ledge behaviour assumed by the merge pass for `Ledge`,
  `DoubleExtreme`, `MicroDoubleExtreme`, `HigherSwingHigh`, `TrendingSwings` and
  `LaggedHigherHigh`: a flat run of equal highs is ONE pivot, not N.
