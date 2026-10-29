"""M1 step 5h: disk sizing rule R-DISK.1 (rules/disk.md, geometry/rotor_hardware.py size_disk) and sourced 718 density.

Checks the rule as stated: growth variables monotonic with the step, all together in equal fractions of their initial
values and capped by their envelopes; fixed dimensions unchanged; the loop stops at the first step whose margin over
all sections meets the R-AM.13/15 rule; the sized disk is a valid solid inside its axial envelope; mass = volume x
density; blade mass definitions.
"""

import pytest

from core.util import read_yaml
from engine.M1_inlet_fan.geometry import dovetail as dv
from engine.M1_inlet_fan.geometry import frame as fr
from engine.M1_inlet_fan.geometry import rotor_hardware as rh


@pytest.fixture(scope="module")
def model():
    return rh.build()


@pytest.fixture(scope="module")
def stress(model):
    return rh.stress(model)


def test_density_718_from_materials_yaml():
    mats = read_yaml(rh.MATERIALS)["materials"]
    d = rh.densities()
    assert d["alloy718"]["value"] == mats["alloy718"]["density"]["value"] and d["alloy718"]["from"] == "materials.yaml"
    if "density" not in mats["aluminium_alloy"]:
        assert d["aluminium_alloy"]["from"] == "rotor_params.yaml fallback" and d["aluminium_alloy"]["tag"] == "T"


def test_growth_monotonic_proportional_and_capped(model):
    L = model["layout"]
    s = fr.v(dv.rotor_params()["disk_sizing"]["step_fraction"])
    p0 = rh.disk_profile(L, 0)
    prev = p0
    for k in range(1, 30):
        p = rh.disk_profile(L, k)
        assert p["w_bore"] >= prev["w_bore"] and p["t_web"] >= prev["t_web"] and p["r_bore_out"] >= prev["r_bore_out"]
        if not p["caps"]["bore_width"]:
            assert p["w_bore"] == pytest.approx(p0["w_bore"] * (1 + s * k), rel=1e-12)
        if not p["caps"]["web_thickness"]:
            assert p["t_web"] == pytest.approx(p0["t_web"] * (1 + s * k), rel=1e-12)
        assert p["w_bore"] <= p["W"] + 1e-12 and p["t_web"] <= p["w_bore"] + 1e-12
        assert p["r_bore_out"] < p["r_rim_inner"]
        prev = p


def test_fixed_dimensions_unchanged(model):
    p0, p = model["disk_profile_initial"], model["disk_profile"]
    for k in ("W", "x_mid", "r_rim_inner", "r_bore_in"):
        assert p[k] == p0[k], k
    assert p["points"][:4] == p0["points"][:4]  # live rim outline


def test_stops_at_first_passing_step(model, stress):
    z = model["disk_sizing"]
    h = z["history"]
    assert z["result"] == "pass" and z["step"] == h[-1]["step"] == len(h) - 1
    assert h[-1]["margin"] >= stress["margin_min"]
    assert all(r["margin"] < stress["margin_min"] for r in h[:-1])
    assert all(b["margin"] > a["margin"] for a, b in zip(h, h[1:]))
    assert model["disk_profile"]["step"] == z["step"]
    assert stress["margin"] == pytest.approx(h[-1]["margin"], rel=1e-12) and stress["margin"] >= stress["margin_min"]


def test_sized_disk_valid_in_envelope_and_mass(model):
    d, L = model["disk"], model["layout"]
    assert d.isValid() and d.Volume() > model["disk_initial"].Volume()
    bb = d.BoundingBox()
    assert bb.xmin >= L["x_a"] - 1e-6 and bb.xmax <= L["x_b"] + 1e-6
    rho = rh.densities()["ti6al4v"]["value"]
    row = rh.masses(model)["M1.1.2 disk"]
    assert row["mass_kg"] == pytest.approx(d.Volume() * rho, rel=1e-12)


def test_blade_mass_definitions(model):
    rec = fr.record(model["flowpath"]["revision"])["results"]["mechanical"]["blade_mass"]["per_blade_kg"]
    rho = rh.densities()["ti6al4v"]["value"]
    airfoil, root, blade = (model[k].Volume() * rho for k in ("airfoil", "root", "blade"))
    assert blade == pytest.approx(airfoil + root, rel=1e-5)
    assert airfoil < rec < blade  # trimmed airfoil < record integral (rectangular meridian) < whole part
