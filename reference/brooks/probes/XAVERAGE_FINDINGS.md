# XAverage probe findings

Source probe: `C:\Users\brian\source\repos\BacktestEngine\EL_XAverage_Probe.txt`.
Outputs read: `el_xaverage_output4.txt` (chart 4 = **RunTag 1**, @OJ 240min,
chart start 01/01/2007, 9,646 printed bars) and `el_xaverage_output5.txt`
(chart 5 = **RunTag 2**, same symbol/interval, chart start 01/01/2010, 8,139
printed bars). Both runs end on the same bar, 1260902 14:00.

**Headline: every pre-registered question the probe could ask was answered, and
all four answers are the "clean" branch.** `WFSafe_Xaverage` **exists and
compiles** (Brian's spelling; EasyLanguage is case-insensitive, so the probe's
`WFSafe_XAverage` resolved to it), and it is **bit-identical to the plain
built-in at a fixed length** -- `ovr = 0.0000` on all 9,646 + 8,139 = 17,785
bars. `XAverage` **seeds with the PRICE on the study's first calculated bar**,
runs the **`X[1] + SF*(P - X[1])`** recurrence, has **no warm-up hole**, and its
seed memory decays out in **~330 bars**.

Two things the probe asked for are **not in the outputs and remain open**: the
full `WFSafe_` library listing, and anything about a *length change*. A third
question the probe did not think to ask -- what `XAverage(Close, 20)[k]` reads
at a lag -- turns out to gate 9 of the 14 blocked rules. See sections 5 and 6.

## 1. Results table (filled from the outputs)

| question | run 1 (2007 start) | run 2 (2010 start) |
|---|---|---|
| sf as printed | `0.095238095238095` on every one of 9,646 bars | `0.095238095238095` on every one of 8,139 bars |
| xa on bar 1 | `28.800000000000` | `17.450000000000` |
| Close on bar 1 | `28.800000` | `17.450000` |
| d1 on bar 1 / bar 2 / bar 100 | `0.0000` / `0.0000` / `0.0000` -- and `0.0000` on **all 9,646** bars | `0.0000` / `0.0000` / `0.0000` -- and `0.0000` on **all 8,139** bars |
| d2 on bar 100 | `-34468749.2593` (= -3.45e-05) | `-77783181.4904` (= -7.78e-05) |
| d3, typical magnitude past bar 100 | non-zero on 6,437 / 9,546 bars (67.4%); values are exact multiples of `3.5527` (2^-48); mean abs when non-zero `19.34`; max `170.5303` (bar 8267) | non-zero on 5,329 / 8,039 bars (66.3%); same 2^-48 quantum; mean abs when non-zero `22.43`; max `170.5303` (bar 6760) |
| largest \|ovr\| anywhere | `0.0000` (exact, all 9,646 bars) | `0.0000` (exact, all 8,139 bars) |
| first bar where xa is non-zero | bar **1**; `xa` is never 0 on any bar | bar **1**; `xa` is never 0 on any bar |

| question | answer |
|---|---|
| does WFSafe_XAverage compile? | **Yes.** Brian confirms the library spells it `WFSafe_Xaverage`; EL is case-insensitive so the probe's `WFSafe_XAverage` bound to it, and the `wf=` field printed a real number on every line of both runs. Per the register's standing "MultiWalk overrides" rule, **`wfsafe_xaverage` is therefore the gold standard and plain `xaverage` is the cross-check column** -- and at this fixed length the two are the same function numerically. |
| full list of WFSafe_ functions in the library | **NOT REPORTED.** The outputs are per-bar prints only; no library listing came back with them, and there is no new file in the engine repo carrying one. Six are now known: the five already on file (`WFSafe_AvgTrueRange`, `WFSafe_ADX`, `WFSafe_DirMovement`, `WFSafe_RSI`, `WFSafe_SummationFC`) plus `WFSafe_Xaverage`. The register's catch-all row still has to assume any other one exists and differs. **Open.** |
| roughly where do runs 1 and 2 agree bit-exactly | At **run-2 bar 331 = 1110228 12:00 = run-1 bar 1838**, and every one of the 7,809 shared bars after it. 306 of the 8,139 shared bars differ; the gap decays as (1-SF)^n exactly as pre-registered. |

