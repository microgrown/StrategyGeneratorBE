#!/usr/bin/env python3
"""Roll up the Brooks merge pass into a coverage/collision report.

Reads every reference/brooks/merged/<bucket>.json (schema: MERGE.md "Output
file"), cross-checks it against reference/brooks/merge/buckets/<bucket>.json
(the merge agents' inputs) and the full mined corpus
(reference/brooks/mined/**/*.json, schema: MINING.md "Output file"), and
writes:

  - reference/brooks/CANDIDATES.md   human-readable rollup
  - reference/brooks/merge/RULES.tsv one row per merged rule

Checks performed (see README-style docstrings on each run_* function below):
  1. per-bucket coverage: every id in a bucket file appears exactly once
     across that bucket's merged file's rules[].sources / dropped[].id /
     cross_bucket[].id.
  2. corpus-wide coverage: ids in the full mined corpus that are absorbed by
     no merged file at all, and ids that landed in rules in >1 bucket.
  3. cross_bucket reconciliation: did the target bucket's merged file
     actually pick up the stray?
  4. key collisions: the same rule `key` used in two merged files, or a key
     that collides with an existing rules/*.json filename without the
     catalog_match relation being "duplicate".

Usage:
    python reference/brooks/rollup.py [--strict]
        [--merged-dir DIR] [--buckets-dir DIR] [--mined-dir DIR]
        [--rules-dir DIR] [--out-dir DIR]

Defaults are all derived from this script's location (reference/brooks/) and
the repo's rules/ directory. --out-dir controls where CANDIDATES.md and
merge/RULES.tsv are written (default: reference/brooks); point it elsewhere
(e.g. a scratch dir) when testing against fake --merged-dir/--buckets-dir
data so nothing under reference/ is touched.

--strict: exit 1 if any coverage or collision problem was found (id landing
in rules in two buckets is explicitly allowed and never counts). Default:
report and exit 0.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

GRADE_ORDER = {"trivial": 0, "simple": 1, "moderate": 2, "hard": 3, "research": 4}
PRIORITIES = ["A", "B", "C", "D"]


def collect_ids(obj) -> set[str]:
    """Recursively collect every string value of a dict key literally named 'id'."""
    ids: set[str] = set()

    def walk(o):
        if isinstance(o, dict):
            v = o.get("id")
            if isinstance(v, str):
                ids.add(v)
            for val in o.values():
                walk(val)
        elif isinstance(o, list):
            for it in o:
                walk(it)

    walk(obj)
    return ids


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_mined(mined_dir: Path):
    """Return (set of all candidate ids in the corpus, list of (path, error) load failures)."""
    ids: set[str] = set()
    errors: list[tuple[Path, str]] = []
    for path in sorted(mined_dir.rglob("*.json")):
        try:
            data = load_json(path)
        except (json.JSONDecodeError, OSError) as e:
            errors.append((path, str(e)))
            continue
        for c in data.get("candidates", []):
            cid = c.get("id")
            if isinstance(cid, str):
                ids.add(cid)
    return ids, errors


def load_buckets(buckets_dir: Path):
    """Return (dict bucket -> set(ids), list of (path, error) load failures)."""
    buckets: dict[str, set[str]] = {}
    errors: list[tuple[Path, str]] = []
    if not buckets_dir.is_dir():
        return buckets, errors
    for path in sorted(buckets_dir.glob("*.json")):
        try:
            data = load_json(path)
        except (json.JSONDecodeError, OSError) as e:
            errors.append((path, str(e)))
            continue
        buckets[path.stem] = collect_ids(data)
    return buckets, errors


def load_merged(merged_dir: Path):
    """Return (dict bucket -> data, list of (path, error) load failures)."""
    merged: dict[str, dict] = {}
    errors: list[tuple[Path, str]] = []
    if not merged_dir.is_dir():
        return merged, errors
    for path in sorted(merged_dir.glob("*.json")):
        try:
            data = load_json(path)
        except (json.JSONDecodeError, OSError) as e:
            errors.append((path, str(e)))
            continue
        merged[path.stem] = data
    return merged, errors


def rule_sources(rule: dict) -> list[str]:
    return [s for s in rule.get("sources", []) if isinstance(s, str)]


def check_bucket_coverage(buckets: dict[str, set[str]], merged: dict[str, dict]):
    """Check 1: per-bucket coverage against that bucket's own bucket-file ids."""
    report = {}
    for bucket, bucket_ids in buckets.items():
        data = merged.get(bucket)
        if data is None:
            report[bucket] = {
                "no_merged_file": True,
                "missing": sorted(bucket_ids),
                "duplicate": [],
            }
            continue
        counts: Counter[str] = Counter()
        for rule in data.get("rules", []):
            for sid in rule_sources(rule):
                counts[sid] += 1
        for d in data.get("dropped", []):
            did = d.get("id")
            if isinstance(did, str):
                counts[did] += 1
        for x in data.get("cross_bucket", []):
            xid = x.get("id")
            if isinstance(xid, str):
                counts[xid] += 1
        missing = sorted(cid for cid in bucket_ids if counts.get(cid, 0) == 0)
        duplicate = sorted(cid for cid in bucket_ids if counts.get(cid, 0) > 1)
        report[bucket] = {"no_merged_file": False, "missing": missing, "duplicate": duplicate}
    return report


