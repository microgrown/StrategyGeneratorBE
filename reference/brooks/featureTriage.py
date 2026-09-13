"""Triage every `el_words_needed` entry across the mined rule candidates
against the EasyLanguage feature register (`rules/EL_FEATURES.md`).

    python reference/brooks/featureTriage.py
    python reference/brooks/featureTriage.py --input "reference/brooks/merged/*.json"

Writes reference/brooks/merge/EL_WORDS.md and prints the same report to
stdout. Reuses `lintElFeatures.loadRegistry` rather than re-parsing the
register's markdown tables a second way.

WHY THIS EXISTS

`el_words_needed` is free-form: several different mining agents wrote it, so
the same EL feature shows up as "XAverage", "xaverage", "XAverage (EMA)",
"EMA", and so on. Before those candidates can be authored, every distinct
feature they lean on has to be either already VERIFIED/ACCEPTED in the
register or flagged as a probe to write. This script normalizes the raw
strings to register-style tokens, classifies each against the register, and
reports which tokens are blocking the most candidates -- so probing effort
goes where it unblocks the most work first.

NORMALIZATION, NOT GUESSING

Parenthesized notes and bracketed argument lists are stripped
(`XAverage (EMA)` -> `xaverage`, `Highest(High, n)` -> `highest`). A short
synonym table (below) maps known abbreviations and phrasings onto the
register's own token spelling. Anything left with internal whitespace after
that -- a sentence, an "X or Y" hedge, a parenthetical caveat that ate the
whole entry -- is NOT collapsed into a single guessed token; it is reported
under "raw / unmapped" instead, because a wrong guess here would silently
misclassify a candidate's real dependency.
"""
import argparse
import glob
import os
import re
import sys
from collections import Counter, defaultdict

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)
import lintElFeatures  # noqa: E402  -- reuse loadRegistry, don't re-parse the register

DEFAULT_INPUT = "reference/brooks/mined/**/*.json"
OUTPUT_PATH = os.path.join(_REPO_ROOT, "reference", "brooks", "merge", "EL_WORDS.md")
MISSING = "MISSING"

# Synonym table: normalized phrase (lowercase, single-spaced, hyphens/
# underscores already turned to spaces) -> the register's own token spelling.
# Extend this as mining turns up new phrasings; anything not covered here and
# not already a single bare word falls to raw/unmapped rather than a guess.
SYNONYMS = {
    "ema": "xaverage",
    "exponential average": "xaverage",
    "exponential moving average": "xaverage",
    "sma": "average",
    "simple moving average": "average",
    "moving average": "average",
    "average": "average",
    "atr": "wfsafe_avgtruerange", "avgtruerange": "wfsafe_avgtruerange", "wfsafe_avgtruerange": "wfsafe_avgtruerange", "wfsafe avgtruerange": "wfsafe_avgtruerange", "wfsafe adx": "wfsafe_adx", "wfsafe_adx": "wfsafe_adx",
    "average true range": "avgtruerange",
    "swing high": "swinghigh",
    "swinghigh": "swinghigh",
    "swing low": "swinglow",
    "swinglow": "swinglow",
    "time of day": "time",
    "timeofday": "time",
    "barssinceentry": "barssinceentry",
    "marketposition": "marketposition",
}

_PAREN = re.compile(r"\([^)]*\)")
_BRACKETED_ARGS = re.compile(r"\[[^\]]*\]")
_NON_ALNUM_SPACE = re.compile(r"[^a-z0-9 ]")
_WS = re.compile(r"\s+")


def normalize(raw):
    """raw string -> (token, confident). token is a candidate register key
    when confident is True; otherwise it is the cleaned phrase to display
    under raw/unmapped."""
    s = raw
    s = _PAREN.sub(" ", s)
    s = _BRACKETED_ARGS.sub(" ", s)
    s = re.sub(r"[-_]", " ", s)
    low = s.lower()
    low = _NON_ALNUM_SPACE.sub(" ", low)
    low = _WS.sub(" ", low).strip()
    if not low:
        return raw.strip().lower(), False
    if low in SYNONYMS:
        return SYNONYMS[low], True
    if " " not in low:
        return low, True
    return low, False


def collectWords(pattern):
    """[(candidateId, sourceFile, rawWord), ...] for every el_words_needed
    entry across every matched JSON file."""
    if not os.path.isabs(pattern):
        pattern = os.path.join(_REPO_ROOT, pattern)
    files = sorted(glob.glob(pattern, recursive=True))
    out = []
    for f in files:
        try:
            with open(f, encoding="utf-8-sig") as fh:
                import json
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            print(f"WARNING: could not read {f}: {exc}", file=sys.stderr)
            continue
        # Mined files carry `candidates` (id); merged files carry `rules` (key).
        # Priority-D merged rules are not authored, so their words do not block.
        items = list(data.get("candidates", []) or [])
        items += [r for r in (data.get("rules", []) or []) if r.get("priority") != "D"]
        for cand in items:
            cid = cand.get("id") or cand.get("key", "?")
            for word in cand.get("el_words_needed") or []:
                word = (word or "").strip()
                if word:
                    out.append((cid, f, word))
    return out, files


