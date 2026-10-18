from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.records import active_revision, read_revision
from ui import data, widgets

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "ui" / "app.py")


def run(page: str | None = None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    if page:
        at.switch_page(page)
        at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


@pytest.mark.parametrize("page", list(widgets.PAGES.values()))
def test_every_page_loads(page):
    # AppTest.switch_page runs the page script alone; the entry script (top bar, nav) is tested below
    assert len(run(page).title) == 1


def test_entry_renders_top_bar_and_overview():
    at = run()
    md = " ".join(m.value for m in at.markdown)
    snap = data.load()
    assert "CFM56-7B27 konsept" in md and snap["concept"] in md
    assert snap["active_module"]["label"] in md
    assert [t.value for t in at.title] == ["Genel bakış"]


@pytest.mark.parametrize("page", [p for k, p in widgets.PAGES.items() if k not in ("genel_bakis", "m0")])
def test_placeholder_pages(page):
    assert [i.value for i in run(page).info] == ["3. aşamada"]


def test_overview_metrics_match_results():
    rev = active_revision("M0")
    results = read_revision("M0", rev, "results.yaml")
    egt = next(c for c in results["checks"] if c["name"] == data.EGT_CHECK)
    expected = {
        "İtki": data.quantity(results["performance"]["thrust"], 1),
        "SFC": data.quantity(results["performance"]["sfc"], 2),
        "EGT payı": data.quantity({"value": egt["margin"], "unit": "K", "tag": results["egt"]["displayed_C"]["tag"]}, 0),
        "W2": data.quantity(results["calibration"]["W2"], 0),
    }
    shown = {m.label: m.value for m in run().metric}
    assert shown == expected
    assert shown["İtki"] == f"{results['performance']['thrust']['value']:.1f}".replace(".", ",") + " kN [H]"


def test_m0_page_shows_validation_and_stations():
    at = run(widgets.PAGES["m0"])
    md = " ".join(m.value for m in at.markdown)
    assert "Girão 18/19" in md
    stations = at.dataframe[0].value
    assert list(stations["İst."]) == data.read_yaml(data.CONCEPT_REFERENCE)["stations"]["order"]
    assert set(stations["Etiket"]) == {"H"}


def test_formatting():
    assert data.num(1670.66, 1) == "1670,7"
    assert data.quantity({"value": 75.08, "unit": "K", "tag": "T"}, 0) == "75 K [T]"
    assert data.tolerance({"value": 0.01, "type": "relative"}) == "± %1"
    assert data.tolerance({"value": 10.0, "type": "absolute", "unit": "K"}) == "± 10 K"
