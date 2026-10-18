import shutil
from pathlib import Path

import pytest

from core.diff import diff_concepts, diff_revisions, flatten, is_empty
from core.records import RecordError, create_concept, create_revision
from core.util import read_yaml

ROOT = Path(__file__).resolve().parents[1]


def test_identical_revisions_give_empty_diff():
    d = diff_revisions("M0", "rev005", "rev005")
    assert is_empty(d)
    assert d["params"] == d["results"] == d["outputs"] == []


def test_m0_rev004_to_rev005_known_changes():
    d = diff_revisions("M0", "rev004", "rev005")
    results = {r["key"]: r for r in d["results"]}
    w2, t4 = results["calibration.W2.value"], results["calibration.T4.value"]
    assert (w2["old"], w2["new"]) == (371.98, 345.397)
    assert w2["delta"] == pytest.approx(-26.583)
    assert w2["pct"] == pytest.approx(-7.1464, abs=1e-3)
    assert (t4["old"], t4["new"]) == (1626.59, 1670.66)
    assert t4["delta"] == pytest.approx(44.07)
    assert results["stations[2].W_kg_s"]["new"] == 345.4  # list of stations keyed by station id

    params = {p["path"]: p for p in d["params"]}
    assert (params["version"]["old"], params["version"]["new"]) == (4.2, 4.3)
    assert params["rated_case.delta_eta_limit.value"] == {
        "path": "rated_case.delta_eta_limit.value", "old": None, "new": 0.03}

    assert d["bom"] == {"header": [], "added": [], "removed": [], "changed": {}}  # M0 has no parts
    assert d["outputs"] == []


def test_non_numeric_results_have_no_delta():
    d = diff_revisions("M0", "rev004", "rev005")
    model = next(r for r in d["results"] if r["key"] == "model")
    assert model["delta"] is None and model["pct"] is None


def test_unknown_revision_raises():
    with pytest.raises(RecordError):
        diff_revisions("M0", "rev005", "rev999")


def test_flatten_keys_lists_by_id_and_keeps_scalar_lists():
    data = {"parts": [{"id": "M1.1.1", "qty": {"value": 24}}], "unknowns": ["W2", "T4"]}
    assert flatten(data) == {"parts[M1.1.1].qty.value": 24, "unknowns": ["W2", "T4"]}


# --- BOM, outputs and concepts on a temp copy -------------------------------------------------

NO_RECORDS = shutil.ignore_patterns("rev[0-9][0-9][0-9]", "concept[0-9][0-9][0-9]", "ACTIVE", "ACTIVE_CONCEPT", "ACCEPTED", "CR-*.yaml")
FIXTURE = Path(__file__).parent / "fixtures" / "bom_valid.yaml"


@pytest.fixture
def repo(tmp_path) -> Path:
    shutil.copytree(ROOT / "engine", tmp_path / "engine", ignore=NO_RECORDS)
    shutil.copyfile(FIXTURE, tmp_path / "engine" / "M1_inlet_fan" / "bom" / "bom.yaml")
    return tmp_path


def test_bom_outputs_and_concepts(repo):
    from core.bom import load, write

    m1 = repo / "engine" / "M1_inlet_fan"
    out = m1 / "geometry" / "section.svg"
    out.parent.mkdir(exist_ok=True)
    out.write_text("<svg/>", encoding="utf-8")
    create_revision("M0", "M0 base", "test", root=repo)
    create_revision("M1", "Baseline", "test", outputs=["geometry/section.svg"], root=repo)
    c1 = create_concept("first", root=repo)

    bom = load(m1 / "bom" / "bom.yaml")
    blade = next(p for p in bom["parts"] if p["id"] == "M1.1.1")
    blade["qty"] = dict(blade["qty"], value=blade["qty"]["value"] + 2)
    spinner = dict(bom["parts"][0], id="M1.1.3", name="Fan Stage 1 Spinner", parent="M1.1",
                   function="Guide inlet flow at the hub", material="Al alloy")
    bom["parts"].append(spinner)
    write(m1 / "bom" / "bom.yaml", bom)
    out.write_text("<svg></svg>", encoding="utf-8")
    create_revision("M1", "More blades", "test", outputs=["geometry/section.svg"], root=repo)
    c2 = create_concept("second", root=repo)

    d = diff_revisions("M1", "rev001", "rev002", root=repo)
    assert list(d["bom"]["changed"]) == ["M1.1.1"]
    assert [c["path"] for c in d["bom"]["changed"]["M1.1.1"]] == ["qty.value"]
    assert d["bom"]["added"] == ["M1.1.3"] and d["bom"]["removed"] == []
    assert diff_revisions("M1", "rev002", "rev001", root=repo)["bom"]["removed"] == ["M1.1.3"]
    assert [o["file"] for o in d["outputs"]] == ["geometry/section.svg"]
    assert d["outputs"][0]["old"] != d["outputs"][0]["new"]

    assert diff_concepts(c1, c2, root=repo) == [{"module": "M1", "old": "rev001", "new": "rev002"}]
    assert diff_concepts(c1, c1, root=repo) == []
    assert read_yaml(m1 / "records" / "rev002" / "manifest.yaml")["parent_revision"] == "rev001"


def test_numeric_changes_counts_numbers_not_text_or_added_keys():
    from core.diff import blocking, diff_data, numeric_changes
    a = {"params": {"q": {"value": 1.0, "note": "x"}, "t": {"value": 0.1, "tag": "T"}, "s": {"value": "4.3e6"}},
         "results": {"r": 2.0, "list": [1, 2]}}
    same = {"params": {"q": {"value": 1.0, "note": "y"}, "t2": {"value": 0.1, "tag": "T"}, "s": {"value": "4.3e6"}},
            "results": {"r": 2.0, "list": [1, 2], "new": 5.0}}
    changes = numeric_changes(diff_data(a, same))
    assert [c["kind"] for c in changes] == ["moved"] and blocking(changes) == []
    worse = {"params": {"q": {"value": 1.1}, "s": {"value": "4.4e6"}}, "results": {"list": [1, 3]}}
    kinds = sorted((c["kind"], c["path"]) for c in blocking(numeric_changes(diff_data(a, worse))))
    assert kinds == [("changed", "list"), ("changed", "q.value"), ("changed", "s.value"),
                     ("removed", "r"), ("removed", "t.value")]


def test_rev006_is_a_maintenance_revision():
    from core.diff import numeric_changes
    assert numeric_changes(diff_revisions("M0", "rev005", "rev006")) == []
    assert numeric_changes(diff_revisions("M0", "rev004", "rev005"))  # design


def test_text_change_inside_keyed_list_is_not_numeric():
    from core.diff import diff_data, numeric_changes
    a = {"results": {"assumptions": [{"path": "x", "value": 1.0, "note": "a"}]}}
    b = {"results": {"assumptions": [{"path": "x", "value": 1.0, "note": "a, b"}]}}
    d = diff_data(a, b)
    assert [c["key"] for c in d["results"]] == ["assumptions[x].note"]
    assert numeric_changes(d) == []
