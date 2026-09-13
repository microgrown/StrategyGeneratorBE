# SwingHigh / SwingLow / SwingHighBar / SwingLowBar — measured

Probe: `C:\Users\brian\source\repos\BacktestEngine\EL_Swing_Probe.txt`
Output: `C:\Users\brian\source\repos\BacktestEngine\el_swing_output1.txt` (chart 1, @ES 60 min, bars 1..100)
MultiWalk override check: reported by Brian — **there is no `WFSafe_SwingHigh` in
the MultiWalk library**, so plain EasyLanguage `SwingHigh`/`SwingLow` are the
functions the MW twins call and the functions the C++ must mirror.

Both sanity checks passed. The whole 21-column pattern repeats with period 8 on
**76/76 bars from bar 25 onward** — every phase's row is identical across all
nine-and-a-bit cycles — so the functions really are reading the variables they
were passed. And `SwingLow` mirrors `SwingHigh`: it finds SigA's ph7 trough
(`la=9.00`, `pl=7`) on all 92 bars from bar 9.

---

## 1. The probe's results table, filled in

Read one full cycle from bar 25 onward.

| question | answer |
|---|---|
| `pb` at every bar (flat top: 3, 4, or −1) | **4**, on all 95 bars where `hbb <> -1` (bars 6..100). Never 3, never −1 past warm-up |
| smallest `hab` seen anywhere in the run | **2** — exactly `Strength`. Never 0 or 1 on any of the 100 bars (−1 on bars 1..4 only, then 2..9) |
| `pa` at every bar (should be constant) | **3**, on all 96 bars where `hab <> -1` |
| `hab` at ph3 / ph4 (during the lag) | **8 / 9** — the previous cycle's ph3 |
| `ha` at ph3 / ph4 (during the lag) | **17.00 / 17.00** — the prior pivot's price, not −1 and not the unconfirmed candidate |
| `hab2 − hab` (occurrence spacing) | **8** on every steady-state bar (one full cycle), 76/76 from bar 25. `ha2 = -1` only on bars 1..12, before a second pivot exists |
| `hc` / `hcb` on the ramp (the sentinel) | **−1.00 / −1** on all 100 bars |
| `la` / `pl` (does SwingLow mirror it?) | **9.00 / 7** on all 92 bars from bar 9; min `lab` = 2. Yes |
| `pd` (tolerance: 2, 4, or `hd = -1`) | **4**, with `hd = 0.9999999999999` — ph4's own value |
| phases where `hs` (Length 5) is not −1 | **ph5, ph6, ph7 only** (`hsb` = 2, 3, 4); −1 at ph0..ph4, where the pivot is 5..9 bars back |
| `WFSafe_` names in the MW library | Not re-reported this round; the five on file stand (`WFSafe_AvgTrueRange`, `WFSafe_ADX`, `WFSafe_DirMovement`, `WFSafe_RSI`, `WFSafe_SummationFC`) |
| does `WFSafe_SwingHigh` compile? | **No** — Brian reports it is not in the library. Plain EL governs |

---

## 2. The questions, answered

### Q1 — comparison sense and ties: MIXED, and the merged corpus's `>=`-on-both-sides is WRONG

SigB's flat top (ph3 = ph4 = 17) produces **exactly one pivot per cycle, at the
LATER bar (ph4)**. `pb = 4` on every bar past warm-up and never 3, so ph3 is not
a pivot at all — if the sense were at-or-above on both sides, ph3 would also be
one and would be reported as occurrence 1 at ph5 with `hbb = 2`.

Proof — at ph5 the scan skips the just-completed ph3 entirely and still points at
the *previous* cycle's ph4, nine bars back; two bars later it picks up the new
ph4:

```
run=1 bar=   29 ph= 5 ... hb= 17.00 hbb=   9 pb= 4      <- 29-9 = bar 20 = ph4
run=1 bar=   30 ph= 6 ... hb= 17.00 hbb=   2 pb= 4      <- 30-2 = bar 28 = ph4
```

