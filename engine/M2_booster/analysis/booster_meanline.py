"""M2 booster meanline, 3 stages on the LP shaft (aero_method.md meanline plan steps 1-7, R-AM2.1-4, R-KV2.1).

Inputs read at run time, never copied:
- ICD via core.budgets.read_icd: station 21 Tt/Pt/W, pr_booster, eta_booster (isentropic, see below),
  duct_25_24, station 24/25 states for the consistency check, N1 = shafts.LP.speed_refs.girao_nominal [KS].
- M1 station 21 annulus: engine/M1_inlet_fan/geometry/flowpath.yaml (M2_station_21, read-only, rev014).
- Rotor blade counts: rules/known_values.md table (fixed inputs [KS], R-AM2.3).
- Method choices: analysis/booster_params.yaml.
- Spanwise distribution (aero_method.md, step 3): booster_params spanwise_distribution; tp1523_shape reads the
  hub/mean/tip shape ratios from learning/tp1523_reference.yaml (a1_case rotor 23B, stator20_exit) [T transfer].
eta_booster is an isentropic efficiency: engine/M0_engine/analysis/cycle.py lines 11 and 75 ("isentropic
efficiencies"), used in compressor_is at line 193. Each stage gets the same polytropic efficiency, solved so that
the overall isentropic efficiency equals eta_booster [H] (no efficiency prediction, ADR-015).

The code gives velocity triangles, angles, DF, solidity, chords, blade counts and annulus radii only. Rule checks
(R-AM2.2 DF limits, TP-1523 tip solidity range, hub/tip vs the rig) are reported, never tuned away. Rotor counts
and chords are fixed by R-AM2.3; only the stator count follows from R-KV2.1.

Validation status: A-1 (a1_validation.py) checks the section code with the rig's tabulated distribution. Section
values are [H] only if A-1 passes and the booster spanwise distribution is not a [T] choice; otherwise [T].

Run: python -m engine.M2_booster.analysis.booster_meanline  (writes analysis/meanline_results.yaml)
"""

import math
import re
from pathlib import Path

from core.budgets import check_budget, read_icd
from core.util import read_yaml, write_yaml
from engine.M2_booster.analysis import a1_validation
from engine.M2_booster.analysis import stage_aero as sa
from engine.M2_booster.analysis.a1_validation import section_shapes, table
from tools.thermo import NasaGas, compressor, compressor_isentropic_eff

ROOT = Path(__file__).resolve().parents[3]
M2 = ROOT / "engine" / "M2_booster"
PARAMS_FILE = M2 / "analysis" / "booster_params.yaml"
KNOWN_VALUES = M2 / "rules" / "known_values.md"
REF_FILE = M2 / "learning" / "tp1523_reference.yaml"
FLOWPATH_M1 = ROOT / "engine" / "M1_inlet_fan" / "geometry" / "flowpath.yaml"
OUT_FILE = M2 / "analysis" / "meanline_results.yaml"
Z_SEARCH_SOLIDITY = 4.0  # stop the stator count search at this tip solidity (search bound only) [T]


def rotor_counts(path: Path = KNOWN_VALUES) -> list[int]:
    """Rotor blade counts from the known_values.md table rows '| Booster stage n | z | [KS] | ... |'."""
    rows = re.findall(r"^\|\s*Booster stage (\d+)\s*\|\s*(\d+)\s*\|\s*\[KS\]", path.read_text(encoding="utf-8"), re.M)
    counts = dict((int(s), int(z)) for s, z in rows)
    return [counts[i] for i in sorted(counts)]


def poly_eff_for(gas, Tt: float, pr: float, eta_is: float) -> float:
    lo, hi = eta_is - 0.1, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if compressor_isentropic_eff(Tt, pr, mid, gas) < eta_is else (lo, mid)
    return (lo + hi) / 2


def p(params: dict, key: str):
    return params[key]["value"]


