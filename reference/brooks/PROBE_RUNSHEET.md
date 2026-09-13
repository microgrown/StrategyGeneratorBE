# Probe run sheet: Swing, TickSize, TLValue, XAverage

How to run the four open probes (`BacktestEngine/EL_Swing_Probe.txt`,
`EL_TickSize_Probe.txt`, `EL_TLValue_Probe.txt`, `EL_XAverage_Probe.txt`) in
TradeStation with the fewest chart setups that still answer every question
each probe pre-registers. Follow `BacktestEngine/docs/EL_VERIFICATION.md`'s
loop (Brian runs -> mirror in Python -> decide by pre-registered criteria ->
lock in) once the outputs are back.

**5 charts total**, one non-chart step (compile-only), run in this order.

---

## Step 0 — shared MultiWalk override check (no chart, 2 minutes)

Swing (Q5) and XAverage (Q5) both need the same `WFSafe_` enumeration. Do
this once, in the TradeStation Development Environment, before touching any
chart:

1. Open the MultiWalk function library and search for every function whose
   name begins `WFSafe_`. Report the FULL LIST. Five are on file today:
   `WFSafe_AvgTrueRange`, `WFSafe_ADX`, `WFSafe_DirMovement`, `WFSafe_RSI`,
   `WFSafe_SummationFC`.
2. For the Swing probe, compile (Verify only — do not apply to any chart)
   each of these one-liners on its own:

   ```EasyLanguage
   Value1 = WFSafe_SwingHigh( 1, Close, 2, 20 ) ;
   ```
   ```EasyLanguage
   Value1 = WFSafe_SwingHighBar( 1, Close, 2, 20 ) ;
   ```
   ```EasyLanguage
   Value1 = WFSafe_SwingLow( 1, Close, 2, 20 ) ;
   ```
   ```EasyLanguage
   Value1 = WFSafe_SwingLowBar( 1, Close, 2, 20 ) ;
   ```
   "unknown identifier" on all four -> no swing override, plain EL governs.
   Any of them compiling -> STOP, report which; that wrapper wins and its
   source is needed before any swing rule is written.
3. XAverage's own probe code (Step 4 below) calls `WFSafe_XAverage` inline,
   so its compile check is the run itself — no separate action needed here,
   just fold this list into that probe's result table.

---

## Chart 1 — @ES, 60 min, back-adjusted continuous, 2015 -> today

Hosts **TickSize run 1** and the entire **Swing probe** (Swing is
data-independent, so it rides on whichever chart is convenient; @ES is
already open for TickSize run 1, so putting it there saves a chart).
Sharing is safe: Swing's code never reads the chart's price series (its
four signals are all `Mod(CurrentBar, 8)` synthetic), and TickSize places
no orders and holds no state that Swing could disturb — the two studies
just print to different files.

- Symbol: `@ES`, continuous contract, **back-adjusted**
- Interval: 60 min
- Session: Regular Session
- Chart start: 2015-01-01 -> today (comfortably >= 120 bars for Swing)
- Apply as: Indicator (both studies)
- Max Bars Back: TickSize study 10; Swing study 30 (set per-study in each
  study's Format dialog — they don't need to match)
- Costs: irrelevant, indicators only

Studies, in order:

1. **TickSize probe, run 1** (`RunTag = 1`). Before applying, delete
   `el_ticksize_output.txt` if it exists — TradeStation appends and all
   four TickSize runs share one file.

   ```EasyLanguage
   inputs:
       RunTag( 1 );

   variables:
       MM( 0 ),
       PS( 0 ),
       Tick( 0 ),
       BPV( 0 ),
       PV( 0 ),
       DTick( 0 ),
       Diff( 0 ),
       MinD( 999999 ),
       OrdRes( 0 ),
       Changed( false );

   { Mirror the words into variables first: a variable has history, so the
     "did it change" test is a plain [1] comparison, and a Print of a variable
     is legible even if one of the words is unavailable on this chart. }
   MM  = MinMove;
   PS  = PriceScale;
   BPV = BigPointValue;
   PV  = PointValue;          { delete this line and the pv= field if TS rejects it }

   Tick  = MM / PS;
   DTick = BPV * Tick;

   { Independent cross-check: the smallest non-zero close-to-close move seen so
     far must be the tick, and it is computed without touching MinMove. }
   Diff = AbsValue( Close - Close[1] );
   If CurrentBar > 1 and Diff > 0 and Diff < MinD then
       MinD = Diff;

   { Operand order on a four-tick margin: division first (what the merged
     pseudocode writes) minus multiplication first, scaled by 1e15. }
   OrdRes = ( 4 * ( MM / PS ) - ( 4 * MM ) / PS ) * 1000000000000000;

   Changed = CurrentBar = 1
             or MM <> MM[1]
             or PS <> PS[1]
             or BPV <> BPV[1];

   If Changed or Mod( CurrentBar, 500 ) = 0 or LastBarOnChart then
       Print( File( "C:\Users\brian\source\repos\BacktestEngine\el_ticksize_output.txt" ),
              "run=",     RunTag:1:0,
              " sym=",    GetSymbolName,
              " bar=",    CurrentBar:7:0,
              " date=",   Date:7:0,
              " time=",   Time:5:0,
              " chg=",    IFF( Changed, 1, 0 ):1:0,
              " mm=",     MM:8:4,
              " ps=",     PS:10:4,
              " tick=",   Tick:0:12,
              " bpv=",    BPV:10:4,
              " pv=",     PV:10:4,
              " dtick=",  DTick:10:6,
              " mind=",   MinD:0:12,
              " ordres=", OrdRes:0:4 );
   ```

   Copy from the Print Log into the TickSize result table: the `@ES` row
   (mm, ps, tick, bpv, dtick, mind), plus into the shared questions: did
   mm/ps change mid-chart (extra "chg=1" lines beyond bar 1 -> report the
   dates), and the `ordres` value for this run.

