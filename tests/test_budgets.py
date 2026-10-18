import shutil
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from core.budgets import BudgetError, check_budget, load_icd
from core.requests import load_cr
from engine.M0_engine.analysis.cycle import load_inputs, uncertainty_band, validation_velocity_ratio
from engine.M0_engine.analysis.icd import MODULES, STATIONS, build_icd
from engine.M0_engine.analysis.integration import integration_check

ROOT = Path(__file__).resolve().parents[1]
NO_RECORDS = shutil.ignore_patterns("rev[0-9][0-9][0-9]", "concept[0-9][0-9][0-9]", "CR-*.yaml")


@pytest.fixture(scope="module")
def icd():
    return load_icd()


@pytest.fixture
def repo(tmp_path) -> Path:
    """Temp copy of engine/ for CR drafts; real folders are never touched."""
    shutil.copytree(ROOT / "engine", tmp_path / "engine", ignore=NO_RECORDS)
    return tmp_path


def budget_value(icd, module, item):
    return icd["modules"][module]["budget"][item]["value"]


# --- ICD ------------------------------------------------------------------------------

def test_icd_is_generated_from_its_revision(icd):
    rebuilt = yaml.safe_load(yaml.safe_dump(build_icd(icd["source"]["revision"]), sort_keys=False))
    assert rebuilt == icd


def test_upstream_module_owns_its_exit_stations(icd):
    for module, (_, _, exits) in MODULES.items():
        for s in exits:
            assert icd["stations"][s]["owner"] == module
    for itf in icd["interfaces"]:
        assert itf["from"] == STATIONS[itf["station"]][0]
        assert {itf[q]["tag"] for q in ("Tt", "Pt", "W", "FAR")} == {"H"}


def test_secondary_air_budget_matches_cycle(icd):
    flows = {f["name"]: f for f in icd["secondary_air"]["flows"]}
    assert [flows[n]["return"] for n in ("ngv_cooling", "hpt_rotor_cooling", "interstage_leak")] == ["41", "44", "45"]
    W25 = icd["stations"]["25"]["W"]["value"]
    for name, item in (("ngv_cooling", "ngv"), ("hpt_rotor_cooling", "hpt_rotor"), ("interstage_leak", "leak")):
        assert flows[name]["W"]["value"] == pytest.approx(budget_value(icd, "M9", item) * W25, rel=1e-5)


# --- budget check ---------------------------------------------------------------------

def test_check_budget_pass_fail_info(icd):
    eta = budget_value(icd, "M3", "eta_hpc")
    T3 = budget_value(icd, "M3", "T3")
    rows = {r["item"]: r for r in check_budget("M3", {"eta_hpc": eta - 0.004, "T3": T3 + 12.0, "power": 1.0})}
    assert rows["eta_hpc"]["result"] == "pass"   # within 0.005 absolute
    assert rows["T3"]["result"] == "fail"        # beyond 10 K
    assert rows["power"]["result"] == "info"
    pr = budget_value(icd, "M3", "hpc_pr")
    assert check_budget("M3", {"hpc_pr": pr * 1.011})[0]["result"] == "fail"  # beyond 1 % relative


def test_check_budget_rejects_unknown_items():
    with pytest.raises(BudgetError):
        check_budget("M3", {"eta_hpt": 0.9})


# --- integration: three paths -----------------------------------------------------------

def test_integration_within_budget_passes_without_cr(icd, repo):
    achieved = {"eta_hpc": budget_value(icd, "M3", "eta_hpc"), "hpc_pr": budget_value(icd, "M3", "hpc_pr")}
    res = integration_check("M3", achieved, cr_root=repo)
    assert all(r["result"] == "pass" for r in res["budget"])
    assert res["passed"] and res["cr"] is None


def test_integration_budget_miss_absorbed_by_cycle(icd, repo):
    res = integration_check("M3", {"eta_hpc": budget_value(icd, "M3", "eta_hpc") - 0.008}, cr_root=repo)
    assert res["budget"][0]["result"] == "fail"
    assert res["passed"] and res["cr"] is None
    assert not list((repo / "engine" / "M0_engine" / "requests").glob("CR-*.yaml"))


def test_integration_out_of_tolerance_drafts_open_cr(icd, repo):
    eta = budget_value(icd, "M3", "eta_hpc")
    res = integration_check("M3", {"eta_hpc": eta - 0.03}, cr_root=repo)
    assert not res["passed"]
    assert {m["name"] for m in res["metrics"] if m["result"] == "fail"} >= {"thrust"}
    cr = load_cr(res["cr"], root=repo)
    assert (cr["status"], cr["from_module"], cr["to_modules"]) == ("open", "M3", ["M0"])
    assert cr["applied_revisions"] is None
    assert cr["changes"][0]["path"] == "icd_M3_eta_hpc"
    assert cr["changes"][0]["new"]["value"] == pytest.approx(eta - 0.03)
    assert not list((ROOT / "engine" / "M0_engine" / "requests").glob("CR-*.yaml"))  # real folder untouched


# --- uncertainty band -----------------------------------------------------------------

def test_uncertainty_band_groups_solve():
    p, t, initial, raw, refs = load_inputs()
    vr = validation_velocity_ratio(p, refs, initial, 1e-9)
    rows = {r["group"]: r for r in uncertainty_band(p, replace(t, velocity_ratio=vr), initial, raw, 1e-9)}
    assert all(r["solvable"] for r in rows.values())
    assert rows["uniform"]["delta_eta"] == pytest.approx(0.01713, abs=1e-4)
    assert rows["compressors"]["T4_K"] < rows["uniform"]["T4_K"] < rows["turbines"]["T4_K"]