def stator_count(gas, inlet: sa.Plane, exit_: sa.Plane, chord: float, neighbours: tuple[int, ...],
                 df_limit: float) -> tuple[int, bool]:
    """R-KV2.1: smallest count with every section DF <= limit, then the next count that differs from the
    adjacent rotor counts. Returns (z, DF limit met)."""
    r_tip = (inlet.r_tip + exit_.r_tip) / 2
    z_max = math.ceil(Z_SEARCH_SOLIDITY * 2 * math.pi * r_tip / chord)
    z_found, met = None, True
    for z in range(2, z_max + 1):
        if all(sa.stator_section(gas, inlet, exit_, s, chord, z)["DF"] <= df_limit for s in sa.SECTIONS):
            z_found = z
            break
    if z_found is None:
        z_found, met = z_max, False
    while z_found in neighbours:
        z_found += 1
    return z_found, met


def spanwise_shapes(params: dict, ref: dict | None = None) -> dict:
    """Shape ratios (hub, mean, tip) for the booster (aero_method.md Spanwise distribution)."""
    kind = p(params, "spanwise_distribution")
    ones = (1.0, 1.0, 1.0)
    if kind == "free_vortex":
        return {"work": ones, "rotor_exit_vx": ones, "stator_exit_vx": ones}
    if kind != "tp1523_shape":
        raise ValueError(f"unknown spanwise_distribution {kind!r}")
    ref = ref or read_yaml(REF_FILE)
    rig = section_shapes({r["station"]: r for r in table(ref, "a1_case")})
    st = {r["station"]: r for r in table(ref, "stator20_exit")}
    return {"work": rig["work"], "rotor_exit_vx": rig["vx_out"],
            "stator_exit_vx": tuple(st[s]["v_out"] / st["mid"]["v_out"] for s in ("hub", "mid", "tip"))}


ANNULUS_RULES = {"constant_hub_constant_axial_mach": "hub", "constant_mean_constant_axial_mach": "mean",
                 "constant_tip_constant_axial_mach": "tip"}


def stage_prs(gas, Tt21: float, pr: float, e_poly: float, n: int, split) -> list[float]:
    """Equal PR (plan step 3) or work fractions of the total enthalpy rise -> stage PR at constant e_poly [H]."""
    if split == "equal_stage_pressure_ratio":
        return [pr ** (1 / n)] * n
    w_tot = compressor(Tt21, 1.0, pr, e_poly, gas)[2]
    out, Tt = [], Tt21
    for f in split:
        Tt_out = gas.T_from_h(gas.h(Tt) + f * w_tot)
        out.append(math.exp((gas.phi(Tt_out) - gas.phi(Tt)) * e_poly / gas.R_s()))
        Tt = Tt_out
    return out


