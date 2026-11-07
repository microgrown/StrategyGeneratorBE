#!/usr/bin/env python3
"""Bucketize the 1635 mined Brooks candidates into topic files small enough
for one dedup agent to read (<= ~45k tokens each, tokens ~= chars/4).

Usage: python reference/grimes/bucketize.py
Writes:
  reference/grimes/merge/index.tsv
  reference/grimes/merge/secondary.tsv
  reference/grimes/merge/buckets/<bucket>.json
  reference/grimes/merge/buckets/SUMMARY.md
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MINED_DIR = REPO_ROOT / "reference" / "grimes" / "mined"
MERGE_DIR = REPO_ROOT / "reference" / "grimes" / "merge"
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
        "trail", "tighten", "initial stop", "stop at", "stop above", "stop below",
        "stop beyond", "stop inside", "stop distance", "stop placement", "move the stop",
        "hard stop", "time stop", "chandelier", "parabolic sar", "\bsar\b",
        "stopped out", "stop-out", "stop out", "widen the stop", "stop widening",
        "gap through", "gap against", "gap down through", "windfall",
    ]),
    ("exits_targets", [
        "profit target", "take profit", "target", "objective", "reward",
        "risk multiple", "multiple of risk", "\b1r\b", "\b2r\b", "\b3r\b", "times risk",
        "scale out", "partial profit", "partial exit", "first target", "second target",
        "measured move", "exit when", "exit if", "exit on", "exit the", "exit after",
        "flat after", "flatten",
    ]),
    ("indicators_bands", [
        "keltner", "band", "free bar", "channel", "macd", "3/10", "3-10", "oscillator",
        "fast line", "slow line", "signal line", "hook", "efficiency ratio", "kaufman",
        "standard deviation", "stddev", "bollinger", "stochastic", "typical price",
        "ema slope", "moving average slope", "distance from the ema", "distance above",
        "distance below", "atr multiple", "ema", "moving average", "xaverage",
    ]),
    ("pullbacks_continuation", [
        "pullback", "pull back", "anti", "abcd", "nested", "complex", "retracement",
        "first pullback", "second pullback", "continuation", "with-trend", "with trend",
        "consolidation in a trend", "flag", "resume", "resumption", "leg ratio",
        "successive legs", "trend leg", "impulse",
    ]),
    ("climax_termination", [
        "climax", "exhaustion", "parabolic", "termination", "terminat", "divergence",
        "three pushes", "three push", "3 push", "three-push", "blow off", "blow-off",
        "overextended", "overextension", "too far", "change of character", "last gasp",
        "loss of momentum", "momentum loss", "shrinking", "acceleration", "accelerat",
    ]),
    ("breakouts", [
        "breakout", "break out", "failed breakout", "follow-through", "follow through",
        "breakdown", "break down", "expansion", "range expansion", "opening range",
        "gap up", "gap down", "\bgap\b",
    ]),
    ("ranges_levels_tests", [
        "trading range", "range", "support", "resistance", "level", "spring", "upthrust",
        "failure test", "fakeout", "shakeout", "test of", "retest", "\btest\b",
        "accumulation", "distribution", "boundary", "consolidation", "confluence",
        "double top", "double bottom", "holding", "hold the", "held",
    ]),
    ("swing_structure", [
        "swing high", "swing low", "higher high", "lower low", "higher low", "lower high",
        "pivot", "swing point", "swing", "zigzag", "zig zag", "trend line", "trendline",
        "second-order", "second order", "first-order", "first order", "structure",
    ]),
    ("bar_anatomy", [
        "wide range bar", "wide-range bar", "narrow range bar", "narrow-range bar",
        "inside bar", "outside bar", "large bar", "small bar", "big bar", "range bar",
        "close near", "close at", "closes at", "close in the", "bar close location",
        "body", "tail", "wick", "consecutive closes", "consecutive bars", "consecutive",
        "engulfing", "reversal bar", "two-bar", "two bar", "single bar", "bar range",
        "bar's range",
    ]),
    ("context_regime", [
        "uptrend", "downtrend", "trend", "market cycle", "phase", "markup", "markdown",
        "higher time frame", "higher timeframe", "lower time frame", "lower timeframe",
        "multiple time frame", "regime", "environment", "context", "session", "time of day",
        "day of week", "daily loss", "loss limit", "trade count", "trades per",
        "drawdown", "equity",
    ]),
    ("trade_management", [
        "add on", "add-on", "adding on", "pyramid", "scale in", "scaling in", "re-entry",
        "reentry", "re-enter", "reenter", "position size", "position sizing",
        "add to", "second unit", "remaining position", "runner",
    ]),
    # misc = fallback, not matched by keywords
]

BUCKET_ORDER = [b for b, _ in PRIMARY_BUCKETS] + ["misc"]

SUB_SPLIT_RULES = {
    "exits_stops": [
        ("trailing", ["trail", "chandelier", "parabolic", "sar", "tighten", "breakeven",
                      "break even", "move the stop", "raise the stop", "lower the stop"]),
        ("initial_time", ["initial stop", "stop placement", "stop distance", "time stop",
                          "stop beyond", "stop inside", "stop above", "stop below", "gap",
                          "windfall", "widen"]),
    ],
    "indicators_bands": [
        ("keltner", ["keltner", "band", "free bar", "channel", "typical price", "bollinger",
                     "standard deviation", "stddev"]),
        ("macd_momentum", ["macd", "3/10", "3-10", "oscillator", "fast line", "slow line",
                           "signal line", "hook", "stochastic", "efficiency ratio", "kaufman"]),
        ("ema", ["ema", "moving average", "xaverage", "slope", "distance"]),
    ],
    "ranges_levels_tests": [
        ("failure_tests", ["spring", "upthrust", "failure test", "fakeout", "shakeout",
                           "test of", "retest", "\btest\b", "penetrat", "probe"]),
        ("range_structure", ["trading range", "range", "accumulation", "distribution",
                             "boundary", "consolidation", "double top", "double bottom"]),
        ("levels", ["support", "resistance", "level", "confluence"]),
    ],
    "pullbacks_continuation": [
        ("anti_complex", ["anti", "abcd", "nested", "complex", "two-legged", "two legged"]),
        ("simple", ["pullback", "pull back", "retracement", "first pullback", "flag",
                    "resume", "resumption", "continuation", "impulse", "leg"]),
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
    if total_in_buckets != total or len(unique_ids) != len(all_ids):
        print("SANITY CHECK FAILED", file=sys.stderr)
    else:
        print(f"SANITY CHECK OK: {total} candidates, all ids unique, every id in exactly one bucket file.")


if __name__ == "__main__":
    main()
