"""M1 step 4i-e / 4i-f tests (merged by M0 from engine/M1_inlet_fan/agent/proposed_test_m1_step4i_e.py).

Solidity = true chord x blade count / (2 pi r_mean) (Rotor 67 Table I 3.116 / 1.285 [H from KS]); R-AM.18 hub floor on the
hub mean-radius pitch; supersonic R-AM.9 floor on the tube inlet pitch (known conservative deviation, user-accepted).
"""

import math

import pytest

from core.util import read_yaml
from engine.M1_inlet_fan.analysis import blade_profile as bp
from engine.M1_inlet_fan.analysis import fan_design as fd

R_HUB1, R_TIP1 = 0.2324, 0.7747
EDGES = {"r_hub_edges": (R_HUB1, R_HUB1 * 1.30), "r_tip_edges": (R_TIP1, R_TIP1 * 0.95)}


def _ctx(**kw):
    ctx = {"blades": 24, "r67": fd.rotor67_solidity_ends(), **EDGES,
           "blading": {"solidity_min": {"value": 1.0}, "solidity_max": {"value": 3.2},
                       "df_limit_hub": {"value": 0.6}, "df_limit_tip": {"value": 0.4}},
           "kappa1": [math.radians(50.0)], "supersonic": [True]}
    ctx.update(kw)
    return ctx


def _tube(r1=0.60, r2=0.58, span=0.7):
    return {"name": "tube x", "r1": r1, "r2": r2, "A1": 0.1, "A2": 0.09, "span": span}


# --- definition (code) --------------------------------------------------------------------------------------------

def test_rotor67_table1_reproduces_published_solidity_with_mean_radius():
    """Table I chord x 22 / (pi (r_LE + r_TE)) gives 3.116 / 1.285, i.e. the TP-2879 p. 2 pair 3.11 / 1.29 [KS];
    the LE (inlet) pitch gives 3.48 / 1.27 and does not."""
    r67 = bp.rotor67_solidity_paper()
    pub = fd.rotor67_solidity_ends()
    assert r67["blade_count"] == 22
    assert math.isclose(r67["hub"], 3.116, abs_tol=5e-4) and math.isclose(r67["tip"], 1.285, abs_tol=5e-4)
    assert abs(r67["hub"] - pub["hub"]) < 0.01 and abs(r67["tip"] - pub["tip"]) < 0.01
    assert math.isclose(r67["inlet_pitch"]["hub"], 3.48, abs_tol=5e-3)
    assert math.isclose(r67["inlet_pitch"]["tip"], 1.27, abs_tol=5e-3)
    assert abs(r67["inlet_pitch"]["hub"] - pub["hub"]) > 0.3


def test_solidity_paper_definition():
    c, r1, r2, z = 0.2, 0.25, 0.33, 24
    assert math.isclose(fd.mean_pitch(r1, r2, z), 2 * math.pi * (r1 + r2) / 2 / z, rel_tol=1e-14)
    assert math.isclose(fd.solidity_paper(c, r1, r2, z), c * z / (2 * math.pi * (r1 + r2) / 2), rel_tol=1e-14)
    t = _tube(r1, r2)
    assert math.isclose(fd.tube_mean_pitch(t, {"blades": z}), fd.mean_pitch(r1, r2, z), rel_tol=1e-14)
    assert math.isclose(fd.pitch(t, {"blades": z}), 2 * math.pi * r1 / z, rel_tol=1e-14)  # meanline basis kept


def test_root_floor_uses_hub_mean_radius():
    ctx = _ctx()
    f0, c_min = fd.root_chord_floor(ctx)
    assert f0 == 0.0
    r_mean = (R_HUB1 + R_HUB1 * 1.30) / 2
    assert math.isclose(c_min * 24 / (2 * math.pi * r_mean), ctx["r67"]["hub"], rel_tol=1e-12)
    assert c_min * 24 / (2 * math.pi * R_HUB1) > ctx["r67"]["hub"] * 1.14  # larger than the step 4i-c floor
    assert read_yaml(fd.PARAMS)["blading"]["solidity_definition"]["value"] == "chord_count_over_2pi_r_mean"


def test_supersonic_floor_basis_is_inlet_pitch_param():
    bl = read_yaml(fd.PARAMS)["blading"]
    assert fd.SUPERSONIC_FLOOR_BASIS == "inlet_pitch"
    assert bl["supersonic_floor_basis"]["value"] == fd.SUPERSONIC_FLOOR_BASIS
    assert "known conservative deviation" in bl["supersonic_floor_basis"]["note"]


