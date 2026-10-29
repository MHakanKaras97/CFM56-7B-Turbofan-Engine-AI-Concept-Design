"""M1 step 4i / 4i-b unit tests (merged by M0 from engine/M1_inlet_fan/agent/proposed_test_m1_step4i.py).

Code only, not results.yaml (results-based step 4i-c checks: tests/test_m1_step4i_c.py).
"""

import math

import pytest

from core.util import read_yaml
from engine.M1_inlet_fan.analysis import blade_profile as bp
from engine.M1_inlet_fan.analysis import fan_design as fd

PARAMS = fd.PARAMS
FS = [0.06, 0.15, 0.24, 0.36, 0.51, 0.64, 0.75, 0.86, 0.95]
CHORD = {"form": "quadratic", "degree": 2, "coefficients": [0.10, 0.4, -0.25]}


def _ctx(taper=0.335, omega=553.1):
    return {"omega": omega, "taper_min": 0.3, "taper_max": 0.5, "area_taper": taper, "blades": 24,
            "r67": fd.rotor67_solidity_ends(),
            "r_hub_edges": (0.2324, 0.2324 * 1.30), "r_tip_edges": (0.7747, 0.7747 * 0.95),
            "mech": {"rho": 4430.0, "r_hub": 0.2324, "span": 0.5423, "allowable": 733.3e6, "margin_min": 1.0}}


def _area(a_root=1e-3, taper=0.335):
    return {"degree": 1, "taper": taper, "shape": fd.area_shape(1, taper), "A_root": a_root}


# --- R-AM.17 roughness, Rotor 67 t/c ranges (step 4i) ---------------------------------------------------------

def test_chord_roughness_plain_quadratic_is_zero():
    chords = [0.2 + 0.3 * f - 0.25 * f * f for f in FS]
    assert bp.chord_roughness_metric(FS, chords)["metric"] < 1e-12


def test_chord_roughness_bump_scores_high():
    chords = [0.2 + 0.3 * f - 0.25 * f * f + (0.03 if i == 3 else 0.0) for i, f in enumerate(FS)]
    limit = bp.rotor67_chord_roughness()["metric"]
    assert bp.chord_roughness_metric(FS, chords)["metric"] > 10 * limit


def test_chord_roughness_limit_r_am17_step4i():
    r67 = bp.rotor67_chord_roughness()
    rec = read_yaml(PARAMS)["blading"]["chord_smoothness_limit"]["value"]
    assert fd.sig4(r67["metric"]) == fd.sig4(rec) == 0.00388
    assert r67["section"] == 6 and math.isclose(r67["rms"], 0.001975, abs_tol=5e-7)


def test_tc_ranges_rotor67_equal_recorded():
    rng = fd.tc_ranges_rotor67()
    rec = read_yaml(PARAMS)["mechanical"]["tc_check_ranges"]["value"]
    assert rng["hub"]["sections"] == [1, 2, 3, 4, 5] and rng["mid"]["sections"] == [6, 7, 8, 9]
    assert rng["tip"]["sections"] == [10, 11, 12, 13, 14]
    for k in ("hub", "mid", "tip"):
        assert [fd.sig4(rng[k]["min"]), fd.sig4(rng[k]["max"])] == rec[k]
    fd.check_recorded_tc_ranges(read_yaml(PARAMS), rng)


# --- chord LP: R-AM.9 needs and R-AM.18 root floor (step 4i-b) ------------------------------------------------

def test_chord_lp_meets_needs_aero_only():
    needs = [0.07, 0.08, 0.10, 0.23, 0.29, 0.30, 0.29, 0.28, 0.27]
    law = fd.size_chord(FS, needs, {"chord_law": "quadratic"})  # no floors in ctx: needs only
    assert law["degree"] == 2 and len(law["coefficients"]) == 3
    assert all(fd.chord_value(law, f) >= n - 1e-9 for f, n in zip(FS, needs))
    assert sum(1 for f, n in zip(FS, needs) if fd.chord_value(law, f) - n < 1e-9) >= 3  # LP vertex


def test_root_chord_floor_r_am18_from_rotor67_yaml():
    ctx = _ctx()
    sol_hub = read_yaml(fd.R67_REFERENCE)["design"]["solidity_hub"]
    assert sol_hub["tag"] == "KS" and ctx["r67"]["hub"] == sol_hub["value"]
    f0, c_min = fd.root_chord_floor(ctx)
    assert f0 == 0.0
    assert math.isclose(c_min / (math.pi * (0.2324 + 0.2324 * 1.30) / 24), sol_hub["value"], rel_tol=1e-12)
    assert read_yaml(PARAMS)["blading"]["root_chord_floor"]["value"] == "rotor67_hub_solidity"


