from pathlib import Path

from tools.pdf_text import SCANNED_LINE, format_pages, text_path


def test_page_markers():
    pages = ["a" * 60 + "\n", "b" * 60]
    assert format_pages(pages) == f"=== p.1 ===\n{'a' * 60}\n=== p.2 ===\n{'b' * 60}\n"


def test_scanned_when_no_text_layer():
    assert format_pages(["", "  \n", ""]) == SCANNED_LINE + "\n"
    assert format_pages([]) == SCANNED_LINE + "\n"
    # Cover page only, rest images: treated as a scan
    assert format_pages(["x" * 200] + [""] * 20) == SCANNED_LINE + "\n"


def test_text_path_maps_archive_into_repo():
    archive, root = Path("C:/archive"), Path("repo")
    assert (text_path(archive / "M1_inlet_fan" / "aero" / "r67.pdf", archive, root)
            == root / "engine" / "M1_inlet_fan" / "learning" / "sources_text" / "aero" / "r67.txt")
    assert (text_path(archive / "M0_engine" / "a.pdf", archive, root)
            == root / "engine" / "M0_engine" / "learning" / "sources_text" / "a.txt")