def triage(entries, registry):
    """token -> {"status": str, "candidates": set(id), "examples": [id,...],
    "raw": set(rawStrings)}; plus the raw/unmapped tally."""
    byToken = defaultdict(lambda: {"candidates": set(), "raw": set()})
    rawUnmapped = defaultdict(lambda: {"count": 0, "candidates": set()})

    for cid, _f, rawWord in entries:
        token, confident = normalize(rawWord)
        if not confident:
            rawUnmapped[token]["count"] += 1
            rawUnmapped[token]["candidates"].add(cid)
            continue
        entry = byToken[token]
        entry["candidates"].add(cid)
        entry["raw"].add(rawWord)

    rows = []
    for token, entry in byToken.items():
        status = registry.get(token, MISSING)
        rows.append({
            "token": token,
            "status": status,
            "count": len(entry["candidates"]),
            "examples": sorted(entry["candidates"])[:5],
            "rawForms": sorted(entry["raw"]),
        })
    return rows, rawUnmapped


def render(rows, rawUnmapped, filesScanned, totalEntries):
    blockingStatuses = (MISSING, "UNKNOWN")

    def sortKey(r):
        return (0 if r["status"] in blockingStatuses else 1, -r["count"], r["token"])

    rows = sorted(rows, key=sortKey)

    lines = []
    lines.append("# EL words needed -- feature triage")
    lines.append("")
    lines.append(f"Generated by `reference/brooks/featureTriage.py` from {filesScanned} "
                 f"mined JSON file(s), {totalEntries} `el_words_needed` entries total.")
    lines.append("")
    lines.append("Status is looked up in `rules/EL_FEATURES.md` via "
                 "`lintElFeatures.loadRegistry`. Per that register, a token with **no "
                 "row at all (MISSING) blocks authoring exactly like UNKNOWN** -- both "
                 "need a probe (or an ACCEPTED sign-off) before a rule that reaches for "
                 "them can be written.")
    lines.append("")
    lines.append("## Tokens")
    lines.append("")
    lines.append("| Token | Status | Candidates | Example candidate ids |")
    lines.append("|---|---|---:|---|")
    for r in rows:
        examples = ", ".join(r["examples"])
        lines.append(f"| `{r['token']}` | {r['status']} | {r['count']} | {examples} |")
    lines.append("")

    lines.append("## Blocking summary")
    lines.append("")
    blocking = [r for r in rows if r["status"] in blockingStatuses]
    if blocking:
        allBlockedCandidates = set()
        for r in blocking:
            allBlockedCandidates |= set(r["examples"])
        lines.append(f"{len(blocking)} distinct token(s) are MISSING or UNKNOWN. "
                     "Highest-impact first (probe these to unblock the most candidates):")
        lines.append("")
        for r in blocking[:15]:
            lines.append(f"- `{r['token']}` ({r['status']}) -- {r['count']} candidate(s), "
                         f"e.g. {', '.join(r['examples'][:3])}")
    else:
        lines.append("None -- every normalized token has a VERIFIED/ACCEPTED row.")
    lines.append("")

    lines.append("## Raw / unmapped")
    lines.append("")
    if rawUnmapped:
        lines.append("Could not be normalized with confidence -- extend `SYNONYMS` in "
                     "`featureTriage.py` or fix the source mining JSON, then re-run.")
        lines.append("")
        lines.append("| Raw / cleaned text | Count | Example candidate ids |")
        lines.append("|---|---:|---|")
        for text, info in sorted(rawUnmapped.items(), key=lambda kv: -kv[1]["count"]):
            examples = ", ".join(sorted(info["candidates"])[:5])
            lines.append(f"| {text} | {info['count']} | {examples} |")
    else:
        lines.append("None -- every entry normalized to a token.")
    lines.append("")
    return "\n".join(lines), blocking


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", default=DEFAULT_INPUT,
                        help=f"glob of mined JSON files (default: {DEFAULT_INPUT})")
    args = parser.parse_args(argv)

    registry = lintElFeatures.loadRegistry()
    entries, files = collectWords(args.input)
    rows, rawUnmapped = triage(entries, registry)

    # Recompute the true blocked-candidate set over full candidate sets, not
    # just the printed top-5 examples.
    byTokenFull = defaultdict(set)
    for cid, _f, rawWord in entries:
        token, confident = normalize(rawWord)
        if confident:
            byTokenFull[token].add(cid)
    blockedCandidates = set()
    for r in rows:
        if r["status"] in (MISSING, "UNKNOWN"):
            blockedCandidates |= byTokenFull[r["token"]]

    text, blocking = render(rows, rawUnmapped, len(files), len(entries))

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)

    print(text)
    print(f"\n(blocked candidates: {len(blockedCandidates)}; "
         f"distinct MISSING/UNKNOWN tokens: {len(blocking)}; "
         f"raw/unmapped distinct strings: {len(rawUnmapped)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