2. **Swing probe** (`RunTag = 1`), one run:

   ```EasyLanguage
   inputs:
       RunTag( 1 );

   variables:
       Ph( 0 ),
       SigA( 0 ), SigB( 0 ), SigC( 0 ), SigD( 0 ),
       Ha( 0 ), Hab( 0 ), Ha2( 0 ), Hab2( 0 ), Pa( 0 ),
       La( 0 ), Lab( 0 ), Pl( 0 ),
       Hb( 0 ), Hbb( 0 ), Pb( 0 ),
       Hc( 0 ), Hcb( 0 ),
       Hd( 0 ), Hdb( 0 ), Pd( 0 ),
       Hs( 0 ), Hsb( 0 );

   Ph = Mod( CurrentBar, 8 );

   { SigA -- one isolated peak (ph3) and one isolated trough (ph7) per cycle }
   SigA = 10;
   If Ph = 1 then SigA = 11;
   If Ph = 2 then SigA = 12;
   If Ph = 3 then SigA = 17;
   If Ph = 4 then SigA = 12;
   If Ph = 5 then SigA = 11;
   If Ph = 7 then SigA = 9;

   { SigB -- a FLAT TOP: ph3 and ph4 are equal maxima }
   SigB = 10;
   If Ph = 1 then SigB = 11;
   If Ph = 2 then SigB = 12;
   If Ph = 3 then SigB = 17;
   If Ph = 4 then SigB = 17;
   If Ph = 5 then SigB = 12;
   If Ph = 6 then SigB = 11;

   { SigC -- strictly rising forever: no pivot high and no pivot low, ever }
   SigC = CurrentBar * 0.05;

   { SigD -- three values inside the measured 2.22e-12 relational tolerance }
   SigD = 0.90;
   If Ph = 1 then SigD = 0.95;
   If Ph = 2 then SigD = 1.0000000000001;   { +1e-13 above ph3 }
   If Ph = 3 then SigD = 1.00;
   If Ph = 4 then SigD = 0.9999999999999;   { -1e-13 below ph3 }
   If Ph = 5 then SigD = 0.95;
   If Ph = 6 then SigD = 0.90;
   If Ph = 7 then SigD = 0.85;

   { Read every accessor into a variable BEFORE the Print, so a failure is
     legible rather than a blank line. }
   Ha   = SwingHigh(    1, SigA, 2, 20 );
   Hab  = SwingHighBar( 1, SigA, 2, 20 );
   Ha2  = SwingHigh(    2, SigA, 2, 20 );
   Hab2 = SwingHighBar( 2, SigA, 2, 20 );
   La   = SwingLow(     1, SigA, 2, 20 );
   Lab  = SwingLowBar(  1, SigA, 2, 20 );
   Hb   = SwingHigh(    1, SigB, 2, 20 );
   Hbb  = SwingHighBar( 1, SigB, 2, 20 );
   Hc   = SwingHigh(    1, SigC, 2, 20 );
   Hcb  = SwingHighBar( 1, SigC, 2, 20 );
   Hd   = SwingHigh(    1, SigD, 2, 20 );
   Hdb  = SwingHighBar( 1, SigD, 2, 20 );
   Hs   = SwingHigh(    1, SigA, 2,  5 );
   Hsb  = SwingHighBar( 1, SigA, 2,  5 );

   { The phase of the bar each function pointed at -- the answer, read
     directly. Meaningless when the matching bar column is the -1 sentinel;
     the -1 in that column says so. }
   Pa = Mod( CurrentBar - Hab, 8 );
   Pl = Mod( CurrentBar - Lab, 8 );
   Pb = Mod( CurrentBar - Hbb, 8 );
   Pd = Mod( CurrentBar - Hdb, 8 );

   If CurrentBar <= 100 then
       Print( File( "C:\Users\brian\source\repos\BacktestEngine\el_swing_output.txt" ),
              "run=",   RunTag:1:0,
              " bar=",  CurrentBar:5:0,
              " ph=",   Ph:2:0,
              " ha=",   Ha:6:2,
              " hab=",  Hab:4:0,
              " pa=",   Pa:2:0,
              " ha2=",  Ha2:6:2,
              " hab2=", Hab2:4:0,
              " la=",   La:6:2,
              " lab=",  Lab:4:0,
              " pl=",   Pl:2:0,
              " hb=",   Hb:6:2,
              " hbb=",  Hbb:4:0,
              " pb=",   Pb:2:0,
              " hc=",   Hc:8:2,
              " hcb=",  Hcb:4:0,
              " hd=",   Hd:0:13,
              " hdb=",  Hdb:4:0,
              " pd=",   Pd:2:0,
              " hs=",   Hs:6:2,
              " hsb=",  Hsb:4:0 );
   ```

   Copy from the Print Log, reading one full cycle from bar 25 onward, into
   the Swing result table: `pb` at every bar, smallest `hab` seen, `pa` at
   every bar, `hab`/`ha` at ph3/ph4, `hab2 - hab`, `hc`/`hcb` on the ramp,
   `la`/`pl`, `pd`, and the phases where `hs` (Length 5) is not -1.

---

## Chart 2 — MSFT, Daily, 2015 -> today

TickSize run 2 only — a stock, needed specifically because it is the only
chart in the whole set with a 0.01 tick and BigPointValue 1; nothing else
can share it without changing symbol/interval, which the probe forbids.

- Symbol: `MSFT`
- Interval: Daily
- Session: Regular Session
- Chart start: 2015-01-01 -> today
- Apply as: Indicator
- Max Bars Back: 10
- Costs: irrelevant

Study — same TickSize code as Chart 1, with `RunTag` set to `2`. Do not
delete `el_ticksize_output.txt` before this run (only before run 1); it
appends.

Copy into the TickSize result table: the MSFT row (mm, ps, tick, bpv,
dtick, mind), and whether `PointValue` compiled / matched `bpv` here too.

---

## Chart 3 — @HO, 60 min, 2007-01-01 -> today

TickSize run 3 only — this is the probe's sanity-check chart (`dtick` must
print exactly 4.20); it needs its own interval (60 min) and start date,
which none of the @OJ 240 min charts share, so it cannot be folded in.

- Symbol: `@HO`, continuous contract (same construction used for the
  earlier `@HO` probes, e.g. `EL_HO_WFSafeAtr_Probe.txt` — back-adjustment
  doesn't matter here, MinMove/PriceScale/BigPointValue are contract-level
  constants)
- Interval: 60 min
- Session: Regular Session
- Chart start: 2007-01-01 -> today
- Apply as: Indicator
- Max Bars Back: 10
- Costs: irrelevant

