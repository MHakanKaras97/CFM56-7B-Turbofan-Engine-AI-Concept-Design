import hashlib
import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.records import active_revision, read_revision
from core.requests import load_cr
from ui import data, widgets

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "ui" / "app.py")
REAL_REQUESTS = ROOT / "engine" / "M0_engine" / "requests"


def run(page: str | None = None, query: dict | None = None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    if page:
        at.switch_page(page)
        for k, v in (query or {}).items():
            at.query_params[k] = v
        at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def text(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


# --- pages ----------------------------------------------------------------------------------

@pytest.mark.parametrize("page", list(widgets.PAGES.values()))
def test_every_page_loads(page):
    # AppTest.switch_page runs the page script alone; the entry script (top bar, nav) is tested below
    assert len(run(page).title) == 1


def test_entry_renders_top_bar_and_overview():
    at = run()
    md = text(at)
    snap = data.load()
    assert "CFM56-7B27 konsept" in md and snap["concept"] in md
    assert snap["active_module"]["label"] in md
    assert [t.value for t in at.title] == ["Genel bakış"]


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


@pytest.mark.parametrize("module, title", [("M1", "M1 Giriş ve fan"), ("M0", "M0 motor")])
def test_strip_opens_module_page(module, title):
    at = run()
    at.button(key=f"strip_{module}").click().run()
    assert not at.exception and [t.value for t in at.title] == [title]


def test_module_card_and_template():
    at = run()
    at.button(key="card_M3").click().run()
    assert [t.value for t in at.title] == ["M3 HP kompresör"]
    assert "BOM boş" in " ".join(c.value for c in at.caption)
    assert {"btn_section", "btn_3d", "btn_fusion"} <= {b.key for b in at.button}
    assert {"mod_rev_a", "mod_rev_b"} <= {s.key for s in at.selectbox}


def test_m0_page_validation_stations_ref_tags_and_info():
    at = run(widgets.PAGES["m0"])
    md = text(at)
    assert "Girão 18/19" in md
    stations = at.dataframe[0].value
    assert list(stations["İst."]) == data.read_yaml(data.CONCEPT_REFERENCE)["stations"]["order"]
    assert set(stations["Etiket"]) == {"H"}
    captions = " ".join(c.value for c in at.caption)
    assert "ref 950 [K]" in captions and "ref 190 – 215 [G]" in captions
    results = read_revision("M0", active_revision("M0"), "results.yaml")
    assert all(f"`{a['path']}`" in md for a in results["assumptions"])
    assert [t.label for t in at.tabs] == ["Genel", "Bilgi"]
    assert "Belirsizlik bandı" in md and "ADR-010" in " ".join(w.value for w in at.warning)


def test_revisions_page_shows_diff():
    at = run(widgets.PAGES["revizyonlar"])
    at.selectbox(key="rev_b").set_value("rev005").run()
    at.selectbox(key="rev_a").set_value("rev004").run()
    results = next(df.value for df in at.dataframe if "Anahtar" in df.value.columns)
    w2 = results[results["Anahtar"] == "calibration.W2.value"].iloc[0]
    assert (w2["Eski"], w2["Yeni"], w2["%"]) == ("371,98", "345,4", "-7,15")


def test_learning_page_sources_and_legend():
    at = run(widgets.PAGES["ogrenme"])
    assert any("Kaynak" in df.value.columns and "Lisans" in df.value.columns for df in at.dataframe)
    assert all(f"**[{t}]**" in text(at) for t, _ in data.TAG_LEGEND)


def test_formatting():
    assert data.num(1670.66, 1) == "1670,7"
    assert data.quantity({"value": 75.08, "unit": "K", "tag": "T"}, 0) == "75 K [T]"
    assert data.tolerance({"value": 0.01, "type": "relative"}) == "± %1"
    assert data.tolerance({"value": 10.0, "type": "absolute", "unit": "K"}) == "± 10 K"
    assert widgets.ref_tag({"a": "KS", "b": "T", "c": "KS"}) == "[KS/T]"


# --- CR decision flow on a temporary copy -----------------------------------------------------

@pytest.fixture
def ui_repo(tmp_path, monkeypatch) -> Path:
    """Temp copy of engine/ with one open budget CR; the UI is pointed at it."""
    from engine.M0_engine.analysis.integration import integration_check

    shutil.copytree(ROOT / "engine", tmp_path / "engine",
                    ignore=shutil.ignore_patterns("__pycache__", "CR-*.yaml", "sources"))
    icd = data.load_icd()
    eta = icd["modules"]["M3"]["budget"]["eta_hpc"]["value"]
    cr_id = integration_check("M3", {"eta_hpc": eta - 0.03}, cr_root=tmp_path)["cr"]
    assert cr_id == "CR-001"
    monkeypatch.setenv("TURBOFAN_UI_ROOT", str(tmp_path))
    before = sorted(REAL_REQUESTS.glob("CR-*.yaml"))
    yield tmp_path
    assert sorted(REAL_REQUESTS.glob("CR-*.yaml")) == before  # the real repo is never touched


def open_dialog(root: Path, option: str, note: str) -> AppTest:
    at = run(widgets.PAGES["talepler"])
    assert "CR-001" in text(at) and data.root() == root
    assert {m.label for m in at.metric} >= {"ΔSFC", "ΔEGT", "ΔT41"}
    assert "M0 integration_check" in text(at)
    at.radio(key="opt_CR-001").set_value(option).run()
    at.text_area(key="note_CR-001").input(note).run()
    at.button(key="save_CR-001").click().run()
    assert not at.exception
    assert {"confirm_ok", "confirm_cancel"} <= {b.key for b in at.button}  # dialog open
    return at


def cr_sha(root: Path) -> str:
    return hashlib.sha256((root / "engine" / "M0_engine" / "requests" / "CR-001.yaml").read_bytes()).hexdigest()


def test_dialog_cancel_writes_nothing(ui_repo):
    before = cr_sha(ui_repo)
    at = open_dialog(ui_repo, "b", "M3 redesign")
    at.button(key="confirm_cancel").click().run()
    assert not at.exception
    assert "confirm_ok" not in {b.key for b in at.button}  # dialog closed
    assert cr_sha(ui_repo) == before
    assert load_cr("CR-001", root=ui_repo)["status"] == "open"


def test_decision_flow_records_decision(ui_repo):
    at = open_dialog(ui_repo, "b", "M3 redesign")
    at.button(key="confirm_ok").click().run()
    assert not at.exception
    cr = load_cr("CR-001", root=ui_repo)
    assert cr["status"] == "rejected"
    assert cr["decision"]["option"] == "b" and cr["decision"]["note"] == "M3 redesign"
    assert cr["decision"]["decided_by"] == "user (UI)"
    assert [h["to"] for h in cr["history"]] == ["open", "rejected"]
    assert "karar kaydedildi" in " ".join(s.value for s in at.success)
    assert active_revision("M0", root=ui_repo) == active_revision("M0")  # decide only, nothing applied


def test_save_needs_a_note(ui_repo):
    at = run(widgets.PAGES["talepler"])
    assert at.button(key="save_CR-001").disabled
