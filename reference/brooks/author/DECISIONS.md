# Orchestrator decisions during A-list authoring (2026-09-13)

- AverageBarOverlapWindow (slice 01) dropped: same windowed-mean overlap statistic as
  AverageBarOverlap (slice 12) with the comparison reversed; negation is a per-placement
  toggle. AverageBarOverlap is authored.
- Tick-unit parameters: authored as price-point inputs (defaults = book tick counts at
  0.25 pt/tick) until MinMove/PriceScale get a register row; rows say so.
- OutsideBar has no key of its own after the merge; slice 01 inlined it as the inclusive
  mirror of InsideBarInclusive. Candidate for a small atomic rule later.
- Cross-slice overlaps flagged by agents, to review after all slices land:
  StopAtSignalBarRangeMultiple (09) vs EntryBarRangeStop (13);
  PullbackReachesEntryPrice (09) vs EntryPriceRetest / BreakevenRetestExit (06).
- NarrowRangeWidth (06) not authored: same width-over-ATR arithmetic as RangeWidthBelowAtrMultiple
  (11), one bar back; slice 11 owns the measure. HorizontalFlagWidthTest (14) likely the same; the
  slice-14 agent is told to treat it as a duplicate unless it differs in more than the window end.
- EntryPriceRetest (06) not authored: its first conjunct is PullbackReachesEntryPrice (09) and the
  "holds" term is separable; panes AND entries.
- Probes written (engine repo): EL_Swing_Probe.txt, EL_TickSize_Probe.txt, EL_TLValue_Probe.txt,
  EL_XAverage_Probe.txt; register rows swinghigh/swinglow/swinghighbar/swinglowbar/tlvalue/
  xaverage/wfsafe_xaverage/minmove/pricescale added as UNKNOWN. Brian runs them in TradeStation.
- Engine work implied, not EL: (1) tick size never reaches strategies (only BigPointValue does;
  SymbolSpec::tick_size is ingest-only), so the 49 tick-unit rules need a ctx.TickSize() or
  MinMove/PriceScale accessor after the probe says whether it can change mid-run; (2)
  MinPositionProfit is not an EL word anywhere (checked 8,600 lines of MW EL); it is a
  ctx.MinPositionProfit() request with MaxPositionProfit's per-position reset semantics.
- MicroChannelSameColorLowOverlap (12) dropped: composition of the existing ConsecutiveUpBars
  and ConsecutiveBarsLittleOverlap (07); panes AND entries.
- Post-pass dedup review list (rules authored in parallel that may be parameterizations of
  each other): NoOppositeBarInLastN (11) vs OppositeBodyCountInWindow (12) at maxOpposite 0 vs
  OppositeCloseCountBelowThreshold (14); PullbackFromRecentHigh (12) vs BounceFromLowByAtr (11)
  vs DistanceAboveRecentLow (13); MicroChannelRunLength (12) vs HigherLowCount (13).
- Slice 11 held back five keys as duplicates of sibling-slice keys, which the sibling authors:
  BounceFromLowByAtr -> DistanceAboveRecentLow (13); RangeExtremeFade -> CloseInRangePosition (02);
  ConsecutiveTrendBarRun -> ConsecutiveTrendBars (04); StrongTrendBarCount -> TrendBarCountInWindow
  (05) / StrongBodyBarCountInWindow (04), one of which must win; NoOppositeBarInLastN ->
  OppositeBodyCountInWindow (12, already on disk).
- TightRangeBlocksEntries kept as a Switch even though strategyWriter makes every Switch force
  flat; the block-only reading is RangeWidthBelowAtrMultiple placed negated at 15 / 1.2 / 20.
- HorizontalFlagWidthTest (14) is to be dropped as a duplicate of RangeWidthBelowAtrMultiple (11).
- BounceFromLowByAtr (11) == DistanceAboveRecentLow (13): resolved, slice 13 authored
  DistanceAboveRecentLow after a nudge; no orphan remains from this pair.
