"""M2 open issue #64: one-lever-at-a-time sensitivity of the booster section DF (R-AM2.2), plus the closure check.

Read-only study: it never writes booster_params.yaml, meanline_results.yaml, bom or geometry. Every variant is a
stated rule, applied once (no iteration toward a DF target). The baseline row reproduces booster_meanline.run.

Levers (one at a time; the rest stay at the booster_params.yaml values):
- annulus: constant hub (baseline, plan step 5), constant mean radius, constant tip radius, each fixed at the
  station 21 value for all planes 21 -> 24; axial Mach constant at the station 21 value in all variants [T];
- work split: stage work fractions of the total booster enthalpy rise, 40/33/27 and 30/33/37, against equal stage
  PR (baseline). Same polytropic efficiency per stage, so overall PR and eta_booster are unchanged [H];
- rotor solidity: rotor chord x 0.9 / 1.1 / 1.2 with counts 74/78/74 fixed (equivalent rotor AR 2.0 / k);
  stator chord unchanged (stator count still from R-KV2.1);
- tip work ratio: g_tip = 1 + k (g_tip,rig - 1), k = 0.5 and 0 (hub ratio and Vx shapes unchanged);
- closure normalisation (#68, info lever, not in the grid): on every plane the Vx shape is divided by its Simpson
  mass-flow ratio and the work shape by its mass-averaged work ratio, so the 3-point profile carries the 1-D flow
  and work (mean section then differs from the 1-D value, against the current aero_method.md rule).
The combination grid is the full product of the lever values above (3 x 3 x 4 x 3 = 108 runs).

Closure (aero_method.md Spanwise distribution): stage_aero.simpson_closure ratios are turned into the budget items
they would move if the section profile were taken as the flow (W25 from the stage 3 stator-TE mass ratio, work from
the rotor work ratios) and checked with core.budgets.check_budget [H].

Run: python -m engine.M2_booster.analysis.sensitivity_64   (prints tables only)
"""

import itertools
import math

from core.budgets import check_budget, read_icd
from core.util import read_yaml
from engine.M2_booster.analysis import booster_meanline as bm
from engine.M2_booster.analysis import stage_aero as sa
from tools.thermo import NasaGas, compressor

ANNULUS = ("hub", "mean", "tip")
SPLITS = {"equal_pr": None, "40/33/27": (0.40, 0.33, 0.27), "30/33/37": (0.30, 0.33, 0.37)}
CHORD_SCALES = (1.0, 0.9, 1.1, 1.2)
TIP_WORK_K = (1.0, 0.5, 0.0)


def plane_fixed_radius(gas, Tt, Pt, W, mach_x, K, rule: str, r_fix: float, guess: tuple) -> sa.Plane:
    """Axial Mach given, one radius (hub, mean or tip) fixed: other radius from continuity [T]."""
    if rule == "hub":
        return sa.plane_from_mach(gas, Tt, Pt, W, r_fix, mach_x, K, guess[1])
    rh, rt = guess
    for _ in range(500):
        rm = (rh + rt) / 2
        vt = K / rm
        vx = sa._fixed_point(lambda v: mach_x * sa.static_state(gas, Tt, Pt, math.hypot(v, vt)).a, 100.0, "vx")
        area = W / (sa.static_state(gas, Tt, Pt, math.hypot(vx, vt)).rho * vx)
        if rule == "tip":
            new = (math.sqrt(r_fix ** 2 - area / math.pi), r_fix)
        elif rule == "mean":
            h = area / (2 * math.pi * r_fix)
            new = (r_fix - h / 2, r_fix + h / 2)
        else:
            raise ValueError(rule)
        if max(abs(new[0] - rh), abs(new[1] - rt)) < 1e-12:
            return sa.Plane(Tt, Pt, new[0], new[1], vx, K)
        rh, rt = new
    raise ValueError("plane_fixed_radius: no convergence")


