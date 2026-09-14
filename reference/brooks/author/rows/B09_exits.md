# CATALOG rows — slice B09_exits (swing/measured-move targets, armed and range-sized stops)

Thirteen keys in the slice; nine written, both twins each. Rows are in
`rules/CATALOG.md` table format, ready to append.

| Rule | Type | Sides | Reaches back | Inputs | Fires when |
|---|---|---|---|---|---|
| `BreakevenExitAfterAdverseExcursion` | Exit | mirrored | 0 | `adverseDollars(200)` | This position's open loss has at some point been worse than X dollars and the close has come back to the entry price (long: `Close >= EntryPrice`, short mirrored) — scratch a trade that went badly and crawled back. The running minimum is kept in a local because the engine has no `MinPositionProfit` accessor, and it is reset on `BarsSinceEntry = 0`, never on `MarketPosition = 0`: `BarsSinceEntry` is VERIFIED as 0 on the fill bar and as restarting through a reversal, which is the per-position boundary a flat test misses, and it is the same at-entry capture convention slices 09 and 10 use. One difference from a true accessor remains: `OpenPositionProfit` is marked at the last close, so this is the worst bar-close excursion, not the intrabar one. Not `BreakevenStop`, which arms on peak PROFIT — that arms after the trade has gone well, this one after it has gone badly, and the two arm on disjoint trades. The slice said sides `same`; the `EntryPrice` comparison is directional, so they are mirrored, the same correction slice 09 made to `BreakevenStop` |
| `BreakevenStopAfterEmaHoldingRun` | Exit | mirrored | 0 (the EMA is recursive state, not a window — its seed bar is part of the specification) | `emaLength(20)`, `barsAboveEma(4)` | The breakeven stop is armed structurally rather than on a dollar amount: once the close has held above the EMA for N consecutive bars SINCE ENTRY the flag is set, and a later close at or below the entry price takes the long off; short is the mirror below. Counter and flag are per position, reset on `BarsSinceEntry = 0` (VERIFIED: 0 on the fill bar, restarting through a reversal), and the fill bar itself counts as the first of the run. Not `BreakevenStop`, whose trigger is `MaxPositionProfit >= activationProfit`: a four-bar rally holding above the average and a $100 peak arm on completely different bars, and neither is a parameter setting of the other. The EMA is the `WFSafe_Xaverage` mirror carried by `EmaGapBar` — price seed on the first calculated bar, `x + sf*(p − x)` as ONE statement, `sf = 2/(emaLength+1)`, no warm-up hole. `emaLength` MUST BE PINNED in the grid: the wrapper's walkforward length-change behaviour is unmeasured. Only the current EMA value is read; no lagged read |
| `StopSizedToRecentRange` | Exit | same | `runLookback` | `runLookback(20)`, `runFraction(1)` | Open loss reaches F × the high−low SPAN of the `runLookback` bars ENDING ONE BAR AGO, converted with `BigPointValue` — risk about what the move being faded already made. Brooks measures the breakout's start-to-extreme leg; the N-bar span is the mechanizable stand-in, and the window ends one bar ago so the bar being judged cannot widen its own stop. Not `StopAtSignalBarRangeMultiple` (ONE bar's range), not `SessionAvgBarRangeStop` (the mean bar range so far today), not `AvgDailyRangeFractionStop` (an N-SESSION average daily range), not `AtrProfitTarget`/`AtrTrailingStop` (a rolling N-bar ATR, and a target and a trail). Direction-agnostic, so both sides are identical text, as `StopLoss` is; `BigPointValue` is the raw multiplier and is not currency-converted while `OpenPositionProfit` is |
| `NearMeasuredMoveTargetFilter` | Entry | mirrored | `max(refOffset + refBars − 1, atrLookback + 1)` | `refBars(20)`, `refOffset(10)`, `multiple(1)`, `nearTargetAtr(0.5)`, `atrLookback(14)` | Gate: the bar's high is within `nearTargetAtr` × ATR of the up measured-move target `patternHigh + multiple × (patternHigh − patternLow)`, where the pattern is the `refBars` bars ENDING `refOffset` BARS AGO; short is the mirror on the down target. `refOffset` is not in the merged parameter list and is what makes the rule able to fire at all — with the window ending one bar ago its own extreme tracks the market, so price could only be a measured move beyond it after a single bar spanning the whole pattern height. The tolerance is an ATR fraction (R08-14's own form) rather than T03-17's tick count, since the engine exposes no tick size, and the ATR is the `WFSafe_AvgTrueRange` rolling accumulator. Each side reads the target in ITS OWN direction, so placed plain on a with-trend long it is "take the breakout only into the target" and placed NEGATED it is T22-06's block on with-trend entries near the target; Brooks's countertrend fade AT a bull target is a short taken on the long side's level, which one side alone cannot express — that use needs both placements. `depends_on_keys: PatternHeightMeasuredMoveTarget`, inlined not referenced |
| `ExitOnMicroChannelBreakout` | Exit | mirrored | `minBars + 1` | `minBars(5)` | The micro channel that carried the trade ends: none of the `minBars` bar pairs ENDING AT BAR 1 made a lower low (inclusive containment, so an equal low keeps a bull micro channel alive) and this bar makes a strictly lower low, with a long open; short is the mirror on highs. `MicroChannelRunLength`'s bounded all-pairs test read one bar back, inlined. The condition text is `MicroChannelBreakoutBar`'s plus the position guard, in the Exit role — the pairing established by `ConsecutiveCloseExit` (= `MomentumConsecutiveBars` in the exit pane) and `AdverseBodyCountExit` (= `ConsecutiveUpBars` mirrored there), and an Entry rule cannot occupy the exit pane. Unlike `AdverseBodyCountExit` this one does read position state, because the side matters: the bull channel is what takes the long off. Same shape as `ExitOnFirstOppositeBodyAfterRun` but the run is counted on higher lows rather than bull bodies, so they fire on different bars. `depends_on_keys: MicroChannel` |
| `OpeningRangeMeasuredMoveTarget` | Exit | mirrored | 1 (plus the session state carried in locals) | `openingBars(12)`, `multiple(1)`, `tolerancePoints(0.25)` | Once the first `openingBars` bars of the session have fixed the opening range, a long is closed when the high reaches `orHigh + multiple × (orHigh − orLow) − tolerancePoints`; short mirrored below `orLow`. Brooks's "approximate doubling of the day's range". Not `PatternHeightMeasuredMoveTarget`, whose reference window is the `refBars` bars before the breakout and moves with it — this window is SESSION-ANCHORED and fixed for the whole day, so the two project off different bars. Session model per the standing decision, with `SessionOpeningRange`/`OpeningRangeBreakout` inlined rather than referenced: `date > date[1]`, mirrored as `day_of(ctx.Time(0)) > day_of(ctx.Time(1))`, running extremes and a bars-into-session counter in locals reset there, `barsIn` 1 on the session's first bar, target trusted only at `barsIn >= openingBars`. Warm-up mirrors EL: a mid-session first calculated bar leaves `orLow` at 0 until the first date change, so the short target is unreachable up to that point. `tolerancePoints` is price points, not ticks (one Emini tick). Intraday only |
| `SessionMidpointTarget` | Exit | mirrored | 1 (plus the session state carried in locals) | `midpointFraction(0.5)`, `minSessionBars(6)` | A countertrend long taken near the day's extreme is closed when the high reaches `priorLow + midpointFraction × (priorHigh − priorLow)`, the midpoint of the session's range SO FAR THROUGH THE PREVIOUS BAR; short is the mirror down from `priorHigh`. The one-bar lag is load-bearing: testing this bar's high against a midpoint this bar just widened would fire on every bar that makes a new session extreme, since a new extreme is above its own midpoint by construction — the same "ending one bar ago" convention `RangeMidpointTarget` uses on its fixed window. `minSessionBars` is the second guard: with two or three bars printed the session midpoint sits inside the current bar, and it also covers the session's first bar, where the prior extremes still hold yesterday's numbers. `midpointFraction` promotes Brooks's hard-coded half to an input, measured up from the low for a long and down from the high for a short so 0.5 is the midpoint on both. Not `RangeMidpointZone`/`RangeMidpointTarget` (a fixed N-bar window) and not `CloseNearSessionRangeMidpoint` (an Entry filter on the CLOSE inside a band). Session model per the standing decision. Intraday only |
| `PullbackSizedProfitTarget` | Exit | mirrored | `lookbackBars − 1 + swingStrength` | `swingStrength(2)`, `lookbackBars(40)`, `profitFraction(0.8)` | Take profit at a fraction of the market's own last pullback: at entry, capture the most recent confirmed swing high and swing low and freeze the level `swingLow + profitFraction × (swingHigh − swingLow)`; the long exits when the high reaches it, the short mirrored down from the swing high. Frozen on the fill bar (`BarsSinceEntry = 0`) so the target does not walk away as new pivots confirm, with both scans run unconditionally every bar so Max Bars Back covers them. The −1 sentinel is guarded by `havePb`, which also requires the swing high above the swing low. Pivot scan inlined per `SwingHigh`: at or above the `swingStrength` older bars, strictly above the `swingStrength` newer ones, lag exactly `swingStrength`, occurrence 1 only (occurrence 3+ is unmeasured). Not `SwingPivotTarget`, which exits AT the pivot and re-reads it every bar — at `profitFraction = 1` the level coincides with its `pivotIndex 1` on trades entered before a new pivot confirms, which is why the default is 0.8 — and not `PatternHeightMeasuredMoveTarget`, which spans a fixed window where this spans two confirmed pivots |
| `ShrinkingSwingIncrementsExit` | Exit | mirrored | `lookbackBars − 1 + swingStrength` | `swingStrength(2)`, `lookbackBars(40)`, `shrinkFraction(0.5)` | Three confirmed swing highs are rising and the newest gain is shrinking: `pivot1 > pivot2 > pivot3` and `pivot1 − pivot2 < shrinkFraction × (pivot2 − pivot3)`, so take profits on the long; short is the mirror on three swing lows. The second increment's sign is required as well as the first — the merged pseudocode states only `pivot1 > pivot2`, and without the other the right-hand side can go negative and the comparison stops meaning "shrinking". Brooks's worked numbers (eight ticks then three) put the fraction well under 0.5; 0.5 is the candidate's default. The scan is hand-rolled rather than a third-occurrence call because occurrence 3+ is UNMEASURED in the register, exactly as `SwingPivotTarget` does it, with no early break and the counters capping the pivots kept at three. Usable as a negative entry filter through the per-placement negate toggle, which is not a second rule |