def run(icd: dict | None = None, params: dict | None = None) -> dict:
    icd = icd or read_icd("M2 booster meanline")
    params = params or read_yaml(PARAMS_FILE)
    shapes = dict(spanwise_shapes(params))
    k_tip = p(params, "tip_work_ratio_k")
    g = shapes["work"]
    shapes["work"] = (g[0], g[1], 1 + k_tip * (g[2] - 1))  # L1 tip work lever (aero_method.md), before normalisation
    normalise = p(params, "spanwise_normalisation") == "mass_and_work"
    if p(params, "spanwise_normalisation") not in ("mass_and_work", "none"):
        raise ValueError("spanwise_normalisation must be mass_and_work or none")
    gas = NasaGas()
    budget = icd["modules"]["M2"]["budget"]
    st = icd["stations"]
    s21 = read_yaml(FLOWPATH_M1)["interfaces"]["M2_station_21"]

    Tt21, Pt21, W = st["21"]["Tt"]["value"], st["21"]["Pt"]["value"] * 1e3, st["21"]["W"]["value"]
    pr, eta = budget["pr_booster"]["value"], budget["eta_booster"]["value"]
    duct = budget["duct_25_24"]["value"]
    rpm = icd["shafts"]["LP"]["speed_refs"]["girao_nominal"]["value"]
    omega = rpm * 2 * math.pi / 60
    n = p(params, "stage_count")
    zr = rotor_counts()
    if len(zr) != n:
        raise ValueError(f"{len(zr)} rotor counts in known_values.md for {n} stages")
    ar_r, ar_s = p(params, "rotor_aspect_ratio"), p(params, "stator_aspect_ratio")
    chord_scale = p(params, "rotor_chord_scale")
    split = p(params, "loss_split_rotor")
    df_tip, df_other = p(params, "df_limit_rotor_tip"), p(params, "df_limit_other")
    annulus = ANNULUS_RULES[p(params, "annulus")]

    e_poly = poly_eff_for(gas, Tt21, pr, eta)
    prs = stage_prs(gas, Tt21, pr, e_poly, n, p(params, "work_split"))

    p21 = sa.plane_from_area(gas, Tt21, Pt21, W, s21["r_hub_m"], s21["r_tip_m"], 0.0)
    mach_21 = sa.axial_mach(gas, p21)
    mach_x = mach_21 * p(params, "axial_mach_scale")
    r_fix = p21.radius(annulus)

    planes, stages = [p21], []
    inlet = p21
    for i in range(n):
        pr_stage = prs[i]
        Tt_out, Pt_out, w = compressor(inlet.Tt, inlet.Pt, pr_stage, e_poly, gas)
        ds = gas.phi(Tt_out) - gas.phi(inlet.Tt) - gas.R_s() * math.log(pr_stage)
        Pt_rotor = inlet.Pt * math.exp((gas.phi(Tt_out) - gas.phi(inlet.Tt) - split * ds) / gas.R_s())
        K = w / omega + inlet.K  # Euler work on every streamline: w = omega (r Vt)_2 - omega (r Vt)_1
        rotor_exit = sa.plane_fixed_radius(gas, Tt_out, Pt_rotor, W, mach_x, K, annulus, r_fix,
                                           (inlet.r_hub, inlet.r_tip))
        vx_r, g_r = shapes["rotor_exit_vx"], shapes["work"]
        if normalise:
            vx_r, g_r = sa.normalised_shapes(rotor_exit, vx_r, g_r)
        rotor_exit = sa.with_profile(rotor_exit, vx_r, sa.rotor_exit_swirl(inlet, rotor_exit, omega, w, g_r))
        stage_exit = sa.plane_fixed_radius(gas, Tt_out, Pt_out, W, mach_x, 0.0, annulus, r_fix,
                                           (rotor_exit.r_hub, rotor_exit.r_tip))
        vx_s = shapes["stator_exit_vx"]
        if normalise:
            vx_s = sa.normalised_shapes(stage_exit, vx_s)[0]
        stage_exit = sa.with_profile(stage_exit, vx_s)

        c_r = chord_scale * (inlet.height + rotor_exit.height) / 2 / ar_r
        rotor = {s: sa.rotor_section(gas, inlet, rotor_exit, omega, s, c_r, zr[i]) for s in sa.SECTIONS}
        c_s = (rotor_exit.height + stage_exit.height) / 2 / ar_s
        neighbours = (zr[i],) + ((zr[i + 1],) if i + 1 < n else ())
        zs, met = stator_count(gas, rotor_exit, stage_exit, c_s, neighbours, df_other)
        stator = {s: sa.stator_section(gas, rotor_exit, stage_exit, s, c_s, zs) for s in sa.SECTIONS}

        U_tip = omega * inlet.r_tip
        h_is = gas.h(gas.T_from_phi(gas.phi(inlet.Tt) + gas.R_s() * math.log(pr_stage)))
        stages.append({
            "stage": i + 1, "pr": pr_stage, "tt_ratio": Tt_out / inlet.Tt, "w": w,
            "phi": inlet.Vx / U_tip, "psi": w / U_tip ** 2, "psi_is": (h_is - gas.h(inlet.Tt)) / U_tip ** 2,
            "U_tip_inlet": U_tip, "inlet": inlet, "rotor_exit": rotor_exit, "stage_exit": stage_exit,
            "rotor": rotor, "stator": stator, "z_rotor": zr[i], "z_stator": zs, "stator_df_met": met,
            "chord_rotor": c_r, "chord_stator": c_s, "work_shape": g_r,
            "closure_rotor_exit": sa.simpson_closure(rotor_exit, g_r),
            "closure_stator_exit": sa.simpson_closure(stage_exit),
        })
        planes += [rotor_exit, stage_exit]
        inlet = stage_exit

    p24 = inlet
    Pt25 = p24.Pt * duct
    h_is = gas.h(gas.T_from_phi(gas.phi(Tt21) + gas.R_s() * math.log(p24.Pt / Pt21)))
    eta_achieved = (h_is - gas.h(Tt21)) / (gas.h(p24.Tt) - gas.h(Tt21))
    achieved = {"pr_booster": p24.Pt / Pt21, "eta_booster": eta_achieved, "duct_25_24": Pt25 / p24.Pt,
                "W25": W, "T25": p24.Tt, "power": W * (gas.h(p24.Tt) - gas.h(Tt21)) / 1e6}
    return {"gas": gas, "omega": omega, "shapes": shapes, "rpm": rpm, "mach_x": mach_x, "mach_21": mach_21,
            "e_poly": e_poly, "W": W, "Tt21": Tt21, "Pt21": Pt21,
            "stages": stages, "p21": p21, "p24": p24, "Pt25": Pt25, "achieved": achieved,
            "budget_rows": check_budget("M2", achieved), "params": params, "icd": icd}


