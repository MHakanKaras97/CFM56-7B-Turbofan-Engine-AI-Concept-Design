"""Proposed tests for M2 step 3 (#63: spanwise distribution, A-1 with the rig's tabulated section inputs,
booster TP-1523 shape transfer [T]). Moved to tests/ by M0; replaces the step 2 assertions that no longer hold.

Run: .venv/Scripts/python -m pytest -q --tb=short tests/test_m2_step3.py
"""

from pathlib import Path

import pytest

from core.util import read_yaml
from engine.M2_booster.analysis import a1_validation, booster_meanline as bm
from engine.M2_booster.analysis import stage_aero as sa

M2 = Path(__file__).resolve().parents[1] / "engine" / "M2_booster"
A1_FILE = M2 / "analysis" / "a1_validation.yaml"
RESULTS_FILE = M2 / "analysis" / "meanline_results.yaml"
PARAMS_FILE = M2 / "analysis" / "booster_params.yaml"
AERO_RULES = M2 / "rules" / "aero_method.md"


@pytest.fixture(scope="module")
def ref():
    return read_yaml(bm.REF_FILE)


@pytest.fixture(scope="module")
def a1(ref):
    return a1_validation.run(ref)


@pytest.fixture(scope="module")
def results(ref, a1):
    res = bm.run()
    return bm.to_yaml(res, a1, bm.rule_checks(res, ref, a1))


@pytest.fixture(scope="module")
def recorded():
    return read_yaml(RESULTS_FILE)


def checks(data, name, **match):
    return [r for r in data["rule_checks"] if r["check"] == name and all(r[k] == v for k, v in match.items())]


def df(recorded, stage, row, section):
    return checks(recorded, "R-AM2.2 DF", stage=stage, row=row, section=section)[0]


# --- rules text written before the run ------------------------------------------------

def test_spanwise_and_blockage_definitions_in_rules():
    text = AERO_RULES.read_text(encoding="utf-8")
    assert "### Spanwise distribution (hub/mean/tip)" in text
    assert "### Blockage" in text and "**no blockage**" in text
    # pass criteria unchanged
    assert "D at tip/mid/hub within +-0.02 of 0.452 / 0.450 / 0.571" in text
    assert "+-1.5 deg" in text and "within 1 % of 1.257" in text
    assert (a1_validation.TOL_DF, a1_validation.TOL_BETA, a1_validation.TOL_PR) == (0.02, 1.5, 0.01)


# --- A-1 ------------------------------------------------------------------------------

def test_a1_reproduces_recorded_file(a1):
    assert a1_validation.to_yaml(a1) == read_yaml(A1_FILE)


def test_a1_passes_with_tabulated_section_inputs(a1):
    data = read_yaml(A1_FILE)
    assert a1["passed"] and data["result"] == "pass"
    assert data["inputs"]["method"]["value"] == "tabulated_section_inputs"
    for c in data["criteria"]:
        assert c["result"] == "pass" and abs(c["delta"]) <= c["tolerance"], c["item"]


def test_a1_shapes_from_table(ref):
    case = {r["station"]: r for r in a1_validation.table(ref, "a1_case")}
    sh = a1_validation.section_shapes(case)
    assert sh["work"][1] == sh["vx_out"][1] == sh["vx_in"][1] == 1.0
    assert sh["work"][2] == pytest.approx(0.079 / 0.071) and sh["work"][0] == pytest.approx(0.076 / 0.071)
    assert sh["vx_out"][2] == pytest.approx(93.7 / 102.5) and sh["vx_out"][0] == pytest.approx(94.9 / 102.5)


def test_a1_exit_swirl_from_section_work(a1):
    """Euler with w_sec = cp Tt1 (TR_sec - 1) reproduces the tabulated exit swirl within TR rounding (0.0005)."""
    for r in a1["rows"]:
        s, t = r["section"], r["table"]
        tol = 1004.0 * 288.2 * 0.0005 / s["U2"]
        assert s["Vt2"] == pytest.approx(t["vt_out"], abs=tol + 0.05), r["station"]


def test_a1_df_formula_reproduces_table_velocities():
    for s in read_yaml(A1_FILE)["sections"]:
        d = s["df_from_table_velocities"]
        assert d["value"] == pytest.approx(d["table"], abs=0.002), s["station"]


# --- stage_aero ------------------------------------------------------------------------

def test_default_profile_is_free_vortex():
    pl = sa.Plane(300.0, 1e5, 0.2, 0.3, 100.0, 20.0)
    for sec in sa.SECTIONS:
        assert pl.vx_at(sec) == 100.0
        assert pl.vt_at(sec) == pytest.approx(20.0 / pl.radius(sec))
    ex = sa.with_profile(pl, (1, 1, 1), sa.rotor_exit_swirl(sa.with_profile(pl, (1, 1, 1), (0, 0, 0)), pl, 500.0,
                                                            1e4, (1, 1, 1)))
    for sec in sa.SECTIONS:
        assert ex.vt_at(sec) == pytest.approx(1e4 / (500.0 * pl.radius(sec)))