@pytest.mark.parametrize("r1,r2", [(0.60, 0.58), (0.45, 0.47)])
def test_supersonic_need_uses_tube_inlet_pitch(r1, r2):
    """Step 4i-f: chord need = Rotor 67 solidity at the span x 2 pi r1 / 24, whatever r2; the paper-definition
    solidity of that chord is sigma_R67 x 2 r1 / (r1 + r2) (above Rotor 67 for a contracting tube, below for an
    expanding one)."""
    t, ctx = _tube(r1, r2), _ctx()
    q = fd.required_solidity(t, 0, 1.2, 10.0, ctx, None)
    sig = fd.r67_solidity(ctx["r67"], t["span"])
    assert math.isclose(q["chord_m"], sig * 2 * math.pi * r1 / 24, rel_tol=1e-12)
    assert math.isclose(q["solidity_inlet_pitch"], sig, rel_tol=1e-12)
    assert math.isclose(q["solidity"], sig * 2 * r1 / (r1 + r2), rel_tol=1e-12)
    assert (q["solidity"] > sig) == (r2 < r1)
    assert q["met"] and q["basis"].startswith("inlet pitch") and "known conservative deviation" in q["basis"]


def test_subsonic_df_rule_keeps_inlet_pitch(monkeypatch):
    """SP-36 DF rule: the solidity search runs on the meanline Tube solidity (inlet pitch); the returned chord is
    that solidity x inlet pitch, the paper-definition solidity is reported from it."""
    seen = []

    class _Res:
        def __init__(self, df):
            self.diffusion_factor = df

    monkeypatch.setattr(fd, "kappa2_for", lambda *a, **k: 0.1)
    monkeypatch.setattr(fd, "make_tube", lambda t, k1, k2, sigma, ctx: seen.append(sigma) or sigma)
    monkeypatch.setattr(fd, "solve_tube", lambda sigma, *a, **k: _Res(0.9 / sigma))  # DF = 0.9 / sigma_inlet
    t = _tube(r1=0.30, r2=0.36, span=0.0)
    ctx = _ctx(supersonic=[False], omega=553.1, Tt=288.15, Pt=101325.0, gas=None)
    q = fd.required_solidity(t, 0, 1.1, 10.0, ctx, None)
    sigma_in = 0.9 / 0.6  # DF limit 0.6 at the hub
    assert abs(q["solidity_inlet_pitch"] - sigma_in) <= fd.SIGMA_TOL
    assert math.isclose(q["chord_m"], q["solidity_inlet_pitch"] * 2 * math.pi * t["r1"] / 24, rel_tol=1e-12)
    assert math.isclose(q["solidity"], q["chord_m"] / fd.mean_pitch(t["r1"], t["r2"], 24), rel_tol=1e-12)
    assert "inlet pitch" in q["basis"] and min(seen) >= 1.0 - 1e-12


def test_balanced_needs_supersonic_on_inlet_pitch(monkeypatch):
    class _R:
        Tt_ratio, mass_flow = 1.2, 10.0

    ctx = _ctx(supersonic=[True, True], kappa1=[0.9, 0.9], gas=type("G", (), {"cp": 1004.5})(), Tt=288.15)
    geo = [_tube(0.60, 0.58, 0.7), _tube(0.70, 0.66, 0.9)]
    out = fd.balanced_needs(geo, [_R(), _R()], ctx)
    for t, c, s, si in zip(geo, out["chord_m"], out["solidity"], out["solidity_inlet_pitch"]):
        sig = fd.r67_solidity(ctx["r67"], t["span"])
        assert math.isclose(c, sig * fd.pitch(t, ctx), rel_tol=1e-12)
        assert math.isclose(si, sig, rel_tol=1e-12)
        assert math.isclose(s, c / fd.tube_mean_pitch(t, ctx), rel_tol=1e-12)  # reported by the paper definition


# --- results (need a step 4i-f results.yaml) -----------------------------------------------------------------------

def _results():
    r = read_yaml(fd.OUT)
    if "R_AM9_supersonic_floor_basis" not in r.get("summary", {}):
        pytest.skip("results.yaml not regenerated by a step 4i-f run")
    return r


