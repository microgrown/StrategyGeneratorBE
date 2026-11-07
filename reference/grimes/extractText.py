#!/usr/bin/env python
"""Extract Adam Grimes' "The Art and Science of Technical Analysis" PDF to per-chapter text files.

Output: reference/grimes/text/grimes/NN_<slug>.txt (git-ignored)
        reference/grimes/MANIFEST.json and MANIFEST.md

Unlike the Brooks books, this PDF's outline entries are file-style labels with
no titles (ffirs, ftoc, fpref, flast, c01..c12, bapp01..bapp03, bgloss, bbiblio,
babout, bindex). Chapter *boundaries* come from those outline page numbers;
chapter *titles* come from the printed table of contents (PDF pages 7-10) and
were hand-verified against the first heading line of each chapter/appendix.

Numbering: 00 = front matter (ffirs+ftoc+fpref+flast merged: half-title, copyright,
dedication, contents, preface, acknowledgments); 01..12 = chapters; 13..15 =
appendices A-C; 16 = glossary; 17..19 = bibliography / about the author / index
(trailing, not mined).

Page markers "[[page P]]" use 1-based PDF page numbers (what a PDF viewer shows).

Cleanup: printer slug lines ("P1: OTA...", "JWBT634-...") and running heads are
stripped; ligatures (fi, fl, ...) are unfolded; drop-cap letters are rejoined to
their word; runs of blank lines are collapsed. Body text is not rewrapped.

Running heads in this book differ from the Brooks books: even pages carry
"NN ALL CAPS SECTION" (matches the Brooks all-caps head regex) but odd pages
carry "Title Case Chapter Name NN" (mixed case) -- so the head regex here is
extended to also match a leading title-case run before the trailing folio
number. Verified against all 480 pages with no false positives on body text.

Usage: python extractText.py [--pdf-dir DIR] [--out DIR]
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
DEFAULT_PDF_DIR = HERE.parent

BOOKS = [
    {
        "key": "grimes",
        "title": "The Art and Science of Technical Analysis",
        "pdf": "pcmbrokers_(Wiley finance series) Adam Grimes-The art and science of technical "
               "analysis _ market structure, price action, and trading strategies-J. Wiley  &  "
               "Sons  (2012).pdf",
    },
]

# Chapter plan: (chapter_num, title, [outline keys to merge], kind)
# kind "front" bundles multiple outline entries into 00; everything else is one outline
# entry each. Titles for c01..c12 and bapp01..bapp03 are taken from the printed TOC
# (PDF pages 7-10); bgloss/bbiblio/babout/bindex titles are the first heading line.
CHAPTER_PLAN = [
    ("00", "Front Matter, Preface, and Acknowledgments", ["ffirs", "ftoc", "fpref", "flast"], "front"),
    ("01", "The Trader’s Edge", ["c01"], "chapter"),
    ("02", "The Market Cycle and the Four Trades", ["c02"], "chapter"),
    ("03", "On Trends", ["c03"], "chapter"),
    ("04", "On Trading Ranges", ["c04"], "chapter"),
    ("05", "Interfaces between Trends and Ranges", ["c05"], "chapter"),
    ("06", "Practical Trading Templates", ["c06"], "chapter"),
    ("07", "Tools for Confirmation", ["c07"], "chapter"),
    ("08", "Trade Management", ["c08"], "chapter"),
    ("09", "Risk Management", ["c09"], "chapter"),
    ("10", "Trade Examples", ["c10"], "chapter"),
    ("11", "The Trader’s Mind", ["c11"], "chapter"),
    ("12", "Becoming a Trader", ["c12"], "chapter"),
    ("13", "Appendix A: Trading Primer", ["bapp01"], "appendix"),
    ("14", "Appendix B: A Deeper Look at Moving Averages and the MACD", ["bapp02"], "appendix"),
    ("15", "Appendix C: Sample Trade Data", ["bapp03"], "appendix"),
    ("16", "Glossary", ["bgloss"], "glossary"),
    ("17", "Bibliography", ["bbiblio"], "back"),
    ("18", "About the Author", ["babout"], "back"),
    ("19", "Index", ["bindex"], "back"),
]

LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl",
             "ﬅ": "st", "ﬆ": "st"}

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


def unfold_ligatures(t):
    for k, v in LIGATURES.items():
        t = t.replace(k, v)
    return t


# ---------------------------------------------------------------- boundary detection


def outline_page_map(reader):
    """Map bare outline labels (ffirs, c01, bapp01, ...) -> 0-based start page."""
    flat = {}

    def walk(items):
        for it in items:
            if isinstance(it, list):
                walk(it)
            else:
                try:
                    p = reader.get_destination_page_number(it)
                except Exception:
                    p = None
                if p is not None:
                    flat[norm_title(it.title)] = p

    walk(reader.outline)
    return flat


def build_sections(reader):
    page_map = outline_page_map(reader)
    n_pages = len(reader.pages)
    missing = [k for spec in CHAPTER_PLAN for k in spec[2] if k not in page_map]
    if missing:
        raise RuntimeError(f"outline keys missing from PDF: {missing}")

    sections = []
    for num, title, keys, kind in CHAPTER_PLAN:
        start = min(page_map[k] for k in keys)
        sections.append({"chapter": num, "title": title, "file": f"{num}_{slugify(title)}.txt",
                          "start": start, "kind": kind})
    sections.sort(key=lambda s: s["start"])
    for i, s in enumerate(sections):
        s["end"] = (sections[i + 1]["start"] - 1) if i + 1 < len(sections) else n_pages - 1
    return sections


# ---------------------------------------------------------------- page cleanup

SLUG_RE = re.compile(r"^\s*(P1:\s*OTA|JWBT\d+-)")
CAPS = r"[A-Z0-9][A-Z0-9 ,:;'’\-–—()/&.?!]*"
TITLECASE = r"[A-Z][A-Za-z0-9 ,:;'’\-–—()/&.?!]*"
# Running heads in this book: even pages "NN ALL CAPS SECTION", odd pages
# "Title Case Chapter Name NN" (mixed case) -- both are matched here.
HEAD_RE = re.compile(
    r"^\s*(?:\d{1,3}\s+(?:" + CAPS + r")"
    r"|(?:" + CAPS + r"|" + TITLECASE + r")\s+\d{1,3})\s*$")
HEAD_EXCLUDE_RE = re.compile(r"^\s*(CHAPTER|PART|FIGURE|APPENDIX)\b", re.I)
FOLIO_RE = re.compile(r"^\s*\d{1,3}\s*$")
DROPCAP_RE = re.compile(r"^[A-Z]$")


def clean_page(text):
    text = unfold_ligatures(text).replace("\r", "")
    lines = [l.rstrip() for l in text.split("\n")]
    # printer slug lines (first line(s) of every page)
    while lines and (not lines[0].strip() or SLUG_RE.match(lines[0])):
        lines.pop(0)
    # running head: first line of the page (see HEAD_RE docstring above)
    if lines and len(lines[0].strip()) <= 70 and HEAD_RE.match(lines[0].strip()) \
            and not HEAD_EXCLUDE_RE.match(lines[0].strip()):
        lines.pop(0)
    # folio at page bottom (chapter openers and blank pages)
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
    sections = build_sections(reader)
    method = "outline (bare file-style labels; titles hand-mapped from printed TOC)"

    sample = "".join((reader.pages[i].extract_text() or "") for i in range(min(40, n_pages)))
    typeset = "wiley" if "JWBT" in sample else "reflow"

    out_dir = out_root / book["key"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.txt"):
        old.unlink()

    manifest = []
    nospace_pages = []
    print(f"\n== {book['title']} ({book['pdf']}) pages={n_pages} method={method} typeset={typeset}")
    for s in sections:
        a, b = s["start"], s["end"]
        parts = [f"# {book['title']} — Chapter {s['chapter']}: {s['title']} (PDF pages {a + 1}–{b + 1})", ""]
        for i in range(a, b + 1):
            raw = reader.pages[i].extract_text() or ""
            t = clean_page(raw)
            if not t:
                continue
            # detect pages whose inter-word spaces were lost (long run of letters,
            # no spaces, on a line that clearly isn't a number/URL/table)
            for line in t.split("\n"):
                letters_only = re.sub(r"[^A-Za-z]", "", line)
                if len(letters_only) >= 40 and " " not in line.strip() and len(line.strip()) >= 40:
                    nospace_pages.append(i + 1)
                    break
            parts.append(f"[[page {i + 1}]]")
            parts.append(t)
            parts.append("")
        body = "\n".join(parts).rstrip() + "\n"
        path = out_dir / s["file"]
        path.write_text(body, encoding="utf-8")
        chars = len(body)
        entry = {"chapter": s["chapter"], "title": s["title"], "file": f"text/{book['key']}/{s['file']}",
                 "pdf_pages": [a + 1, b + 1], "chars": chars, "approx_tokens": chars // 4}
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
    if nospace_pages:
        print(f"  pages with lost inter-word spaces: {len(set(nospace_pages))} -> {sorted(set(nospace_pages))[:20]}...")
    return {"title": book["title"], "pdf": book["pdf"], "pdf_pages": n_pages, "boundary_method": method,
            "typeset": typeset, "total_chars": total, "total_approx_tokens": total // 4,
            "chapters": manifest}, sorted(set(nospace_pages))


def write_manifests(result, grimes_dir):
    (grimes_dir / "MANIFEST.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                                                encoding="utf-8")
    md = ["# Grimes text extraction manifest", "",
          f"Generated {result['generated']} by `extractText.py`. Files live under `reference/grimes/text/` "
          "(git-ignored; regenerate with the script). `[[page P]]` markers and the PDF pages column are "
          "1-based PDF page numbers, not printed folios. Chapters 13-15 are appendices A-C; 16 is the "
          "glossary; 17-19 (bibliography, about the author, index) are trailing back matter and are not mined.",
          ""]
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
            md.append(f"| {c['chapter']} | {title} | `{c['file']}` | {c['pdf_pages'][0]}–{c['pdf_pages'][1]} | "
                      f"{c['chars']:,} | {c['approx_tokens']:,} |")
        md.append("")
    (grimes_dir / "MANIFEST.md").write_text("\n".join(md), encoding="utf-8")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-dir", default=str(DEFAULT_PDF_DIR))
    ap.add_argument("--out", default=str(HERE / "text"))
    args = ap.parse_args()
    pdf_dir = Path(args.pdf_dir)
    out_root = Path(args.out)

    result = {"generated": str(date.today()), "books": {}}
    all_nospace = {}
    for book in BOOKS:
        entry, nospace = process_book(book, pdf_dir, out_root)
        result["books"][book["key"]] = entry
        all_nospace[book["key"]] = nospace
    write_manifests(result, HERE)
    print(f"\nwrote {HERE / 'MANIFEST.json'} and MANIFEST.md")
    for k, pages in all_nospace.items():
        print(f"{k}: {len(pages)} pages with lost inter-word spaces")


if __name__ == "__main__":
    main()
