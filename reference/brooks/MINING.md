# Mining the Brooks trilogy for candidate rules

This is the brief for every mining agent. Read it fully before opening a chapter.

## Job

Read one chapter of an Al Brooks *Trading Price Action* volume (plain text in
`reference/brooks/text/<book>/NN_<slug>.txt`, with `[[page P]]` markers) and
record every statement that could become a **mechanical, bar-by-bar trading
condition** as a candidate in `reference/brooks/mined/<book>/NN_<slug>.json`.

You are **mining, not authoring**. Do not write `rules/*.json`, do not edit
`rules/CATALOG.md` or `rules/EL_FEATURES.md`, do not touch any file outside
`reference/brooks/mined/`. A later pass dedups across all chapters and authors
the survivors with the `author-rule` skill.

## What counts as a candidate

Anything Brooks states that can be decided from OHLCV bars, position state, or
bar count, phrased as *if X then enter / exit / stay out*. Be **high recall**:
a later pass discards, you cannot recover what you skipped. Include:

- Bar patterns: inside bar, outside bar, trend bar, doji, ii, ioi, tails, gaps,
  bar overlap, "signal bar" quality tests.
- Counting setups: H1/H2/L1/L2, two-legged pullbacks, three pushes, consecutive
  bars, "first pullback", bar counts since a breakout.
- Moving-average relations: 20-bar EMA gap bars, "always in", MA touches,
  distance from the EMA, moving average as support.
- Swing structure: higher highs / lower lows, double tops/bottoms, measured
  moves, wedges, final flags, climaxes, failed breakouts, breakout pullbacks,
  trading-range boundaries, "measuring gaps".
- Trend lines, channels, and micro-channels **even though they need pivot
  detection and line projection**. Record them with an honest `complexity`.
- Exits and management: scalps at N ticks, swing targets at measured moves,
  stops beyond the signal bar, breakeven moves, "exit on the first reversal
  bar", time-based exits.
- Context filters: "only buy in a bull trend", "do not fade a strong trend",
  "after a climax expect a two-legged correction". These become `Entry`
  candidates that gate other entries, flagged `is_filter: true`.
- Intraday-only ideas (opening range, first hour, time of day). **Do not
  reject these**; set `timeframe` to `intraday-only` and move on.

**Reject** (record under `rejected`, with the page and a one-line reason) only:
data the engine cannot have (another symbol, volume profile, order book, news,
options, tick data below the bar), randomness or wall-clock, future bars, and
pure discretion with no bar-level test at all ("trade what makes sense").

## Conventions you must apply

- **Stop entries become close-and-next-open.** Brooks enters on a stop one tick
  beyond the signal bar. Mechanize every such setup as *signal bar closes with
  the pattern true → enter at the next bar's open*. Record his actual order
  placement in `book_order_type`, but write `pseudocode` for the close-based
  form. Same for stop exits.
- **Every tunable constant is a parameter.** "Two legs", "20-bar EMA", "five
  bars", "one tick", "half the bar" all become named parameters with Brooks's
  value as the default. Only 0, 1, and structural constants stay literal.
- **One condition per candidate.** If Brooks says "in a bull trend, buy the
  second pullback that forms an inside bar above the EMA", that is three or
  four candidates (trend context, pullback count, inside bar, above EMA), plus
  optionally one `composite` candidate that names them via `composes`. Split
  aggressively; the pane system ANDs entries and ORs exits.
- **Shared primitives once per chapter.** "Signal bar", "trend bar", "swing
  high", "always-in" and similar recur. Define each as its own candidate the
  first time the chapter uses it and refer to it by `id` in `composes` or
  `depends_on` afterwards. Do not redefine it in the same file. It is fine and
  expected that other chapters define the same primitive; the dedup pass
  merges them.
- **Pseudocode dialect.** Use the corpus's C++-ish form: `close[0]`, `high[1]`,
  `low[n]`, `open[0]`, `volume[0]`, `ctx.MarketPosition()`,
  `ctx.OpenPositionProfit()`, `ctx.BarsSinceEntry()`, `ctx.EntryPrice()`.
  `[0]` is the current bar, `[1]` the previous. Write the **long** side only;
  the `sides` field says whether the short side is `mirrored` (flip `>`/`<`,
  high/low) or `same` (identical text). For loops, write
  `highest(high, n)`-style helpers; that is enough for the authoring pass.
- **Cite pages.** Every candidate carries the `[[page P]]` it came from and a
  short verbatim quote (under 60 words). If a candidate is assembled from
  several passages, list every page and quote the most rule-like one.
