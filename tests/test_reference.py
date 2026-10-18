import xml.dom.minidom

import pytest

from tools.reference import SVG_FILE, build_svg, check_layout, load_reference


@pytest.fixture(scope="module")
def ref():
    return load_reference()


def test_svg_regenerates_identically(ref):
    assert build_svg(ref) == SVG_FILE.read_text(encoding="utf-8")
    assert build_svg(ref) == build_svg(load_reference())


def test_svg_is_well_formed_and_shows_all_stations(ref):
    doc = xml.dom.minidom.parseString(build_svg(ref))
    texts = {t.firstChild.data for t in doc.getElementsByTagName("text") if t.firstChild}
    assert set(ref["stations"]["order"]) <= texts
    assert set(ref["modules"]["order"]) <= texts


def test_reference_content(ref):
    assert ref["modules"]["order"] == ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]
    stages = {m: (i["stages"] or {}).get("value") for m, i in ref["modules"]["items"].items()}
    assert stages == {"M1": 1, "M2": 3, "M3": 9, "M4": None, "M5": 1, "M6": 4, "M7": None}
    assert ref["envelope"]["length"]["tag"] == "K"
    assert ref["shafts"]["LP"]["inner"] and not ref["shafts"]["HP"]["inner"]


def test_check_layout_accepts_reference(ref):
    layout = {"module_order": ref["modules"]["order"],
              "stage_counts": {"M1": 1, "M2": 3, "M3": 9, "M5": 1, "M6": 4}}
    assert check_layout(layout, ref) == []
    assert check_layout({"module_order": ["M1", "M2"]}, ref) == []  # partial layout, order kept


def test_check_layout_flags_order_and_stage_counts(ref):
    problems = check_layout({"module_order": ["M2", "M1"], "stage_counts": {"M2": 4, "M9": 1}}, ref)
    assert len(problems) == 3
    assert any("order" in p for p in problems)
    assert any("M2: 4 stages, reference 3" in p for p in problems)
