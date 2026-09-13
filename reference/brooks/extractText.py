#!/usr/bin/env python
"""Extract the three Al Brooks "Trading Price Action" PDFs to per-chapter text files.

Output: reference/brooks/text/<trends|ranges|reversals>/NN_<slug>.txt (git-ignored)
        reference/brooks/MANIFEST.json and MANIFEST.md

Chapter boundaries come from the PDF outline when one exists (Trends, Reversals);
otherwise from "Chapter N" / "Part N" heading lines at the top of pages, with
titles taken from the printed table of contents (Ranges).

Numbering: 00 = front matter (contents, acknowledgments, list of terms, introduction);
01..N = chapters; part introductions are written as "NN-part_<roman>_<slug>.txt"
where NN is the first chapter of the part (sorts just before that chapter);
About the Author / About the Website / Index follow as trailing chapters N+1..

Page markers "[[page P]]" use 1-based PDF page numbers (what a PDF viewer shows),
not the printed folio.

Cleanup is light: printer slug lines, running heads, bare folio lines are removed;
ligatures (fi, fl, ...) are unfolded; drop-cap letters are rejoined to their word;
runs of blank lines are collapsed. Body text is not rewrapped.

Usage: python extractText.py [--pdf-dir DIR] [--out DIR] [--only trends,ranges]
"""
import argparse
import json
import logging
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

logging.getLogger("pypdf").setLevel(logging.ERROR)
from pypdf import PdfReader  # noqa: E402

HERE = Path(__file__).resolve().parent
DEFAULT_PDF_DIR = Path("C:/Users/brian/Downloads")

BOOKS = [
    {
        "key": "trends",
        "title": "Trading Price Action Trends",
        "pdf": "Al-Brooks-Trading-Price-Action-Trends-(KohanFx.com).pdf",
    },
    {
        "key": "ranges",
        "title": "Trading Price Action Trading Ranges",
        "pdf": "Al-Brooks-Trading-Price-Action-Ranges-(KohanFx.com).pdf",
    },
    {
        "key": "reversals",
        "title": "Trading Price Action Reversals",
        "pdf": "Al-Brooks-Trading-Price-Action-Reversals-(KohanFx.com).pdf",
    },
]

FRONT_TITLES = ("contents", "acknowledgments", "list of terms", "introduction",
                "cover", "series", "title page", "copyright", "dedication")
BACK_TITLES = ("about the author", "about the website", "index", "glossary", "appendix")

LIGATURES = {"\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl",
             "\ufb05": "st", "\ufb06": "st"}

# ---------------------------------------------------------------- helpers


def slugify(title, maxlen=48):
    t = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_").lower()
    if len(t) > maxlen:
        t = t[:maxlen].rsplit("_", 1)[0]
    return t or "untitled"


def norm_title(t):
    t = t.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", t).strip()


def roman_to_int(s):
    vals = {"I": 1, "V": 5, "X": 10, "L": 50}
    total = 0
    for i, c in enumerate(s):
        v = vals[c]
        if i + 1 < len(s) and vals[s[i + 1]] > v:
            total -= v
        else:
            total += v
    return total


def int_to_roman(n):
    out = ""
    for v, r in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out += r
            n -= v
    return out


# ---------------------------------------------------------------- boundary detection
# A "mark" is (kind, number, title, start_page0) with kind in {front, part, chapter, back}.

CHAPTER_RE = re.compile(r"^(CHAPTER|Chapter)\s+(\d+)\s*[:.]?\s*(.*)$")
PART_RE = re.compile(r"^(PART|Part)\s+([IVXL]+|\d+)\s*[:.]?\s*(.*)$")


def part_num(s):
    return int(s) if s.isdigit() else roman_to_int(s)


def marks_from_outline(reader):
    flat = []

    def walk(items, depth):
        for it in items:
            if isinstance(it, list):
                walk(it, depth + 1)
            else:
                try:
                    p = reader.get_destination_page_number(it)
                except Exception:
                    p = None
                if p is not None:
                    flat.append((depth, norm_title(it.title), p))

    walk(reader.outline, 0)
    if not flat:
        return None
    marks = []
    for depth, title, p in flat:
        m = CHAPTER_RE.match(title)
        if m:
            marks.append(("chapter", int(m.group(2)), m.group(3).strip(), p))
            continue
        m = PART_RE.match(title)
        if m:
            marks.append(("part", part_num(m.group(2)), m.group(3).strip(), p))
            continue
        low = title.lower()
        if low.startswith(BACK_TITLES):
            marks.append(("back", None, title, p))
        elif low.startswith(FRONT_TITLES):
            marks.append(("front", None, title, p))
        # anything else (the root "book title" entry) is ignored
    return marks