def stage_prs(gas, Tt21, pr, e_poly, n, split) -> list[float]:
    """Equal PR (None) or work fractions of the total enthalpy rise -> stage PR at constant e_poly [H]."""
    if split is None:
        return [pr ** (1 / n)] * n
    w_tot = compressor(Tt21, 1.0, pr, e_poly, gas)[2]
    out, Tt = [], Tt21
    for f in split:
        Tt_out = gas.T_from_h(gas.h(Tt) + f * w_tot)
        out.append(math.exp((gas.phi(Tt_out) - gas.phi(Tt)) * e_poly / gas.R_s()))
        Tt = Tt_out
    return out


def normalised(plane: sa.Plane, work_shape: tuple | None = None) -> tuple:
    """Shapes rescaled so that the Simpson closure of the plane is 1 (mass flow, and work if given)."""
    c = sa.simpson_closure(plane, work_shape)
    vx = tuple(f / c["mass_flow_ratio"] for f in plane.vx_shape)
    g = None if work_shape is None else tuple(x / c["work_ratio"] for x in work_shape)
    return vx, g


def run_variant(icd, params, annulus="hub", split=None, chord_scale=1.0, tip_work_k=1.0,
                normalise: bool = False) -> dict:
    """booster_meanline.run with one or more stated levers changed (same code path otherwise)."""
    gas = NasaGas()
    shapes = dict(bm.spanwise_shapes(params))
    g = shapes["work"]
    shapes["work"] = (g[0], g[1], 1 + tip_work_k * (g[2] - 1))
    budget, st = icd["modules"]["M2"]["budget"], icd["stations"]
    s21 = read_yaml(bm.FLOWPATH_M1)["interfaces"]["M2_station_21"]
    Tt21, Pt21, W = st["21"]["Tt"]["value"], st["21"]["Pt"]["value"] * 1e3, st["21"]["W"]["value"]
    pr, eta = budget["pr_booster"]["value"], budget["eta_booster"]["value"]
    omega = icd["shafts"]["LP"]["speed_refs"]["girao_nominal"]["value"] * 2 * math.pi / 60
    n, zr = bm.p(params, "stage_count"), bm.rotor_counts()
    ar_r, ar_s = bm.p(params, "rotor_aspect_ratio"), bm.p(params, "stator_aspect_ratio")
    lsplit, df_other = bm.p(params, "loss_split_rotor"), bm.p(params, "df_limit_other")
    e_poly = bm.poly_eff_for(gas, Tt21, pr, eta)
    prs = stage_prs(gas, Tt21, pr, e_poly, n, split)

    p21 = sa.plane_from_area(gas, Tt21, Pt21, W, s21["r_hub_m"], s21["r_tip_m"], 0.0)
    mach_x = sa.axial_mach(gas, p21)
    r_fix = p21.radius({"hub": "hub", "mean": "mean", "tip": "tip"}[annulus])
    stages, inlet = [], p21
    for i in range(n):
        Tt_out, Pt_out, w = compressor(inlet.Tt, inlet.Pt, prs[i], e_poly, gas)
        ds = gas.phi(Tt_out) - gas.phi(inlet.Tt) - gas.R_s() * math.log(prs[i])
        Pt_rotor = inlet.Pt * math.exp((gas.phi(Tt_out) - gas.phi(inlet.Tt) - lsplit * ds) / gas.R_s())
        K = w / omega + inlet.K
        guess = (inlet.r_hub, inlet.r_tip)
        rotor_exit = plane_fixed_radius(gas, Tt_out, Pt_rotor, W, mach_x, K, annulus, r_fix, guess)
        vx_r, g = shapes["rotor_exit_vx"], shapes["work"]
        if normalise:
            vx_r, g = normalised(sa.with_profile(rotor_exit, vx_r), g)
        rotor_exit = sa.with_profile(rotor_exit, vx_r, sa.rotor_exit_swirl(inlet, rotor_exit, omega, w, g))
        stage_exit = plane_fixed_radius(gas, Tt_out, Pt_out, W, mach_x, 0.0, annulus, r_fix,
                                        (rotor_exit.r_hub, rotor_exit.r_tip))
        vx_s = shapes["stator_exit_vx"]
        if normalise:
            vx_s = normalised(sa.with_profile(stage_exit, vx_s))[0]
        stage_exit = sa.with_profile(stage_exit, vx_s)
        c_r = chord_scale * (inlet.height + rotor_exit.height) / 2 / ar_r
        rotor = {s: sa.rotor_section(gas, inlet, rotor_exit, omega, s, c_r, zr[i]) for s in sa.SECTIONS}
        c_s = (rotor_exit.height + stage_exit.height) / 2 / ar_s
        neighbours = (zr[i],) + ((zr[i + 1],) if i + 1 < n else ())
        zs, met = bm.stator_count(gas, rotor_exit, stage_exit, c_s, neighbours, df_other)
        stator = {s: sa.stator_section(gas, rotor_exit, stage_exit, s, c_s, zs) for s in sa.SECTIONS}
        stages.append({"stage": i + 1, "pr": prs[i], "w": w, "rotor": rotor, "stator": stator, "z_stator": zs,
                       "stator_df_met": met, "inlet": inlet, "rotor_exit": rotor_exit, "stage_exit": stage_exit,
                       "closure_rotor_exit": sa.simpson_closure(rotor_exit, g),
                       "closure_stator_exit": sa.simpson_closure(stage_exit)})
        inlet = stage_exit
    return {"stages": stages, "params": params, "gas": gas, "W": W, "Tt21": Tt21, "Pt21": Pt21,
            "e_poly": e_poly, "p24": inlet, "shapes": shapes}