So the pivot bar must be **at or above the `Strength` OLDER bars** (ph4 ties ph3
and survives) and **strictly above the `Strength` NEWER bars** (ph3 ties ph4 and
dies). That is TradeStation's documented `SwingHighBar` shape — `> Highest(newer
side)` and `>= Highest(older side)` — and it means a flat ledge yields exactly
one pivot, not N and not zero.

### Q2 — confirmation lag: exactly `Strength` bars, and the PRIOR pivot is returned in between

`hab` is never 0 or 1 anywhere in the run; its minimum over all 100 bars is
**2 = Strength**, hit at ph5 which is ph3 + 2. There is no lookahead. During the
two-bar lag the function returns the **previous** confirmed pivot — not −1, not
the candidate:

```
run=1 bar=   35 ph= 3 ha= 17.00 hab=   8 pa= 3       <- 35-8 = bar 27, the PRIOR ph3
run=1 bar=   36 ph= 4 ha= 17.00 hab=   9 pa= 3       <- 36-9 = bar 27, the same pivot
run=1 bar=   37 ph= 5 ha= 17.00 hab=   2 pa= 3       <- 37-2 = bar 35, the NEW pivot
```

`pa = 3` on all 96 non-sentinel bars: the reported pivot is always a ph3 bar, so
the answer only ever steps from one true pivot to the next.

### Q3a — Occurrence: 1 = most recent confirmed, 2 = the one before it

`hab2 − hab = 8` — exactly one cycle, i.e. one pivot — on every steady-state bar
(76/76 from bar 25), with `ha2 = 17.00`. `ha2` is −1 only on bars 1..12, before a
second pivot exists in the window. Occurrence 2 becomes available at bar 13 and
`hab2` reaches 17 at ph4, comfortably inside Length 20. Occurrence 3+ was never
printed.

### Q3b — Length: bars back from the current bar, INCLUSIVE (candidate offsets 0..Length−1)

With Length 5, `hs` is non-−1 only when the pivot is 2, 3 or 4 bars back
(`hsb ∈ {2,3,4}`, phases ph5/ph6/ph7) and −1 the moment it is 5 bars back
(`hs = -1.00, hsb = -1` at ph0..ph4). So the candidate window is offsets
`0..Length-1`, and a pivot older than the window returns **−1 rather than falling
back to an earlier pivot**.

Two consequences the mirror must copy. First, `Length` does **not** have to
exceed `2*Strength+1` for a pivot to be reported at the window's far edge: the
bars-ago-4 pivot is returned under Length 5 even though the two older bars its
test needs (5 and 6 bars back) sit *outside* the window — the neighbourhood test
reaches `Strength` bars past `Length`, so the data requirement is
`Length - 1 + Strength` bars of history. Second, the effective reportable range
is `Strength .. Length-1`, so a `Length <= Strength` can never return anything.
Behaviour at `Length < Strength+1` and at `Length = 0` was not printed — that
part stays **UNKNOWN**.

### Q4 — not found: the −1 sentinel is real, for both the price and the bar form

SigC (a strictly rising ramp, no pivot ever) gives `hc = -1.00` and `hcb = -1` on
all 100 bars. It does not degrade to "the highest bar seen" and it does not
return 0. Since −1 as a *price* sits below every real price, every corpus rule
comparing a price against `SwingHigh(...)` needs an explicit `<> -1` guard.

### Q5 — tolerance: the pivot test carries the 2.22e-12 relational tolerance

SigD's three values within 2.22e-12 of one another report `pd = 4` with
`hd = 0.9999999999999` — ph4's own value, the *last* bar of the tolerance-equal
run. Under raw IEEE comparison with the sense measured in Q1 the pivot would be
ph2 (the +1e-13 bar, the raw strict maximum) and `pd` would read 2. It reads 4 on
95/95 non-sentinel bars, e.g. `bar= 30 ... hd=0.9999999999999 hdb= 2 pd= 4`.

The measured answer is exactly `el_gt`/`el_ge` from
`C:\Users\brian\source\repos\BacktestEngine\src\bt\core\el_compare.h`:

* ph2 rejected: `el_gt(1.0000000000001, 1.00)` → `1e-13 > 2.22e-12` is false — fails on the newer side
* ph3 rejected: `el_gt(1.00, 0.9999999999999)` → false, same reason
* ph4 accepted: `el_ge(0.9999999999999, 1.0000000000001)` → `-2e-13 >= -2.22e-12` is true on the older side, and `el_gt(0.9999999999999, 0.95)` on the newer side

So the mirror must use the toleranced helpers **inside** the swing scan, not raw
`>`/`>=`. This is consistent with `el_compare.h`'s own note that EL's standard
functions are themselves EasyLanguage and carry the tolerance like any other
comparison.

### Warm-up over a variable

Bars 2..8 return `la = 0.00` with `lab` 2..8: the scan reached into the
variable's **zero-filled pre-assignment history** and reported a spurious swing
low at 0. Same shape as the `countif` and `percentile` rows. A swing over a
computed series is only trustworthy once `MaxBarsBack` real bars exist.

---

## 3. Replacement register rows

Same column layout as `rules/EL_FEATURES.md`: `| Feature | Status | What is known | Evidence |`.
The orchestrator applies these; this file does not edit the registry.

```
| `swinghigh` | VERIFIED | `SwingHigh(Occurrence, Price, Strength, Length)` returns the PRICE of the Occurrence-th most recent confirmed pivot, or the **−1 sentinel** when none lies in the window (measured on a strictly rising ramp: −1 on 100/100 bars — every rule comparing a price against it needs an explicit `<> -1` guard, since −1 sits below every real price). **The pivot test is MIXED, not at-or-above on both sides**: the pivot bar is at-or-above the `Strength` OLDER bars and STRICTLY above the `Strength` NEWER bars, so a flat top yields exactly ONE pivot, the LATER of the equal bars (`pb` = 4, never 3, on 95/95 bars). **Confirmation lag is exactly `Strength` bars** — the smallest bars-ago ever returned is 2 at Strength 2, never 0 or 1, so it is lookahead-safe; during the lag it returns the PREVIOUS pivot (bars-ago 8 / 9 at ph3 / ph4), not −1 and not the unconfirmed candidate. **Occurrence** 1 is the most recent confirmed pivot, 2 the one before it (spacing exactly one pivot on 76/76 steady-state bars). **Length** counts bars back from the current bar INCLUSIVE (candidate offsets `0..Length-1`); a pivot older than that returns −1 rather than an earlier pivot, and Length need NOT exceed `2*Strength+1` — the neighbourhood test reaches `Strength` bars PAST the window (a bars-ago-4 pivot is reported under Length 5), so the mirror needs `Length-1+Strength` bars of history. **The comparisons carry the 2.22e-12 relational tolerance** (`el_gt`/`el_ge`, not raw): three values within 1e-13 of each other pivot on the LAST of the run, where raw IEEE would pivot on the first. Over a VARIABLE, warm-up scans zero-filled pre-history and can report a spurious pivot at 0. No MultiWalk override exists — plain EL governs. Unmeasured: `Length` below `Strength+1`, `Length = 0`, and Occurrence 3+ | `EL_Swing_Probe.txt`; `el_swing_output1.txt` (@ES 60 min, bars 1..100; pattern period-8 stable on 76/76 bars from bar 25) |
| `swinglow` | VERIFIED | Mirror of `swinghigh`, measured on the same run: finds SigA's isolated trough at the same `Strength` lag with the same −1 sentinel (`la` = 9.00 and a constant 7-phase on 92/92 bars from bar 9, min bars-ago = 2 = Strength). Occurrence, Length, lag and sentinel semantics are the `swinghigh` row's, measured on the same output. **The TIE sense on the low side is inferred, not measured** — the probe's flat-extreme series (SigB) is a flat TOP only, so "at-or-below the `Strength` older bars, strictly below the `Strength` newer bars" is the mirror of the measured high-side rule rather than an observation; a flat-bottom series would settle it. Same zero-filled warm-up caution (bars 2..8 return a spurious pivot at 0.00). No MultiWalk override | `EL_Swing_Probe.txt`; `el_swing_output1.txt` |
| `swinghighbar` | VERIFIED | `SwingHighBar(Occurrence, Price, Strength, Length)` returns the same pivot as `SwingHigh` expressed as a **plain bars-ago count from the current bar**, in `Strength..Length-1`, with **−1** when there is no pivot in the window (−1 on 100/100 ramp bars). Never 0 or 1 at Strength 2 — the `Strength`-bar confirmation lag bounds it below; occurrence 2 lands exactly one pivot older (`hab2 - hab` = 8 on 76/76 steady-state bars); a pivot older than `Length-1` gives −1, not the previous pivot (Length 5: reported at bars-ago 2/3/4, −1 at 5 and beyond). Whether that bars-ago count is the convention `TLValue` wants as a bar argument is still `tlvalue`'s question and is NOT settled here. No MultiWalk override | `EL_Swing_Probe.txt`; `el_swing_output1.txt` |
| `swinglowbar` | VERIFIED | Mirror of `swinghighbar`, measured on the same run (bars-ago 2..9 across the cycle, min 2 = Strength, −1 before the first pivot, one pivot per cycle). Inherits `swinglow`'s one caveat: the low-side TIE sense is the mirror of the measured high-side rule rather than an observation | `EL_Swing_Probe.txt`; `el_swing_output1.txt` |
```

---

## 4. The C++ mirror the authoring pass should use

Corpus dialect: `high[k]` / `low[k]` / `close[k]` are `k` bars ago, `[0]` is the
current bar. `el_gt` / `el_lt` / `el_ge` / `el_le` are from
`C:\Users\brian\source\repos\BacktestEngine\src\bt\core\el_compare.h`
(`a - b > 2.220446049250313e-12` and `a - b >= -2.220446049250313e-12`).

`swingHigh(strength)` in merged pseudocode means: **the bar `strength` bars ago
is a confirmed swing high, as known on the current bar.** One definition, and it
is a pure fixed-offset test — no scan-back, no state:

```cpp
// True on the current bar iff high[strength] is a confirmed swing high.
// Needs 2*strength+1 bars of history.
bool swingHigh(int strength) {
    for (int k = 0; k < strength; ++k)                  // NEWER bars: strength-1 .. 0
        if (!el_gt(high[strength], high[k])) return false;       // STRICT
    for (int k = strength + 1; k <= 2 * strength; ++k)  // OLDER bars: strength+1 .. 2*strength
        if (!el_ge(high[strength], high[k])) return false;       // AT-OR-ABOVE
    return true;
}

