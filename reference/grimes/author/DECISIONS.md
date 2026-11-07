# Orchestrator decisions during Grimes A-list authoring (2026-09-21)

- Existing-rule amendment ownership (one agent per existing rule): 03_exits owns every stop and
  exit rule it amends (StopBeyondRecentRangeExtreme x2, InitialStopBeyondSwingAtEntry x2,
  SwingPointTrailingStop x2, StopBeyondExtremeSinceEntry, TrailArmedAfterProfitThreshold,
  NumBarsIfLosing, ExitOnOppositeStrongTrendBar); 04_pullbacks owns HigherSwingLow (two proposed
  inputs, decided there), PullbackDepthFromRecentHigh, OppositeBodyCountInWindow, AtrAboveAverage,
  TrendLineSlopeFlattening, TrendLineBreak; 05_ranges owns Momentum (both `lag` and the
  minMoveAtr/atrLookback pair), RangeWidthBelowAtrMultiple, CloseNearSessionExtreme;
  06_breakouts_climax owns LevelTouchCount, ShavedTopBar, ChannelLineBreakTrendBarClose;
  02_keltner owns EmaGapBar.
- Clusters placed in one slice for the agent to collapse or keep: LowTouchesRecentLow /
  LowTouchesRecentRangeLow (06); TrendRateAcceleration / AcceleratingLegsClimax (06);
  HigherSwingLowRun / RisingSwingLowCount (04); NumBarsIfBelowProfitThreshold /
  FlatTradeScratchExit / StalledPositionExit (03).
- Waves: 1 = 01_oscillator, 03_exits, 04_pullbacks; 2 = 05_ranges, 06_breakouts_climax, 02_keltner.
- 2026-09-21 evening: pass 3 paused after seven Opus agents died on API 529/500 server errors
  (three original wave-1 launches, four relaunches). State on disk: slice 03_exits has six new
  rules with both twins, linted, rows written for them in rows/03_exits.md (StopAtLowNBarsAgo,
  StopFractionOfTestedLevelRisk, ProfitTargetAtRiskMultiple, WindfallRangeExpansionExit,
  StalledPositionExit, FlatTradeScratchExit); its 11 remaining rules (ConsecutiveAdverseCloseExit
  plus ten amendments) are untouched; no existing rule has been amended. Slices 01, 02, 04, 05, 06
  have nothing on disk. Resume: relaunch 03 telling it the six exist and rows are written; relaunch
  01 and 04 fresh; then wave 2.
- 2026-09-22: ConsecutiveAdverseCloseExit (03) not written: it is ConsecutiveCloseExit with the
  per-placement flip toggle on (grid consecutiveBars from 1). Brian may ask for a separate file.
- 03 amended: StopBeyondRecentRangeExtreme (+bufferAtrMultiple, atrLookback, confirmBars),
  StopBeyondExtremeSinceEntry (+preEntryBars), InitialStopBeyondSwingAtEntry (+pivotIndex;
  stopTicks now signed), SwingPointTrailingStop (+pivotIndex, maxRiskAtr, atrLength),
  TrailArmedAfterProfitThreshold (+stopOffsetAtr, atrLength), NumBarsIfLosing (+profitThreshold),
  ExitOnOppositeStrongTrendBar (+scratchWindow). Two EL twins now hand-roll the three-pivot scan
  (Occurrence 3+ unmeasured).
- 2026-09-22: 04 collapsed HigherSwingLowRun / RisingSwingLowCount into ONE input `legs(2)` on
  HigherSwingLow (EL twin now inlines the pivot scan; behaviour unchanged at default). 04 deferred
  ImpulseLegNetMove to 05: at searchBars 0 it is MomentumBeyondAtrMultiple term for term, so 05
  carries it as a third new input `searchBars(0)` on Momentum. 04 amended OppositeBodyCountInWindow
  (+minOpposite), AtrAboveAverage (+atrMultiple; REVERTED 2026-09-27, now AtrAboveAverageMultiple), PullbackDepthFromRecentHigh
  (+maxRetracementFraction), TrendLineSlopeFlattening (+steepenSense), TrendLineBreak
  (+maxAnchorSpanBars), HigherSwingLow (+legs).
- 2026-09-22: 05 amended Momentum (+lag, minMoveAtr, atrLookback, searchBars; searchBars carries
  ImpulseLegNetMove; REVERTED 2026-09-27, now the new rule MomentumBeyondAtrMultiple, see end), RangeWidthBelowAtrMultiple (+consecutiveBars; EL twin now an explicit nested
  Extremes loop), CloseNearSessionExtreme (+strengthMode). Momentum's EL twin gained a hook and an
  ATR call evaluated by all 151 existing placements; deepest bar max(lag+searchBars+lookback,
  atrLookback+1), within every template's Max Bars Back. Spot-check both at the next MultiWalk.