Study — same TickSize code as Chart 1, with `RunTag` set to `3`.

Copy into the TickSize result table: the `@HO` row, and confirm the sanity
check — `dtick` must print exactly `4.20`. If it does not, stop; nothing
else in the TickSize probe should be trusted until that's resolved.

---

## Chart 4 — @OJ, 240 min, 2007-01-01 -> today

Hosts **TickSize run 4**, **all of TLValue** (both runs), and **XAverage
run 1**. All three want the identical symbol / interval / session / chart
start, so sharing costs nothing — but do it in two passes, in this order,
because TLValue's run 2 is *designed* to halt the strategy engine with a
divide-by-zero error, and a halt on one study must not be allowed to
truncate the other two studies' output.

**Pass A — TLValue's halting run, in isolation.** Apply only this study to
a bare chart (no TickSize, no XAverage yet):

```EasyLanguage
inputs:
    RunTag( 2 ),
    DegenTest( 1 );      { set to 1 for run 2 -- expected to halt }

variables:
    P1( 0 ), P2( 0 ),
    V1( 0 ), V2( 0 ), V3( 0 ), V4( 0 ), V5( 0 ),
    Slope( 0 ), TwA( 0 ), TwB( 0 ),
    Degen( 0 );

P1 = High[10];      { the OLDER anchor }
P2 = High[2];       { the NEWER anchor }

{ The function under test, five ways. Read into variables before the Print
  so a failure is legible rather than a blank line. }
V1 = TLValue( P1, 10, P2, 2, 0 );                                  { bars-ago }
V2 = TLValue( P1, CurrentBar - 10, P2, CurrentBar - 2, CurrentBar );  { absolute }
V3 = TLValue( P1, 10, P2, 2, -5 );                          { 5 bars forward }
V4 = TLValue( P1, 10, P2, 2, 50 );                        { 40 bars past P1 }
V5 = TLValue( P2, 2, P1, 10, 0 );                        { anchors swapped }

{ Open-coded twins. Written out rather than calling a second built-in, so
  the comparison is statement for statement. Two anchorings, because they
  round differently. }
Slope = ( P2 - P1 ) / ( 2 - 10 );      { price per unit of BARS AGO }
TwA   = P1 + ( 0 - 10 ) * Slope;
TwB   = P2 + ( 0 - 2 ) * Slope;

{ Run 2 only: two anchors on the SAME bar. Expected to raise a runtime
  divide-by-zero (EL_ZeroRange_Probe.txt). Fired once, on bar 40, so the
  output up to that point survives. }
If DegenTest = 1 and CurrentBar = 40 then
    Degen = TLValue( P1, 5, P2, 5, 0 );

Print( File( "C:\Users\brian\source\repos\BacktestEngine\el_tlvalue_output.txt" ),
       "run=",   RunTag:1:0,
       " bar=",  CurrentBar:6:0,
       " date=", Date:7:0,
       " time=", Time:5:0,
       " p1=",   P1:0:6,
       " p2=",   P2:0:6,
       " v1=",   V1:0:6,
       " v2=",   V2:0:6,
       " v3=",   V3:0:6,
       " v4=",   V4:0:6,
       " v5=",   V5:0:6,
       " dA=",   ( ( V1 - TwA ) * 1000000000000000 ):0:4,
       " dB=",   ( ( V1 - TwB ) * 1000000000000000 ):0:4,
       " dAB=",  ( ( TwA - TwB ) * 1000000000000000 ):0:4,
       " d12=",  ( ( V1 - V2 ) * 1000000000000000 ):0:4,
       " d15=",  ( ( V1 - V5 ) * 1000000000000000 ):0:4,
       " fwd=",  ( ( V3 - V1 ) * 1000000 ):0:2,
       " degen=", Degen:0:6 );
```

Delete `el_tlvalue_output.txt` before this pass (or note in the file which
lines are run 2). Let it run to bar 40 and record the exact halt error
text and the bar number. Then **remove this study from the chart**
before Pass B, and if it left the chart in an error state, close and
reopen the chart to clear it.

Copy into the TLValue result table: "run 2: did it halt? exact error
text", and "run 2: if not, v5/degenerate value" (only if it didn't halt).

