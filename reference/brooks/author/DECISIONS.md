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
