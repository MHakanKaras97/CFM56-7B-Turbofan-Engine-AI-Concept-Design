"""M1 step 5i: dovetail / lug sizing rule R-DISK.2 (rules/disk.md; geometry/rotor_hardware.py root_modes and the slab
loop in build; geometry/dovetail.py layout(slab_step)), then R-DISK.1 re-run.

Checks the rule as stated: slab = initial x (1 + 0.1 k), symmetric, k <= 5; the dovetail cross-section, slot count and
rim top fixed; the loop stops at the first k where every mode meets margin >= 1.0; mode formulas; R-DISK.1 re-run on
the final slab; spinner follows the disk front face.
"""

import math

import pytest

from core import records
from engine.M1_inlet_fan.geometry import dovetail as dv
from engine.M1_inlet_fan.geometry import frame as fr
from engine.M1_inlet_fan.geometry import rotor_hardware as rh
from engine.M1_inlet_fan.geometry import spinner_case as sc

MODES = {"lug_tension_lobe", "lug_tension_neck", "flank_bearing", "ear_shear_vm", "ear_bending", "blade_neck_tension"}
FIXED = ("gamma", "b_n", "b_l", "alpha", "r_rim", "z1", "z2", "z3", "r_slot_bottom", "t_sh", "c", "w_c", "x_a0", "x_b0")


@pytest.fixture(scope="module")
def model():
    return rh.build()


@pytest.fixture(scope="module")
def stress(model):
    return rh.stress(model)


def test_all_modes_pass(stress):
    rm = stress["root_modes"]
    assert set(rm["modes"]) == MODES
    for k, row in rm["modes"].items():
        assert row["margin"] >= stress["margin_min"], k
    assert rm["pass"] and stress["check"] == "pass"


def test_mode_formulas(model, stress):
    L, rm = model["layout"], stress["root_modes"]
    F, length = rm["F_N"], rm["slot_length_m"]
    assert length == pytest.approx((L["x_b"] - L["x_a"]) / math.cos(L["gamma"]), rel=1e-12)
    assert rm["modes"]["flank_bearing"]["stress_MPa"] == pytest.approx(F / ((L["b_l"] - L["b_n"]) * length) / 1e6, rel=1e-9)
    w = 2 * math.pi * L["z2"] / model["n"] * math.cos(L["gamma"]) - (L["b_l"] + 2 * (L["t_sh"] + L["c"]))
    assert rm["lug_width_lobe_m"] == pytest.approx(w, rel=1e-12)
    for k, row in rm["modes"].items():
        assert row["margin"] == pytest.approx(stress["allowable_MPa"] / row["stress_MPa"] - 1, rel=1e-9), k


def test_slab_steps_as_stated(model):
    z = model["slab_sizing"]
    h = z["history"]
    s = fr.v(dv.rotor_params()["dovetail"]["slab_step_fraction"])
    k_max = fr.v(dv.rotor_params()["dovetail"]["slab_max_steps"])
    assert z["result"] == "pass" and z["step"] == h[-1]["step"] == len(h) - 1 <= k_max
    assert all(r["min_margin"] < 1.0 for r in h[:-1]) and h[-1]["min_margin"] >= 1.0
    assert all(b["min_margin"] > a["min_margin"] for a, b in zip(h, h[1:]))
    for r in h:
        assert r["slab_m"] == pytest.approx(h[0]["slab_m"] * (1 + s * r["step"]), rel=1e-12)
    L = model["layout"]
    assert L["slab_step"] == z["step"]
    assert (L["x_a"] + L["x_b"]) / 2 == pytest.approx((L["x_a0"] + L["x_b0"]) / 2, abs=1e-12)


def test_fixed_dimensions(model):
    fp, airfoil = dv.base(None, records.ROOT)
    L0 = dv.layout(fp, airfoil, 0)
    L = model["layout"]
    for k in FIXED:
        assert L[k] == L0[k], k
    assert model["n"] == 24


def test_disk_rule_rerun_on_final_slab(model, stress):
    prof, L = model["disk_profile"], model["layout"]
    assert prof["W"] == pytest.approx(L["x_b"] - L["x_a"], rel=1e-12)
    assert model["disk_sizing"]["result"] == "pass"
    assert stress["margin"] >= stress["margin_min"]


def test_spinner_follows_disk_front(model):
    sp = sc.build()
    assert sp["info"]["spinner"]["x_end_m"] == pytest.approx(model["layout"]["x_a"] - model["layout"]["c"], abs=1e-12)


def test_root_mass_and_pull_grew(model, stress):
    rho = rh.densities()["ti6al4v"]["value"]
    P0 = dv.parts(None, records.ROOT, 0)
    assert model["root"].Volume() > P0["root"].Volume()
    assert stress["loads_per_slot"]["blade"]["mass_kg"] == pytest.approx(model["blade"].Volume() * rho, rel=1e-12)
