# OneNote notebook triage (`Strategies.pdf`)

Source: Brian's OneNote notebook, exported to PDF (97 pages, notes dated 2024-10-05 .. 2026-01-03).
Triaged 2026-11-05 for the source-publicity OOS study (the "own rules" arm): every
note is listed once, with a status and the reason.

Page numbers are the notebook's printed `Page N` footers (PDF page = N + 1).
Provenance evidence used: the typed text, the 11 embedded hyperlinks (resolved with
YouTube oEmbed: 7 are the channel "Algo Trading With Kevin Davey", 1 is "The Secret
Mindset"), and a page-by-page survey of the images (Davey thumbnails and
kjtradingsystems.com slide captures, a scanned 2B diagram, Copilot screenshots).

## Status key

| Status | Meaning |
|---|---|
| KEEP | Brian's own idea, concrete enough to author (concretization noted) |
| KEEP? | Looks like Brian's own, but provenance needs his confirmation (see Questions) |
| INFO | Brian's own, but cannot be authored without a missing definition (see Questions) |
| X-DAVEY | Kevin Davey idea: linked video, named, or a direct derivative of one |
| X-CLASSIC | Brian's note, but only the most obvious use of a classic construct (Brian 2026-11-05: excluded) |
| X-EXT | Other external source (non-Davey video, book figure, AI chat) |
| DEFER | Research project or open-ended sketch; not authored in this study |
| NOTE | Not a trading rule (study question, plan, process note) |

## Notes

