"""M1 step 4i-c tests (merged by M0 from engine/M1_inlet_fan/agent/proposed_test_m1_step4i_c.py; R-AM.16 level from the mid / tip t/c ranges,
hub t/c known deviation, results-based checks of the step 4i-c design in analysis/results.yaml)."""

import math

import pytest

from core.util import read_yaml
from engine.M1_inlet_fan.analysis import blade_profile as bp
from engine.M1_inlet_fan.analysis import fan_design as fd

CHORD = {"form": "quadratic", "degree": 2, "coefficients": [0.19, 0.33, -0.26]}


def _ctx(taper=0.335, omega=553.1, ranges=None):
    return {"omega": omega, "taper_min": 0.3, "taper_max": 0.5, "area_taper": taper, "blades": 24,
            "tc_ranges": ranges or fd.tc_ranges_rotor67(),
            "mech": {"rho": 4430.0, "r_hub": 0.2324, "span": 0.5423, "allowable": 733.3e6, "margin_min": 1.0}}


def _results():
    return read_yaml(fd.OUT)


# --- R-AM.16 level rule (code) -----------------------------------------------------------------------------------

def test_level_is_smallest_area_with_mid_and_tip_in_range():
    ctx = _ctx()
    area = fd.area_law(CHORD, ctx)
    th = {"chord": CHORD, "area": area}
    rng = ctx["tc_ranges"]
    for name, f in fd.TC_LEVEL_POINTS:
        assert rng[name]["min"] - 1e-12 <= fd.derived_tc(th, f) <= rng[name]["max"] + 1e-12
    binding = area["level"]["binding_point"]
    f_b = dict(fd.TC_LEVEL_POINTS)[binding]
    assert math.isclose(fd.derived_tc(th, f_b), rng[binding]["min"], rel_tol=1e-12)
    # any smaller level puts the binding point below its range
    smaller = {"chord": CHORD, "area": dict(area, A_root=area["A_root"] * (1 - 1e-6))}
    assert fd.derived_tc(smaller, f_b) < rng[binding]["min"]


def test_level_windows_disjoint_raise():
    ranges = {"hub": {"min": 0.07, "max": 0.09, "sections": []}, "mid": {"min": 0.01, "max": 0.011, "sections": []},
              "tip": {"min": 0.5, "max": 0.6, "sections": []}}
    with pytest.raises(fd.AreaLevelUndetermined) as exc:
        fd.area_law(CHORD, _ctx(ranges=ranges))
    w = exc.value.info["windows_A_root_m2"]
    assert max(x[0] for x in w.values()) > min(x[1] for x in w.values())


def test_level_does_not_use_hub_range():
    base = fd.tc_ranges_rotor67()
    moved = dict(base, hub={"min": 0.5, "max": 0.6, "sections": []})
    a1 = fd.area_law(CHORD, _ctx(ranges=base))["A_root"]
    a2 = fd.area_law(CHORD, _ctx(ranges=moved))["A_root"]
    assert a1 == a2


def test_stress_rule_is_a_check_that_fails_the_design():
    with pytest.raises(fd.StressRuleViolated):
        fd.area_law(CHORD, _ctx(omega=1200.0))


def test_area_law_linear_with_rotor67_taper():
    area = fd.area_law(CHORD, _ctx())
    assert area["degree"] == 1 and area["shape"] == [1.0, 0.335 - 1.0]


# --- hub deviation status (code) -------------------------------------------------------------------------------

def _blade_with_level(scale=1.0):
    ctx = _ctx()
    area = fd.area_law(CHORD, ctx)
    return {"chord": CHORD, "thickness": {"chord": CHORD, "area": dict(area, A_root=area["A_root"] * scale)}}, ctx


def test_hub_out_of_range_is_known_deviation_not_fail():
    blade, ctx = _blade_with_level()
    chk = fd.thickness_check(blade, ctx)
    hub = chk["points"]["hub"]
    assert not hub["in_range"] and hub["check"] == fd.HUB_DEVIATION == "known deviation (user-accepted)"
    assert chk["check"] == "pass" and chk["failed_points"] == [] and chk["known_deviations"] == ["hub"]


def test_mid_or_tip_out_of_range_still_fails():
    blade, ctx = _blade_with_level(scale=0.9)  # below the smallest level: binding point out of range
    chk = fd.thickness_check(blade, ctx)
    assert chk["check"] == "fail" and chk["failed_points"]
    assert set(chk["failed_points"]) <= {"mid", "tip"}


# --- results of the step 4i-c design ---------------------------------------------------------------------------

