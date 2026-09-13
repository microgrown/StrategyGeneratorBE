# Authoring the Brooks A list

Brief for every authoring agent. Read it fully, then read
`.claude/skills/author-rule/SKILL.md` fully; that skill is the procedure and this
file only says what is specific to this batch.

## Inputs

- Your slice: `reference/brooks/author/slices/NN_<family>.json`. Each entry is a
  merged rule: `key` (the intended rule name), `role`, `description`, `pseudocode`
  (long side, corpus dialect), `sides`, `parameters` (input name → default),
  `complexity`, `catalog_match`, `sources` (mined candidate ids, for citation),
  `merge_notes`, `variants_kept_separate`, `depends_on_keys`, `el_words`.
- `reference/brooks/author/A_KEYS.md`: every key in every slice, for the
  cross-slice duplicate check.
- `rules/CATALOG.md`, `rules/EL_FEATURES.md`, `README.md` §"Writing rules" and
  §"The `ctx` API", per the skill.
- If a merged rule's pseudocode is unclear, the mined candidate is in
  `reference/brooks/mined/**/*.json` (grep its id) with the book quote and page.

## Both twins, every rule

Every rule is two files with the same name and the same inputs:

- `rules/<Key>.json` — the C++ rule (schema `rule.py:74-98`; examples
  `rules/Breakout.json`, `rules/Momentum.json`, `rules/BarRangeAboveStd.json`,
  `rules/MonthlyProfitTarget.json`).
- `C:/Users/brian/source/repos/StrategyGeneratorTS/rules/<Key>.json` — the
  EasyLanguage twin (same field names minus `classMembersHook`; conditions are EL
  expressions, e.g. `Close = Highest(Close, lookback)`; see the TS `Breakout.json`
  next to the BE one). Write the EL twin first: EasyLanguage's behaviour is the
  specification, and the lint reads the EL twin as the primary feature source.

Translate the merged `pseudocode` into EL first, then mirror it in C++ exactly
per the skill's translation table (`el_gt`/`el_lt`/`el_eq` for comparisons,
loops into locals for `Highest`/`Lowest`/`Average`, `WFSafe_AvgTrueRange` rolling
form for ATR, population standard deviation, zero-initialized mirrored buffers
for variable history). Every merged `parameters` entry becomes an input with the
merged default. `sides` says whether the short side is mirrored or identical.

## Per-rule gate

For each rule, in order:

1. Duplicate check (skill §2) against `rules/CATALOG.md` **and**
   `reference/brooks/author/A_KEYS.md`. The merge pass already set
   `catalog_match`; re-check it against the actual JSON of the named rule. On a
   `duplicate`, do not write the rule; record it in your report. On a suspected
   duplicate the merge pass missed, stop for that rule and report it; author the
   rest.
2. Feature check (skill §4): every EL word the twin uses must be VERIFIED or
   ACCEPTED in `rules/EL_FEATURES.md`. Your slice was pre-filtered, but the
   translation may reach for something new (`MaxList`, `AbsValue`, `CountIF`
   are registered; `XAverage`, `SwingHigh`, `MinMove`, `TLValue` are not). If a
   rule needs an unregistered word after all, do not write it; report it as
   blocked on that word. Do not write probes and do not edit EL_FEATURES.md.
3. `validateRule` (skill §5), then `python lintElFeatures.py <Key>`. Both must
   pass before the files stay.
4. Deepest bar index reached, as an expression over inputs, for the catalog row.

## What you may write

- `rules/<Key>.json` and `StrategyGeneratorTS/rules/<Key>.json` for keys in your
  slice only. Never overwrite an existing file of either name.
- `reference/brooks/author/rows/NN_<family>.md`: your CATALOG rows, one per rule
  written, in the exact `rules/CATALOG.md` table format
  (`| Rule | Type | Sides | Reaches back | Inputs | Fires when |`), plus a
  `## Not written` list (key, reason: duplicate of X / blocked on word W /
  suspected duplicate of Y / not translatable because Z).

Do **not** edit `rules/CATALOG.md` or `rules/EL_FEATURES.md`; the orchestrator
appends the rows so parallel agents do not collide. Do not commit.

## Naming and inputs

- Use the merged `key` as the name unless it collides with an existing rule; then
  pick a name that says how it differs and note it.
- Input names are the merged parameter names; if a merged pseudocode hard-codes a
  number that Brooks tunes (a tick count, a bar count, a fraction), promote it to
  an input with that default.
- Tick offsets: a "ticks" parameter cannot be converted to price without
  `MinMove`/`PriceScale`, which are unregistered. Express such thresholds as a
  price-unit input (`offsetPoints`) or a fraction of ATR / bar range instead, and
  say so in the row. Rules in your slice were filtered to avoid tick units, but
  check.

## Report back

Under 30 lines: rules written (key, role, one phrase), rules not written with
reason, any `ASSUMED` register row a rule now leans on, anything outside the EL
translation table, and the path of your rows file. No JSON in the report.
