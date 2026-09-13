# TLValue probe findings

Source probe: `C:\Users\brian\source\repos\BacktestEngine\EL_TLValue_Probe.txt`.
Outputs read in full: `el_tlvalue_output2.txt` (RunTag 2, DegenTest=1, the
degenerate `Bar1 == Bar2` run, 9,846 bars, @OJ 240min) and
`el_tlvalue_output4.txt` (RunTag 1, DegenTest=0, the main run, 9,646 bars,
@OJ 240min from 2007-07-03). Both charts carry the same five spellings (v1-v5),
the two open-coded twins (TwA/TwB), and the diff columns (dA, dB, dAB, d12,
d15, fwd) on every line. Total probed bars across both files: 19,492.

## 1. Results table (filled from the outputs)

Typical bar used: `el_tlvalue_output4.txt` bar 200 (`run=1 bar= 200
date=1071121 time=1400`).

```
  column   value on a typical bar                    constant across bars? (y/n)
  -------  ----------------------------------------  ---------------------------------------------------
  p1 / p2  p1=33.700000  p2=29.300000                 n -- tracks High[10]/High[2] each bar; p1==p2 (flat
                                                       line, slope 0) on 47/9,646 and 48/9,846 bars, never
                                                       a problem (Bar1<>Bar2 still holds: 10<>2)
  v1       28.200000                                  n (price-dependent); the FORMULA is constant --
                                                       v1 == TwA bit-for-bit on 19,492/19,492 bars (dA)
  v2       28.200000                                  n (price-dependent); v2 == v1 EXACTLY on
                                                       19,492/19,492 bars (d12 = 0 always)
  v3       25.450000                                  n (price-dependent); always v1 + 5*(-slope) exactly
                                                       (e.g. bar 1: v3-v1 = 3.75 = -5 * -0.75 slope)
  v4       55.700000                                  n (price-dependent); always the plain line
                                                       extended 40 bars past P1, never clamped (confirmed:
                                                       values run to -13.45 and beyond, see Q3 below)
  v5       28.200000                                  n (price-dependent); matches v1 to 6 printed
                                                       decimals on every bar; differs from v1 at the
                                                       1e-14 level on 116/9,846 bars (see d15)
  dA       0.0000                                     y -- EXACTLY 0.0000 on all 19,492 probed bars,
                                                       both files, zero exceptions
  dB       0.0000                                     n -- 0.0000 on 19,376/19,492 bars (99.4%); nonzero
                                                       on the other 116 (both files show the SAME 116-bar
                                                       distribution: +/-0.1110 .. +/-28.4217, units of
                                                       1e-15, i.e. max |dB| = 2.84217e-14 absolute)
  dAB      0.0000                                     n -- identical to dB bar-for-bar, always (verified:
                                                       zero mismatches between dB and dAB columns in
                                                       either file)
  d12      0.0000                                     y -- EXACTLY 0.0000 on all 19,492 probed bars,
                                                       both files, zero exceptions
  d15      0.0000                                     n -- identical to dB bar-for-bar, always (verified:
                                                       zero mismatches between dB and d15 columns in
                                                       either file); same 116/9,846 nonzero bars, same
                                                       magnitudes, same signs
  fwd      -2750000.00  (real units: -2.75)            n -- tracks 5x the local per-bar slope, which
                                                       tracks price; zero only when p1==p2 (flat line)
```

```
  question                                       answer
  ---------------------------------------------  ------------------------------------------------------
  run 2: did it halt? exact error text            NO HALT. el_tlvalue_output2.txt runs unbroken from
                                                   bar 1 (1070208) to bar 9846 (1260902) -- the same
                                                   span as the main run -- with no error text anywhere
                                                   and no gap or truncation at bar 40.
  run 2: if not, v5/degenerate value              degen=0.000000 at bar 40 (the only bar where
                                                   DegenTest fires `TLValue(P1, 5, P2, 5, 0)`,
                                                   i.e. Bar1=Bar2=5). Every other bar also prints
                                                   degen=0.000000, consistent with the variable's
                                                   0-initialization and never being reassigned again.
  did TS accept the 5-argument TLValue?           YES -- both full runs (9,846 and 9,646 bars) compile
                                                   and print valid numeric v1-v5 on every line; nothing
                                                   in either file indicates a rejected call or argument
                                                   count.
```

