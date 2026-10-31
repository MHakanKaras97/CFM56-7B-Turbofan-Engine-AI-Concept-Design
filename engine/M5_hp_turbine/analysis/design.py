"""M5 HP turbine system design (rules/design.md R-D5.1-6): mean line, annulus, NGV and rotor rows, hardware layout and
the station 44 interface.

Inputs: read_icd("M5 design"), M4 and M3 interfaces (geometry/flowpath.yaml, read-only); design choices in
analysis/hpt_params.yaml. Writes analysis/hpt_results.yaml and the derived geometry/flowpath.yaml (for M6, M8).

Run: python -m engine.M5_hp_turbine.analysis.design
"""

import math
from pathlib import Path

from core.budgets import read_icd
from core.util import read_yaml, write_yaml
from tools import concept as C

HERE = Path(__file__).resolve().parent
PARAMS_FILE = HERE / "hpt_params.yaml"
OUT_FILE = HERE / "hpt_results.yaml"


def p(params: dict, key: str):
    return C.v(params[key])


def _state(st: dict, key: str) -> tuple[float, float, float, float]:
    return tuple(float(st[key][k]["value"]) for k in ("W", "Tt", "Pt", "FAR"))


def run(params: dict | None = None, icd: dict | None = None) -> dict:
    params = params or read_yaml(PARAMS_FILE)
    icd = icd or read_icd("M5 design")
    st = icd["stations"]
    W41, T41, P41, f41 = _state(st, "41")
    W44, T44, P44, f44 = _state(st, "44")
    power = float(icd["modules"]["M5"]["budget"]["power"]["value"]) * 1e6
    N = float(icd["shafts"]["HP"]["speed_refs"]["girao_nominal"]["value"])
    omega = N * 2 * math.pi / 60
    m4 = C.read_interface("M4")["interfaces"]
    m3 = C.read_interface("M3")["interfaces"]
    s4 = m4["M5_station_4"]
    x4, rh4, rt4 = float(s4["x_m"]), float(s4["r_hub_m"]), float(s4["r_tip_m"])

    # R-D5.1 mean line
    r_m = 0.5 * (rh4 + rt4)
    U = omega * r_m
    psi = power / W41 / U ** 2
    tri = C.stage_triangles(-psi, p(params, "flow_coefficient"), p(params, "reaction"))
    Vx = tri["phi"] * U
    vt1, vt2 = tri["vt1"] * U, tri["vt2"] * U
    # R-D5.2 annulus
    A41 = C.area_swirl(W41, T41, P41, Vx, vt1, f41)
    A44 = C.area_swirl(W44, T44, P44, Vx, vt2, f44)
    rh41, rt41 = C.radii_mean(A41, r_m)
    rh44, rt44 = C.radii_mean(A44, r_m)

    # R-D5.3 / R-D5.4 rows
    m = p(params, "carter_m")
    n_r = int(p(params, "rotor_blades"))
    c_r = p(params, "rotor_solidity") * 2 * math.pi * r_m / n_r
    h_ngv = 0.5 * ((rt4 - rh4) + (rt41 - rh41))
    c_n = h_ngv / p(params, "ngv_aspect_ratio")
    n_n = round(p(params, "ngv_solidity") * 2 * math.pi * r_m / c_n)
    while n_n == n_r or n_r % n_n == 0 or n_n % 2:
        n_n += 1
    ngv_tc = {k: p(params, "ngv_tc") for k in ("hub", "mean", "tip")}
    rtc = p(params, "rotor_tc")
    rot_tc = {"hub": rtc[0], "mean": 0.5 * (rtc[0] + rtc[1]), "tip": rtc[1]}
    ngv = {"kind": "ngv", "count": n_n, "count_tag": "T", "chord": c_n,
           "hub_le": rh4, "tip_le": rt4, "hub_te": rh41, "tip_te": rt41,
           "sections": C.free_vortex_sections({"hub": max(rh4, rh41), "mean": r_m, "tip": min(rt4, rt41)}, r_m, U, Vx,
                                              0.0, vt1, False, c_n, ngv_tc, c_n * n_n / (2 * math.pi * r_m), m)}
    rotor = {"kind": "rotor", "count": n_r, "count_tag": "KS", "chord": c_r,
             "hub_le": rh41, "tip_le": rt41, "hub_te": rh44, "tip_te": rt44,
             "sections": C.free_vortex_sections({"hub": max(rh41, rh44), "mean": r_m, "tip": min(rt41, rt44)}, r_m, U,
                                                Vx, vt1, vt2, True, c_r, rot_tc, c_r * n_r / (2 * math.pi * r_m), m)}
    for row in (ngv, rotor):
        row["width"] = C.axial_width(row["sections"])
    ngv["x_le"], ngv["x_te"] = x4, x4 + ngv["width"]
    rotor["x_le"] = ngv["x_te"] + p(params, "axial_gap_over_chord") * c_r
    rotor["x_te"] = rotor["x_le"] + rotor["width"]

    # R-D5.5 hardware layout
    d, sh = p(params, "disk"), p(params, "shafts")
    w_rim = d["rim_width_over_rotor_width"] * rotor["width"]
    r_rim = rotor["sections"][0]["r"]
    disk = {"x_mid": 0.5 * (rotor["x_le"] + rotor["x_te"]), "w_rim": w_rim, "r_rim_out": r_rim,
            "r_rim_in": r_rim - d["rim_depth"], "t_web": d["web_thickness"], "w_bore": d["bore_width"],
            "r_bore_in": d["bore_inner_radius"], "r_bore_out": d["bore_inner_radius"] + d["bore_height"]}
    cdp = m3["M5_cdp_flange"]
    front_shaft = {"x0": float(cdp["x_m"]), "r0": float(cdp["r_in_m"]), "x1": disk["x_mid"] - disk["t_web"] / 2,
                   "r1": disk["r_bore_out"] + 0.01, "t": sh["thickness"]}
    seal = {"x1": disk["x_mid"] - w_rim / 2, "x0": disk["x_mid"] - w_rim / 2 - sh["seal_plate_thickness"],
            "r_out": disk["r_rim_in"], "r_in": disk["r_rim_in"] - sh["seal_plate_height"]}
    x_j = disk["x_mid"] + sh["rear_journal_x_aft_of_disk"]
    rear_shaft = {"x0": disk["x_mid"] + disk["w_bore"] / 2, "r0": disk["r_bore_out"] - sh["thickness"] - 0.005, "x1": x_j,
                  "r1": sh["rear_journal_radius"], "x2": x_j + sh["journal_length"], "t": sh["thickness"]}
    if not front_shaft["r1"] + front_shaft["t"] < seal["r_in"]:
        raise ValueError("M5: front shaft meets the front air seal")
    return {"params": params, "icd_revision": icd["source"]["revision"], "N": N, "omega": omega, "r_mean": r_m,
            "U": U, "psi": psi, "Vx": Vx, "vt1": vt1, "vt2": vt2, "ngv": ngv, "rotor": rotor,
            "station_4": {"x": x4, "r_hub": rh4, "r_tip": rt4}, "station_41": {"r_hub": rh41, "r_tip": rt41, "area": A41},
            "station_44": {"x": rotor["x_te"], "r_hub": rh44, "r_tip": rt44, "area": A44},
            "m4": m4, "disk": disk, "front_shaft": front_shaft, "seal_plate": seal, "rear_shaft": rear_shaft,
            "exit_swirl_deg": math.degrees(math.atan2(vt2, Vx))}


