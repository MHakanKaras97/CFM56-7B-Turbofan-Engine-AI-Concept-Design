"""Plain-text cache of source PDFs, so agents grep text instead of opening PDFs.

Usage:
    python -m tools.pdf_text

Inputs:  every PDF under the source archive (`sources_archive` in config/tools.local.yaml, outside the repo),
         laid out as <archive>/<module>/<relative path>.pdf
Output:  engine/<module>/learning/sources_text/<same relative path>.txt (git-ignored),
         pages separated by "=== p.N ===" markers (N = PDF page, 1-based).
PDFs without a usable text layer (scans) get the single line SCANNED_LINE.
Uses pypdf (BSD-3-Clause).
"""

import sys
from pathlib import Path

from pypdf import PdfReader

from core.toolpaths import sources_archive

ROOT = Path(__file__).resolve().parents[1]
SCANNED_LINE = "SCANNED: no text layer"
# A page counts as text-bearing above this many non-blank characters.
MIN_PAGE_CHARS = 50
# Below this fraction of text-bearing pages the PDF is treated as a scan.
MIN_TEXT_PAGE_FRACTION = 0.1


def format_pages(pages: list[str]) -> str:
    """Join page texts with page markers; SCANNED_LINE if too few pages carry text."""
    text_pages = sum(1 for p in pages if len("".join(p.split())) > MIN_PAGE_CHARS)
    if not pages or text_pages / len(pages) < MIN_TEXT_PAGE_FRACTION:
        return SCANNED_LINE + "\n"
    return "".join(f"=== p.{i} ===\n{p.rstrip()}\n" for i, p in enumerate(pages, 1))


def pdf_pages(path: Path) -> list[str]:
    return [page.extract_text() or "" for page in PdfReader(path).pages]


def text_path(pdf: Path, archive: Path, root: Path = ROOT) -> Path:
    """<archive>/<M>/a/b.pdf -> <root>/engine/<M>/learning/sources_text/a/b.txt"""
    module, *rel = pdf.relative_to(archive).parts
    return (root / "engine" / module / "learning" / "sources_text" / Path(*rel)).with_suffix(".txt")


def main() -> int:
    archive = sources_archive()
    pdfs = sorted(archive.glob("*/**/*.pdf"))
    for pdf in pdfs:
        out = text_path(pdf, archive)
        out.parent.mkdir(parents=True, exist_ok=True)
        text = format_pages(pdf_pages(pdf))
        out.write_text(text, encoding="utf-8")
        status = "scanned" if text.startswith(SCANNED_LINE) else f"{text.count('=== p.')} pages"
        print(f"{out.relative_to(ROOT)}: {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
