# Authoring Brian's own rules (OneNote + phone notes)

Brief for every authoring agent, 2026-11-05. Read it fully, then read
`.claude/skills/author-rule/SKILL.md` fully (the procedure), then
`reference/brooks/AUTHORING.md` fully. Everything there applies here, including the
B-list addendum (measured SwingHigh/EMA/TLValue/tick primitives, double placement),
except where this file says otherwise.

## Inputs

- Your slice: `reference/my_onenote/author/slices/NN_<family>.json`.
  - `rules[]` are the candidates to author. Each one is a spec in the schema of
    `reference/my_onenote/MINING.md`: `name` is the proposed key, and `pane`,
    `library_check`, `pseudocode` (long side), `sides`, `parameters` and `notes`
    are all there.
  - `primitives_to_inline[]` are shared building blocks the rules depend on. They
    are inlined in the code, never authored as their own file, unless your slice
    lists them under `rules`.
  - `resolutions[]` are Brian's answers. **They override `notes` and
    `open_questions` wherever the two conflict.**
- `reference/my_onenote/author/KEYS.md`: every key in every slice, for the
  cross-slice duplicate check.
- `reference/my_onenote/TRIAGE.md`: the row behind each candidate (`triage_row`).
  Its Decisions section holds every settled answer.
- Raw note wording: `reference/my_onenote/text/strategies.txt`,
  `reference/my_onenote/text/indicators.txt`, `reference/my_onenote/phone_notes.txt`.

## What is specific to this batch

- **Pane 1 is one rule.** A pane-1 candidate is authored as ONE rule containing its
  whole pattern (a tight cluster, such as a large bar followed by a pause and then
  the trigger). Its trend or volatility filters are separate pane-2 candidates;
  never fold them in. The reverse comes from the GUI flip, so author the long side
  and its mirror per `sides`, nothing else.
- **Pane-2 candidates are plain conditions**: a threshold on an indicator, with its
  mirror where the spec says `mirrored`.
- **Exits** read position state (`ctx.EntryPrice()`, `ctx.BarsSinceEntry()`,
  `MarketPosition`). An exit tied to an entry's signal bar uses the bar at entry,
  found via `BarsSinceEntry`. See `rules/StopAtSignalBarRangeMultiple.json`.
- **Do not author `exists` / `exists-param` candidates**; the templates will use
  the named rule. If your re-check finds a `near` that is really `exists` or
  `exists-param`, do not write it: list it under "Not written" with the rule and
  the parameter mapping.
- **`extends`** (slice 05 only): `RangeWidthBelowAtrMultiple` and
  `AvgBodyBelowRangeFraction` each gain a `lag` input. The default is 0, and at
  that default the rule must behave exactly as before, character for character.
  Edit both twins, keep every existing input name and default, and update the
  reaches-back expression. These two are the only existing files any agent may
  edit.
- **Provenance in the catalog row.** End every "Fires when" cell with
  `Source: Brian's notes (<candidate id>, <triage row>).` The study separates this
  arm from the Davey and Brooks rules by that tag.
- **Swings are non-alternating**, using the measured `SwingHigh`/`SwingLow` form.
  "Fractal" with N bars per side is strength N; a 5-bar fractal is strength 2.
  Where a bar is both a swing high and a swing low, it counts as both, ordered by
  the bar's direction: a green bar is low then high, a red bar high then low.
- **Shift test**: no price levels, no percent-of-price. Coefficient of variation is
  on true range.
- **Gaps.** If a spec still leaves a real design gap after the resolutions, stop for
  that rule and report the question. Author the rest of the slice; do not invent
  the answer.

## What you may write

- `rules/<Key>.json` and `C:/Users/brian/source/repos/StrategyGeneratorTS/rules/<Key>.json`,
  for keys in your slice only. Never overwrite an existing file. The exception is
  the two `extends` amendments, in slice 05 only.
- `reference/my_onenote/author/rows/NN_<family>.md`: your CATALOG rows in the exact
  `rules/CATALOG.md` format, plus a `## Not written` list.

Do not edit `rules/CATALOG.md` or `rules/EL_FEATURES.md`, do not write probes, do
not commit, **do not build the engine** (the orchestrator runs compileCheck), and
never stop or kill any process. If a word turns out to be unregistered, report the
rule as blocked.

## Report back

Under 30 lines:
- The rules written (key, pane, one phrase each).
- The rules not written, with the reason.
- Any open design questions.
- Any `ASSUMED` register rows relied on.
- Anything outside the EL translation table.
- The rows-file path.

No JSON.
