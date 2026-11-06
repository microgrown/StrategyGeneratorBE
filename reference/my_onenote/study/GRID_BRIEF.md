# Grid and role brief for the own-rules study templates

Brief for the grid agents, 2026-11-06. The own-rules arm repeats the platinum test
(36-month held-out OOS) with Brian's own rules, in the same shape as the Brooks study
(`reference/brooks/study/SELECTION.md`, which you should skim for the conventions it
settled: §"Pane structure and version arithmetic", §"Trial runs", §"Brian's decisions").
Read `.claude/skills/design-grid/SKILL.md` fully first. It is the procedure.

## Template shape (settled with Brian)

- **Pane-1 families** (one per own pane-1 entry; 50 of them):
  - pane 1 = setup | reverse (the reverse is every setup placement with `flipped` toggled);
  - pane 2 = empty | own trend condition | own regime condition | classic filter, all pinned;
  - panes 3-5 = drawn stops, exits and switches, as in the Brooks study.
- **Pane-2 families** (one per own pane-2 condition; 14 of them):
  - pane 1 = two classic entries, each with its reverse, all pinned;
  - pane 2 = condition | condition flipped (for mirrored conditions), or condition | condition negated (for same-sided ones). There is no empty group.

## Budget (per version; worst version counts)

- Setup (pane-1 family): **at most 2 optimized inputs and at most 25 iterations**.
- Condition in its own pane-2 family: **at most 2 optimized inputs and at most 25 iterations**.
- Pane-2 placements when the condition is drawn into a pane-1 family: **every input pinned**.
- One pane-4 exit adds at most 4 values, so the worst version is at most 25 x 4 = 100.

## Data conventions

- WF 2007-01-01 -> 2019-04-01, incubation -> 2020-01-01, OOS -> 2023-01-01.
- 43 futures, timeframes 30-1440 minutes, every family on every timeframe.
- M1440 has about 3,270 bars to 2020.
- Max Bars Back is 250 by default.
  - Anything whose reach (CATALOG "Reaches back", with inputs at their grid STOP values) exceeds 250 needs 500. Say so.
  - The P1 level-visit rules (`Level*`) and `EmaTouchAfterLongAbsence` already need 500.
  - Never exceed 500.
- Shift test: no price levels, no point or tick inputs that cannot carry across 43 symbols.
  - Pin any point or tick tolerance at 0, or at a value that is clearly harmless, and say so.
- `NewWindowLowAboveLongerLow`: `longFactor` must stay on whole numbers.

## Trade-count evidence

Brian accepts low daily trade counts, so do not distort an idea just to reach 30 M1440
trades. Do centre grids where the rule fires at a reasonable rate, though, and lean the
range toward the looser side when the defaults are rare.

A smoke test (2026-11-05) ran every rule at its DEFAULT inputs, alone in pane 1, as pure
stop-and-reverse, on **ES M60, 2012-01-01..2019-12-31 (47,108 bars)**. Trade counts:

