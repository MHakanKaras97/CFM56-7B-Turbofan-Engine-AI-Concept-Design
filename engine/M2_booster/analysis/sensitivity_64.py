"""M2 open issue #64: one-lever-at-a-time sensitivity of the booster section DF (R-AM2.2), lever sequence (step 4),
axial Mach sensitivity and the #68 closure check.

Read-only study: it never writes booster_params.yaml, meanline_results.yaml, bom or geometry. Every variant is
booster_meanline.run with stated parameter overrides (same code path), applied once (no iteration toward a DF
target). Step 4: the baseline uses the spanwise normalisation rule (aero_method.md "Spanwise normalisation", #68).

Levers (one at a time on the normalised step 3 baseline; the rest stay at their step 3 values):
- annulus: constant hub (baseline, plan step 5), constant mean radius, constant tip radius, each fixed at the
  station 21 value for all planes 21 -> 24; axial Mach constant at the station 21 value [T];
- work split: stage work fractions 40/33/27 and 30/33/37 of the total enthalpy rise against equal stage PR;
  same polytropic efficiency per stage, so overall PR and eta_booster are unchanged [H];
- rotor solidity: rotor chord x 0.9 / 1.1 / 1.2 with counts 74/78/74 fixed (equivalent rotor AR 2.0 / k);
- tip work ratio: g_tip = 1 + k (g_tip,rig - 1), k = 0.5 and 0 (before normalisation);
- un-normalised profile (step 3 rule, info only);
- axial Mach (task 4, sensitivity only): axial Mach downstream of station 21 x 0.9 / x 1.1.
Lever sequence (aero_method.md "Design levers"): L1 tip work k = 0, L2 constant tip radius, L3 rotor chord x 1.1,
L4 equal PR kept; a lever is kept only if it strictly reduces the R-AM2.2 DF violation count (its [G] rationale is
in the rules, written before the run). The combination grid is 3 x 3 x 4 x 3 = 108 runs on the normalised profile.

Run: python -m engine.M2_booster.analysis.sensitivity_64   (prints tables only)
"""

import copy
import itertools
import math

from core.budgets import check_budget, read_icd
from core.util import read_yaml
from engine.M2_booster.analysis import booster_meanline as bm
from engine.M2_booster.analysis import stage_aero as sa

ANNULUS = {"hub": "constant_hub_constant_axial_mach", "mean": "constant_mean_constant_axial_mach",
           "tip": "constant_tip_constant_axial_mach"}
SPLITS = {"equal_pr": "equal_stage_pressure_ratio", "40/33/27": [0.40, 0.33, 0.27], "30/33/37": [0.30, 0.33, 0.37]}
CHORD_SCALES = (1.0, 0.9, 1.1, 1.2)
TIP_WORK_K = (1.0, 0.5, 0.0)
MACH_SCALES = (0.9, 1.1)
STEP3_BASE = {"annulus": ANNULUS["hub"], "work_split": SPLITS["equal_pr"], "rotor_chord_scale": 1.0,
              "tip_work_ratio_k": 1.0, "spanwise_normalisation": "mass_and_work", "axial_mach_scale": 1.0}
LEVERS = [  # aero_method.md "Design levers", in this order
    ("L1 tip work ratio k = 0", {"tip_work_ratio_k": 0.0}),
    ("L2 constant tip radius", {"annulus": ANNULUS["tip"]}),
    ("L3 rotor chord x 1.1", {"rotor_chord_scale": 1.1}),
    ("L4 equal stage PR kept", {"work_split": SPLITS["equal_pr"]}),
]


def with_values(params: dict, values: dict) -> dict:
    out = copy.deepcopy(params)
    for k, v in values.items():
        out[k] = dict(out[k], value=v)
    return out


def run_variant(icd, params, **values) -> dict:
    return bm.run(icd=icd, params=with_values(params, values))


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


def icd_match(res: dict) -> dict:
    """Station 21 inlet and station 25 outlet Pt, Tt, W against the ICD (read_icd) and the M2 budget rows."""
    st = res["icd"]["stations"]
    p21 = res["p21"]
    diff = {"Tt21": p21.Tt - st["21"]["Tt"]["value"], "Pt21_kPa": p21.Pt / 1e3 - st["21"]["Pt"]["value"],
            "W21": res["W"] - st["21"]["W"]["value"], "Tt25": res["p24"].Tt - st["25"]["Tt"]["value"],
            "Pt25_kPa": res["Pt25"] / 1e3 - st["25"]["Pt"]["value"], "W25": res["W"] - st["25"]["W"]["value"]}
    budget_ok = all(r["result"] in ("pass", "info") for r in res["budget_rows"])
    return {"diff": {k: round(v, 4) for k, v in diff.items()}, "budget_pass": budget_ok,
            "ok": budget_ok and all(abs(v) <= 0.01 for v in diff.values())}  # ICD values carry 2-3 decimals


def summary(res: dict) -> dict:
    v = violations(res)
    return {
        "rotor_df": [[round(s["rotor"][sec]["DF"], 4) for sec in sa.SECTIONS] for s in res["stages"]],
        "stator_df": [[round(s["stator"][sec]["DF"], 4) for sec in sa.SECTIONS] for s in res["stages"]],
        "rotor_tip_sigma": [round(s["rotor"]["tip"]["solidity"], 4) for s in res["stages"]],
        "z_stator": [s["z_stator"] for s in res["stages"]],
        "hub_tip_le": [round(s["inlet"].hub_tip, 4) for s in res["stages"]],
        "r_hub_24": round(res["p24"].r_hub, 5), "r_tip_24": round(res["p24"].r_tip, 5),
        "n_df": len(v["df"]), "df_fail": v["df"], "n_sigma": len(v["sigma_tip"]), "sigma_out": v["sigma_tip"],
        "icd": icd_match(res),
    }


