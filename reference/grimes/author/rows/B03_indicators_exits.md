# Slice B03_indicators_exits — CATALOG rows

Paste-ready rows for `rules/CATALOG.md`, one per rule written. Eight of the
slice's nine keys were authored; `TimeDecayStopTightening` is under
"Not written".

2026-11-06: the `DailyLossLimit` row below is superseded. A `DailyLossLimit` with input
`LossLimit(1000)`, written separately and already placed in 202611 BRK and OWN templates,
arrived in a pull; it is the same rule bar for bar except the first evaluated bar and an exact
tie, so it replaced this one. See `author/DECISIONS.md`.

| Rule | Type | Sides | Reaches back | Inputs | Fires when |
|---|---|---|---|---|---|
| `MomentumDivergenceAtSwingExtreme` | Entry | mirrored | `max(slowLen - 1, divLookback)` | `fastLen(3)`, `slowLen(10)`, `divLookback(20)` | Price makes a new `divLookback`-bar high while the 3/10 oscillator stays under its OWN window high (short: a new low with the oscillator above its window low) — Grimes's momentum divergence, settled by **merge decision 3** as WINDOW MAXIMA, never a pivot scan. `VolumeDivergenceAfterClimax` is the porting template (same shape, volume in place of the oscillator) and was re-read against its JSON: a variant, not a duplicate. **Sides read literally from the merged pseudocode, which is the long side by convention**, so the long side is the upper-extreme (classically BEARISH) divergence and the short side its mirror at a new low. That is what lets this rule and `NoMomentumDivergenceInWindow` share one computation — Grimes's use is "after a divergence at the high, do not buy the next pullback", a LONG-PANE reading — and the merge marks it `is_filter`, so as a blocker it is placed NEGATED in the long pane. The window extremes are explicit loops, not `Highest(...)[1]`: they mirror `Extremes`' measured semantics (seed the window's first bar, scan the rest, STRICT comparison) and need no lagged read of a function's own output. `osc` is an EL VARIABLE, mirrored as a zero-seeded ring buffer; `divReady = CurrentBar > divLookback` holds the rule off that zero-filled pre-history, against which a real reading would look "short of the peak" for free |
| `NoMomentumDivergenceInWindow` | Entry | mirrored | `max(slowLen - 1, sinceDivergenceBars + divLookback - 1)` | `fastLen(3)`, `slowLen(10)`, `divLookback(20)`, `sinceDivergenceBars(20)` | No momentum divergence fired at any of the last `sinceDivergenceBars` bars — Grimes's "long trades should not be entered on the next pullback" after a divergence, stated POSITIVELY, so an entry pane places it un-negated to require the all-clear. The inner test is `MomentumDivergenceAtSwingExtreme`'s term for term (merge decision 3), evaluated at each bar of the window with its own one-bar-shifted `divLookback` window, so the two rules share one computation and their sides line up. **A single negated placement of that rule cannot express this** — it tests the current bar only — which is why the bounded OR is its own file, the same relation `NoClimaxBarInWindow` has to its primitive. Nested `Extremes`-shaped loops (about `sinceDivergenceBars × divLookback` comparisons a bar), the form `TightRangeRunLength` uses. **While `divReady` is false the rule reads TRUE**: the oscillator's zero-filled pre-history would manufacture divergences, and an all-clear filter must not block on a warm-up reading (`OscillatorSlowLineExtendedRollover`'s precedent) |
| `OscillatorArtifactWindowBlock` | Entry | same | `slowLen - 1` | `fastLen(3)`, `slowLen(10)` | More than `slowLen` bars have passed since the 3/10 oscillator last crossed zero — Appendix B's proof that for the first `slowLen` bars after a genuine trend inflection the fast line's curvature is an artifact of the slow average rolling into the new regime, so hook and divergence reads inside that window mean nothing. **Resolves the merge's one open question** (what anchors the window) with the C-list resolution: the anchor is the OSCILLATOR ZERO CROSS, which merge decision 2 records as `MovingAverageCross` at `fastLen`/`slowLen`. Not `BarsSinceEmaCross`, the merge's named `variant`: that counts bars since the CLOSE crossed an EMA, a different anchor on a different series; re-read against its JSON. **The window length is `slowLen` and gets no input of its own** — Appendix B's point is that the distortion lasts exactly as long as the slow average takes to roll over, so a separate input would invite a grid to optimize away the one measured thing here. `crosses above`/`below` is the VERIFIED STATE MACHINE, mirrored as `MovingAverageCross` mirrors it (fire flag before the side update, equality runs bridged, side starts UNKNOWN) rather than reading `osc[1]`, which is the variable's zero-filled pre-history. Identical both sides — an inflection has no direction. Before any cross the counter counts bars since the strategy's first, so the rule reads TRUE after `slowLen` bars, the permissive polarity a window blocker wants during warm-up |
| `AntiStochasticSlopeDisagreement` | Entry | mirrored | `max(fastLookback, slowLookback) - 1` | `fastLookback(5)`, `slowLookback(20)`, `smoothing1(3)` | A fast stochastic's SlowK is rising while a slow one's is falling (short: mirrored) — Linda Raschke's original "Anti" confirmation, which Grimes cites beside his own price-structure Anti. **Was priority C, resolved**: FastK/SlowK need no register row of their own, because the `stochastic` row is VERIFIED for the whole chain and `rules/StochasticCross.json` is the measured port this rule copies — the ratio-of-sums SlowK (`100·Sum(C − LL, Smoothing1) / Sum(HH − LL, Smoothing1)`, NOT an average of FastK) with the SEED-FILLED warm-up, and `SmoothingType` pinned to 1. Not `StochasticCross`, the merge's named `variant`: that fires on a SlowK/SlowD cross at ONE length and never compares two lengths; this one never reads SlowD. Re-read against its JSON. **Deliberate divergence from the merged pseudocode**, recorded rather than hidden: the pseudocode spells the series `fastK(n)` and the rule reads **SlowK**, because that is the VERIFIED quantity the addendum points at, Raschke's Anti is a slow-stochastic rule, and a one-bar slope on a 5-bar raw FastK is close to a coin flip. `smoothing1` is passed in BOTH of `Stochastic`'s smoothing slots rather than carrying a second input that could not change behaviour (SlowD, its only consumer, is never read). The one-bar slopes read the VARIABLES' own zero-filled history, so on the first evaluated bar neither AND can hold — mirrored, not corrected. An all-flat window makes a denominator 0 and EL raises there; neither twin guards it, as `StochasticCross` does not. A ratio of price DIFFERENCES, so it passes the shift test |
| `ParabolicSarTrailingStop` | Exit | mirrored | `2` | `afStart(0.02)`, `afStep(0.02)`, `afMax(0.2)` | Wilder's Parabolic SAR, literally, as an EXIT-ONLY trailing stop: `sar = sar + af·(ep − sar)`, the extreme point set from the position's own new highs (short: lows), the acceleration factor starting at `afStart` and stepping `afStep` to `afMax` on each new extreme, and the stop clamped so it never sits inside the PRIOR TWO BARS' range. The long exits on a close at or below the stop. **Never stop-and-reverse** — the generator's `MarketPosition` guard decides which side is live, so the recursion is carried once in the position's direction and restarts at the next entry. **All state is per position and resets on `BarsSinceEntry == 0`**, VERIFIED as 0 on the fill bar and as restarting through a REVERSAL, which a `MarketPosition == 0` reset would miss. The seed is the fill bar's own extreme (no pre-entry trend to inherit) and the stop is not live until `BarsSinceEntry >= 1`, or a fill bar closing on its low would be stopped out on the spot. Merge decision 23 makes this the only new exit machinery Grimes contributes; place it with `NumBarsIfLosing` (decision 23's `NumBarsIfBelowProfitThreshold`, which slice 03 resolved into that rule's new `profitThreshold` input) as the hard time stop. `ParabolicAccelerationExit` shares only the name — it compares two successive leg magnitudes and carries no recursion; re-read against its JSON. The cap is an `if`, not `MinList`, so both twins read as the same walk. A price plus multiples of price DIFFERENCES, so the recursion shifts with the series |
| `BreakevenStopAfterFavorableCloseRun` | Exit | mirrored | `1` | `favorableCloses(2)` | `favorableCloses` consecutive closes since entry have each moved in the trade's favour (`Close > Close[1]` long, `Close < Close[1]` short), arming a breakeven stop, and a later close back at the entry price takes the trade off. Grimes: "once a trade is working ... tighten stops to reduce open risk"; his worked example arms on 2 closes and he gives no general number. `BreakevenStopAfterEmaHoldingRun` is the shape and the latch idiom, copied term for term, and only the ARMING TEST differs — the two arm on completely different bars (a drift up below the average arms this one and not that, a flat stretch above the average arms that one and not this) and no input setting of either reproduces the other, so it is a **variant, not a parameterization**; re-read against its JSON. Kept apart from `BreakevenStop`, whose trigger is peak profit reaching a dollar figure. Counters and flags reset on `BarsSinceEntry == 0` (VERIFIED on the fill bar and through a reversal) and advance on the fill bar too, so a fill bar closing above the previous close is the first of the run — the precedent's timing exactly. Both terms are price DIFFERENCES |
| `GapAgainstPositionOpeningRangeBreakExit` | Exit | mirrored | `1` | `openingBars(3)`, `minGapTicks(0)` | The session gapped against the position AND the market has since broken the opening range the wrong way — the long exits when the session opened below the previous close and, after the first `openingBars` bars, a bar's low breaks the opening range low. Grimes: "if the market opens down and immediately presses lower, or breaks lower out of an opening range ... long positions should be dumped immediately." Two session facts fixed early and read all day: the GAP SIGN, captured on the session's first bar from `Open − Close[1]`, and the OPENING RANGE, frozen once `openingBars` bars have printed. **SESSION MODEL** per the standing decision, the block copied from `OpeningRangeBreakout` / `OpeningRangeMeasuredMoveTarget`: `date > date[1]` (the bar's wall-clock CLOSE date), running extremes and a bars-into-session counter in locals, `barsIn` 1 on the session's first bar. **Intraday only.** The gap is latched in BOOLEANS, never a price local with a sentinel, and the quantity tested is a difference, so the rule is shift-safe. `minGapTicks` is written division-first, `ticks × (MinMove / PriceScale)`; at its default 0 the test is the merged pseudocode exactly (any gap at all, strictly) and a grid can raise it. Warm-up mirrors EL: if the first calculated bar falls mid-session, `barsIn`/`orHigh`/`orLow` hold 0 and both flags false, so nothing fires before the first date change. The corpus's other opening-range exits are TARGETS and none reads the gap direction against an open position (`OpeningRangeMeasuredMoveTarget` re-read: `none`, as the merge said) |
| `DailyLossLimit` | Switch | same | `1` | `dailyLossLimit(1000)` | Equity given up since the first bar of the current calendar day has reached `dailyLossLimit` — no new entries are taken and the open position is closed for the rest of the day. **Merge decision 16**: `MonthlyProfitTarget`'s construction with the boundary moved from `Month(Date) <> Month(Date[1])` to `date <> date[1]` and the comparison on the LOSS side; that rule was re-read against its JSON and no new engine accessor is needed. `EquityDrawdownFilter` is the rolling-window cousin and resets at no boundary. The day's starting equity is the PREVIOUS bar's equity captured on the date-change bar (`CurrentEquity[1]`), so the day's first bar is already inside the tally. **Forcing flat is WANTED** — unlike `MaxTradesPerSession`, which adds a `MarketPosition = 0` term to block entries only, this rule carries none: a day that has lost its limit is over, which is `MonthlyProfitTarget`'s Switch behaviour. Direction-agnostic, so both sides are identical text. **The C++ boundary reads the previous bar's date directly** (`day_of(ctx.Time(0)) != day_of(ctx.Time(1))`, `MaxTradesPerSession`'s spelling) rather than a remembered day number, which would differ from EL on the strategy's first evaluated bar. **No `periodSelect` input**: the month form is already `MonthlyProfitTarget`'s mirror image and a mode input would buy one boundary at the cost of a branch in both twins. Grimes gives no figure; 1000 is a placeholder for the grid. Dollars of profit, so it is shift-safe |

## Amended

_None. No rule in this slice is a `parameterization` of an existing rule._

Every `catalog_match` in the slice was re-read against the named rule's actual
JSON before writing. Findings:

- `VolumeDivergenceAfterClimax` — `variant`, confirmed. Same "new price extreme
  while the companion series stays under its own window extreme" shape on
  volume; it is the porting template for `MomentumDivergenceAtSwingExtreme` and
  shares no inputs with it.
- `BarsSinceEmaCross` — `variant`, confirmed. Counts bars since the **close**
  crossed an EMA; `OscillatorArtifactWindowBlock` counts bars since the
  **oscillator** crossed zero. Different anchor, different series, not a
  parameterization (the EMA cross cannot be reduced to the oscillator cross by
  an input).
- `StochasticCross` — `variant`, confirmed, and the measured port copied into
  `AntiStochasticSlopeDisagreement`'s C++. That rule is a SlowK/SlowD cross at
  one length; the new rule compares two lengths' SlowK slopes and never reads
  SlowD, so no input of either reproduces the other.
- `ParabolicAccelerationExit` — `none`, confirmed. Name overlap only: two
  successive leg magnitudes (`close[0] − close[legBars]` against
  `close[legBars] − close[2·legBars]`), no recursion, no state.
- `BreakevenStopAfterEmaHoldingRun` — `variant`, confirmed. Identical latch
  idiom and identical conditions; only the arming test differs, and the two arm
  on different bars, so it is a second file and **not** a new input on the
  existing rule.
- `OpeningRangeMeasuredMoveTarget` — `none`, confirmed. Shares only the session
  block (which was copied verbatim); it projects a measured move and never reads
  the gap direction or the position.
- `MonthlyProfitTarget` — `variant`, confirmed, and its construction copied
  (period-start equity latched from `NetProfit + OpenPositionProfit`, mirrored
  `[1]` history, Switch that forces flat).

## Not written

- `TimeDecayStopTightening` — **not written, merge decision 23.** Grimes gives
  only the analogy to the Parabolic and no tightening curve, and decision 23
  settles that `ParabolicSarTrailingStop` (the accelerating form he points at)
  placed with the hard time stop covers it. `NumBarsIfBelowProfitThreshold` is
  not a separate file: slice 03 resolved it into `NumBarsIfLosing`'s new
  `profitThreshold` input (`rows/03_exits.md`, Amended), so both halves of the
  pairing exist once the orchestrator applies that row. (**Superseded 2026-11-07:** it is now
  its own rule, `NumBarsIfBelowProfitThreshold`, and `NumBarsIfLosing` is back as HEAD has it.) The slice's own `catalog_match` already names
  `ParabolicSarTrailingStop` as its variant.

## Notes for the orchestrator

- `MomentumDivergenceAtSwingExtreme`, `NoMomentumDivergenceInWindow`,
  `AntiStochasticSlopeDisagreement` declare `std::vector<double>` /
  `std::size_t` locals for mirrored EL variable history and for the stochastic's
  growing num/den series, which `validateRule` reports as an "Unusual local
  type" warning — the same warning `BarRangeAboveStd`, `AtrRising`,
  `AwesomeOscillatorSlope`, `OscillatorNewExtreme` and `StochasticCross` already
  raise. No errors and no other warnings on any of the eight.
- **A deliberate divergence from `rules/StochasticCross.json`'s C++**: that rule
  declares `double hhWin = high[0];` and friends **at hook scope**, which is a
  redefinition under double placement. `AntiStochasticSlopeDisagreement` puts
  every one of those scratch values in `localVariables` instead. Worth fixing in
  `StochasticCross` separately; this slice did not touch it.
- **Sides convention for the divergence pair, flagged for review.** The merged
  `description` of `MomentumDivergenceAtSwingExtreme` ends "Grimes's bearish
  divergence fires on the LONG-side price extreme, so a short pane places it
  un-negated", which can be read as putting the high-side test on the SHORT
  side. It was authored the other way — high-side on the LONG side — because the
  slice states its `pseudocode` as the long side, because `G03-14`'s sentence
  ("long trades should not be entered on the next pullback") is a long-pane
  reading that forces the high-side test onto `NoMomentumDivergenceInWindow`'s
  long side, and because the addendum requires the two rules to share one
  computation. Flipping both rules' sides is a two-line change in four files if
  Brian reads it the other way.
- `AntiStochasticSlopeDisagreement` introduces `smoothing1(3)` and reads SlowK
  where the merged pseudocode spells `fastK`; see the row. Its two `Stochastic`
  call sites are separate EL function instances at different lengths, which is
  the normal EL shape but has not been exercised twice in one study before in
  this corpus.
