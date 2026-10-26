"""M1 fan design (analysis/fan_design.py -> analysis/results.yaml), recorded as M1 rev004.

Step 4d redesign: radial equilibrium and full loss model ON, R-AM.9 limits, ADR-015 budget-efficiency branch.
Reads the generated results only; the full re-run is covered by core.records.verify/reproducible.
"""

import math

from core.budgets import read_icd
from core.records import ROOT, module_dir
from core.util import read_yaml

RESULTS = module_dir("M1", ROOT) / "analysis" / "results.yaml"


def results():
    return read_yaml(RESULTS)


def budget():
    return read_icd("M1 test")["modules"]["M1"]["budget"]


def test_annulus_matches_icd_fan_face_area():
    assert results()["annulus"]["fan_face_area_check"] == "pass"


def test_each_stream_meets_its_pressure_ratio():
    b, s = budget(), results()["summary"]
    assert abs(s["outer"]["Pt_ratio_meanline"] / b["FPR"]["value"] - 1) <= 1e-4
    assert abs(s["inner"]["Pt_ratio_meanline"] / b["pr_fan_inner"]["value"] - 1) <= 1e-4


def test_design_converged_on_physical_branch():
    r = results()
    assert len(r["tubes"]) == 9
    assert r["convergence"]["converged"]
    assert all(not t["notes"] for t in r["tubes"])  # no tube at exit choke


def test_efficiencies_are_budget_values_adr015():
    b, a = budget(), results()["achieved"]
    assert a["eta_fan_outer"] == b["eta_fan_outer"]["value"]
    assert a["eta_fan_inner"] == b["eta_fan_inner"]["value"]


def test_exit_temperatures_from_target_pr_and_budget_eta():
    r, b = results(), budget()
    k = 1.4 / 0.4
    tt = r["inputs"]["Tt2_K"]
    t13 = tt * (1 + (b["FPR"]["value"] ** (1 / k) - 1) / b["eta_fan_outer"]["value"])
    assert math.isclose(r["achieved"]["T13"], t13, abs_tol=1e-3)


def test_ram9_failures_are_reported():
    r = results()
    failed = [t["name"] for t in r["tubes"] if "fail" in (t["R_AM9"]["DF_check"], t["R_AM9"]["solidity_check"])]
    assert failed == r["summary"]["R_AM9_failed_tubes"]
    assert all(t["solidity"] >= t["R_AM9"]["solidity_floor"] - 1e-4 for t in r["tubes"])


def test_core_mass_flow_is_w21():
    w21 = budget()["W21"]["value"]
    inner = sum(t["mass_flow_kg_s"] for t in results()["tubes"] if t["stream"] == "inner")
    assert abs(inner / w21 - 1) <= 1e-6


def test_root_stress_has_margin():
    assert results()["mechanical"]["margin"] > 0


def test_budget_rows_cover_achieved_items():
    r = results()
    assert [row["item"] for row in r["budget_check"]] == list(r["achieved"])
