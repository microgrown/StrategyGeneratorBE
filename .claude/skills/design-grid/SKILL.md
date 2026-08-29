---
name: design-grid
description: Design the optimizer grid (start/stop/step per input) for rules being placed into a StrategyGeneratorBE template. Use when asked to pick optimization ranges, fill in template params, decide which inputs to optimize vs pin, or when the user asks "what grid should I use" for a rule or strategy. Also use right after authoring new rules when the user asks how to parameterize them. Enforces the iteration budget, checks expected M1440 trade counts against prior run data before recommending, and emits paste-ready params blocks.
---

# Designing optimizer grids

Grids live in a template's per-placement `params`: `{"start","stop","step"}`
strings. Blank `stop` or `step` (or `stop == start`) pins the input to a single
value. Values per row = `(stop - start) / step + 1`, inclusive —
`rowIterations` in `parameterGUI.py:17` is the authority.

A template generates one **version** per cross-product of pane groups (one
delimited group per pane, README.md §"Template workflow"). Everything below is
budgeted **per version**: the optimizer grid for a version is the product of
the row counts of every param of every rule placed in that version's groups.

## Hard budgets (per generated version)

- **≤ 3 optimized inputs** (rows with a real stop/step). Everything else pinned.
- **≤ 100 total iterations** — the product across all placed rules, entries,
  exits, and switches together. Show the arithmetic when proposing a grid.
- Any lookback's max value must respect `maxBarsBack` (250, `config.json`).

When a template's panes make several versions, budget the *worst* version —
the group combination with the most optimized rows.

## Which inputs to optimize

Optimize only what the edge is sensitive to — usually the entry rule's
selectivity knobs (main lookback, trigger threshold). Pin:

- Smoothing / secondary lookbacks at conventional values: ATR 14–15, ADX 14,
  RSI 14 (or the source's published value — check
  `reference/EntryExitConfessions.json` for EEC rules).
- Anything the source publication fixed.
- Switch-rule params (usually 1 value, at most 2).

Exits get small grids when optimized at all: 2–4 values (dollar targets, ATR
multiples). The entry earns the budget; don't spend 5 values on a stop-loss.

## Range shape

3–5 values per optimized input, coarse steps. The walkforward re-optimizes
every IS window, so fine steps fit noise and burn compute; endpoints should
represent *qualitatively different* behavior, with the published/default value
near the center. Corpus conventions (recent `templates/2026*.json`):

| Input type | Typical grid |
|---|---|
| Bar lookback | 10..50 step 10, or 10..100 step 30 (5 rows only if it's THE knob) |
| ATR / range multiple | 0.5..2 step 0.5, or 1..3 step 1 |
| Dollar amount per contract | 1500..3000 step 500 (or step 1500 for 2 rows) |
| Indicator threshold (RSI, ADX, ratio) | 3–4 coarse values spanning a regime change, e.g. RSI 70/80/90 |
| Enumeration (day of week, etc.) | full domain, step 1 — counts as an optimized input |

## Trade-count sanity (the M1440 constraint)

The spec's selection chain has a `trade_count` filter, `min_trades: 30`
(`specs/Futures_Swing.json` in BacktestEngine), counted per candidate on its
selected schedule. Target: a good chunk of M1440 cases > 30 trades, ideally
> 50. M1440 ≈ 252 bars/year; the walkforward spans 2007–2025 ≈ 4,600 daily
bars per symbol. So at the **most selective corner of the grid** the strategy
still needs roughly ≥ 2–3 round trips/year on daily bars; at the center aim
for ~1 entry per 25–50 daily bars.

Estimate analytically first: what fraction of bars satisfies the condition?
(`close == highest(close, N)` fires ~1/N of bars per side; a day-of-week
filter passes 1/5; two ANDed panes multiply.) Then discount for time already
in a position. If the selective corner lands under ~1 signal per 100 daily
bars, pull the range in.

**Check empirically before running anything new.** Prior runs already hold
per-case trade counts — never re-run the chain to learn them (aggregates are
in `BacktestEngine/runs/<stem>/selection_report.json`). For a rule family
that appeared in an earlier strategy:

```python
import json, glob
for f in glob.glob(r"C:\Users\brian\source\repos\BacktestEngine\runs\<stem>\selection_report.json"):
    d = json.load(open(f, encoding="utf-8"))
    for rn, rv in d["runs"].items():
        for c in rv["candidates"]:
            if c["timeframe_minutes"] != 1440: continue
            for o in c["outcomes"]:
                if o["filter"] == "trade_count":
                    for s in o["details"]["schedules"]:
                        print(rn, c["symbol"], s["trades"])
```

Report the M1440 distribution (n cases, median, % > 30, % > 50) and say which
prior stem it came from. If no prior run used a similar entry, say so and — as
an *offer, not an action* — suggest a one-version probe template (pattern:
`templates/quickTest.json`) with mid-grid pinned values via `runBatch.py`.
Running it is Brian's call; it costs engine compute.

## Deliverable

1. A table: input → pinned value or start/stop/step → row count → one-line
   rationale (why this range, why pinned).
2. The iteration arithmetic per version, against the ≤ 100 budget.
3. The trade-count evidence used (prior-run stats or the analytical estimate).
4. Paste-ready `params` JSON blocks in template shape — all values strings,
   pinned inputs as `{"start": "X", "stop": "", "step": ""}`.

Don't edit a template file unless asked; the default deliverable is the
recommendation. When asked to apply it, edit the template JSON directly
(same shape `templateIO.py` reads) and leave rule JSON defaults alone.