# --- checks and output --------------------------------------------------------------

def blade_table_ranges(ref: dict) -> dict:
    """TP-1523 design-stage section solidity range per row type and station (blade tables 8-17) [K]."""
    t = ref["blade_tables"]
    out = {}
    for r in (dict(zip(t["columns"], row)) for row in t["rows"]):
        if r["solidity"] is None:
            continue
        key = (r["row"].split()[0], {"mid": "mean"}.get(r["station"], r["station"]))
        lo, hi = out.get(key, (r["solidity"], r["solidity"]))
        out[key] = (min(lo, r["solidity"]), max(hi, r["solidity"]))
    return out


def rule_checks(res: dict, ref: dict, a1: dict) -> list[dict]:
    """R-AM2.2 DF limits and TP-1523 range checks (A-3). Reported, never tuned away."""
    pr_ = res["params"]
    df_tip, df_other = p(pr_, "df_limit_rotor_tip"), p(pr_, "df_limit_other")
    lo, hi = p(pr_, "solidity_tip_range")
    rig_ht = ref["rig"]["hub_tip_ratio"]["value"]
    ranges = blade_table_ranges(ref)
    rig_hub = next(r["section"] for r in a1["rows"] if r["station"] == "hub")
    rig_psi_hub = (rig_hub["U2"] * rig_hub["Vt2"] - rig_hub["U1"] * rig_hub["Vt1"]) / rig_hub["U2"] ** 2
    rig_turn_hub = rig_hub["beta1"] - rig_hub["beta2"]
    rows = []
    for s in res["stages"]:
        for row in ("rotor", "stator"):
            for sec in sa.SECTIONS:
                limit = df_tip if (row == "rotor" and sec == "tip") else df_other
                df = s[row][sec]["DF"]
                rows.append({"check": "R-AM2.2 DF", "stage": s["stage"], "row": row, "section": sec,
                             "value": round(df, 4), "limit": limit, "margin": round(limit - df, 4),
                             "result": "pass" if df <= limit else "fail"})
            sig = s[row]["tip"]["solidity"]
            rows.append({"check": "tip solidity in TP-1523 Table 1 range", "stage": s["stage"], "row": row,
                         "section": "tip", "value": round(sig, 4), "limit": [lo, hi],
                         "result": "pass" if lo <= sig <= hi else "outside (open issue)"})
            for sec in ("hub", "mean"):
                r_lo, r_hi = ranges[(row, sec)]
                sig = s[row][sec]["solidity"]
                rows.append({"check": "section solidity vs TP-1523 design-stage blade tables (info, #57)",
                             "stage": s["stage"], "row": row, "section": sec, "value": round(sig, 4),
                             "limit": [r_lo, r_hi], "result": "inside" if r_lo <= sig <= r_hi else "outside"})
        for row, plane in (("rotor", s["inlet"]), ("stator", s["rotor_exit"])):
            ht = plane.hub_tip
            rows.append({"check": "hub/tip vs TP-1523 rig (#57)", "stage": s["stage"], "row": row, "section": "LE",
                         "value": round(ht, 4), "limit": rig_ht,
                         "result": "outside (below the only tested value, #57)" if ht < rig_ht else "at or above rig"})
        hub = s["rotor"]["hub"]
        psi_hub = (hub["U2"] * hub["Vt2"] - hub["U1"] * hub["Vt1"]) / hub["U2"] ** 2
        rows.append({"check": "rotor hub section loading w_hub / U_hub^2 (Euler) vs TP-1523 rotor 23B A-1 (info, #57)",
                     "stage": s["stage"], "row": "rotor", "section": "hub", "value": round(psi_hub, 4),
                     "limit": round(rig_psi_hub, 4), "result": "above rig" if psi_hub > rig_psi_hub
                     else "at or below rig"})
        turn = hub["beta1"] - hub["beta2"]
        rows.append({"check": "rotor hub relative turning, deg, vs TP-1523 rotor 23B A-1 run (info, #57)",
                     "stage": s["stage"], "row": "rotor", "section": "hub", "value": round(turn, 2),
                     "limit": round(rig_turn_hub, 2), "result": "above rig" if turn > rig_turn_hub else "at or below rig"})
    return rows