- EntryBarRangeStop (13) dropped: StopAtSignalBarRangeMultiple (09) one bar index earlier.
- BullReversalBarShape (02) dropped: term for term StrongTrendBar (07), same inputs and defaults.
- More review-list pairs: ThinAreaLowBarOverlap (02) vs ConsecutiveBarsLittleOverlap (07);
  AverageUpperTailFraction (02) vs AverageTailFractionBelow (04); BullReversalBarWithTail (02) vs
  ReversalBarTailFraction (03); BarRangeBelowAverageMultiple (02) vs SmallWeakSignalBarBlock (03).
- BarOpensAbovePriorClose (07) dropped: identical to BodyGapBar (08).
- BodyAboveAverageBody (07) folded into BodyAboveAverageMultiple (04): slice 04 told to carry both
  consecutiveBars and bodyMultiple inputs so one rule covers both statements.
- BodyGapBar (08) == BarOpensAbovePriorClose (07): both deferred, neither written; slice 05 is
  told to author BodyGapBar (open[0] > close[1], mirrored, no inputs) from the merged entry in
  reference/brooks/merged/breakouts_volume_gap.json.
- Slice 14 drops: HorizontalFlagWidthTest (dup of RangeWidthBelowAtrMultiple),
  OppositeCloseCountBelowThreshold (dup of OppositeBodyCountInWindow), CloseAboveHighestClose
  (dup of catalog Breakout at lookback N+1).
