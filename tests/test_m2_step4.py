"""Tests for M2 step 4 (#68 spanwise normalisation, #64 design levers, axial Mach sensitivity, M3 interface).

Replaces these tests that no longer hold after step 4 (baseline changed by rule, not by tuning):
- tests/test_m2_step2.py::test_constant_hub_and_axial_mach -> test_constant_tip_and_axial_mach
- tests/test_m2_step3.py::test_free_vortex_option_reproduces_mean_section -> test_free_vortex_unaffected_by_normalisation
- tests/test_m2_step3.py::test_closure_reported -> test_closure_ratios_are_one
- tests/test_m2_step3.py::test_rotor_tip_df_known_violation[1] (XPASS) and ::test_stage3_rotor_hub_known_violation
  (XPASS) -> test_remaining_df_violations and test_rotor_tip_df_known_violation (stages 2, 3)
Numbers below were printed by analysis/sensitivity_64.py and analysis/booster_meanline.py.
"""

from pathlib import Path

import pytest

from core.util import read_yaml
from engine.M2_booster.analysis import a1_validation, booster_meanline as bm
from engine.M2_booster.analysis import sensitivity_64 as s64
from engine.M2_booster.analysis import stage_aero as sa
from engine.M2_booster.geometry import flowpath

M2 = Path(__file__).resolve().parents[1] / "engine" / "M2_booster"
AERO_RULES = M2 / "rules" / "aero_method.md"
A1_FILE = M2 / "analysis" / "a1_validation.yaml"


@pytest.fixture(scope="module")
def recorded():
    return read_yaml(bm.OUT_FILE)


@pytest.fixture(scope="module")
def icd():
    return s64.read_icd("M2 proposed test")


@pytest.fixture(scope="module")
def study(icd):
    return s64.study(icd=icd, grid=False)


def checks(data, name, **match):
    return [r for r in data["rule_checks"] if r["check"] == name and all(r[k] == v for k, v in match.items())]


# --- rules written before the run ------------------------------------------------------

def test_normalisation_and_lever_rules_in_aero_method():
    text = AERO_RULES.read_text(encoding="utf-8")
    assert "### Spanwise normalisation (#68) [step 4, written before the step 4 runs]" in text
    assert "### Design levers for R-AM2.2 (step 4, #64) [rationale written before the step 4 runs]" in text
    for lever in ("L1 tip work ratio", "L2 constant tip radius", "L3 rotor chord x 1.1", "L4 work split"):
        assert lever in text
    assert "**no blockage**" in text
    p = read_yaml(bm.PARAMS_FILE)
    assert (bm.p(p, "df_limit_rotor_tip"), bm.p(p, "df_limit_other"), bm.p(p, "stage_count")) == (0.45, 0.58, 3)
    assert bm.rotor_counts() == [74, 78, 74]


# --- normalisation (#68) ----------------------------------------------------------------

def test_closure_ratios_are_one(recorded):
    for st in bm.run()["stages"]:
        assert abs(st["closure_rotor_exit"]["mass_flow_ratio"] - 1) <= 1e-6
        assert abs(st["closure_rotor_exit"]["work_ratio"] - 1) <= 1e-6
        assert abs(st["closure_stator_exit"]["mass_flow_ratio"] - 1) <= 1e-6
    for s in recorded["stages"]:
        c = s["spanwise_closure"]
        for k in ("rotor_te_mass_flow_ratio", "rotor_mass_averaged_work_ratio", "stator_te_mass_flow_ratio"):
            assert abs(c[k] - 1) <= 1e-6


def test_normalised_shapes_unit():
    pl = sa.Plane(300.0, 1e5, 0.3, 0.43, 120.0, 10.0)
    vx, g = sa.normalised_shapes(pl, (0.9, 1.0, 0.95), (1.07, 1.0, 1.11))
    c = sa.simpson_closure(sa.with_profile(pl, vx), g)
    assert c["mass_flow_ratio"] == pytest.approx(1.0, abs=1e-12)
    assert c["work_ratio"] == pytest.approx(1.0, abs=1e-12)


def test_free_vortex_unaffected_by_normalisation(icd):
    params = read_yaml(bm.PARAMS_FILE)
    fv_norm = s64.run_variant(icd, params, spanwise_distribution="free_vortex")
    fv_raw = s64.run_variant(icd, params, spanwise_distribution="free_vortex", spanwise_normalisation="none")
    for a, b in zip(fv_norm["stages"], fv_raw["stages"]):
        for row in ("rotor", "stator"):
            for sec in sa.SECTIONS:
                assert a[row][sec]["DF"] == pytest.approx(b[row][sec]["DF"], abs=1e-12)