def violations(res: dict) -> dict:
    """R-AM2.2 counts: DF limit per section (rotor tip 0.45, rest 0.58) and tip solidity range 0.9-2.0."""
    pr_ = res["params"]
    df_tip, df_other = bm.p(pr_, "df_limit_rotor_tip"), bm.p(pr_, "df_limit_other")
    lo, hi = bm.p(pr_, "solidity_tip_range")
    df_fail, sig_out = [], []
    for s in res["stages"]:
        for row in ("rotor", "stator"):
            for sec in sa.SECTIONS:
                lim = df_tip if (row == "rotor" and sec == "tip") else df_other
                if s[row][sec]["DF"] > lim:
                    df_fail.append(f"{s['stage']}{row[0].upper()}{sec[0]}")
            if not lo <= s[row]["tip"]["solidity"] <= hi:
                sig_out.append(f"{s['stage']}{row[0].upper()}")
    return {"df": df_fail, "sigma_tip": sig_out}


def summary(res: dict) -> dict:
    v = violations(res)
    return {
        "rotor_df": [[round(s["rotor"][sec]["DF"], 4) for sec in sa.SECTIONS] for s in res["stages"]],
        "stator_df": [[round(s["stator"][sec]["DF"], 4) for sec in sa.SECTIONS] for s in res["stages"]],
        "rotor_tip_sigma": [round(s["rotor"]["tip"]["solidity"], 4) for s in res["stages"]],
        "z_stator": [s["z_stator"] for s in res["stages"]],
        "hub_tip_le": [round(s["inlet"].hub_tip, 4) for s in res["stages"]],
        "n_df": len(v["df"]), "df_fail": v["df"], "n_sigma": len(v["sigma_tip"]), "sigma_out": v["sigma_tip"],
    }