- **Dedup hint, not dedup.** Skim `rules/CATALOG.md` once at the start. If a
  candidate looks like an existing rule, put the rule name in
  `likely_existing_rule`. Do not drop the candidate on that basis.

## `complexity` grades

| grade | meaning |
|---|---|
| `trivial` | a bare comparison of prices on fixed offsets (`close[0] > high[1]`) |
| `simple` | a window loop into a local: highest/lowest/average/ATR over N bars |
| `moderate` | cross-bar state, an EMA, a counter that persists between bars, position-history reads |
| `hard` | needs swing-pivot detection, trend-line or channel projection from pivots, leg counting, measured-move targets, pattern recognition over variable-length windows |
| `research` | the concept is real but a design decision is needed before it can be coded at all (e.g. "always-in direction", "the market is in a trading range") |

Always fill `complexity.reason` with one sentence saying what makes it that
grade. `hard` and `research` are expected and welcome; the point of the field
is to tell the authoring pass what it is walking into.

## Output file

`reference/brooks/mined/<book>/NN_<slug>.json` (same `NN_<slug>` as the text
file). Valid JSON, UTF-8, no trailing commas. Validate with
`python -c "import json;json.load(open(path, encoding='utf-8'))"` before you
finish.

```json
{
  "source": {
    "book": "Trading Price Action Trends",
    "book_key": "trends",
    "author": "Al Brooks",
    "chapter": 3,
    "chapter_title": "Trend Bars and Doji Bars",
    "text_file": "reference/brooks/text/trends/03_trend_bars_and_doji_bars.txt",
    "pdf_pages": [41, 62],
    "mined": "2026-09-12"
  },
  "conventions": "stop entries mechanized as signal-bar-close then next-bar-open; every tunable constant is a parameter; long side only in pseudocode",
  "candidates": [
    {
      "id": "T03-01",
      "name": "TrendBarBodyFraction",
      "role": "Entry",
      "is_filter": false,
      "composite": false,
      "composes": [],
      "depends_on": [],
      "pages": [43],
      "quote": "A trend bar has a body that is most of the bar's range, with small or no tails.",
      "description": "The current bar is a bull trend bar: its body is at least a fraction F of its high-low range and it closed up.",
      "pseudocode": "close[0] > open[0] && (close[0] - open[0]) >= bodyFraction * (high[0] - low[0])",
      "sides": "mirrored",
      "parameters": { "bodyFraction": 0.7 },
      "book_order_type": "n/a (bar classification used as a signal-bar test)",
      "timeframe": "any",
      "complexity": { "grade": "trivial", "reason": "single-bar arithmetic on open/high/low/close" },
      "el_words_needed": [],
      "likely_existing_rule": "",
      "confidence": "high",
      "notes": ["Brooks does not give a number; 0.7 is a reading of 'most of the range'."]
    }
  ],
  "rejected": [
    { "pages": [58], "quote": "…", "reason": "needs tick-level data inside the bar" }
  ],
  "chapter_summary": "Two or three sentences: what the chapter is about and which candidate families it produced."
}
```

Field notes:

- `id` is `<B><NN>-<k>`: `B` is `T`, `R`, or `V` (Trends, Ranges, Reversals),
  `NN` the chapter, `k` a running counter from 01.
- `role` is `Entry`, `Exit`, or `Switch` (a Switch is a global condition that
  blocks entries and forces flat — rare in Brooks; most context filters are
  `Entry` with `is_filter: true`).
- `sides`: `mirrored` or `same`. Copying a directional long condition to the
  short side unflipped is the classic error; think about it for every row.
- `timeframe`: `any`, `intraday-only`, or `daily-ok` (Brooks says it explicitly
  works on daily charts too).
- `el_words_needed`: EasyLanguage words the rule would need beyond plain price
  arithmetic — `XAverage`, `SwingHigh`, `SwingLow`, `Highest`, `Lowest`,
  `Average`, `AvgTrueRange`, `Time`, `Date`, `BarsSinceEntry`, `EntryPrice`,
  `MaxPositionProfit`, and so on. Guess when unsure; the feature-triage pass
  checks them against the register.
- `confidence`: how faithfully the pseudocode captures what Brooks means
  (`high` / `medium` / `low`), not how good the rule is.

## Report back

Under 25 lines: path of the JSON written, number of candidates by role and by
complexity grade, number rejected, the three most distinctive candidates by
name, and anything about the chapter that the dedup pass should know (for
example "this chapter is mostly chart examples; primitives defined in T03 are
reused here"). Do not paste the JSON.