def test_chord_lp_with_root_floor_r_am18():
    ctx = dict(_ctx(), chord_law="quadratic")
    ctx["chord_floors"] = [fd.root_chord_floor(ctx)]
    needs = [0.07, 0.08, 0.10, 0.23, 0.29, 0.30, 0.29, 0.28, 0.27]
    free = fd.size_chord(FS, needs, {"chord_law": "quadratic"})
    law = fd.size_chord(FS, needs, ctx)
    c_floor = ctx["chord_floors"][0][1]
    assert fd.chord_value(free, 0.0) < c_floor  # the floor is active for these needs
    assert math.isclose(fd.chord_value(law, 0.0), c_floor, rel_tol=1e-9)
    assert all(fd.chord_value(law, f) >= n - 1e-9 for f, n in zip(FS, needs))
    assert len(fd.chord_constraints(FS, needs, law, ctx["chord_floors"])) == len(FS) + 1


def test_rotor67_inlet_pitch_needs_below_mean_radius_floor():
    ctx = dict(_ctx(), chord_law="quadratic")
    ctx["chord_floors"] = [fd.root_chord_floor(ctx)]
    r_h, L, z = ctx["mech"]["r_hub"], ctx["mech"]["span"], ctx["blades"]
    sup = FS[4:]
    needs = [fd.r67_solidity(ctx["r67"], f) * 2 * math.pi * (r_h + f * L) / z for f in sup]
    free = fd.size_chord(sup, needs, {"chord_law": "quadratic"})
    law = fd.size_chord(sup, needs, ctx)
    c_floor = ctx["chord_floors"][0][1]
    assert math.isclose(fd.chord_value(free, 0.0), ctx["r67"]["hub"] * 2 * math.pi * r_h / z, rel_tol=1e-9)
    assert fd.chord_value(free, 0.0) < c_floor
    assert math.isclose(fd.chord_value(law, 0.0), c_floor, rel_tol=1e-9)
    assert all(fd.chord_value(law, f) >= n - 1e-9 for f, n in zip(sup, needs))


# --- R-AM.16 area law, structural level (step 4i-b) -----------------------------------------------------------

def test_stress_independent_of_area_level_and_half_allowable():
    ctx = _ctx()
    m1, m2 = fd.blade_mechanics(_area(1e-3), ctx), fd.blade_mechanics(_area(7e-3), ctx)
    assert math.isclose(m1["sigma_max"], m2["sigma_max"], rel_tol=1e-12)
    assert math.isclose(m1["steady_limit"], 733.3e6 / 2)
    assert math.isclose(m1["sigma_root"], fd.root_stress(4430.0, 553.1, 0.2324, 0.2324 + 0.5423, 0.335), rel_tol=1e-9)


def test_area_law_taper_outside_band_rejected():
    with pytest.raises(ValueError, match="outside the band"):
        fd.area_law(CHORD, _ctx(taper=0.6))


def test_derived_tc_from_area_and_chord():
    th = {"chord": CHORD, "area": _area(2e-3)}
    for f in (0.0, 0.6, 1.0):
        assert math.isclose(fd.derived_tc(th, f), 2e-3 * (1 - 0.665 * f)
                            / (bp.AREA_COEFFICIENT * fd.chord_value(CHORD, f) ** 2), rel_tol=1e-12)
    # t/c ratios along the span do not depend on the level (only A_root scales them)
    th2 = {"chord": CHORD, "area": _area(5e-3)}
    assert math.isclose(fd.derived_tc(th, 0.5) / fd.derived_tc(th, 0.0),
                        fd.derived_tc(th2, 0.5) / fd.derived_tc(th2, 0.0), rel_tol=1e-12)


def test_blade_mechanics_uniform_blade_matches_closed_form():
    ctx = _ctx()
    area = {"degree": 1, "taper": 1.0, "shape": [1.0, 0.0], "A_root": 2 / 3 * 0.05 * 0.04}
    res = fd.blade_mechanics(area, ctx)
    assert math.isclose(res["sigma_root"], fd.root_stress(4430.0, 553.1, 0.2324, 0.7747, 1.0), rel_tol=1e-9)
    assert math.isclose(res["mass"], 4430.0 * 2 / 3 * 0.05 * 0.04 * 0.5423, rel_tol=1e-9)


def test_profile_builder_uses_derived_tc():
    ctx = {"profile_fits": bp.rotor67_fits()}
    assert math.isclose(fd.tc_at(0.5, ctx), bp.polyval(ctx["profile_fits"]["coefficients"]["tc"], 0.5))
    th = {"chord": CHORD, "area": _area(2e-3)}
    ctx["thickness"] = th
    assert math.isclose(fd.tc_at(0.5, ctx), fd.derived_tc(th, 0.5))
