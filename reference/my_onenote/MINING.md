# Candidate specs for Brian's own rules (OneNote + phone notes)

Brief for the spec agents, 2026-11-05. This source differs from Brooks: it is small,
already triaged row by row with Brian, and the job is to write one precise candidate
spec per KEEP idea and check it against the existing library. Nothing is authored.

## Inputs

- `reference/my_onenote/TRIAGE.md`: the authority. Only rows with status KEEP
  (including `KEEP (exit)` and the KEEP half of `X-DAVEY / KEEP`) become candidates.
  The row text records Brian's clarifications; where it differs from the raw note,
  the row wins. Read its "Decisions" section first.
- Raw wording: `text/strategies.txt` (Strategies.pdf; printed page = the
  `... Page N` footer), `text/indicators.txt`, `phone_notes.txt`.
- `rules/CATALOG.md` (~420 KB: grep it, do not read it whole) and `rules/<Name>.json`
  for any plausible match.

## Schema

Use the candidate schema of `reference/brooks/MINING.md` ("Output file"), with these
changes:

- `source` block: `{"source": "Brian's notebooks", "files": [...], "specced": "2026-11-05"}`.
- `id`: the TRIAGE row id prefixed `ON-` for Strategies.pdf rows (`ON-30`), `I3` for
  indicators, `P7` for phone notes, `P1a`..`P1f` for the P1 family. If one row yields
  several candidates (a primitive plus an entry, or a pane-2 filter split off), suffix
  `-a`, `-b`.
- `pages`: printed page(s) or phone-note line numbers. `quote`: the raw note wording
  (under 60 words). `book_order_type`: what the note implies, if anything.
- Add `pane`: `1` (pane-1 entry: one rule whose reverse is the opposite side),
  `2` (pane-2 condition/filter), `exit`, or `primitive` (a shared building block
  other candidates `depends_on`, such as the consolidation zone or the visit scan).
- Add `triage_row`: the TRIAGE row id.
- Add `library_check`: `{"verdict": "...", "rule": "<Name or empty>", "origin": "...", "evidence": "..."}`.
  - `verdict` is one of:
    - `exists`: the same bars fire, possibly at different defaults.
    - `exists-param`: an existing rule with a different parameter value.
    - `extends`: an existing rule plus one new input or a tolerance, behaviour-preserving at its default.
    - `near`: related but behaviourally distinct; name what differs.
    - `none`.
  - `origin`: where the matched rule came from, if the catalog row or JSON says so
    (Davey book or EEC, Brooks, Brian's earlier work, unknown). This matters because the
    study is about provenance: an own idea that coincides with a Davey rule must be
    surfaced, not silently reused.
- Replace `chapter_summary` with `summary`, and `rejected` with `not_specced`
  (KEEP rows you could not spec, with the reason).

## Conventions

- Inherit every convention in `reference/brooks/MINING.md` §"Conventions you must
  apply": entries are signal-bar close then next-bar open, every constant is a
  parameter (default from the note), one condition per candidate, long side only in
  pseudocode with `sides`, and the corpus's C++-ish dialect.
- Swings are NON-ALTERNATING throughout (EasyLanguage `SwingHigh`/`SwingLow`
  semantics, already ported). "Fractal" in Brian's notes means a swing pivot of the
  stated strength, and 5-bar fractals have strength 2.
- Pane 1 holds ONE rule (or a tight cluster) plus its reverse. The note's trend or
  volatility conditions go to separate pane-2 candidates. A classic construct is fine
  in pane 2.
- Parameter ranges need not be the note's; give a default and a plausible range.
  The design-grid skill sets grids later.
- Where the note leaves a gap, concretize it the obvious way and say so in
  `notes`. "Downtrend" becomes a named pane-2 trend filter candidate, for example
  close below the EMA(N), and a tolerance like "about the same level" becomes an ATR
  multiple. If a gap would need a real design decision (not just an obvious choice),
  do NOT invent one. Put it in `open_questions` (a top-level list in the output file) for Brian.
- The shift test (author-rule §1) applies: no price levels, no percent-of-price.
- `el_words_needed`: list the words; check each against `rules/EL_FEATURES.md` and
  mark any with no row or an UNKNOWN row in `notes`.
- `complexity` uses the Brooks grades.

## Output

One JSON file per agent under `reference/my_onenote/mined/`, validated with
`json.load`. Write it in two steps (Write half, then Edit in the rest) if it would
exceed about 40 candidates. Report under 25 lines: counts by pane and
`library_check` verdict, every `exists`/`exists-param` match with its origin, and the
open questions. Do not paste JSON.