| # | Note | p. | Status | Idea / reason |
|---|---|---|---|---|
| 1 | 20241005.1 Idea 1 | 1-2 | KEEP | Channel from a non-alternating X-bar (5-7) swing low that is also the lowest low of 20-40 bars, then an X-bar swing high, neither taken out. The opposite ordering (swing high first, then swing low) is also a channel (Brian 2026-11-05). After the most recently hit side: a 2-bar swing toward the middle, then a 2-bar swing that fails short of the hit side; enter away from that side. Hard but defined. |
| 2 | 20241005.1 Idea 2 | 2 | KEEP | Idea 2, per Brian 2026-11-05: once the channel of Idea 1 is recognized, wait for an X-bar (same X) swing HIGH to form inside it; short the first time a bar's high goes above that swing high. Mirrors with the channel's opposite ordering. |
| 3 | 20241005.1 Idea 3 | 2 | KEEP | Inner box from a second opposite swing pair inside the channel, height at least 3 x ATR(50). Close below the inner box but above the outer box, then long on the first close back above the inner box low. Hard, defined. |
| 4 | 20241005.2 | 3 | KEEP | Support from two 7-bar swing lows at a similar price (make "similar" an ATR tolerance), not yet broken. A close below it; the first bar back above is the setup bar; a red close back below support within 5 bars of the break means short. A second close above invalidates. |
| 5 | 20241005.3 | 4 | X-DAVEY | Big-doji plus 10-bar momentum. "Taken directly from Kevin Davey video" (CRAZY Algo Trading Strategy...); thumbnail on page. |
| 6 | 20241006.1 | 5 | KEEP | Study question "does a big bar (range at least 2 x ATR15) follow through or reverse?" Concretized as a bar-range rule plus its reverse. The library already has `BarRangeAtrMultiple`. |
| 7 | 20241013.1 | 6 | KEEP | RSI inside a band (40-60 / 35-65 / 30-70) for the last 50 bars, then falls below the lower bound; long on the first green close; invalidated if RSI re-enters the band first. Reverse asked for explicitly. |
| 8 | 20241020.1 | 7 | X-DAVEY | "Algo Trading Mini S&P Algo": a Davey video (link resolves to his channel), thumbnail on page. |
| 9 | 20241020.2 | 8-9 | X-DAVEY | "Algo Trading Entry That Works In TODAY'S Markets!": a Davey video; his EasyLanguage slide with the kjtradingsystems.com watermark is on the page. |
| 10 | 20241020.3 | 10 | X-DAVEY | "An Entry Technique That Works TODAY!" (Bollinger band plus momentum): a Davey video. |
| 11 | 20241020.4 | 11 | KEEP | Two swing lows at about the same level, with an earlier, lower swing low (1-3 ATR lower) not yet taken out. Long on a bar with low below the earliest swing low and close above it. AD H8 chart with own annotations. |
| 12 | 20241020.5 | 12 | KEEP | Large bull bar (2-7 ATR, open in the bottom quarter, close in the top quarter); 3-5 following bars each under 0.5 x its range, all inside high +/- 0.4 x range. Long. |
| 13 | 20241020.6 | 14 | KEEP | Large bull bar (over 2 ATR, open in the bottom quarter, close in the top quarter). Price holds between its 50% retracement and 50% extension for at least 5 bars; short on the first close below the 50% retracement. |
| 14 | 20241020.7 | 15 | X-DAVEY | Close above the close 100-150 bars ago, and low below the lower Bollinger band: long. Written the same day as three Davey video notes, and it is his long-momentum-plus-pullback pattern with a Bollinger trigger. See Q3. |
| 15 | 20241020.8 | 16 | X-DAVEY | Close above the close 150-200 bars ago but below the close 50-80 bars ago, and high touches the upper Bollinger band: long. The momentum window is Davey's (#8, #29). See Q3. |
| 16 | 20241020.9 | 17 | X-DAVEY | Close above the close 100-150 bars ago but below the close 25-50 bars ago, and a strong bull bar (open in the bottom third, close in the top third, close above the prior high): long. Same Davey window. See Q3. |
| 17 | 20241022.1 | 18 | X-CLASSIC | Opening-range breakout, entry within 3 bars, range between 1 and 5 ATR. The per-timeframe opening ranges `'W'`, `'D'`, `'T1'`, `'T2'` are Brian's intraday windows, not defined in the notebook. See Q6. |
| 18 | 20241023.1 | 19 | X-CLASSIC | ORB variant: range over X ATR (2-4), only in the direction of 100-150-bar momentum. Same window question as #17. |
| 19 | 20241023.2 | 20 | X-CLASSIC | Opening-range takeout: a high breaks above the range, then a close below the range low, short. Same window question as #17. |
| 20 | 20241025.1 / .2 | 21-22 | KEEP | RSI(14) inside 45-55 or 40-60 for at least 5 bars, and the signal bar takes it out of the range. A green signal bar means short (.1) or long (.2): one rule and its reverse. |
| 21 | 20241025.3 | 23 | KEEP | Large (over 1.5 ATR) standard bear bar (open/close within about 1/3 of the extremes) closing at or near the 20-bar low; the next bar makes a lower low but closes in the bottom 20% of the large bar's range. Short. |
| 22 | 20241026.1 | 24 | X-CLASSIC | Bullish engulfing (prior bar red; lower low and close above the prior high). Long. EMA stack (7-14, 2x, 3x) as a pane-2 condition. |
| 23 | 20241107.1 | 25 | X-EXT | Image-only note: a scanned "2B Buy / 2B Sell" diagram, Victor Sperandeo's named pattern (Trader Vic books). |
| 24 | 20241113.1 | 26 | KEEP | Huge bear bar (open near the high, close near the low) takes out the X-bar low (10-50). A bullish inside bar (open near its low, close near its high) follows before the bear bar's high is taken out; short on the close of the first red bar after. Own EA screenshots. |
| 25 | 20241113.2 | 27 | KEEP | 50-bar breakout candles classed L / H / C (consolidation). Pattern L-C...C-L (or H-C...C-H). The notebook gives no direction; pane 1's reverse covers both. |
| 26 | 20250116.1 | 28 | KEEP | Price in a range (I3 / I1 as pane-2), then an unbroken run of red bars that starts at or above the upper of two stacked I2 support zones and whose last close is below the lower one: long (fade). Reading confirmed by Brian 2026-11-05. |
| 27 | Test these | 29 | NOTE | Method notes (pair range indicators with mean reversion, long structure with short triggers). |
| 28 | 20250206.1 | 30 | X-DAVEY | "From Kevin Davey": close above close[200], close below close[X], ADX over Y. |
| 29 | 20250208.1 / .1b | 31 | KEEP | Large bar (at least 2 ATR14) with low below the X-bar low but above the (Y x X)-bar low, and close in the top 20%. Long. .1b drops the size and close requirements; parameterize, don't author twice. |
| 30 | 20250221.1 | 32 | KEEP | Consolidation (X-bar high minus low under Y x ATR(X)). The breakout bar opens inside the zone and closes at least Z x ATR above the prior X-bar high. Long. |
| 31 | 20250221.2 | 33 | KEEP | Failed breakout: the same trigger, short. This is #30's reverse; one rule. Its "exit on the first low back below the breakout point" can go to the exit pool. |
| 32 | 20250221.3 | 34 | KEEP | Breakout and retest: the first bar after #30's breakout with a low inside the zone and a close above it. Long. |
| 33 | 20250221.4 | 35 | KEEP | Continuation: the first close above the high of #30's breakout bar. Long. |
| 34 | 20250222.1 | 36 | KEEP | Large consolidation (X 40-60, Y 5-7); short when the close is in the top 25% of the zone. EMA200 trend filter. |
| 35 | 20250226.1 / .2 | 37-38 | KEEP | X (2-4) consecutive bars with EMA25 below EMA50 and the whole bar above EMA50. No direction stated; .2 says "reverse": one rule and its reverse. AUXCAX H12 2022-02-09 chart (see Q1). |
| 36 | 20250302.1 | 39 | X-DAVEY | Big doji again, with stop-and-reverse. "Taken directly from Kevin Davey video." |
| 37 | 20250302.2 | 40 | X-DAVEY | #28 with stop-and-reverse. "From Kevin Davey." |
| 38 | 20250303.1 | 41 | KEEP | X (3-5) consecutive bars touching both EMA25 and EMA50. Direction by close versus the close 50 bars ago. AUXCAX H12 2022-08-11 chart (see Q1). |
| 39 | 20250303.2 | 42 | KEEP | #38's reverse with EMA25 below EMA50; one rule, the filter in pane 2. |
| 40 | 20250303.3 / .4 | 43-44 | KEEP | Downtrend; large bear bar (over 1 ATR, body over 0.5 x range); bars 2..X inside bar 1; bar X+1 does not exceed bar 1's high but closes below bar 1's low ("below it", read as the low; the drawing shows the entry on that close). Short (.3) or long (.4). |
| 41 | 20250309.1 / .2 | 45-46 | KEEP | RSI divergence: High[1] is the highest of X bars and RSI is below RSI X bars ago. Short (.1) or long (.2). |
| 42 | 20250311.1 / .2 | 47-48 | KEEP | Large bar (at least 1 ATR) whose low is the X-bar low, closing in the top 20%. Long above EMA200 (.1); .2 shorts the same bar below EMA200. One rule plus reverse, EMA200 side in pane 2. |
| 43 | 20250223.1 | 49 | KEEP | Support from 3+ wicks to a level with no close below. Price drops below, meets resistance at the level (2+ touches) without going far (ATR bound), and then reclaims it: long. Hard. EUR/CHF TradingView chart, own drawings. |
| 44 | 20250312.1 | 50 | X-DAVEY | "From Kevin Davey video": Algo Entry That Works in 30 Different Futures Markets. |
| 45 | 20250312.2 / .3 | 51-52 | X-EXT | "Inspired by this video" (The Secret Mindset, "Manipulation Candlestick Patterns Banks Use Against You"): wick past a fractal. See Q2. |
| 46 | 20250312.4 / .5 | 53-54 | X-EXT | Same video. Wick past a round number. That is also a price-LEVEL test, which back-adjusted data cannot support. |
| 47 | 20250312.6 / .7 | 55-56 | X-EXT | Same video. Repeated large-wick candles within about 10 bars. See Q2. |
| 48 | 20250312. (sideways bull bar) | 57 | X-EXT | Same video. Large bullish bar in a sideways market, short. See Q2. |
| 49 | 20250312. (fractal highs cluster) | 58 | X-EXT | Same video. Clustered fractal highs, then a big bull close above them, short. See Q2. |
| 50 | 20250312. (L-H-L-H box) | 59-60 | KEEP | 5-bar fractals ordered low, high, low, high with the last two inside the first two; enter on the first close outside the last two (with the break, or faded). One rule plus reverse. No link, but written the same evening right after #45-49. See Q4. |
| 51 | 20250312. (fractal timing) | 61 | KEEP | Average bar gap over the last 8+ fractals; when the next fractal arrives 2-3x late, fade it. See Q4. |
| 52 | 20250312. (fractal trendline) | 62-63 | KEEP | Down trendline through 3+ consecutive 5-bar fractal highs, qualifying when the regression R^2 > Y (Brian 2026-11-05) and the slope is at least a minimum; it expires after Z bars or when a close crosses it. First close above it: long (or short, the reverse). Brian's own (Q4). |
| 53 | 20250312. (fractal order) | 64 | KEEP | Fractal order low, high, high means long; high, low, low means short. See Q4. |
| 54 | 20250319.1 / .2 | 65-66 | KEEP | Close above Close[X], above Close[2X], above Close[4X]. Long (.1) or short (.2). |
| 55 | 20250319.3 / .4 | 67-68 | KEEP | ADX[1] below ADX[Z] and Close[1] above Close[Z]: short (.3) or long (.4). Its exit, ADX[1] above ADX[Z], can go to the exit pool. |
| 56 | 20250323. | 69 | X-DAVEY | A Davey video title and thumbnail ("Algorithm Trading Complete ENTRY Tutorial"); no rule written. |
| 57 | Pullback Study | 70 | X-DAVEY / KEEP | The study frame (long-term up, short-term down) is Davey's momentum pullback and is excluded. Kept per Brian: only the generic filters (short/long ATR ratio, coefficient of variation, ADX, Choppiness Index) as pane-2 conditions. Davey momentum (close above close N ago) is ALLOWED as a pane-2 trend filter (Brian 2026-11-05), never as pane 1. |
| 58 | Exit Ideas | 71 | KEEP (exit) | Stop beyond the most recent fractal. Exit pool only. |
| 59 | 20240412.1 (dated 2025-04-12) | 72 | KEEP | Fractals low, high, low, high where the last up-leg's slope is below the first up-leg's: short. |
| 60 | 20250413.1 / .2 | 73-74 | X-DAVEY | "Davey Momentum up for X consecutive bars". Already in the library as `MomentumConsecutiveBars` from the Davey corpus. |
| 61 | 20250427.1 | 75 | KEEP | Rising moving averages not crossed, but their gap is narrower than X bars ago, and the bar makes a new X-bar low. Short. |
| 62 | 20250427.2 | 76 | KEEP | Trend-strength indicator: the fraction of the last X bars that made a Y-bar low. Concretized as a threshold, pane-2 filter (and mirror). |
| 63 | 20250503.1-4 | 77 | X-CLASSIC | Range-engulfing (outside) bar. Green means long, red means short, optionally with range above an ATR threshold. The library has `OutsideBar`. Previously backtested in 2025 (see Q1). |
| 64 | 20250511.1 / .2 | 78 | KEEP | (.1) The last two upper Bollinger touches make a higher high: long. (.2) After an upper-band touch, long on the next close above the touch bar's high, invalidated by a lower-band touch. Low-volatility filter: band width below its X-bar average. Previously backtested (Q1). |
| 65 | 20250512.1.1-8 | 79 | X-DAVEY | Long momentum up, short momentum up, optionally a large green bar: long (and reversed). Davey's dual-momentum construction; Brian's backtests (.7/.8) found the candle irrelevant. See Q3. |
| 66 | 20250519.1.1-4 | 80 | X-DAVEY | "Momentum pullback study": 150-250 momentum up, 30-70 momentum down. This is #28 without the ADX. |
| 67 | 20250524.1 | 81 | DEFER | Price-level congestion profile (count of swing points within X·ATR of each level); "try a few different entry ideas" are not specified. |
| 68 | Ideas 1 | 82 | KEEP | Average distance of price from an MA, long versus short window: long-window large and positive, short-window small. Enter long (v1) or short (v2). Thresholds in ATR units. |
| 69 | Ideas 2 | 82 | KEEP | Two large (over 1 ATR) green bars with little range overlap. Overlap fraction as an input. |
| 70 | Ideas 3 | 82 | DEFER | Regression channel on highs and lows with a minimum R^2 and a fill percentage. Needs a channel-fit design; candidate for a later round. |
| 71 | Ideas 4 | 82 | KEEP | The last X touches of the MA were wicks that closed on the same side. |
| 72 | Ideas 5 | 82 | KEEP | The last 10 bars have a small average body/range; then a large bar (over 1 ATR, body over 50%) enters in its direction. |
| 73 | Ideas 6 | 82 | KEEP | EMA slope in ATR per bar as a pane-2 trend filter. The R^2 sub-question is dropped. |
| 74 | Ideas 7 | 82 | DEFER | A parabola fit to the EMA with an R^2 test; no entry stated. |
| 75 | Ideas 8 | 82 | DEFER | Regime segmentation with a window error score. Research. |
| 76 | Ideas 9a / 9b | 82 | KEEP | Fraction of the last X bars closing green; mean body/range over X bars. Pane-2 filters. |
| 77 | Ideas 10 | 82 | DEFER | Touch-maximizing trendline, area between touches, touch spacing. Research. |
| 78 | Ideas 11 | 82 | DEFER | Touch-maximizing horizontal S/R from fractals; no entry stated. |
| 79 | Ideas 12 | 82 | DEFER | "Clearly defined trendline", then X bars without a touch. Depends on #77 or #52's trendline. |
| 80 | More Ideas | 83 | KEEP | Downtrend (pane-2 trend filter). A bar makes the X-bar low, and the bottom Y x ATR of that bar (from its low up) is a price band that no bar enters in the Z bars before it or the Z bars after it (Brian 2026-11-05). Short on the first close below the wick's low after that. The signal is confirmed Z bars late, by construction. |
| 81 | One More Idea | 84 | NOTE | Fundamentals question. |
| 82 | Basic idea (Regime_Detector) | 85-86 | DEFER | Trend/volatility region binning, a repainting model, and "two adjacent consolidation zones". Research. |
| 83 | Adaptive number of points | 87-88 | X-EXT / DEFER | Pasted Copilot output (HDP-HMM, PELT, GMM). Excluded as both AI-sourced and a research project. |
| 84 | PELT pages | 89-94 | X-EXT / DEFER | AI chat screenshots and a newton.ac.uk poster link; no trading rule. |
| 85 | 2025-10-20 (EMA touches) | 95 | KEEP | 200-EMA: bars since the last touch, against the recent average gap. When the current gap is much longer (K x the mean of the last N gaps), enter on the touch in the direction of crossing (the drawing: "Long Entry" at the first touch after a long absence). Variant: no touch in X bars, plus a volatility filter. |
| 86 | Intraday windows | 96 | NOTE | Experiment plan (do T1/T2 windows change results?), not a rule. |

