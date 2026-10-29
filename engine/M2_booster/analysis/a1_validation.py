"""A-1: M2 meanline validation on NASA TP-1523 rotor 23B at the design point (aero_method.md, analyses.md).

Step 3 method (aero_method.md "Spanwise distribution"): the case runs the same section code as the booster
(stage_aero.with_profile, rotor_exit_swirl, rotor_section) with the rig's own tabulated hub/mid/tip inputs from
Table 2(b) p. 21: radii, rpm, inlet and exit meridional velocity, zero inlet swirl, section work from the total
temperature ratio w_sec = cp Tt1 (TR_sec - 1), rig chords and blade count (Table 8 via blade_tables). No continuity,
no blockage. Outputs (exit swirl, relative angles, W1/W2, solidity, DF) are compared with Table 2(b): D at
tip/mid/hub +-0.02, exit relative flow angle +-1.5 deg, rotor PR within 1 % (mean section Euler work with the
efficiency from the PR/TR pair, Table 2(a)). No tuning: a failure is reported as is.

What it checks: the section triangles, solidity and DF given the spanwise distribution. It does not validate a
spanwise distribution that the booster chooses itself (step 3 booster shape is a [T] transfer). The PR criterion
follows from the tabulated mid-span TR and the PR/TR efficiency; it checks the code chain, not the physics.

Run: python -m engine.M2_booster.analysis.a1_validation  (writes analysis/a1_validation.yaml)
"""

import math
from pathlib import Path

from core.util import read_yaml, write_yaml
from engine.M2_booster.analysis import stage_aero as sa
from tools.meanline import diffusion_factor
from tools.thermo import ConstantCp, compressor_is

M2 = Path(__file__).resolve().parents[1]
REF_FILE = M2 / "learning" / "tp1523_reference.yaml"
OUT_FILE = M2 / "analysis" / "a1_validation.yaml"

CP, GAMMA = 1004.0, 1.40  # TP-1523 symbol list p. 11 [K]
TOL_DF, TOL_BETA, TOL_PR = 0.02, 1.5, 0.01  # A-1 criteria [T], aero_method.md
STATION_TO_SECTION = {"tip": "tip", "mid": "mean", "hub": "hub"}


def table(ref: dict, name: str) -> list[dict]:
    t = ref[name]
    return [dict(zip(t["columns"], row)) for row in t["rows"]]


def rig_gas() -> ConstantCp:
    return ConstantCp(CP, GAMMA, R_value=CP * (GAMMA - 1) / GAMMA)


def section_shapes(case: dict) -> dict:
    """Rig shape ratios (hub, mean, tip) from Table 2(b) rows: inlet/exit meridional velocity and work, mid = 1."""
    st = ("hub", "mid", "tip")
    return {
        "vx_in": tuple(case[s]["vm_in"] / case["mid"]["vm_in"] for s in st),
        "vx_out": tuple(case[s]["vm_out"] / case["mid"]["vm_out"] for s in st),
        "work": tuple((case[s]["tt_ratio"] - 1) / (case["mid"]["tt_ratio"] - 1) for s in st),
    }


def run(ref: dict | None = None) -> dict:
    ref = ref or read_yaml(REF_FILE)
    gas = rig_gas()
    case = {row["station"]: row for row in table(ref, "a1_case")}
    blades = {row["station"]: row for row in table(ref, "blade_tables") if row["row"] == "rotor 23B"}
    df_rows = {row["station"]: row for row in table(ref, "df_check")}
    cc = ref["coefficient_check"]

    rpm = ref["rig"]["design_rpm_23B"]["value"]
    omega = rpm * 2 * math.pi / 60
    Tt1 = cc["inlet_total_temperature"]["value"]
    Pt1 = ref["a1_case"]["inlet_total_pressure"]["value"] * 1e3
    PR = cc["rotor_pressure_ratio"]["value"]
    TR = ref["a1_case"]["rotor_total_temperature_ratio"]["value"]
    eta = (PR ** ((GAMMA - 1) / GAMMA) - 1) / (TR - 1)
    shapes = section_shapes(case)

    inlet = sa.with_profile(
        sa.Plane(Tt1, Pt1, case["hub"]["r_in_cm"] / 100, case["tip"]["r_in_cm"] / 100, case["mid"]["vm_in"], 0.0),
        shapes["vx_in"], (0.0, 0.0, 0.0))
    W = sa.Plane(Tt1, Pt1, inlet.r_hub, inlet.r_tip, inlet.Vx, 0.0).mean_static(gas).rho * inlet.Vx * inlet.area
    w_mid = gas.h(Tt1 * case["mid"]["tt_ratio"]) - gas.h(Tt1)  # cp Tt1 (TR_mid - 1)
    w = gas.h(Tt1 * TR) - gas.h(Tt1)
    exit0 = sa.Plane(Tt1 * TR, Pt1 * PR, case["hub"]["r_out_cm"] / 100, case["tip"]["r_out_cm"] / 100,
                     case["mid"]["vm_out"], w_mid / omega)
    exit_ = sa.with_profile(exit0, shapes["vx_out"], sa.rotor_exit_swirl(inlet, exit0, omega, w_mid, shapes["work"]))

    rows, results = [], {}
    for station, section in STATION_TO_SECTION.items():
        b = blades[station]
        s = sa.rotor_section(gas, inlet, exit_, omega, section, b["chord_cm"] / 100, b["blades"])
        c = case[station]
        d = df_rows[station]
        df_table_velocities = diffusion_factor(d["W1"], d["W2"], d["r1_cm"], d["r2_cm"], d["U1"] - d["Vt1"],
                                               d["U2"] - d["Vt2"], d["solidity"])
        res = {
            "DF": {"achieved": s["DF"], "target": c["df_table"], "tol": TOL_DF},
            "beta2_rel": {"achieved": s["beta2"], "target": c["beta_rel_out"], "tol": TOL_BETA},
        }
        for item in res.values():
            item["delta"] = item["achieved"] - item["target"]
            item["pass"] = abs(item["delta"]) <= item["tol"]
        results[station] = res
        rows.append({"station": station, "section": s, "table": c, "df_from_table_velocities": df_table_velocities})

    mean = next(r["section"] for r in rows if r["station"] == "mid")
    w_euler = mean["U2"] * mean["Vt2"] - mean["U1"] * mean["Vt1"]
    T_is = gas.T_from_h(gas.h(Tt1) + eta * w_euler)
    PR_mean = math.exp((gas.phi(T_is) - gas.phi(Tt1)) / gas.R_s())
    pr_item = {"achieved": PR_mean, "target": PR, "tol": TOL_PR, "delta": PR_mean / PR - 1}
    pr_item["pass"] = abs(pr_item["delta"]) <= TOL_PR
    passed = pr_item["pass"] and all(i["pass"] for r in results.values() for i in r.values())
    return {"eta": eta, "omega": omega, "W": W, "inlet": inlet, "exit": exit_, "w": w, "w_mid": w_mid,
            "shapes": shapes, "rows": rows, "results": results, "pr": pr_item, "passed": passed}