def _r(x, n=4):
    return round(float(x), n)


def _plane(pl: sa.Plane, gas) -> dict:
    s = pl.mean_static(gas)
    return {"Tt": _r(pl.Tt, 2), "Pt_kPa": _r(pl.Pt / 1e3, 3), "r_hub": _r(pl.r_hub, 5), "r_tip": _r(pl.r_tip, 5),
            "r_mean": _r(pl.r_mean, 5), "area": _r(pl.area, 5), "hub_tip": _r(pl.hub_tip), "Vx": _r(pl.Vx, 2),
            "Vt_mean": _r(pl.vt(pl.r_mean), 2), "Ts_mean": _r(s.T, 2), "Mx": _r(pl.Vx / s.a)}


ROTOR_COLS = ["section", "r_le", "r_te", "U1", "U2", "Vx1", "Vx2", "Vt2", "W1", "W2", "beta1", "beta2", "alpha2",
              "M1rel", "W2_W1", "solidity", "DF"]
STATOR_COLS = ["section", "r_le", "r_te", "Vx1", "Vx2", "Vt1", "V1", "V2", "alpha1", "alpha2", "M1", "V2_V1",
               "solidity", "DF"]


def _table(sections: dict, cols: list[str]) -> list[list]:
    out = []
    for sec in sa.SECTIONS:
        d = sections[sec]
        out.append([sec] + [_r(d[c], 5 if c.startswith("r_") else 4) for c in cols[1:]])
    return out


