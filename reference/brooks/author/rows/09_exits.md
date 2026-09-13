# CATALOG rows — slice 09_exits (exits: targets and stops)

Eleven rules in the slice, eleven written, both twins each. Rows are in
`rules/CATALOG.md` table format, ready to append.

| Rule | Type | Sides | Reaches back | Inputs | Fires when |
|---|---|---|---|---|---|
| `PullbackNearMissesEntryPrice` | Entry | mirrored | 0 | `missOffset(0)`, `nearOffset(1.25)` | The bar's low comes down into a band just above the open long's entry price — beyond it by more than `missOffset` but no more than `nearOffset` — so the pullback tested the breakeven stops and missed; short is the mirror on the high. A BAND, so not the negation of `PullbackReachesEntryPrice`: on a bar that never comes near the entry price that rule negated is true and this one is false. Offsets are PRICE POINTS, not ticks (`MinMove`/`PriceScale` are unregistered): the book's 0 and 5 ticks are carried as 0 and 1.25, five Emini ticks — instrument-specific, like `CloseNearPriorLow`'s `threshold` |
| `PullbackReachesEntryPrice` | Entry | mirrored | 0 | `toleranceOffset(0)` | The bar's low trades at or below the open long's entry price plus the tolerance — the pullback hit the breakeven stops; short is the mirror on the high. Brooks's strength sign is this NEGATED ("the first pullback does not reach breakeven"), which the per-placement negate toggle gives. An Entry that reads position state, like `FlatOrOpenLossExceeds`. `toleranceOffset` is price points, not ticks (book values 0 and 2 ticks; 0 is the default because the book means the stop being hit) |
| `BreakevenStop` | Exit | **mirrored** | 0 | `activationProfit(100)`, `breakevenBuffer(0)` | Peak profit for this position has reached X dollars and the close has come back to the entry price (long: at or below `EntryPrice − breakevenBuffer`; short mirrored above). `MaxPositionProfit` is the activation accessor — VERIFIED as the INTRABAR peak, net of the entry side's costs, reset per position including through a reversal. Not `ProfitProtector`: the buffer lets the floor sit BELOW the entry price, which no `retracement` reaches. At `activationProfit = 0` it degenerates to the bare "price returns to entry" test; at 0.5 × a target it is Brooks's "halfway to the target". `breakevenBuffer` is price points, not ticks (the book's 3-tick give is why the input exists). **The slice said sides `same`; it is directional and the short side is flipped** |
| `StopAtSignalBarRangeMultiple` | Exit | same | 1 | `stopRangeMult(1)` | Open loss reaches K × the SIGNAL bar's own high−low range, converted with `BigPointValue` — a volatility-scaled INITIAL stop, the gap between `StopLoss` (fixed dollars) and `AtrTrailingStop`. The signal bar is the bar before the entry bar; it is captured once on the fill bar (`BarsSinceEntry() = 0`, VERIFIED) as `high[1] − low[1]` rather than re-indexed by the position's age every bar, which is what holds "reaches back" at 1 instead of the length of the longest trade. `BigPointValue` is the raw multiplier and is NOT currency-converted while `OpenPositionProfit` is — TradeStation's own inconsistency, same as `AtrProfitTarget` |
| `StopBeyondExtremeSinceEntry` | Exit | mirrored | 0 | `ratchetOffset(0.25)` | Close breaks the worst price the trade has seen since entry: long exits at or below (lowest low from the entry bar through the PREVIOUS bar) − `ratchetOffset`, short mirrored above the highest high. Not a trail — the level only widens — so it behaves as a self-widening initial stop, exactly as the book's 11-tick-pullback → 12-tick-stop arithmetic does. **Corrected from the merged pseudocode**, which took the extreme over a window INCLUDING the current bar: that low is always ≤ this close, so the long side could never fire with a positive offset. Kept as a running min/max in locals rather than a window whose length is the position's age, so nothing indexes back by the trade's length. `ratchetOffset` is price points, not ticks (one Emini tick) |
| `StopBeyondRecentRangeExtreme` | Exit | mirrored | `rangeLookback` | `rangeLookback(20)`, `stopBuffer(1.25)` | Close falls below `Lowest(Low, N)` of the N bars ENDING ONE BAR AGO minus the buffer (long) / rises above `Highest(High, N)[1]` plus it (short) — a Donchian-style protective stop, which the catalog had only as entries (`Breakout`, `CloseAbovePriorHighestHigh`). The book anchors it to an identified trading range's low; the N-bar low is the substitution, and it tracks a real range floor well inside a range and badly right after a trend leg. Brooks's point is the SIZE of the buffer, so `stopBuffer` is the input worth optimizing — price points, not ticks (5 Emini ticks) |
| `StopFractionOfSignalBarRisk` | Exit | mirrored | 1 | `stopFraction(0.3)` | The stop sits a fraction of the way from the signal bar's low up toward the entry price, not beyond the bar: long exits when close ≤ `sigLow + stopFraction × (EntryPrice − sigLow)`, short mirrored. A money-management stop for a signal bar too tall to risk whole; the book's 30% is a couple of ticks beyond the 62% retracement of that bar. Both ends are readable at run time, so no stored initial-stop accessor is needed. Signal bar captured on the fill bar as `low[1]`/`high[1]`. At `stopFraction = 0` it degenerates to a zero-offset `StopBeyondSignalBar` |
| `TightenStopToEntryBarIfStrong` | Exit | mirrored | 0 | `strongBodyFrac(0.6)`, `stopOffset(0.25)` | Once the entry bar has closed AND closed as a trend bar in the trade's direction — bull close and body ≥ F × its own range — the stop moves in from the signal bar to the entry bar's own extreme: long exits when close ≤ entry-bar low − `stopOffset`. Otherwise the rule never fires and the wider signal-bar stop (a separate placement) stands. The entry bar's four prices are captured on the fill bar, so nothing indexes back by the trade's age, and the "entry bar has closed" gate is `BarsSinceEntry ≥ 1`. At `strongBodyFrac = 0` it is the book's unconditional form (`R05-14`, `R24-03`). The body test is a multiplication, never a division, so a zero-range bar cannot raise EL's divide-by-zero. `stopOffset` is price points, not ticks |
| `WeakEntryBarScratchExit` | Exit | same | 0 | `weakBodyFrac(0.3)` | On the entry bar itself, the body \|close − open\| is no more than F × the bar's range — a doji entry bar, a setup without urgency — so scratch the trade; the exit fills at the next open. **Corrected from the merged pseudocode's `BarsSinceEntry() == 1`**, which with a bar-[0] test reads the bar AFTER the entry bar and contradicts the description: `BarsSinceEntry()` is VERIFIED as 0 on the fill bar, so `MarketPosition <> 0 and BarsSinceEntry = 0` is exactly the entry bar. Fires at most once per position. `NumBars(1)` with a bar-quality gate instead of a bar count. The book's other halves are separate panes: the inside-bar term is `InsideBar`, the breakeven band is `BreakevenStop`, the weak-signal-bar term is a bar_anatomy rule |
| `WiderStopForSmallSignalBarCapped` | Exit | mirrored | 1 | `smallBarRange(1)`, `widerStopOffset(0.75)`, `baseStopOffset(0.25)`, `maxStopDistance(2)` | Stop beyond the signal bar, with the offset widened when that bar is unusually small (an outside-bar stop run is likelier) and the whole distance capped from the entry price: long exits when close ≤ `sigLow − offset` OR close ≤ `EntryPrice − maxStopDistance`, where `offset` is `widerStopOffset` if the signal bar's range ≤ `smallBarRange` and `baseStopOffset` otherwise. Two behavioural differences from `StopBeyondSignalBar`, not one parameter. **`MaxList` deliberately avoided**: `Close ≤ MaxList(A, B)` is exactly `Close ≤ A or Close ≤ B`, and the register ACCEPTS MaxList only for tick-grid price operands — `EntryPrice − maxStopDistance` is an optimizer value, off the grid. The if/else picking the offset lives in the hook because EasyLanguage has no ternary. All four inputs are price points, not ticks (book values 4, 3, 1 and 8 Emini ticks, the 8-tick cap calibrated to the 5-minute Emini) |
| `BreakoutMissesScalpTarget` | Entry | mirrored | `pullbackWindow + swingLookback - 1` | `swingLookback(20)`, `pullbackWindow(5)`, `scalpDistance(1)` | Sign of weakness: the breakout never paid a scalper. The highest high of the last `pullbackWindow` bars minus the highest high of the `swingLookback` bars ending just before them is less than `scalpDistance` (short: the mirror on lows). Written as two BACKWARD windows so nothing peeks ahead — the evaluation bar is a bar of the pullback. `Highest(High[pullbackWindow], swingLookback)` rather than `Highest(High, swingLookback)[pullbackWindow]`: same bars, no function-series history. `scalpDistance` is price points, not ticks (4 Emini ticks) |

## Not written

None — all eleven rules in the slice were written.

## Flagged for the orchestrator (written, but check against a sibling slice)

- `StopAtSignalBarRangeMultiple` vs **`EntryBarRangeStop` (slice 13)**: the same
  test — open loss ≥ K × one bar's high−low range — on a bar ONE INDEX apart
  (this reads the signal bar, `BarsSinceEntry + 1`; slice 13 reads the entry bar,
  `BarsSinceEntry`). Slice 13's pseudocode also compares in POINTS where this one
  converts to dollars with `BigPointValue`. If the two are merged, one rule with a
  bar-offset input covers both; neither merge-notes block mentions the other.
- `PullbackReachesEntryPrice` vs **`EntryPriceRetest` (slice 06)**: `EntryPriceRetest`
  is this rule's long condition AND a `Close >= EntryPrice − tol` "and holds" term,
  same Entry role. Kept as the atom on the corpus's own precedent (`InsideBar` and
  `CloseAbovePriorHigh` live beside `EecQuickPullbackPattern`, which is their
  conjunction), but if only one survives it should be this one plus a separate
  hold term.
