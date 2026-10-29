"""Proposed tests for M2 step 2 (A-1 validation run, booster meanline). Moved to tests/ by M0.
Step 3 (#63) superseded the A-1 fail and step-2 rotor DF assertions; they live in tests/test_m2_step3.py.

Run: .venv/Scripts/python -m pytest -q --tb=short tests/test_m2_step2.py
"""

from pathlib import Path

import pytest

from core.budgets import read_icd
from core.util import read_yaml
from engine.M2_booster.analysis import a1_validation, booster_meanline as bm

M2 = Path(__file__).resolve().parents[1] / "engine" / "M2_booster"
A1_FILE = M2 / "analysis" / "a1_validation.yaml"
RESULTS_FILE = M2 / "analysis" / "meanline_results.yaml"


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


# --- A-1 ------------------------------------------------------------------------------

def test_a1_reproduces_recorded_file(a1):
    assert a1_validation.to_yaml(a1) == read_yaml(A1_FILE)


def test_a1_df_formula_reproduces_table_velocities():
    """The DF code itself is right: on the Table 2(b) triangles it gives the table D-FACT within 0.002."""
    for s in read_yaml(A1_FILE)["sections"]:
        d = s["df_from_table_velocities"]
        assert d["value"] == pytest.approx(d["table"], abs=0.002), s["station"]


# --- meanline ---------------------------------------------------------------------------

def test_meanline_reproducible(results, recorded):
    assert results == recorded


def test_results_derive_from_read_icd(recorded):
    icd = read_icd("M2 proposed test")
    st, budget = icd["stations"], icd["modules"]["M2"]["budget"]
    assert recorded["icd_revision"] == icd["source"]["revision"]
    assert recorded["station_21"]["Tt"] == pytest.approx(st["21"]["Tt"]["value"], abs=0.01)
    assert recorded["station_21"]["Pt_kPa"] == pytest.approx(st["21"]["Pt"]["value"], abs=0.001)
    assert recorded["inputs"]["N1"]["value"] == icd["shafts"]["LP"]["speed_refs"]["girao_nominal"]["value"]
    pr = 1.0
    for s in recorded["stages"]:
        pr *= s["pr"]["value"]
    assert pr == pytest.approx(budget["pr_booster"]["value"], rel=1e-4)
    assert all(r["result"] in ("pass", "info") for r in recorded["budget_check"])
    for row in recorded["consistency_vs_icd"]:
        assert abs(row["difference"]) <= 0.01, row["item"]  # ICD values carry 2-3 decimals


def test_station21_annulus_from_m1(recorded):
    s21 = read_yaml(bm.FLOWPATH_M1)["interfaces"]["M2_station_21"]
    assert recorded["station_21"]["r_hub"] == pytest.approx(s21["r_hub_m"], abs=1e-5)
    assert recorded["station_21"]["r_tip"] == pytest.approx(s21["r_tip_m"], abs=1e-5)
    assert recorded["station_21"]["area"] == pytest.approx(s21["area_m2"], rel=1e-4)


# --- rules ------------------------------------------------------------------------------

def test_rotor_counts_are_known_values(recorded):
    """R-AM2.3: rotor counts are fixed inputs [KS] (#52), not derived."""
    assert bm.rotor_counts() == [74, 78, 74]
    assert [s["rotor_blades"]["value"] for s in recorded["stages"]] == bm.rotor_counts()
    assert all(s["rotor_blades"]["tag"] == "KS" for s in recorded["stages"])


def test_stator_counts_differ_from_neighbours(recorded):
    zr = [s["rotor_blades"]["value"] for s in recorded["stages"]]
    for i, s in enumerate(recorded["stages"]):
        zs = s["stator_vanes"]["value"]
        assert zs != zr[i] and (i + 1 == len(zr) or zs != zr[i + 1])
        assert s["stator_vanes"]["tag"] == "T"


def test_chords_from_aspect_ratio(recorded):
    for s in recorded["stages"]:
        pl = s["planes"]
        h_r = (pl["rotor_le"]["r_tip"] - pl["rotor_le"]["r_hub"] + pl["rotor_te"]["r_tip"] - pl["rotor_te"]["r_hub"]) / 2
        h_s = (pl["rotor_te"]["r_tip"] - pl["rotor_te"]["r_hub"] + pl["stator_te"]["r_tip"] - pl["stator_te"]["r_hub"]) / 2
        assert s["rotor_chord"]["value"] == pytest.approx(h_r / 2.0, abs=2e-5)
        assert s["stator_chord"]["value"] == pytest.approx(h_s / 1.2, abs=2e-5)


def test_stator_df_within_limit(recorded):
    for r in checks(recorded, "R-AM2.2 DF", row="stator"):
        assert r["result"] == "pass", r


def test_tip_solidity_in_tested_range(recorded):
    for r in checks(recorded, "tip solidity in TP-1523 Table 1 range"):
        assert r["result"] == "pass", r


@pytest.mark.xfail(strict=True, reason="#57: every booster blade row LE hub/tip is below the rig 0.8")
def test_hub_tip_inside_rig(recorded):
    assert all(r["result"] == "at or above rig" for r in checks(recorded, "hub/tip vs TP-1523 rig (#57)"))
