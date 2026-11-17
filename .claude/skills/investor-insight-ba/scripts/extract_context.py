#!/usr/bin/env python3
"""Dump the text of a context document (.pdf, .pptx, .docx) to stdout as UTF-8.

Why this exists: the Read tool needs poppler to open PDFs, and .pptx/.docx are
zip files it cannot read at all. The project's business context lives in exactly
those formats (contexts/), so a BA pass starts with this script.

Usage:
    python extract_context.py <file>                 # print text
    python extract_context.py <file> --out plan.txt  # save text, print only the size
    python extract_context.py <dir>                  # list supported files in a directory

Do not run python with -I: isolated mode hides user-site packages such as pymupdf.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

SUPPORTED = {".pdf", ".pptx", ".docx"}


def _natural_key(name: str) -> int:
    nums = re.findall(r"\d+", name)
    return int(nums[-1]) if nums else 0


def read_pdf(path: Path) -> str:
    for mod_name in ("pymupdf", "fitz"):
        try:
            mod = __import__(mod_name)
        except ImportError:
            continue
        doc = mod.open(str(path))
        return "\n".join(f"--- page {i + 1}\n{p.get_text()}" for i, p in enumerate(doc))
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(f"--- page {i + 1}\n{p.extract_text() or ''}" for i, p in enumerate(reader.pages))
    except ImportError:
        pass
    if shutil.which("pdftotext"):
        # Pipe through stdin/stdout: pdftotext mangles non-ASCII characters in file *names* on Windows.
        with open(path, "rb") as fh:
            res = subprocess.run(["pdftotext", "-layout", "-", "-"], stdin=fh, capture_output=True)
        return res.stdout.decode("utf-8", errors="replace")
    raise SystemExit("No PDF reader found. Install one:  pip install pymupdf")


def read_pptx(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        slides = sorted(
            (n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
            key=_natural_key,
        )
        out = []
        for n in slides:
            xml = z.read(n).decode("utf-8")
            out.append(f"--- slide {_natural_key(n)}\n" + " ".join(re.findall(r"<a:t>([^<]*)</a:t>", xml)))
    return "\n".join(out)


def read_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    paragraphs = re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S)
    lines = ["".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)) for p in paragraphs]
    return "\n".join(line for line in lines if line.strip())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", type=Path)
    ap.add_argument("--out", type=Path, help="write text to this file instead of stdout")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    p: Path = args.path
    if p.is_dir():
        for f in sorted(p.iterdir()):
            if f.suffix.lower() in SUPPORTED:
                print(f"{f.name}\t{f.stat().st_size} bytes")
        return
    if not p.exists():
        raise SystemExit(f"Not found: {p}")

    readers = {".pdf": read_pdf, ".pptx": read_pptx, ".docx": read_docx}
    reader = readers.get(p.suffix.lower())
    if reader is None:
        raise SystemExit(f"Unsupported type {p.suffix}; supported: {', '.join(sorted(SUPPORTED))}")

    text = reader(p)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {len(text)} characters to {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
