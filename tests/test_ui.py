import hashlib
import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.records import active_revision, read_revision, revision_ids
from core.requests import decide, load_cr
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
    assert len(run(page).subheader) == 1


def test_entry_renders_top_bar_and_overview():
    at = run()
    md = text(at)
    snap = data.load()
    assert "CFM56-7B27 konsept" in md and snap["concept"] in md
    assert snap["active_module"]["label"] in md
    assert [t.value for t in at.subheader] == ["Genel bakış"] and not at.title
    assert "&nbsp;·&nbsp; Genel bakış" in md  # top bar names the page


def test_overview_metrics_match_results():
    rev = active_revision("M0")
    results = read_revision("M0", rev, "results.yaml")
    egt = next(c for c in results["checks"] if c["name"] == data.EGT_CHECK)
    margin = {"value": egt["margin"], "unit": "K", "tag": results["egt"]["displayed_C"]["tag"]}
    cards = {"İtki": (results["performance"]["thrust"], 1), "SFC": (results["performance"]["sfc"], 2),
             "EGT payı": (margin, 0), "W2": (results["calibration"]["W2"], 0)}
    expected = {}
    for k, (q, d) in cards.items():
        if len(q["unit"]) > widgets.LONG_UNIT:  # long unit moves to the label
            k, q = f"{k} ({q['unit']})", {**q, "unit": None}
        expected[f"{k} {widgets.tag_badge(q['tag'])}"] = data.quantity(q, d, tag=False)
    shown = {m.label: m.value for m in run().metric}
    assert shown == expected
    assert shown["SFC (g/(kN s)) :gray-badge[H]"] == data.num(results["performance"]["sfc"]["value"], 2)
    thrust = results["performance"]["thrust"]
    assert shown["İtki :gray-badge[H]"] == f"{thrust['value']:.1f}".replace(".", ",") + " kN"  # tag not in value
    assert shown["EGT payı :orange-badge[T]"].endswith(" K")


@pytest.mark.parametrize("module, title", [("M1", "M1 Giriş ve fan"), ("M0", "M0 motor")])
def test_strip_opens_module_page(module, title):
    at = run()
    at.button(key=f"strip_{module}").click().run()
    assert not at.exception and [t.value for t in at.subheader] == [title]


def test_module_card_and_template():
    at = run()
    at.button(key="card_M3").click().run()
    assert [t.value for t in at.subheader] == ["M3 HP kompresör"]
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
    shutil.copytree(ROOT / "tools" / "data", tmp_path / "tools" / "data")  # gas data for apply()
    icd = data.read_icd("tests")
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
    assert {m.label.split()[0] for m in at.metric} >= {"ΔSFC", "ΔEGT", "ΔT41"}
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


# --- phase 3b: apply, revert, verify, concept diff link (temporary copy only) ---------------------

def tree_sha(root: Path) -> dict:
    return {str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in (root / "engine").rglob("*") if f.is_file() and "__pycache__" not in f.parts}


def approved_cr(root: Path) -> None:
    decide("CR-001", True, "accept achieved HPC efficiency", root=root, option="a")


def test_apply_cancel_writes_nothing(ui_repo):
    approved_cr(ui_repo)
    before = tree_sha(ui_repo)
    at = run(widgets.PAGES["talepler"])
    at.button(key="apply_CR-001").click().run()
    assert {"confirm_ok", "confirm_cancel"} <= {b.key for b in at.button}
    at.button(key="confirm_cancel").click().run()
    assert not at.exception and tree_sha(ui_repo) == before
    assert load_cr("CR-001", root=ui_repo)["status"] == "approved"


def test_apply_flow_creates_design_revision(ui_repo):
    approved_cr(ui_repo)
    latest = revision_ids("M0", ui_repo)[-1]
    new = f"rev{int(latest[3:]) + 1:03d}"
    at = run(widgets.PAGES["talepler"])
    at.button(key="apply_CR-001").click().run()
    at.button(key="confirm_ok").click().run()
    assert not at.exception
    cr = load_cr("CR-001", root=ui_repo)
    assert cr["status"] == "applied" and cr["applied_revisions"] == {"M0": new}
    manifest = read_revision("M0", new, "manifest.yaml", ui_repo)
    assert (manifest["revision_type"], manifest["change_request"]) == ("design", "CR-001")
    assert f"CR-001 uygulandı: M0 {new}" in " ".join(s.value for s in at.success)
    assert active_revision("M0") == latest  # real repo untouched