**Pass B — the combined main pass.** With the chart clean, apply all three
studies together:

1. **TickSize probe, run 4** (`RunTag = 4`) — same code as Chart 1, appending
   to the same `el_ticksize_output.txt` used by Charts 1–3. Max Bars Back
   10 for this study.

   Copy into the TickSize result table: the `@OJ` row, plus the shared
   `ordres` question — @OJ (0.05 tick) is one of only two charts in this
   whole set (with MSFT) that can show a non-zero operand-order residual.

2. **TLValue probe, run 1** (`RunTag = 1`, `DegenTest = 0`), the main run:

   ```EasyLanguage
   inputs:
       RunTag( 1 ),
       DegenTest( 0 );      { set to 1 for run 2 -- expected to halt }

   variables:
       P1( 0 ), P2( 0 ),
       V1( 0 ), V2( 0 ), V3( 0 ), V4( 0 ), V5( 0 ),
       Slope( 0 ), TwA( 0 ), TwB( 0 ),
       Degen( 0 );

   P1 = High[10];      { the OLDER anchor }
   P2 = High[2];       { the NEWER anchor }

   { The function under test, five ways. Read into variables before the Print
     so a failure is legible rather than a blank line. }
   V1 = TLValue( P1, 10, P2, 2, 0 );                                  { bars-ago }
   V2 = TLValue( P1, CurrentBar - 10, P2, CurrentBar - 2, CurrentBar );  { absolute }
   V3 = TLValue( P1, 10, P2, 2, -5 );                          { 5 bars forward }
   V4 = TLValue( P1, 10, P2, 2, 50 );                        { 40 bars past P1 }
   V5 = TLValue( P2, 2, P1, 10, 0 );                        { anchors swapped }

   { Open-coded twins. Written out rather than calling a second built-in, so
     the comparison is statement for statement. Two anchorings, because they
     round differently. }
   Slope = ( P2 - P1 ) / ( 2 - 10 );      { price per unit of BARS AGO }
   TwA   = P1 + ( 0 - 10 ) * Slope;
   TwB   = P2 + ( 0 - 2 ) * Slope;

   { Run 2 only: two anchors on the SAME bar. Expected to raise a runtime
     divide-by-zero (EL_ZeroRange_Probe.txt). Fired once, on bar 40, so the
     output up to that point survives. }
   If DegenTest = 1 and CurrentBar = 40 then
       Degen = TLValue( P1, 5, P2, 5, 0 );

   Print( File( "C:\Users\brian\source\repos\BacktestEngine\el_tlvalue_output.txt" ),
          "run=",   RunTag:1:0,
          " bar=",  CurrentBar:6:0,
          " date=", Date:7:0,
          " time=", Time:5:0,
          " p1=",   P1:0:6,
          " p2=",   P2:0:6,
          " v1=",   V1:0:6,
          " v2=",   V2:0:6,
          " v3=",   V3:0:6,
          " v4=",   V4:0:6,
          " v5=",   V5:0:6,
          " dA=",   ( ( V1 - TwA ) * 1000000000000000 ):0:4,
          " dB=",   ( ( V1 - TwB ) * 1000000000000000 ):0:4,
          " dAB=",  ( ( TwA - TwB ) * 1000000000000000 ):0:4,
          " d12=",  ( ( V1 - V2 ) * 1000000000000000 ):0:4,
          " d15=",  ( ( V1 - V5 ) * 1000000000000000 ):0:4,
          " fwd=",  ( ( V3 - V1 ) * 1000000 ):0:2,
          " degen=", Degen:0:6 );
   ```

   Max Bars Back 30 for this study. This appends run-1 lines into the same
   `el_tlvalue_output.txt` that already holds Pass A's run-2 lines.

   Copy into the TLValue result table, reading any bar past 100: `p1`/`p2`,
   `v1`–`v5`, `dA`, `dB`, `dAB`, `d12`, `d15`, `fwd`, and whether each is
   constant across bars.