## 2. Every pre-registered question, answered with the proving lines

**Q2 -- bar-number convention (`d12`).** `d12 = (v1 - v2) * 1e15` is `0.0000`
on every one of the 19,492 probed bars in both files (verified with `grep -vc
" d12=0.0000 "` returning `0` on both `el_tlvalue_output2.txt` and
`el_tlvalue_output4.txt`). Example, output4 bar 1: `v1=33.050000
v2=33.050000 ... d12=0.0000`. This is the pre-registered "pure interpolation"
branch: **TLValue never reads CurrentBar.** The bars-ago spelling
(`TLValue(P1,10,P2,2,0)`) and the CurrentBar-relative spelling
(`TLValue(P1,CurrentBar-10,P2,CurrentBar-2,CurrentBar)`) are the identical
line to the last representable bit, on every bar, across a ~19-year span. The
corpus's bars-ago convention (inherited from `SwingHighBar`) is correct
because it is self-consistent, not because TLValue requires it -- **the
bar-number convention is the caller's responsibility.**

**Q1 -- argument order / anchor role (`d15`, `v5`).** `d15` is nonzero on
116/9,846 bars (output2) and the identical 116/9,646 bars (output4) --
verified the two files print the SAME distribution of nonzero values (both
`awk` dumps above match line for line: `-14.2109` once, `-7.1054` x4,
`-3.5527` x8, ... up to `28.4217` once). On every bar in both files, `d15`
equals `dB` EXACTLY (verified: an awk pass comparing the two columns line by
line found zero mismatches in either file). That equality is itself the
finding: swapping the anchor order (`v5 = TLValue(P2,2,P1,10,0)`) reproduces
not the P1-anchored line (`v1`/`TwA`, drift 0) but the P2-anchored twin's
rounding pattern (`TwB`) instead -- **TLValue anchors on whichever
(Price,Bar) pair is passed FIRST**, not on which one is chronologically
older. `v5` is a plausible price on every bar (equal to `v1` to all 6 printed
decimals in every sampled line, e.g. output4 bar 370: `v1=5.825000
v5=5.825000`), so per the pre-registered branch: **order matters only
through rounding**, magnitude at most `2.84217e-14` absolute (dB/d15 max
`28.4217` in units of 1e-15) -- utterly negligible next to EL's 2.22e-12
relational tolerance, but the mirror must still match the corpus's
older-anchor-first order (`P1` older, passed first) because THAT is the
spelling with literally zero drift (`dA` = 0 always), not merely small
drift.

**Q3 -- extrapolation (`v3`, `v4`, `fwd`).** Both directions extrapolate
freely with no clamp and no sentinel. Forward: `fwd = (v3-v1)*1e6` matches
`5 * (-slope)` exactly on every sampled bar -- output4 bar 1:
`p1=25.550000 p2=31.550000` -> `slope=(31.55-25.55)/(2-10)=-0.75`;
`v3-v1 = 36.800000-33.050000 = 3.75 = -5 * -0.75`. Backward: `v4` (target
bar 50, i.e. 40 bars behind the older anchor) matches the same line
extended, e.g. bar 1: `v4 = 25.55 + 40*(-0.75) = -4.45` = printed
`v4=-4.450000`. `v4` goes deeply negative on several bars (e.g. output4 bar
2: `v4=-13.450000`), which rules out any clamp near 0 or -1. A handful of
bars print `v4=-1.000000` exactly (bars 414, 1423, 1529 of output4) --
checked and this is a genuine coincidence of the linear formula (e.g. bar
414: `p1=17.25, p2=20.90, slope=-0.45625, v4 = 17.25 + 40*(-0.45625) =
-1.0` exactly), NOT a sentinel: other bars extrapolate to -4.45, -13.45 and
beyond, so -1 is not a floor. **Conclusion: TLValue is the plain unclamped
line equation in both directions; the mirror is exactly that, and
TrendLineBreak-style rules work as written w.r.t. extrapolation.**