def to_yaml(res: dict, a1: dict, checks: list[dict]) -> dict:
    gas = res["gas"]
    span = res["params"]["spanwise_distribution"]
    tag = "H" if (a1["passed"] and span["tag"] in ("K", "KS", "H")) else "T"
    if not a1["passed"]:
        status = "UNVALIDATED placeholder [T]: A-1 failed (analysis/a1_validation.yaml); stopping rule, no tuning"
    elif tag == "T":
        status = ("A-1 pass (section code with the rig's tabulated distribution); booster spanwise distribution "
                  f"{span['value']!r} is a [T] design choice, so section values stay [T]")
    else:
        status = "validated by A-1"
    icd = res["icd"]
    st = icd["stations"]
    consistency = []
    for name, ach, ref in (("Tt24", res["p24"].Tt, st["24"]["Tt"]["value"]),
                           ("Pt24_kPa", res["p24"].Pt / 1e3, st["24"]["Pt"]["value"]),
                           ("W24", res["W"], st["24"]["W"]["value"]),
                           ("Tt25", res["p24"].Tt, st["25"]["Tt"]["value"]),
                           ("Pt25_kPa", res["Pt25"] / 1e3, st["25"]["Pt"]["value"]),
                           ("W25", res["W"], st["25"]["W"]["value"])):
        consistency.append({"item": name, "achieved": _r(ach, 4), "icd": ref, "difference": _r(ach - ref, 5)})
    stages = []
    for s in res["stages"]:
        stages.append({
            "stage": s["stage"],
            "pr": {"value": _r(s["pr"], 5), "unit": "-", "tag": "T", "note": "equal stage PR of pr_booster (plan step 3)"},
            "tt_ratio": {"value": _r(s["tt_ratio"], 5), "unit": "-", "tag": "H"},
            "work": {"value": _r(s["w"] / 1e3, 3), "unit": "kJ/kg", "tag": "H"},
            "phi": {"value": _r(s["phi"]), "unit": "-", "tag": tag},
            "psi": {"value": _r(s["psi"]), "unit": "-", "tag": "H"},
            "psi_is": {"value": _r(s["psi_is"]), "unit": "-", "tag": "H"},
            "U_tip_inlet": {"value": _r(s["U_tip_inlet"], 2), "unit": "m/s", "tag": "H"},
            "rotor_blades": {"value": s["z_rotor"], "unit": "-", "tag": "KS", "note": "#52 p. 159, known_values.md (R-AM2.3)"},
            "stator_vanes": {"value": s["z_stator"], "unit": "-", "tag": "T",
                             "note": "R-KV2.1" + ("" if s["stator_df_met"] else "; DF limit not met within the search")},
            "rotor_chord": {"value": _r(s["chord_rotor"], 5), "unit": "m", "tag": "T", "note": f"height / AR {p(res['params'], 'rotor_aspect_ratio')} x chord scale {p(res['params'], 'rotor_chord_scale')} (R-AM2.3, L3)"},
            "stator_chord": {"value": _r(s["chord_stator"], 5), "unit": "m", "tag": "T", "note": f"height / AR {p(res['params'], 'stator_aspect_ratio')} (R-AM2.3)"},
            "spanwise_closure": {
                "tag": "H", "note": "Simpson 1/4/1 on r Vx, uniform density; after the aero_method.md Spanwise normalisation rule (" + p(res["params"], "spanwise_normalisation") + ")",
                "rotor_te_mass_flow_ratio": _r(s["closure_rotor_exit"]["mass_flow_ratio"]),
                "rotor_mass_averaged_work_ratio": _r(s["closure_rotor_exit"]["work_ratio"]),
                "stator_te_mass_flow_ratio": _r(s["closure_stator_exit"]["mass_flow_ratio"])},
            "planes": {"tag": tag, "rotor_le": _plane(s["inlet"], gas), "rotor_te": _plane(s["rotor_exit"], gas),
                       "stator_te": _plane(s["stage_exit"], gas)},
            "rotor_sections": {"tag": tag, "units": "m, m/s, deg", "columns": ROTOR_COLS,
                               "rows": _table(s["rotor"], ROTOR_COLS)},
            "stator_sections": {"tag": tag, "units": "m, m/s, deg", "columns": STATOR_COLS,
                                "rows": _table(s["stator"], STATOR_COLS)},
        })
    return {
        "description": "M2 booster meanline (step 4: normalised spanwise profile, design levers); generated by engine/M2_booster/analysis/booster_meanline.py, "
                       "do not edit by hand. Inputs: ICD (read_icd), M1 flowpath station 21, known_values.md, "
                       "booster_params.yaml.",
        "icd_revision": icd["source"]["revision"],
        "validation": {"a1_result": "pass" if a1["passed"] else "fail", "status": status},
        "inputs": {
            "N1": {"value": res["rpm"], "unit": "rpm", "tag": "KS", "note": "ICD shafts.LP.speed_refs.girao_nominal"},
            "eta_booster_definition": {"value": "isentropic", "unit": "-", "tag": "H",
                                       "note": "engine/M0_engine/analysis/cycle.py:11 and :75; compressor_is at :193"},
            "stage_polytropic_efficiency": {"value": _r(res["e_poly"], 5), "unit": "-", "tag": "H",
                                            "note": "equivalent of eta_booster over pr_booster (ADR-015)"},
            "spanwise_distribution": {"value": span["value"], "unit": "-", "tag": span["tag"],
                                      "note": "aero_method.md Spanwise distribution; booster_params.yaml"},
            "shape_ratios": {"tag": "H", "note": "hub, mean, tip; mean = 1; from TP-1523 [K] via the rule above [T]",
                             **{k: [_r(x) for x in v] for k, v in res["shapes"].items()}},
            "axial_mach_station21": {"value": _r(res["mach_21"]), "unit": "-", "tag": "H",
                                     "note": "1-D (mean) value at station 21 (M1 annulus)"},
            "axial_mach_booster": {"value": _r(res["mach_x"]), "unit": "-", "tag": "T",
                                   "note": "station 21 value x axial_mach_scale, constant on every plane downstream "
                                           "(plan step 5)"},
            "annulus": {"value": p(res["params"], "annulus"), "unit": "-", "tag": "T",
                        "note": "plan step 5; lever L2 (aero_method.md Design levers)"},
            "levers": {"tag": "T", "note": "aero_method.md Design levers; booster_params.yaml",
                       **{k: p(res["params"], k) for k in ("tip_work_ratio_k", "rotor_chord_scale", "work_split",
                                                            "spanwise_normalisation", "axial_mach_scale")}},
        },
        "station_21": _plane(res["p21"], gas),
        "stages": stages,
        "station_24": _plane(res["p24"], gas),
        "station_25": {"Tt": _r(res["p24"].Tt, 2), "Pt_kPa": _r(res["Pt25"] / 1e3, 3), "W": _r(res["W"], 4),
                       "tag": "H", "note": "duct_25_24 applied to station 24; duct annulus not modelled: station 25 annulus = station 24 annulus [T] (geometry/flowpath.yaml interfaces.M3_station_25)"},
        "consistency_vs_icd": consistency,
        "budget_check": [{k: (_r(v, 6) if isinstance(v, float) else v) for k, v in row.items()}
                         for row in res["budget_rows"]],
        "rule_checks": checks,
    }


