---
name: mine-document
description: Orchestrate mining a trading book, paper, lecture, or other document (PDF or text) for candidate trading rules, feeding the author-rule skill. Use when Brian drops a document and asks for it to be mined, parsed, or processed for rules, or asks you to act as an orchestrator over a long source. Covers sizing the source, extracting text once, writing the per-source mining brief, dispatching chapter-sized subagents without blowing the session limit, validating their output, and handing off to the dedup / feature-triage / authoring passes. Does not itself write rules/*.json.
---

# Mining a document for rules, as an orchestrator

You are the orchestrator. Your session stays small: subagents read the source and
write the candidate files; you size, brief, dispatch, validate, and report. The
worked instance of this skill is the Al Brooks trilogy under `reference/brooks/`
(mined 2026-09-12); copy from it rather than reinventing.

The pipeline has four passes. This skill is authoritative for pass 1 and the
hand-off into pass 2. Passes 3 and 4 have their own skills.

| Pass | What | Who | Output |
|---|---|---|---|
| 1 Mine | source → per-chapter candidate JSON | Sonnet miners, 5 at a time | `reference/<source>/mined/**.json` |
| 2 Merge | feature triage, topic buckets, dedup per bucket, reconcile, roll-up | scripts + Opus merge agents, 3 at a time | `reference/<source>/CANDIDATES.md` |
| 3 Author | survivors → `rules/*.json` via `author-rule`, disjoint slices | strong-model agents | rules + CATALOG rows |
| 4 Template | grids via `design-grid` | separate sessions | `templates/*.json` |

Standing decisions from Brian that every brief inherits (do not re-ask):

- **Stop and limit entries are mechanized as signal-bar close then next-bar open.** The
  generator has no stop-entry-at-price path. Record the book's real order type in
  `book_order_type`.
- **Do not reject intraday-only ideas.** Tag `timeframe: intraday-only` and keep them.
- **Keep trend lines, channels, leg counts and other non-trivial constructs**, graded by
  the `complexity` field (`trivial | simple | moderate | hard | research` + reason) so
  the authoring pass knows what it is walking into.
- Miners write only under `reference/<source>/mined/`. Nothing in `rules/` is touched
  until pass 3.

---

## 1. Size the source before anything else

```
python -c "
from pypdf import PdfReader; import logging; logging.disable(logging.CRITICAL)
r=PdfReader('<file>.pdf', strict=False); n=len(r.pages)
t=''.join((r.pages[i].extract_text() or '') for i in range(min(n,40),min(n,60)))
print(n,'pages ~',n*len(t)//20//4//1000,'k tokens')"
```

| Size | Plan |
|---|---|
| under ~60k tokens (an article, a lecture deck, a Davey-style book with code) | one miner, whole document, no split; still extract to text first |
| 60k–150k | split by chapter, 2–4 miners |
| 150k+ (each Brooks volume was 240k–325k) | split by chapter, group into ~25–40k-token assignments, one miner each |

A miner that reads more than ~40k tokens of source starts compacting and loses the
early chapters. Never hand one agent a whole long book.

Non-PDF sources: `.txt`/`.md` need no extraction; `.docx` via `python-docx`;
`.epub`/`.html` strip to text with `pandoc` if installed, otherwise BeautifulSoup. The
rest of the pipeline only needs per-chapter text files with `[[page P]]` markers (or
section markers when there are no pages).

## 2. Extract text once, by subagent

Delegate to one general-purpose agent. Point it at `reference/brooks/extractText.py`:
the chapter detection (PDF outline → `Chapter N` heading lines → printed TOC
fallback), running-header stripping, ligature unfolding, `[[page P]]` markers and
manifest writing are all reusable. It has a hardcoded `BOOKS` list near the top; the
agent copies the script to `reference/<source>/extractText.py` and edits that list.

Output layout (keep it, the miners and `tally.py` assume it):

```
reference/<source>/
  extractText.py
  MANIFEST.md, MANIFEST.json      # chapter, title, file, pdf_pages, chars, approx_tokens
  MINING.md                        # the brief, see §3
  tally.py                         # copy of reference/brooks/tally.py, edit the books dict
  text/<book>/NN_<slug>.txt        # GIT-IGNORED: copyrighted text
  mined/<book>/NN_<slug>.json      # committed
```

Add `reference/<source>/text/` to `.gitignore` in the same step. Ask the extraction
agent for a report under 40 lines: detection method, chapter counts, suspicious
boundaries, total tokens per book. Check the first line of each chapter looks like a
title; Ranges needed a second pass because a TOC page matched the heading regex.

Known extraction defects to warn miners about: some pages lose inter-word spaces
(pypdf, Wiley layout), occasional kerning noise in first sentences. Miners read
through these; nothing rule-bearing was lost in Brooks.

## 3. Write the brief: `reference/<source>/MINING.md`

Copy `reference/brooks/MINING.md` and edit the source block. It carries the schema,
the conventions above, the complexity rubric, the pseudocode dialect, and the
report-back format. Two schema variants exist; pick by source type:

- **Prose source, no code** (Brooks): the `reference/brooks/MINING.md` schema. Fields:
  `id`, `name`, `role`, `is_filter`, `composite`, `composes`, `depends_on`, `pages`,
  `quote`, `description`, `pseudocode`, `sides`, `parameters`, `book_order_type`,
  `timeframe`, `complexity{grade,reason}`, `el_words_needed`, `likely_existing_rule`,
  `confidence`, `notes`; plus a per-file `rejected` list and `chapter_summary`.
- **Source with verbatim code** (Davey's *Entry and Exit Confessions*): the
  `reference/EntryExitConfessions.json` schema, which adds `tradestation_code`
  verbatim, `hardcoded_constants`, `decomposition`, `discrepancies`, and
  `el_words_unregistered`. Code is copied exactly and never corrected; disagreements
  between code and prose go in `discrepancies`.

Things the brief must say, because miners got them wrong when it did not:

- Every tunable constant is a parameter with the book's value as default.
- One condition per candidate; split compounds; a composite may be recorded in
  addition, naming its parts via `composes`.
- Shared primitives are defined once **per file** and cross-referenced by id inside
  that file. Cross-file duplication is expected; pass 2 merges it.
- High recall. Pass 2 discards; pass 1 cannot recover what it skipped. Chart
  walk-throughs that only reapply known primitives may be summarized, not re-mined
  bar by bar.
- Reject only: data the engine cannot have, randomness or wall clock, future bars,
  pure discretion with no bar-level test. Record rejects with page and reason.
- Validate the JSON with `json.load` before finishing.
- Report under 25 lines, no JSON pasted.

## 4. Dispatch miners

**Model: Sonnet.** Mining against a tight schema is well within it, and it costs a
fraction of the session budget. Reserve Fable/Opus for pass 2 and pass 3.

**Concurrency: five.** The harness caps subagents at 20, but the first Brooks wave of
20 Fable miners hit the *session* limit within minutes, and every agent died mid-file.
Five Sonnet miners ran for two hours without incident. Launch a replacement each time a
completion notification arrives; do not batch-wait.

**Assignments.** Contiguous chapters within one book, ~25–40k tokens each from the
manifest. Merge tiny chapters into neighbours; give a 40k chapter its own agent. Skip
about-the-author, about-the-website, index. Front matter usually contains a glossary
and a long introduction that are the densest primitive definitions in the book; mine
it as chapter 0.

**Prompt template** (short; the brief carries everything else):

```
You are a mining agent for <source>. Working directory: <repo>. Do all the work
yourself: do not spawn subagents or forks (concurrency is being rationed by the
orchestrator).

First read reference/<source>/MINING.md completely and follow it exactly. Skim
rules/CATALOG.md once for the dedup hints.

Book: "<title>" (book_key "<key>", id prefix <X>). Mine these chapter files under
reference/<source>/text/<key>/, writing one JSON per file to
reference/<source>/mined/<key>/<same basename>.json:
- NN_<slug>.txt   (long; read in slices of about 300 lines)
- ...              (Part intro; use chapter "P1" and id prefix <X>P1)

<one or two lines of chapter-specific steering, e.g. "signs-of-strength lists: one
candidate per sign", "this is the H1/H2 chapter, define the counter precisely">
Chapters already mined: <list>; do not touch their JSON. Write each chapter's JSON
as soon as that chapter is done. Report per the "Report back" section of MINING.md,
once for all files.
```

The "do not spawn subagents" line matters: without it a Sonnet miner forked six
children and silently multiplied concurrency. "Write each chapter as soon as it is
done" is what made the rate-limit deaths recoverable.

## 5. Validate, recover, report

Run `python reference/<source>/tally.py` after every few completions and at the end.
It parses every mined file, counts candidates by role / complexity / timeframe, and
flags candidates with no pseudocode or no page. Exit code 1 on a malformed file.

**Rate-limit death.** Files an agent wrote before dying are complete (each chapter is
one atomic Write). Validate them with the tally, list which basenames exist, and
relaunch only the missing chapters, telling the new agent which files not to touch.
Do not resume the dead agent.

**Orchestrator hygiene.** Never read a subagent's transcript file. Do not paste
candidate JSON into the session. Your per-completion message to Brian is one or two
lines: what finished, candidate count, what launched next, how many remain.

Final report to Brian: the tally table per book, the role and complexity split, and
the cross-cutting notes miners flagged for pass 2 (which primitives recur, which
research-grade concepts gate many candidates, which engine primitives were requested
and do not exist). Then stop, unless told to continue into pass 2.

## 6. Pass 2: merge and feature triage

Run for Brooks on 2026-09-12: 1635 candidates → 548 merged rules (A 228, B 212, C 75,
D 33), 245 dropped, coverage clean under `rollup.py --strict`. Result:
`reference/brooks/CANDIDATES.md`.

The mined corpus is too big for one agent (Brooks: 2.4 MB, ~600k tokens), so pass 2
is mechanical splitting, then one strong-model merge agent per topic, then a
mechanical roll-up. Scripts live in `reference/brooks/` and take the source dir as
their base; copy or point them at the new source.

1. **Feature triage first, it is cheap and it reshapes the plan.**
   `python reference/brooks/featureTriage.py` (default input `mined/**/*.json`,
   `--input <glob>` for later stages) normalizes every `el_words_needed` entry to a
   register token, looks it up in `rules/EL_FEATURES.md` via `lintElFeatures`, and
   writes `merge/EL_WORDS.md`. For Brooks: SwingHigh/SwingLow (528 candidates),
   XAverage (134), TLValue (41) had no register row, and 530 candidates depended on
   at least one missing word. Those probes get written once, before any authoring
   agent is launched. Plain `AvgTrueRange` maps to the registered `WFSafe_` variant
   (author-rule §4), it is a synonym, not a probe.
2. **Bucket by topic, not by book or alphabet.** `python reference/brooks/bucketize.py`
   assigns each candidate one primary bucket by keyword rules over name, description
   and pseudocode, sub-splits any bucket over ~45k tokens by finer keywords, and writes
   `merge/buckets/<bucket>.json` with full candidate objects plus `index.tsv`,
   `secondary.tsv` (other buckets that also matched) and `buckets/SUMMARY.md`. Iterate
   the keyword lists until `misc` is under 5 percent (Brooks: 23 buckets, misc 2.5
   percent). Candidates about one concept must share a file or the dedup cannot see
   them together.
3. **Brief:** `reference/brooks/MERGE.md`. Merge on behaviour not wording; prefer the
   most mechanizable definition; keep behaviourally distinct variants apart and
   cross-link them; atomic beats composite except for named book setups; check every
   merged rule against `rules/CATALOG.md`; priority A (author now) / B (hard but
   defined) / C (blocked on a design decision) / D (drop). Coverage rule: every
   candidate id lands in exactly one of a rule's `sources`, `dropped`, or
   `cross_bucket`.
4. **Merge agents: Opus for judgment-heavy buckets, Sonnet for mechanical ones, three concurrent, one bucket each** (combine buckets under
   ~20k tokens into one agent that writes one file per bucket). Prompt: read MERGE.md,
   read CATALOG.md once, read the bucket in full, write `merged/<bucket>.json`, report
   under 25 lines. Same "do not spawn subagents" line as miners, plus: **parallel
   subagents share one scratchpad directory**, so tell each to prefix scratch files
   with its bucket name; a Brooks merge agent had its working dump overwritten by a
   sibling mid-read. Have them read the bucket JSON directly and write the output
   with the Write tool: a 70 KB merged file exceeds the shell heredoc argument limit,
   and one agent died on exactly that. Four Opus merge agents at once hit the session
   limit in about twenty minutes (each costs ~180k tokens); three is the ceiling.
   **A subagent reported as failed may still have finished its file**: four of the
   five rate-limited Brooks merge agents had already written complete, coverage-clean
   output. Run the roll-up and trust its per-bucket coverage, not the task status,
   before relaunching anything. **Cap single-response output**: a Sonnet merge agent
   died emitting a 79-candidate merged file in one Write (over the 64k output-token
   limit). Tell merge agents to keep merge_notes under 60 words, and to write the file
   in two steps (Write the first half, Edit in the second) when a bucket has more than
   about 40 rules.
   **Order the buckets so decisions flow downstream.** Run the buckets that own a
   shared primitive or design decision first (swing pivots, leg counting, always-in,
   trading-range classification, spike definition, trend-line construction) and paste
   each settled decision into every later prompt as "decisions already taken". In
   Brooks this turned dozens of research-graded candidates into B rules because the
   later agents could build on a defined primitive instead of re-deferring.
5. **Stray reconciliation, after the last merge:** agents send misfiled candidates to
   other buckets via `cross_bucket`, but a target agent that had already finished
   never sees them. The roll-up lists the ones that fell through; one small agent
   absorbs them into the right merged files at the end.
6. **Roll-up:** `python reference/brooks/rollup.py [--strict]` checks coverage per
   bucket, reconciles `cross_bucket` strays, flags key collisions with `rules/*.json`,
   and writes `CANDIDATES.md` (tables per priority, design decisions unioned by
   topic, EL words over A and B rules, dropped appendix) plus `merge/RULES.tsv`.

Known from the mining reports, to expect when merging: about 40 percent of
candidates restate primitives defined in other chapters (trend bar, doji, inside
bar, swing pivot, measured move, always-in, H1/H2 counter). A few research-grade
concepts gate hundreds of candidates and need one central decision each: always-in
direction, trading-range vs trend classification, "tight channel". The H1/H2 leg
counter from Ranges ch17 `R17-01` is the most mechanizable definition. Two engine
primitives were requested repeatedly and do not exist: a fixed initial-stop price
accessor and a minimum-position-profit tracker.

**Feature triage after merging, not only before.** Re-run `featureTriage.py --input
"reference/<source>/merged/*.json"` (it reads `rules[]`, skipping priority D). For
Brooks the blocking words over the 515 authorable rules were SwingHigh/SwingLow
(92 rules), MinMove/PriceScale (49, tick size), TLValue (32), XAverage (30), plus
MinPositionProfit (an engine primitive, not an EL word). Four probes unblock almost
everything that is not A already.

## 7. Pass 3: probes, then authoring

1. **Probes first, one agent.** The post-merge triage names the unregistered words;
   one Opus agent writes all the probes per `author-rule` §4 (template in the engine
   repo, one file per word family, UNKNOWN rows added to `rules/EL_FEATURES.md`). It
   is the only agent allowed to edit the register. Brooks: Swing*, MinMove/PriceScale,
   TLValue, XAverage. Brian runs the probes in TradeStation; nothing that needs those
   words is authored until the rows flip. Ask the probe agent to also check what the
   engine exposes: for Brooks it found tick size never reaches strategies and that
   MinPositionProfit is not an EL word, both engine work rather than probes.
2. **Split the A list by blockage, not by hand.** A script reads `merged/*.json`,
   normalizes each A rule's `el_words_needed`, looks them up via
   `lintElFeatures.loadRegistry()`, and writes `author/A_QUEUE.json` with `unblocked`
   and `blocked` lists. Brooks: 228 A rules → 176 unblocked, 52 blocked (32 on tick
   size, 14 on XAverage).
3. **Slice the unblocked list by bucket family, ~12–15 rules per slice**, into
   `author/slices/NN_<family>.json`, plus `author/A_KEYS.md` listing every key so each
   agent can check sibling slices for duplicates. Run different families in parallel,
   not two slices of the same family.
4. **Brief:** `reference/brooks/AUTHORING.md`. The load-bearing points: every rule is
   two files, the C++ in `rules/` and the EasyLanguage twin in
   `../StrategyGeneratorTS/rules/` (the lint reads the EL twin as its primary source,
   so write EL first); the per-rule gate is duplicate check, register check,
   `validateRule`, `lintElFeatures.py <Key>`; agents write only their own rule files
   and a rows file under `author/rows/`, never `CATALOG.md` or `EL_FEATURES.md`; tick
   thresholds become price or ATR inputs until MinMove is registered.
5. **Agents: Opus, three concurrent**, one slice each. After each completion the
   orchestrator appends the rows file to `rules/CATALOG.md` and launches the next
   slice. Finish with `lintElFeatures.py` over the whole corpus and the engine
   Release build, which is the real check on the C++.
6. **Cross-slice duplicates are the main failure mode.** Agents stop on a suspected
   duplicate, as the skill requires, and two slices routinely defer the same rule to
   each other so neither writes it (Brooks: `BounceFromLowByAtr`/`DistanceAboveRecentLow`,
   `BodyGapBar`/`BarOpensAbovePriorClose`). Mitigations that worked: tell every prompt
   which sibling keys are already on disk (point at `author/rows/*.md`); keep a
   `author/DECISIONS.md` and make each deferral an explicit assignment to a named
   slice; a `SendMessage` to a still-running agent lands at its next tool round and
   can hand it a rule; give any leftover orphan to the last slice. Agents also flag
   near-neighbours they wrote anyway; collect those pairs for one dedup review agent
   after the last slice, before the commit.
7. **Per-slice cost:** 12–14 rules, both twins, validated and linted, ran 145k–180k
   Opus tokens and 10–15 minutes each. Rows files append cleanly with
   `reference/brooks/appendRows.py`, which skips keys already in the catalog.


---

## Log

- **2026-09-12, Brooks trilogy.** 3 PDFs, 1291 pages, ~870k tokens. 108 chapter files,
  99 mined. 27 assignments planned; 20 Fable miners launched at once died on the
  session limit after writing 9 files; reran as 25 Sonnet assignments at 5 concurrent,
  about two hours wall clock. Result: 1635 candidates (1399 Entry, 232 Exit, 4
  Switch), 367 rejected; complexity trivial 217 / simple 224 / moderate 495 / hard 457
  / research 242; 180 intraday-only. Per-miner cost 110k–245k tokens.
- **2026-09-12, Brooks merge.** 23 topic buckets in 18 assignments plus one
  reconciliation agent; Opus merge agents cost 130k–205k tokens each, Sonnet ones
  about the same count. Four Opus at once hit the session limit (four of five files
  still landed complete); a Sonnet agent died on the 64k output cap. 1635 → 548 rules
  (A 228, B 212, C 75, D 33). Five design decisions settled by bucket owners and
  recorded in CANDIDATES.md for Brian to ratify: always-in, leg counter, trading range,
  tight channel, trend-line construction.
- **2026-09-13, Brooks pass 3.** One Opus agent wrote four probes and nine UNKNOWN
  register rows. 228 A rules → 176 unblocked; 14 Opus slices (145k–200k tokens each,
  10–16 min, 3–4 concurrent) authored 148 rules with twins, 28 dropped as cross-slice
  or catalog duplicates, one existing rule gained an input. A dedup-review agent
  removed 3 more and corrected 24 catalog rows; the corpus went 92 → 240 rules, lint
  and 319 tests clean, engine Release build clean via compileCheck.py. 52 A rules and
  all B rules wait on the probes; the tick-size ones also need a ctx accessor.