**Q5 -- precision / operand order (`dA`, `dB`, `dAB`).** `dA = (v1-TwA)*1e15`
is `0.0000` on ALL 19,492 probed bars in both files -- zero exceptions
(verified with `grep -vc "dA=0.0000 "` returning `0` on both files). `dB =
(v1-TwB)*1e15` and `dAB = (TwA-TwB)*1e15` are identical to each other
bar-for-bar (consistent with `v1==TwA` exactly, so `dB` collapses to `dAB`
algebraically) and are nonzero on 116/9,846 (~1.2%) bars, magnitude up to
`2.84217e-14` absolute. This is the pre-registered clean case: **`dA=0`
everywhere and `dB != 0` sometimes -> TLValue anchors at Price1: `p1 +
(target - b1) * slope`, in that exact order** (`Slope = (Price2-Price1) /
(Bar2-Bar1)` computed first, matching the probe's own `TwA` code
statement-for-statement). This is not a null result (`dAB` is nonzero on
116 bars in both files) -- the probe's non-dyadic 0.05 @OJ tick did surface
the effect, just rarely, because most bars' arithmetic happens to round the
same way regardless of operand order.

**Q4 -- Bar1 = Bar2, degenerate case (run 2 only).** Contrary to the
pre-registered primary hypothesis (that TLValue would halt like the bare `/`
operator per `EL_ZeroRange_Probe.txt`), **run 2 did NOT halt.**
`el_tlvalue_output2.txt` runs unbroken from bar 1 to bar 9846 (the file's
full expected length, matching the main run's span), with the DegenTest
branch's trigger bar (`CurrentBar = 40`) passing through with no
interruption: `run=2 bar= 40 date=1070308 time=1400 ... degen=0.000000`,
and every later bar continues normally through `bar=9846 date=1260902`.
The call made at bar 40, `TLValue(P1, 5, P2, 5, 0)` (`Bar1=Bar2=5`),
returned exactly `0.0`, not Price1 (~103), not -1, not an infinity. Given
`degen` is a variable initialized to 0 and reassigned only at bar 40, and
every bar (including bar 40 itself) prints `degen=0.000000`, the most
literal reading is that the call executed and returned `0.0`.

**Ambiguity flag (per instructions, not guessed past):** the probe's `Print`
statement never echoes the `DegenTest` INPUT value itself, so nothing in the
log independently proves `DegenTest` was actually `1` for this run rather
than `0` (in which case the `Degen = TLValue(...)` line would never execute
and `degen=0.000000` would just be the untouched initializer, telling us
nothing about the degenerate case). This document takes the file at the
identification given -- `el_tlvalue_output2.txt` is RunTag 2, the
DegenTest=1 run, per how it was named and handed off -- and reports the
finding at face value: **no halt, and the call returns `0.0`.** If that
identification is ever in doubt, the only way to close it is a re-run that
also prints `DegenTest:1:0` in the header line.

Because `0.0` is not a plausible line value anywhere near the surrounding
~90-160 OJ price range, it functions as a silent sentinel rather than a
usable number -- exactly the situation the probe's write-up already
anticipated for a "returns a number" outcome. **The C++ mirror must still
GUARD `Bar1 == Bar2` and never call through to a live TLValue-equivalent
computation on that input; it must not rely on reproducing the `0.0`.**

**TS acceptance.** Both full-length runs (9,846 and 9,646 bars) compiled and
produced six-decimal numeric output for v1 through v5 and every diff column
on every line -- no sign of a rejected call or an unsupported argument
count for the 5-argument `TLValue`.

## 3. Exact replacement text for the `rules/EL_FEATURES.md` register row

(Not applied to the file per instructions -- `rules/EL_FEATURES.md` is not to
be edited. Exact text below, same column layout: `| Feature | Status | What
is known | Evidence |`.)

```
| `tlvalue` | VERIFIED | `TLValue(Price1, Bar1, Price2, Bar2, TargetBar)` is a pure two-point linear interpolation anchored at the FIRST (Price1, Bar1) pair: `Slope = (Price2-Price1)/(Bar2-Bar1); value = Price1 + (TargetBar-Bar1)*Slope` -- reproduced with drift 0.0 (`dA`) on all 19,492 probed bars across two @OJ 240min charts (2007-2026). The bar-number convention is the CALLER's responsibility, not the function's: bars-ago and CurrentBar-relative spellings of the identical line agree exactly, drift 0 (`d12`) on all 19,492 bars -- TLValue never reads CurrentBar. It extrapolates freely, unclamped, in both directions past the anchors (5 bars forward and 40 bars behind the older anchor both match the plain line formula exactly on every sampled bar; an apparent `v4=-1.000000` on 3 bars is a genuine extrapolated coincidence, not a sentinel -- other bars extrapolate to -13.45 and beyond). Argument order changes only rounding, not the line: swapping the anchors reproduces the SAME line to 6 printed decimals on every bar, differing from the Price1-anchored spelling by at most 2.84e-14 absolute on 116/9,846 bars (~1.2%) -- negligible next to EL's 2.22e-12 relational tolerance -- but the corpus's older-anchor-first convention (older pivot passed as Price1/Bar1) is the spelling with ZERO drift, not merely small drift, so the mirror must keep that order. **`Bar1 == Bar2` does NOT raise a runtime divide-by-zero** (unlike the bare `/` operator, see the `/` row and `EL_ZeroRange_Probe.txt`): the dedicated degenerate run (RunTag 2, DegenTest=1, 9,846 bars, no halt) made the single call `TLValue(P1,5,P2,5,0)` at bar 40 and it returned exactly `0.0` -- not Price1, not -1, not an error. 0.0 is never a plausible line value against the surrounding ~90-160 prices, so every rule MUST GUARD `Bar1 <> Bar2` before calling rather than rely on or reproduce that return (the log does not independently print the DegenTest input, so this rests on the run being configured as identified -- see TLVALUE_FINDINGS.md). 32 merged candidates project trend lines through two pivots and are unblocked by this row | `EL_TLValue_Probe.txt`; `el_tlvalue_output2.txt` (RunTag 2, degenerate), `el_tlvalue_output4.txt` (RunTag 1, @OJ 240min from 2007) |
```

## 4. C++ mirror for the authoring pass

Generic form -- a trend line through two pivots (older `p1`/`b1`, newer
`p2`/`b2`) projected to bar `k` (bars-ago axis, matching the corpus's
`SwingHighBar`/`SwingLowBar` callers), in the corpus dialect (see
`AtrAboveAverage.json`'s `preConditionHook` for the house style: locals
computed imperatively, guard folded into the condition rather than thrown):

```cpp
// TLValue(Price1, Bar1, Price2, Bar2, TargetBar) mirror -- VERIFIED
// (EL_TLValue_Probe.txt; el_tlvalue_output2.txt, el_tlvalue_output4.txt):
//   * pure two-point interpolation, anchored at the FIRST (Price1, Bar1)
//     pair -- drift 0 vs TLValue on 19,492/19,492 probed bars
//   * caller's bar-number convention (bars-ago here, matching SwingHighBar);
//     TLValue never reads CurrentBar (d12 = 0 on 19,492/19,492 bars)
//   * extrapolates unclamped in both directions -- no sentinel
//   * REQUIRED GUARD: Bar1 == Bar2 does not halt (unlike bare '/') -- it
//     measured a bare 0.0 return, which is not a usable line value. The
//     rule must guard, not branch on the return.
bool   tlOk    = (b1 != b2);
double tlSlope = tlOk ? (p2 - p1) / (double)(b2 - b1) : 0.0;
double tlValue = tlOk ? p1 + ((double)k - b1) * tlSlope : 0.0;   // anchor at (p1,b1); older-first order, matching TwA bit-for-bit
```

Applied to the probe's own `TrendLineBreak` example (the spelling all 32
merged candidates inherit), with the guard now made explicit instead of
assumed:

```cpp
int    p1b = swingHighBar(swingStrength, 2);   // OLDER occurrence -- pass first
int    p2b = swingHighBar(swingStrength, 1);   // NEWER occurrence -- pass second
if (p1b != p2b) {                              // REQUIRED: TLValue(Bar1==Bar2) returns 0.0, not a halt, and 0.0 is not a usable line value
    double slope   = (high[p2b] - high[p1b]) / (double)(p2b - p1b);
    double bearTl0 = high[p1b] + (0 - p1b) * slope;   // anchored at (high[p1b], p1b) -- matches TLValue to 0 ULP
    // ... close[0] > bearTl0 + breakTicks * tickSize
}
// else: no valid trend line this bar -- the condition must not fire
```