- Review-list additions: VolumeBelowAverageFraction (14) generalizes catalog VolumeBelowAverage
  (candidate to fold into the existing rule with a fraction input, Brian's call);
  DeepPullbackRetracementFilter (14) vs CloseInRangePosition (02).
- Slice 03 drops: ReversalBarLowOverlap (BarOverlapFraction negated);
  SignalBarBodyMatchesTradeDirection (StrongTrendBar at bodyFraction 0, tailFraction 1, with lag).
  Slice 07's rows cite SignalBarBodyMatchesTradeDirection as a peer; dedup review fixes the wording.
- Slice 04 drops: BarRangeAboveAtrMultiple (dup of BarRangeAtrMultiple, 08; widen its grid);
  ConsecutiveTrendBars and slice 11's ConsecutiveTrendBarRun (both dup of StrongTrendBarRun, 08).
  AverageUpperTailFraction (02) and AverageTailFractionBelow (04) confirmed distinct.
- Slice 05: TrendBarBody dropped (StrongTrendBar at tailFraction >= 1 - bodyFraction, with lag);
  MicroGapAroundTrendBar dropped (MicroMeasuringGap); TrendBarCountInWindow written then deleted
  in favour of StrongBodyBarCountInWindow (04), which also settles slice 11's StrongTrendBarCount.
  Grid note for StrongBodyBarCountInWindow: carry windowBars 10 / minCount 6 as a design point.
- Review-list addition: OpenNearHighCloseNearLow (03) = OpenNearBarLow (05) AND catalog
  CloseRangePosition; a composition, candidate for removal.

## Post-pass dedup review (2026-09-13)

Every flagged pair reopened on the BE JSON, not the descriptions. Verdicts:

- REMOVED `HigherLowBar` (13): `HigherLowCount` (13) at `lookback = 1`, `minCount = 1` is
  it term for term, same strict comparison on both sides; the count form is more general and
  has more sources (3 vs 2). Both twins deleted, catalog row removed, the degenerate setting
  recorded in `HigherLowCount`'s row.
- REMOVED `OpenNearHighCloseNearLow` (03): exactly `OpenNearBarLow` (05) at
  `nearFraction = 1 - nearExtreme` ANDed with the catalog's `CloseRangePosition` at
  `threshold = nearExtreme`; entry panes AND, and as two placements the halves can be
  parameterized apart. Both twins deleted, catalog row removed, relation recorded in
  `OpenNearBarLow`'s row.
- REMOVED `VolumeBelowAverageFraction` (14): the catalog's `VolumeBelowAverage` at a fraction,
  same average, same window construction. Folded instead of dropped: `volumeFraction` added to
  both `VolumeBelowAverage` twins with default `1`, which reproduces the existing rule exactly
  (missing template params pin to the rule default, so the two templates that place it are
  unchanged). The removed rule's `0.8` / 20-bar defaults are carried in the row's Inputs prose
  as the quiet-market design point. Re-validated and re-linted.
- DISTINCT, wording corrected: `ThinAreaLowBarOverlap` (02) vs `ConsecutiveBarsLittleOverlap`
  (07) - identical at-most-F all-pairs test, but the divisor is the EARLIER bar's range vs the
  SMALLER of the two, so they disagree on every pair whose newer bar is the smaller; neither is
  the other at any input. `OverlappingBarRun` (11) is the same earlier-bar divisor with an
  at-LEAST test, which is not either of them negated (negating an all-pairs conjunction gives
  "some pair", not "every pair"). Both rows now say so; the dropped
  `MicroChannelSameColorLowOverlap` name is out of the catalog.
- DISTINCT: `DeepPullbackRetracementFilter` (14) vs `CloseInRangePosition` (02). It IS that rule
  flipped at `bottomFraction = 1 - retracementThreshold`, but its window ENDS ONE BAR AGO where
  `CloseInRangePosition`'s is current-inclusive, so on a bar making a new extreme the two read
  different ranges and no placement toggle bridges them. Both rows now state the relation.
- DISTINCT: `PullbackReachesEntryPrice` (09, Entry) vs `BreakevenRetestExit` (06, Exit) -
  identical condition text, different role, the `ConsecutiveCloseExit` / `MomentumConsecutiveBars`
  precedent; `BreakevenStop` (09) arms on `MaxPositionProfit` and triggers on the CLOSE.
  `BreakevenRetestExit`'s row now says the Entry/Exit pairing is deliberate.
- DISTINCT, already recorded: `BullReversalBarWithTail` (02) vs `ReversalBarTailFraction` (03)
  (body colour + close position vs a BANDED tail plus an opposite-tail cap);
  `BarRangeBelowAverageMultiple` (02) vs `SmallWeakSignalBarBlock` (03) (a bare range cap vs a
  NEGATED conjunction, i.e. an OR no negate toggle reaches); `AverageUpperTailFraction` (02) vs
  `AverageTailFractionBelow` (04) (one mirrored tail vs both tails, direction-agnostic);
  `SmallTailsBar` (03) vs `StrongTrendBar` (08) (no body-colour term, unreachable from it);
  `PullbackFromRecentHigh` (12) vs `DistanceAboveRecentLow` (13) (the bar's own extreme measured
  from the opposite N-bar extreme vs the CLOSE measured from the same-side one);
  `MicroChannelRunLength` (12) vs `HigherLowCount` (13) (all-of-N inclusive vs K-of-N strict);
  `RangeWidthBelowAtrMultiple` (11) vs `TightRangeBlocksEntries` (11) (Entry filter vs Switch,
  which forces flat); `OverlappingBarRun` (11) vs `BarOverlapFraction` (the run form beside the
  single-pair form, the `MomentumConsecutiveBars` / `MomentumChange` precedent);
  `LargeTrendBarCountInWindow` (05) vs `ConsecutiveClimaxBarCount` (13) (the separation term).
- Catalog rows citing keys that were dropped or never assigned to a slice now say so in the row:
  `SignalBarBodyMatchesTradeDirection` (NonOppositeClose - rewritten as `StrongTrendBar` at
  `lag = 0`, and the same fix applied to `rows/07_breakouts.md`), `BarRangeAboveAtrMultiple`
  (corrected to `BarRangeAtrMultiple`), `BullReversalBarShape` (to `StrongTrendBar`),
  `TrendBarBody` (to `StrongTrendBar`), `MicroChannelSameColorLowOverlap`, `RangeExtremeFade`,
  `BarOpensAbovePriorClose`, `BodyAboveAverageBody`, `StrongTrendBarCount`, `TrendingCloseRun`,
  `PullbackBar`, `BreakoutPullbackLimitEntry`.
- GAP, not a dedup: `StopBeyondSignalBar` is an A-list `exits_stops` key that no slice was ever
  given, yet `StopFractionOfSignalBarRisk` and `WiderStopForSmallSignalBarCapped` both define
  themselves against it. Their rows now say it is not on disk. It still wants authoring.
- 2026-09-13 post-probe slice 15: 7 rules written (5 EMA current-value reads, SwingHigh primitive,
  BreakoutLevelRetest). 9 XAverage rules blocked on lagged reads until the follow-up run.
  Superseded merged assumptions: pivot newer-side test is strict; BreakoutLevelRetest anchors on a
  confirmed pivot. CloseCrossesEma left for Brian: EL `crosses above` (state machine) would
  unblock it today but changes the merged two-bar spec. emaLength must stay pinned in grids.
- B pass (2026-09-13): PostClimaxCorrectionBlock (B06) dropped: ConsecutiveClimaxBarCount negated at
  fixed inputs. HighThreeEntry (B03) = HighLowBarCount at countTarget 3; B03 told to drop it.
- B01: PriceInLowerHalfOfChannel dropped (EntryRoomToChannelLine with fraction = 1 - minRoomFraction).
  StairsPattern and ShrinkingStairs blocked: need SwingHigh/SwingLow Occurrence 3-4, unmeasured
  (probe extension: print occurrences 1-4). Channel construction settled by B01 and binding on
  B02: trend line through the two most recent confirmed swing lows, channel line through the two
  most recent swing highs (bear mirrored), NON-parallel; pivotLookback(20) added everywhere.
- B03: HighThreeEntry dropped (HighLowBarCount at countTarget 3). Three-pivot scans are hand-written
  (swing Occurrence 3+ unmeasured); always-in inlined with consecutiveBars/bodyFraction/tailFraction
  inputs, to be pinned in grids.
- B04: BreakoutFailedBackIntoRange dropped (FailedBreakoutReversal side-flipped);
  OverlappingLargeBarCluster dropped as a composition of AverageBarOverlap (negated) and the
  existing LargeBarCountInWindow. SessionBarBreakout (B04) vs SessionFirstBarBreakout (B05): B05
  told to check.
- B02: dropped ChannelHeightEqualsSpikeHeightTarget (PatternHeightMeasuredMoveTarget at 1),
  ChannelStartRetestExit (SwingPivotTarget at pivotIndex 2), ThreePushesInChannel (ThreePushPattern
  shapeMode 0), TrendChannelLineOvershoot (TrendLineTouch at negative touchTolAtr). B09's
  TrendChannelLineTarget and B10's CountertrendNeedsPriorTrendLineBreak are covered by
  ChannelLineTargetExit / TrendLineBrokenRecently and are not to be authored.
- Corpus-wide decision (orchestrator): the third-and-later pivot may be found by an INLINED scan
  written in both twins (B03's route: plain EL loops and comparisons, all VERIFIED words), since
  only the SwingHigh/SwingLow FUNCTION's Occurrence 3+ is unmeasured. Unblocks
  TrendLineSlopeFlattening (B02), StairsPattern and ShrinkingStairs (B01); authored in a final
  orphan slice.
- B07: 12 written, none dropped. AverageDailyRange family is a bar scan with maxScanBars(500)
  (HighD(k) has no engine counterpart). MaxTradesPerSession Switch carries MarketPosition = 0 so
  it blocks without liquidating.
- Final review must scan every new rule's hooks for hook-scope C++ declarations (e.g. B04's
  SessionBarBreakout `const int sessOffset`) that collide when a rule is placed twice, the
  AdxBelowThreshold class of bug; move such scratch into localVariables.
- B05: SessionFirstBarBreakout not authored; final review adds windowBars(1) to SessionBarBreakout
  (B04) so it covers the window form. LargeOpeningRangeBreakoutFilter dropped
  (OpeningRangeVsAvgDailyRange at lowFraction 0, negated). QuietPeriodBreakoutNeedsPullback split:
  quiet half authored as QuietBarCountInWindow, size half is BarRangeAtrMultiple.
- B08: FirstBarOfSessionTrendBar dropped (IsFirstBarOfSession AND StrongTrendBarRun(1, 0.7)).
  Supersets kept with a note: ConsecutiveStrongTrendBars over StrongTrendBarRun,
  TrendBarRunWithinWindow over StrongTrendBarRun.
- B09: StopAtInitialRiskMultiple and ProfitTargetAtInitialRiskMultiple blocked on the missing
  initial-risk accessor (engine request). PriorSwingExtremeTarget not authored; final review adds
  toleranceAtr(0) to SwingPivotTarget. BarsSinceEntry() == 0 accepted as the per-position reset for
  hand-kept state (it is the VERIFIED accessor that restarts through a reversal); BreakevenExit-
  AfterAdverseExcursion therefore measures bar-close MAE, noted in its row. Hook-scope const
  declarations reported in SwingHigh, ChannelLineTargetExit, EmaGapBar -> final review fixes.
- Double-placement sweep (compileCheck.py --double): 31 of 92 checked B rules fail with C2374
  redefinitions from hook-scope consts (pivS/pivW/foundLo/foundHi in channel and trend-line rules,
  pivStrength/pivWindow in three-push rules, emaSf, sessOffset). Final fix agent moves every
  hook-scope declaration into localVariables across ALL new rules (A and B), then re-runs
  --double over the whole new set until clean.
- INCIDENT: the harness agent killed a running bt_walkforward.exe (a live runBatch computation,
  spec s_202608_bas_1_v9) to free a build lock. Brian to check that family's state and re-run
  the interrupted version; runBatch skips cached versions so only the lost one recomputes.
- B11: ClimaxBarAfterExtendedRun dropped (ClimaxBar AND TrendDurationBars). NearAnyLevel carries
  three magnets; the round-number magnet is blocked on a rounding word (Round/IntPortion/Floor
  have no register row, Mod is UNKNOWN).
- B10: RecentStrongTrendDaysCount dropped (StrongBodyBarCountInWindow on daily bars).
  DeepPullbackMeansRange not authored; final review adds pullbackLookback(1) to
  PullbackDepthFromRecentHigh. Note: the engine link step fails with LNK1104 while Brian's
  walkforward holds bt_walkforward.exe; compile diagnostics (C2374 etc.) still surface, so the
  double-placement sweep judges by compiler errors, never by killing the process.

## Final review of the A + B passes (2026-09-13)

- Double-placement repair: 43 of the 293 rules added since 78da94e declared C++ scratch at
  hook scope. Every such declaration was promoted to `localVariables` and the declaration
  turned into a plain assignment, exactly as f65c5e4 did for AdxBelowThreshold; each hook
  carries a four-line note saying why. The scratch was `pivS`/`pivW`/`foundLo`/`foundHi` in
  the eleven channel and trend-line rules, `pivStrength`/`pivWindow` (plus `mode`, `perBarMode`,
  `loBound`/`hiBound`, `failWindow`) in the three-push and swing rules, `emaSf` in the six EMA
  rules, `sessOffset` in SessionBarBreakout and `histLen` in AtrAtExtreme. No name collided
  with an existing local or input and none was shadowed in a nested block, so behaviour is
  unchanged: every one is fully assigned each bar before it is read. `compileCheck.py --double
  --since 78da94e` went from 31+ rules failing (the first pass stopped at MSVC's 100-error cap,
  alphabetically at FirstTrendLineBreakOfSession) to "No compiler errors or warnings attributed
  to checked rules". The build still exits 1 on LNK1104 while Brian's walkforward holds
  bt_walkforward.exe; that is the environment, not a rule.
- Three input additions the log assigned to this review, both twins each, behaviour unchanged
  at the new default:
  * `SessionBarBreakout` gains `windowBars(1)` -- the session's first bar is now accepted at any
    offset from `offsetBars` to `offsetBars + windowBars - 1`, which is B05's SessionFirstBarBreakout
    window form. At most one offset in a window can be a session start, so the scan finds at most
    one level. Reaches back becomes `offsetBars + windowBars`.
  * `SwingPivotTarget` gains `toleranceAtr(0)` and, with it, `atrLength(14)` -- the tolerance is
    meaningless without an ATR, and ChannelLineTargetExit's `touchTolAtr`/`atrLength` pair is the
    precedent. WFSafe_AvgTrueRange rolling accumulator on the C++ side, the built-in on the EL side.
    Reaches back becomes `max(lookbackBars - 1 + swingStrength, atrLength + 1)`.
  * `PullbackDepthFromRecentHigh` gains `pullbackLookback(1)` -- depth measured from the lowest low
    (long) / highest high (short) of the last N bars instead of this bar alone. `Lowest(Low, 1)` is
    `Low`, so the default reproduces the rule exactly. Reaches back becomes
    `max(lookback, pullbackLookback) - 1`.
- Dedup review of the B pass. NO rule deleted; every flagged pair is distinct, and the rows now
  say why:
  * `ConsecutiveStrongTrendBars` vs `StrongTrendBarRun` -- KEPT BOTH. StrongTrendBarRun is this
    rule at `tailFraction = 1` exactly (a tail cannot exceed the bar's own range, so both tail
    tests go vacuous), but the base rule stands beside its generalization on the
    MomentumChange / MomentumConsecutiveBars precedent this log already cites twice, and it is
    the corpus's settled spike definition -- sixteen catalog rows cite it, a dozen rules inline
    it, and three rules were dropped in its favour. Row wording corrected from `>= 1` to `= 1`.
  * `TrendBarRunWithinWindow` vs `StrongTrendBarRun` -- KEPT BOTH, same precedent. The two
    supersets generalize the base in DIFFERENT directions (tails vs window position) and neither
    reaches the other, so StrongTrendBarRun is their shared floor and cannot be folded into
    either.
  * The day-type reads -- DISTINCT, wording added. `SessionTrendDayDirection` is re-evaluated
    every bar where `MorningLegDirection` latches once and holds (already in the rows);
    `TradingRangeDay` and `TrendResumptionDayContext` share only the AverageDailyRange divisor --
    whole-session travel and direction-agnostic vs the midday window from the leg bar on and
    directional -- and neither row said so, so both now cross-reference the other.
  * `ConsecutiveClimaxBars` vs `ConsecutiveClimaxBarCount` -- DISTINCT, confirmed. No setting of
    the count rule requires the CURRENT bar to be a climax, and the separation tests differ
    (non-climax bar there, non-trend bar here).
- Consistency sweep: 382 rules on disk, 382 catalog rows, 382 TS twins, no orphan either way.
  26 TS twins were missing the `type` field entirely and so defaulted to Entry -- two of them,
  `ExitOnConsecutiveClimax` and `WeakEntryBarExit`, are Exits, which was a live bug in the EL
  twin. All 26 now carry the BE type explicitly. `HigherLowStreak` in
  NoQualifyingPullbackSinceLegStart's row is a mined candidate that was never authored; the rule
  it meant is `MicroChannelRunLength`, and the row was corrected. `TrendChannelLineTarget`,
  `SessionFirstBarBreakout`, `PriorSwingExtremeTarget` and `DeepPullbackMeansRange` are now
  annotated in their rows as not on disk. Remaining twin difference, left alone: ProfitProtector,
  ProfitProtectorRatio and TieredProfitProtector spell fractional defaults `.5` in EL and `0.5`
  in C++ -- numerically identical, pre-dates this batch, and changing it would move committed
  EL text for no behavioural gain.
