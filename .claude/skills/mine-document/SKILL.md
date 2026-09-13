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
| 2 Merge | dedup across chapters, rank, group by primitive; triage `el_words_needed` against `rules/EL_FEATURES.md` | one strong-model agent, then probes | `reference/<source>/CANDIDATES.md` (planned) |
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

## 6. Hand-off to pass 2 (merge and feature triage)

Not yet run for Brooks; update this section when it is. What is already known:

- Expect roughly 40 percent of candidates to be near-duplicates of primitives defined
  in other chapters (trend bar, doji, inside bar, swing pivot, measured move, always-in,
  H1/H2 counter). Merge those first; the survivor keeps every source citation.
- A few research-grade concepts gate hundreds of candidates and need one design
  decision each before authoring: always-in direction, trading-range vs trend
  classification, "tight channel". Decide once, centrally.
- Prefer the most mechanizable definition when merging: for the H1/H2 leg counter that
  is Ranges ch17 `R17-01` (no swing pivots needed), not the research-graded versions.
- Collect `el_words_needed` across survivors and check each against
  `rules/EL_FEATURES.md`; unregistered words get one probe each, per `author-rule` §4,
  before any authoring agent is launched. Otherwise every authoring agent stops on the
  same word and writes a duplicate probe.
- Engine primitives requested repeatedly and absent: a fixed initial-stop price
  accessor, and a minimum-position-profit tracker (mirror of `MaxPositionProfit`).
- Authoring agents in pass 3 get disjoint slices, write only `rules/*.json` and their
  TS twins, and return CATALOG / EL_FEATURES rows as text for the orchestrator to
  append, so they never collide on shared files.

---

## Log

- **2026-09-12, Brooks trilogy.** 3 PDFs, 1291 pages, ~870k tokens. 108 chapter files,
  99 mined. 27 assignments planned; 20 Fable miners launched at once died on the
  session limit after writing 9 files; reran as 25 Sonnet assignments at 5 concurrent,
  about two hours wall clock. Result: 1635 candidates (1399 Entry, 232 Exit, 4
  Switch), 367 rejected; complexity trivial 217 / simple 224 / moderate 495 / hard 457
  / research 242; 180 intraday-only. Per-miner cost 110k–245k tokens. Pass 2 not
  started.