def test_simpson_closure_uniform_is_one():
    pl = sa.Plane(300.0, 1e5, 0.2, 0.3, 100.0, 0.0)
    c = sa.simpson_closure(pl, (1.0, 1.0, 1.0))
    assert c["mass_flow_ratio"] == pytest.approx(1.0) and c["work_ratio"] == pytest.approx(1.0)


# --- booster meanline ------------------------------------------------------------------

def test_meanline_reproducible(results, recorded):
    assert results == recorded


def test_spanwise_choice_is_T_and_read_from_reference(recorded, ref):
    params = read_yaml(PARAMS_FILE)
    assert "vortex" not in params
    assert params["spanwise_distribution"]["value"] == "tp1523_shape"
    assert params["spanwise_distribution"]["tag"] == "T"
    sh = bm.spanwise_shapes(params, ref)
    st = {r["station"]: r["v_out"] for r in a1_validation.table(ref, "stator20_exit")}
    assert sh["stator_exit_vx"] == pytest.approx((st["hub"] / st["mid"], 1.0, st["tip"] / st["mid"]))
    assert recorded["inputs"]["spanwise_distribution"] == {
        "value": "tp1523_shape", "unit": "-", "tag": "T",
        "note": "aero_method.md Spanwise distribution; booster_params.yaml"}


def test_section_values_stay_T(recorded):
    """A-1 passes, but the booster shape is a [T] transfer: section values are not promoted to [H]."""
    assert recorded["validation"]["a1_result"] == "pass"
    for s in recorded["stages"]:
        assert s["rotor_sections"]["tag"] == s["stator_sections"]["tag"] == s["planes"]["tag"] == "T"


def test_free_vortex_option_reproduces_mean_section(recorded):
    """Mean section is the 1-D value in both options (shape ratio 1 at mean)."""
    params = read_yaml(PARAMS_FILE)
    params["spanwise_distribution"] = dict(params["spanwise_distribution"], value="free_vortex")
    fv = bm.run(params=params)
    for s_fv, s_rec in zip(fv["stages"], recorded["stages"]):
        cols = s_rec["rotor_sections"]["columns"]
        mean = dict(zip(cols, s_rec["rotor_sections"]["rows"][1]))
        assert s_fv["rotor"]["mean"]["DF"] == pytest.approx(mean["DF"], abs=1e-4)


def test_closure_reported(recorded):
    for s in recorded["stages"]:
        c = s["spanwise_closure"]
        assert 0.95 < c["rotor_te_mass_flow_ratio"] < 1.0
        assert 1.0 < c["rotor_mass_averaged_work_ratio"] < 1.05


def test_budget_and_annulus_unchanged(recorded):
    assert all(r["result"] in ("pass", "info") for r in recorded["budget_check"])
    mach = recorded["inputs"]["axial_mach_station21"]["value"]
    for s in recorded["stages"]:
        for name in ("rotor_le", "rotor_te", "stator_te"):
            assert s["planes"][name]["Mx"] == pytest.approx(mach, abs=1e-4)
    assert bm.rotor_counts() == [74, 78, 74]


def test_stator_df_within_limit(recorded):
    for r in checks(recorded, "R-AM2.2 DF", row="stator"):
        assert r["result"] == "pass", r


@pytest.mark.parametrize("stage", [1, 2, 3])
@pytest.mark.xfail(strict=True, reason="#64: rotor tip D > 0.45 (R-AM2.2) with the step 3 spanwise shape; not tuned")
def test_rotor_tip_df_known_violation(recorded, stage):
    assert df(recorded, stage, "rotor", "tip")["result"] == "pass"


@pytest.mark.xfail(strict=True, reason="#64: stage 3 rotor hub D > 0.58 (R-AM2.2) with the step 3 spanwise shape")
def test_stage3_rotor_hub_known_violation(recorded):
    assert df(recorded, 3, "rotor", "hub")["result"] == "pass"


def test_other_rotor_hub_mean_within_limit(recorded):
    for r in checks(recorded, "R-AM2.2 DF", row="rotor"):
        if r["section"] != "tip" and not (r["stage"] == 3 and r["section"] == "hub"):
            assert r["result"] == "pass", r


def test_tip_solidity_in_tested_range(recorded):
    for r in checks(recorded, "tip solidity in TP-1523 Table 1 range"):
        assert r["result"] == "pass", r


def test_stator_counts_differ_from_neighbours(recorded):
    zr = [s["rotor_blades"]["value"] for s in recorded["stages"]]
    for i, s in enumerate(recorded["stages"]):
        zs = s["stator_vanes"]["value"]
        assert zs != zr[i] and (i + 1 == len(zr) or zs != zr[i + 1])
        assert s["stator_vanes"]["tag"] == "T"
        assert "not met" not in s["stator_vanes"]["note"]
