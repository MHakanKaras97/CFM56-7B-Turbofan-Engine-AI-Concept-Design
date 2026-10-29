"""M1 step 5e: outlet guide vane row (geometry/ogv.py).

Acceptance (M0 step 5e): V copies of one vane, no overlap (adjacent pair boolean, others by bbox/sector), inlet
angle from the rev011 rotor-exit swirl, valid solid with volume > 0, mass = volume x density, STEP per part.
"""

import math

import cadquery as cq
import pytest

from engine.M1_inlet_fan.geometry import frame as fr
from engine.M1_inlet_fan.geometry import ogv
from engine.M1_inlet_fan.geometry import rotor_hardware as rh

VOL_ZERO = 1e-12  # m3 [T]


@pytest.fixture(scope="module")
def model():
    return ogv.build()


@pytest.fixture(scope="module")
def chk(model):
    return ogv.checks(model)


def test_vane_count_rule(model):
    B = model["flowpath"]["blade"]["inputs"]["blades"]
    assert model["V"] == math.ceil(ogv.ogv_params()["vane_count_rule"]["value"] * B) == 51


def test_inlet_angle_from_record_swirl(model):
    res = fr.record(model["flowpath"]["revision"])["results"]
    outer = [t for t in res["tubes"] if t["stream"] == "outer"]
    assert len(model["per_tube"]) == len(outer)
    for row, t in zip(model["per_tube"], outer):
        assert row["r_m"] == t["r2_m"]
        assert row["alpha1_deg"] == pytest.approx(math.degrees(math.atan2(t["Vt2_m_s"], t["Vm2_m_s"])), abs=1e-12)
        assert row["kappa1_deg"] == pytest.approx(row["alpha1_deg"] - ogv.ogv_params()["incidence"]["value"], abs=1e-9)
        assert row["flow_turning_deg"] == pytest.approx(row["alpha1_deg"], abs=1e-9)  # axial exit


def test_carter_deviation_gives_axial_exit(model):
    for s in model["sections"]:
        assert s["kappa2"] + s["delta"] == pytest.approx(s["alpha2"], abs=1e-9)
        assert s["delta"] == pytest.approx(s["m"] * (s["kappa1"] - s["kappa2"]) / math.sqrt(s["sigma"]), rel=1e-6)


def test_chord_fills_axial_extent(model):
    for s in model["sections"]:
        assert s["chord"] * math.cos(s["gamma"]) == pytest.approx(model["x_te"] - model["x_le"], rel=1e-9)


def test_vane_valid_and_in_annulus(chk, model):
    assert chk["valid"] and chk["volume_m3"] > 0
    assert chk["r_min_m"] == pytest.approx(model["r_in"], abs=1e-6)
    assert chk["r_max_m"] == pytest.approx(model["r_out"], abs=1e-6)


def test_no_overlap(chk):
    inter = chk["interference"]
    assert 1 in inter["boolean_pairs"]
    assert inter["max_common_volume_m3"] <= VOL_ZERO
    assert len(inter["pairs"]) == chk["vane_count"] // 2


@pytest.mark.parametrize("other", ["case_shell", "containment_ring", "rotor_blade"])
def test_no_clash(chk, other):
    assert chk["clash"][other]["common_volume_m3"] <= VOL_ZERO


def test_mass_is_volume_times_density(chk):
    rho = rh.densities()[ogv.ogv_params()["material"]["value"]]["value"]
    assert chk["density"] == rho
    assert chk["mass_kg"] == pytest.approx(chk["volume_m3"] * rho, rel=1e-12)
    assert chk["row_mass_kg"] == pytest.approx(chk["mass_kg"] * chk["vane_count"], rel=1e-12)


def test_step_exports(model, chk):
    paths = ogv.export(model)
    for p in paths.values():
        assert p.exists() and p.stat().st_size > 0
    back = cq.importers.importStep(str(paths["ogv_vane"])).val()
    assert back.Volume() == pytest.approx(chk["volume_m3"], rel=1e-3)