bool swingLow(int strength) {                           // mirrored; the tie side is inferred
    for (int k = 0; k < strength; ++k)
        if (!el_lt(low[strength], low[k])) return false;         // STRICT
    for (int k = strength + 1; k <= 2 * strength; ++k)
        if (!el_le(low[strength], low[k])) return false;         // AT-OR-BELOW
    return true;
}
```

In one line: **strictly greater than the `strength` bars that came after it;
greater than or equal to the `strength` bars that came before it; both
comparisons toleranced; known `strength` bars late, so at the moment of detection
the pivot's price is `high[strength]` and its bars-ago is `strength`.**

For "the last swing high", which is what most rules actually want, the pivot must
be **latched** when `swingHigh(strength)` fires — price `high[strength]`, bar
`CurrentBar - strength` — and carried forward across the lag, because carrying
the previous pivot forward is exactly what EL does. A rule that instead
recomputes `SwingHigh(1, High, strength, Length)` on every bar must guard
`<> -1` before comparing it to a price, and must accept that the answer goes
*stale* rather than blank once the pivot ages past `Length - 1`, at which point
it goes to −1 with no fallback.

Bars of history required: `Length - 1 + strength` (the window reaches
`Length - 1` bars back for candidates, and each candidate's older-side test
reaches `strength` further).

---

## 5. What this contradicts

`reference/brooks/merged/swing_structure.json`, rule key `SwingHigh`, pseudocode:

```
high[strength] >= highest(high, strength)[0]
&& high[strength] >= highest(high, strength)[strength + 1]
```

**Half of it is wrong.** The older-side `>=` (the second clause) is right. The
newer-side comparison must be **strict `>`**, not `>=`. The merge notes chose
`>=` on both sides deliberately and flagged it as a guess — "TIE BEHAVIOUR: with
`>=` a flat run of equal highs makes every bar in the run a swing high ... Kept
`>=` per the glossary" — and the guess is refuted. Concretely:

1. **A flat ledge produces ONE pivot, not N.** The merged reading makes every bar
   of a flat top a swing high; the measurement makes only the last one a pivot.
   This changes `Ledge`, `DoubleExtreme`, `MicroDoubleExtreme` and every flat-top
   / double-top rule — and it removes the noise the merge notes worried about, so
   the "expose the sense as a structural constant if flat ledges prove noisy"
   escape hatch is no longer needed.
2. **Pivot-counting rules count differently.** Under `>=` a three-bar flat top
   emits three pivots and inflates `HigherSwingHigh`, `TrendingSwings`,
   `HigherLowCount`, `TrendingHighsAndLows` and `LaggedHigherHigh`; under the
   measured sense it emits one.
3. **The comparisons are toleranced.** The merged pseudocode's bare `>=` implies
   raw IEEE. `el_ge`/`el_gt` are required, and on SigD the two disagree about
   *which* bar is the pivot — not a cosmetic difference.
4. **Brooks's glossary wording is not the EL function.** "Its high is at or above
   that of the bar before it and that of the bar after it" is symmetric; EL is
   not. Where a rule's *source* is Brooks's prose and its *implementation* is
   `SwingHigh`, the two now differ on flat bars, and each such rule deserves a
   line saying so.

Unchanged and confirmed by the measurement: the `strength` parameter with default
2, the `strength`-bar confirmation lag (so detection really is lookahead-safe),
and the "simple — no persistence, no scan-back" complexity grade for *detection*.
The retention machinery in the second design decision (a ring of the last four
same-side pivots plus a staleness cap) is still needed and still separate —
though note that EL's own `Length` **is** a staleness cap with −1 as its answer,
which is a cheaper model than the ring for the rules that only need "the last
one".

## Still open

* **Low-side tie sense** — not measured; SigB is a flat top only. Presumed mirror.
* **`Length` below `Strength+1`, and `Length = 0`** — never printed.
* **Occurrence 3+** — never printed; only occurrences 1 and 2 were exercised.
* **The full `WFSafe_` list** — not re-reported this round; only the absence of
  `WFSafe_SwingHigh` was confirmed, and the compile-check text is not on file.
* **`SwingHighBar`'s bars-ago vs `TLValue`'s bar argument** —
  `EL_TLValue_Probe.txt`'s question, untouched here.
