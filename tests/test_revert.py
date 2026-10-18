"""Full-state revert and revert CRs (core.records.revert, core.requests revert CRs) on a temporary copy."""

import shutil
from pathlib import Path

import pytest

from core.records import (
    RecordError,
    active_concept,
    active_revision,
    create_revision,
    read_revision,
    revert,
)
from core.requests import CRError, apply, create_cr, create_revert_cr, decide, load_cr
from core.util import read_yaml, write_yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo(tmp_path) -> Path:
    """Temp copy of engine/ (records included) and the gas data; real folders are never touched."""
    shutil.copytree(ROOT / "engine", tmp_path / "engine",
                    ignore=shutil.ignore_patterns("__pycache__", "CR-*.yaml", "sources"))
    shutil.copytree(ROOT / "tools" / "data", tmp_path / "tools" / "data")
    return tmp_path


def m0(repo: Path) -> Path:
    return repo / "engine" / "M0_engine"


def test_revert_restores_params_results_and_icd(repo):
    out = revert("M0", "rev004", root=repo)
    assert active_revision("M0", root=repo) == "rev004"
    assert read_yaml(m0(repo) / "analysis" / "cycle_params.yaml") == read_revision("M0", "rev004", "params.yaml", repo)
    assert read_yaml(m0(repo) / "analysis" / "results.yaml") == read_revision("M0", "rev004", "results.yaml", repo)
    icd = read_yaml(m0(repo) / "rules" / "icd.yaml")
    assert icd["source"]["revision"] == "rev004" and "recorded operating point" in icd["source"]["method"]
    recorded_W2 = read_revision("M0", "rev004", "results.yaml", repo)["calibration"]["W2"]["value"]
    assert icd["stations"]["2"]["W"]["value"] == pytest.approx(recorded_W2, rel=1e-5)
    assert any("güncel kod" in w for w in out["warnings"])  # the current solver cannot re-run rev004


def test_revert_to_latest_reruns_identically(repo):
    revert("M0", "rev005", root=repo)
    out = revert("M0", "rev007", root=repo)
    assert out["warnings"] == [] and out["results_diff"] is None
    assert read_yaml(m0(repo) / "rules" / "icd.yaml")["source"] == read_yaml(ROOT / "engine" / "M0_engine" / "rules" / "icd.yaml")["source"]


def test_rev005_verification_reports_result_difference(repo):
    out = revert("M0", "rev005", root=repo)
    assert any("kayıtlı sonuç ile güncel kod sonucu farklı" in w for w in out["warnings"])
    keys = {c["key"] for c in out["results_diff"]}
    assert any(k.startswith("assumptions") for k in keys)  # added after rev005; numbers unchanged
    assert read_yaml(m0(repo) / "analysis" / "results.yaml") == read_revision("M0", "rev005", "results.yaml", repo)


def test_rev001_restores_record_and_warns(repo):
    before_icd = read_yaml(m0(repo) / "rules" / "icd.yaml")
    out = revert("M0", "rev001", root=repo)
    assert read_yaml(m0(repo) / "analysis" / "results.yaml") == read_revision("M0", "rev001", "results.yaml", repo)
    assert any("güncel kod kayıtlı params ile çalışmadı" in w for w in out["warnings"])
    assert any("icd.yaml rev001 kaydından üretilemedi" in w for w in out["warnings"])
    assert read_yaml(m0(repo) / "rules" / "icd.yaml") == before_icd


def test_revert_refuses_unrecorded_params(repo):
    path = m0(repo) / "analysis" / "cycle_params.yaml"
    params = read_yaml(path)
    params["components"]["eta_hpc"]["value"] = 0.8
    write_yaml(path, params)
    with pytest.raises(RecordError, match="cycle_params.yaml"):
        revert("M0", "rev005", root=repo)
    assert active_revision("M0", root=repo) == "rev007"


def test_revert_cr_lists_icd_affected_modules_and_applies(repo):
    cr_id = create_revert_cr({"M0": "rev004"}, "test", root=repo)
    cr = load_cr(cr_id, root=repo)
    assert cr["impact"]["by"] == "M0 revert"
    assert set(cr["impact"]["affected_modules"]) >= {"M0", "M1", "M3", "M5"}  # not started, listed anyway
    assert cr["changes"] == [{"type": "revert", "module": "M0", "from": "rev007", "to": "rev004"}]
    decide(cr_id, True, "back to rev004", root=repo, decided_by="user (UI)")
    assert apply(cr_id, root=repo) == {"M0": "rev004"}
    cr = load_cr(cr_id, root=repo)
    assert cr["status"] == "applied" and cr["apply_warnings"]
    assert active_revision("M0", root=repo) == "rev004"


def test_stale_revert_cr_is_refused(repo):
    cr_id = create_revert_cr({"M0": "rev005"}, "test", root=repo)
    decide(cr_id, True, "ok", root=repo)
    revert("M0", "rev006", root=repo)
    with pytest.raises(CRError, match="expects rev007"):
        apply(cr_id, root=repo)


def test_concept_revert_cr(repo):
    cr_id = create_revert_cr({"M0": "rev005"}, "concept back", root=repo, concept="concept001")
    decide(cr_id, True, "back to concept001", root=repo)
    assert apply(cr_id, root=repo) == {"M0": "rev005"}
    assert active_concept(root=repo) == "concept001" and active_revision("M0", root=repo) == "rev005"
    assert read_yaml(m0(repo) / "rules" / "icd.yaml")["source"]["revision"] == "rev005"
    with pytest.raises(CRError, match="pins"):
        create_revert_cr({"M0": "rev004"}, "wrong", root=repo, concept="concept001")


def test_revert_changes_cannot_mix_with_other_changes(repo):
    change = {"type": "revert", "module": "M0", "from": "rev007", "to": "rev005"}
    bom = {"module": "M0", "path": "module_name", "old": "Engine", "new": "Engine X"}
    with pytest.raises(CRError, match="only revert"):
        create_cr("M0", ["M0"], "mixed", [change, bom], root=repo)


def test_moved_value_needs_review_mapping(repo):
    params = read_revision("M0", "rev007", "params.yaml", repo)
    params["checks"]["w2_band"] = params["checks"].pop("w2_tolerance")
    results = read_revision("M0", "rev007", "results.yaml", repo)
    with pytest.raises(RecordError, match="REVIEW.md"):
        create_revision("M0", "move", "test", params=params, results=results, root=repo, kind="maintenance")
    review = m0(repo) / "records" / "REVIEW.md"
    review.write_text(review.read_text(encoding="utf-8")
                      + "\n- checks.w2_tolerance.value -> checks.w2_band.value\n", encoding="utf-8")
    assert create_revision("M0", "move", "test", params=params, results=results, root=repo,
                           kind="maintenance") == "rev008"