def closure_budget(res: dict) -> dict:
    """Budget items implied by taking the Simpson section profile as the flow (not the meanline result) [H]."""
    gas, W = res["gas"], res["W"]
    ratios = [{"stage": s["stage"], **{k: round(v, 4) for k, v in s["closure_rotor_exit"].items()},
               "stator_te_mass_flow_ratio": round(s["closure_stator_exit"]["mass_flow_ratio"], 4)}
              for s in res["stages"]]
    Tt, lnpr = res["Tt21"], 0.0
    for s in res["stages"]:
        Tt_out = gas.T_from_h(gas.h(Tt) + s["w"] * s["closure_rotor_exit"]["work_ratio"])
        lnpr += (gas.phi(Tt_out) - gas.phi(Tt)) * res["e_poly"] / gas.R_s()
        Tt = Tt_out
    implied = {"W25": W * res["stages"][-1]["closure_stator_exit"]["mass_flow_ratio"],
               "pr_booster": math.exp(lnpr), "T25": Tt}
    return {"ratios": ratios, "implied": implied, "rows": check_budget("M2", implied)}


def one_lever_variants() -> list[tuple[str, str, dict]]:
    out = [("baseline", "-", {})]
    out += [("annulus", f"constant {a} radius", {"annulus": a}) for a in ANNULUS[1:]]
    out += [("work split", k, {"split": v}) for k, v in SPLITS.items() if v is not None]
    out += [("rotor solidity", f"chord x {k}", {"chord_scale": k}) for k in CHORD_SCALES[1:]]
    out += [("tip work ratio", f"k = {k}", {"tip_work_k": k}) for k in TIP_WORK_K[1:]]
    out += [("closure normalisation (#68)", "f, g / Simpson ratio", {"normalise": True})]
    out += [("best grid + normalisation", "tip, equal PR, chord x 1.1, k = 0",
             {"annulus": "tip", "chord_scale": 1.1, "tip_work_k": 0.0, "normalise": True})]
    return out


def combination_grid(icd, params) -> list[dict]:
    rows = []
    for a, (sn, sv), c, k in itertools.product(ANNULUS, SPLITS.items(), CHORD_SCALES, TIP_WORK_K):
        s = summary(run_variant(icd, params, a, sv, c, k))
        rows.append({"annulus": a, "split": sn, "chord_scale": c, "tip_work_k": k, **s})
    return rows


def study(icd=None, params=None, grid: bool = True) -> dict:
    icd = icd or read_icd("M2 sensitivity #64")
    params = params or read_yaml(bm.PARAMS_FILE)
    base = run_variant(icd, params)
    rows = [{"lever": lv, "variant": name, "kwargs": kw, **summary(run_variant(icd, params, **kw))}
            for lv, name, kw in one_lever_variants()]
    out = {"rows": rows, "closure": closure_budget(base),
           "shapes": {k: [round(x, 4) for x in v] for k, v in base["shapes"].items()}}
    if grid:
        out["grid"] = combination_grid(icd, params)
    return out


def main() -> None:
    res = study()
    print("shapes", res["shapes"])
    for r in res["rows"]:
        print(f"{r['lever']:<15}{r['variant']:<22} R {r['rotor_df']} S {r['stator_df']} zs {r['z_stator']} "
              f"sig_tip {r['rotor_tip_sigma']} h/t {r['hub_tip_le']} nDF {r['n_df']} {r['df_fail']} "
              f"nSig {r['n_sigma']} {r['sigma_out']}")
    c = res["closure"]
    print("closure ratios", c["ratios"])
    for row in c["rows"]:
        print("CLOSURE BUDGET", row["item"], round(row["achieved"], 4), row["budget"],
              round(row["deviation"], 4), row["tolerance"], row["result"])
    grid = sorted(res["grid"], key=lambda r: (r["n_df"] + r["n_sigma"], r["n_df"]))
    print("grid runs", len(grid), "min DF violations", min(r["n_df"] for r in grid),
          "zero-DF combos", sum(r["n_df"] == 0 for r in grid))
    for r in grid[:8]:
        print("GRID", r["annulus"], r["split"], r["chord_scale"], r["tip_work_k"], "R", r["rotor_df"],
              "S", r["stator_df"], "zs", r["z_stator"], "sig", r["rotor_tip_sigma"], r["df_fail"], r["sigma_out"])


if __name__ == "__main__":
    main()
