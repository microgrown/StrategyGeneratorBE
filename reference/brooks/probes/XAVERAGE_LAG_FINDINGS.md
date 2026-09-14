# XAverage lag / length-change probe -- findings

Source probe: `C:\Users\brian\source\repos\BacktestEngine\EL_XAverage_Lag_Probe.txt`.
Outputs read: `el_xaverage_output_rerun_chart4.txt` (labelled chart 4 = RunTag 1,
2007 start, 9,646 lines) and `el_xaverage_output_rerun_chart5.txt` (labelled
chart 5 = RunTag 2, 8,339 lines).

**Headline: the follow-up probe did not run. Neither output file contains any of
the five new columns (`xa1=`, `lag1=`, `xa5=`, `lag5=`, `ovrd=`), so nothing in
this probe was measured. Both questions the probe exists to close -- (a) the
lagged read `XAverage(...)[k]`, and (b) the length change -- remain exactly as
open as they were in `XAVERAGE_FINDINGS.md` section 5. Nine of the fourteen
XAverage-blocked A rules stay blocked; `emaLength` stays pinned in the grid.**

Nothing in the register or the mirror changes on the strength of these files,
and nothing below should be read as a measurement.

## 1. What the two files actually are

`grep -c` over both files, for each of the five new field labels:

| file | `xa1=` | `lag1=` | `xa5=` | `lag5=` | `ovrd=` | fields/line | lines |
|---|---|---|---|---|---|---|---|
| `el_xaverage_output_rerun_chart4.txt` | 0 | 0 | 0 | 0 | 0 | 14 (uniform) | 9,646 |
| `el_xaverage_output_rerun_chart5.txt` | 0 | 0 | 0 | 0 | 0 | 14 (uniform) | 8,339 |

`awk '{print NF}' | sort -u` returns the single value `14` for both files --
i.e. every line of both files is the ORIGINAL probe's `Print`, the twelve fields
`run bar date time c sf xa wf ovr d1 d2 d3` (14 whitespace tokens because the
`:6:0` and `:5:0` formats put a space inside `bar=` and `time=`). Not one line
of either file carries a sixth-through-tenth new field, so this is not a
partially-written or truncated run: it is the old strategy's output.

`el_xaverage_lag_output.txt`, the file the new study prints to, **does not exist**
anywhere in the engine repo. `grep -rl 'xa1=' *.txt` over the engine repo
returns exactly one file: `EL_XAverage_Lag_Probe.txt` itself, the probe text.

### chart 4: a byte-for-byte copy of the first run's output

`cmp el_xaverage_output4.txt el_xaverage_output_rerun_chart4.txt` reports
**IDENTICAL** -- same 1,501,742 bytes, same 9,646 lines, same first and last
line. The suspicion raised by the matching byte size is confirmed: this file is
a copy of the original run's `el_xaverage_output4.txt`, not a new run at all.

```
run=1 bar=     1 date=1070703 time= 1200 c=28.800000 sf=0.095238095238095 xa=28.800000000000 wf=28.800000000000 ovr=0.0000 d1=0.0000 d2=28800000000000.0000 d3=0.0000
run=1 bar=  9646 date=1260902 time= 1400 c=148.050000 sf=0.095238095238095 xa=147.909807060146 wf=147.909807060146 ovr=0.0000 d1=0.0000 d2=0.0000 d3=0.0000
```

(first and last line of `el_xaverage_output_rerun_chart4.txt`; identical to the
first and last line of `el_xaverage_output4.txt`.)

### chart 5: a genuinely new run -- of the OLD strategy, on a DIFFERENT chart

This one is not a copy. It differs from `el_xaverage_output5.txt` in length
(8,339 vs 8,139 lines) and in its first bar:

```
el_xaverage_output5.txt            run=2 bar=     1 date=1100702 time= 1200 c=17.450000 ...
el_xaverage_output_rerun_chart5.txt run=2 bar=     1 date=1100209 time= 1200 c=11.350000 ...
```