Cross-run decay, measured on shared date/time bars (run-1 `xa` minus run-2 `xa`):

| run-2 bar | date/time | run-1 xa | run-2 xa | difference |
|---|---|---|---|---|
| 1 | 1100702 12:00 | 12.042943522096 | 17.450000000000 | -5.407e+00 |
| 10 | 1100709 14:00 | 10.716704802593 | 12.913399298604 | -2.197e+00 |
| 50 | 1100806 14:00 | 12.803922517361 | 12.844022290037 | -4.010e-02 |
| 100 | 1100913 14:00 | 6.239693064937 | 6.239962129945 | -2.691e-04 |
| 150 | 1101018 14:00 | 13.963130808870 | 13.963132614267 | -1.805e-06 |
| 200 | 1101122 14:00 | 18.388757298421 | 18.388757310535 | -1.211e-08 |
| 250 | 1101229 14:00 | 30.343897185942 | 30.343897186023 | -8.100e-11 |
| 300 | 1110203 14:00 | 40.212898481716 | 40.212898481717 | -9.948e-13 |
| 331 | 1110228 12:00 | 46.423481682524 | 46.423481682524 | 0 (and every bar after) |

(1 - 2/21)^100 = 4.5e-05, and 5.407 x 4.5e-05 = 2.4e-04 against the measured
2.69e-04 at bar 100. The chain is contractive at exactly the rate the probe
pre-registered.

## 2. Every pre-registered question, answered with the proving lines

### Q1 / Q2 -- the seed: **the PRICE, on the study's first calculated bar**

The pre-registered criterion was "d1 = 0 (or a few units at 1e15) from the
FIRST printed bar onward -> XAverage seeds with the PRICE at the study's first
calculated bar." That is what happened, at the *strongest* possible strength:
d1 is **exactly** `0.0000` on every bar of both runs, not "a few units."

```
run=1 bar=     1 date=1070703 time= 1200 c=28.800000 sf=0.095238095238095 xa=28.800000000000 wf=28.800000000000 ovr=0.0000 d1=0.0000 d2=28800000000000.0000 d3=0.0000
run=2 bar=     1 date=1100702 time= 1200 c=17.450000 sf=0.095238095238095 xa=17.450000000000 wf=17.450000000000 ovr=0.0000 d1=0.0000 d2=17450000000000.0000 d3=0.0000
```

`xa` on bar 1 **is** the close on bar 1, to all twelve printed decimals, in both
runs at two completely different price levels (28.80 and 17.45). Counted:
`d1=0.0000` on 9,646 of 9,646 lines of output4 and 8,139 of 8,139 lines of
output5. **TradeStation's XAverage source is what we thought it was:
`if CurrentBar <= 1 then XAverage = Price`.**

The textbook alternative is refuted, and not marginally. `d2` (`xa` minus a twin
seeded with a fresh 20-term simple average at bar 20) is the whole value of `xa`
before bar 20 -- the textbook twin is 0 there -- and is still **-3.4e-05** at
bar 100:

```
run=1 bar=   100 date=1070912 time= 1400 c=22.050000 ... xa=16.724887915964 ... d1=0.0000 d2=-34468749.2593 d3=3.5527
run=2 bar=   100 date=1100913 time= 1400 c=10.350000 ... xa=6.239962129945  ... d1=0.0000 d2=-77783181.4904 d3=0.0000
```

The two models only coincide (`d2` reaching an exact `0.0000`, i.e. below 5e-17)
at **bar 334** in run 1 and **bar 382** in run 2:

```
run=1 bar=   333 ... xa=25.965222263561 ... d2=-0.0036 d3=-7.1054
run=1 bar=   334 ... xa=26.211391571794 ... d2= 0.0000 d3=-3.5527
run=2 bar=   381 ... xa=35.550923372302 ... d2=-0.0071 d3=-14.2109
run=2 bar=   382 ... xa=35.831787813036 ... d2= 0.0000 d3=-7.1054
```

**Which "first bar" (Q2): MaxBarsBack + 1, confirmed by the dates.** Both charts
were started on 01/01 with Max Bars Back 250. Run 1's `bar=1` is dated 1070703
and run 2's `bar=1` is dated 1100702 -- roughly six months of @OJ 240min bars
(2 bars/day, ~125 trading days) after each chart start. The function's
`CurrentBar` is the study's `CurrentBar`, and the seed lands on the first bar
`OnBarClose` runs, exactly as the `currentbar` register row and the `WFSafe_`
accumulator probes have it. The seed bar therefore moves with **both** Max Bars
Back and the chart start.

**Seed memory (Q2, the two-run comparison): contractive, ~330 bars.** The two
runs are 5.407 apart on the later run's first bar and agree to all twelve
printed decimals from run-2 bar **331** (1110228 12:00) onward -- 306 of 8,139
shared bars differ, none after that point. The last disagreeing bar is one unit
in the last place:

```
run=1 bar=  1837 date=1110225 time= 1400 c=52.000000 ... xa=46.373321859631 ...
run=2 bar=   330 date=1110225 time= 1400 c=52.000000 ... xa=46.373321859632 ...
run=1 bar=  1838 date=1110228 time= 1200 c=46.900000 ... xa=46.423481682524 ...
run=2 bar=   331 date=1110228 time= 1200 c=46.900000 ... xa=46.423481682524 ...
```

*Honest limit on this one:* `xa` is printed at 12 decimals, so what is
demonstrated is agreement at print precision, not provably bit-for-bit. The
intra-run `d2` column is the better witness for true bit convergence, because it
is a printed *difference* at 1e-16 resolution, and it reaches an exact zero at
bar 334 / 382 from a seed error of 0.103. Both numbers say the same thing:
**a mirror that gets the seed bar slightly wrong self-heals within roughly
330-380 bars, and is materially wrong before that.** This matches
`wfsafe_adx`'s "~500 bars" finding in shape and beats it in speed, as the faster
decay rate ((1-2/21)^n vs ~(13/14)^n) predicts.

### Q3 -- the recurrence form: **`X[1] + SF*(P - X[1])`, and the forms do differ**

The pre-registered branch "d3 != 0 on most bars, and d1 = 0 -> the forms
genuinely differ AND XAverage uses the `X[1] + SF*(P - X[1])` form" is the one
that fired. The probe's own sanity check ("d3 must be NON-ZERO on most bars")
passed: d3 is non-zero on **67.4%** of run-1 bars past 100 and **66.3%** of
run-2 bars, so the non-dyadic 0.05 tick did its job and the precision half of
the probe exercised something real.

The magnitudes are exact multiples of `3.5527` at 1e-15 scale, i.e. 2^-48 --
1 to 4 ULP at @OJ's price levels. The largest seen in either run:

```
run=1 bar=  8267 date=1231130 time= 1400 c=361.050000 ... xa=366.218386048466 ... d1=0.0000 d2=0.0000 d3=-170.5303
```

That is 1.7e-13, which is an order of magnitude **inside** EasyLanguage's
2.22e-12 relational tolerance -- so choosing the wrong recurrence form would
not, on its own, flip a bare `close > ema` test. It would still flip a chained
one (an EMA difference divided by a small slope lookback, as in
`BuyLimitBelowRisingMA`, or an EMA fed into a `lowest()` window), and there is
no reason to accept the risk: **d1 = 0 everywhere says EL's form is
`X[1] + SF*(P - X[1])`, so write that, statement for statement, the way
`AtrProfitTarget`'s accumulator had to be.**

### Q4 -- warm-up: **no hole; the recurrence just runs from the seed**