```
0 BreakawayPullbackBreak | 0 RsiBandBreakThenOppositeBar | 6 ConsolidationBreakoutFirstRetest
6 UndercutOfLowerSwingBelowLevelPair | 7 InnerBoxFalseBreakReclaim | 8 DoubleSwingLevelBreakRetestFail
9 ChannelInnerSwingBreakFade | 14 SupportBreakResistanceThenReclaim | 15 ConsolidationBreakoutBarHighClose
20 SwingHighClusterDecisiveBreak | 23 LargeBarInsideRunCloseBeyond | 29 BreakoutCandleClassSequence
38 LevelPairPivotBreakout | 43 HugeBarOppositeInsideBarThenResume | 44 LargeBarTightPauseNearHigh
69 MaDistanceRegime | 72 LargeBarHoldThenCloseThroughMidpoint | 74 RedRunThroughStackedSupportFade
80 SwingStructureTrend | 126 LargeBarAtExtremeNextBarExtendsWeakClose | 127 MaWickTouchesHoldSide
129 EmaTouchAfterLongAbsence | 148 ChannelFailedSwingFromHitSide | 149 FractalBoxBreakout
165 MomentumLadder | 189 EmaInvertedBarsAboveSlow | 189 LevelRejectedFromAbove
191 DonchianOutsizedBreakoutFade | 196 NewExtremeFrequency | 198 MaSideFlipRun
218 RsiTightBandExitBarColour | 236 FractalMovePullbackContraction | 274 LateFractalFade
281 BearBarTopHalfUntouchedLong | 286 MaStackGapNarrowing | 330 ConsolidationBreakoutBar
331 BreakoutDirectionShare | 370 NewWindowLowAboveLongerLow | 406 FastEmaAboveSlowEma
407 ConsecutiveUpsideBreakouts | 417 BreakoutClearsByHalfBar | 460 UpperBandTouchHigherHigh
484 UpperBandTouchBarBreak | 515 RsiDivergenceAtWindowExtreme | 528 FractalTrendlineBreak
618 LevelThinAir | 655 FractalOrderLowHighHigh | 756 SwingRegressionTrend
792 BandHighThenMidlineRetrace | 886 LevelForwardDrift | 977 FractalLegSlopeDecay
1005 ExtremePairRetraceEntry | 1042 SwingLowRejection | 1130 DoubleEmaTouchRun
1157 BodyMaBandBreakout | 2700 AdxFallingMomentumFade | 7303 LevelBodyDominated
12109 TrueRangeCoefficientOfVariation | 14204 RangeWidthBelowAtrMultiple | 16233 AvgBodyBelowRangeFraction
17223 RangeOutsidePriorRangeFraction | 21196 LevelWasTrending | 23270 LevelBigBars
26440 BollingerWidthBelowAverage | 27749 LevelHighVolume
```

These counts are stop-and-reverse round trips. Because the position reverses, the
count is roughly the number of side changes, not the number of signals. Very high
counts (thousands) mean the condition is a state that flips often, which is normal for
pane-2 conditions.

A per-bar rate scales to M1440 roughly as `count / 47108 * 3270`; for example, 189 gives
about 13 daily trades. This is crude, because pattern frequency per bar is not
timeframe-invariant. Use it only as an order of magnitude.