def toc_titles(reader, max_pages=12):
    """Parse 'Chapter N: Title' / 'Part N: Title' lines from the printed contents pages."""
    chapters, parts = {}, {}
    last = None
    started = False
    for i in range(min(max_pages, len(reader.pages))):
        text = reader.pages[i].extract_text() or ""
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.lower() == "contents":
                started = True
                continue
            if not started:
                continue
            m = CHAPTER_RE.match(line)
            if m:
                chapters[int(m.group(2))] = m.group(3).strip()
                last = ("c", int(m.group(2)))
                continue
            m = PART_RE.match(line)
            if m:
                parts[part_num(m.group(2))] = m.group(3).strip()
                last = ("p", part_num(m.group(2)))
                continue
            if line.lower().startswith(BACK_TITLES):
                if line.lower() == "index":
                    started = False
                last = None
                continue
            # continuation of a wrapped title: not an all-caps sub-heading, not a bare number
            if last and not line.isupper() and not re.fullmatch(r"[\divx]+", line.lower()):
                d = chapters if last[0] == "c" else parts
                d[last[1]] = (d[last[1]] + " " + line).strip()
    return chapters, parts


def marks_from_headings(reader):
    ch_titles, part_titles = toc_titles(reader)
    marks = []
    toc_done = False
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            continue
        first = lines[0]
        nxt = lines[1] if len(lines) > 1 else ""
        # skip TOC pages: several chapter/part/back-matter entries at line starts on one page
        toc_like = sum(1 for l in lines
                       if CHAPTER_RE.match(l) or PART_RE.match(l) or l.lower().startswith(BACK_TITLES))
        if toc_like >= 3 and (CHAPTER_RE.match(first) or PART_RE.match(first)):
            continue
        m = CHAPTER_RE.match(first)
        if m and (m.group(3) or nxt):
            n = int(m.group(2))
            title = ch_titles.get(n) or m.group(3).strip() or nxt
            marks.append(("chapter", n, title, i))
            toc_done = True
            continue
        m = PART_RE.match(first)
        if m:
            num = part_num(m.group(2))
            title = part_titles.get(num) or m.group(3).strip() or nxt
            marks.append(("part", num, title, i))
            toc_done = True
            continue
        low = first.lower()
        if toc_done and low.startswith(BACK_TITLES) and len(first) < 40:
            marks.append(("back", None, first, i))
        elif not toc_done and low.startswith(FRONT_TITLES) and len(first) < 40 and len(lines) > 1:
            marks.append(("front", None, first, i))
    return marks


def build_sections(marks, n_pages):
    """Turn marks into ordered sections with page ranges. Returns list of dicts."""
    marks = sorted(marks, key=lambda m: m[3])
    first_body = next((m for m in marks if m[0] in ("part", "chapter")), None)
    if first_body is None:
        raise RuntimeError("no chapter marks found")
    front_end = first_body[3]  # exclusive
    front_items = [m[2] for m in marks if m[0] == "front" and m[3] < front_end]
    body = [m for m in marks if m[0] in ("part", "chapter") and m[3] >= front_end]
    back = [m for m in marks if m[0] == "back" and m[3] >= front_end]
    seen = set()
    dedup = []
    for m in body:  # keep the first occurrence of each chapter/part number
        k = (m[0], m[1])
        if k in seen:
            continue
        seen.add(k)
        dedup.append(m)
    body = dedup
    max_ch = max(m[1] for m in body if m[0] == "chapter")

    sections = [{"chapter": "00", "title": "Front Matter and Introduction",
                 "contains": front_items, "file": "00_front_matter.txt",
                 "start": 0, "kind": "front"}]
    for idx, m in enumerate(body):
        kind, num, title, p = m
        if kind == "chapter":
            sections.append({"chapter": f"{num:02d}", "title": title,
                             "file": f"{num:02d}_{slugify(title)}.txt", "start": p, "kind": "chapter"})
        else:
            nxt = next((mm[1] for mm in body[idx + 1:] if mm[0] == "chapter"), max_ch + 1)
            roman = int_to_roman(num)
            sections.append({"chapter": f"P{num}", "title": f"Part {roman}: {title}",
                             "file": f"{nxt:02d}-part_{roman.lower()}_{slugify(title)}.txt",
                             "start": p, "kind": "part"})
    n = max_ch
    for m in back:
        n += 1
        sections.append({"chapter": f"{n:02d}", "title": m[2],
                         "file": f"{n:02d}_{slugify(m[2])}.txt", "start": m[3], "kind": "back"})
    sections.sort(key=lambda s: s["start"])
    for i, s in enumerate(sections):
        s["end"] = (sections[i + 1]["start"] - 1) if i + 1 < len(sections) else n_pages - 1
    return sections


