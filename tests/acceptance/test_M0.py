"""M0 acceptance tests (docs/architecture.md section 10): rule checks, calculation validation,
parameter change, revert and conflict. Results: engine/M0_engine/analysis/acceptance_M0.md."""

import copy
import hashlib
import shutil
from pathlib import Path

import pytest

from core.records import active_revision, revert, revision_ids, verify
from core.requests import CRError, apply, decide, load_cr, set_impact
from core.util import dump_yaml, read_yaml
from engine.M0_engine.analysis import calc
from engine.M0_engine.analysis.cycle import calibrate, load_inputs, solve_rated, validation_case, validation_rows
from engine.M0_engine.analysis.integration import integration_check

ROOT = Path(__file__).resolve().parents[2]
M0 = ROOT / "engine" / "M0_engine"
TOL = 1e-9


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def repo(tmp_path) -> Path:
    """Temp copy of engine/ (records included) and the gas data; real folders are never touched."""
    shutil.copytree(ROOT / "engine", tmp_path / "engine",
                    ignore=shutil.ignore_patterns("__pycache__", "CR-*.yaml", "sources"))
    shutil.copytree(ROOT / "tools" / "data", tmp_path / "tools" / "data")
    return tmp_path


@pytest.fixture(scope="module")
def rated():
    p, t, initial, raw, refs = load_inputs()
    return solve_rated(p, t, initial, raw, refs, TOL)


# --- rule checks ------------------------------------------------------------------------

def test_rule_checks_run_and_pass(rated):
    results, r, *_ = rated
    assert r is not None and results["hard_checks_passed"]
    assert {c["result"] for c in results["checks"]} <= {"pass", "info"}
    assert results == read_yaml(M0 / "analysis" / "results.yaml")  # derived file matches its source


# --- calculation validation ------------------------------------------------------------------

def test_girao_validation_accepted():
    p, _, initial, raw, refs = load_inputs()
    pv, tv = validation_case(p, refs)
    r, _ = calibrate(pv, tv, initial, tol=TOL)
    failing = {row["item"] for row in validation_rows(r, raw, refs) if row["result"] == "fail"}
    assert failing == {"P5"}  # accepted expected failure (analysis/validation_girao.md)


# --- parameter change ----------------------------------------------------------------------

def test_parameter_change_propagates_without_writing(rated):
    before = sha(M0 / "analysis" / "results.yaml")
    raw = copy.deepcopy(read_yaml(M0 / "analysis" / "cycle_params.yaml"))
    raw["components"]["bypass_duct"]["value"] = 0.970
    out = calc.recalculate(ROOT, {"cycle_params.yaml": raw})
    base = rated[0]
    assert out["results"]["performance"]["thrust"]["value"] == pytest.approx(121.43, rel=1e-6)
    assert out["results"]["calibration"]["W2"]["value"] != base["calibration"]["W2"]["value"]
    assert out["results"]["hard_checks_passed"]
    assert sha(M0 / "analysis" / "results.yaml") == before


# --- revert ---------------------------------------------------------------------------------

def test_revert_and_rerun_reproduces_record(repo):
    m0 = repo / "engine" / "M0_engine"
    revert("M0", "rev004", root=repo)
    assert active_revision("M0", root=repo) == "rev004"
    latest = revision_ids("M0", repo)[-1]  # the current code reproduces the latest record
    revert("M0", latest, root=repo)
    rev = active_revision("M0", root=repo)
    assert rev == latest and verify("M0", rev, root=repo) == []
    p, t, initial, raw, refs = load_inputs(m0 / "records" / rev / "params.yaml", repo)
    results, *_ = solve_rated(p, t, initial, raw, refs, TOL)
    rerun = hashlib.sha256(dump_yaml(results).encode("utf-8")).hexdigest()
    assert rerun == sha(m0 / "records" / rev / "results.yaml")


# --- conflict ---------------------------------------------------------------------------------

def test_conflict_reject_then_approve(repo):
    m0 = repo / "engine" / "M0_engine"
    tracked = [m0 / "analysis" / "cycle_params.yaml", m0 / "analysis" / "results.yaml",
               m0 / "rules" / "icd.yaml", m0 / "records" / "ACTIVE"]
    before = {f: sha(f) for f in tracked}
    eta = read_yaml(m0 / "rules" / "icd.yaml")["modules"]["M3"]["budget"]["eta_hpc"]["value"]
    achieved = {"eta_hpc": eta - 0.03}

    # option (b): module redesign -> CR rejected, nothing changes
    cr1 = integration_check("M3", achieved, cr_root=repo)["cr"]
    with pytest.raises(CRError):
        decide(cr1, approve=False, note="redesign", option="a", root=repo)  # option/decision mismatch
    decide(cr1, approve=False, note="M3 redesign", option="b", root=repo)
    assert load_cr(cr1, root=repo)["status"] == "rejected"
    assert {f: sha(f) for f in tracked} == before

    # option (a): accept the achieved value in M0 params -> new revision, regenerated derived files
    cr2 = integration_check("M3", achieved, cr_root=repo)["cr"]
    set_impact(cr2, ["M0", "M3"], "HPC efficiency fixed at the achieved value; other efficiencies re-balance.",
               root=repo)
    decide(cr2, approve=True, note="accept achieved HPC efficiency", option="a", root=repo)
    new = f"rev{int(revision_ids('M0', repo)[-1][3:]) + 1:03d}"
    revisions = apply(cr2, root=repo)
    assert revisions == {"M0": new} and active_revision("M0", root=repo) == new
    params = read_yaml(m0 / "analysis" / "cycle_params.yaml")
    assert params["components"]["eta_hpc"]["value"] == pytest.approx(eta - 0.03)
    assert params["rated_case"]["delta_eta_exclude"] == ["eta_hpc"]
    icd = read_yaml(m0 / "rules" / "icd.yaml")
    assert icd["source"]["revision"] == new
    assert icd["modules"]["M3"]["budget"]["eta_hpc"]["value"] == pytest.approx(eta - 0.03, abs=1e-6)
    assert "eta_hpc" not in icd["integration"]["operating_point"]["delta_eta_group"]
    assert read_yaml(m0 / "analysis" / "results.yaml") == read_yaml(m0 / "records" / new / "results.yaml")
    assert read_yaml(m0 / "records" / new / "manifest.yaml")["change_request"] == cr2


def test_results_carry_assumptions_and_reference_tags(rated):
    results = rated[0]
    tags = {"K", "KS", "H", "G", "T"}
    for c in results["checks"]:
        ref_tags = c["ref_tag"].values() if isinstance(c["ref_tag"], dict) else [c["ref_tag"]]
        assert set(ref_tags) <= tags
        if isinstance(c["reference"], dict):
            assert set(c["ref_tag"]) == set(c["reference"])
    by_name = {c["name"]: c["ref_tag"] for c in results["checks"]}
    assert by_name["EGT displayed vs TCDS limit"] == "K"
    assert by_name["Fan specific flow W2/A"] == "G"
    assert by_name["Fan choke (HARD)"] == "H"
    paths = {a["path"] for a in results["assumptions"]}
    assert {"components.LHV", "rated_case.similarity", "geometry.fan_diameter"} <= paths
    assert not any(p.startswith(("checks.", "calibration.")) for p in paths)