The pre-registered branch "xa on bar 1 equals Close on bar 1" fired, and its
alternative ("xa = 0 on any early bar") did not: **`xa` is non-zero on bar 1 and
on every one of the 17,785 bars printed across both runs.** There is no
sentinel, no zero, and no `Length`-bar dead zone. A rule that gates an entry on
the EMA at bar 5 of a run gets a real number -- just not yet a 20-bar average.

Note the contrast with the textbook twin, which *does* have a hole: `EmaAvg` is
0 on bars 1..19 (that is why `d2` on bar 1 is the full 28.8). **Our mirror must
have XAverage's behaviour, not the twin's** -- no `if (CurrentBar < n) return 0`
guard.

### Q5 -- the override: **`WFSafe_Xaverage` exists and is identical at fixed length**

`ovr = (wf - xa) * 1e12` printed **`0.0000` on all 9,646 lines of output4 and
all 8,139 lines of output5**, and the `wf=` and `xa=` fields are
character-for-character identical on every one of those 17,785 lines. The
pre-registered branch is "ovr = 0 on every bar -> the wrapper is identical to
the built-in AT A FIXED LENGTH, same as wfsafe_adx and wfsafe_rsi. Both rows
then say the same thing, and the MW twin may call either."

So the finding is exactly the `wfsafe_adx` / `wfsafe_rsi` finding, a third time:
**the WFSafe_ wrapper's difference from the built-in is invisible at a fixed
length and lives entirely in what happens when a walkforward changes the
length.** The C++ mirror therefore does not have to choose between the two -- at
a fixed `emaLength` there is nothing to choose. It also means we did **not**
have to escalate: the probe's "STOP: I need its source" branch (`ovr != 0`) did
not fire, so authoring is not blocked on obtaining `WFSafe_Xaverage`'s source.