def check_corpus_coverage(mined_ids: set[str], merged: dict[str, dict]):
    """Check 2: corpus-wide coverage + ids landing in rules in >1 bucket."""
    covered: set[str] = set()
    rule_bucket_map: dict[str, list[str]] = defaultdict(list)
    for bucket, data in merged.items():
        for rule in data.get("rules", []):
            for sid in rule_sources(rule):
                covered.add(sid)
                rule_bucket_map[sid].append(bucket)
        for d in data.get("dropped", []):
            did = d.get("id")
            if isinstance(did, str):
                covered.add(did)
        for x in data.get("cross_bucket", []):
            xid = x.get("id")
            if isinstance(xid, str):
                covered.add(xid)
    uncovered = sorted(mined_ids - covered)
    multi_bucket = {cid: sorted(set(bs)) for cid, bs in rule_bucket_map.items() if len(set(bs)) > 1}
    return uncovered, multi_bucket


def check_cross_bucket(merged: dict[str, dict]):
    """Check 3: did the target bucket's merged file actually absorb the stray?"""
    fell_through = []
    for bucket, data in merged.items():
        for x in data.get("cross_bucket", []):
            xid = x.get("id")
            target = x.get("belongs_in")
            if not isinstance(xid, str) or not isinstance(target, str):
                continue
            target_data = merged.get(target)
            if target_data is None:
                fell_through.append(
                    {"id": xid, "from_bucket": bucket, "belongs_in": target, "reason": "target merged file missing"}
                )
                continue
            absorbed = any(xid in rule_sources(r) for r in target_data.get("rules", []))
            if not absorbed:
                fell_through.append(
                    {"id": xid, "from_bucket": bucket, "belongs_in": target, "reason": "not in any rule's sources in target"}
                )
    return fell_through


def check_key_collisions(merged: dict[str, dict], rules_dir: Path):
    """Check 4: same key in two merged files; key collides with an existing rules/*.json name."""
    key_bucket_map: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for bucket, data in merged.items():
        for rule in data.get("rules", []):
            key = rule.get("key")
            if isinstance(key, str):
                key_bucket_map[key].append((bucket, rule))

    cross_file = {k: [b for b, _ in v] for k, v in key_bucket_map.items() if len(v) > 1}

    existing_names = set()
    if rules_dir.is_dir():
        for p in rules_dir.glob("*.json"):
            existing_names.add(p.stem.lower())

    catalog_collisions = []
    for key, entries in key_bucket_map.items():
        if key.lower() not in existing_names:
            continue
        for bucket, rule in entries:
            relation = (rule.get("catalog_match") or {}).get("relation", "")
            if relation != "duplicate":
                catalog_collisions.append({"key": key, "bucket": bucket, "relation": relation or "(none given)"})

    return cross_file, catalog_collisions