# ---------------------------------------------------------------- page cleanup

SLUG_RE = re.compile(r"^\s*(P1:\s*OTA|JWBT\d+-)")
CAPS = r"[A-Z0-9][A-Z0-9 ,:;'\u2019\-\u2013\u2014()/&.?!]*"
HEAD_RE = re.compile(
    r"^\s*(?:Figure\s*\d+\.\d+[A-Z]?\s+)?(?:\d{1,3}\s+" + CAPS + r"|" + CAPS + r"\s+\d{1,3})"
    r"(?:\s+Figure\s*\d+\.\d+[A-Z]?)?\s*$")
HEAD_EXCLUDE_RE = re.compile(r"^\s*(CHAPTER|PART|FIGURE)\b")
FOLIO_RE = re.compile(r"^\s*\d{1,3}\s*$")
DROPCAP_RE = re.compile(r"^[A-Z]$")


def unfold_ligatures(t):
    for k, v in LIGATURES.items():
        t = t.replace(k, v)
    return t


def clean_page(text, typeset):
    """typeset: 'wiley' (Trends/Reversals print layout) or 'reflow' (Ranges)."""
    text = unfold_ligatures(text).replace("\r", "")
    lines = [l.rstrip() for l in text.split("\n")]
    if typeset == "wiley":
        # printer slug lines (first two lines of every page)
        while lines and (not lines[0].strip() or SLUG_RE.match(lines[0])):
            lines.pop(0)
        # running head: first line of the page, "N TITLE" or "TITLE N" (optionally with Figure x.y)
        if lines and HEAD_RE.match(lines[0]) and not HEAD_EXCLUDE_RE.match(lines[0]):
            lines.pop(0)
        # folio at page bottom (chapter openers and index pages)
        while lines and not lines[-1].strip():
            lines.pop()
        if lines and FOLIO_RE.match(lines[-1]):
            lines.pop()
        # drop cap: single capital letter on its own line followed by the rest of the word
        out = []
        i = 0
        while i < len(lines):
            l = lines[i]
            if DROPCAP_RE.match(l.strip()) and i + 1 < len(lines) and re.match(r"^[a-z]", lines[i + 1]):
                out.append(l.strip() + lines[i + 1])
                i += 2
                continue
            out.append(l)
            i += 1
        lines = out
    # collapse blank runs
    out = []
    blank = False
    for l in lines:
        if l.strip():
            out.append(l)
            blank = False
        elif not blank:
            out.append("")
            blank = True
    while out and not out[0]:
        out.pop(0)
    while out and not out[-1]:
        out.pop()
    return "\n".join(out)


# ---------------------------------------------------------------- main