Both still end on the same last bar, `1260902 14:00`. So the rerun's history
starts exactly 200 bars earlier than the original chart 5's -- ~5 months of
@OJ 240min at 2 bars/day, which is the signature of a smaller Max Bars Back
(250 -> 50) or an earlier chart start, not of the new code. **The chart 5 rerun
was therefore executed, but with the original probe's strategy, and on a chart
whose setup no longer matches either the original run or the follow-up probe's
SETUP block.** It cannot be used as a fresh chart-5 comparison either.

### block (b): not "dropped per the fallback" -- never attempted

The probe's fallback for block (b) is that if TradeStation rejects a variable in
the `numericsimple` `Length` slot, the `DynLen`/`Xd`/`Wd` lines and the `ovrd`
field are removed and the run proceeds -- which would leave a file with `xa1=`,
`lag1=`, `xa5=` and `lag5=` present and `ovrd=` absent. That is not what these
files look like: **all five new fields are absent, including the four that have
nothing to do with `DynLen`.** The fallback was not exercised; the whole new
`Print` is missing. So we cannot even record "a variable Length does not
compile" as the answer to (b) -- that outcome would have been visible, and is
not what we have.

### sanity columns (all that these files can confirm)

The two sanity checks the probe reprints do pass, on both files -- which is
consistent with them being (a copy of, and a rerun of) the original strategy:
`sf` is `0.095238095238095` on every line of both, `ovr` is `0.0000` on all
9,646 + 8,339 lines (`grep -vc ' ovr=0.0000 '` returns 0), and `d3` is non-zero
on 5,534 of the chart-5 rerun's 8,339 lines (66.4%), the same ~67% as the first
run. These re-confirm section 1-2 of `XAVERAGE_FINDINGS.md` at a third chart
start; they say nothing about the lag or the length change.

## 2. Results table

Every cell that the probe asked for is unmeasured, for the reason above.

| question | run 1 (chart 4 file) | run 2 (chart 5 file) |
|---|---|---|
| xa1 on bar 1 | NOT MEASURED -- no `xa1=` field | NOT MEASURED -- no `xa1=` field |
| lag1 on bar 2 / bar 100 / last bar | NOT MEASURED -- no `lag1=` field | NOT MEASURED -- no `lag1=` field |
| xa5 on bars 1..5 | NOT MEASURED -- no `xa5=` field | NOT MEASURED -- no `xa5=` field |
| lag5 on bar 6 / bar 100 / last bar | NOT MEASURED -- no `lag5=` field | NOT MEASURED -- no `lag5=` field |
| max abs ovrd on bars 1..1999 | NOT MEASURED -- no `ovrd=` field | NOT MEASURED -- no `ovrd=` field |
| first bar where ovrd != 0 after bar 2000 | NOT MEASURED | NOT MEASURED |
| did the DynLen line compile? | UNKNOWN -- the new `Print` is absent in full, so this is not the fallback outcome either | UNKNOWN -- same |
| what the file IS | byte-identical copy of `el_xaverage_output4.txt` (`cmp` reports no difference) | a real run of the ORIGINAL strategy on a chart starting 200 bars earlier (bar 1 = 1100209, 8,339 bars) |

| question | answer |
|---|---|
| full list of WFSafe_ functions in the library | STILL NOT REPORTED. No listing came back with these outputs and there is no new file in the engine repo carrying one. The six known remain `WFSafe_AvgTrueRange`, `WFSafe_ADX`, `WFSafe_DirMovement`, `WFSafe_RSI`, `WFSafe_SummationFC`, `WFSafe_Xaverage`; the register's catch-all guess stands. |

## 3. What this leaves open

Unchanged from `XAVERAGE_FINDINGS.md` section 5:

- **(a) The lagged read.** Whether `XAverage(Close, Length)[k]` is exactly the
  recurrence's own past printed values (so the section-4 ring buffer is exact
  and needs no separate code path for `k > 0`), and what it returns before that
  history exists (0, the seed, or something else). **This gates 9 of the 14
  XAverage-blocked A rules** in `reference/brooks/author/A_QUEUE.json`. They stay
  blocked; the 5 current-bar-only rules in `XAVERAGE_FINDINGS.md` section 6 are
  still authorable.
- **(b) The length change.** Whether `WFSafe_Xaverage` recomputes SF (or
  re-seeds) when `Length` changes and the built-in does not. `emaLength` stays
  **pinned** in every grid until this is measured.
