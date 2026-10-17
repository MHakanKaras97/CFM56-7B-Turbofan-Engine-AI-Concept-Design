import shutil
from pathlib import Path

import pytest
import yaml

from core.records import active_revision, create_revision
from core.requests import CRError, apply, create_cr, decide, load_cr, set_impact

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "bom_valid.yaml"
NO_RECORDS = shutil.ignore_patterns("rev[0-9][0-9][0-9]", "concept[0-9][0-9][0-9]", "ACTIVE", "ACTIVE_CONCEPT", "CR-*.yaml")

BLADE_QTY_CHANGE = {
    "module": "M1",
    "path": "parts[M1.1.1].qty",
    "old": {"value": 24, "unit": "ea", "tag": "KS"},
    "new": {"value": 22, "unit": "ea", "tag": "T"},
}


@pytest.fixture
def repo(tmp_path) -> Path:
    """Temp copy of engine/ with a recorded M1 baseline; real folders are never touched."""
    shutil.copytree(ROOT / "engine", tmp_path / "engine", ignore=NO_RECORDS)
    shutil.copyfile(FIXTURE, tmp_path / "engine" / "M1_inlet_fan" / "bom" / "bom.yaml")
    create_revision("M1", "Baseline", "Test setup", root=tmp_path)
    return tmp_path


def bom(repo: Path) -> dict:
    return yaml.safe_load((repo / "engine" / "M1_inlet_fan" / "bom" / "bom.yaml").read_text(encoding="utf-8"))


def new_cr(repo: Path, changes=None) -> str:
    return create_cr("M2", ["M1"], "Booster inlet needs fewer fan blades", changes or [BLADE_QTY_CHANGE], root=repo)


def test_lifecycle_open_approved_applied(repo):
    cr_id = new_cr(repo)
    assert cr_id == "CR-001"
    assert load_cr(cr_id, root=repo)["status"] == "open"

    set_impact(cr_id, ["M1", "M2"], "Fan mass flow changes; booster inlet re-check.", root=repo)
    decide(cr_id, approve=True, note="Accepted for concept study", root=repo)
    assert load_cr(cr_id, root=repo)["status"] == "approved"

    revisions = apply(cr_id, root=repo)

    cr = load_cr(cr_id, root=repo)
    assert cr["status"] == "applied"
    assert revisions == {"M1": "rev002"} == cr["applied_revisions"]
    assert active_revision("M1", root=repo) == "rev002"
    blade = next(p for p in bom(repo)["parts"] if p["id"] == "M1.1.1")
    assert blade["qty"] == {"value": 22, "unit": "ea", "tag": "T"}
    manifest = yaml.safe_load(
        (repo / "engine" / "M1_inlet_fan" / "records" / "rev002" / "manifest.yaml").read_text(encoding="utf-8")
    )
    assert manifest["change_request"] == "CR-001"


def test_history_grows(repo):
    cr_id = new_cr(repo)
    set_impact(cr_id, ["M1"], "Local change", root=repo)
    assert [h["to"] for h in load_cr(cr_id, root=repo)["history"]] == ["open"]

    decide(cr_id, approve=True, note="ok", root=repo)
    apply(cr_id, root=repo)

    history = load_cr(cr_id, root=repo)["history"]
    assert [(h["from"], h["to"]) for h in history] == [(None, "open"), ("open", "approved"), ("approved", "applied")]


def test_reject_blocks_apply(repo):
    cr_id = new_cr(repo)
    decide(cr_id, approve=False, note="Not needed", root=repo)

    with pytest.raises(CRError, match="only approved"):
        apply(cr_id, root=repo)
    with pytest.raises(CRError, match="already decided"):
        decide(cr_id, approve=True, note="changed my mind", root=repo)

    assert load_cr(cr_id, root=repo)["status"] == "rejected"
    assert active_revision("M1", root=repo) == "rev001"


def test_approve_requires_impact(repo):
    cr_id = new_cr(repo)
    with pytest.raises(CRError, match="impact"):
        decide(cr_id, approve=True, note="too early", root=repo)


def test_stale_old_value_blocks_apply(repo):
    stale = dict(BLADE_QTY_CHANGE, old={"value": 30, "unit": "ea", "tag": "KS"})
    cr_id = new_cr(repo, [stale])
    set_impact(cr_id, ["M1"], "", root=repo)
    decide(cr_id, approve=True, note="ok", root=repo)

    with pytest.raises(CRError, match="expected"):
        apply(cr_id, root=repo)
    assert load_cr(cr_id, root=repo)["status"] == "approved"
    assert active_revision("M1", root=repo) == "rev001"


def test_add_part(repo):
    part = {
        "id": "M1.1.3", "name": "Fan Stage 1 Spinner", "parent": "M1.1",
        "qty": {"value": 1, "unit": "ea", "tag": "G"},
        "function": "Guide flow into fan hub", "material": "Al 2014", "status": "draft",
    }
    cr_id = new_cr(repo, [{"module": "M1", "path": "parts[M1.1.3]", "old": None, "new": part}])
    set_impact(cr_id, ["M1"], "New part", root=repo)
    decide(cr_id, approve=True, note="ok", root=repo)
    apply(cr_id, root=repo)
    assert any(p["id"] == "M1.1.3" for p in bom(repo)["parts"])


@pytest.mark.parametrize("changes, to_modules", [
    ([dict(BLADE_QTY_CHANGE, new=22)], ["M1"]),                                   # raw number, no Quantity
    ([dict(BLADE_QTY_CHANGE, new={"value": 22, "unit": "ea"})], ["M1"]),          # Quantity without tag
    ([dict(BLADE_QTY_CHANGE, path="parts/M1.1.1/qty")], ["M1"]),                  # bad path syntax
    ([BLADE_QTY_CHANGE], ["M3"]),                                                 # change module not in to_modules
    ([], ["M1"]),                                                                 # no changes
])
def test_invalid_cr_rejected(repo, changes, to_modules):
    with pytest.raises(CRError):
        create_cr("M2", to_modules, "bad", changes, root=repo)
    assert not list((repo / "engine" / "M0_engine" / "requests").glob("CR-*.yaml"))


def test_tampered_cr_file_rejected(repo):
    cr_id = new_cr(repo)
    path = repo / "engine" / "M0_engine" / "requests" / f"{cr_id}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["status"] = "applied"  # applied without decision or applied_revisions
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n")
    with pytest.raises(CRError):
        load_cr(cr_id, root=repo)
