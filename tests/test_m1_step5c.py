"""M1 step 5c: blade root (geometry/dovetail.py), disk, shim, spacer, platform (geometry/rotor_hardware.py) and the
analytic disk check (analysis/disk_stress.py).

Acceptance (M0 step 5c): every slot mates with its dovetail (common volume 0, clearance [T]), disk analytic stress
reported, masses = volume x density, valid solids with volume > 0, STEP per part. Heavy solids built once per module.
Since step 5h the disk web and bore are sized by R-DISK.1 (rules/disk.md) and the disk margin meets the R-AM.13/15
rule; the lug margin stays below it (strict xfail, open issue #33).
"""

import math

import cadquery as cq
import pytest

from core import records
from core.util import read_yaml
from engine.M1_inlet_fan.analysis import disk_stress
from engine.M1_inlet_fan.geometry import blade_solid as bs
from engine.M1_inlet_fan.geometry import dovetail as dv
from engine.M1_inlet_fan.geometry import rotor_hardware as rh

VOL_ZERO = 1e-12  # m3, boolean common volume treated as zero [T]
DIST_TOL = 1e-5  # m, clearance measurement tolerance [T]


@pytest.fixture(scope="module")
def model():
    return rh.build()


@pytest.fixture(scope="module")
def L(model):
    return model["layout"]


@pytest.fixture(scope="module")
def stress(model):
    return rh.stress(model)


@pytest.fixture(scope="module")
def inter(model):
    return rh.interference(model)


def test_disk_solver_matches_closed_form():
    rho, omega, E, nu, a, b = 4430.0, 553.0, 114e9, 0.323, 0.05, 0.2
    sol = disk_stress.solve([(a, 0.1, 0.1), (0.1, b, 0.1)], rho, omega, E, nu, 0.0)
    closed = (3 + nu) / 4 * rho * omega ** 2 * (b * b + (1 - nu) / (3 + nu) * a * a)
    assert sol["bore"]["sigma_t"] == pytest.approx(closed, rel=1e-9)
    outer = sol["points"][-1]
    assert abs(outer["sigma_r"]) < 1e-3 * closed


def test_layout_levels(model, L):
    fp = model["flowpath"]
    assert L["gamma"] == pytest.approx(bs.chord_angle(fp["blade"]["sections"][0]), abs=1e-12)
    ratio = dv.rotor_params()["dovetail"]["neck_width_over_footprint"]["value"]
    assert L["b_n"] == pytest.approx(ratio * L["footprint"], rel=1e-12)
    seq = [fp["rotor_edges"]["le_hub"][1], L["r_rim"], L["z1"], L["z2"], L["z3"], L["spacer_top"],
           L["spacer_bottom"], L["r_slot_bottom"]]
    assert all(a > b for a, b in zip(seq, seq[1:]))
    w0, w1 = L["base_w_range"]
    assert L["w_c"] - L["b_n"] / 2 <= w0 + 1e-12 and w1 - 1e-12 <= L["w_c"] + L["b_n"] / 2


@pytest.mark.parametrize("part", ["blade", "root", "airfoil", "disk", "shim", "spacer", "platform", "lug"])
def test_parts_valid(model, part):
    assert model[part].isValid() and model[part].Volume() > 0


def test_blade_is_airfoil_plus_root(model):
    assert model["blade"].Volume() == pytest.approx(model["airfoil"].Volume() + model["root"].Volume(), rel=1e-5)  # boolean volume noise about 4e-6 [T]


def test_lugs_positive(stress):
    assert stress["lug"]["width_at_lobe_m"] > 0


@pytest.mark.parametrize("pair", ["root-disk", "shim-disk", "spacer-disk", "spacer-shim", "spacer-root", "shim-root",
                                  "platform-disk", "platform-root0", "platform-root1", "platform-platform1"])
def test_no_interference(inter, pair):
    assert inter[pair]["common_volume_m3"] <= VOL_ZERO


def test_clearances(inter, L):
    c = L["c"]
    assert inter["shim-root"]["distance_m"] <= DIST_TOL  # shim lies on the dovetail
    for pair in ("shim-disk", "spacer-disk", "spacer-shim", "platform-disk"):
        assert inter[pair]["distance_m"] == pytest.approx(c, abs=DIST_TOL), pair
    for pair in ("root-disk", "spacer-root", "platform-root0", "platform-root1"):
        assert inter[pair]["distance_m"] >= c - DIST_TOL, pair


def test_masses_are_volume_times_density(model):
    mats = read_yaml(rh.MATERIALS)["materials"]
    fb = dv.rotor_params()["materials_fallback"]
    expect = {"ti6al4v": mats["ti6al4v"]["density"]["value"],
              "alloy718": mats["alloy718"].get("density", fb["alloy718_density"])["value"],
              "aluminium_alloy": mats["aluminium_alloy"].get("density", fb["aluminium_alloy_density"])["value"]}
    m = rh.masses(model)
    rho = {k: r["density"] for k, r in m.items()}
    assert rho["M1.1.1 blade with root"] == rho["M1.1.2 disk"] == rho["M1.1.5 spacer"] == expect["ti6al4v"]
    assert rho["M1.1.4 shim"] == expect["alloy718"] and rho["M1.1.6 platform"] == expect["aluminium_alloy"]
    for row in m.values():
        assert row["mass_kg"] == pytest.approx(row["volume_m3"] * row["density"], rel=1e-12)
    assert m["M1.1.1 blade with root"]["qty"] == 24


def test_speed_from_icd_equals_record(model, stress):
    res = records.read_revision("M1", model["flowpath"]["revision"], "results.yaml")
    assert stress["rpm"] == res["inputs"]["rotor_speed_rpm"]


def test_rim_load_is_sum_of_pulls(stress, model):
    per_slot = sum(x["pull_N"] for x in stress["loads_per_slot"].values())
    assert stress["rim_load_total_N"] == pytest.approx(per_slot * model["n"], rel=1e-12)
    assert stress["allowable_MPa"] == pytest.approx(1100 / 1.5, rel=1e-9)
    assert stress["check"] == ("pass" if stress["margin"] >= stress["margin_min"] else "fail")


def test_disk_margin_meets_rule(stress):
    assert stress["margin"] >= stress["margin_min"]
    assert stress["check"] == "pass" and stress["sizing"]["result"] == "pass"


@pytest.mark.xfail(strict=True, reason="lug margin below the R-AM.13/15 rule (open issue #33, dovetail proportions)")
def test_lug_margin_meets_rule(stress):
    assert stress["lug"]["margin"] >= stress["margin_min"]


def test_step_exports(model):
    paths = rh.export(model)
    for p in paths.values():
        assert p.exists() and p.stat().st_size > 0
    back = cq.importers.importStep(str(paths["fan_disk"])).val()
    assert back.Volume() == pytest.approx(model["disk"].Volume(), rel=1e-3)
    assert math.isfinite(back.Volume())
