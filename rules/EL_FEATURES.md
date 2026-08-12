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
| `time` | ACCEPTED | Bar **close** timestamp, exchange time, no timezone conversion anywhere in the engine | Ingest validates bars inside the session window; `CLAUDE.md` |
| `date` | **ASSUMED** | EL `Date` is the bar's date; the engine derives it from the bar's **close** timestamp. On an overnight session those are not the same day, and `MonthlyProfitTarget` — a live rule — pivots on the month boundary. Never measured | — probe warranted |
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
| `maxlist` `minlist` | **UNKNOWN** | **Not EL source**, so whether they carry the relational tolerance is unestablished. Inert in the corpus today only because `AtrProfitTarget`'s stand-in loop compares tick-grid prices that differ by zero or by ≥1 tick — 1e9–1e11× the tolerance | `el_compare.h` says so explicitly |
| `mod` | **UNKNOWN** | Sign behaviour on **negative** operands differs between C++ `%`, `std::fmod` and EL's `Mod`, and nothing has measured which EL follows | — |

## MultiWalk overrides

A `WFSafe_` wrapper is a **different function** from the EL built-in it
resembles, and it wins. Where MultiWalk provides no override, follow plain EL.

| Feature | Status | What is known | Evidence |
|---|---|---|---|
| `wfsafe_avgtruerange` | VERIFIED | A **rolling accumulator**, not a fresh mean: seeded with a full N-term sum on the study's first calculated bar (MaxBarsBack + 1), then `S = S[1] + value − value[Length]`, re-seeding when the length changes. The update is **two statements** — EL evaluates left to right, and folding to `S += in − out` rounds differently and lands on the other side of a threshold | `EL_WFSafeAtr_Probe.txt`, `EL_WFSafeSeed_Probe.txt`; `EL_HO_WFSafeAtr_Probe.txt` reproduces TradeStation on **112,705/112,705** bars |
| `wfsafe_summationfc` | **UNKNOWN** | Named in MultiWalk's library and presumed to share the rolling/re-seeding shape, but never measured | — |
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
| `and` `or` `not` | **ASSUMED** | EasyLanguage is believed **not** to short-circuit, where C++ `&&`/`\|\|` does — never measured. Two consequences if true: a stateful call inside a condition would advance in EL and be skipped in C++ (inert today *only because* every accumulator lives in `preConditionHook`, which runs unconditionally); and `MomentumChange`'s `not (close[1] > close[lookback+1])` would evaluate its right operand in EL even when the left already decided, so a subscript past Max Bars Back raises in EL where C++ skips it | — probe warranted |
| `if` `then` `begin` `end` `for` `to` `true` `false` | ACCEPTED | Ordinary control flow | — |
| `buy` `sellshort` `sell` `buytocover` | VERIFIED | Fill at the **next bar's open**. **Exits apply before entries**, whatever order the statements were written in — TS resolves by order *type*, not statement order (byte-identical output with the exits emitted first). An exit and a same-direction entry on one bar close and re-open at the same fill. No-pyramiding is a **fill-time** cap, so entries are emitted **unguarded** | `EL_OrderCollision_Probe.txt` (98 collisions); `test_fill_engine.cpp` `ExitsApplyBeforeEntriesSoAReversalCostsOneClosedTrade` |

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