def closure_budget(res: dict) -> dict:
    """Budget items implied by taking the Simpson section profile as the flow (not the meanline result) [H]."""
    gas, W = res["gas"], res["W"]
    ratios = [{"stage": s["stage"], **{k: round(v, 6) for k, v in s["closure_rotor_exit"].items()},
               "stator_te_mass_flow_ratio": round(s["closure_stator_exit"]["mass_flow_ratio"], 6)}
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
    out = [("baseline (normalised)", "-", {})]
    out += [("annulus", f"constant {a} radius", {"annulus": ANNULUS[a]}) for a in ("mean", "tip")]
    out += [("work split", k, {"work_split": v}) for k, v in SPLITS.items() if k != "equal_pr"]
    out += [("rotor solidity", f"chord x {k}", {"rotor_chord_scale": k}) for k in CHORD_SCALES[1:]]
    out += [("tip work ratio", f"k = {k}", {"tip_work_ratio_k": k}) for k in TIP_WORK_K[1:]]
    out += [("axial Mach", f"x {k}", {"axial_mach_scale": k}) for k in MACH_SCALES]
    out += [("un-normalised (step 3 rule, info)", "f, g raw", {"spanwise_normalisation": "none"})]
    return out


def lever_sequence(icd, params) -> list[dict]:
    """aero_method.md Design levers: in order, keep a lever only if it strictly reduces the DF violation count."""
    current = dict(STEP3_BASE)
    base = summary(run_variant(icd, params, **current))
    rows = [{"lever": "normalised step 3 baseline", "applied": True, "before": base["n_df"], **base}]
    for name, change in LEVERS:
        trial = dict(current, **change)
        if trial == current:
            rows.append({"lever": name, "applied": False, "before": base["n_df"], "reason": "no change", **base})
            continue
        s = summary(run_variant(icd, params, **trial))
        keep = s["n_df"] < base["n_df"] and s["n_sigma"] <= base["n_sigma"] and s["icd"]["ok"]
        rows.append({"lever": name, "applied": keep, "before": base["n_df"],
                     "reason": "fewer DF violations" if keep else "violation count not reduced", **s})
        if keep:
            current, base = trial, s
    rows.append({"lever": "final", "values": current})
    return rows


def combination_grid(icd, params) -> list[dict]:
    rows = []
    for a, (sn, sv), c, k in itertools.product(ANNULUS, SPLITS.items(), CHORD_SCALES, TIP_WORK_K):
        s = summary(run_variant(icd, params, **dict(STEP3_BASE, annulus=ANNULUS[a], work_split=sv,
                                                    rotor_chord_scale=c, tip_work_ratio_k=k)))
        rows.append({"annulus": a, "split": sn, "chord_scale": c, "tip_work_k": k, **s})
    return rows


def study(icd=None, params=None, grid: bool = True) -> dict:
    icd = icd or read_icd("M2 sensitivity #64")
    params = params or read_yaml(bm.PARAMS_FILE)
    step3 = with_values(params, STEP3_BASE)
    rows = [{"lever": lv, "variant": name, "values": kw, **summary(run_variant(icd, step3, **kw))}
            for lv, name, kw in one_lever_variants()]
    seq = lever_sequence(icd, params)
    final = seq[-1]["values"]
    mach = [{"variant": f"final, axial Mach x {k}", **summary(run_variant(icd, params, **dict(final,
                                                                       axial_mach_scale=k)))}
            for k in (1.0,) + MACH_SCALES]
    out = {"rows": rows, "sequence": seq, "mach_final": mach,
           "closure": closure_budget(run_variant(icd, params, **final)),
           "closure_step3_rule": closure_budget(run_variant(icd, step3, spanwise_normalisation="none"))}
    if grid:
        out["grid"] = combination_grid(icd, params)
    return out


def _line(name, r):
    return (f"{name:<44} R {r['rotor_df']} S {r['stator_df']} zs {r['z_stator']} sig_tip {r['rotor_tip_sigma']} "
            f"h/t {r['hub_tip_le']} r24 {r['r_hub_24']}/{r['r_tip_24']} nDF {r['n_df']} {r['df_fail']} "
            f"nSig {r['n_sigma']} {r['sigma_out']} icd_ok {r['icd']['ok']}")


def main() -> None:
    res = study()
    for r in res["rows"]:
        print(_line(f"{r['lever']}: {r['variant']}", r))
    for r in res["sequence"][:-1]:
        print("SEQ", r["applied"], r.get("reason", ""), r["before"], "->", _line(r["lever"], r))
    print("FINAL", res["sequence"][-1]["values"])
    for r in res["mach_final"]:
        print("MACH", _line(r["variant"], r), r["icd"]["diff"])
    for key in ("closure", "closure_step3_rule"):
        c = res[key]
        print(key, c["ratios"])
        for row in c["rows"]:
            print("  ", row["item"], round(row["achieved"], 4), row["budget"], round(row["deviation"], 4),
                  row["tolerance"], row["result"])
    grid = sorted(res["grid"], key=lambda r: (r["n_df"] + r["n_sigma"], r["n_df"]))
    print("grid runs", len(grid), "min DF violations", min(r["n_df"] for r in grid),
          "zero-DF combos", sum(r["n_df"] == 0 for r in grid))
    for r in grid[:6]:
        print("GRID", r["annulus"], r["split"], r["chord_scale"], r["tip_work_k"], _line("", r))


if __name__ == "__main__":
    main()