def test_results_converged_and_stream_prs():
    r = _results()
    assert r["convergence"]["converged"] and r["convergence"]["final_check"]["physical"]
    assert math.isclose(r["achieved"]["FPR"], r["inputs"]["FPR_target"], rel_tol=1e-4)
    assert math.isclose(r["achieved"]["pr_fan_inner"], r["inputs"]["pr_fan_inner_target"], rel_tol=1e-4)
    assert all(row["result"] in ("pass", "info") for row in r["budget_check"])


def test_results_level_recomputed_from_chord_and_ranges():
    r = _results()
    coeffs = r["blade"]["chord_law"]["coefficients_m"]
    taper = r["blade"]["area_law"]["taper"]
    rng = r["mechanical"]["thickness_check"]["points"]
    lows = []
    for name, f in fd.TC_LEVEL_POINTS:
        c = bp.polyval(coeffs, f)
        lows.append(rng[name]["range"][0] * 2 / 3 * c * c / (1 - (1 - taper) * f))
    assert math.isclose(r["blade"]["area_law"]["A_root_cm2"], max(lows) * 1e4, rel_tol=1e-4)


def test_results_tc_check_and_hub_deviation():
    r = _results()
    chk = r["mechanical"]["thickness_check"]
    assert chk["check"] == "pass" and chk["points"]["mid"]["check"] == "pass"
    assert chk["points"]["tip"]["check"] == "pass"
    assert chk["points"]["hub"]["check"] == "known deviation (user-accepted)"
    assert r["summary"]["R_AM16_tc_check"] == "pass" and r["summary"]["R_AM16_tc_known_deviations"] == ["hub"]


def test_results_open_item_tip_tc_lower_bound():
    items = {i["id"]: i for i in _results()["open_items"]}
    tip = items["tip_tc_lower_bound"]
    assert tip["status"] == "open" and tip["at_lower_bound"]
    assert "bird strike" in tip["item"] and "flutter" in tip["item"]
    assert items["hub_tc_known_deviation"]["status"] == "open"


def test_results_chord_plain_quadratic_with_root_floor():
    r = _results()
    coeffs = r["blade"]["chord_law"]["coefficients_m"]
    assert r["blade"]["chord_law"]["form"] == "quadratic"
    for t in r["tubes"]:
        assert math.isclose(t["chord_m"], bp.polyval(coeffs, t["span_fraction"]), abs_tol=2e-5)
    hub_sol = coeffs[0] * 24 / (math.pi * (r["annulus"]["r_hub1_m"] + r["annulus"]["r_hub2_m"]))
    assert math.isclose(hub_sol, r["summary"]["hub_solidity_paper"], abs_tol=2e-4)
    ref = read_yaml(fd.R67_REFERENCE)
    assert hub_sol >= ref["design"]["solidity_hub"]["value"] - 1e-3
    assert r["chord_smoothness_r_am17"]["check"] == "pass"


def test_results_stress_and_mass_by_independent_quadrature():
    r = _results()
    m, a, al = r["mechanical"], r["annulus"], r["blade"]["area_law"]
    rho, omega = m["density_kg_m3"], r["inputs"]["rotor_speed_rpm"] * 2 * math.pi / 60
    rh, L = a["r_hub1_m"], a["r_tip1_m"] - a["r_hub1_m"]
    n = 2000
    fs = [j / n for j in range(n + 1)]
    area = [al["A_root_cm2"] * 1e-4 * (1 - (1 - al["taper"]) * f) for f in fs]
    h = L / n
    moment = sum((area[j] * (rh + fs[j] * L) + area[j + 1] * (rh + fs[j + 1] * L)) / 2 * h for j in range(n))
    mass = rho * sum((area[j] + area[j + 1]) / 2 * h for j in range(n))
    assert math.isclose(m["root_stress_MPa"], rho * omega ** 2 * moment / area[0] / 1e6, rel_tol=2e-3)
    assert math.isclose(m["blade_mass"]["per_blade_kg"], mass, rel_tol=2e-3)
    s = m["section_stress_r_am15"]
    assert s["check"] == "pass" and s["max_section_stress_MPa"] <= s["steady_stress_limit_MPa"]
    assert math.isclose(s["steady_stress_limit_MPa"], s["allowable_MPa"] / 2, abs_tol=0.1)


def test_results_area_monotonic_and_taper_in_band():
    r = _results()
    a = r["mechanical"]["area_monotonic_r_am16"]
    assert a["check"] == "pass" and a["taper_in_band"]
    assert a["area_law"]["level_binding_point"] in ("mid", "tip")
