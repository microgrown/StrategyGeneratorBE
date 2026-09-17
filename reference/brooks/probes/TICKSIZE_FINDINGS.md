# TickSize probe findings

Source probe: `C:\Users\brian\source\repos\BacktestEngine\EL_TickSize_Probe.txt`.
Outputs read: `el_ticksize_output1.txt` (RunTag 1, @ES 60min), `el_ticksize_output3.txt`
(RunTag 3, @HO 60min), `el_ticksize_output4.txt` (RunTag 4, @OJ 240min). RunTag 2
(MSFT Daily, the stock case) was **not run**; see "What MSFT would add" below.

## 1. Results table (filled from the outputs)

| run | symbol | mm | ps | tick | bpv | dtick | mind |
|---|---|---|---|---|---|---|---|
| 1 | @ES | 25 | 100 | 0.250000000000 | 50 | 12.500000 | 0.250000000000 |
| 2 | MSFT | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| 3 | @HO | 1 | 10000 | 0.000100000000 | 42000 | 4.200000 | 0.000100000000 |
| 4 | @OJ | 5 | 100 | 0.050000000000 | 150 | 7.500000 | 0.050000000000 |

`pv` (PointValue) also printed and compiled on all three charts: ES pv=0.5000,
HO pv=4.2000, OJ pv=1.5000. In each case `pv = bpv / ps`, not `bpv` -- see
question 3 below.

`ordres` (the four-tick operand-order residual) printed `0.0000` on every line
of all three charts, @OJ's non-dyadic 0.05 tick included.

## 2. Every pre-registered question, answered with the proving lines

**Registry agreement, checked first per the probe's instruction.** All three
measured (mm, ps, dtick) triples match the pre-registered predictions and the
`symbols/*.json` specs exactly:

- ES: predicted tick 0.25 / bpv 50 / dtick 12.50. Measured `tick=0.250000000000
  bpv= 50.0000 dtick= 12.500000` (output1, bar=1 and every later line).
  `symbols/ES.json` says `tick_size: "0.25"`, `big_point_value: 50` -- agrees.
- HO: predicted tick 0.0001 / bpv 42000 / dtick 4.20. Measured
  `tick=0.000100000000 bpv=42000.0000 dtick=  4.200000` (output3, bar=1 and
  every later line). `symbols/HO.json` says `tick_size: "0.0001"`,
  `big_point_value: 42000` -- agrees.
- OJ: predicted tick 0.05 / bpv 150 / dtick 7.50. Measured
  `tick=0.050000000000 bpv=  150.0000 dtick=  7.500000` (output4, bar=1 and
  every later line). `symbols/OJ.json` says `tick_size: "0.05"`,
  `big_point_value: 150` -- agrees.

**No registry defect found.** The measured tick, bpv and dtick agree with
`symbols/ES.json`, `symbols/HO.json` and `symbols/OJ.json` on all three
futures charts run.

- **Did mm/ps change mid-chart anywhere? (dates)**
  No. Grepping `chg=1` (the study's own change flag, computed as
  `CurrentBar = 1 or MM <> MM[1] or PS <> PS[1] or BPV <> BPV[1]`) against each
  output file returns exactly **one** line per chart -- the bar=1
  initialization line -- and none thereafter:
  - output1: `run=1 sym=@ES bar=      1 ... chg=1 ...` is the only `chg=1` line
    in 232 lines spanning bar 1 to bar 115391 (2015 -> 2026).
  - output3: `run=3 sym=@HO bar=      1 ... chg=1 ...` is the only `chg=1` line
    in 228 lines spanning bar 1 to bar 113455 (2007 -> 2026).
  - output4: `run=4 sym=@OJ bar=      1 ... chg=1 ...` is the only `chg=1` line
    in 21 lines spanning bar 1 to bar 9646 (2007 -> 2026).
  Every heartbeat (every 500 bars) and every last-bar line repeats the same
  mm/ps/bpv as bar 1 on all three charts, including across the back-adjusted
  continuous @ES and @HO series over an 11-19 year span that necessarily
  contains multiple contract rolls. **MinMove and PriceScale are per-symbol
  constants on these three charts; they do not track contract rolls.**

- **MinMove / PriceScale really is the tick (independent cross-check)?**
  Yes on all three. `mind` (smallest non-zero `|Close - Close[1]|` seen,
  computed without touching MinMove/PriceScale) equals `tick` exactly by the
  last bar of each chart:
  - ES: `mind=0.250000000000` vs `tick=0.250000000000` (output1, last line,
    bar=115391).
  - HO: `mind=0.000100000000` vs `tick=0.000100000000` (output3, last line,
    bar=113455).
  - OJ: `mind=0.050000000000` vs `tick=0.050000000000` (output4, last line,
    bar=9646).
  No line on any chart shows `mind < tick` (which would mean off-grid prices)
  and every chart eventually reaches `mind == tick` (so the cross-check
  actually ran on all three, not just "never saw a one-tick move").