3. **XAverage probe, run 1** (`Length = 20`, `RunTag = 1`), applied as a
   **Strategy** (not an indicator — it needs the study's own first-calculated-bar
   and the MultiWalk library to be available):

   ```EasyLanguage
   inputs:
       Length( 20 ),
       RunTag( 1 );

   variables:
       SF( 0 ),
       Xa( 0 ),
       Wf( 0 ),
       EmaEL( 0 ),      { seeded with Price, EL-source recurrence }
       EmaWt( 0 ),      { seeded with Price, weighted recurrence }
       EmaAvg( 0 ),     { seeded with a fresh simple average at bar Length }
       FreshSum( 0 ),
       kk( 0 );

   SF = 2 / ( Length + 1 );

   Xa = XAverage( Close, Length );
   Wf = WFSafe_XAverage( Close, Length );   { delete this line and the wf/ovr
                                              fields if TS rejects the word --
                                              and say so, that is the finding }

   { Twin A -- seeded with the PRICE on the study's first calculated bar, then
     the EL-source recurrence, written as its own statement so the rounding is
     EL's and not a re-association of it. }
   If CurrentBar = 1 then
       EmaEL = Close
   Else
       EmaEL = EmaEL[1] + SF * ( Close - EmaEL[1] );

   { Twin B -- identical seed, the WEIGHTED recurrence. Algebraically the same
     as Twin A and not the same in floating point; the gap between them is the
     d3 column. }
   If CurrentBar = 1 then
       EmaWt = Close
   Else
       EmaWt = SF * Close + ( 1 - SF ) * EmaWt[1];

   { Twin C -- the textbook seed: a fresh Length-term simple average at bar
     Length, then the same recurrence. Open-coded loop, not a call to
     Average, so the comparison is statement for statement. }
   If CurrentBar = Length then Begin
       FreshSum = 0;
       For kk = 0 To Length - 1 Begin
           FreshSum = FreshSum + Close[kk];
       End;
       EmaAvg = FreshSum / Length;
   End
   Else If CurrentBar > Length then
       EmaAvg = EmaAvg[1] + SF * ( Close - EmaAvg[1] );

   Print( File( "C:\Users\brian\source\repos\BacktestEngine\el_xaverage_output.txt" ),
          "run=",   RunTag:1:0,
          " bar=",  CurrentBar:6:0,
          " date=", Date:7:0,
          " time=", Time:5:0,
          " c=",    Close:0:6,
          " sf=",   SF:0:15,
          " xa=",   Xa:0:12,
          " wf=",   Wf:0:12,
          " ovr=",  ( ( Wf - Xa ) * 1000000000000 ):0:4,
          " d1=",   ( ( Xa - EmaEL ) * 1000000000000000 ):0:4,
          " d2=",   ( ( Xa - EmaAvg ) * 1000000000000 ):0:4,
          " d3=",   ( ( EmaEL - EmaWt ) * 1000000000000000 ):0:4 );
   ```

   Max Bars Back 250, Contracts 1, Pyramiding off, no orders placed. Do NOT
   guard the Print with a date filter on this run — the seed (Q1/Q4) is
   only visible in the first ~20 bars of run 1.

   Copy into the XAverage result table's "run 1" column: `sf`, `xa` on bar
   1, `Close` on bar 1, `d1` on bars 1/2/100, `d2` on bar 100, `d3`'s
   typical magnitude past bar 100, largest `|ovr|` anywhere, first bar
   where `xa` is non-zero, whether `WFSafe_XAverage` compiled, and the
   full `WFSafe_` list from Step 0.

---

## Chart 5 — @OJ, 240 min, 2010-01-01 -> today

**XAverage run 2** only. This is the seed-memory half of the probe (Q2) —
it must be a chart whose start date differs from Chart 4's, so it cannot
be merged there; everything else about it is identical to Chart 4's
XAverage study.

- Symbol: `@OJ`, continuous contract, same construction as Chart 4
- Interval: 240 min
- Session: Regular Session
- Chart start: 2010-01-01 -> today
- Apply as: Strategy
- Max Bars Back: 250, Contracts: 1, Pyramiding: off

Study — identical EasyLanguage to Chart 4/Study 3 above, with `RunTag` set
to `2`. This appends run-2 lines into the same `el_xaverage_output.txt`
Chart 4 wrote run-1 lines into.

Copy into the XAverage result table's "run 2" column (same fields as
Chart 4), plus, once both runs are back, compare them offline: roughly
where do run 1's and run 2's `xa` columns converge to bit-identical
values (the seed-memory answer, Q2).