def test_results_converged_budget_streams():
    r = _results()
    assert r["convergence"]["converged"] is True
    assert math.isclose(r["summary"]["outer"]["Pt_ratio_meanline"], 1.765, abs_tol=1e-4)
    assert math.isclose(r["summary"]["inner"]["Pt_ratio_meanline"], 1.344, abs_tol=1e-4)
    assert all(row["result"] in ("pass", "info") for row in r["budget_check"])


def test_results_solidity_by_paper_definition_and_supersonic_floor_on_inlet_pitch():
    r = _results()
    assert r["summary"]["R_AM9_supersonic_floor_basis"] == "inlet pitch"
    assert "known conservative deviation" in r["summary"]["R_AM9_supersonic_floor_known_deviation"]
    n_sup = 0
    for t in r["tubes"]:
        q = t["R_AM9"]
        assert math.isclose(t["solidity"], t["chord_m"] * 24 / (math.pi * (t["r1_m"] + t["r2_m"])), abs_tol=2e-4)
        assert math.isclose(t["solidity_inlet_pitch_info"], t["chord_m"] * 24 / (2 * math.pi * t["r1_m"]),
                            abs_tol=2e-4)
        assert math.isclose(q["solidity_floor_paper_definition_info"],
                            q["solidity_floor"] * 2 * t["r1_m"] / (t["r1_m"] + t["r2_m"]), abs_tol=2e-4)
        if t["R_AM9"]["zone"].startswith("supersonic"):
            n_sup += 1
            f = t["span_fraction"]
            assert math.isclose(q["solidity_floor"], 3.11 + (1.29 - 3.11) * f, abs_tol=2e-3)
            assert q["solidity_floor_basis"] == "inlet pitch"
            assert "known conservative deviation" in q["solidity_floor_known_deviation"]
            assert t["solidity_inlet_pitch_info"] >= q["solidity_floor"] - 1e-4
            assert q["rule"] == "pass"
    assert n_sup >= 1
    tip = r["tubes"][-1]["R_AM9"]
    assert tip["solidity_floor_over_rotor67_paper_info"] > 1.0  # conservative at the tip (contracting tube)
    assert r["summary"]["R_AM9_pass_count"] == f"{len(r['tubes'])}/{len(r['tubes'])}"


def test_results_hub_and_tip_solidity_by_paper_definition():
    r = _results()
    s, a = r["solidity_r_am18"], r["annulus"]
    coeffs = r["blade"]["chord_law"]["coefficients_m"]
    c_tip = sum(coeffs)
    hub = coeffs[0] * 24 / (math.pi * (a["r_hub1_m"] + a["r_hub2_m"]))
    tip = c_tip * 24 / (math.pi * (a["r_tip1_m"] + a["r_tip2_m"]))
    assert math.isclose(hub, s["hub_solidity_paper"], abs_tol=2e-4)
    assert math.isclose(tip, s["tip_solidity_paper"], abs_tol=2e-4)
    assert math.isclose(s["hub_solidity_inlet_pitch_info"], coeffs[0] * 24 / (2 * math.pi * a["r_hub1_m"]),
                        abs_tol=2e-4)
    assert math.isclose(s["tip_solidity_inlet_pitch_info"], c_tip * 24 / (2 * math.pi * a["r_tip1_m"]), abs_tol=2e-4)
    assert r["summary"]["hub_solidity_paper"] == s["hub_solidity_paper"]
    assert r["summary"]["tip_solidity_paper"] == s["tip_solidity_paper"]
    assert hub >= fd.rotor67_solidity_ends()["hub"] - 1e-4 and s["check"] == "pass"
    assert r["summary"]["R_AM18_check"] == "pass"
    assert s["rotor67_table1_paper_definition"] == {"hub": 3.1159, "tip": 1.285}


def test_results_design_checks_kept():
    """Step 4i-c rules kept: taper 0.3352, mid/tip t/c in range, hub t/c known deviation, stress <= half the
    allowable, R-AM.17 pass."""
    r = _results()
    m, s = r["mechanical"], r["summary"]
    assert math.isclose(m["taper_ratio"], 0.3352, abs_tol=1e-4)
    pts = m["thickness_check"]["points"]
    assert pts["mid"]["check"] == "pass" and pts["tip"]["check"] == "pass"
    assert pts["hub"]["check"] == "known deviation (user-accepted)"
    assert s["R_AM16_tc_known_deviations"] == ["hub"]
    s15 = m["section_stress_r_am15"]
    assert s15["max_section_stress_MPa"] <= s15["steady_stress_limit_MPa"] and s15["check"] == "pass"
    assert s["R_AM17_check"] == "pass"