## Indicators notebook (`Indicators.pdf`, added 2026-11-05)

Five notes, dated 2025-01-03 .. 2025-02-08, no links. One chart: AD H8 2024 with 1-bar
swing arrows and two support lines (Brian's MT tool). Brian: these may be used as
strategy ideas in their own right, under the same criteria. As indicators, they become
pane-2 conditions (a threshold on the indicator, plus its mirror) unless noted.

| # | Note | p. | Status | Idea / reason |
|---|---|---|---|---|
| I1 | 20250103.1 | 1 | KEEP | Trend vs consolidation bar: the fraction of the bar's range lying outside the range of the previous X bars (X=1 is the plain version). Threshold above means trend bar, below means consolidation. The "normalization techniques from the indicators book" are not used; the fraction is already scale-free. |
| I2 | 20250116.1 | 2 | KEEP | Support zone: several non-alternating 1-bar swing lows within X x ATR of each other whose spread (standard deviation of the swing lows) is at most k x ATR (Brian 2026-11-05, replacing the horizontal-line R^2, which is identically 0); invalidated by a close a margin (0.5 ATR, or a fraction of X) below the zone. |
| I3 | 20250116.2 | 3 | KEEP | Trend vs range: regression lines through the last X 1-bar swing highs and the last X swing lows. Slopes in ATR per bar: both above +s means up, both below -s means down, otherwise range. |
| I4 | 20250116.3 | 4 | KEEP | The last two 30-bar swing highs and lows: higher highs and higher lows means uptrend, lower highs and lower lows means downtrend, otherwise ranging. Filter. |
| I5 | 20250208.1 | 5 | KEEP | Congestion: ATR(X) / (X-bar high - X-bar low), above a threshold. This is the inverse of the consolidation test in #30-34, so it is authored as one rule (or reuses `RangeWidthBelowAtrMultiple`), not two. |

## Phone notes (`phone_notes.txt`, added 2026-11-05)

45 lines, undated, no links, no names. Nothing in the text points to an outside
source, but nothing proves it is original either (see Q-P0). Rows are keyed by line number.

| # | Lines | Status | Idea / reason |
|---|---|---|---|
| P1 | 1 | KEEP | Developed into six rules, approved by Brian 2026-11-05: see "P1 rules" below. |
| P2 | 3-4 | KEEP | MAs of the body tops (max(open, close)) and the body bottoms (min(open, close)). Long when the close is more than X x (top MA - bottom MA) above their midpoint (Brian 2026-11-05). Plus reverse. |
| P3 | 7 | KEEP | Mean body / mean wick length over N bars as a volatility-style indicator. Pane-2 filter (threshold, plus its mirror). |
| P4 | 9 | KEEP | Of the last Y X-bar breakouts (new X-bar highs or lows), at least a fraction F were upside: long, plus reverse. Pane-1 entry per Brian, distinct from P8 (the last Y consecutive) even though related. |
| P5 | 11-12 | KEEP | The most recent X bars all close above the MA, and the Y (longer) bars before that all closed below it. Long, plus reverse. Kept as a twist (Brian 2026-11-05). |
| P6 | 14-16 | KEEP | A down move from a fractal high to a length-3 fractal low that is the lowest of the last several fractal lows. Then a pullback of at least fractal-length bars, contained inside the move, whose mean bar range is much smaller than the move's. Short. |
| P7 | 18 | KEEP | X-bar breakout bar whose prior X-bar high is below the breakout bar's midpoint, i.e. a breakout that clears the range by at least half its own size. Long, plus reverse. |
| P8 | 20 | KEEP | The last Y consecutive X-bar breakouts (new X-bar highs or lows) were all upside. Long, plus reverse. |
| P9 | 22-24 | KEEP | 3+ swing highs (3- or 5-bar) at about the same level (ATR tolerance) with no significant break, then a close at least Y x ATR above them: long. The momentum filter on lines 22-23 (X-bar up, or X-bar and X/2-bar up) goes to pane 2. |
| P10 | 26 | KEEP | An X-bar high that touches the upper Bollinger band; long on the retracement to the middle (or lower) band. Kept as a twist (Brian 2026-11-05). |
| P11 | 28 | KEEP | A breakaway move (several bars, or over an ATR cutoff), measured from the first bar's open to the move's high. Then a 3-5 bar pullback that stays in the top 20-30% of the move and does not exceed its high; long on the break above the high. |
| P12 | 31-33 | KEEP | Signal 1: a bar makes the highest high of X (5-10) bars, with no higher bar since. Signal 2, within the next X bars: the lowest low of X bars, with no lower bar since. Short on a retracement into the top Y% (about 50%) of signal bar 2. The limit-style entry is mechanized as a close inside that zone, then the next open (the standing convention). |
| P13 | 35-36 | KEEP | A swing low, then a higher swing low; a bar rejects off the second (low within a tolerance of it, close higher, i.e. a lower wick). Long, plus reverse. |
| P14 | 38-40 | KEEP | Strong bear bar (over 1 ATR, body a large fraction of the range); none of the NEXT 10-15 bars trades into its top half (Brian 2026-11-05). Long counter-trend once that window completes, so the signal is delayed by construction. The target at the bear bar's open goes to the exit pool. |
| P15 | 42-43 | KEEP | Non-alternating 2-bar swing highs: the 2nd and 3rd most recent are level (within about 0.05 ATR) and the most recent exceeds them by at least 1 x ATR(10). Long. Not the same as P9: a pivot break against a close break, and an exact pair against 3+ touches. |
| P16 | 45-46 | KEEP | Donchian(20): one large bar with a low below the channel midline whose high sets a new channel top. Short. Beyond the classic Donchian breakout (a fade of an outsized breakout bar). |

## P1 rules ("what happened the last times price was here"), approved 2026-11-05

A VISIT is a past bar between M and N bars back whose high-low range contains the
current close (Brian confirmed this definition; no ATR band). The M-bar gap keeps the
current move out of its own history. Every rule needs at least K visits. This is a
difference test, so back-adjustment does not affect it.

| # | Name | Pane | Definition |
|---|---|---|---|
| P1a | LevelRejectedFromAbove | 1 | At least F of the visits are upper-wick visits (the close is between the visit's body top and its high): short. Mirror: lower-wick visits, long. |
| P1b | LevelForwardDrift | 1 | Over visits at least H bars old, the mean H-bar move after the visit, divided by ATR, is at least +D: long. At most -D: short. No look-ahead. |
| P1c | LevelThinAir | 1 | At most K visits in the window: enter in the direction of the last J-bar move. Also covers 20250524.1's "vertical roadmap". |
| P1d | LevelBodyDominated | 2 | At least F of the visits had the close inside the body. |
| P1e | LevelWasTrending | 2 | The mean ADX(14) on visit bars is at least T (mirror: at most T). |
| P1f | LevelBigBars | 2 | The mean visit range / current ATR is at least R (mirror: small). The volume version is the same rule on volume. |

## Decisions (Brian, 2026-11-05)

1. Ideas are not excluded on date. Conception after the OOS window is recorded as a caveat only.
2. The Secret Mindset video ideas (#45-49) are excluded.
3. 20241020.7/.8/.9 and 20250512.1 are excluded as Davey-derived. From the Pullback Study only the generic filters are kept. Davey momentum may be a pane-2 trend filter.
4. The 20250312 fractal notes (#50-53) are Brian's own.
5. Generic constructs are kept only when they go beyond the indicator's most obvious use. A twist such as a divergence, or comparing the last two band touches, is kept. A plain threshold or band-touch entry is excluded (X-CLASSIC).
6. The ORB notes (#17-19) are excluded as too close to the classic ORB. W/D/T1/T2 were session windows meant for a time-based switch (W: no weekend holding, D: no overnight holding, T1/T2: market-dependent tier windows chosen for volume and spread).
7. #52's trendline qualifies on R^2 > Y. #80 and #2 are re-read per Brian (see rows). Channels in #1-3 may form in either order.
8. (second round) #2's reading is confirmed. I2 uses a spread test (std dev of the swing lows at most k x ATR). #26 is a red run from at or above the upper zone closing below the lower zone, then long. #6 is kept. #22 and #63 are excluded as classic. Classic constructs are fine as pane-2 filters.
9. (phone notes) All phone notes are Brian's own. P2 uses the midpoint of the two body MAs. P4 counts upside breakouts and is a pane-1 entry distinct from P8. P5 and P10 are kept as twists. P14 is delayed (the following 10-15 bars).
10. P1 rule family approved as above. General: a NOVEL pane-2 condition may be paired with a simple, even classic, pane-1 entry; the classic exclusion applies only when the classic construct is the whole idea.
11. (spec round, resolutions recorded in mined/*.json) ON-25: HIGH candle = CLOSE above the 50-bar high (symmetric with LOW). Every bar between the two L's (H's) must be a C candle. ON-43: Level = a cluster of wick lows within a tolerance, built like the I2 support zone (not the most recent swing low). I2: Zone: scanning back N bars, the K+ most recent 1-bar swing lows all within X*ATR of each other, with std dev of those lows <= k*ATR; bottom = lowest of them; a close more than 0.5*ATR below the bottom kills it. #26 needs two distinct stacked zones. No pane-2 'near zone' condition for now. pivot-order (ON-50, ON-53, ON-59): A bar that is both a swing high and a swing low counts as both, ordered by bar direction: a green bar (close > open) is low-then-high, a red bar high-then-low. ON-50: The mirror order (high, low, high, low with the last two inside the first two) also counts. P11: Breakaway move = a run of consecutive bull bars each with range >= k*ATR; measured from the first run bar's open to the run's highest high. ON-80: Cancel the armed setup if a later bar trades back into the band. Add a window input W, counted from the wick bar, constrained W > Z. P6: 'Fractal low length ~3' = swing strength 3 (three bars each side); the pullback must be at least 3 bars.
