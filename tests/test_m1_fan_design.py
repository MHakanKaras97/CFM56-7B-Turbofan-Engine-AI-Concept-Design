"""M1 fan design (analysis/fan_design.py -> analysis/results.yaml), M1 step 4f.

Step 4e: one smooth blade (MCA profile, free vortex per stream blended across the splitter), radial
equilibrium and full loss model ON, R-AM.9 (SP-36 DF limits subsonic, Rotor 67 solidity floor supersonic),
ADR-015 budget-efficiency branch. Step 4f: root sized from the integrated section area (R-AM.13: taper band,
stress margin at every section), kappa2 monotonic over the splitter blend, like-for-like tip
efficiency against Rotor 67, blade mass.
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


def chord_at(law: dict, f: float) -> float:
    """Chord law R-AM.14 evaluated independently: quadratic + a (1 - x^2)^3, x = (f - f_b) / w_b, |x| < 1."""
    b = law["bump"]
    x = (f - b["centre_span_fraction"]) / b["half_width_span_fraction"]
    return bp.polyval(law["base_coefficients_m"], f) + (b["amplitude_m"] * (1 - x * x) ** 3 if abs(x) < 1 else 0.0)


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
        assert math.isclose(t["chord_m"], chord_at(b["chord_law"], f), abs_tol=2e-4)
        k2 = sum(c * v for c, v in zip(b["kappa2_deg_coefficients_total"], [1, f, f * f, f ** 3, blend]))
        assert math.isclose(t["kappa2_deg"], k2, abs_tol=0.02)


def test_smoothness_better_than_step_4d():
    sm = results()["smoothness"]
    assert sm["chord_m"]["max_abs_second_difference"] < 10  # step 4d: 32.3; step 4g local bump 8.45
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


def test_efficiency_bias():
    r = results()
    s = r["summary"]
    assert math.isclose(s["overall_efficiency_bias_meanline_minus_budget"],
                        s["overall_meanline"]["efficiency"] - s["overall_efficiency_budget"], abs_tol=2e-5)


def test_core_mass_flow_is_w21():
    w21 = budget()["W21"]["value"]
    inner = sum(t["mass_flow_kg_s"] for t in results()["tubes"] if t["stream"] == "inner")
    assert abs(inner / w21 - 1) <= 1e-6


def test_root_stress_has_margin():
    m = results()["mechanical"]
    assert m["margin"] >= read_yaml(PARAMS)["mechanical"]["stress_margin_min"]["value"] - 1e-3


def test_budget_rows_cover_achieved_items():
    r = results()
    assert [row["item"] for row in r["budget_check"]] == list(r["achieved"])


# --- M1 step 4f -----------------------------------------------------------------------------------------------

def _area_profile(r, n=2000):
    """Section area along the span from the stored chord coefficients and the Rotor 67 t/c fit (independent
    trapezoidal quadrature)."""
    tc = bp.rotor67_fits()["coefficients"]["tc"]
    law = r["blade"]["chord_law"]
    fs = [j / n for j in range(n + 1)]
    return fs, [2 / 3 * bp.polyval(tc, f) * chord_at(law, f) ** 2 for f in fs]


def test_root_sizing_rules_r_am13():
    r, mech_p = results(), read_yaml(PARAMS)["mechanical"]
    m = r["mechanical"]
    assert mech_p["area_taper_min"]["value"] - 1e-4 <= m["taper_ratio"] <= mech_p["area_taper_max"]["value"] + 1e-4
    assert math.isclose(m["thickness_root_mm"], m["tc_root"] * m["chord_root_m"] * 1e3, abs_tol=0.02)
    assert math.isclose(m["area_root_cm2"], 2 / 3 * m["tc_root"] * m["chord_root_m"] ** 2 * 1e4, rel_tol=1e-3)
    assert m["margin"] >= mech_p["stress_margin_min"]["value"] - 1e-3  # every section, not only the root
    assert m["max_section_stress_MPa"] >= m["root_stress_MPa"] - 0.1


def test_root_stress_and_mass_by_independent_quadrature():
    r = results()
    m, a = r["mechanical"], r["annulus"]
    rho = m["density_kg_m3"]
    omega = r["inputs"]["rotor_speed_rpm"] * 2 * math.pi / 60
    rh, L = a["r_hub1_m"], a["r_tip1_m"] - a["r_hub1_m"]
    fs, area = _area_profile(r)
    h = L / (len(fs) - 1)
    moment = sum((area[j] * (rh + fs[j] * L) + area[j + 1] * (rh + fs[j + 1] * L)) / 2 * h for j in range(len(fs) - 1))
    mass = rho * sum((area[j] + area[j + 1]) / 2 * h for j in range(len(fs) - 1))
    assert math.isclose(m["root_stress_MPa"], rho * omega ** 2 * moment / area[0] / 1e6, rel_tol=2e-3)
    bm = m["blade_mass"]
    assert math.isclose(bm["per_blade_kg"], mass, rel_tol=2e-3)
    assert math.isclose(bm["set_kg"], bm["per_blade_kg"] * bm["blade_count"], rel_tol=1e-3)
    assert bm["check_set_kg"] == read_yaml(PARAMS)["mechanical"]["blade_set_mass_check"]["value"]


def test_kappa2_has_no_dip_in_splitter_blend():
    """R-AM.12 (step 4f): total kappa2 (stored coefficients incl. offsets) does not fall over the blend region."""
    r, bl = results(), read_yaml(PARAMS)["blading"]
    fsplit = r["annulus"]["splitter_span_fraction"]
    start, width = bl["splitter_blend_start"]["value"], bl["splitter_blend_width"]["value"]
    lo, hi = max(0.0, fsplit + start), min(1.0, fsplit + start + width)
    coeffs = r["blade"]["kappa2_deg_coefficients_total"]
    sign = {"rising": 1, "falling": -1}[bl["kappa2_blend_direction"]["value"]]

    def k2(f):
        x = min(1, max(0, (f - fsplit - start) / width))
        return sum(c * v for c, v in zip(coeffs, [1, f, f * f, f ** 3, x ** 3 * (10 - 15 * x + 6 * x * x)]))

    ks = [k2(lo + (hi - lo) * j / 1000) for j in range(1001)]
    assert min(sign * (b - a) for a, b in zip(ks, ks[1:])) >= -1e-3
    chk = r["kappa2_blend_check"]
    assert chk["check"] == "pass" and chk["largest_reverse_step_deg"] <= chk["tolerance_deg"]
    # curvature limit: Rotor 67 largest |d2 kappa2/df2| (Table I), independent finite differences here
    assert bl["kappa2_blend_curvature_limit"]["value"] == "rotor67_max"
    assert math.isclose(chk["curvature_limit_deg"], bp.rotor67_kappa2_curvature()["max_abs_deg"], abs_tol=0.01)
    h = (hi - lo) / 1000
    curv = max(abs(ks[j + 1] - 2 * ks[j] + ks[j - 1]) / h ** 2 for j in range(1, 1000))
    assert math.isclose(curv, chk["max_abs_d2kappa2_df2_deg"], rel_tol=0.02)
    assert curv <= chk["curvature_limit_deg"] and chk["curvature_check"] == "pass"


def test_rotor67_kappa2_curvature():
    c = bp.rotor67_kappa2_curvature()
    assert len(c["d2kappa2_df2_deg"]) == bp.N_SECTIONS - 2
    assert 300 < c["max_abs_deg"] < 380  # about 340 deg per unit span^2 near 15-25 % span [H from KS]


def test_kappa2_fit_removes_a_dip():
    from engine.M1_inlet_fan.analysis import fan_design as fd
    ctx = {"f_split": 0.3, "blend_start": -0.25, "blend_width": 0.5, "k2_direction": 1.0}
    fs = [0.05, 0.15, 0.25, 0.36, 0.5, 0.64, 0.75, 0.86, 0.95]
    k2 = [math.radians(x) for x in (22, 23.5, 19, 10.7, 18.3, 31.7, 40.3, 43.9, 42.4)]
    off = {"inner": 0.0, "outer": math.radians(1.0)}
    fit = fd.kappa2_fit(fs, k2, ctx, off)
    assert fit["constrained"]
    blade = {"kappa2": fit["coefficients"], "offsets": off}
    lo, hi = fd.blend_region(ctx)
    ks = [fd.blade_kappa2(blade, lo + (hi - lo) * j / 400, ctx) for j in range(401)]
    assert min(b - a for a, b in zip(ks, ks[1:])) >= -math.radians(1e-3)


def test_blade_mechanics_uniform_blade_matches_closed_form():
    from engine.M1_inlet_fan.analysis import fan_design as fd
    ctx = {"omega": 550.0, "profile_fits": {"coefficients": {"tc": [0.05]}},
           "mech": {"rho": 4430.0, "r_hub": 0.23, "span": 0.54, "allowable": 733.3e6}}
    res = fd.blade_mechanics([0.2], ctx)
    assert math.isclose(res["sigma_root"], fd.root_stress(4430.0, 550.0, 0.23, 0.77, 1.0), rel_tol=1e-9)
    assert math.isclose(res["mass"], 4430.0 * 2 / 3 * 0.05 * 0.04 * 0.54, rel_tol=1e-9)


def test_chord_lp_meets_needs_and_taper_band():
    from engine.M1_inlet_fan.analysis import fan_design as fd
    fits = bp.rotor67_fits()
    tc = fits["coefficients"]["tc"]
    ctx = {"tc_ratio": bp.polyval(tc, 1) / bp.polyval(tc, 0), "taper_min": 0.3, "taper_max": 0.5, "profile_fits": fits}
    fs = [0.06, 0.15, 0.24, 0.36, 0.51, 0.64, 0.75, 0.86, 0.95]
    needs = [0.07, 0.08, 0.10, 0.23, 0.29, 0.30, 0.29, 0.28, 0.27]
    c = fd.lowest_quadratic_above(fd.chord_constraints(fs, needs, ctx))
    assert all(bp.polyval(c, f) >= n - 1e-9 for f, n in zip(fs, needs))
    area = [bp.section_area(bp.polyval(c, j / 200), bp.polyval(tc, j / 200)) for j in range(201)]
    assert 0.3 - 1e-6 <= area[-1] / area[0] <= 0.5 + 1e-6
    c_min = fd.lowest_quadratic_above(fd.chord_constraints(fs, needs, ctx, root_chord_min=1.2 * c[0]))
    assert c_min[0] >= 1.2 * c[0] - 1e-9


def test_rotor67_section_area_taper_in_band():
    r67 = bp.rotor67_section_areas()
    assert 0.3 <= r67["taper_tip_over_root"] <= 0.5
    assert all(0.65 <= s["area_coefficient"] <= 0.75 for s in r67["sections"])


def test_tip_region_like_for_like():
    tr, lim = results()["tip_region"], read_yaml(PARAMS)["tip_check"]
    assert tr["rotor67_solution"]["converged"] and tr["rotor67_solution"]["physical"]
    band = tr["bands"][0]
    assert band["band_span_min"] == lim["band_span_min"]["value"]
    assert band["tubes_M1"] >= 2 and band["tubes_rotor67"] >= 2
    assert math.isclose(band["gap_M1_minus_rotor67"], band["eta_M1"] - band["eta_rotor67_model"], abs_tol=2e-5)
    required = band["gap_M1_minus_rotor67"] < -lim["eta_gap_limit"]["value"]
    assert tr["decision"].startswith("controlled vortex required") == required


def test_profile_area_coefficient_is_two_thirds():
    for x_max in (0.35, 0.45, 0.5, 0.6):
        assert math.isclose(bp.profile_area_coefficient(x_max), 2 / 3, abs_tol=1e-4)
    assert bp.AREA_COEFFICIENT == 2 / 3


def test_vortex_law_stated_free_vortex():
    r = results()
    vt, tip = r["blade"]["vortex"], r["tip_region"]
    assert vt["law"] == "free_vortex" and vt["controlled_vortex"] is False
    assert tip["bands"][0]["gap_M1_minus_rotor67"] >= -tip["eta_gap_limit"]
    assert tip["decision"] == "within the limit: free vortex kept"
    assert r["summary"]["vortex_law"].startswith("free vortex")


def test_blade_mass_diagnosis():
    m = results()["mechanical"]
    d, bm = m["mass_diagnosis"], m["blade_mass"]
    assert math.isclose(d["mass_over_check"], bm["per_blade_kg"] / bm["check_per_blade_kg"], rel_tol=1e-3)
    assert d["area_coefficient"]["used"] <= min(d["area_coefficient"]["rotor67"])  # k is not the cause
    assert all(math.isclose(k, 2 / 3, abs_tol=1e-4) for k in d["area_coefficient"]["profile_integral_f0_f05_f1"])
    assert math.isclose(d["chord"]["chord_scale_for_check"] ** 2, d["thickness"]["tc_scale_for_check"], rel_tol=1e-3)
    assert m["margin_required"] <= m["margin"]  # step 4h: the stress loop may need no root raise
    drops = d["variants"][1:]
    assert drops and all(v["margin"] >= m["margin_required"] - 1e-3 for v in drops)
    best = min(d["variants"], key=lambda v: v["mass_kg"])
    assert d["dominant_chord_driver"] == best["case"]
    assert all(v["mass_kg"] <= bm["per_blade_kg"] + 1e-3 for v in d["variants"])


# --- M1 step 4g -----------------------------------------------------------------------------------------------

def test_chord_bump_is_local_r_am14():
    r = results()
    law, fs = r["blade"]["chord_law"], [t["span_fraction"] for t in r["tubes"]]
    b = law["bump"]
    assert law["form"] == "quadratic_local_bump" and b["amplitude_m"] >= 0
    i = b["tube_index_0based"]
    assert math.isclose(b["centre_span_fraction"], fs[i], abs_tol=1e-4)
    for j in (i - 1, i + 1):  # zero at both neighbour tube centres
        assert abs(fs[j] - b["centre_span_fraction"]) >= b["half_width_span_fraction"] - 1e-4


def test_rotor67_tc_benchmark():
    tc = results()["blade"]["tc_benchmark_rotor67"]
    secs = tc["sections"]
    for q in secs:
        assert math.isclose(q["t_c"], q["max_thickness_cm"] / q["chord_cm"], abs_tol=1e-5)
    assert len(secs) == 14 and tc["hub"] == secs[0]["t_c"] and tc["tip"] == secs[-1]["t_c"]
    lo = max(j for j, q in enumerate(secs) if q["span_fraction"] <= 0.5)
    a, b = secs[lo], secs[lo + 1]
    w = (0.5 - a["span_fraction"]) / (b["span_fraction"] - a["span_fraction"])
    assert math.isclose(tc["mid"], a["t_c"] + w * (b["t_c"] - a["t_c"]), abs_tol=2e-5)
    assert tc["hub"] > tc["mid"] > tc["tip"]


def test_chord_law_variants_ordered():
    """Same R-AM.9 needs: the local bump is not heavier than the plain quadratic, and is the law used."""
    r = results()
    mass = {v["law"]: v["mass_kg"] for v in r["mechanical"]["mass_diagnosis"]["chord_law_variants"]}
    assert mass["quadratic_local_bump"] <= mass["quadratic"] + 1e-3
    assert math.isclose(mass["quadratic_local_bump"], r["mechanical"]["blade_mass"]["per_blade_kg"], abs_tol=1e-3)


# --- M1 step 4h -----------------------------------------------------------------------------------------------

def test_r_am9_needs_from_balanced_work():
    for t in results()["tubes"]:
        q = t["R_AM9"]
        assert q["need_basis"] == "balanced state (step 4h)" and q["need_met_balanced"] and q["rule"] == "pass"


def test_section_stress_every_section_r_am15():
    m = results()["mechanical"]
    s = m["section_stress_r_am15"]
    assert s["sections"] > 100 and s["check"] == "pass"
    assert s["max_section_stress_MPa"] <= s["allowable_MPa"]
    assert s["margin_min_over_sections"] >= s["margin_required"]


def test_area_monotonic_r_am16_reported():
    a = results()["mechanical"]["area_monotonic_r_am16"]
    assert a["check"] in ("pass", "fail")
    if a["check"] == "fail":  # infeasible for the quadratic law: shown, not hidden
        quad = next(v for v in a["feasibility"]["max_monotonic_taper"] if v["degree"] == 2)
        assert quad["max_area_taper"] < a["feasibility"]["taper_band_min"]


def test_chord_smoothness_limit_r_am17():
    c = results()["chord_smoothness_r_am17"]
    assert math.isclose(bp.rotor67_chord_smoothness()["metric"], 1.2685, abs_tol=5e-5)
    assert c["limit"] == 1.2685 and c["limit_equals_recorded"]
    assert c["check"] == ("pass" if c["metric_M1"] <= c["limit"] else "fail")