def test_step3_rule_closure_still_fails_icd(study):
    """Info: the old (un-normalised) rule gives 0.973 / 1.030 and fails the ICD W25 and pr_booster tolerance."""
    rows = {r["item"]: r["result"] for r in study["closure_step3_rule"]["rows"]}
    assert rows == {"W25": "fail", "pr_booster": "fail", "T25": "pass"}
    assert all(r["result"] == "pass" for r in study["closure"]["rows"])


def test_a1_still_passes_and_reproducible():
    a1 = a1_validation.run()
    assert a1["passed"]
    assert a1_validation.to_yaml(a1) == read_yaml(A1_FILE)


# --- levers (#64) -----------------------------------------------------------------------

def test_lever_sequence(study):
    seq = study["sequence"]
    assert [(r["lever"], r["applied"], r["before"], r["n_df"]) for r in seq[:-1]] == [
        ("normalised step 3 baseline", True, 3, 3),
        ("L1 tip work ratio k = 0", False, 3, 3),
        ("L2 constant tip radius", True, 3, 2),
        ("L3 rotor chord x 1.1", False, 2, 2),
        ("L4 equal stage PR kept", False, 2, 2),
    ]
    params = read_yaml(bm.PARAMS_FILE)
    assert seq[-1]["values"] == {k: bm.p(params, k) for k in seq[-1]["values"]}


def test_normalised_one_lever_baseline(study):
    base = next(r for r in study["rows"] if r["lever"] == "baseline (normalised)")
    assert base["df_fail"] == ["1Rt", "2Rt", "3Rt"]
    assert base["z_stator"] == [31, 39, 49]
    assert all(r["icd"]["ok"] for r in study["rows"])


def test_meanline_reproducible(recorded):
    ref = read_yaml(bm.REF_FILE)
    a1 = a1_validation.run(ref)
    res = bm.run()
    assert bm.to_yaml(res, a1, bm.rule_checks(res, ref, a1)) == recorded


def test_constant_tip_and_axial_mach(recorded):
    mach = recorded["inputs"]["axial_mach_station21"]["value"]
    assert recorded["inputs"]["axial_mach_booster"]["value"] == mach
    for s in recorded["stages"]:
        for name in ("rotor_le", "rotor_te", "stator_te"):
            plane = s["planes"][name]
            assert plane["r_tip"] == recorded["station_21"]["r_tip"]
            assert plane["Mx"] == pytest.approx(mach, abs=1e-4)


def test_remaining_df_violations(recorded):
    fails = {(r["stage"], r["row"], r["section"]) for r in checks(recorded, "R-AM2.2 DF") if r["result"] == "fail"}
    assert fails == {(2, "rotor", "tip"), (3, "rotor", "tip")}
    for r in checks(recorded, "tip solidity in TP-1523 Table 1 range"):
        assert r["result"] == "pass", r
    assert [s["stator_vanes"]["value"] for s in recorded["stages"]] == [31, 39, 49]
    assert all(r["result"] in ("pass", "info") for r in recorded["budget_check"])


@pytest.mark.parametrize("stage", [2, 3])
@pytest.mark.xfail(strict=True, reason="#64: rotor tip D > 0.45 (R-AM2.2) after step 4; known deviation, not tuned")
def test_rotor_tip_df_known_violation(recorded, stage):
    assert checks(recorded, "R-AM2.2 DF", stage=stage, row="rotor", section="tip")[0]["result"] == "pass"


# --- axial Mach sensitivity -------------------------------------------------------------

def test_axial_mach_sensitivity_keeps_icd(study):
    m = {r["variant"]: r for r in study["mach_final"]}
    assert all(r["icd"]["ok"] for r in m.values())
    base, lo, hi = (m[f"final, axial Mach x {k}"] for k in (1.0, 0.9, 1.1))
    assert lo["rotor_df"][0][0] > base["rotor_df"][0][0] > hi["rotor_df"][0][0]
    assert lo["n_df"] == 4 and hi["n_df"] == 2 and hi["sigma_out"] == ["1S", "2S", "3S"]


# --- M3 interface -----------------------------------------------------------------------

def test_m3_interface_reproducible_and_station21_untouched(recorded):
    data = flowpath.build()
    assert data == read_yaml(flowpath.OUT_FILE)
    s25 = data["interfaces"]["M3_station_25"]
    assert s25["r_hub_m"] == pytest.approx(recorded["station_24"]["r_hub"], abs=1e-5)
    assert s25["r_tip_m"] == pytest.approx(recorded["station_24"]["r_tip"], abs=1e-5)
    s21 = read_yaml(bm.FLOWPATH_M1)["interfaces"]["M2_station_21"]
    assert data["planes"][0]["r_hub_m"] == pytest.approx(s21["r_hub_m"], abs=1e-6)
    assert data["planes"][0]["r_tip_m"] == pytest.approx(s21["r_tip_m"], abs=1e-6)