## Not written

- `StopAtInitialRiskMultiple` — blocked on a missing engine primitive: there is
  no accessor for the entry-to-initial-stop distance frozen at entry, and the
  stop that set it belongs to a different placement. Substituting an input that
  restates the distance turns the rule into `StopLoss` at a fixed dollar amount,
  which the merge notes themselves call the cheap way to test it; emulating the
  captured stop with a `MarketPosition` reset is forbidden by skill §4. Engine
  request: a fixed initial-risk / initial-stop accessor.
- `ProfitTargetAtInitialRiskMultiple` — blocked on the same missing accessor
  (`ctx.InitialStopPrice()`), as its own merge notes state. With the risk
  supplied as an input it degenerates to a fixed-dollar target, i.e.
  `TakeProfitWithRatioStop`'s target leg. One accessor unblocks both this and
  `StopAtInitialRiskMultiple`.
- `PriorSwingExtremeTarget` — suspected duplicate of `SwingPivotTarget` (B03,
  on disk), which the merge pass could not have seen: `SwingPivotTarget` at
  `pivotIndex = 1` is "the long exits when the high reaches the most recent
  confirmed swing high", which is this rule at `toleranceAtr = 0`. The only
  behavioural difference is the ATR tolerance band that lets it fire a little
  early. Skill §2's third test ("is it an existing rule at a fixed parameter?")
  says stop and report rather than write. If the orchestrator wants the
  tolerance, the cheaper change is a `toleranceAtr(0)` input added to
  `SwingPivotTarget`, which is backward compatible at its default.
