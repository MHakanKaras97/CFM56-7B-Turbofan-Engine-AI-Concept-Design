"""M1 step 5d: spinner, case shell, containment ring (geometry/spinner_case.py).

Acceptance (M0 step 5d): no case/blade and no spinner/rotor interference, valid solids with volume > 0,
mass = volume x density, STEP per part, masses reported. Heavy solids built once per module.
"""

import math

import cadquery as cq
import pytest

from engine.M1_inlet_fan.geometry import frame as fr
from engine.M1_inlet_fan.geometry import rotor_hardware as rh
from engine.M1_inlet_fan.geometry import spinner_case as sc

VOL_ZERO = 1e-12  # m3 [T]
DIST_TOL = 1e-5  # m [T]
PARTS = ["spinner", "case_shell", "containment_ring"]


@pytest.fixture(scope="module")
def model():
    return sc.build()


@pytest.fixture(scope="module")
def chk(model):
    return sc.checks(model)


@pytest.mark.parametrize("part", PARTS)
def test_parts_valid(model, part):
    assert model[part].isValid() and model[part].Volume() > 0


def test_ogive_tangent_and_closed():
    pts = sc.ogive(0.2, 0.3, -1.0)
    assert pts[0] == (-1.0, 0.0) and pts[-1] == pytest.approx((-0.7, 0.2))
    (x0, r0), (x1, r1) = pts[-2], pts[-1]
    assert (r1 - r0) / (x1 - x0) < 2e-2  # last secant of a curve tangent to the hub line at the base
    assert all(b[1] >= a[1] for a, b in zip(pts, pts[1:]))


def test_case_inner_is_5b_casing_wall(model):
    fp = model["rotor"]["flowpath"]
    wall = fp["curves"]["casing_wall"]
    e = fp["rotor_edges"]
    for x in (e["le_tip"][0], 0.0, e["te_tip"][0]):
        r = fr.r_at(wall, x)
        assert model["case_shell"].isInside(cq.Vector(x, 0, r + 1e-4))
        assert not model["case_shell"].isInside(cq.Vector(x, 0, r - 1e-4))
    assert fr.r_at(wall, e["le_tip"][0]) - e["le_tip"][1] == pytest.approx(fp["tip_clearance_m"], abs=1e-9)


def test_case_covers_blade_tip_and_ring_over_blade(model):
    fp, info = model["rotor"]["flowpath"], model["info"]
    e = fp["rotor_edges"]
    assert info["case_shell"]["x_front_m"] < e["le_tip"][0] and info["case_shell"]["x_rear_m"] > e["te_tip"][0]
    assert info["containment_ring"]["x_front_m"] < e["le_tip"][0] and info["containment_ring"]["x_rear_m"] > e["te_tip"][0]


@pytest.mark.parametrize("pair", ["case-airfoil", "case-containment", "spinner-disk", "spinner-blade",
                                  "spinner-platform", "spinner-shim", "spinner-spacer"])
def test_no_interference(chk, pair):
    assert chk[pair]["common_volume_m3"] <= VOL_ZERO


def test_clearances(chk, model):
    fp = model["rotor"]["flowpath"]
    c = model["rotor"]["layout"]["c"]
    e = fp["rotor_edges"]
    cone = math.atan2(e["le_tip"][1] - e["te_tip"][1], e["te_tip"][0] - e["le_tip"][0])
    d = chk["case-airfoil"]["distance_m"]
    assert fp["tip_clearance_m"] * math.cos(cone) * 0.99 <= d <= fp["tip_clearance_m"] * 1.001
    for pair in ("spinner-disk", "spinner-blade", "spinner-platform", "spinner-shim", "spinner-spacer"):
        assert chk[pair]["distance_m"] >= c - DIST_TOL, pair
    assert chk["case-containment"]["distance_m"] <= DIST_TOL  # ring wrapped on the case


def test_masses_are_volume_times_density(model):
    rho = rh.densities()
    for row in sc.masses(model).values():
        assert row["density"] == rho[row["material"]]["value"]
        assert row["mass_kg"] == pytest.approx(row["volume_m3"] * row["density"], rel=1e-12)


def test_blade_off_energy_reported(model):
    b = sc.blade_off_energy(model)
    assert b["energy_kJ"] == pytest.approx(0.5 * b["mass_kg"] * b["speed_m_s"] ** 2 / 1e3, rel=1e-12)
    assert b["energy_kJ"] > 0


def test_step_exports(model):
    for name, p in sc.export(model).items():
        assert p.exists() and p.stat().st_size > 0
        back = cq.importers.importStep(str(p)).val()
        assert back.Volume() == pytest.approx(model[name].Volume(), rel=1e-3)
