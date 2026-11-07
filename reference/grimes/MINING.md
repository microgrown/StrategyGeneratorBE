# Mining Grimes, *The Art and Science of Technical Analysis*, for candidate rules

This is the brief for every mining agent. Read it fully before opening a chapter.

## Job

Read one or more chapters of Adam Grimes, *The Art and Science of Technical
Analysis: Market Structure, Price Action, and Trading Strategies* (Wiley, 2012)
(plain text in `reference/grimes/text/grimes/NN_<slug>.txt`, with `[[page P]]`
markers) and record every statement that could become a **mechanical,
bar-by-bar trading condition** as a candidate in
`reference/grimes/mined/grimes/NN_<slug>.json`.

You are **mining, not authoring**. Do not write `rules/*.json`, do not edit
`rules/CATALOG.md` or `rules/EL_FEATURES.md`, do not touch any file outside
`reference/grimes/mined/`. A later pass dedups across all chapters and authors
the survivors with the `author-rule` skill.

## What counts as a candidate

Anything Grimes states that can be decided from OHLCV bars, position state, or
bar count, phrased as *if X then enter / exit / stay out*. Be **high recall**:
a later pass discards, you cannot recover what you skipped. Include:

- The market-cycle and four-trade framework: trend continuation (pullbacks),
  trend termination (climaxes, exhaustion, parabolic moves), support or
  resistance holding (failure tests, springs, upthrusts) and failing
  (breakouts). Each named setup and each of its conditions is a candidate.
- Pullback structure: simple vs complex pullbacks, pullback to the moving
  average, nested pullbacks, the "Anti", "three pushes", the first pullback
  after a breakout, pullback depth as a fraction of the prior swing.
- Momentum and impulse tests: large-range bars, consecutive closes in one
  direction, momentum divergence at new highs, the 3/10 oscillator (fast
  MACD variant) and any statement about its slope, zero-line, or divergence.
- Channel and band relations: Keltner channels (20-period EMA with bands at a
  multiple of ATR), closes outside the band, "free bars", riding the band,
  returns inside the band, band width.
- Bar patterns: wide-range bars, narrow-range bars, inside bars, bars closing
  at their extreme, gaps, "climax" bars, bar overlap, volatility contraction.
- Swing structure: higher highs / lower lows, swing failure, lower highs
  inside a range, measured moves, the length ratio of successive legs,
  trading-range boundaries, "spring" (dip below support and recovery),
  "upthrust" (pop above resistance and failure), breakout with and without
  follow-through, failed breakouts.
- Trend lines, channels and anything requiring pivots or projection **even
  though they need pivot detection**. Record with an honest `complexity`.
- Exits and management: initial stop placement (beyond the setup bar, beyond
  the swing, ATR-based), partial profits at N times risk, trailing by swing
  or by band, breakeven moves, time stops, "exit when the reason for the
  trade is gone", targets by measured move.
- Position sizing and risk statements that reduce to a bar-level rule
  (fixed fractional risk per trade is *not* a rule the generator can use;
  record it under `rejected` with the reason "position sizing"). Anything
  that sets the stop distance from bar data *is* a candidate.
- Context filters: "only take pullbacks in a trend with momentum", "avoid
  range trades after a climax", "stand aside when the higher time frame is in
  a range". These become `Entry` candidates that gate other entries, flagged
  `is_filter: true`.
- Higher-time-frame / lower-time-frame reasoning. The engine sees one
  timeframe. **Do not reject** multi-timeframe ideas: write the pseudocode
  with the higher-timeframe quantity approximated by a longer lookback on
  the same bars (a 20-bar EMA on a chart five times slower is roughly a
  100-bar EMA here), note the approximation in `notes`, and grade the
  complexity honestly.
- Intraday-only ideas (opening range, session times). **Do not reject
  these**; set `timeframe` to `intraday-only` and move on.
- Appendix material: the trading primer and the moving-average / MACD
  appendix contain the most precise indicator definitions in the book.
  Mine the definitions themselves (lengths, smoothing, band multipliers) as
  candidates or as parameters of candidates.

**Reject** (record under `rejected`, with the page and a one-line reason) only:

- Data the engine cannot have: another symbol or sector, breadth, volume
  profile, order book, news, options, fundamentals, tick data below the bar.