- `PullbackReachesEntryPrice` vs **`BreakevenRetestExit` (slice 06)**: identical
  condition text, Exit role instead of Entry. That pairing is established in the
  corpus (`ConsecutiveCloseExit` is `MomentumConsecutiveBars(1)` in the exit pane),
  so both are legitimate — noting it so it is not read as an accident.
- `BreakevenStop` at `activationProfit = 0`, `breakevenBuffer = 0` is close to
  **`BreakevenRetestExit` (slice 06)**, but tests the CLOSE where that rule tests
  the LOW, so they fire on different bars.

## Conventions used across the slice

- **No tick units anywhere.** Every `*Ticks` parameter in the slice became a
  price-point input, per AUTHORING.md: `MinMove`/`PriceScale` have no register row.
  Defaults are the book's tick counts at the Emini's 0.25 points/tick, and are
  instrument-specific — the grid pass should set them per symbol.
- **Signal-bar and entry-bar values are captured once on the fill bar**
  (`BarsSinceEntry() = 0`, VERIFIED — 0 on the fill bar, 0 while flat, restarting
  through a reversal) instead of indexed by `BarsSinceEntry() + 1` on every bar.
  Identical values; it keeps the deepest subscript at 1 instead of the length of
  the longest trade, which Max Bars Back would otherwise have to cover. The
  re-capture on every flat bar is harmless and is what leaves the value right on
  the fill bar. `StopBeyondExtremeSinceEntry` does the same with a running
  min/max instead of a window whose length is the position's age.
