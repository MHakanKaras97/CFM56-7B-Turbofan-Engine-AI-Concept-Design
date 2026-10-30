"""M1 step 5f: fan frame (geometry/fan_frame.py).

Acceptance (M0 step 5f): valid solids with volume > 0, no interference with the OGV row, case and rotor,
interfaces listed (M2 station 21, M7 station 13, M8 bearing boundary, nacelle, VBV), mass = volume x density, STEP
per part.
"""

import cadquery as cq
import pytest

from engine.M1_inlet_fan.geometry import fan_frame as ff
from engine.M1_inlet_fan.geometry import m2_boundary as m2b
from engine.M1_inlet_fan.geometry import rotor_hardware as rh

VOL_ZERO = 1e-12  # m3 [T]


@pytest.fixture(scope="module")
def model():
    return ff.build()


@pytest.fixture(scope="module")
def chk(model):
    return ff.checks(model)


@pytest.mark.parametrize("part", ff.PARTS)
def test_parts_valid(model, part):
    s = model["parts"][part]
    assert s.isValid() and s.Volume() > 0


def test_layout_follows_flowpath(model):
    L, st = model["layout"], model["flowpath"]["stations"]
    assert L["x0"] == st["13"]["x_m"] and L["x1"] > L["x0"]
    assert L["x21"] == st["21"]["x_m"] and L["r_split"] == st["21"]["r_tip_m"]
    assert L["r_root"] == st["13"]["r_inner_m"]  # CR-002 (a), R-G1.3
    m2 = m2b.m2_boundary()
    assert L["xc0"] == m2["x24"]  # CR-003, R-G1.1
    assert (L["r_hub"], L["r_core_out"]) == (m2["r_core_hub"], m2["r_core_tip"])  # R-G1.7
    assert L["r_wall"] == st["13"]["r_casing_wall_m"]
    assert L["r_bearing"] < L["r_hub"] - L["t_hub"] < L["r_hub"] < L["r_core_out"] <= L["r_root"] < L["r_wall"]


def test_no_interference(chk):
    bad = {k: r["common_volume_m3"] for k, r in chk.items() if r["common_volume_m3"] > VOL_ZERO}
    assert not bad
    for key in ("outer_ring-ogv0", "wall_ring-ogv0", "core_strut-wall_ring", "outer_ring-case", "bypass_strut-outer_ring",
                "core_strut-hub_ring", "struts-ogv_row"):
        assert key in chk


def test_ogv_mates_with_frame_walls(chk, model):
    assert chk["outer_ring-ogv0"]["distance_m"] <= 1e-5
    assert ff.root_radii(model)["ogv_root"] == pytest.approx(model["layout"]["r_root"], abs=1e-9)  # R-G1.4
    assert chk["outer_ring-case"]["distance_m"] <= 1e-5


def test_interfaces_listed(model):
    itf = ff.interfaces(model)
    assert set(itf) == {"M2_station_21", "M7_station_13", "M8_bearing_support", "nacelle_inlet", "VBV"}
    st = model["flowpath"]["stations"]
    assert itf["M2_station_21"]["r_hub_m"] == st["21"]["r_hub_m"] and itf["M2_station_21"]["r_tip_m"] == st["21"]["r_tip_m"]
    assert itf["M7_station_13"]["r_outer_m"] == st["13"]["r_outer_m"]


def test_masses(model):
    rho = rh.densities()[ff.frame_params()["material"]["value"]]["value"]
    for r in ff.masses(model).values():
        assert r["density"] == rho and r["mass_kg"] == pytest.approx(r["volume_m3"] * rho, rel=1e-12)


def test_step_exports(model):
    paths = ff.export(model)
    for p in paths.values():
        assert p.exists() and p.stat().st_size > 0
    back = cq.importers.importStep(str(paths["wall_ring"])).val()
    assert back.Volume() == pytest.approx(model["parts"]["wall_ring"].Volume(), rel=1e-3)