def main() -> None:
    ref = read_yaml(REF_FILE)
    a1 = a1_validation.run(ref)
    res = run()
    checks = rule_checks(res, ref, a1)
    data = to_yaml(res, a1, checks)
    write_yaml(OUT_FILE, data)
    print("A-1:", data["validation"]["a1_result"], "|", data["validation"]["status"])
    for s in data["stages"]:
        print(f"stage {s['stage']}: PR {s['pr']['value']} z_r {s['rotor_blades']['value']} z_s "
              f"{s['stator_vanes']['value']} c_r {s['rotor_chord']['value']} c_s {s['stator_chord']['value']}")
        for name in ("rotor_sections", "stator_sections"):
            cols = s[name]["columns"]
            for row in s[name]["rows"]:
                d = dict(zip(cols, row))
                print(f"  {name[:6]} {d['section']:<4} DF {d['DF']:.4f} sigma {d['solidity']:.4f}")
    for row in data["rule_checks"]:
        if row["result"] not in ("pass", "inside", "at or below rig", "at or above rig"):
            print("CHECK", row)
    for row in data["budget_check"]:
        print("BUDGET", row["item"], row["achieved"], row["budget"], row["result"])
    for row in data["consistency_vs_icd"]:
        print("ICD", row)


if __name__ == "__main__":
    main()
