# EasyLanguage feature registry

Every EasyLanguage reserved word or built-in a rule may use, and what we actually
know about it. **Read this before writing a condition that reaches for anything
not already in the corpus.** `lintElFeatures.py` reads the tables below, so the
first column is the exact token it matches — lowercase, because EasyLanguage is
case-insensitive and the corpus writes `Maxpositionprofit` and
`maxpositionprofit` on the same line.

Why this exists: the engine reproduces TradeStation and MultiWalk bit-for-bit,
and *almost every EL feature the corpus reached for turned out to behave
differently from the obvious reading*. Thirteen rules needed seventeen
`EL_*_Probe.txt` runs to pin down. `Volume` is up-ticks, not total.
`BarsSinceExit` needs an index. `WFSafe_AvgTrueRange` is a rolling accumulator
and a different function from the built-in it resembles. Each was found *after* a
MultiWalk disagreement. This table is how the next one gets found before.

## Status

| Status | Meaning | Gate |
|---|---|---|
| **VERIFIED** | A TradeStation probe was run and the finding is recorded. The row cites the probe. | passes |
| **ACCEPTED** | No probe, but the basis is stated and Brian has signed off on the row. | passes |
| **UNKNOWN** | Behaviour not established. | **blocks** |

Anything not listed at all is treated as UNKNOWN and blocks. That is deliberate:
the default answer to "does EL do the obvious thing here?" has been *no* more
often than yes.

## Data series

| Feature | Status | What is known | Evidence |
|---|---|---|---|
| `close` `open` `high` `low` | VERIFIED | EL-indexed, `[0]` is the just-closed bar; reading past Max Bars Back throws, mirroring TS's "tried to reference back more bars than allowed" | `bt_compare` bar-level acceptance; `test_strategy.cpp` `ElIndexingMatchesForwardArrays` |
| `volume` | VERIFIED | **Up-ticks, not total.** `Volume` == UpTicks on all 18,203 bars of @KW 480min and 1440min. A 1440-minute bar is still an *intraday* bar (`BarInterval` reads 1440; a Daily-bar chart reports 1), which settles the whole universe | `EL_Volume_Probe.txt`; `chunk.h` `up_volume` |
| `ticks` | VERIFIED | Up + down. Stored separately so a rule can ask for either | `EL_Volume_Probe.txt` |
| `time` | VERIFIED | Bar **close** timestamp, exchange time, no timezone conversion anywhere in the engine. EL `Time` is the close's wall-clock **HHMM**, and a bar closing at midnight reads **0**, not 2400 — measured as a byproduct of the Date probe on @HO 60min: its `time` column matched the close timestamp's HHMM on **169/169** printed bars, **7 of them midnight bars printing 0** with `date` advancing on the 23:00→0:00 rollover, and evening bars 1900–2300 carrying the wall-clock date. **Strategy context measured too**: `EL_TimeOfDayExit_Probe.txt` (@HO 60min, 2015, two runs at TimeExit 1600/1700) — `Time >= T` **includes the bar closing exactly at T**; an exit signalled on the session's **last** bar fills at the **next session's first-bar open**; evening bars 1900–2300 satisfy `Time >= 1600` (wall clock, not session time — proven on holiday early closes); midnight bars never signal. A replica of the engine's semantics reproduces `MarketPosition`/`BarsSinceEntry` on **5,743/5,743 bars in both runs** once the from-flat order collision (see the order-placement row) is modelled | Ingest validates bars inside the session window; `CLAUDE.md`; `EL_Date_Probe.txt` + `el_date_output.txt`; `EL_TimeOfDayExit_Probe.txt` + `el_timeofdayexit_output_1600/1700.txt` |
| `date` | VERIFIED | The bar's **wall-clock close date**, not its session date — @HO opens at 18:00, so the 21:00–23:00 bars of 2015-06-30 could have belonged to the 1 July session, and TradeStation calls them 30 June. `Year`/`Month`/`DayOfMonth`/`DayOfWeek` agree with `civil_from_days(day_of(ctx.Time(0)))` on **169/169** bars, **50 of them evening bars**, across two month boundaries. `MonthlyProfitTarget` snapshots on the right bar | `EL_Date_Probe.txt`; `CLAUDE.md`; `Strategy.GatingAndCurrentBar` locks `Time()` |
| `dayofweek` | VERIFIED | `DayOfWeek(Date)` of the bar's wall-clock close date, **0 = Sunday .. 6 = Saturday**. Printed as the `dow` column of the date probe and agreed with `day_of_week(day_of(ctx.Time(0)))` (`time.h`, same numbering) on **169/169** bars, 50 of them evening bars. `DayOfWeekEntry` reads it | `EL_Date_Probe.txt`; `time.h` `day_of_week` |
| `currentbar` | ACCEPTED | 1 on the first `OnBarClose`, i.e. EL's 1-based numbering. The first evaluated bar is index `MaxBarsBack`, which is also the `WFSafe_` seed bar | `simulator.cpp` gating; `test_strategy.cpp` `GatingAndCurrentBar` |