---

## What could not be consolidated, in one line each

- **TickSize's four charts (1–3, and OJ inside Chart 4)** cannot merge:
  the probe is specifically about whether MinMove/PriceScale/BigPointValue
  differ *by symbol*, so each of @ES, MSFT, @HO, @OJ needs its own chart by
  construction.
- **Chart 4 and Chart 5 (both @OJ 240 min)** cannot merge: XAverage's whole
  Q2 (seed memory) requires two different chart-start dates on otherwise
  identical setups, so the two starts must be two charts.
- **TLValue's DegenTest=1 pass** cannot run alongside TickSize/XAverage on
  Chart 4: it is engineered to halt the strategy engine with a
  divide-by-zero on bar 40, which would truncate whatever else was
  computing on that chart. It runs alone, first, and is removed before the
  other two studies go on.

---

## Pre-registered predictions — checklist for a registry defect

If any of these come back different from the prediction, that is a defect
in `symbols/*.json` or in an existing settled finding, not noise — stop and
report it before interpreting the rest of that probe.

- [ ] `@ES`: tick = `0.25`, BigPointValue = `50` (dtick = 12.50). Dyadic
      tick, so `ordres` should be exactly `0` here — a non-zero value would
      itself be the finding, not a registry defect.
- [ ] `@HO`: tick = `0.000100000000`, BigPointValue = `42000`, and
      **`dtick` must print exactly `4.20`** — the probe's own sanity check;
      if this fails, nothing else in TickSize should be trusted.
- [ ] `@OJ`: tick = `0.05`, BigPointValue = `150` (dtick = 7.50). Non-dyadic
      tick — this and MSFT are the only two charts where `ordres` can come
      back non-zero.
- [ ] `MSFT`: not in `symbols/*.json` (confirmed — no `symbols/MSFT.json`
      exists today); predicted tick `0.01`, BigPointValue `1` purely by
      convention for US equities, not from our registry. A different
      result here is a fact to record, not a defect to fix.
- [ ] `PointValue` prediction: equals `BigPointValue` on every chart
      (`pv == bpv`); if TradeStation rejects the identifier, that's a
      finding too (delete the field, don't block on it).
- [ ] Swing Q1 (ties): merged corpus assumes at-or-above on both sides
      (`>=`) — predict `pb = 4` (the later of the two flat-top bars).
- [ ] Swing Q2 (lag): predict pivots confirm exactly `strength` (2) bars
      late and never sooner — `hab >= 2` on every bar, `pa` constant at 3.
- [ ] Swing Q4 (not found): predict the `-1` sentinel on the strictly
      rising ramp (`hc = -1`, `hcb = -1`), consistent with the `-1`
      sentinel `EL_DayRef_Probe.txt` already found for the `xxxD` family.
- [ ] Swing/XAverage Q5: predict **no** `WFSafe_Swing*` overrides exist (a
      swing scan holds no accumulator to break under walkforward), but
      predict `WFSafe_XAverage` **does** exist (SF is a load-time constant
      from Length, the same failure mode as ADX/RSI) and, at fixed Length,
      is identical to the plain built-in (`ovr = 0` everywhere), matching
      the `WFSafe_ADX`/`WFSafe_RSI` precedent.
- [ ] TLValue Q2 (convention): predict a pure two-point interpolation,
      `d12 = 0` on every bar (bar numbers are the caller's convention, not
      read against `CurrentBar` internally).
- [ ] TLValue Q4 (degenerate): predict a runtime divide-by-zero halt on
      bar 40 of run 2, matching `EL_ZeroRange_Probe.txt`.
- [ ] XAverage Q1 (seed): predict seeding with `Close` on the study's first
      calculated bar (`d1 = 0` from the first printed bar), not a
      Length-term simple average (`d2 != 0`).
- [ ] XAverage `sf`: predict exactly `0.095238095238095` (`2/21`).
- [ ] XAverage Q3 (recurrence form): predict `d3 != 0` on most bars (the
      two algebraically-identical recurrences round differently on @OJ's
      non-dyadic tick) together with `d1 = 0` (EL uses the
      `X[1] + SF*(P - X[1])` form).