def test_revert_cancel_and_confirm(ui_repo):
    active = active_revision("M0", ui_repo)
    target = revision_ids("M0", ui_repo)[-2]
    before = tree_sha(ui_repo)
    at = run(widgets.PAGES["revizyonlar"])
    assert at.button(key=f"revert_{active}").disabled
    at.button(key=f"revert_{target}").click().run()
    at.button(key="confirm_cancel").click().run()
    assert tree_sha(ui_repo) == before
    at.button(key=f"revert_{target}").click().run()
    at.button(key="confirm_ok").click().run()
    assert not at.exception and active_revision("M0", ui_repo) == target
    cr = load_cr("CR-002", root=ui_repo)  # CR-001 is the fixture's budget CR
    assert cr["changes"] == [{"type": "revert", "module": "M0", "from": active, "to": target}]
    assert (cr["status"], cr["impact"]["by"], cr["decision"]["decided_by"]) == ("applied", "M0 revert", "user (UI)")
    assert "CR-002 uygulandı" in " ".join(s.value for s in at.success)
    warnings = " ".join(w.value for w in at.warning)
    assert all(w in warnings for w in cr.get("apply_warnings", []))
    params = read_revision("M0", target, "params.yaml", ui_repo)
    assert data.read_yaml(ui_repo / "engine" / "M0_engine" / "analysis" / "cycle_params.yaml") == params
    assert active_revision("M0") == active  # real repo untouched


def test_concept_revert_through_ui(ui_repo):
    from core.records import active_concept
    before = tree_sha(ui_repo)
    at = run(widgets.PAGES["revizyonlar"])
    at.button(key="revert_concept_concept001").click().run()
    at.button(key="confirm_cancel").click().run()
    assert tree_sha(ui_repo) == before
    at.button(key="revert_concept_concept001").click().run()
    at.button(key="confirm_ok").click().run()
    assert not at.exception
    pins = {m: r for m, r in data.read_concept("concept001", ui_repo)["modules"].items() if r}
    cr = load_cr("CR-002", root=ui_repo)
    assert cr["concept"] == "concept001" and {c["module"]: c["to"] for c in cr["changes"]} == pins
    assert active_concept(root=ui_repo) == "concept001"
    assert all(active_revision(m, ui_repo) == r for m, r in pins.items())


def test_verify_reports_result(ui_repo):
    before = tree_sha(ui_repo)
    rev = active_revision("M0", ui_repo)
    at = run(widgets.PAGES["revizyonlar"])
    at.button(key=f"verify_{rev}").click().run()
    at.button(key="confirm_ok").click().run()
    assert "kayıtla aynı" in " ".join(s.value for s in at.success)
    assert tree_sha(ui_repo) == before  # read-only


def test_concept_diff_row_opens_module_diff():
    at = run(widgets.PAGES["revizyonlar"])
    concepts = data.load()["concepts"]
    a, b = concepts[-2]["modules"]["M0"], concepts[-1]["modules"]["M0"]
    at.button(key="cdiff_M0").click().run()
    assert not at.exception
    assert (at.selectbox(key="rev_a").value, at.selectbox(key="rev_b").value) == (a, b)


def test_history_revisions_cannot_be_reverted():
    at = run(widgets.PAGES["revizyonlar"])
    for rev in ("rev001", "rev002", "rev003"):
        assert at.button(key=f"revert_{rev}").disabled
        assert at.button(key=f"verify_{rev}").disabled is False  # still viewable and verifiable
    for rev in ("rev004", "rev005", "rev006"):
        assert not at.button(key=f"revert_{rev}").disabled
    captions = " ".join(c.value for c in at.caption)
    assert captions.count("Geçmiş kaydı: bu revizyona dönülemez") == 3


def test_stale_icd_is_shown_not_used(tmp_path, monkeypatch):
    shutil.copytree(ROOT / "engine", tmp_path / "engine",
                    ignore=shutil.ignore_patterns("__pycache__", "CR-*.yaml", "sources"))
    (tmp_path / "engine" / "M0_engine" / "records" / "ACTIVE").write_text("rev006\n", encoding="utf-8")
    monkeypatch.setenv("TURBOFAN_UI_ROOT", str(tmp_path))
    at = run(widgets.PAGES["m0"])
    assert "active M0 revision is rev006" in " ".join(e.value for e in at.error)
    assert not at.dataframe  # no stations or budgets from the stale ICD
