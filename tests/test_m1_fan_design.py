"""M1 fan design (analysis/fan_design.py -> analysis/results.yaml), recorded as M1 rev005.

Step 4e: one smooth blade (MCA profile, free vortex per stream blended across the splitter), radial
equilibrium and full loss model ON, R-AM.9 (SP-36 DF limits subsonic, Rotor 67 solidity floor supersonic),
ADR-015 budget-efficiency branch.
Reads the generated results only; the full re-run is covered by core.records.verify/reproducible.
"""

import math

from core.budgets import read_icd
from core.records import ROOT, module_dir
from core.util import read_yaml
from engine.M1_inlet_fan.analysis import blade_profile as bp

RESULTS = module_dir("M1", ROOT) / "analysis" / "results.yaml"
PARAMS = module_dir("M1", ROOT) / "analysis" / "fan_params.yaml"


def results():
    return read_yaml(RESULTS)


def budget():
    return read_icd("M1 test")["modules"]["M1"]["budget"]


def test_annulus_matches_icd_fan_face_area():
    assert results()["annulus"]["fan_face_area_check"] == "pass"


def test_each_stream_meets_its_pressure_ratio():
    b, s = budget(), results()["summary"]
    assert abs(s["outer"]["Pt_ratio_meanline"] / b["FPR"]["value"] - 1) <= 1e-4
    assert abs(s["inner"]["Pt_ratio_meanline"] / b["pr_fan_inner"]["value"] - 1) <= 1e-4


def test_design_converged_on_physical_branch():
    r = results()
    fc = r["convergence"]["final_check"]
    assert len(r["tubes"]) == 9 and r["convergence"]["converged"]
    assert fc["physical"] and fc["issues"] == [] and all(not t["notes"] for t in r["tubes"])


def test_efficiencies_are_budget_values_adr015():
    b, a = budget(), results()["achieved"]
    assert a["eta_fan_outer"] == b["eta_fan_outer"]["value"]
    assert a["eta_fan_inner"] == b["eta_fan_inner"]["value"]


def test_exit_temperatures_from_target_pr_and_budget_eta():
    r, b = results(), budget()
    k = 1.4 / 0.4
    tt = r["inputs"]["Tt2_K"]
    t13 = tt * (1 + (b["FPR"]["value"] ** (1 / k) - 1) / b["eta_fan_outer"]["value"])
    assert math.isclose(r["achieved"]["T13"], t13, abs_tol=1e-3)


def test_ram9_step4e_per_tube():
    r, bl = results(), read_yaml(PARAMS)["blading"]
    hub, tip = bl["df_limit_hub"]["value"], bl["df_limit_tip"]["value"]
    for t in r["tubes"]:
        q, f = t["R_AM9"], t["span_fraction"]
        if t["M1rel"] < 1:
            assert f < r["summary"]["sonic_span_fraction"]
            assert math.isclose(q["DF_limit"], hub + (tip - hub) * f, abs_tol=2e-4)
            ok = t["diffusion_factor"] <= q["DF_limit"] + 1e-4
        else:
            assert math.isclose(q["solidity_floor"], 3.11 + (1.29 - 3.11) * f, abs_tol=2e-3)
            ok = t["solidity"] >= q["solidity_floor"] - 1e-4
        assert q["rule"] == ("pass" if ok else "fail")
    assert r["summary"]["R_AM9_failed_tubes"] == [t["name"] for t in r["tubes"] if t["R_AM9"]["rule"] == "fail"]


def test_blade_is_one_smooth_function_of_span():
    r, bl = results(), read_yaml(PARAMS)["blading"]
    b, fs = r["blade"], r["annulus"]["splitter_span_fraction"]
    for t in r["tubes"]:
        f = t["span_fraction"]
        x = min(1, max(0, (f - fs - bl["splitter_blend_start"]["value"]) / bl["splitter_blend_width"]["value"]))
        blend = x ** 3 * (10 - 15 * x + 6 * x * x)
        assert math.isclose(t["chord_m"], bp.polyval(b["chord_m_coefficients"], f), abs_tol=2e-4)
        k2 = sum(c * v for c, v in zip(b["kappa2_deg_coefficients_total"], [1, f, f * f, f ** 3, blend]))
        assert math.isclose(t["kappa2_deg"], k2, abs_tol=0.02)


def test_smoothness_better_than_step_4d():
    sm = results()["smoothness"]
    assert sm["chord_m"]["max_abs_second_difference"] < 5  # step 4d: 32.3
    assert sm["kappa2_deg"]["max_abs_second_difference"] < 1500  # step 4d: 3940


def test_tubes_use_profile_ss_turn():
    for t in results()["tubes"]:
        s = bp.ss_turn(math.radians(t["kappa1_deg"]), math.radians(t["kappa2_deg"]), t["front_camber_share"],
                       t["t_c"], t["x_max"], t["covered_fraction"])
        assert math.isclose(math.degrees(s), t["ss_turn_deg"], abs_tol=0.05)


def test_profile_builder_limits():
    k1, k2 = math.radians(40), math.radians(10)
    assert math.isclose(bp.camber_angle(k1, k2, 0.5, 0.5), (k1 + k2) / 2)
    assert math.isclose(bp.suction_surface_angle(k1, k2, 0.5, 0.0, 0.5, 1.0), k2)
    assert bp.suction_surface_angle(k1, k2, 0.5, 0.05, 0.5, 0.2) > bp.camber_angle(k1, k2, 0.5, 0.2)
    assert bp.suction_surface_angle(k1, k2, 0.5, 0.05, 0.5, 0.8) < bp.camber_angle(k1, k2, 0.5, 0.8)


def test_profile_builder_on_rotor67_supersonic_streamlines():
    rows = results()["profile_check_rotor67"]["streamlines"]
    sup = [s for s in rows if s["span_fraction"] > 0.45]
    assert len(sup) == 5 and all(abs(s["diff_smooth_fit_deg"]) <= 1.5 for s in sup)
    tip = max(rows, key=lambda s: s["span_fraction"])
    assert abs(tip["diff_smooth_fit_deg"]) < abs(tip["diff_dca_deg"])


def test_tip_loading_above_rotor67():
    lc = results()["summary"]["loading_coefficient"]
    assert lc["psi_tip_M1"] > lc["psi_tip_rotor67"]
    assert math.isclose(lc["psi_tip_M1"], lc["dh0_M1_J_kg"] / lc["U_tip_M1_m_s"] ** 2, rel_tol=1e-3)


def test_taper_bound_and_efficiency_bias():
    r = results()
    assert r["mechanical"]["taper_ratio"] <= read_yaml(PARAMS)["mechanical"]["area_taper_max"]["value"] + 1e-4
    s = r["summary"]
    assert math.isclose(s["overall_efficiency_bias_meanline_minus_budget"],
                        s["overall_meanline"]["efficiency"] - s["overall_efficiency_budget"], abs_tol=2e-5)


def test_core_mass_flow_is_w21():
    w21 = budget()["W21"]["value"]
    inner = sum(t["mass_flow_kg_s"] for t in results()["tubes"] if t["stream"] == "inner")
    assert abs(inner / w21 - 1) <= 1e-6


def test_root_stress_has_margin():
    assert results()["mechanical"]["margin"] > 0


def test_budget_rows_cover_achieved_items():
    r = results()
    assert [row["item"] for row in r["budget_check"]] == list(r["achieved"])