- **(c) The `WFSafe_` library listing.** Asked for twice now, not returned. No
  code waits on it.

## 4. To re-run

The probe text needs no change -- it is correct as written, and its output
filename (`el_xaverage_lag_output.txt`) is deliberately different from the
original's so the two cannot be confused. What is needed is that the strategy
actually compiled from `EL_XAverage_Lag_Probe.txt` (not the older
`EL_XAverage_Probe.txt`) be applied to the two charts, with the probe's SETUP
block matched exactly: @OJ 240min, Regular Session, **Max Bars Back 250**,
apply as STRATEGY, chart starts 01/01/2007 and 01/01/2010.

Two checks that make a repeat of this outcome visible in one command, before any
analysis:

```
grep -c 'ovrd=' <file>          # must be the line count, not 0
cmp el_xaverage_output4.txt <file>   # must report a difference
```

The chart-5 rerun's 200-extra-bar history is a second, independent sign that the
chart setup drifted: if the re-run's `bar=1` date is not `1070703` (run 1) and
`1100702` (run 2), Max Bars Back or the chart start is not what the probe asked
for, and the run is not comparable to the first probe's evidence.

## 5. The C++ mirror for `ema(...)[k]` reads -- UNCHANGED, and still gated

No measurement arrived, so the mirror in `XAVERAGE_FINDINGS.md` section 4 stands
exactly as written, including its `!! UNMEASURED !!` banner. Restated here in
the style of `rules/BarRangeAboveStd.json`'s mirrored-history comment, which is
the same shape and the same justification -- a ring buffer of *the recurrence's
own past values*, zero-initialised, because the value cannot be recomputed from
price:

```cpp
// classMembersHook
static constexpr int kEmaHistLen = 64;   // >= the largest lag the rule reads + 1
double emaHist_[kEmaHistLen] = {0.0};
int    emaPos_ = 0;

// EL: XAverage() is a RECURRENCE, so unlike a window function (average(),
// stddev(), highest()) a lagged read cannot be recomputed from price -- it has
// to be remembered. ema(close, n)[k] is mirrored the way BarRangeAboveStd
// mirrors rrange's history: a ring buffer that starts ZEROED and is fed one
// value per bar from the recurrence itself, so the mirror's history is the
// mirror's own past output and never touches warm-up bars EasyLanguage did not
// evaluate. For k < CurrentBar this is exact BY CONSTRUCTION -- provided EL's
// XAverage(...)[k] is likewise its own past printed values, which is
// !! STILL UNMEASURED !!: EL_XAverage_Lag_Probe.txt was written to settle it
// and its 2026-09-13 run came back in the ORIGINAL probe's format with no
// xa1/lag1/xa5/lag5/ovrd columns at all (chart 4's file is a byte-identical
// copy of el_xaverage_output4.txt). See XAVERAGE_LAG_FINDINGS.md.
//
// !! ALSO UNMEASURED !! For k >= CurrentBar (the first k evaluated bars of a
// run) this returns the pre-seed 0.0, following the one measured precedent for
// a function's own series history -- WFSafe_RSI(...)[1] reads 0 on bar 1
// (EL_WFSafeRsi_Probe.txt) -- but that was measured for RSI, not XAverage, and
// extrapolating across functions is what this register does not do.
//
// Until both are measured, NO RULE THAT READS A LAG SHIPS. If a length change
// is ever mirrored, the ring is re-seeded on it the way BarRangeAboveStd
// re-assigns rangeHistory when lookback changes -- but the length-change
// behaviour is unmeasured too, so emaLength stays PINNED in the grid.
double emaAt(int k) const {
    return emaHist_[(emaPos_ - 1 - k + 2 * kEmaHistLen) % kEmaHistLen];
}

// ... end of preConditionHook, immediately after emaVal is updated:
emaHist_[emaPos_] = emaVal;
emaPos_ = (emaPos_ + 1) % kEmaHistLen;
```

The current-bar half of the mirror (`XAVERAGE_FINDINGS.md` section 4: price
seed on `ctx.CurrentBar() == 1`, `emaVal + emaSf * (close[0] - emaVal)` as one
statement, no warm-up guard) is measured and unaffected by this null result.