def _sec(d: dict) -> dict:
    return {k: C.r6(v) if isinstance(v, float) else v for k, v in d.items() if not isinstance(v, (dict, list))}


def to_yaml(res: dict) -> dict:
    rows = []
    for r in (res["ngv"], res["rotor"]):
        out = _sec(r)
        out["sections"] = [_sec(s) for s in r["sections"]]
        rows.append(out)
    return {"description": "M5 HPT concept design results; generated by engine/M5_hp_turbine/analysis/design.py",
            "icd_revision": res["icd_revision"],
            "hp_speed": {"value": res["N"], "unit": "rpm", "tag": "KS", "note": "ICD shafts.HP girao_nominal"},
            "r_mean": {"value": C.r6(res["r_mean"]), "unit": "m", "tag": "H"},
            "U_mean": {"value": C.r6(res["U"]), "unit": "m/s", "tag": "H"},
            "psi": {"value": C.r6(res["psi"]), "unit": "-", "tag": "H"},
            "exit_swirl": {"value": C.r6(res["exit_swirl_deg"]), "unit": "deg", "tag": "H"},
            "station_41": _sec(res["station_41"]), "station_44": _sec(res["station_44"]), "rows": rows,
            "disk": _sec(res["disk"])}


def interface(res: dict) -> dict:
    s44, rs = res["station_44"], res["rear_shaft"]
    m4c = res["m4"]["M5_outer_case_flange"]
    t = p(res["params"], "case_thickness")
    return {
        "description": "M5 HPT interfaces; generated by engine/M5_hp_turbine/analysis/design.py, do not edit by hand",
        "icd_revision": res["icd_revision"],
        "interfaces": {
            "M6_station_44": {"x_m": C.r6(s44["x"]), "r_hub_m": C.r6(s44["r_hub"]), "r_tip_m": C.r6(s44["r_tip"]),
                              "area_m2": C.r6(s44["area"]), "swirl_deg": C.r6(res["exit_swirl_deg"]), "tag": "H",
                              "note": "HPT rotor exit plane (R-D5.2)"},
            "M6_case_flange": {"x_m": C.r6(case_aft_x(res)), "r_in_m": C.r6(float(m4c["r_in_m"])),
                               "r_out_m": C.r6(float(m4c["r_in_m"]) + t), "tag": "H",
                               "note": "aft end of the HPT case; LPT transition duct / case continues"},
            "M6_duct_start": {"x_m": C.r6(case_aft_x(res)), "r_hub_m": C.r6(res["disk"]["r_rim_out"]),
                              "r_tip_m": C.r6(res["rotor"]["sections"][-1]["r"]), "tag": "H",
                              "note": "aft end of the HPT shroud and rim: LPT transition duct walls start here"},
            "M8_bearing_4_journal": {"x_fwd_m": C.r6(rs["x1"]), "x_aft_m": C.r6(rs["x2"]), "r_inner_m": C.r6(rs["r1"]),
                                     "tag": "H", "note": "HPT rear shaft journal; bearing #4 (intershaft, M8) inside"},
        },
    }


def case_aft_x(res: dict) -> float:
    return res["rotor"]["x_te"] + 0.25 * res["rotor"]["chord"]


def main() -> None:
    res = run()
    write_yaml(OUT_FILE, to_yaml(res))
    C.write_interface("M5", interface(res))
    print("M5 station 44", {k: round(v, 4) for k, v in res["station_44"].items()})


if __name__ == "__main__":
    main()
