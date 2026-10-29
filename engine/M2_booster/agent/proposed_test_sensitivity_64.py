"""Proposed tests for the #64 sensitivity study and the #68 closure check (not wired into tests/; M0 decides).

Move to tests/test_m2_sensitivity_64.py if accepted. Uses only code outputs; the numbers below were printed by
engine/M2_booster/analysis/sensitivity_64.py (rounded as in the learning note duyarlilik_64.md).
"""

import pytest

from core.util import read_yaml
from engine.M2_booster.analysis import booster_meanline as bm
from engine.M2_booster.analysis import sensitivity_64 as s64

RESULTS = bm.OUT_FILE


@pytest.fixture(scope="module")
def study():
    return s64.study(grid=True)


def rows_by_variant(study):
    return {(r["lever"], r["variant"]): r for r in study["rows"]}


def test_study_does_not_write_files():
    before = RESULTS.read_bytes(), bm.PARAMS_FILE.read_bytes()
    s64.study(grid=False)
    assert (RESULTS.read_bytes(), bm.PARAMS_FILE.read_bytes()) == before


def test_baseline_reproduces_meanline_results(study):
    rec = read_yaml(RESULTS)
    base = rows_by_variant(study)[("baseline", "-")]
    for i, st in enumerate(rec["stages"]):
        for name, key in (("rotor_sections", "rotor_df"), ("stator_sections", "stator_df")):
            cols = st[name]["columns"]
            df = [dict(zip(cols, row))["DF"] for row in st[name]["rows"]]
            assert base[key][i] == pytest.approx(df, abs=1e-4)
    assert base["df_fail"] == ["1Rt", "2Rt", "3Rh", "3Rt"]


def test_constant_hub_variant_is_the_baseline(study):
    assert rows_by_variant(study)[("baseline", "-")]["hub_tip_le"][0] == pytest.approx(0.697, abs=1e-3)


def test_no_single_lever_or_grid_combination_closes_all_df(study):
    assert all(r["n_df"] >= 1 for r in study["rows"])
    assert len(study["grid"]) == 108
    assert min(r["n_df"] for r in study["grid"]) == 1
    assert not any(r["n_df"] == 0 for r in study["grid"])


def test_stage3_rotor_tip_is_the_last_violation(study):
    best = rows_by_variant(study)[("best grid + normalisation", "tip, equal PR, chord x 1.1, k = 0")]
    assert best["df_fail"] == ["3Rt"]
    assert best["rotor_df"][2][2] > 0.45


def test_closure_exceeds_icd_flow_and_pr_tolerance(study):
    rows = {r["item"]: r for r in study["closure"]["rows"]}
    assert rows["W25"]["result"] == "fail"
    assert rows["pr_booster"]["result"] == "fail"
    assert rows["T25"]["result"] == "pass"
    for r in study["closure"]["ratios"]:
        assert r["mass_flow_ratio"] == pytest.approx(0.973, abs=1e-3)
        assert r["work_ratio"] == pytest.approx(1.030, abs=1e-3)


def test_normalised_profile_closes_to_one():
    icd = s64.read_icd("M2 proposed test")
    res = s64.run_variant(icd, read_yaml(bm.PARAMS_FILE), normalise=True)
    for st in res["stages"]:
        assert st["closure_rotor_exit"]["mass_flow_ratio"] == pytest.approx(1.0, abs=1e-12)
        assert st["closure_rotor_exit"]["work_ratio"] == pytest.approx(1.0, abs=1e-12)
        assert st["closure_stator_exit"]["mass_flow_ratio"] == pytest.approx(1.0, abs=1e-12)
