"""First CFM56-7B27 fan rotor design at the M0 design point (SLS ISA, max take-off), M1 step 3.

Method (rules/aero_method.md; tools/meanline.py used unchanged):
- Budget and inlet state from the ICD (core.budgets.read_icd): W2, W21, W13, Tt2, Pt2, the stream
  targets FPR (outer) and pr_fan_inner (inner), and the LP speed (Girão 2023 nominal) [KS/H].
- Annulus: tip radius from the fan diameter, hub radius from the hub/tip ratio (analysis/fan_params.yaml);
  the annulus area is compared with the ICD fan_face_area.
- Splitter: solve_rotor splits the mass flow by inlet area (uniform inlet), so the splitter radius is the
  radius whose inner annulus area share equals W21/W2.
- Stream tubes: n_inner tubes of equal inlet area between hub and splitter and n_outer tubes of equal
  inlet area between splitter and tip (equal mass flow within each stream). At the rotor exit the annulus
  is set by the exit radius ratios and the core share of the exit area [T]; the tubes again share their
  stream's exit area equally. Tube radius = area-mean radius sqrt((ri^2 + ro^2) / 2).
- Blading per tube: kappa1 = beta1 - design incidence; kappa2 by bisection so the tube pressure ratio
  equals its stream target; solidity by bisection so the Lieblein DF equals the local DF limit, 0.6 at
  the hub and 0.3 at the tip (Abrisha 2026 PDF p. 38) [KS], linear in inlet span fraction [T] (bounded
  by solidity_min/max). Chord = solidity x pitch at the inlet tube radius. Covered-passage fraction as in
  analysis/rotor67.py with the stagger taken as the mean of the metal angles [T].
- Stream results: mass_averaged per stream; check against the budget with core.budgets.check_budget.
- Mechanical check: centrifugal root stress of a blade with linear area taper between the inlet hub and
  tip radius, sigma = rho omega^2 L [r_h + L/2 - (1 - tau)(r_h/2 + L/3)], L = r_t - r_h [G].
  Not modelled: OGV, inlet recovery, endwall and tip clearance loss, radial equilibrium.

Run: python -m engine.M1_inlet_fan.analysis.fan_design  (writes analysis/results.yaml).
"""

import math
from pathlib import Path

from core.budgets import check_budget, read_icd
from core.util import read_yaml, write_yaml
from tools.meanline import Gas, Tube, mass_averaged, solve_rotor, solve_tube

M1 = Path(__file__).resolve().parents[1]
ROOT = M1.parents[1]
PARAMS = M1 / "analysis" / "fan_params.yaml"
OUT = M1 / "analysis" / "results.yaml"
MATERIALS = ROOT / "tools" / "data" / "materials.yaml"

INCH = 0.0254
KAPPA2_MIN = math.radians(-70.0)  # search bound of the exit metal angle [T]
AREA_CHECK = 0.01  # [T] allowed relative difference to the ICD fan_face_area
DF_TOL = 1e-4  # bisection tolerance of the DF match


def v(q: dict) -> float:
    return float(q["value"])


def icd_inputs(icd: dict) -> dict:
    budget = icd["modules"]["M1"]["budget"]
    st2 = icd["stations"]["2"]
    assert st2["Pt"]["unit"] == "kPa" and st2["Tt"]["unit"] == "K"
    rpm = icd["shafts"]["LP"]["speed_refs"]["girao_nominal"]
    assert rpm["unit"] == "rpm"
    return {"W2": v(budget["W2"]), "W21": v(budget["W21"]), "W13": v(budget["W13"]),
            "FPR": v(budget["FPR"]), "pr_fan_inner": v(budget["pr_fan_inner"]),
            "Tt2": v(st2["Tt"]), "Pt2": v(st2["Pt"]) * 1e3, "rpm": v(rpm),
            "fan_face_area": v(icd["fan_face_area"])}


