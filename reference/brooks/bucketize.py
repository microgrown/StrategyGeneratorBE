#!/usr/bin/env python3
"""Bucketize the 1635 mined Brooks candidates into topic files small enough
for one dedup agent to read (<= ~45k tokens each, tokens ~= chars/4).

Usage: python reference/brooks/bucketize.py
Writes:
  reference/brooks/merge/index.tsv
  reference/brooks/merge/secondary.tsv
  reference/brooks/merge/buckets/<bucket>.json
  reference/brooks/merge/buckets/SUMMARY.md
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MINED_DIR = REPO_ROOT / "reference" / "brooks" / "mined"
MERGE_DIR = REPO_ROOT / "reference" / "brooks" / "merge"
BUCKETS_DIR = MERGE_DIR / "buckets"

TOKEN_BUDGET = 45_000  # approx tokens per bucket file
CHARS_PER_TOKEN = 4

# ---------------------------------------------------------------------------
# Primary bucket taxonomy, in priority order. First matching bucket wins.
# Keywords are matched as \b-delimited (word-boundary) case-insensitive
# regex fragments against name / description / pseudocode, searched in that
# order (name first; if nothing matches in name, try description; then
# pseudocode).
# ---------------------------------------------------------------------------
PRIMARY_BUCKETS = [
    ("exits_stops", [
        "stop loss", "protective stop", "breakeven", "break even", "trailing stop",
        "trail the stop", "tighten stop", "tighten the stop", "stop beyond signal bar",
        "stop beyond the signal bar", "initial stop", "stop at", "stop above", "stop below",
        "wide stop", "stop under", "stop over", "move the stop", "raise the stop",
        "lower the stop", "hard stop", "giveback", "give back", "stop order",
    ]),
    ("exits_targets", [
        "profit target", "take profit", "measured move target", "scalp target",
        "reward", "risk multiple", "risk:reward", "risk reward", "scale out",
        "exit at", "exit on", "swing target", "target price", "first target",
        "second target", "partial exit", "measured target", "measured move",
    ]),
    ("leg_counting", [
        "high 1", "high1", "h1", "h2", "high 2", "low 1", "low1", "l1", "l2", "low 2",
        "leg count", "two-legged", "two legged", "second entry", "second signal",
        "pullback count", "first pullback", "second pullback", "third pullback",
        "one legged", "one-legged", "leg up", "leg down", "counting legs",
        "pullback bar",
    ]),
    ("ema_relations", [
        "ema", "moving average", "gap bar", "20 gap", "20-bar ema", "20 ema",
        "moving average gap", "xaverage", "average line",
    ]),
    ("bar_anatomy", [
        "trend bar", "doji", "inside bar", "outside bar", "\\bii\\b", "\\biii\\b",
        "ioi", "oio", "tail", "body fraction", "close near", "two-bar reversal",
        "two bar reversal", "pause bar", "bar overlap", "small bar", "large bar",
        "big bar", "bull bar", "bear bar", "reversal bar", "signal bar", "entry bar",
        "wide range bar", "narrow range bar", "climactic bar",
    ]),
    ("swing_structure", [
        "swing high", "swing low", "higher high", "lower low", "higher low",
        "lower high", "double top", "double bottom", "pivot", "micro double",
        "major swing", "minor swing", "swing point", "ledge", "prior high", "prior low",
    ]),
    ("three_push_patterns", [
        "wedge", "three push", "3 push", "triangle", "expanding triangle",
        "head and shoulders", "final flag", "three-push", "diamond",
    ]),
    ("lines_channels", [
        "trend line", "trendline", "channel", "micro channel", "trend channel line",
        "dueling line", "dueling lines", "stairs pattern", "stair pattern",
        "spike and channel", "channel line",
    ]),
    ("breakouts", [
        "breakout", "failed breakout", "breakout pullback", "follow-through",
        "follow through", "spike up", "spike down", "gap up", "gap down",
        "opening gap", "measuring gap", "gap opening", "spike", "gap",
    ]),
    ("climax_reversal", [
        "climax", "exhaustion", "major trend reversal", "consecutive trend bars",
        "parabolic", "spike followed by", "blow off", "blow-off", "climactic",
    ]),
    ("context_regime", [
        "always in", "always-in", "trend day", "trading range", "tight trading range",
        "barbwire", "strong trend", "signs of strength", "signs of weakness",
        "sign of strength", "sign of weakness", "trend strength", "with-trend only",
        "with trend only", "countertrend", "counter-trend", "broad trading range",
        "trendless", "bull trend", "bear trend", "range-bound", "range bound",
    ]),
    ("time_session", [
        "time of day", "opening range", "first hour", "first bar of the day",
        "session", "close of day", "last hour", "premarket", "pre-market",
        "overnight", "yesterday's", "yesterday close", "first 30 minutes",
        "final hour", "lunch hour", "market open", "market close",
    ]),
    ("volume", [
        "volume",
    ]),
    ("trade_management", [
        "scaling in", "scale in", "add on", "adding on", "two reasons",
        "position size", "position sizing", "reentry", "re-entry", "pyramiding",
        "add to a winner", "add to the position",
    ]),
    # Low-priority catch-all for level/magnet concepts (support/resistance,
    # Fibonacci, round numbers, higher-timeframe levels) that are not already
    # claimed by a more specific bucket above (trend lines, channels, swings,
    # breakouts, etc. all take priority since they are more specific).
    ("support_resistance_levels", [
        "support level", "resistance level", "support/resistance", "s/r level",
        "magnet", "fibonacci", "round number", "role flip", "remembered level",
        "remembered support", "remembered resistance", "prior support",
        "prior resistance", "higher time frame", "higher timeframe",
    ]),
    # misc = fallback, not matched by keywords
]

BUCKET_ORDER = [b for b, _ in PRIMARY_BUCKETS] + ["misc"]

# ---------------------------------------------------------------------------
# Sub-split rules, applied only to buckets that end up over TOKEN_BUDGET.
# Each entry: bucket_name -> ordered list of (sub_bucket_suffix, keywords)
# Same word-boundary / name-then-description-then-pseudocode matching.
# Candidates matching none of the sub-rules fall into "<bucket>_other".
# ---------------------------------------------------------------------------
SUB_SPLIT_RULES = {
    "bar_anatomy": [
        ("trend_doji", ["trend bar", "doji", "small bar", "large bar", "big bar",
                         "bull bar", "bear bar", "narrow range bar", "wide range bar",
                         "climactic bar", "body fraction"]),
        ("inside_outside", ["inside bar", "outside bar", "\\bii\\b", "\\biii\\b",
                             "ioi", "oio", "bar overlap", "pause bar"]),
        ("reversal_signal", ["reversal bar", "signal bar", "entry bar", "tail",
                              "close near", "two-bar reversal", "two bar reversal"]),
    ],
    "context_regime": [
        ("always_in", ["always in", "always-in", "with-trend only", "with trend only",
                        "countertrend", "counter-trend"]),
        ("trading_range", ["trading range", "tight trading range", "barbwire",
                            "broad trading range", "trendless", "range-bound",
                            "range bound"]),
        ("trend_strength", ["trend day", "strong trend", "signs of strength",
                             "signs of weakness", "sign of strength", "sign of weakness",
                             "trend strength", "bull trend", "bear trend"]),
    ],
    "breakouts": [
        ("pullback_retest", ["failed breakout", "breakout pullback", "pullback",
                              "retest", "\\btest\\b", "fade", "resume", "resumption"]),
        ("volume_gap", ["volume", "gap"]),
        ("signal_strength", ["follow-through", "follow through", "spike",
                              "significant", "strong", "weak", "body", "strength"]),
    ],
    "lines_channels": [
        ("trendlines", ["trend line", "trendline", "trend line break",
                         "trend line retest"]),
        ("channels", ["channel", "micro channel", "trend channel line", "dueling",
                       "stairs", "spike and channel"]),
    ],
}


def compile_kw(kw: str):
    """Compile a keyword into a word-boundary regex. Keywords may already be
    raw regex fragments (e.g. \\bii\\b) if they start with a backslash.
    A trailing 's?' allows simple plurals ("inside bar" also matches
    "inside bars")."""
    if kw.startswith("\\"):
        return re.compile(kw, re.IGNORECASE)
    return re.compile(r"\b" + re.escape(kw) + r"s?\b", re.IGNORECASE)


def compile_bucket_list(bucket_kw_pairs):
    return [(name, [compile_kw(k) for k in kws]) for name, kws in bucket_kw_pairs]


PRIMARY_COMPILED = compile_bucket_list(PRIMARY_BUCKETS)
SUB_COMPILED = {
    bucket: compile_bucket_list([(s, kws) for s, kws in rules])
    for bucket, rules in SUB_SPLIT_RULES.items()
}


def camel_to_space(s: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1 \2", s or "")
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s1)
    return s2.lower()


def first_match(text: str, compiled_buckets):
    for name, patterns in compiled_buckets:
        for pat in patterns:
            if pat.search(text):
                return name
    return None


def all_matches(text: str, compiled_buckets):
    hits = []
    for name, patterns in compiled_buckets:
        for pat in patterns:
            if pat.search(text):
                hits.append(name)
                break
    return hits


def assign_primary(name_text, desc_text, pseudo_text, compiled_buckets):
    return (
        first_match(name_text, compiled_buckets)
        or first_match(desc_text, compiled_buckets)
        or first_match(pseudo_text, compiled_buckets)
        or "misc"
    )


def approx_tokens_for_obj(obj) -> float:
    return len(json.dumps(obj, ensure_ascii=False)) / CHARS_PER_TOKEN


def load_all_candidates():
    records = []
    seen_ids = {}
    for path in sorted(MINED_DIR.rglob("*.json")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"WARN: failed to parse {rel}: {e}", file=sys.stderr)
            continue
        source = data.get("source", {}) or {}
        book_key = source.get("book_key", "")
        chapter_title = source.get("chapter_title", "")
        for cand in data.get("candidates", []):
            cid = cand.get("id", "")
            enriched = dict(cand)
            enriched["book_key"] = book_key
            enriched["source_file"] = rel
            enriched["chapter_title"] = chapter_title
            records.append(enriched)
            if cid in seen_ids:
                print(f"WARN: duplicate id {cid} in {rel} (first seen in {seen_ids[cid]})",
                      file=sys.stderr)
            else:
                seen_ids[cid] = rel
    return records


STOP_TOKENS = {"a", "an", "the", "of", "in", "on", "at", "to", "is", "and", "or",
               "with", "for", "no", "not"}


def name_tokens_counter(records):
    counters = defaultdict(Counter)
    for r in records:
        bucket = r["_bucket"]
        spaced = camel_to_space(r.get("name", ""))
        for tok in spaced.split():
            if tok in STOP_TOKENS or len(tok) < 2:
                continue
            counters[bucket][tok] += 1
    return counters


def main():
    records = load_all_candidates()
    total = len(records)
    print(f"Loaded {total} candidates from {MINED_DIR}")

    # --- assign primary bucket ---
    for r in records:
        name_text = camel_to_space(r.get("name", ""))
        desc_text = (r.get("description") or "").lower()
        pseudo_text = (r.get("pseudocode") or "").lower()
        r["_search_text"] = f"{name_text} {desc_text} {pseudo_text}"
        r["_bucket"] = assign_primary(name_text, desc_text, pseudo_text, PRIMARY_COMPILED)

    # --- sub-split any bucket over budget ---
    bucket_records = defaultdict(list)
    for r in records:
        bucket_records[r["_bucket"]].append(r)

    final_bucket_of = {}
    top_bucket_of = {}
    split_report = {}
    for bucket, recs in bucket_records.items():
        tokens = sum(approx_tokens_for_obj(r) for r in recs)
        if bucket in SUB_SPLIT_RULES and tokens > TOKEN_BUDGET:
            sub_compiled = SUB_COMPILED[bucket]
            sub_counts = Counter()
            for r in recs:
                name_text = camel_to_space(r.get("name", ""))
                desc_text = (r.get("description") or "").lower()
                pseudo_text = (r.get("pseudocode") or "").lower()
                sub = assign_primary(name_text, desc_text, pseudo_text, sub_compiled)
                if sub == "misc":
                    sub = "other"
                final_name = f"{bucket}_{sub}"
                final_bucket_of[r["id"]] = final_name
                top_bucket_of[r["id"]] = bucket
                sub_counts[final_name] += 1
            split_report[bucket] = dict(sub_counts)
        else:
            for r in recs:
                final_bucket_of[r["id"]] = bucket
                top_bucket_of[r["id"]] = bucket

    for r in records:
        r["_bucket"] = final_bucket_of[r["id"]]
        r["_top_bucket"] = top_bucket_of[r["id"]]

    # --- secondary bucket matches (against combined text, excluding primary
    #     top-level bucket family, using PRIMARY taxonomy only) ---
    secondary_of = {}
    for r in records:
        hits = all_matches(r["_search_text"], PRIMARY_COMPILED)
        primary_top = r["_top_bucket"]
        secondary = [h for h in hits if h != primary_top]
        secondary_of[r["id"]] = secondary

    # --- write index.tsv ---
    MERGE_DIR.mkdir(parents=True, exist_ok=True)
    BUCKETS_DIR.mkdir(parents=True, exist_ok=True)

    index_path = MERGE_DIR / "index.tsv"
    with index_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join([
            "id", "book_key", "source_file", "name", "role", "is_filter",
            "complexity_grade", "timeframe", "likely_existing_rule", "description_160",
        ]) + "\n")
        for r in records:
            desc = (r.get("description") or "").replace("\t", " ").replace("\n", " ")
            desc_trunc = desc[:160]
            complexity = (r.get("complexity") or {}).get("grade", "")
            f.write("\t".join([
                str(r.get("id", "")),
                str(r.get("book_key", "")),
                str(r.get("source_file", "")),
                str(r.get("name", "")).replace("\t", " "),
                str(r.get("role", "")),
                str(r.get("is_filter", "")),
                str(complexity),
                str(r.get("timeframe", "")),
                str(r.get("likely_existing_rule", "")).replace("\t", " "),
                desc_trunc,
            ]) + "\n")

    # --- write secondary.tsv ---
    secondary_path = MERGE_DIR / "secondary.tsv"
    with secondary_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("id\tprimary\tsecondary\n")
        for r in records:
            sec = secondary_of[r["id"]]
            f.write(f"{r['id']}\t{r['_bucket']}\t{','.join(sec)}\n")

    # --- write bucket files ---
    bucket_groups = defaultdict(list)
    for r in records:
        clean = {k: v for k, v in r.items() if not k.startswith("_")}
        bucket_groups[r["_bucket"]].append(clean)

    bucket_stats = []
    for bucket, recs in sorted(bucket_groups.items(), key=lambda kv: -len(kv[1])):
        out_path = BUCKETS_DIR / f"{bucket}.json"
        out_path.write_text(json.dumps(recs, indent=2, ensure_ascii=False), encoding="utf-8")
        tokens = approx_tokens_for_obj(recs)
        bucket_stats.append((bucket, len(recs), tokens))

    # --- SUMMARY.md ---
    name_toks = name_tokens_counter(records)
    misc_count = sum(n for b, n, t in bucket_stats if b == "misc" or b.split("_")[0] == "misc")
    summary_lines = [
        "# Bucket summary\n",
        f"Total candidates: {total}\n",
        f"Misc percentage: {misc_count/total*100:.2f}%\n",
        "| bucket | count | approx tokens | top name tokens |",
        "|---|---|---|---|",
    ]
    for bucket, count, tokens in sorted(bucket_stats, key=lambda x: -x[1]):
        top = ", ".join(t for t, _ in name_toks[bucket].most_common(8))
        summary_lines.append(f"| {bucket} | {count} | {int(tokens)} | {top} |")
    (BUCKETS_DIR / "SUMMARY.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    # --- console report ---
    print("\nBucket sizes:")
    print(f"{'bucket':<28}{'count':>8}{'tokens':>10}")
    for bucket, count, tokens in sorted(bucket_stats, key=lambda x: -x[1]):
        print(f"{bucket:<28}{count:>8}{int(tokens):>10}")

    print(f"\nMisc: {misc_count} / {total} = {misc_count/total*100:.2f}%")
    over_budget = [(b, t) for b, c, t in bucket_stats if t > TOKEN_BUDGET]
    if over_budget:
        print("\nOVER BUDGET buckets (> 45k tokens):")
        for b, t in over_budget:
            print(f"  {b}: {int(t)} tokens")
    else:
        print("\nAll bucket files are within the 45k-token budget.")

    if split_report:
        print("\nSub-split buckets:")
        for bucket, counts in split_report.items():
            print(f"  {bucket} ->")
            for sub, n in sorted(counts.items(), key=lambda kv: -kv[1]):
                print(f"    {sub}: {n}")

    # --- sanity check ---
    total_in_buckets = sum(len(v) for v in bucket_groups.values())
    all_ids = [r["id"] for r in records]
    unique_ids = set(all_ids)
    print(f"\nSanity: total candidates loaded = {total}")
    print(f"Sanity: total candidates written to bucket files = {total_in_buckets}")
    print(f"Sanity: unique ids = {len(unique_ids)} (duplicates: {len(all_ids) - len(unique_ids)})")
    if total_in_buckets != 1635 or len(unique_ids) != len(all_ids) or total != 1635:
        print("SANITY CHECK FAILED", file=sys.stderr)
    else:
        print("SANITY CHECK OK: 1635 candidates, all ids unique, every id in exactly one bucket file.")


if __name__ == "__main__":
    main()
