# XAverage follow-up: lagged reads and the length change

Source probe: `C:\Users\brian\source\repos\BacktestEngine\EL_XAverage_Lag_Probe.txt`
(engine commit 6b88d09; the 2026-09-13 copy was one unclosed comment and never ran).
Outputs, run 2026-09-17: `el_xaverage_lag_output1.txt` (chart start 01/01/2007,
9,665 bars, bar 1 = 1070703) and `el_xaverage_lag_output2.txt` (01/01/2010, 8,158
bars, bar 1 = 1100702). Both print `run=1` (RunTag was left at 1 for the second
chart); the files are told apart by their bar-1 date. Both carry the five new
fields on every line (`grep -c 'xa1='` equals the line count in each).

Sanity columns match the first run exactly: `sf = 0.095238095238095` on every
line, `ovr = 0` on all 17,823 lines, `xa` on bar 1 equals the close (28.80 /
17.45), and a Python re-run of `X = X[1] + SF*(C - X[1])` from the printed closes
reproduces `xa` to 5.1e-13 over both charts.

## 1. Lagged reads: `XAverage(Close, Length)[k]` is the printed history, exactly

| question | run 1 (2007) | run 2 (2010) |
|---|---|---|
| `xa1` on bar 1 | 0.000000000000 | 0.000000000000 |
| `xa1` on bar 2 | 28.800000000000 (= xa on bar 1) | 17.450000000000 (= xa on bar 1) |
| `lag1` bars 2..last, non-zero count | 0 of 9,664 | 0 of 8,157 |
| `xa5` on bars 1..5 | 0, 0, 0, 0, 0 | 0, 0, 0, 0, 0 |
| `xa5` on bar 6 | 28.800000000000 (= xa on bar 1) | 17.450000000000 (= xa on bar 1) |
| `lag5` bars 6..last, non-zero count | 0 of 9,659 | 0 of 8,152 |

So a series function's own history read with `[k]` is bit for bit the value it
printed k bars earlier: no re-derivation, no different rounding path. Before the
history exists (`[k]` on bars 1..k) it reads **0.0**, the same zero-filled
pre-history the `WFSafe_RSI` precedent showed. It is not the seed price and not a
`-1` sentinel.

**C++ mirror (settles §4 of `XAVERAGE_FINDINGS.md`):** the zero-initialized
mirrored ring buffer the corpus already builds for EMA history is exact. A rule
reading `ema[k]` on its first k bars gets 0.0 in both twins, which is why every
such rule must guard its early bars (`CurrentBar > k` in EL, the bar counter in
C++) rather than compare against the zero. That guard is the only thing the
authoring pass adds for lagged reads.

## 2. Length change: `WFSafe_Xaverage` recomputes SF on the same bar; the built-in freezes it

| question | run 1 (2007) | run 2 (2010) |
|---|---|---|
| max abs `ovrd` on bars 1..1999 (before the flip) | 0.0000 | 0.0000 |
| first bar with `ovrd <> 0` | 2000 (the flip bar itself) | 2000 |
| `ovrd` on bar 2000 (× 1e-12 = price units) | −0.188432 | +0.062109 |
| bars 2000..last with `ovrd <> 0` | 7,666 of 7,666 | 6,159 of 6,159 |
| `ovrd` on the last bar (both charts end 2026-09-17) | +0.455868 | +0.455868 |
| did `DynLen` (a variable) compile in the `Length` slot? | yes, as written | yes |

Which side moved was settled by reconstruction from the printed closes. Four
hypotheses were run and compared with `ovrd / 1e12` on every bar from 2000 on:

| hypothesis | max error, run 1 | max error, run 2 |
|---|---|---|
| **Wd = SF recomputed at the flip, state carried; Xd = SF frozen at 20** | **3.6e-15** | **3.6e-15** |
| Wd frozen, Xd recomputed | 42.4 | 42.4 |
| Wd re-seeded with the close at the flip, then SF(30); Xd frozen | 5.7 | 1.9 |
| Wd frozen, Xd re-seeded | 42.4 | 42.4 |

So `WFSafe_Xaverage` is the `WFSafe_ADX`/`WFSafe_RSI` shape: when `Length`
changes it recomputes `SF = 2/(Length+1)` on that bar and continues from the
carried state, with no re-seed. The built-in `XAverage` keeps the SF it computed
when the study loaded, so after a length change it is silently still a 20-bar EMA.
The identical last-bar `ovrd` on both charts is the same fact seen another way:
by 2026 both series have forgotten their seeds and differ only by SF.

**Consequence for grids.** `emaLength` may now be optimized under MultiWalk: the
wrapper tracks the new length from the first bar of each walk-forward window,
carrying state across the boundary exactly as the corpus's C++ mirror does when
the generator re-instantiates with a new input. The "pin `emaLength`" caveat is
retired. The C++ mirror (`SF` derived from the input each bar or at construction,
state carried) already behaves like the wrapper; nothing changes in the code.

## 3. Register rows

`xaverage` and `wfsafe_xaverage` stay VERIFIED; the in-row "STILL UNMEASURED"
caveats for the lagged read and the length change are replaced with §1 and §2.
Rows applied by the orchestrator on 2026-09-17.

## 4. What this unblocks

- The 9 A-list EMA rules held back for lagged reads: `BarsBeyondEmaCount`,
  `ConsecutiveClosesBeyondEmaRun`, `EmaGapBarBreakoutEntry`, `CloseCrossesEma`,
  `NoTwoConsecutiveClosesBeyondEma`, `PullbackDepthBeyondEma`, `EmaSlope`,
  `EmaFlat`, `BuyLimitBelowRisingMA`.
- The 3 B-list rules in `B_QUEUE.json` `xaverage_lag`:
  `CounterColorTrendBarClosingBelowEma`, `SecondEmaGapBarEntry`, `BarsSinceEmaCross`.
- Grid design: `emaLength` is a legitimate optimization axis.

## 5. Still open

Only the `WFSafe_` library listing (asked three times; blocks nothing). Seven
functions are now known to exist: `WFSafe_AvgTrueRange`, `WFSafe_ADX`,
`WFSafe_DirMovement`, `WFSafe_RSI`, `WFSafe_SummationFC`, `WFSafe_Xaverage`, and
no `WFSafe_SwingHigh`/`WFSafe_SwingLow` (Brian, 2026-09-13).