def annulus(p: dict, inp: dict) -> dict:
    a = p["annulus"]
    r_tip1 = v(a["fan_tip_diameter"]) * INCH / 2
    r_hub1 = v(a["hub_tip_ratio"]) * r_tip1
    r_tip2 = v(a["exit_tip_radius_ratio"]) * r_tip1
    r_hub2 = v(a["exit_hub_radius_ratio"]) * r_hub1
    core_share = inp["W21"] / inp["W2"]
    r_split1 = math.sqrt(r_hub1 ** 2 + core_share * (r_tip1 ** 2 - r_hub1 ** 2))
    f2 = v(a["exit_core_area_fraction"])
    r_split2 = math.sqrt(r_hub2 ** 2 + f2 * (r_tip2 ** 2 - r_hub2 ** 2))
    area1 = math.pi * (r_tip1 ** 2 - r_hub1 ** 2)
    return {"r_tip1": r_tip1, "r_hub1": r_hub1, "r_split1": r_split1, "r_tip2": r_tip2, "r_hub2": r_hub2,
            "r_split2": r_split2, "area1": area1, "area2": math.pi * (r_tip2 ** 2 - r_hub2 ** 2),
            "core_share": core_share, "fan_face_area_deviation": area1 / inp["fan_face_area"] - 1}


def equal_area_rings(r_in: float, r_out: float, n: int) -> list[tuple[float, float]]:
    """n rings of equal area between r_in and r_out: (inner, outer) radii."""
    edges = [math.sqrt(r_in ** 2 + k / n * (r_out ** 2 - r_in ** 2)) for k in range(n + 1)]
    return list(zip(edges[:-1], edges[1:]))


def tube_layout(p: dict, ann: dict) -> list[dict]:
    """Inlet and exit radius and area of every tube, hub first, with its stream."""
    n_in, n_out = int(v(p["stream_tubes"]["n_inner"])), int(v(p["stream_tubes"]["n_outer"]))
    rings1 = equal_area_rings(ann["r_hub1"], ann["r_split1"], n_in) + equal_area_rings(ann["r_split1"], ann["r_tip1"], n_out)
    rings2 = equal_area_rings(ann["r_hub2"], ann["r_split2"], n_in) + equal_area_rings(ann["r_split2"], ann["r_tip2"], n_out)
    out = []
    for j, ((a, b), (c, d)) in enumerate(zip(rings1, rings2), 1):
        out.append({"name": f"tube {j}", "stream": "inner" if j <= n_in else "outer",
                    "r1": math.sqrt((a * a + b * b) / 2), "r2": math.sqrt((c * c + d * d) / 2),
                    "A1": math.pi * (b * b - a * a), "A2": math.pi * (d * d - c * c)})
    return out


def covered_fraction(kappa1: float, kappa2: float, solidity: float) -> float:
    """Pitch sin(kappa1) cos(kappa1) over the meridional chord (chord x cos(stagger)), as in rotor67.py."""
    stagger = (kappa1 + kappa2) / 2
    return min(1.0, math.sin(kappa1) * math.cos(kappa1) / (solidity * math.cos(stagger)))


def make_tube(t: dict, kappa1: float, kappa2: float, solidity: float) -> Tube:
    return Tube(name=t["name"], r1=t["r1"], r2=t["r2"], A1=t["A1"], A2=t["A2"], kappa1=kappa1, kappa2=kappa2,
                solidity=solidity, covered_fraction=covered_fraction(kappa1, kappa2, solidity))


def kappa2_for_pr(t: dict, kappa1: float, solidity: float, target: float, m: float, omega: float,
                  Tt: float, Pt: float, gas: Gas) -> float:
    """Exit metal angle that gives the target tube pressure ratio (scan in 1 deg steps, then bisection)."""
    def pr(k2):
        return solve_tube(make_tube(t, kappa1, k2, solidity), m, omega, Tt, Pt, gas).Pt_ratio

    hi = kappa1 - math.radians(1.0)
    if pr(hi) > target:
        raise ValueError(f"{t['name']}: PR {target} below the 1 deg camber value")
    k2 = hi
    while k2 > KAPPA2_MIN:
        lo = k2 - math.radians(1.0)
        if pr(lo) >= target:
            for _ in range(60):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if pr(mid) >= target else (lo, mid)
            return (lo + hi) / 2
        k2, hi = lo, lo
    raise ValueError(f"{t['name']}: PR {target} not reached down to kappa2 {math.degrees(KAPPA2_MIN)} deg")


def df_limit(bl: dict, span: float) -> float:
    """Local DF limit, linear in inlet span fraction between the hub and tip values."""
    assert bl["df_limit_distribution"]["value"] == "linear"
    return v(bl["df_limit_hub"]) + (v(bl["df_limit_tip"]) - v(bl["df_limit_hub"])) * span