**What this does NOT settle**, and the probe said so in advance: the
length-change behaviour, which is the entire reason the wrapper exists. A
fixed-input chart cannot exercise it. By analogy with the two wrappers whose
source we hold, the expectation is SF recomputed every bar and **no re-seed**
(the `wfsafe_adx`/`wfsafe_rsi` shape, not `wfsafe_avgtruerange`'s) -- an EMA has
no window to re-seed. That remains an expectation, not a measurement.

## 3. Exact replacement text for the `rules/EL_FEATURES.md` register rows

(Not applied -- `rules/EL_FEATURES.md` is the orchestrator's to edit. Same
column layout in both sections: `| Feature | Status | What is known | Evidence |`.)

Replacement for the `xaverage` row in **## Standard functions**:

```
| `xaverage` | VERIFIED | `XAverage(Price, Length)`. **Seeds with the PRICE on the study's first calculated bar** (`CurrentBar` = 1 = MaxBarsBack + 1), not a Length-term simple average: measured `xa == Close` on bar 1 of both runs (28.80 and 17.45) and a price-seeded twin matched on **9,646/9,646 and 8,139/8,139 bars** (`d1` exactly 0 everywhere), while the textbook simple-average-at-bar-`Length` twin was still 3.4e-05 off at bar 100 and did not coincide until bar 334 / 382. **Recurrence form is `X[1] + SF*(P − X[1])`, not `SF*P + (1−SF)*X[1]`** — the two separate on 67% of bars past 100 (exact multiples of 2^-48, max 1.7e-13 at @OJ, which is inside the 2.22e-12 relational tolerance for a bare `close > ema` but not for a chained use), and XAverage tracks the first form bit for bit. `SF = 2/(Length+1)` printed `0.095238095238095` at Length 20 on every bar rather than being assumed. **No warm-up hole**: non-zero from bar 1 (the seed) on all 17,785 bars — a rule reading the EMA early gets a number, not a sentinel or a zero. An EMA never forgets its seed, so Max Bars Back and the chart start are part of the specification of every EMA rule: two runs 5.41 apart at the later start's bar 1 decay to 2.7e-04 by bar 100, 8.1e-11 by 250, and are identical at print precision from bar 331 on (~330 bars of memory, the (1−SF)^n rate). **Identical to `wfsafe_xaverage` at a fixed length** (`ovr` = 0 on all 17,785 bars); MW strategies call `wfsafe_xaverage`, which is the row rules are held to. **UNMEASURED: what `XAverage(...)[k]` returns at a lag** (the probe printed only the current value; `WFSafe_RSI(...)[1]` measured 0 on bar 1, but that is a different function) **and the length-change behaviour** | `EL_XAverage_Probe.txt`; `el_xaverage_output4.txt`, `el_xaverage_output5.txt` |
```

Replacement for the `wfsafe_xaverage` row in **## MultiWalk overrides**:

```
| `wfsafe_xaverage` | VERIFIED | **It exists** — the library spells it `WFSafe_Xaverage`; EL being case-insensitive, the probe's `WFSafe_XAverage` compiled and printed on every bar. Per the section rule it is the gold standard and plain `xaverage` is only the cross-check column — and **at a fixed length the two are the same number**: `ovr = (wf − xa) * 1e12` printed exactly `0.0000` on all 9,646 (2007 start) and 8,139 (2010 start) bars of @OJ 240min, with the `wf` and `xa` fields character-identical on all 17,785. Same result as `wfsafe_adx` and `wfsafe_rsi`, so the verified model is `xaverage`'s in full: price seed on the study's first calculated bar (MaxBarsBack + 1), `X[1] + SF*(P − X[1])`, SF = 2/(Length+1), no warm-up hole, ~330 bars of seed memory. **UNMEASURED, and it is the reason the wrapper exists: the length-change behaviour.** A fixed-input chart cannot exercise it; by analogy with the two wrappers whose source we hold (`el_wf_safe_rsi.txt`, `el_source_wfsafe_adx.txt` — "SF was only initialized when the function is loaded ... if Length changes, it is ignored") the expectation is SF recomputed per bar and **no re-seed** (the `wfsafe_adx`/`wfsafe_rsi` shape, not `wfsafe_avgtruerange`'s — an EMA has no window to re-seed), but a walkforward that re-optimizes `emaLength` has not been measured. **Pin `emaLength` in the grid until it is.** The wrapper's source is NOT on file and was not needed: the probe's `ovr != 0` escalation branch did not fire. Also unmeasured, shared with `xaverage`: the lagged read `WFSafe_Xaverage(...)[k]` | `EL_XAverage_Probe.txt`; `el_xaverage_output4.txt`, `el_xaverage_output5.txt` |
```

Two notes for the orchestrator applying these:

- The `adx` row's phrasing ("Identical to `wfsafe_adx` ... MW strategies call
  `wfsafe_adx`, which is the row rules are held to") is the model, and the
  `xaverage` row above copies it.
- Both rows are proposed **VERIFIED with the unmeasured items named in-row**,
  the way the `minmove` row carries "**UNMEASURED: the stock case**". The gate
  is per-row and cannot enforce a caveat inside a VERIFIED row -- so the lag
  caveat has to be enforced by the authoring pass (section 6), which is exactly
  the limitation `docs/EL_VERIFICATION.md` describes under "What the gate does
  and does not catch."

## 4. The C++ mirror for `ema(close, n)[k]`

To be pasted as the `preConditionHook` comment + body of the first EMA rule
authored, in the style of `rules/AtrProfitTarget.json`'s rolling-accumulator
comment. `localVariables`: `emaVal` (double, `0.0`); plus the `classMembersHook`
ring below if the rule reads a lag.

```cpp
// MultiWalk's WFSafe_Xaverage -- which measured BIT-IDENTICAL to the plain
// XAverage built-in at a fixed length: ovr = (wf - xa) * 1e12 printed exactly
// 0.0000 on all 9,646 + 8,139 bars of EL_XAverage_Probe.txt (@OJ 240min, chart
// starts 2007 and 2010). At a fixed emaLength there is nothing to choose
// between the two; the wrapper's difference lives only in a walkforward length
// change, which is UNMEASURED (see below).
//
// SEED: the PRICE on the study's first calculated bar -- NOT a Length-term
// simple average, which is what most textbooks and most other platforms do.
// Measured: xa == Close on bar 1 of both runs (28.800000000000 and
// 17.450000000000), and a price-seeded twin matched on 9,646/9,646 and
// 8,139/8,139 bars (d1 exactly 0 everywhere). The simple-average twin was
// -3.4e-05 off at bar 100 and did not coincide until bar 334 / 382.
//
// An EMA NEVER FORGETS ITS SEED -- unlike wfsafe_avgtruerange's rolling window
// there is no bar at which the seed drops out of the sum; it only decays at
// (1 - SF)^n. So the seed BAR is part of the spec: it is MaxBarsBack + 1, the
// first bar OnBarClose runs, i.e. ctx.CurrentBar() == 1 -- the same seed bar
// EL_WFSafeSeed_Probe.txt pinned for the rolling accumulator. Measured decay
// between the two chart starts: 5.41 apart at the later run's bar 1, 2.7e-04
// at bar 100, 8.1e-11 at bar 250, identical at print precision from bar 331.
// A mirror that seeds one bar off self-heals in ~330 bars and is materially
// wrong before that.
//
// ONE STATEMENT, IN EL'S FORM. X[1] + SF*(P - X[1]) and SF*P + (1-SF)*X[1] are
// algebraically identical and NOT identical in floating point: the probe's d3
// column separated them on 67% of bars past 100 (exact multiples of 2^-48, up
// to 1.7e-13), and XAverage tracked the first form on every bar. Do not
// re-associate this, for the same reason AtrProfitTarget's accumulator is two
// statements rather than one.
//
// NO WARM-UP HOLE. xa is non-zero from bar 1 (the seed) on all 17,785 probed
// bars -- no 0, no sentinel, no Length-bar dead zone. A rule that gates an
// entry on bar 5 of a run gets a real number that is simply not yet a 20-bar
// average. Do NOT add an `if (CurrentBar < n) return 0` guard: that is the
// textbook twin's behaviour, not EasyLanguage's.
//
// UNMEASURED, both named in the register rows:
//   (1) a walkforward length change. No re-seed is EXPECTED (the wfsafe_adx /
//       wfsafe_rsi shape -- SF recomputed per bar, state carried over; an EMA
//       has no window to re-seed), but it is not measured. emaLength is PINNED
//       in the grid until it is. If that changes, the re-seed branch goes here,
//       shaped like AtrProfitTarget's `atrLength != lookback` block.
//   (2) what XAverage(...)[k] reads on the first k evaluated bars. See emaAt().
const int emaN = (int)emaLength;
const double emaSf = 2.0 / (emaN + 1);
if (ctx.CurrentBar() == 1) {
    emaVal = close[0];                                // the seed: the PRICE
} else {
    emaVal = emaVal + emaSf * (close[0] - emaVal);    // EL's form, one statement
}
```

For the rules that read the EMA at a lag (`ema(close, emaLength)[k]`), the
recurrence is recursive, so -- unlike `UltimateOscillatorExtreme`'s `UoAt()`,
which recomputes a *window* function fresh from prices -- **the lagged value
cannot be recomputed; it has to be remembered.** Keep a ring:

```cpp
// classMembersHook
static constexpr int kEmaHistLen = 64;   // >= the largest lag the rule reads + 1
double emaHist_[kEmaHistLen] = {0.0};
int    emaPos_ = 0;
// The EMA k bars ago. Because the mirror runs EL's recurrence forward,
// emaHist_ holds exactly the values XAverage held on those bars -- for
// k < CurrentBar this is exact, not an approximation.
//
// !! UNMEASURED !! For k >= CurrentBar (the first k evaluated bars of a run)
// this returns the pre-seed 0.0, following the one measured precedent for a
// function's own series history -- WFSafe_RSI(...)[1] reads 0 on bar 1
// (EL_WFSafeRsi_Probe.txt) -- but that was measured for RSI, not XAverage, and
// extrapolating across functions is exactly what this register does not do.
// EL_XAverage_Probe.txt printed only the current value. Until the two-line
// follow-up run measures it, no rule that reads a lag ships.
double emaAt(int k) const {
    return emaHist_[(emaPos_ - 1 - k + 2 * kEmaHistLen) % kEmaHistLen];
}

// ... end of preConditionHook, immediately after emaVal is updated:
emaHist_[emaPos_] = emaVal;
emaPos_ = (emaPos_ + 1) % kEmaHistLen;
```

Comparisons against the EMA go through `el_gt` / `el_lt` / `el_ne` as usual: the
EMA and the close both sit near the tick grid, so the 2.22e-12 relational
tolerance is load-bearing here the way it was in `wfsafe_adx`'s DM
classification.

## 5. What is still open, and the follow-up lines to close it

Three things. Only the first blocks authoring.

**(a) The lagged read -- `XAverage(Close, Length)[k]`.** The probe printed only
the current value, so nothing is known about the function's own series history.
This gates 9 of the 14 blocked rules (section 6). It is cheap to close.

**(b) The length change.** `WFSafe_Xaverage` exists precisely to fix the
load-time-SF defect, and a fixed-input chart cannot show it. It *can* be
exercised on a single chart by driving `Length` from a bar counter -- which the
probe did not think to do, and which would settle in one run what `wfsafe_adx`
and `wfsafe_rsi` had to be read out of source to establish.

**(c) The `WFSafe_` library listing.** Brian was asked for it in the probe's Q5
and it did not come back with the outputs. Six are now known. No code change
waits on it; it retires the register's catch-all guess. Not a probe -- just the
library's function list.

Draft EasyLanguage for a follow-up run. Same SETUP as this probe (@OJ 240min,
Regular Session, Max Bars Back 250, apply as STRATEGY, both chart starts),
everything already in `EL_XAverage_Probe.txt` unchanged; add to `variables:`
`DynLen( 20 ), Xa1( 0 ), Xa5( 0 ), Xd( 0 ), Wd( 0 )` and add these lines:

```
{ (a) the function's own series history, against the variable history the probe
      already keeps in Xa. lag1/lag5 must be 0 once CurrentBar is past the lag;
      what Xa1 PRINTS on bar 1 -- 0, the seed, or something else -- is the
      whole question, and Xa5 on bars 1..5 is the same question with room. }
Xa1 = XAverage( Close, Length )[1];
Xa5 = XAverage( Close, Length )[5];

{ (b) the load-time SF defect, on one chart: flip the length at bar 2000 and
      watch whether the wrapper departs from the built-in. ovrd must be 0
      before bar 2000; if it goes non-zero after, WFSafe_Xaverage recomputes SF
      and the built-in does not -- which is the whole point of the wrapper. }
DynLen = IFF( CurrentBar < 2000, 20, 30 );
Xd = XAverage( Close, DynLen );
Wd = WFSafe_XAverage( Close, DynLen );
```

and append to the existing `Print(`:

```
       " xa1=",  Xa1:0:12,
       " lag1=", ( ( Xa1 - Xa[1] ) * 1000000000000000 ):0:4,
       " xa5=",  Xa5:0:12,
       " lag5=", ( ( Xa5 - Xa[5] ) * 1000000000000000 ):0:4,
       " ovrd=", ( ( Wd - Xd ) * 1000000000000 ):0:4
```

Reading it, written before the run: `lag1`/`lag5` = 0 on every bar past the
respective lag means a series function's history is just the recurrence's own
past values and the ring buffer in section 4 is exact; whatever `xa1` prints on
bar 1 (and `xa5` on bars 1-5) is the pre-seed answer, and if it is 0 the
`WFSafe_RSI` precedent generalises. `ovrd` = 0 on every bar means even a length
change does not separate the wrapper from the built-in; `ovrd` non-zero only
after bar 2000 means it does, and the bar it starts on says whether the wrapper
re-seeds or merely recomputes SF. If TradeStation rejects a variable in the
`numericsimple` `Length` slot, drop block (b) and say so -- that is itself the
answer that the length change can only be observed through MultiWalk. Please
also send the library's full `WFSafe_` function list.

## 6. The 14 XAverage-blocked A rules

All 14 rules in `reference/brooks/author/A_QUEUE.json`'s `blocked` list carry
`blocking_words: ["xaverage"]` and nothing else -- their other EL words
(`countif`, `lowest`, `wfsafe_avgtruerange`) are already registered and passing.
So the register gate opens for all 14 the moment the rows in section 3 land.

**The gate is not the constraint; the lagged read is.** Splitting on whether the
merged pseudocode reads the EMA only on the current bar:

**Authorable now on what was measured (5)** -- current-bar EMA only, nothing
that needs `ema(...)[k]` with k > 0:

| rule | pseudocode | why it is clear |
|---|---|---|
| `EmaGapBar` | `low[0] > ema(close, emaLength)[0]` | lag 0 only |
| `EmaTouch` | `low[0] <= ema(...)[0] && high[0] >= ema(...)[0]` | lag 0 only |
| `EmaTouchRecovery` | `low[0] <= ema(...)[0] && close[0] > ema(...)[0]` | lag 0 only |
| `CloseBeyondEma` | `close[0] > ema(...)[0] + marginAtr * atr(atrLookback)` | lag 0; `wfsafe_avgtruerange` is VERIFIED, reuse `AtrProfitTarget`'s accumulator verbatim |
| `CloseWithinAtrOfEma` | `abs(close[0] - ema(...)[0]) <= nearAtr * atr(atrLookback)` | same |

**Still waiting on the lagged read (9)** -- every one of these reads
`ema(close, emaLength)[k]` for some k > 0, which section 5(a) leaves open:

| rule | what it needs beyond the current bar |
|---|---|
| `CloseCrossesEma` | `ema(...)[1]` |
| `EmaGapBarBreakoutEntry` | `ema(...)[1]` |
| `ConsecutiveClosesBeyondEmaRun` | `ema(...)[i]`, i over 0..strongBars-1 |
| `BarsBeyondEmaCount` | `ema(...)[i]`, i over 0..lookback-1 |
| `NoTwoConsecutiveClosesBeyondEma` | `ema(...)[k]` and `[k+1]` across the window |
| `EmaSlope` | `ema(...)[slopeLookback]` |
| `EmaFlat` | `ema(...)[slopeLookback]` |
| `PullbackDepthBeyondEma` | the EMA at every lag in the window, **and** an EL `Lowest` over a *computed series* (`close - ema`), which is the zero-filled-variable-history hazard the `average` row records (see `BarRangeAboveStd`) -- needs its own look before authoring, independent of this probe |
| `BuyLimitBelowRisingMA` | `movingAverage[maSlopeLookback]`, and separately a limit-order entry, which is not an EMA question |

*A defensible shortcut, stated so it can be rejected rather than quietly taken:*
for k < CurrentBar the lagged value is unambiguous -- a series function's history
at lag k is the value it had k bars ago, which the ring buffer reproduces
exactly. The only genuinely unknown bars are the first k evaluated bars of a
run (k <= 5 for seven of the nine). One could author all nine now and accept
that hole. **The recommendation is not to**, on two grounds: `CLAUDE.md`'s rule
is "when EL's behaviour is unknown, ask rather than choose," and the one measured
precedent (`WFSafe_RSI(...)[1]` reading 0 on bar 1) shows this class of question
has a non-obvious answer that mattered enough to record. Two extra `Print`
fields close it -- cheaper than a wrong assumption baked into nine rules.

**Applies to all 14 regardless: pin `emaLength` in the grid** (`design-grid`)
until section 5(b) is measured. `WFSafe_Xaverage` exists and very probably
recomputes SF per bar, but "very probably" is what the wrapper rows were written
to stop us relying on, and a walkforward that re-optimizes the EMA length is
exactly the case nothing here measured.
