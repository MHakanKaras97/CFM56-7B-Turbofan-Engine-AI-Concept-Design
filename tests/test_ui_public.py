"""Public UI (ui_public/): bilingual texts complete, explanations for every M0 value shown, learning topics in both
languages, images present, every page runs in Turkish and English, modules shown as the published baseline rev01."""

from pathlib import Path

import pytest
import yaml
from streamlit.testing.v1 import AppTest

from core.budgets import read_icd
from core.records import active_revision, read_revision
from ui_public import data

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "ui_public" / "app.py")
CONTENT = ROOT / "ui_public" / "content"
STRINGS = yaml.safe_load((CONTENT / "strings.yaml").read_text(encoding="utf-8"))
PAGES = ["pages/overview.py", "pages/engine.py", "pages/modules.py", "pages/learning.py", "pages/requests.py",
         "pages/revisions.py"]
TOPICS = ["00_turbofan"] + [m.lower() for m in data.MODULES]


def run(page: str | None = None, lang: str = "tr", state: dict | None = None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["lang"] = lang
    for k, v in (state or {}).items():
        at.session_state[k] = v
    at.run()
    if page:
        at.switch_page(page)
        at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_every_text_has_both_languages():
    for group, items in STRINGS.items():
        for key, entry in items.items():
            assert isinstance(entry, dict) and entry.get("tr") and entry.get("en"), (group, key)


def test_every_m0_value_is_explained():
    """M0 page: a meaning for every check, metric, shown station and budget item (no reference values)."""
    icd = read_icd("test")
    results = read_revision("M0", active_revision("M0"), "results.yaml")
    for c in results["checks"]:
        assert c["name"] in STRINGS["checks"] and c["name"] in STRINGS["check_labels"], c["name"]
    for m in data.metrics():
        assert m["key"] in STRINGS["metrics"] and f"label_{m['key']}" in STRINGS["metrics"]
    for sid in data.STATION_ORDER:
        assert sid in STRINGS["stations"]
    for mod in icd["modules"].values():
        for k in mod["budget"]:
            assert k in STRINGS["budget"], k
    for m in ["M0", *data.MODULES]:
        assert m in STRINGS["module_names"]


def test_materials_named():
    for m in data.MODULES:
        for p in data.bom(m):
            assert p["material"] is None or p["material"] in STRINGS["materials"], (m, p["material"])  # None: assembly


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_learning_topics(lang):
    for topic in TOPICS:
        text = (CONTENT / "learning" / lang / f"{topic}.md").read_text(encoding="utf-8")
        assert text.startswith("# ")
        if topic != "00_turbofan":
            assert "|---|---|---|---|" in text  # parts table: part, function, material, manufacturing


def test_images_present():
    for name in ["engine", *[m.lower() for m in data.MODULES]]:
        for view in ("iso", "cutaway", "section"):
            assert data.image(f"{name}_{view}") is not None, (name, view)


@pytest.mark.parametrize("lang", ["tr", "en"])
@pytest.mark.parametrize("page", PAGES)
def test_every_page_runs(page, lang):
    at = run(page, lang)
    assert at.title, page


def test_entry_title_language_and_baseline():
    at = run(lang="en")
    md = " ".join(m.value for m in at.markdown)
    assert "CFM56-7B27 Concept Design" in md and "rev01" in md and "published baseline" in md
    at = run(lang="tr")
    assert "yayın sürümü" in " ".join(m.value for m in at.markdown)


def test_module_page_shows_bom_and_baseline():
    at = run("pages/modules.py", "en", {"module": "M3"})
    assert at.title[0].value == "M3 · High-pressure compressor"
    assert "rev01" in " ".join(m.value for m in at.markdown)
    df = at.dataframe[0].value
    assert len(df) == len(data.bom("M3")) and "M3.1.1" in set(df["ID"])


def test_revisions_and_requests_empty():
    for page in ("pages/revisions.py", "pages/requests.py"):
        at = run(page, "tr")
        assert len(at.info) == 1 and not at.dataframe
