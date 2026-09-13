"""Validate and summarize reference/brooks/mined/**/*.json."""
import json, glob, os, sys
from collections import Counter

root = os.path.join(os.path.dirname(__file__), "mined")
books = {"trends": 34, "ranges": 41, "reversals": 33}  # text files incl. non-mined back matter (3 each)
tot = Counter(); role = Counter(); cx = Counter(); tf = Counter(); bad = []
per_book = {}
for book in books:
    files = sorted(glob.glob(os.path.join(root, book, "*.json")))
    c = Counter()
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            bad.append((f, str(e))); continue
        cands = d.get("candidates", [])
        c["files"] += 1; c["cands"] += len(cands); c["rej"] += len(d.get("rejected", []))
        for k in cands:
            role[k.get("role", "?")] += 1
            cx[(k.get("complexity") or {}).get("grade", "?")] += 1
            tf[k.get("timeframe", "?")] += 1
            if not k.get("pseudocode"): c["no_pseudocode"] += 1
            if not k.get("pages"): c["no_pages"] += 1
    per_book[book] = c
    tot.update(c)

print(f"{'book':<10}{'files':>6}{'/expected':>10}{'cands':>7}{'rej':>6}{'noPseudo':>10}{'noPages':>9}")
for b, c in per_book.items():
    print(f"{b:<10}{c['files']:>6}{books[b]-3:>10}{c['cands']:>7}{c['rej']:>6}{c['no_pseudocode']:>10}{c['no_pages']:>9}")
print(f"{'total':<10}{tot['files']:>6}{sum(books.values())-9:>10}{tot['cands']:>7}{tot['rej']:>6}")
print("\nrole:", dict(role)); print("complexity:", dict(cx)); print("timeframe:", dict(tf))
if bad:
    print("\nBAD FILES:"); [print(" ", f, e) for f, e in bad]; sys.exit(1)