You may also look for prior-run evidence under `C:\Users\brian\source\repos\BacktestEngine\runs\`
(see the skill), but none of these rules has run before. **Do not run the engine, do not
build, do not write templates, never stop or kill a process.** The engine is running a
batch.

## Per rule, decide

Read the rule's `rules/<Name>.json` (inputs and code) and its `rules/CATALOG.md` row
(grep it; the file is about 420 KB). Then:

1. **Pane-1 entries:**
   - `setupType`, one of:
     - `with-trend`: continuation or pullback in the trend;
     - `breakout`;
     - `reversal`: fades or countertrend;
     - `range`: fades at the edges of a range or box.
   - The trend condition is oriented by this: as authored for with-trend and breakout, flipped for reversal and range.
   - `setupFlipped`: true only if the authored long side is really the fade of the thing the setup is named for, and the flipped placement should be "the setup". This is rare; the Brooks study had five. Usually false.
   - `cluster`: normally just the rule. Exceptions:
     - `DoubleEmaTouchRun` is direction-agnostic ("same"), so it cannot stand alone in pane 1. Its note (#39) pairs it with `FastEmaAboveSlowEma` flipped. Make the setup that two-placement cluster, and confirm the orientation from the catalog rows.
     - `ConsolidationBreakoutBar` depends on the consolidation zone, which is `RangeWidthBelowAtrMultiple` with `lag` 1 (slice 05 notes, `reference/my_onenote/author/slices/05_breakout_consolidation.json`). Check whether the rule inlines the zone. If it does not, the setup is the cluster [`ConsolidationBreakoutBar`, `RangeWidthBelowAtrMultiple`(lag 1, `rangeLookback` = the zone X, `atrLookback` = X)].
     - Check the other slice-05 rules the same way.
     - Any other rule whose catalog row says it needs a companion placement.
   - The grid for every input of every cluster placement.
   - `pane2Conflicts`: own or classic pane-2 conditions (ids below) that would contradict the setup or make it never fire. One example is `EmaInvertedBarsAboveSlow` (fast EMA below slow EMA) with `FastEmaAboveSlowEma`. Another is a condition that duplicates the setup's own test.
2. **Pane-2 conditions:**
   - `kind`:
     - `trend` for directional, mirrored conditions that confirm a trend in the long direction;
     - `reversal-context` for directional conditions whose long side describes a down move about to turn. `MaStackGapNarrowing`'s long side is like that; check it;
     - `regime` for same-sided volatility, structure or level conditions.
   - `familyGrid`: the grid used when it is the tested condition (at most 2 optimized inputs and at most 25 iterations).
   - `pinned`: the single value set used when it is drawn into a pane-1 family. Usually the familyGrid centre.
   - Note whether the pinned value passes on a sensible share of bars. A pane-2 filter that passes on 95% of bars, or on 1%, is useless; aim for roughly 20-70%.

## Ids of the pane-2 conditions (for `pane2Conflicts`)

- Own trend or reversal-context conditions:
  - `SwingRegressionTrend`
  - `SwingStructureTrend`
  - `FastEmaAboveSlowEma`
  - `MaStackGapNarrowing`
  - `MaWickTouchesHoldSide`
  - `NewExtremeFrequency`
- Own regime conditions:
  - `TrueRangeCoefficientOfVariation`
  - `BollingerWidthBelowAverage`
  - `RangeOutsidePriorRangeFraction`
  - `QuietBodiesBeforeBar` (= `AvgBodyBelowRangeFraction` with a lag)
  - `LevelBodyDominated`
  - `LevelWasTrending`
  - `LevelBigBars`
  - `LevelHighVolume`
- Classic filters:
  - `DaveyMomentum` (`Momentum` 50)
  - `CloseAboveSma` (`CloseAboveAverage` 100)
  - `AdxTrending` (`AdxBelowThreshold` negated, 14/25)
  - `AdxQuiet` (`AdxBelowThreshold` 14/20)
  - `AtrExpanding` (`AtrAboveAverage` 15/20)

## Output

Write `reference/my_onenote/study/grids/<your-part>.json` and validate it with `json.load`:

```json
{"part": "A", "setups": [
  {"rule": "Name", "setupType": "reversal", "setupFlipped": false,
   "cluster": [{"name": "Name", "flipped": false, "negated": false,
                "params": {"input": {"start": "5", "stop": "20", "step": "5"},
                           "pinnedInput": {"start": "14", "stop": "", "step": ""}}}],
   "iterations": 12, "optimizedInputs": 2, "reachAtStop": 40, "maxBarsBack": 250,
   "estM1440": "smoke 189 -> ~13 at default; looser corner ~25",
   "pane2Conflicts": ["FastEmaAboveSlowEma"], "rationale": "one or two lines"}],
 "conditions": [
  {"rule": "Name", "id": "Name", "kind": "trend", "sides": "mirrored",
   "familyGrid": {"input": {"start": "..", "stop": "..", "step": ".."}},
   "pinned": {"input": {"start": "..", "stop": "", "step": ""}},
   "iterations": 9, "reachAtStop": 60, "maxBarsBack": 250,
   "passRate": "estimate", "rationale": "..."}]}
```

The format rules:
- List EVERY input of every placement, with all values as strings.
- A pinned input is `{"start": X, "stop": "", "step": ""}`.
- `rowIterations` semantics: values = (stop - start) / step + 1. Make sure the steps divide exactly.

Report back in under 25 lines:
- Any rule you could not grid, and why.
- Every cluster you made.
- Every `setupFlipped: true`.
- Any `maxBarsBack` 500.
- Any setup whose most selective corner is plainly rare.
- Any question that needs Brian.

No JSON in the report.
