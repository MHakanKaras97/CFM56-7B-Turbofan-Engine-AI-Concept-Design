"""M6 LP turbine system design (rules/design.md R-D6.1-7): mean radius, stage thermodynamics, annulus, rows, hardware
layout and the station 5 interface.

Inputs: read_icd("M6 design") and the M5 interfaces (geometry/flowpath.yaml, read-only); design choices in
analysis/lpt_params.yaml. Writes analysis/lpt_results.yaml and the derived geometry/flowpath.yaml (for M7, M8).

Run: python -m engine.M6_lp_turbine.analysis.design
"""

import math
from pathlib import Path

from core.budgets import read_icd
from core.util import read_yaml, write_yaml
from tools import concept as C

HERE = Path(__file__).resolve().parent
PARAMS_FILE = HERE / "lpt_params.yaml"
OUT_FILE = HERE / "lpt_results.yaml"
N_STAGES = 4


def p(params: dict, key: str):
    return C.v(params[key])


def run(params: dict | None = None, icd: dict | None = None) -> dict:
    params = params or read_yaml(PARAMS_FILE)
    icd = icd or read_icd("M6 design")
    st = icd["stations"]
    W45, T45, P45, f45 = (float(st["45"][k]["value"]) for k in ("W", "Tt", "Pt", "FAR"))
    T5, P5 = float(st["5"]["Tt"]["value"]), float(st["5"]["Pt"]["value"])
    power = float(icd["modules"]["M6"]["budget"]["power"]["value"]) * 1e6
    N = float(icd["shafts"]["LP"]["speed_refs"]["girao_nominal"]["value"])
    omega = N * 2 * math.pi / 60
    m5 = C.read_interface("M5")["interfaces"]
    ds = m5["M6_duct_start"]
    x_d, rh_d, rt_d = float(ds["x_m"]), float(ds["r_hub_m"]), float(ds["r_tip_m"])
    counts = [int(n) for n in p(params, "rotor_blades")]

    # R-D6.1 mean radius
    dh = power / W45 / N_STAGES
    U = math.sqrt(dh / p(params, "stage_loading"))
    r_m = U / omega
    psi = p(params, "stage_loading")
    tri = C.stage_triangles(-psi, p(params, "flow_coefficient"), p(params, "reaction"))
    Vx = tri["phi"] * U
    vt1, vt2 = tri["vt1"] * U, tri["vt2"] * U  # NGV exit / rotor exit absolute swirl (direction of rotation +)

    # R-D6.2 / R-D6.3 planes: 0 = NGV 1 LE, then NGV TE / rotor TE of each stage
    dT = (T45 - T5) / N_STAGES
    n_exp = math.log(P5 / P45) / math.log(T5 / T45)
    planes = []
    for j in range(2 * N_STAGES + 1):
        stage = j // 2  # completed rotors
        Tt = T45 - stage * dT
        Pt = P45 * (Tt / T45) ** n_exp
        vt = vt2 if j % 2 == 0 else vt1
        A = C.area_swirl(W45, Tt, Pt, Vx, vt, f45)
        rh, rt = C.radii_mean(A, r_m)
        planes.append({"j": j, "Tt": Tt, "Pt": Pt, "area": A, "r_hub": rh, "r_tip": rt, "vt": vt})

    m = p(params, "carter_m")
    rtc = p(params, "rotor_tc")
    rows = []
    for i in range(N_STAGES):
        for kind in ("ngv", "rotor"):
            j = 2 * i if kind == "ngv" else 2 * i + 1
            a, b = planes[j], planes[j + 1]
            h = 0.5 * ((a["r_tip"] - a["r_hub"]) + (b["r_tip"] - b["r_hub"]))
            radii = {"hub": max(a["r_hub"], b["r_hub"]), "mean": r_m, "tip": min(a["r_tip"], b["r_tip"])}
            if kind == "rotor":
                n = counts[i]
                chord = p(params, "rotor_solidity") * 2 * math.pi * r_m / n
                tc = {"hub": rtc[0], "mean": 0.5 * (rtc[0] + rtc[1]), "tip": rtc[1]}
                vin, vout = vt1, vt2
            else:
                chord = h / p(params, "ngv_aspect_ratio")
                n = round(p(params, "ngv_solidity") * 2 * math.pi * r_m / chord)
                while n in {counts[i], counts[i - 1] if i else -1}:
                    n += 1
                tc = {k: p(params, "ngv_tc") for k in ("hub", "mean", "tip")}
                vin, vout = vt2, vt1
            sig = chord * n / (2 * math.pi * r_m)
            secs = C.free_vortex_sections(radii, r_m, U, Vx, vin, vout, kind == "rotor", chord, tc, sig, m)
            rows.append({"stage": i + 1, "kind": kind, "count": n, "count_tag": "KS" if kind == "rotor" else "T",
                         "chord": chord, "solidity_mean": sig, "height": h, "sections": secs,
                         "width": C.axial_width(secs), "hub_le": a["r_hub"], "hub_te": b["r_hub"],
                         "tip_le": a["r_tip"], "tip_te": b["r_tip"]})

    x = x_d + p(params, "duct_length")
    g = p(params, "axial_gap_over_chord")
    for r in rows:
        r["x_le"], r["x_te"] = x, x + r["width"]
        x = r["x_te"] + g * r["chord"]
    for j, pl in enumerate(planes):
        pl["x"] = rows[0]["x_le"] if j == 0 else rows[j - 1]["x_te"]

    # R-D6.6 hardware layout
    d, sh = p(params, "disk"), p(params, "shaft")
    rotors = [r for r in rows if r["kind"] == "rotor"]
    ngvs = [r for r in rows if r["kind"] == "ngv"]
    t_sh, gap = p(params, "shroud_thickness"), p(params, "seal_gap")
    disks = []
    for r in rotors:
        w_rim = d["rim_width_over_rotor_width"] * r["width"]
        r_rim = r["sections"][0]["r"]
        disks.append({"stage": r["stage"], "x_mid": 0.5 * (r["x_le"] + r["x_te"]), "w_rim": w_rim, "r_rim_out": r_rim,
                      "r_rim_in": r_rim - d["rim_depth"], "t_web": d["web_thickness"], "w_bore": d["bore_width"],
                      "r_bore_in": d["bore_inner_radius"], "r_bore_out": d["bore_inner_radius"] + d["bore_height"]})
    drums = []
    for a, b, n in zip(disks, disks[1:], ngvs[1:]):
        r_out = n["sections"][0]["r"] - t_sh - gap
        drums.append({"x0": a["x_mid"] + a["w_rim"] / 2, "x1": b["x_mid"] - b["w_rim"] / 2, "r_out": r_out,
                      "r_in": r_out - d["drum_thickness"]})
    s5 = planes[-1]
    d4 = disks[-1]
    x_ce = s5["x"] + sh["cone_end_aft_of_exit"]
    cone = {"x0": d4["x_mid"] + d4["t_web"] / 2, "r0": 0.5 * (d4["r_bore_out"] + d4["r_rim_in"]), "x1": x_ce,
            "r1": sh["r_out"], "t": sh["cone_thickness"]}
    shaft = {"x0": rows[0]["x_le"], "x1": x_ce + sh["journal_length"], "r_out": sh["r_out"],
             "r_in": sh["r_out"] - sh["thickness"], "journal": (x_ce, x_ce + sh["journal_length"])}
    return {"params": params, "icd_revision": icd["source"]["revision"], "N": N, "omega": omega, "r_mean": r_m, "U": U,
            "psi": psi, "Vx": Vx, "vt1": vt1, "vt2": vt2, "planes": planes, "rows": rows,
            "duct_start": {"x": x_d, "r_hub": rh_d, "r_tip": rt_d}, "disks": disks, "drums": drums, "cone": cone,
            "shaft": shaft, "station_5": s5, "exit_swirl_deg": math.degrees(math.atan2(vt2, Vx))}


