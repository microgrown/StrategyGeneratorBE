# Merging mined Grimes candidates into canonical rules

This is the brief for every merge agent. Read it fully before opening a bucket.

## Job

You get one topic bucket, `reference/grimes/merge/buckets/<bucket>.json`: the full
mined candidates (schema: `reference/grimes/MINING.md` "Output file") that a keyword
pass judged to be about one topic, drawn from every chapter of Adam Grimes, *The Art
and Science of Technical Analysis* (2012). Seven agents mined the book chapter by
chapter and were told to redefine shared primitives in every file, so the bucket is
full of restatements. Your output is `reference/grimes/merged/<bucket>.json`: the
distinct rules in the bucket, each with every source it came from, ready for the
`author-rule` pass.

You are **merging, not authoring**. Do not write `rules/*.json`, do not edit
`rules/CATALOG.md` or `rules/EL_FEATURES.md`, do not touch anything outside
`reference/grimes/merged/`. Parallel agents share one scratchpad directory: prefix
any scratch file you make with your bucket name. Read the bucket JSON directly and
write the output with the Write tool (a large merged file exceeds the shell
argument limit). Keep `merge_notes` under 60 words. If your bucket yields more than
about 40 rules, write the file in two steps: Write the first half, then Edit the
second half in, so no single response exceeds the output cap.

## How to merge

**Compare on behaviour, not wording.** Two candidates are one rule when they would
fire on the same bars given the same parameters. The three tests from `author-rule`
section 2 apply: same bars; one is the other negated or flipped (a per-placement
toggle, so redundant by construction); one is the other at a fixed parameter. A
threshold that differs between two candidates is one rule with a parameter; record
both book values in `merge_notes` and pick one as the default.

**Pick the most mechanizable definition.** When restatements differ in how they
would be coded, prefer the one that needs the least machinery: a fixed-offset
comparison over a swing-pivot search, a window extreme over pivot detection, an
existing `ctx` built-in over local emulation. Say in `merge_notes` which definition
won and why. Keep the losing definitions' ids in `sources`; they are citations, not
rules.

**Keep behaviourally distinct rules apart, even when they share a name.** A single
close outside the Keltner band and a run of N consecutive closes outside it are two
rules. A spring defined by one bar's close back inside and one defined by a
multi-bar recovery are two rules until someone measures that they coincide. List
such near-misses in `variants_kept_separate` on both rules so the authoring pass
sees the pair.

**Atomic beats composite.** The pane system ANDs entries and ORs exits, so a
composite of independently meaningful conditions is worse than its parts. Carry the
parts as rules. Carry the composite only when it is one of Grimes's named templates
that Brian would want to test as the book states it (`FailureTest`, `Anti`,
`ComplexPullback`, `Spring`/`Upthrust`, the breakout templates, `ThreePushes`);
give it `depends_on_keys` naming the parts and grade it by its hardest part. Drop
ad hoc composites with reason "composition of <keys>".

**Check the existing corpus, carefully.** The corpus already holds about 460 rules,
most of them mined from Al Brooks, and Grimes overlaps Brooks heavily on bar
anatomy, swing pivots, trend lines, three pushes, failed breakouts, measured moves,
EMA distance and stop placement. Read `rules/CATALOG.md` once. For every merged
rule set `catalog_match`: `duplicate` (same bars, do not author again), `variant`
(same idea, different behaviour, say how), `parameterization` (existing rule at a
fixed input, or an existing rule plus one new tolerance input), or `none`. A
`duplicate` gets priority `D`. A `parameterization` that only needs a new input on
the existing rule gets priority `A` with `merge_notes` saying which input to add.
When a candidate's `likely_existing_rule` names a catalog rule, open
`rules/<Name>.json` and compare the actual test before deciding.

**Cross-bucket strays.** `belongs_in` must be an exact bucket filename (see
`reference/grimes/merge/buckets/`). Strays sent to a bucket whose agent has already
finished are placed by the reconciliation pass at the end, so do not wait on them.
If the orchestrator's prompt names strays sent to you, they are not in your bucket
file: grep the id in `reference/grimes/mined/`. The keyword pass is crude. A
candidate that clearly belongs to another topic goes in `cross_bucket` with the
bucket it belongs to; do not merge it here. Candidates whose `secondary` buckets
(see `reference/grimes/merge/secondary.tsv`) include yours may be merged by that
other agent too; that is fine, the roll-up reconciles by id.

**Standing conventions**, inherited from mining: stop and limit entries are bar
close then next-bar open; intraday-only rules are kept and tagged; hard and
research grades are kept with a reason; multi-timeframe ideas are kept with the
higher timeframe approximated by a longer lookback on the same bars. Do not
re-reject on those grounds. **Do re-reject on the shift test**: if a candidate's
test depends on the price level rather than on price differences (round numbers,
percent of price, comparison of a price against zero), drop it with reason
"shift test"; the data are back-adjusted futures.

**Indicator facts settled by the mining pass**, use them rather than re-deriving:

- Grimes's 3/10 oscillator is `Average(close, 3) - Average(close, 10)` (simple
  averages), with a 16-period simple average of that difference as the signal line.
  It needs no `MACD` EasyLanguage word; its `el_words_needed` is `Average`. Never
  list `MACD`.