def design_tube(t: dict, target: float, df_target: float, m: float, omega: float, Tt: float, Pt: float,
                bl: dict, gas: Gas) -> dict:
    """Metal angles and solidity of one tube: PR = target, DF = df_target within the solidity bounds."""
    s_min, s_max = v(bl["solidity_min"]), v(bl["solidity_max"])
    incidence = math.radians(v(bl["design_incidence"]))
    beta1 = solve_tube(make_tube(t, 1.0, 0.5, 1.5), m, omega, Tt, Pt, gas).beta1  # inlet does not depend on the blade
    kappa1 = beta1 - incidence

    def at(sigma):
        k2 = kappa2_for_pr(t, kappa1, sigma, target, m, omega, Tt, Pt, gas)
        return k2, solve_tube(make_tube(t, kappa1, k2, sigma), m, omega, Tt, Pt, gas).diffusion_factor

    note = None
    k2_lo, df_lo = at(s_min)
    if df_lo <= df_target:
        sigma, k2, note = s_min, k2_lo, "solidity at its lower bound; DF below target"
    else:
        k2_hi, df_hi = at(s_max)
        if df_hi > df_target:
            sigma, k2, note = s_max, k2_hi, "solidity at its upper bound; DF above target"
        else:
            lo, hi = s_min, s_max
            for _ in range(40):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if at(mid)[1] > df_target else (lo, mid)
            sigma = (lo + hi) / 2
            k2 = at(sigma)[0]
    return {"kappa1": kappa1, "kappa2": k2, "solidity": sigma, "note": note}


def tip_relative_mach(r_tip: float, omega: float, outer, Tt: float, gas: Gas) -> float:
    """Inlet relative Mach at the tip radius with the axial velocity of the outermost tube."""
    T1 = Tt - outer.V1 ** 2 / (2 * gas.cp)
    return math.hypot(outer.V1, omega * r_tip) / math.sqrt(gas.gamma * gas.R * T1)


def root_stress(rho: float, omega: float, r_hub: float, r_tip: float, taper: float) -> float:
    """Centrifugal stress at the root of a blade whose section area falls linearly from root to tip."""
    L = r_tip - r_hub
    return rho * omega ** 2 * L * (r_hub + L / 2 - (1 - taper) * (r_hub / 2 + L / 3))


def mechanical(p: dict, ann: dict, omega: float) -> dict:
    ti = read_yaml(MATERIALS)["materials"]["ti6al4v"]
    rho, sy, uts = v(ti["density"]), v(ti["yield_strength"]), v(ti["ultimate_tensile_strength"])
    mech = p["mechanical"]
    taper, sf = v(mech["taper_ratio"]), v(mech["safety_factor"])
    sigma = root_stress(rho, omega, ann["r_hub1"], ann["r_tip1"], taper) / 1e6
    sigma_uniform = root_stress(rho, omega, ann["r_hub1"], ann["r_tip1"], 1.0) / 1e6
    allowable = sy / sf
    return {
        "method": "[G] centrifugal stress at the blade root, linear section-area taper from inlet hub to tip "
                  "radius (root at the inlet hub radius, the longer span); no gas bending, dovetail or platform load",
        "density_kg_m3": rho, "density_tag": "KS (tools/data/materials.yaml ti6al4v, Mirghani 2023 Table 2 p. 17)",
        "taper_ratio": taper, "taper_tag": "T",
        "root_stress_MPa": round(sigma, 1), "root_stress_uniform_blade_MPa": round(sigma_uniform, 1),
        "strength_used": "yield_strength", "yield_strength_MPa": sy, "uts_MPa": uts,
        "strength_note": "[KS] yield, not UTS: the root must not yield under steady load; safety factor [T]",
        "safety_factor": sf, "allowable_MPa": round(allowable, 1),
        "margin": round(allowable / sigma - 1, 3), "margin_uniform_blade": round(allowable / sigma_uniform - 1, 3),
        "tag": "H",
    }


def deg(x: float) -> float:
    return round(math.degrees(x), 3)