def md_escape(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ").strip()


def truncate(s: str, n: int = 140) -> str:
    s = s or ""
    return s if len(s) <= n else s[: n - 1].rstrip() + "\u2026"


def build_rule_rows(merged: dict[str, dict]):
    rows = []
    for bucket, data in merged.items():
        for rule in data.get("rules", []):
            rows.append({**rule, "_bucket": bucket})
    return rows


def sort_key(rule):
    grade = (rule.get("complexity") or {}).get("grade", "")
    return (GRADE_ORDER.get(grade, 99), -len(rule_sources(rule)))


def write_candidates_md(
    out_path: Path,
    mined_ids,
    mined_errors,
    buckets,
    bucket_errors,
    merged,
    merged_errors,
    bucket_coverage,
    uncovered,
    multi_bucket,
    fell_through,
    cross_file_collisions,
    catalog_collisions,
    rows,
):
    lines = []
    lines.append("# Brooks candidate merge rollup")
    lines.append("")
    lines.append(f"Candidates in corpus (mined): **{len(mined_ids)}**")
    lines.append(f"Merged files loaded: **{len(merged)}** (buckets: {', '.join(sorted(merged)) or '(none)'})")
    if merged_errors:
        lines.append(f"Merged files that FAILED to parse ({len(merged_errors)}):")
        for p, e in merged_errors:
            lines.append(f"  - `{p}`: {e}")
    if bucket_errors:
        lines.append(f"Bucket files that FAILED to parse ({len(bucket_errors)}):")
        for p, e in bucket_errors:
            lines.append(f"  - `{p}`: {e}")
    if mined_errors:
        lines.append(f"Mined files that FAILED to parse ({len(mined_errors)}):")
        for p, e in mined_errors:
            lines.append(f"  - `{p}`: {e}")

    priority_counts = Counter(r.get("priority", "?") for r in rows)
    dropped_count = sum(len(d.get("dropped", [])) for d in merged.values())

    lines.append(f"Rules out: **{len(rows)}**  ({', '.join(f'{p}={priority_counts.get(p, 0)}' for p in PRIORITIES)})")
    lines.append(f"Dropped: **{dropped_count}**")
    lines.append("")
    lines.append("## Coverage result")
    lines.append("")
    any_bucket_problem = any(v["missing"] or v["duplicate"] or v["no_merged_file"] for v in bucket_coverage.values())
    lines.append(f"- Per-bucket coverage clean: **{'no' if any_bucket_problem else 'yes'}**")
    for bucket, v in sorted(bucket_coverage.items()):
        if v["no_merged_file"]:
            lines.append(f"  - `{bucket}`: NO MERGED FILE (all {len(v['missing'])} bucket ids uncovered)")
            continue
        if v["missing"] or v["duplicate"]:
            lines.append(
                f"  - `{bucket}`: missing={len(v['missing'])} {v['missing']}, "
                f"duplicate-in-bucket={len(v['duplicate'])} {v['duplicate']}"
            )
    lines.append(f"- Corpus-wide ids covered by no merged file at all: **{len(uncovered)}**")
    if uncovered:
        lines.append(f"  - {uncovered}")
    lines.append(f"- Ids landing in rules in more than one bucket (allowed, reconcile): **{len(multi_bucket)}**")
    for cid, bs in sorted(multi_bucket.items()):
        lines.append(f"  - `{cid}`: {bs}")
    lines.append(f"- Cross-bucket strays that fell through the cracks: **{len(fell_through)}**")
    for f in fell_through:
        lines.append(f"  - `{f['id']}` from `{f['from_bucket']}` -> `{f['belongs_in']}`: {f['reason']}")
    lines.append(f"- Rule keys colliding across merged files: **{len(cross_file_collisions)}**")
    for k, bs in sorted(cross_file_collisions.items()):
        lines.append(f"  - `{k}`: {bs}")
    lines.append(f"- Rule keys colliding with an existing rules/*.json name (non-duplicate relation): **{len(catalog_collisions)}**")
    for c in catalog_collisions:
        lines.append(f"  - `{c['key']}` (bucket `{c['bucket']}`, relation `{c['relation']}`)")
    lines.append("")

    lines.append("## Rules by priority")
    for p in PRIORITIES:
        p_rows = sorted((r for r in rows if r.get("priority") == p), key=sort_key)
        lines.append("")
        lines.append(f"### Priority {p} ({len(p_rows)})")
        if not p_rows:
            lines.append("")
            lines.append("_none_")
            continue
        lines.append("")
        lines.append("| key | role | sides | complexity | timeframe | sources | catalog_match | bucket | description |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for r in p_rows:
            cm = r.get("catalog_match") or {}
            cm_rule = cm.get("rule") or "\u2014"
            cm_str = f"{cm_rule} ({cm.get('relation', 'none')})"
            grade = (r.get("complexity") or {}).get("grade", "")
            lines.append(
                "| `{key}` | {role} | {sides} | {grade} | {tf} | {n} | {cm} | {bucket} | {desc} |".format(
                    key=md_escape(r.get("key", "")),
                    role=md_escape(r.get("role", "")),
                    sides=md_escape(r.get("sides", "")),
                    grade=md_escape(grade),
                    tf=md_escape(r.get("timeframe", "")),
                    n=len(rule_sources(r)),
                    cm=md_escape(cm_str),
                    bucket=md_escape(r.get("_bucket", "")),
                    desc=md_escape(truncate(r.get("description", ""))),
                )
            )

    lines.append("")
    lines.append("## Design decisions")
    lines.append("")
    topics: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for bucket, data in merged.items():
        for dd in data.get("design_decisions", []):
            topic = dd.get("topic", "(untitled)")
            topics[topic.strip().lower()].append((bucket, dd))
    if not topics:
        lines.append("_none raised yet_")
    for topic_key in sorted(topics):
        entries = topics[topic_key]
        display_topic = entries[0][1].get("topic", topic_key)
        lines.append(f"### {display_topic}")
        for bucket, dd in entries:
            lines.append(f"- **{bucket}**: options={dd.get('options', [])}; recommended: {dd.get('recommended', '')}; gates: {dd.get('gates', [])}")
        lines.append("")

    lines.append("## EL words needed (priority A + B rules)")
    lines.append("")
    el_counter: Counter[str] = Counter()
    for r in rows:
        if r.get("priority") in ("A", "B"):
            for w in r.get("el_words_needed", []):
                el_counter[w] += 1
    if not el_counter:
        lines.append("_none_")
    else:
        lines.append("| EL word | rules needing it |")
        lines.append("|---|---|")
        for w, n in sorted(el_counter.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"| `{w}` | {n} |")

    lines.append("")
    lines.append("## Dropped")
    lines.append("")
    any_dropped = False
    for bucket in sorted(merged):
        dropped = merged[bucket].get("dropped", [])
        if not dropped:
            continue
        any_dropped = True
        lines.append(f"### {bucket}")
        for d in sorted(dropped, key=lambda d: d.get("id", "")):
            lines.append(f"- `{d.get('id', '?')}`: {md_escape(d.get('reason', ''))}")
        lines.append("")
    if not any_dropped:
        lines.append("_none_")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_rules_tsv(out_path: Path, rows):
    lines = ["key\tbucket\tpriority\trole\tcomplexity\tsources"]
    for r in sorted(rows, key=lambda r: (r.get("_bucket", ""), r.get("key", ""))):
        grade = (r.get("complexity") or {}).get("grade", "")
        lines.append(
            "\t".join(
                [
                    r.get("key", ""),
                    r.get("_bucket", ""),
                    r.get("priority", ""),
                    r.get("role", ""),
                    grade,
                    ",".join(rule_sources(r)),
                ]
            )
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    script_dir = Path(__file__).resolve().parent  # reference/brooks
    repo_root = script_dir.parent.parent

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--merged-dir", type=Path, default=script_dir / "merged")
    ap.add_argument("--buckets-dir", type=Path, default=script_dir / "merge" / "buckets")
    ap.add_argument("--mined-dir", type=Path, default=script_dir / "mined")
    ap.add_argument("--rules-dir", type=Path, default=repo_root / "rules")
    ap.add_argument("--out-dir", type=Path, default=script_dir)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    mined_ids, mined_errors = load_mined(args.mined_dir)
    buckets, bucket_errors = load_buckets(args.buckets_dir)
    merged, merged_errors = load_merged(args.merged_dir)

    bucket_coverage = check_bucket_coverage(buckets, merged)
    uncovered, multi_bucket = check_corpus_coverage(mined_ids, merged)
    fell_through = check_cross_bucket(merged)
    cross_file_collisions, catalog_collisions = check_key_collisions(merged, args.rules_dir)
    rows = build_rule_rows(merged)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "merge").mkdir(parents=True, exist_ok=True)
    write_candidates_md(args.out_dir / "CANDIDATES.md", mined_ids, mined_errors, buckets, bucket_errors,
                         merged, merged_errors, bucket_coverage, uncovered, multi_bucket, fell_through,
                         cross_file_collisions, catalog_collisions, rows)
    write_rules_tsv(args.out_dir / "merge" / "RULES.tsv", rows)

    print(f"Loaded {len(mined_ids)} mined candidate ids ({len(mined_errors)} mined files failed to parse)")
    print(f"Loaded {len(buckets)} bucket files ({len(bucket_errors)} failed to parse)")
    print(f"Loaded {len(merged)} merged files ({len(merged_errors)} failed to parse)")
    print(f"Rules out: {len(rows)}")
    print(f"Wrote {args.out_dir / 'CANDIDATES.md'}")
    print(f"Wrote {args.out_dir / 'merge' / 'RULES.tsv'}")

    problems = 0
    for bucket, v in bucket_coverage.items():
        if v["no_merged_file"]:
            print(f"PROBLEM: bucket '{bucket}' has no merged file ({len(v['missing'])} ids uncovered)")
            problems += 1
        if v["missing"]:
            print(f"PROBLEM: bucket '{bucket}' missing ids: {v['missing']}")
            problems += 1
        if v["duplicate"]:
            print(f"PROBLEM: bucket '{bucket}' duplicate ids: {v['duplicate']}")
            problems += 1
    if uncovered:
        print(f"PROBLEM: {len(uncovered)} corpus ids covered by no merged file: {uncovered}")
        problems += 1
    if multi_bucket:
        print(f"INFO: {len(multi_bucket)} ids landed in rules in >1 bucket (allowed): {multi_bucket}")
    if fell_through:
        print(f"PROBLEM: {len(fell_through)} cross_bucket strays fell through the cracks: {fell_through}")
        problems += 1
    if cross_file_collisions:
        print(f"PROBLEM: {len(cross_file_collisions)} rule keys collide across merged files: {cross_file_collisions}")
        problems += 1
    if catalog_collisions:
        print(f"PROBLEM: {len(catalog_collisions)} rule keys collide with existing rules/*.json names: {catalog_collisions}")
        problems += 1
    if merged_errors or bucket_errors:
        print(f"PROBLEM: {len(merged_errors) + len(bucket_errors)} bucket/merged files failed to parse")
        problems += 1

    if args.strict and problems:
        print(f"--strict: {problems} problem categories found, exiting 1")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