- **The operand-order residual on the non-dyadic OJ tick.**
  `ordres = ( 4*(MM/PS) - (4*MM)/PS ) * 1e15` prints `0.0000` on **every**
  line of output4 (@OJ, mm=5, ps=100 -> tick=0.05), and also on every line of
  output1 (ES, dyadic 0.25 tick, expected trivial zero) and output3 (HO,
  mm=1/ps=10000). The two operand orders for a four-tick margin are
  bit-identical for all three symbols actually measured -- **the residual the
  probe was designed to catch does not appear on any chart that was run.**
  This does not settle the question for every tick in the registry (a stock's
  0.01 tick was the other candidate named in the probe, and it was not run --
  see below), but for ES, HO and OJ specifically, either operand order
  produces the same double.

- **PointValue vs BigPointValue.**
  `PointValue` compiled on all three charts (the `pv` field was not deleted).
  `pv != bpv` on every chart: ES `pv=0.5000` vs `bpv=50.0000`; HO
  `pv=4.2000` vs `bpv=42000.0000`; OJ `pv=1.5000` vs `bpv=150.0000`. In every
  case `pv = bpv / ps` (ES: 50/100=0.5; HO: 42000/10000=4.2; OJ: 150/100=1.5)
  -- i.e. `PointValue` is currency per one *PriceScale unit* (the smallest
  representable price increment, `1/PriceScale`), while `BigPointValue` is
  currency per whole price point (1.00). They are two different quantities,
  not synonyms, and the corpus/registry must be explicit about which one a
  rule means. (Neither equals `dtick`, currency per *tick*, except by
  coincidence -- `dtick = bpv * mm/ps = pv * mm`.)

- **Run 3 sanity check: is dtick exactly 4.20?**
  Yes. `dtick=  4.200000` on every printed line of output3, including bar=1
  and the last bar (113455). Sanity check passed -- the rest of the probe's
  readings can be trusted.