def run(params: dict | None = None, icd: dict | None = None, gas: Gas = Gas()) -> dict:
    p = params or read_yaml(PARAMS)
    icd = icd or read_icd("M1 agent")
    inp = icd_inputs(icd)
    ann = annulus(p, inp)
    omega = inp["rpm"] * 2 * math.pi / 60
    Tt, Pt = inp["Tt2"], inp["Pt2"]
    layout = tube_layout(p, ann)
    total_area = sum(t["A1"] for t in layout)
    bl = p["blading"]
    z = int(v(bl["blade_count"]))

    designs = []
    for t in layout:
        target = inp["FPR"] if t["stream"] == "outer" else inp["pr_fan_inner"]
        m = inp["W2"] * t["A1"] / total_area
        t["span"] = (t["r1"] - ann["r_hub1"]) / (ann["r_tip1"] - ann["r_hub1"])
        t["df_limit"] = df_limit(bl, t["span"])
        designs.append(design_tube(t, target, t["df_limit"], m, omega, Tt, Pt, bl, gas))
    tubes = [make_tube(t, d["kappa1"], d["kappa2"], d["solidity"]) for t, d in zip(layout, designs)]
    res = solve_rotor(tubes, inp["W2"], omega, Tt, Pt, gas)  # the validated route of A-1

    rows = []
    for t, d, tube, r in zip(layout, designs, tubes, res):
        pitch = 2 * math.pi * t["r1"] / z
        Vm1 = r.V1
        rows.append({
            "name": t["name"], "stream": t["stream"], "r1_m": round(t["r1"], 5), "r2_m": round(t["r2"], 5),
            "A1_m2": round(t["A1"], 5), "A2_m2": round(t["A2"], 5), "mass_flow_kg_s": round(r.mass_flow, 4),
            "U1_m_s": round(r.U1, 2), "U2_m_s": round(tube.r2 * omega, 2), "V1_m_s": round(r.V1, 2),
            "W1_m_s": round(r.W1, 2), "beta1_deg": deg(r.beta1), "M1rel": round(r.M1rel, 4),
            "Vm2_m_s": round(r.Vm2, 2), "Vt2_m_s": round(r.Vt2, 2), "V2_m_s": round(math.hypot(r.Vm2, r.Vt2), 2),
            "W2_m_s": round(r.W2, 2), "beta2_deg": deg(r.beta2), "M2rel": round(r.M2rel, 4),
            "Vm2_over_Vm1": round(r.Vm2 / Vm1, 4),
            "kappa1_deg": deg(tube.kappa1), "kappa2_deg": deg(tube.kappa2), "camber_deg": deg(tube.kappa1 - tube.kappa2),
            "incidence_deg": deg(r.incidence), "deviation_deg": deg(r.deviation),
            "solidity": round(tube.solidity, 4), "pitch_m": round(pitch, 5), "chord_m": round(tube.solidity * pitch, 5),
            "covered_fraction": round(tube.covered_fraction, 4),
            "span_fraction": round(t["span"], 4), "diffusion_factor": round(r.diffusion_factor, 4),
            "DF_limit": round(t["df_limit"], 4),
            "DF_check": "pass" if r.diffusion_factor <= t["df_limit"] + DF_TOL else "fail", "D_eq": round(r.deq, 4),
            "loss_profile": round(r.loss_profile, 5), "loss_shock": round(r.loss_shock, 5),
            "M_passage": round(r.M_passage, 4), "Pt_ratio": round(r.Pt_ratio, 5), "Tt_ratio": round(r.Tt_ratio, 5),
            "efficiency": round(r.efficiency, 5), "notes": r.notes + ([d["note"]] if d["note"] else []),
        })

    streams = {}
    for name in ("outer", "inner"):
        sel = [r for r, t in zip(res, layout) if t["stream"] == name]
        avg = mass_averaged(sel, gas)
        streams[name] = {"mass_flow_kg_s": avg["mass_flow"], "Pt_ratio": avg["Pt_ratio"], "Tt_ratio": avg["Tt_ratio"],
                         "efficiency": avg["efficiency"], "Tt_exit_K": Tt * avg["Tt_ratio"],
                         "power_MW": avg["mass_flow"] * gas.cp * Tt * (avg["Tt_ratio"] - 1) / 1e6}
    overall = mass_averaged(res, gas)

    achieved = {
        "FPR": streams["outer"]["Pt_ratio"], "eta_fan_outer": streams["outer"]["efficiency"],
        "pr_fan_inner": streams["inner"]["Pt_ratio"], "eta_fan_inner": streams["inner"]["efficiency"],
        "W2": overall["mass_flow"], "W13": streams["outer"]["mass_flow_kg_s"], "W21": streams["inner"]["mass_flow_kg_s"],
        "T13": streams["outer"]["Tt_exit_K"], "T21": streams["inner"]["Tt_exit_K"],
        "power_outer_fan": streams["outer"]["power_MW"], "power_inner_fan": streams["inner"]["power_MW"],
    }
    checks = check_budget("M1", achieved)
    dfs = [r.diffusion_factor for r in res]
    sols = [t.solidity for t in tubes]
    chords = [row["chord_m"] for row in rows]
    tip_mrel = tip_relative_mach(ann["r_tip1"], omega, res[-1], Tt, gas)

    return {
        "description": "M1 fan rotor design at the M0 design point (SLS ISA, max take-off); generated by "
                       "engine/M1_inlet_fan/analysis/fan_design.py, do not edit",
        "icd_revision": icd["source"]["revision"],
        "inputs": {"tag": "H/KS from the ICD", "W2_kg_s": inp["W2"], "W21_kg_s": inp["W21"], "Tt2_K": Tt,
                   "Pt2_Pa": Pt, "rotor_speed_rpm": inp["rpm"], "rotor_speed_tag": "KS (Girão 2023 via ICD)",
                   "FPR_target": inp["FPR"], "pr_fan_inner_target": inp["pr_fan_inner"]},
        "annulus": {
            "tag": "H from T inputs",
            "r_tip1_m": round(ann["r_tip1"], 5), "r_hub1_m": round(ann["r_hub1"], 5),
            "r_split1_m": round(ann["r_split1"], 5), "r_tip2_m": round(ann["r_tip2"], 5),
            "r_hub2_m": round(ann["r_hub2"], 5), "r_split2_m": round(ann["r_split2"], 5),
            "inlet_area_m2": round(ann["area1"], 5), "exit_area_m2": round(ann["area2"], 5),
            "icd_fan_face_area_m2": inp["fan_face_area"],
            "fan_face_area_deviation": round(ann["fan_face_area_deviation"], 5),
            "fan_face_area_check": "pass" if abs(ann["fan_face_area_deviation"]) <= AREA_CHECK else "fail",
            "core_share_W21_W2": round(ann["core_share"], 5),
            "splitter_method": "inlet area share of the core tubes = W21/W2 (uniform inlet, solve_rotor splits by area)",
        },
        "summary": {
            "tag": "H",
            "tip_M1rel": round(tip_mrel, 4), "U_tip_m_s": round(omega * ann["r_tip1"], 2),
            "DF_min": round(min(dfs), 4), "DF_max": round(max(dfs), 4),
            "DF_limit": f"{v(bl['df_limit_hub'])} hub to {v(bl['df_limit_tip'])} tip, linear in span [KS Abrisha p. 38; T]",
            "DF_check": "pass" if all(row["DF_check"] == "pass" for row in rows) else "fail",
            "solidity_min": round(min(sols), 4), "solidity_max": round(max(sols), 4),
            "chord_min_m": min(chords), "chord_max_m": max(chords),
            "outer": {k: round(x, 5) for k, x in streams["outer"].items()},
            "inner": {k: round(x, 5) for k, x in streams["inner"].items()},
            "overall": {k: round(x, 5) for k, x in overall.items()},
            "not_modelled": "OGV loss, inlet recovery, endwall and tip clearance loss, radial equilibrium; "
                            "efficiencies are therefore optimistic",
        },
        "tubes": rows,
        "mechanical": mechanical(p, ann, omega),
        "achieved": {k: round(x, 6) for k, x in achieved.items()},
        "budget_check": checks,
    }