- `TrendChannelLineTarget` — not authored, per the orchestrator's decision:
  covered by `ChannelLineTargetExit` (B02).

## Notes for the orchestrator

- No hook-scope C++ declarations anywhere in this slice. Scratch that the
  reference implementations declare as `const int` at hook scope
  (`SwingHigh`'s `pivStrength`/`pivWindow`, `ChannelLineTargetExit`'s
  `pivS`/`pivW`/`foundLo`/`foundHi`, `EmaGapBar`'s `emaSf`) is declared as
  local variables here instead, so a rule placed twice in one strategy still
  compiles. Loop counters and block-scoped temporaries inside `for`/`else`
  bodies are unaffected. The three named files still carry the collision.
- Two rules lean on `BarsSinceEntry() == 0` as the per-position reset for state
  the engine has no accessor for: `BreakevenExitAfterAdverseExcursion` (the
  running minimum of open profit) and `BreakevenStopAfterEmaHoldingRun` (the
  consecutive-bar counter and the armed flag). That is the VERIFIED accessor
  that restarts through a reversal, not the `MarketPosition() == 0` reset skill
  §4 forbids, and it is the same convention slices 09 and 10 use to capture
  signal-bar values. If either should instead be blocked pending a
  `MinPositionProfit` accessor, only the first is affected.
- `NearMeasuredMoveTargetFilter` gained `refOffset(10)` and `multiple(1)`,
  neither in the merged parameter list; `SessionMidpointTarget` gained
  `midpointFraction(0.5)` and `minSessionBars(6)` against an empty merged list;
  `OpeningRangeMeasuredMoveTarget` gained `tolerancePoints(0.25)` and
  `PullbackSizedProfitTarget`/`ShrinkingSwingIncrementsExit` gained
  `lookbackBars(40)` for the pivot window. Each is a hard-coded number the
  pseudocode assumed, promoted per AUTHORING.md; `refOffset` and
  `minSessionBars` are the two that change whether the rule can fire at all,
  and both are argued in the rule's own header comment.
- Ticks: `tolerancePoints(0.25)` is one Emini tick in price points, the slice
  09/10 convention, because `MinMove`/`PriceScale` have no engine counterpart.
  Nothing else in the slice was stated in ticks.
- No `ASSUMED` register rows are relied on. Words used:
  `marketposition`, `entryprice`, `openpositionprofit`, `barssinceentry`,
  `bigpointvalue`, `currentbar`, `date`, `date[n]`, `highest`, `lowest`,
  `absvalue`, `swinghigh`, `swinglow`, `swinghighbar`, `swinglowbar`,
  `wfsafe_xaverage`, `wfsafe_avgtruerange` — all VERIFIED or ACCEPTED.
- Nothing outside the EasyLanguage translation table. The ternaries in the ATR
  accumulator of `NearMeasuredMoveTargetFilter` are `MaxList`/`MinList` on
  tick-grid price operands, carried over verbatim from
  `ChannelLineTargetExit`/`AtrProfitTarget`.
- `validateRule` and `python lintElFeatures.py` are clean on all nine: no
  errors, no warnings, 0 blocking over 353 rules.