def _r(x, n=4):
    return round(float(x), n)


def to_yaml(res: dict) -> dict:
    criteria = []
    for station, items in res["results"].items():
        for name, it in items.items():
            criteria.append({"item": f"{name} {station}", "achieved": _r(it["achieved"]), "target": it["target"],
                             "tolerance": it["tol"], "delta": _r(it["delta"]),
                             "result": "pass" if it["pass"] else "fail"})
    p = res["pr"]
    criteria.append({"item": "rotor PR", "achieved": _r(p["achieved"]), "target": p["target"], "tolerance": p["tol"],
                     "delta": _r(p["delta"], 6), "result": "pass" if p["pass"] else "fail",
                     "note": "mean-section Euler work (from the tabulated mid-span TR) converted with the PR/TR efficiency; checks the code chain, not the physics"})
    sections = []
    for r in res["rows"]:
        s, t = r["section"], r["table"]
        sections.append({
            "station": r["station"],
            "Vt2": {"value": _r(s["Vt2"], 2), "table": t["vt_out"], "unit": "m/s"},
            "Vx2": {"value": _r(s["Vx2"], 2), "table": t["vm_out"], "unit": "m/s"},
            "W1": {"value": _r(s["W1"], 2), "unit": "m/s"},
            "W2": {"value": _r(s["W2"], 2), "unit": "m/s"},
            "beta1_rel": {"value": _r(s["beta1"], 2), "table": t["beta_rel_in"], "unit": "deg"},
            "solidity": {"value": _r(s["solidity"]), "unit": "-"},
            "df_from_table_velocities": {"value": _r(r["df_from_table_velocities"]), "table": t["df_table"],
                                         "unit": "-", "note": "formula check: same DF code on the Table 2(b) triangle"},
        })
    return {
        "description": "A-1 validation, TP-1523 rotor 23B design point; generated by "
                       "engine/M2_booster/analysis/a1_validation.py, do not edit by hand. Values [H] from code, "
                       "targets [K] TP-1523 Table 2(b) p. 21; criteria [T] aero_method.md. Step 3 method: rig "
                       "tabulated section inputs (aero_method.md Spanwise distribution).",
        "tag": "H",
        "result": "pass" if res["passed"] else "fail",
        "inputs": {
            "eta_from_pr_tr": {"value": _r(res["eta"]), "unit": "-", "tag": "H",
                               "note": "(PR^((gamma-1)/gamma) - 1) / (TR - 1), PR 1.257, TR 1.072 Table 2(a) [K]"},
            "mass_flow_from_inlet": {"value": _r(res["W"], 3), "unit": "kg/s", "tag": "H",
                                     "note": "rho V_x A on the rig annulus without blockage; Table 2(a) gives 9.457 kg/s [K]"},
            "method": {"value": "tabulated_section_inputs", "unit": "-", "tag": "K",
                       "note": "aero_method.md Spanwise distribution: Table 2(b) p. 21 radii, rpm, vm_in, vm_out, "
                               "TR per section, zero inlet swirl; Table 8 chords and blade count; no continuity, "
                               "no blockage"},
            "shape_ratios": {"tag": "H", "note": "hub, mean, tip; mid = 1; from Table 2(b) [K]",
                             **{k: [_r(x) for x in v] for k, v in res["shapes"].items()}},
            "mid_section_work": {"value": _r(res["w_mid"] / 1e3, 3), "unit": "kJ/kg", "tag": "H",
                                 "note": "cp Tt1 (TR_mid - 1), cp 1004 (p. 11), Tt1 288.2, TR_mid 1.071 [K]"},
        },
        "criteria": criteria,
        "sections": sections,
    }


def main() -> None:
    data = to_yaml(run())
    write_yaml(OUT_FILE, data)
    for c in data["criteria"]:
        print(f"{c['item']:<16} achieved {c['achieved']:>8} target {c['target']:>7} delta {c['delta']:>9} {c['result']}")
    print("A-1:", data["result"])


if __name__ == "__main__":
    main()
