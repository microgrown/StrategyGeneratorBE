"""Apply an authoring agent's rows file to rules/CATALOG.md.

New rows (keys not yet in the catalog) are appended. Rows under a `## Amended` heading
replace the existing catalog line for that key in place. Bold is stripped.

    python reference/grimes/applyRows.py reference/grimes/author/rows/NN_<family>.md
"""
import re
import sys

text = open(sys.argv[1], encoding="utf-8").read()
new_rows, amended = [], []
section = "new"
for line in text.splitlines():
    if line.startswith("## "):
        low = line.lower()
        # only the main rows table (a heading mentioning "rows") and "## Amended" are applied;
        # any other section (Not written, depends_on_keys, notes, catalog re-checks) is skipped
        section = "amended" if "amend" in low else ("new" if "rows" in low and "not" not in low else "skip")
        continue
    if line.startswith("| `"):
        line = line.replace("**", "")
        (amended if section == "amended" else new_rows if section == "new" else []).append(line)

cat_path = "rules/CATALOG.md"
cat = open(cat_path, encoding="utf-8").read().rstrip("\n")
have = set(re.findall(r"^\| `(\w+)`", cat, re.M))

appended = 0
for l in new_rows:
    k = re.match(r"^\| `(\w+)`", l).group(1)
    if k in have:
        print(f"  skip {k}: already in catalog (use ## Amended to replace)")
        continue
    cat += "\n" + l
    have.add(k)
    appended += 1

replaced = 0
for l in amended:
    k = re.match(r"^\| `(\w+)`", l).group(1)
    pat = re.compile(rf"^\| `{k}` \|.*$", re.M)
    if not pat.search(cat):
        print(f"  amended row for {k} has no existing catalog line; appending instead")
        cat += "\n" + l
        continue
    cat = pat.sub(lambda m: l, cat, count=1)
    replaced += 1

open(cat_path, "w", encoding="utf-8").write(cat + "\n")
print(f"{sys.argv[1]}: appended {appended} new rows, replaced {replaced} amended rows")