- 02 amended EmaGapBar (+marginAtr, atrLookback; reaches back 0 -> atrLookback+1).
- 2026-09-22 B list: B03 wrote 8 (both former C rules OscillatorArtifactWindowBlock and
  AntiStochasticSlopeDisagreement authored; TimeDecayStopTightening not written per dec 23).
  Divergence pair authored with the high-side test on the LONG side (Brian may flip). Reviewer to
  check: rules/StochasticCross.json declares scratch at hook scope (double-placement hazard,
  pre-existing, not from this pass).
- 2026-09-22 B01 wrote all 10. TrendLegCountAboveMax authored mirrored (slice said same). Reviewer
  to check: EL `For` counts DOWN when end < start, so a `for kk = 0 to n-1` at n=0 reads Close[-1];
  B01 guarded its two loops in both twins; the pre-existing MicroTrendLineFailedBreakout and
  TrendLineBrokenRecently are unguarded (grids must start at 1; separate fix). Grid caps:
  UpLegsLongerThanDownLegs.numLegs <= 3, SwingLegExceedsAverageLeg.numLegs <= 2.

## 2026-09-27: two amendments reverted, re-authored as new rules (Brian)

Amending a rule that existing templates place changed the MultiWalk code of every family that
places it, even with an inert default: the next validation batch would have compiled code that
differed from what the engine families ran. So the two Grimes amendments on placed rules were
undone and their behaviour kept as NEW rules, both twins, code otherwise unchanged:

- `Momentum` (151 placements) is back to `close > close[lookback]`. Its four new inputs
  (`lag`, `searchBars`, `minMoveAtr`, `atrLookback`) now live in **`MomentumBeyondAtrMultiple`**,
  which carries all three keys: MomentumBeyondAtrMultiple (G02-06), PriorLegDirection (G02-01)
  and ImpulseLegNetMove (G03-15). Defaults are Grimes's reading, `lookback(3)`, `minMoveAtr(2)`,
  `atrLookback(14)`, `lag(0)`, `searchBars(0)`; at `minMoveAtr 0` it is `Momentum` term for term.
- `AtrAboveAverage` is back to `atr > average(atr, lookback)`. The `atrMultiple` input now lives
  in **`AtrAboveAverageMultiple`** (G05-22), default `atrMultiple(1.5)`.

The other 18 Grimes amendments stand. `NumBarsIfLosing` (+`profitThreshold`) is the only one
of them any template places (29 templates, 202608 BAS-15..43, not yet run); the rest are
placed nowhere. Rows: `rows/04_pullbacks.md` and `rows/05_ranges.md` (moved to the new-rule
tables); `rules/CATALOG.md` has both originals and both new rules. Both new rules pass
`validateRule`, `lintElFeatures.py` and `compileCheck.py --double`. Neither is in any template
yet: both still need templates and a test run.

## 2026-11-06: two collisions with the pulled 202611 studies

The pull brought the Brooks study (BRK-01..50) and the own-rules study (OWN-01..64). Both place
rules that the uncommitted Grimes pass had also touched:

- `RangeWidthBelowAtrMultiple`: upstream gave it a `lag(0)` input (own-rules ON-30-a; OWN-28
  sets it), and BRK-04/13/23/31/40/42/43 and OWN-28 place it. Under the 2026-09-27 rule it
  stays exactly as upstream has it. Its Grimes `consecutiveBars` amendment is now the new rule
  **`TightRangeRunLength`** (G10-07, merge decision 10), both twins, code unchanged. Its default
  is `consecutiveBars(18)`, Grimes's reading, so that at its defaults it is not
  `RangeWidthBelowAtrMultiple`. The TS twin of `RangeWidthBelowAtrMultiple` is back to HEAD;
  upstream's `lag` EL twin had not been pushed to StrategyGeneratorTS at the time.
- `DailyLossLimit`: upstream authored its own (`LossLimit(1000)`), placed in 17 BRK and OWN
  templates. The Grimes version (`dailyLossLimit(1000)`, merge decision 16) is the same rule
  except the first evaluated bar (a remembered day number vs `date <> date[1]`) and the exact
  tie (`<` vs `>=`), so it was dropped as a duplicate and upstream's kept in both repos.

`TightRangeRunLength` passes `validateRule` and `lintElFeatures.py`. `compileCheck.py --double`
could not run, because the engine build itself fails (C1060, compiler out of heap space in
`registry.cpp`, with or without the check batch). It is in no template yet.

## 2026-11-07: nine more amendments on placed rules split out (Brian)

The pulled 202611 BRK and OWN templates (and 202608 BAS-15..43, for `NumBarsIfLosing`) place
nine rules the Grimes pass had given new inputs. Generating those families from this working
tree would have compiled code the committed headers do not contain, so under the 2026-09-27
rule every one is now a NEW rule, both twins, with the amended code unchanged, and each original
is back as HEAD has it. Each new rule's defaults are its key's reading, so that at its defaults
it is not the original:

| Original (placements) | New rule | Keys | Defaults that differ from the off values |
|---|---|---|---|
| `ExitOnOppositeStrongTrendBar` (BRK 3, OWN 4) | `ScratchExitOnEarlyOppositeStrongBar` | G06-20 | `scratchWindow(3)` |
| `HigherSwingLow` (BRK 11, OWN 1) | `HigherSwingLowRun` | G06-43, `RisingSwingLowCount` G05-07 | `legs(3)` |
| `InitialStopBeyondSwingAtEntry` (BRK 7, OWN 9) | `InitialStopBeyondSwingAtRank` | G08-02 | `pivotIndex(2)`, `stopLookback(20)` |
| `NumBarsIfLosing` (BAS 29, BRK 4, OWN 4) | `NumBarsIfBelowProfitThreshold` | G08-19, G10-04 | `profitThreshold(100)`, comparison still strict |
| `StopBeyondExtremeSinceEntry` (BRK 7, OWN 9) | `StopBeyondExtremeSinceBaseStart` | G06-48 | `preEntryBars(10)` |
| `StopBeyondRecentRangeExtreme` (BRK 8, OWN 9) | `StopBeyondRangeExtremeAtrBuffer` | G06-17/25, G08-03; `StopAfterConsecutiveClosesBeyondLevel` G06-49 | `bufferAtrMultiple(0.25)`, `stopBuffer(0)` |
| `SwingPointTrailingStop` (BRK 3, OWN 4) | `SwingTrailCappedAtMaxRisk` | G08-21; `SwingPointTrailingStopAtRank` G08-09 | `maxRiskAtr(2)` |
| `TrailArmedAfterProfitThreshold` (BRK 4, OWN 4) | `PriorBarAtrTrailingStop` | G08-16 | `stopOffsetAtr(1.5)`, `stopOffsetTicks(0)`, `armProfitDollars(0)` |
| `TrendLineBreak` (BRK 1) | `MicroTrendLineBreak` | G16-10, merge decision 17 | `swingStrength(1)`, `maxAnchorSpanBars(5)` |

- This settles `NumBarsIfLosing`, the one amendment left open on 2026-09-27.
- `StopInsideTestedSwingExtreme` (merge decision 25, signed `stopTicks`) never needed code: it is
  a grid below zero on `InitialStopBeyondSwingAtEntry` or `InitialStopBeyondSwingAtRank`.
- Where the amendment rewrote a scan (`HigherSwingLowRun`, `InitialStopBeyondSwingAtRank`,
  `SwingTrailCappedAtMaxRisk`, `StopBeyondRangeExtremeAtrBuffer`), the new rule at the off values
  matches the original's behaviour, not its text.
- Comment-only cross-references were repointed in six unplaced rules (`AscendingTriangleIntoLevel`,
  `FlatTradeScratchExit`, `StalledPositionExit`, `SwingTrendHigherHighsAndLows`,
  `TrendLegCountAboveMax`, `LevelBreakAndRecover`), and in their catalog rows.
- Rows: the amended rows left `## Amended` in `rows/03_exits.md` and `rows/04_pullbacks.md` and
  became the new rules' rows; `rows/05_ranges.md`'s `RangeWidthBelowAtrMultiple` row was moved
  the same way, so `applyRows.py` cannot re-amend the catalog.
- Checks: `validateRule` ([], []) for all nine, `lintElFeatures.py` 618 rules with 0 blocking and
  0 warnings, and each twin's code (comments stripped) identical to the amendment it came from.
  `compileCheck.py --double` could not run while the engine build fails.
- EL `For` guards (Brian, same day): the copied EL twins carried `For` loops that count down
  where the C++ loop runs zero times, which the originals (calling `SwingLow` or `Lowest`) never
  had. At `confirmBars` 0 (`StopBeyondRangeExtremeAtrBuffer`), or a pivot window no larger than
  the strength, or strength 0 (`HigherSwingLowRun`, `InitialStopBeyondSwingAtRank`,
  `SwingTrailCappedAtMaxRisk`), EL read a future bar; at `preEntryBars` 0
  (`StopBeyondExtremeSinceBaseStart`) it folded `Low[1]` into the seed; at `rangeLookback` 1 it
  folded in one bar too many. Every such loop in those five TS twins is now wrapped in the
  2026-09-23 / `TrendLegCountAboveMax` form, `if <bound> then begin ... end;`, skipping it exactly
  when the C++ loop would not run, so the twins agree at every setting. EL twins only; lint clean.

The Grimes amendments still standing (`ChannelLineBreakTrendBarClose`, `CloseNearSessionExtreme`,
`EmaGapBar`, `LevelTouchCount`, `OppositeBodyCountInWindow`, `PullbackDepthFromRecentHigh`,
`ShavedTopBar`, `TrendLineSlopeFlattening`) are placed by no template.