- The Keltner channel is a 20-period moving average with bands at 2.25 times a
  20-period ATR. The book does not say whether the centre line is simple or
  exponential; the existing catalog rule `KeltnerChannelCross` uses a simple
  average. Whichever bucket owns the Keltner primitive records this as a design
  decision with a recommendation; the centre-line type should be a parameter if
  the register supports both cheaply.
- Stochastic-based definitions (the original Raschke Anti) need `FastK`/`SlowK`,
  which are not registered; keep them as `C` with that word named, unless Grimes's
  own non-stochastic form covers the same behaviour, in which case merge into it.
- Risk multiples ("exit half at 1R") have no initial-risk accessor in the engine;
  express them with a `stopDistance` parameter, as the miners did, and note it.

## Priority

| priority | meaning |
|---|---|
| `A` | author next: trivial to moderate complexity, high confidence, no research-grade dependency, `catalog_match` none, variant, or a one-input parameterization |
| `B` | author after A: hard complexity but a clear definition (needs swing pivots, a persistent counter, an EMA, a session boundary) |
| `C` | blocked on a design decision: research grade, or depends on a research-grade primitive (a support/resistance level, "the higher time frame is trending", "the market is in a range") |
| `D` | do not author: duplicate of a catalog rule, fails the shift test, or on re-read not mechanizable |

Every `C` names the decision in `design_decisions_needed`, and the bucket file's
top-level `design_decisions` states each decision once with the options you see in
the sources and the option you recommend. If the orchestrator's prompt lists
"decisions already taken" by earlier buckets, build on them instead of raising the
same decision again; a rule that only needed that decision moves from `C` to `B`.

## Output file

`reference/grimes/merged/<bucket>.json`. Valid JSON, UTF-8. Validate with
`python -c "import json;json.load(open(path, encoding='utf-8'))"` before finishing.

```json
{
  "bucket": "indicators_bands",
  "merged": "2026-09-21",
  "rules": [
    {
      "key": "CloseOutsideKeltnerBand",
      "role": "Entry",
      "is_filter": false,
      "description": "The bar closes above the upper Keltner band (long) / below the lower band (short).",
      "pseudocode": "close[0] > ema(close, length)[0] + bandMult * atr(length)[0]",
      "sides": "mirrored",
      "parameters": { "length": 20, "bandMult": 2.25 },
      "complexity": { "grade": "moderate", "reason": "needs an EMA and an ATR; single-bar test otherwise" },
      "timeframe": "any",
      "el_words_needed": ["XAverage", "AvgTrueRange"],
      "catalog_match": { "rule": "KeltnerChannelCross", "relation": "variant", "note": "catalog rule fires on the cross; this fires on every bar closed outside" },
      "sources": ["G03-05", "G05-02", "G07-05", "G16-09"],
      "merge_notes": "Four restatements of the same single-bar test; G05-02 used high[0] instead of close (a looser variant, kept separate as HighBeyondKeltnerBand). Default 2.25 from Table 7.1.",
      "variants_kept_separate": ["HighBeyondKeltnerBand", "FreeBarOutsideBand"],
      "priority": "A",
      "design_decisions_needed": [],
      "depends_on_keys": []
    }
  ],
  "dropped": [
    { "id": "G06-40", "reason": "composition of PullbackHoldsAboveEma + CountertrendImpulse + AntiTrigger" }
  ],
  "cross_bucket": [
    { "id": "G03-24", "belongs_in": "exits_targets", "note": "a profit target, not a band read" }
  ],
  "design_decisions": [
    { "topic": "Keltner centre line", "options": ["simple average (matches KeltnerChannelCross)", "exponential (conventional)", "parameter"], "recommended": "exponential, matching Grimes's charts; make it a boolean input if cheap", "gates": ["CloseOutsideKeltnerBand", "FreeBarOutsideBand"] }
  ],
  "bucket_summary": "Two or three sentences: what was in the bucket, how much collapsed, what the A-list is."
}
```

Field notes:

- `key` is the canonical PascalCase rule name, naming the condition
  (`CloseOutsideKeltnerBand`), not a strategy. It becomes the `rules/<Name>.json`
  filename if authored, so check it does not collide with a name in
  `rules/CATALOG.md` unless `catalog_match` is `duplicate`.
- `pseudocode` is the long side in the corpus dialect (`close[0]`, `high[1]`,
  `ctx.MarketPosition()`); helpers like `ema(close, n)[k]`, `highest(high, n)`,
  `swingHigh(strength)` are fine.
- `sources` lists every merged candidate id. **Coverage rule:** every candidate id
  in the bucket appears in exactly one of: some rule's `sources`, `dropped`, or
  `cross_bucket`. The roll-up checks this; a missing id fails the bucket.
- `el_words_needed` is the union over the sources, normalized to register tokens
  where obvious (`XAverage`, `Average`, `Highest`, `AvgTrueRange`, `Time`,
  `BarsSinceEntry`, `SwingHigh`).

## Report back

Under 25 lines: path written; candidates in to rules out; rules by priority
A/B/C/D; the A-list keys; catalog duplicates found; design decisions raised (state
each in one line so the orchestrator can pass it downstream); strays sent to other
buckets. Do not paste the JSON.