def _sec(d: dict) -> dict:
    return {k: C.r6(v) if isinstance(v, float) else v for k, v in d.items() if not isinstance(v, (dict, list, tuple))}


def to_yaml(res: dict) -> dict:
    rows = []
    for r in res["rows"]:
        out = _sec(r)
        out["sections"] = [_sec(s) for s in r["sections"]]
        rows.append(out)
    return {"description": "M6 LPT concept design results; generated by engine/M6_lp_turbine/analysis/design.py",
            "icd_revision": res["icd_revision"],
            "lp_speed": {"value": res["N"], "unit": "rpm", "tag": "KS", "note": "ICD shafts.LP girao_nominal"},
            "r_mean": {"value": C.r6(res["r_mean"]), "unit": "m", "tag": "H"},
            "U_mean": {"value": C.r6(res["U"]), "unit": "m/s", "tag": "H"},
            "exit_swirl": {"value": C.r6(res["exit_swirl_deg"]), "unit": "deg", "tag": "H"},
            "planes": [_sec(pl) for pl in res["planes"]], "rows": rows, "disks": [_sec(d) for d in res["disks"]]}


def interface(res: dict) -> dict:
    s5, sh = res["station_5"], res["shaft"]
    t = p(res["params"], "case_thickness")
    return {
        "description": "M6 LPT interfaces; generated by engine/M6_lp_turbine/analysis/design.py, do not edit by hand",
        "icd_revision": res["icd_revision"],
        "interfaces": {
            "M7_station_5": {"x_m": C.r6(s5["x"]), "r_hub_m": C.r6(s5["r_hub"]), "r_tip_m": C.r6(s5["r_tip"]),
                             "area_m2": C.r6(s5["area"]), "swirl_deg": C.r6(res["exit_swirl_deg"]),
                             "x_rotor_aft_m": C.r6(max(s5["x"], res["disks"][-1]["x_mid"] + res["disks"][-1]["w_rim"] / 2)),
                             "tag": "H",
                             "note": "LPT stage 4 rotor exit plane"},
            "M7_case_flange": {"x_m": C.r6(s5["x"]), "r_in_m": C.r6(s5["r_tip"]), "r_out_m": C.r6(s5["r_tip"] + t),
                               "tag": "H", "note": "aft end of the LPT case; turbine rear frame (M7) continues"},
            "M9_bleed_return": {"x_m": C.r6(res["planes"][0]["x"]),
                                "r_case_out_m": C.r6(res["planes"][0]["r_tip"] + t), "tag": "H",
                                "note": "LPT case at the stage 1 NGV leading edge: interstage leak return (45)"},
            "M8_lp_coupling": {"x_m": C.r6(sh["x0"]), "r_in_m": C.r6(sh["r_in"]), "r_out_m": C.r6(sh["r_out"]),
                               "tag": "H", "note": "forward end of the LPT shaft; M8 LP shaft splines here"},
            "M8_bearing_5_journal": {"x_fwd_m": C.r6(sh["journal"][0]), "x_aft_m": C.r6(sh["journal"][1]),
                                     "r_outer_m": C.r6(sh["r_out"]), "tag": "H",
                                     "note": "LPT shaft journal; bearing #5 inner race on it, supported by M7 TRF"},
        },
    }


def main() -> None:
    res = run()
    write_yaml(OUT_FILE, to_yaml(res))
    C.write_interface("M6", interface(res))
    print("M6 station 5", {k: round(res["station_5"][k], 4) for k in ("x", "r_hub", "r_tip", "area")})


if __name__ == "__main__":
    main()