def process_book(book, pdf_dir, out_root):
    reader = PdfReader(str(pdf_dir / book["pdf"]), strict=False)
    n_pages = len(reader.pages)
    marks = marks_from_outline(reader)
    if marks and sum(1 for m in marks if m[0] == "chapter") >= 3:
        method = "outline"
    else:
        marks = marks_from_headings(reader)
        method = "headings"
    sections = build_sections(marks, n_pages)

    # typeset detection: the Wiley print PDFs carry "JWBT" printer slugs on every page
    sample = "".join((reader.pages[i].extract_text() or "") for i in range(min(40, n_pages)))
    typeset = "wiley" if "JWBT" in sample else "reflow"

    out_dir = out_root / book["key"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.txt"):
        old.unlink()

    manifest = []
    print(f"\n== {book['title']} ({book['pdf']}) pages={n_pages} method={method} typeset={typeset}")
    for s in sections:
        a, b = s["start"], s["end"]
        parts = [f"# {book['title']} \u2014 Chapter {s['chapter']}: {s['title']} (PDF pages {a + 1}\u2013{b + 1})", ""]
        for i in range(a, b + 1):
            t = clean_page(reader.pages[i].extract_text() or "", typeset)
            if not t:
                continue
            parts.append(f"[[page {i + 1}]]")
            parts.append(t)
            parts.append("")
        body = "\n".join(parts).rstrip() + "\n"
        path = out_dir / s["file"]
        path.write_text(body, encoding="utf-8")
        chars = len(body)
        entry = {"chapter": s["chapter"], "title": s["title"], "file": f"text/{book['key']}/{s['file']}",
                 "pdf_pages": [a + 1, b + 1], "chars": chars, "approx_tokens": chars // 4}
        if s.get("contains"):
            entry["contains"] = s["contains"]
        manifest.append(entry)
        first_line = ""
        for line in body.splitlines()[2:]:
            if line.strip() and not line.startswith("[[page"):
                first_line = line.strip()
                break
        flag = " <-- EMPTY" if chars < 200 else ""
        print(f"  {s['chapter']:>3} p{a + 1:>3}-{b + 1:<3} {chars:>7}c  {s['file'][:44]:<44} | {first_line[:60]}{flag}")
    total = sum(e["chars"] for e in manifest)
    print(f"  total chars={total} approx_tokens={total // 4} sections={len(manifest)}")
    return {"title": book["title"], "pdf": book["pdf"], "pdf_pages": n_pages, "boundary_method": method,
            "typeset": typeset, "total_chars": total, "total_approx_tokens": total // 4,
            "chapters": manifest}


def write_manifests(result, brooks_dir):
    (brooks_dir / "MANIFEST.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                                              encoding="utf-8")
    md = ["# Brooks text extraction manifest", "",
          f"Generated {result['generated']} by `extractText.py`. Files live under `reference/brooks/text/` "
          "(git-ignored; regenerate with the script). `[[page P]]` markers and the PDF pages column are "
          "1-based PDF page numbers, not printed folios. Chapter `P<n>` rows are part introductions; "
          "trailing rows after the last numbered chapter are back matter.", ""]
    for key, b in result["books"].items():
        md.append(f"## {b['title']} (`{key}`)")
        md.append("")
        md.append(f"PDF: `{b['pdf']}`, {b['pdf_pages']} pages. Boundaries: {b['boundary_method']}. "
                  f"Total {b['total_chars']:,} chars, ~{b['total_approx_tokens']:,} tokens.")
        md.append("")
        md.append("| Ch | Title | File | PDF pages | Chars | ~Tokens |")
        md.append("|---|---|---|---|---:|---:|")
        for c in b["chapters"]:
            title = c["title"].replace("|", "\\|")
            md.append(f"| {c['chapter']} | {title} | `{c['file']}` | {c['pdf_pages'][0]}\u2013{c['pdf_pages'][1]} | "
                      f"{c['chars']:,} | {c['approx_tokens']:,} |")
        md.append("")
    (brooks_dir / "MANIFEST.md").write_text("\n".join(md), encoding="utf-8")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-dir", default=str(DEFAULT_PDF_DIR))
    ap.add_argument("--out", default=str(HERE / "text"))
    ap.add_argument("--only", default="", help="comma-separated book keys")
    args = ap.parse_args()
    pdf_dir = Path(args.pdf_dir)
    out_root = Path(args.out)
    only = {k for k in args.only.split(",") if k}

    manifest_path = HERE / "MANIFEST.json"
    result = {"generated": str(date.today()), "books": {}}
    if manifest_path.exists() and only:
        try:
            result["books"] = json.loads(manifest_path.read_text(encoding="utf-8")).get("books", {})
        except Exception:
            pass
    for book in BOOKS:
        if only and book["key"] not in only:
            continue
        result["books"][book["key"]] = process_book(book, pdf_dir, out_root)
    result["books"] = {b["key"]: result["books"][b["key"]] for b in BOOKS if b["key"] in result["books"]}
    write_manifests(result, HERE)
    print(f"\nwrote {HERE / 'MANIFEST.json'} and MANIFEST.md")


if __name__ == "__main__":
    main()