## Standard functions

| Feature | Status | What is known | Evidence |
|---|---|---|---|
| `average` | VERIFIED | Recomputes from scratch every bar — **not** a rolling accumulator. Matched a fresh loop on 2,808/2,808 bars. Over a *variable*, it reads that variable's own zero-filled history (see `and`/`or` note below) | `EL_Summation_Probe.txt`, `EL_SummationSeed_Probe.txt` |
| `stddev` | VERIFIED | **Population form** (divide by N). Do not "fix" it to N−1 | `BarRangeAboveStd`, MW agreement |
| `highest` `lowest` | ACCEPTED | Bottom out in `Extremes`, which is EL *source*: seeded at bar 0, scanning 1..Length−1, strict comparison so a tie keeps the earliest bar. Being EL source, it carries the relational tolerance | Brian read the function source; `Breakout` |
| `truerange` | VERIFIED | `max(High, Close[1]) − min(Low, Close[1])`, the two-term form | `EL_HO_TrueRange_Precision_Probe.txt` — identical on 316/316 bars incl. per-field price representation |
| `month` | ACCEPTED | Calendar month of the bar's date | `MonthlyProfitTarget`; versions 8/20 agree 100% on money across 768 ranges |
| `squareroot` `absvalue` | ACCEPTED | Pure scalar arithmetic, no state, no accumulation — nothing to measure | — |
| `avgprice` | VERIFIED | **(Open + High + Low + Close) / 4, summed left to right** — the other operand order differs in the last bit on 2,750 of 8,327 bars, so order matters. **A bar whose Open is 0 returns (High + Low + Close) / 3** — measured on the one such bar in the run (2012-05-23 14:00, TS's data), where the four-term mean was off by exactly 0.225 and the three-term one by 0. `CloseWithinAtrOfVwap` accumulates it into a session VWAP and carries the zero-open branch | `EL_AvgPrice_Probe.txt` on @OJ 240min: 8,326/8,327 four-term, 1/1 zero-open |
| `maxlist` `minlist` | **UNKNOWN** | **Not EL source**, so whether they carry the relational tolerance is unestablished. Inert in the corpus today only because `AtrProfitTarget`'s stand-in loop compares tick-grid prices that differ by zero or by ≥1 tick — 1e9–1e11× the tolerance | `el_compare.h` says so explicitly |
| `mod` | **UNKNOWN** | Sign behaviour on **negative** operands differs between C++ `%`, `std::fmod` and EL's `Mod`, and nothing has measured which EL follows | — |
| `adx` | VERIFIED | **Identical to `wfsafe_adx` on all 18,141 probed bars at fixed length** (the probe's `ovr` column: 0 throughout) — the WFSafe wrapper's only change is recomputing `SF = 1/Length` per bar, inert when Length never changes. MW strategies call `wfsafe_adx`, which is the row rules are held to; see it for the full verified model | `EL_ADX_Probe.txt` (cross-check column); `el_source_wfsafe_adx.txt` header |

## MultiWalk overrides

A `WFSafe_` wrapper is a **different function** from the EL built-in it
resembles, and it wins. Where MultiWalk provides no override, follow plain EL.

**Time-series functions generally compare against the `WFSafe_` version.**
MultiWalk wraps the series functions its strategies use — anything that
accumulates state across bars (ATR, summation, ADX, ...) — so when a rule
reaches for one, the default assumption is that the MW twin calls the
`WFSafe_` variant, and *that* is the gold standard to probe; probing the plain
built-in answers the wrong question. Scalar functions and the ones measured
plain above (`average`, `stddev` over variables) are the exceptions, not the
rule.

| Feature | Status | What is known | Evidence |
|---|---|---|---|
| `wfsafe_avgtruerange` | VERIFIED | A **rolling accumulator**, not a fresh mean: seeded with a full N-term sum on the study's first calculated bar (MaxBarsBack + 1), then `S = S[1] + value − value[Length]`, re-seeding when the length changes. The update is **two statements** — EL evaluates left to right, and folding to `S += in − out` rounds differently and lands on the other side of a threshold | `EL_WFSafeAtr_Probe.txt`, `EL_WFSafeSeed_Probe.txt`; `EL_HO_WFSafeAtr_Probe.txt` reproduces TradeStation on **112,705/112,705** bars |
| `wfsafe_summationfc` | **UNKNOWN** | Named in MultiWalk's library and presumed to share the rolling/re-seeding shape, but never measured | — |
| `wfsafe_adx` | VERIFIED | Source-faithful port reproduces TradeStation **bit for bit: drift-exact on 9,794/9,794 bars (2007-start run) and 8,287/8,287 bars (2010-start run)** of @OJ 240min. The verified model: MW's `WFSafe_DirMovement` (source on file — TS's `DirMovement` with `SF = 1/Length` recomputed per bar so a walkforward length change takes effect; **no re-seed on length change**, unlike `wfsafe_avgtruerange` — the accumulators carry over), **seeded at the study's first calculated bar** (function `CurrentBar` = study `CurrentBar`): fresh Length-term DM/TR sums reaching `Length` bars back, then EMA-form `Avg = Avg[1] + SF*(X − Avg[1])`; `oADX` warms up as `Cum(oDMI)/CurrentBar` through bar Length, then `oADX = oADX[1] + SF*(oDMI − oADX[1])`. **The relational tolerance is decisive in the DM classification**: `UpperMove`/`LowerMove` are differences of grid prices, so float noise manufactures near-ties — measured at 2010-02-01 12:00, up = 9.60−8.55 = 1.0499999999999998 vs dn = 6.65−5.60 = 1.0500000000000007: raw `>` assigns MinusDM = 1.05, EL assigns nothing, and that single bar was the entire 2010-run seed mismatch. Identical to plain `adx` at fixed length (`ovr` = 0 on all 18,141 bars). The chain is contractive (~(13/14)^n), so the two runs collapse to bit-identical doubles ~500 bars in | `EL_ADX_Probe.txt`; `el_adx_output1/2.txt`; `el_source_wfsafe_adx.txt`, `el_source_wfsafe_dirmovement.txt`; `scripts/adx_replica.py` |
| `wfsafe_rsi` | VERIFIED | Source on file (`BacktestEngine/el_wf_safe_rsi.txt`): TS's `RSI` with `SF = 1/Length` recomputed per bar, **no re-seed on a length change** (same shape as `wfsafe_adx`). **Seeds at the study's first calculated bar** with `NetChgAvg = (Price − Price[Length])/Length` and a fresh `Average(AbsValue(Price − Price[1]), Length)`, then EMA-form updates; `WFSafe_RSI(...)[1]` reads **0 on bar 1** and the prior value after; **identical to plain `RSI` at a fixed length** (ovr 0 on all 18,161 bars). Drift 0 against an open-coded twin on **9,834/9,834** (2007 start) and **8,327/8,327** (2010 start) bars; `scripts/rsi_replica.py` replays the C++ port from the store at print precision on 9,794/9,794 and 8,287/8,287. `TotChgAvg` was never 0, so the `<> 0` guard's tolerance is unexercised | `EL_WFSafeRsi_Probe.txt`; `el_wfsafe_rsi_output1/2.txt`; `scripts/rsi_replica.py` |
| any other `wfsafe_*` | **UNKNOWN** | Assume it overrides the built-in and differs from it | — |

## Position and account built-ins

| Feature | Status | What is known | Evidence |
|---|---|---|---|
| `marketposition` | ACCEPTED | +1 / 0 / −1 | `test_strategy.cpp` `PositionStateAccessors` |
| `currentcontracts` | ACCEPTED | Total open contracts | — |
| `entryprice` | VERIFIED | Contract-weighted average; 0.0 when flat. TradeStation does **not** fold slippage into the fill price — `EntryPrice` is the entry bar's raw open | `EL_OpenPositionProfit_Probe.txt`; `test_fill_engine.cpp` `RoundTurnAtRawOpenPrices` |
| `barssinceentry` | VERIFIED | Counted from the **oldest** open lot; 0 on the bar the entry fills; restarts through a reversal; **0 while flat**, never a −1 sentinel; a pyramid keeps counting from the first lot. All four measured over 2,721 probe cycles and 13,630 flat bars | `EL_BarsSinceEntry_Probe.txt` |
| `barssinceexit` | VERIFIED | **Wants an index** — `BarsSinceExit(1)`; the bare form answers nothing. 0 on the exit's own bar, counting up from there, and **0 before any exit** (45 such bars). Measured over 5,441 exits | `EL_BarsSinceExit_Probe.txt` |
| `openpositionprofit` | VERIFIED | Close-marked, and **net of the entry side's** commission + slippage + accrued swap — one side, not the round turn. At commission 7 / slippage 3 per side it read exactly 10 below the raw price difference. Reported in account currency | `EL_OpenPositionProfit_Probe.txt`; `test_simulator.cpp` `OpenPositionProfitIsNetOfTheEntrySideCosts` |
| `maxpositionprofit` | VERIFIED | **INTRABAR** — the running peak of each bar's *favourable extreme* (high long, low short), net of the same entry-side costs. Not the peak of the close-marked `OpenPositionProfit`. Starts at 0 per position, so a never-profitable position reports 0. A reversal starts a new position; pyramiding does not. Intrabar reproduced 979/979 open bars; the close rule 29 | `EL_OrderCollision_Probe.txt`; `test_simulator.cpp` `MaxPositionProfitIsMarkedIntrabarNotAtTheClose` |
| `netprofit` | ACCEPTED | Cumulative net P&L of **closed** trades only | `MonthlyProfitTarget`; versions 8/20 agree 100% on money across 768 ranges |
| `bigpointvalue` | ACCEPTED | The raw contract multiplier, quote currency per point — **not** currency-converted, while the profit accessors are. TradeStation's own inconsistency, preserved deliberately | `CLAUDE.md` |

## Operators, control flow, order placement

`lintElFeatures.py` treats EasyLanguage's control-flow words as *syntax* and
subtracts them before looking anything up, so the rows below are documentation
rather than something the gate enforces per rule. The `and`/`or` row is still
recorded as ASSUMED because the debt is real and the whole-corpus test pins it.

| Feature | Status | What is known | Evidence |
|---|---|---|---|
| `>` `<` `>=` `<=` `=` `<>` | VERIFIED | Carry an **absolute** tolerance of 2.22e-12 — bracketed to (2.04636e-12, 2.2737e-12]. Not relative: refuted twice. The vendor docs' "2.22e-16" has the right mantissa and an exponent four out. Use `el_gt`/`el_lt`/… everywhere EL evaluates a relational operator, **including inside EL's own standard functions**, most of which are EL source | `EL_Comparison_Probe.txt`, `EL_Tolerance_Constant_Probe.txt`; reconfirmed live in `EL_HO_OpenPositionProfit_Probe.txt` (`diff` 1.5916 < 2.2204) |
| `and` `or` `not` | VERIFIED | EasyLanguage does **not** short-circuit; C++ `&&`/`\|\|` does. Measured three ways: an unguarded `close[400]` past a Max Bars Back of 50 raises, and so do `false and (close[400] > 0)` and `true or (close[400] > 0)` — EL evaluates the right operand even when the left has already decided the answer. **Two rules follow.** (1) A stateful call must never sit in a condition: a `WFSafe_` accumulator there would advance every bar in EL and only on some bars in C++, drifting apart silently and permanently — keep them in `preConditionHook`, which the generator emits unconditionally. (2) A deep subscript is reached on *every* bar however it is guarded, so Max Bars Back must cover it unconditionally, which is what `CATALOG.md`'s "reaches back" column already assumes | `EL_LogicalEval_Probe.txt` |
| `if` `then` `begin` `end` `for` `to` `true` `false` | ACCEPTED | Ordinary control flow | — |
| `buy` `sellshort` `sell` `buytocover` | VERIFIED | Fill at the **next bar's open**. **Exits apply before entries**, whatever order the statements were written in — TS resolves by order *type*, not statement order (byte-identical output with the exits emitted first). An exit and a same-direction entry on one bar close and re-open at the same fill. No-pyramiding is a **fill-time** cap, so entries are emitted **unguarded**. **From FLAT, an exit order fills against a position opened at the same open**: when an entry and an unguarded exit market order both work for the same open with no position, TS fills the entry and the exit closes it at the **same price** — a booked **$0 round turn** (costs still charged), not a suppressed entry. `EL_TimeOfDayExit_Probe.txt`: 235/235 evening entries queued alongside `Time >= TimeExit`; the TS trade list (`time_of_day_probe_HO_trades.csv`) shows all 235 as entry+exit pairs at one timestamp, entry price == exit price, $0.00; modelling it reproduces all 5,743 bars of both runs. An exit fills **at most once** — a consumed exit does not re-close a same-open re-entry, which is the close-and-re-open case above. **Unreachable in generated strategies**: both generators guard exits on `MarketPosition` at signal time (`If (ExitLong and MarketPosition = 1) Then Sell`), so neither twin places an exit while flat and the engine's exit-when-flat no-op is never exercised. It matters only when the book's RAW EasyLanguage (unguarded exits) is run against the engine | `EL_OrderCollision_Probe.txt` (98 collisions); `test_fill_engine.cpp` `ExitsApplyBeforeEntriesSoAReversalCostsOneClosedTrade`; `EL_TimeOfDayExit_Probe.txt` + `time_of_day_probe_HO_trades.csv` |

## Adding a row

A row is earned, not assumed. The loop is in
`BacktestEngine/docs/EL_VERIFICATION.md`; briefly:

1. Write a probe from `BacktestEngine/EL_Probe_Template.txt`, with its outcomes
   enumerated **before** the data arrives.
2. Brian runs it in TradeStation.
3. Record the finding here with the probe filename, and add a bullet to
   `BacktestEngine/CLAUDE.md` if it is a settled convention.
4. Lock it in a test whose comment names the probe, the symbol, the date and the
   hit counts.

**Never** downgrade a row to ACCEPTED to unblock authoring. UNKNOWN is the honest
answer and the gate exists to make it expensive to ignore.