- Randomness or wall clock, future bars.
- Pure discretion with no bar-level test at all ("trade what makes sense",
  "read the tape").
- **Conditions on the price LEVEL rather than on price differences**: round
  numbers, whole-dollar levels, a threshold as a percent of price, price
  times volume, comparisons of price against zero. The data are back-adjusted
  futures, so the level is arbitrary and can be negative. A rule must give
  the same answer if every price on the chart is shifted by a constant.
  Ratios of *differences* (range / ATR, retracement fraction of a swing) are
  fine; ratios of price *levels* are not. Percent moves ("a 3 percent
  decline") should be re-expressed in ATR units and kept, with the original
  in `notes`.
- Statistics-of-the-book material (expectancy tables, the argument that
  technical analysis works, psychology chapters) that has no bar-level test.

## Conventions you must apply

- **Stop and limit entries become close-and-next-open.** Grimes often enters
  on a stop above the setup bar or on a limit inside a pullback. Mechanize
  every such setup as *bar closes with the pattern true, then enter at the
  next bar's open*. Record his actual order placement in `book_order_type`,
  but write `pseudocode` for the close-based form. Same for stop exits.
- **Every tunable constant is a parameter.** "20-period EMA", "2.25 ATR",
  "two legs", "three pushes", "two times risk" all become named parameters
  with Grimes's value as the default. Only 0, 1, and structural constants
  stay literal. If Grimes gives no number, choose a sensible default and say
  so in `notes`.
- **One condition per candidate.** If Grimes says "in an uptrend with strong
  momentum, buy the first pullback that holds above the moving average", that
  is three or four candidates (trend context, momentum, pullback count, holds
  above MA), plus optionally one `composite` candidate that names them via
  `composes`. Split aggressively; the pane system ANDs entries and ORs exits.
- **Shared primitives once per file.** "Swing high", "impulse move", "Keltner
  band", "pullback", "climax" recur. Define each as its own candidate the
  first time the file uses it and refer to it by `id` in `composes` or
  `depends_on` afterwards. Do not redefine it in the same file. It is fine and
  expected that other chapters define the same primitive; the dedup pass
  merges them.
- **Pseudocode dialect.** Use the corpus's C++-ish form: `close[0]`, `high[1]`,
  `low[n]`, `open[0]`, `volume[0]`, `ctx.MarketPosition()`,
  `ctx.OpenPositionProfit()`, `ctx.BarsSinceEntry()`, `ctx.EntryPrice()`,
  `ctx.MinMove()`, `ctx.TickSize()`. `[0]` is the current bar, `[1]` the
  previous. Write the **long** side only; the `sides` field says whether the
  short side is `mirrored` (flip `>`/`<`, high/low) or `same` (identical
  text). For loops, write `highest(high, n)`, `ema(close, n)`, `atr(n)`-style
  helpers; that is enough for the authoring pass.
- **Cite pages.** Every candidate carries the `[[page P]]` it came from and a
  short verbatim quote (under 60 words). If a candidate is assembled from
  several passages, list every page and quote the most rule-like one.
- **Dedup hint, not dedup.** Skim `rules/CATALOG.md` once at the start. If a
  candidate looks like an existing rule, put the rule name in
  `likely_existing_rule`. Do not drop the candidate on that basis. The Brooks
  corpus already covers many bar patterns, EMA gap bars, swing pivots,
  measured moves, H1/H2 counting and trend-line rules; Grimes candidates
  that restate them are still recorded, with the hint filled in.
- **Chart walk-throughs** (chapter 10 is mostly worked trade examples) that
  only reapply primitives already defined may be summarized, not re-mined
  bar by bar. Mine any new condition, stop rule, or management rule they
  introduce.

## `complexity` grades

| grade | meaning |
|---|---|
| `trivial` | a bare comparison of prices on fixed offsets (`close[0] > high[1]`) |
| `simple` | a window loop into a local: highest/lowest/average/ATR over N bars |
| `moderate` | cross-bar state, an EMA, a counter that persists between bars, position-history reads |
| `hard` | needs swing-pivot detection, trend-line or channel projection from pivots, leg counting, measured-move targets, pattern recognition over variable-length windows |
| `research` | the concept is real but a design decision is needed before it can be coded at all (e.g. "the higher time frame is trending", "the market is in a trading range") |

Always fill `complexity.reason` with one sentence saying what makes it that
grade. `hard` and `research` are expected and welcome; the point of the field
is to tell the authoring pass what it is walking into.

## Output file

`reference/grimes/mined/grimes/NN_<slug>.json` (same `NN_<slug>` as the text
file). Valid JSON, UTF-8, no trailing commas. Validate with
`python -c "import json;json.load(open(path, encoding='utf-8'))"` before you
finish. Write each chapter's JSON as soon as that chapter is done, with a
single Write call; do not hold several chapters in memory.

```json
{
  "source": {
    "book": "The Art and Science of Technical Analysis",
    "book_key": "grimes",
    "author": "Adam Grimes",
    "chapter": 3,
    "chapter_title": "On Trends",
    "text_file": "reference/grimes/text/grimes/03_on_trends.txt",
    "pdf_pages": [63, 112],
    "mined": "2026-09-21"
  },
  "conventions": "stop and limit entries mechanized as bar-close then next-bar-open; every tunable constant is a parameter; long side only in pseudocode; price-level conditions rejected (shift test)",
  "candidates": [
    {
      "id": "G03-01",
      "name": "CloseOutsideKeltnerBand",
      "role": "Entry",
      "is_filter": false,
      "composite": false,
      "composes": [],
      "depends_on": [],
      "pages": [70],
      "quote": "...a close outside the Keltner channel is a sign of strong momentum...",
      "description": "The current bar closes above the upper Keltner band (EMA of length L plus M times ATR of length L).",
      "pseudocode": "close[0] > ema(close, emaLength) + bandMult * atr(atrLength)",
      "sides": "mirrored",
      "parameters": { "emaLength": 20, "bandMult": 2.25, "atrLength": 20 },
      "book_order_type": "n/a (context test)",
      "timeframe": "any",
      "complexity": { "grade": "moderate", "reason": "needs an EMA and an ATR" },
      "el_words_needed": ["XAverage", "AvgTrueRange"],
      "likely_existing_rule": "",
      "confidence": "high",
      "notes": ["Grimes's Keltner channel: 20-period EMA, bands at 2.25 ATR; confirm exact multiplier in Appendix B."]
    }
  ],
  "rejected": [
    { "pages": [58], "quote": "...", "reason": "position sizing, not a bar-level rule" }
  ],
  "chapter_summary": "Two or three sentences: what the chapter is about and which candidate families it produced."
}
```

Field notes:

- `id` is `G<NN>-<k>`: `NN` the chapter number (00 front matter, 01 to 12
  chapters, 13 to 15 appendices, 16 glossary), `k` a running counter from 01.
- `role` is `Entry`, `Exit`, or `Switch` (a Switch is a global condition that
  blocks entries and forces flat; rare here; most context filters are `Entry`
  with `is_filter: true`).
- `sides`: `mirrored` or `same`. Copying a directional long condition to the
  short side unflipped is the classic error; think about it for every row.
- `timeframe`: `any`, `intraday-only`, or `daily-ok` (Grimes says it
  explicitly works on daily charts too). Grimes's examples span intraday,
  daily and weekly charts; most of his ideas are `any`.
- `el_words_needed`: EasyLanguage words the rule would need beyond plain
  price arithmetic: `XAverage`, `Average`, `AvgTrueRange`, `SwingHigh`,
  `SwingLow`, `Highest`, `Lowest`, `MACD`, `StdDev`, `Time`, `Date`,
  `BarsSinceEntry`, `EntryPrice`, `MaxPositionProfit`, and so on. Guess when
  unsure; the feature-triage pass checks them against the register.
- `confidence`: how faithfully the pseudocode captures what Grimes means
  (`high` / `medium` / `low`), not how good the rule is.

## Report back

Under 25 lines, once for all files you were assigned: path of each JSON
written, number of candidates by role and by complexity grade, number
rejected, the three most distinctive candidates by name, and anything about
the chapters that the dedup pass should know (for example "this chapter is
mostly chart examples; primitives defined in G03 are reused here", or "this
chapter defines the 3/10 oscillator precisely; other chapters only refer to
it"). Do not paste the JSON.