def main() -> None:
    result = run()
    write_yaml(OUT, result)
    s = result["summary"]
    print(f"tip M1rel {s['tip_M1rel']}  DF {s['DF_min']}..{s['DF_max']}  solidity {s['solidity_min']}..{s['solidity_max']}")
    print("annulus", result["annulus"]["fan_face_area_check"], result["annulus"]["fan_face_area_deviation"],
          "r_split1", result["annulus"]["r_split1_m"])
    for r in result["tubes"]:
        print(f"{r['name']} {r['stream']:5} M1rel {r['M1rel']:.3f} b1 {r['beta1_deg']:6.2f} k2 {r['kappa2_deg']:6.2f} "
              f"b2 {r['beta2_deg']:6.2f} sig {r['solidity']:.3f} DF {r['diffusion_factor']:.3f}/{r['DF_limit']:.3f} PR {r['Pt_ratio']:.4f} "
              f"eta {r['efficiency']:.4f} Vm2/Vm1 {r['Vm2_over_Vm1']:.3f} {r['notes']}")
    m = result["mechanical"]
    print(f"root stress {m['root_stress_MPa']} MPa (uniform {m['root_stress_uniform_blade_MPa']}), "
          f"allowable {m['allowable_MPa']}, margin {m['margin']}")
    for c in result["budget_check"]:
        print(f"{c['result']:4} {c['item']}: achieved {c['achieved']:.5g} budget {c['budget']} dev {c.get('deviation', '')}")


if __name__ == "__main__":
    main()
