# Merging mined candidates into canonical rules

This is the brief for every merge agent. Read it fully before opening a bucket.

## Job

You get one topic bucket, `reference/brooks/merge/buckets/<bucket>.json`: the full
mined candidates (schema: `reference/brooks/MINING.md` §"Output file") that a keyword
pass judged to be about one topic, drawn from all three Brooks volumes. Several
agents mined those volumes chapter by chapter and were told to redefine shared
primitives in every file, so the bucket is full of restatements. Your output is
`reference/brooks/merged/<bucket>.json`: the distinct rules in the bucket, each with
every source it came from, ready for the `author-rule` pass.

You are **merging, not authoring**. Do not write `rules/*.json`, do not edit
`rules/CATALOG.md` or `rules/EL_FEATURES.md`, do not touch anything outside
`reference/brooks/merged/`.

## How to merge

**Compare on behaviour, not wording.** Two candidates are one rule when they would
fire on the same bars given the same parameters. The three tests from `author-rule`
§2 apply: same bars; one is the other negated or flipped (a per-placement toggle, so
redundant by construction); one is the other at a fixed parameter. A threshold that
differs between two candidates (body ≥ 0.5 vs ≥ 0.6 of range) is one rule with a
parameter; record both book values in `merge_notes` and pick one as the default.

**Pick the most mechanizable definition.** When restatements differ in how they
would be coded, prefer the one that needs the least machinery: a fixed-offset
comparison over a swing-pivot search, a persistent counter over pivot detection
(the H1/H2 counter from Ranges ch17, `R17-01`, over the research-graded versions),
an existing `ctx` built-in over local emulation. Say in `merge_notes` which
definition won and why. Keep the losing definitions' ids in `sources`; they are
citations, not rules.

**Keep behaviourally distinct rules apart, even when they share a name.** A
one-bar EMA gap bar and a run of twenty EMA gap bars are two rules. A tight trading
range by bar overlap and one by N-bar width over ATR are two rules until someone
measures that they coincide. List such near-misses in `variants_kept_separate` on
both rules so the authoring pass sees the pair.

**Atomic beats composite.** The pane system ANDs entries and ORs exits, so a
composite of independently meaningful conditions is worse than its parts. Carry the
parts as rules. Carry the composite only when it is a named Brooks setup that Brian
would want to test as the book states it (`MajorTrendReversal`, `High2`, `FinalFlag`,
`SpikeAndChannel`); give it `depends_on_keys` naming the parts and grade it by its
hardest part. Drop ad hoc composites with reason "composition of <keys>".

**Check the existing corpus.** Read `rules/CATALOG.md` once. For every merged rule
set `catalog_match`: `duplicate` (same bars, do not author again), `variant` (same
idea, different behaviour, say how), `parameterization` (existing rule at a fixed
input), or `none`. A `duplicate` gets priority `D`.

**Cross-bucket strays.** `belongs_in` must be an exact bucket filename (see
`reference/brooks/merge/buckets/`), never a family name like `breakouts`. Strays sent
to a bucket whose agent has already finished are placed by the reconciliation pass at
the end, so do not wait on them. If the orchestrator's prompt names strays sent to
you, they are not in your bucket file: grep the id in `reference/brooks/mined/`. The keyword pass is crude. A candidate that clearly
belongs to another topic goes in `cross_bucket` with the bucket it belongs to; do
not merge it here. Candidates whose `secondary` buckets (see
`reference/brooks/merge/secondary.tsv`) include yours may be merged by that other
agent too; that is fine, the roll-up reconciles by id.

**Standing conventions**, inherited from mining: stop and limit entries are
signal-bar close then next-bar open; intraday-only rules are kept and tagged; hard
and research grades are kept with a reason. Do not re-reject on those grounds.

## Priority

| priority | meaning |
|---|---|
| `A` | author next: trivial–moderate complexity, high confidence, no research-grade dependency, `catalog_match` none or variant |
| `B` | author after A: hard complexity but a clear definition (needs swing pivots, a persistent counter, an EMA, a session boundary) |
| `C` | blocked on a design decision: research grade, or depends on a research-grade primitive (always-in, trading-range classification, tight channel, leg definition) |
| `D` | do not author: duplicate of a catalog rule, or on re-read not mechanizable |

Every `C` names the decision in `design_decisions_needed`, and the bucket file's
top-level `design_decisions` states each decision once with the options you see in
the sources and the option you recommend.

## Output file

`reference/brooks/merged/<bucket>.json`. Valid JSON, UTF-8. Validate with
`python -c "import json;json.load(open(path, encoding='utf-8'))"` before finishing.

```json
{
  "bucket": "ema_relations",
  "merged": "2026-09-12",
  "rules": [
    {
      "key": "EmaGapBar",
      "role": "Entry",
      "is_filter": false,
      "description": "The bar's low is above the N-bar EMA (long) / high below it (short): a moving-average gap bar.",
      "pseudocode": "low[0] > ema(close, emaLength)[0]",
      "sides": "mirrored",
      "parameters": { "emaLength": 20 },
      "complexity": { "grade": "moderate", "reason": "needs an EMA; single-bar test otherwise" },
      "timeframe": "any",
      "el_words_needed": ["XAverage"],
      "catalog_match": { "rule": "", "relation": "none", "note": "" },
      "sources": ["T07-06", "T15-03", "R13-01", "R14-01", "V00-21"],
      "merge_notes": "All five are the same single-bar test; T15-03 used high[0] < ema for the bull case (a typo, mirrored wrong). Default 20 from every source.",
      "variants_kept_separate": ["TwentyGapBarRun"],
      "priority": "A",
      "design_decisions_needed": [],
      "depends_on_keys": []
    }
  ],
  "dropped": [
    { "id": "R28-19", "reason": "composition of EmaGapBar + High2 + TrendBarBody" }
  ],
  "cross_bucket": [
    { "id": "T19-13", "belongs_in": "leg_counting", "note": "a pullback count, not an EMA test" }
  ],
  "design_decisions": [
    { "topic": "always-in direction", "options": ["majority of last N closes vs EMA", "two consecutive strong trend bars flip", "breakout of N-bar range"], "recommended": "two consecutive strong trend bars (V15-01), the test Brooks states most often", "gates": ["AlwaysInFilter", "AlwaysInFlipEntry"] }
  ],
  "bucket_summary": "Two or three sentences: what was in the bucket, how much collapsed, what the A-list is."
}
```

Field notes:

- `key` is the canonical PascalCase rule name, naming the condition
  (`EmaGapBar`), not a strategy. It becomes the `rules/<Name>.json` filename if
  authored, so check it does not collide with a name in `rules/CATALOG.md` unless
  `catalog_match` is `duplicate`.
- `pseudocode` is the long side in the corpus dialect (`close[0]`, `high[1]`,
  `ctx.MarketPosition()`); helpers like `ema(close, n)[k]`, `highest(high, n)`,
  `swingHigh(strength)` are fine.
- `sources` lists every merged candidate id. **Coverage rule:** every candidate id
  in the bucket appears in exactly one of: some rule's `sources`, `dropped`, or
  `cross_bucket`. The roll-up checks this; a missing id fails the bucket.
- `el_words_needed` is the union over the sources, normalized to register tokens
  where obvious (`XAverage`, `Highest`, `AvgTrueRange`, `Time`, `BarsSinceEntry`).

## Report back

Under 25 lines: path written; candidates in → rules out; rules by priority A/B/C/D;
the A-list keys; catalog duplicates found; design decisions raised; strays sent to
other buckets. Do not paste the JSON.