- **MultiWalk portfolio: one symbol per unit, or many?**
  Not settled by this probe. The three runs were single-symbol INDICATOR
  runs (per the probe's own SETUP section), so there is no MultiWalk
  portfolio unit in play here at all. This question remains open and needs a
  separate MultiWalk-specific probe if/when a portfolio run mixes symbols
  per unit; today's run specs are one-symbol-per-unit, so the question is
  moot for the current corpus but not proven in general.

## 3. Exact replacement text for the `rules/EL_FEATURES.md` register rows

(Not applied to the file per instructions -- `rules/EL_FEATURES.md` is not to
be edited. Exact text below, same column layout: `| Feature | Status | What is
known | Evidence |`.)

```
| `minmove` | VERIFIED | Tick size is `MinMove / PriceScale`. Measured on three futures charts (@ES 60min, @HO 60min, @OJ 240min, 2007/2015->2026): MinMove and PriceScale are per-symbol constants that never changed mid-run -- exactly one `chg=1` print per chart (the bar-1 initialization), none on any later bar including across back-adjusted continuous-contract rolls. `MinMove/PriceScale` matches the independent smallest-nonzero-close-change cross-check exactly on all three (mind == tick by the last bar in every case). `marginTicks * (MinMove/PriceScale)` and `(marginTicks * MinMove)/PriceScale` were bit-identical (residual 0) on all three charts, including @OJ's non-dyadic 0.05 tick -- so for the symbols measured, either operand order is safe, though the C++ should still write division-first to match the merged pseudocode. **UNMEASURED: the stock case** (0.01 tick, BigPointValue 1) -- RunTag 2 (MSFT Daily) in the probe was not run. The engine still exposes no tick size to strategies (`ctx` has only `BigPointValue()`, `strategy.h:183`; `PriceSeries` carries only `price_decimals`/`big_point_value`; `SymbolSpec::tick_size`, `symbol.h:126`, never reaches the simulator) -- this row still gates the new `ctx` accessor, which the measurements say can be read once per symbol/run rather than per bar | `EL_TickSize_Probe.txt`; `el_ticksize_output1.txt`, `el_ticksize_output3.txt`, `el_ticksize_output4.txt` |
| `pricescale` | VERIFIED | The denominator of the tick, same probe and same three futures charts as `minmove`. Cross-check `BigPointValue * (MinMove/PriceScale)` = currency per tick confirmed exactly: @HO printed `dtick=4.200000` on every line (the probe's pre-registered sanity line), @ES `dtick=12.500000`, @OJ `dtick=7.500000`, all matching the registry's `tick_size`/`big_point_value` for those symbols with no disagreement. `PointValue` also compiles and is NOT a synonym for `BigPointValue`: measured `PointValue = BigPointValue / PriceScale` (currency per one PriceScale unit, i.e. per `1/PriceScale` of a point) on all three charts (ES 0.5 vs bpv 50; HO 4.2 vs bpv 42000; OJ 1.5 vs bpv 150) -- a rule reaching for "point value" must say which of `BigPointValue`, `PointValue`, or `dtick` (currency per tick) it means. **UNMEASURED: the stock case** (MSFT, RunTag 2, not run) | `EL_TickSize_Probe.txt`; `el_ticksize_output1.txt`, `el_ticksize_output3.txt`, `el_ticksize_output4.txt` |
```

## 4. Engine implication

**Landed 2026-09-17 (engine 7d8d6db):** `ctx.MinMove()`, `ctx.PriceScale()`, `ctx.TickSize()` on the strategy Context, read once per symbol; the C++ idiom is `ticks * (ctx.MinMove() / ctx.PriceScale())`. The rows files that recorded ticks-to-points conversions made before this (`rows/02_bar.md`, `05_bar.md`, `14_misc.md`) stay as history; the affected rules were authored in price/ATR units and were not re-decided.

The measurements answer the accessor-shape question the probe was gating:
on all three futures charts run -- including two back-adjusted continuous
contracts (@ES, @HO) spanning 11-19 years, which necessarily cross multiple
contract rolls -- MinMove, PriceScale and BigPointValue never changed after
the bar-1 initialization print. That means **a tick-size accessor can be read
once per symbol (equivalently, once per run, since these run specs are one
symbol per unit) rather than re-read per bar.** The C++ needs a new
`ctx.TickSize()` (or paired `ctx.MinMove()`/`ctx.PriceScale()`) accessor
plumbed from `SymbolSpec::tick_size` (`symbol.h:126`) through `PriceSeries`
into `bt::Context`, initialized once and cached for the run -- no per-bar
re-read logic is required by anything measured here.

Two caveats on that conclusion, both explicit in the probe and neither closed
by this run: (1) the MultiWalk portfolio question (section 2, last bullet) was
not exercised -- if a future portfolio spec ever lets one unit trade more than
one instrument, "once per symbol" would need to become "once per unit per
active symbol," not "once per run"; today's run specs are one-symbol-per-unit
so this does not block current authoring. (2) only futures were measured; see
below for what the stock run would still need to confirm.

**Exact expression for "N ticks" in EL, for the twins to mirror:** the merged
Brooks pseudocode and this probe both write division first --

```
N * (MinMove / PriceScale)
```

and the operand-order residual (`ordres`) measured **zero** on every line of
all three charts, including @OJ's non-dyadic 0.05 tick (mm=5, ps=100) which
was the one case pre-registered as capable of showing a non-zero residual.
So for ES, HO and OJ specifically, the C++ may compute the margin in either
operand order and get a bit-identical result to EL -- but since the merged
pseudocode already standardizes on division-first and no chart penalizes it,
the C++ should still write `N * (MinMove / PriceScale)` (division first) for
consistency with the corpus and in case a not-yet-measured tick (a stock's
0.01, or another future's tick not in this run) does show a non-zero residual.

## What the missing MSFT run leaves open

RunTag 2 (MSFT Daily) was pre-registered specifically to see how `MinMove`/
`PriceScale`/`BigPointValue` describe an instrument with a 0.01 tick and
`BigPointValue` 1 (a stock), which is the other case besides @OJ that could
show a non-zero operand-order residual. Without it, open questions are:

- Whether a 0.01-tick, BigPointValue-1 instrument shows the same "constant
  for the whole run, no mid-chart changes" behavior as the three futures
  measured, or whether stocks (which can split, unlike the futures measured)
  ever change MinMove/PriceScale mid-series.
- Whether the operand-order residual is truly always zero for a 0.01 tick, or
  whether OJ's 0.05 tick happened to be the one exact case among "nice"
  decimal ticks and 0.01 differs. (5/100 and 1/100 are both simple fractions
  in double, so a priori there is no strong reason to expect a different
  result, but it is unmeasured.)
- Whether `PointValue = BigPointValue / PriceScale` continues to hold for
  `BigPointValue = 1` (predicted: `pv = 1/100 = 0.01`), which would confirm
  the relationship found here is general rather than an artifact of the three
  large-multiplier futures contracts measured.

**Does this matter for futures-only authoring?** No. `symbols/*.json` (the
corpus's registry) contains only futures and FX -- "There is no stock in the
registry -- the corpus trades futures and FX only" (probe, WHY THIS EXISTS
section) -- so the 49 Brooks candidate rules that measure a margin in ticks
are only ever placed against futures/FX symbols. Every conclusion this
document draws (constants for the run, mind==tick, ordres==0, the `ctx`
accessor can be read once per symbol) is already established on the symbol
class the corpus actually uses. The MSFT run remains useful as a general
confirmation that the relationships found here (tick = mm/ps, dtick =
bpv*tick, pv = bpv/ps) are not artifacts specific to large-multiplier futures
contracts, and should still be run before this row is treated as fully
general -- but it does not block authoring the 49 futures/FX rules today.
