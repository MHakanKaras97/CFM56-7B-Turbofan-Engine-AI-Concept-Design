"""M8 shaft and bearing system design (rules/design.md R-D8.1-6): fan and LP shafts, bearings #1-#5, supports, LP
shaft torsion check.

Inputs: read_icd("M8 design"), M1 fan disk and fan frame flange (read-only imports), M3/M5/M6/M7 interfaces; design
choices in analysis/shaft_params.yaml. Writes analysis/shaft_results.yaml and geometry/flowpath.yaml (for M9).

Run: python -m engine.M8_shaft_bearing.analysis.design
"""

import math
from pathlib import Path

from core.budgets import read_icd
from core.util import read_yaml, write_yaml
from tools import concept as C

HERE = Path(__file__).resolve().parent
PARAMS_FILE = HERE / "shaft_params.yaml"
OUT_FILE = HERE / "shaft_results.yaml"


def p(params: dict, key: str):
    return C.v(params[key])


def m1_inputs() -> dict:
    """M1 fan disk bore aft face and the fan frame M8 flange (read-only)."""
    from engine.M1_inlet_fan.geometry import fan_frame, rotor_hardware
    rot = rotor_hardware.build()
    m8 = fan_frame.interfaces(fan_frame.build())["M8_bearing_support"]
    return {"x_disk_aft": float(rot["layout"]["x_b"]), "r_bore_in": float(rot["disk_profile"]["r_bore_in"]),
            "r_bore_out": float(rot["disk_profile"]["r_bore_out"]), "r_flange": float(m8["r_inner_m"]),
            "x_flange": tuple(float(x) for x in m8["x_face_m"])}


def run(params: dict | None = None, icd: dict | None = None, m1: dict | None = None) -> dict:
    params = params or read_yaml(PARAMS_FILE)
    icd = icd or read_icd("M8 design")
    m1 = m1 or m1_inputs()
    j3 = C.read_interface("M3")["interfaces"]["M8_bearing_3_journal"]
    j4 = C.read_interface("M5")["interfaces"]["M8_bearing_4_journal"]
    m6 = C.read_interface("M6")["interfaces"]
    cpl, j5 = m6["M8_lp_coupling"], m6["M8_bearing_5_journal"]
    s5 = C.read_interface("M7")["interfaces"]["M8_bearing_5_support"]
    t_h = p(params, "housing_thickness")

    fs = p(params, "fan_shaft")
    fan = {"x0": m1["x_disk_aft"], "x1": fs["aft_end_x"], "r_out": fs["r_out"], "r_in": fs["r_out"] - fs["thickness"],
           "flange": (fs["flange_r_in"], fs["flange_r_out"], fs["flange_length"])}
    if not (m1["r_bore_in"] <= fs["flange_r_in"] and fs["flange_r_out"] <= m1["r_bore_out"]):
        raise ValueError("M8: fan shaft flange outside the fan disk bore face")
    lp = {"x0": p(params, "lp_shaft")["fwd_end_x"], "x1": float(cpl["x_m"]), "r_in": float(cpl["r_in_m"]),
          "r_out": float(cpl["r_out_m"])}
    if not lp["r_out"] < fan["r_in"]:
        raise ValueError("M8: LP shaft does not fit inside the fan shaft spline")

    def brg(x0, x1, r_in, section):
        return {"x0": x0, "x1": x1, "r_in": r_in, "r_out": r_in + section}
    b1p, b2p = p(params, "bearing_1"), p(params, "bearing_2")
    bearings = {
        1: brg(b1p["x_mid"] - b1p["width"] / 2, b1p["x_mid"] + b1p["width"] / 2, fan["r_out"], b1p["section"]),
        2: brg(b2p["x_mid"] - b2p["width"] / 2, b2p["x_mid"] + b2p["width"] / 2, fan["r_out"], b2p["section"]),
        3: brg(float(j3["x_fwd_m"]), float(j3["x_aft_m"]), float(j3["r_outer_m"]), p(params, "bearing_3")["section"]),
        4: {"x0": float(j4["x_fwd_m"]), "x1": float(j4["x_aft_m"]), "r_in": lp["r_out"], "r_out": float(j4["r_inner_m"])},
        5: brg(float(j5["x_fwd_m"]), float(j5["x_aft_m"]), float(j5["r_outer_m"]), p(params, "bearing_5")["section"]),
    }
    if not (lp["x0"] < bearings[4]["x0"] and bearings[4]["x1"] < lp["x1"]):
        raise ValueError("M8: bearing #4 not on the LP shaft")
    xf0, xf1 = m1["x_flange"]
    rf = m1["r_flange"]
    b1, b2, b3, b5 = bearings[1], bearings[2], bearings[3], bearings[5]
    # forward support: outer surface curve from the #1 housing to the flange inner face, wall inward
    fwd_curve = [(b1["x0"], b1["r_out"] + t_h), (b1["x1"], b1["r_out"] + t_h), (b2["x0"], b2["r_out"] + t_h),
                 (b2["x1"], b2["r_out"] + t_h), (xf0, rf), (xf1, rf)]
    sup3 = [(xf1, rf), (xf1, rf + t_h), (b3["x0"], b3["r_out"] + t_h), (b3["x1"], b3["r_out"] + t_h),
            (b3["x1"], b3["r_out"]), (b3["x0"], b3["r_out"])]
    w5 = p(params, "support_5_width")
    xs1 = float(s5["x_aft_m"])
    rs = float(s5["r_m"])
    sup5 = {"cone": [(xs1 - w5, rs), (xs1, rs), (b5["x1"], b5["r_out"] + t_h), (b5["x1"] - w5, b5["r_out"] + t_h)],
            "housing": (b5["x0"], b5["x1"], b5["r_out"], b5["r_out"] + t_h)}

    # R-D8.3 torsion
    N_lp = float(icd["shafts"]["LP"]["speed_refs"]["girao_nominal"]["value"])
    P_lp = float(icd["shafts"]["LP"]["power_lpt"]["value"]) * 1e6
    omega = N_lp * 2 * math.pi / 60
    T = P_lp / omega
    sy = p(params, "yield_strength")["maraging_c250"]
    allow = 0.577 * sy / 1.5
    checks = {}
    for name, sh in (("lp_shaft", lp), ("fan_shaft", fan)):
        J = math.pi / 2 * (sh["r_out"] ** 4 - sh["r_in"] ** 4)
        tau = T * sh["r_out"] / J / 1e6
        checks[name] = {"torque_Nm": T, "tau_MPa": tau, "allowable_MPa": allow, "margin": allow / tau - 1}
    return {"params": params, "icd_revision": icd["source"]["revision"], "m1": m1, "fan_shaft": fan, "lp_shaft": lp,
            "bearings": bearings, "fwd_support_curve": fwd_curve, "support_3": sup3, "support_5": sup5,
            "torsion": checks, "margin_ok": all(c["margin"] >= p(params, "margin_target") for c in checks.values())}


def _sec(d: dict) -> dict:
    return {k: (C.r6(v) if isinstance(v, float) else v) for k, v in d.items() if not isinstance(v, (dict, list, tuple))}


def to_yaml(res: dict) -> dict:
    return {"description": "M8 shaft and bearing concept design results; generated by "
                           "engine/M8_shaft_bearing/analysis/design.py",
            "icd_revision": res["icd_revision"], "fan_shaft": _sec(res["fan_shaft"]), "lp_shaft": _sec(res["lp_shaft"]),
            "bearings": {f"no_{k}": _sec(v) for k, v in res["bearings"].items()},
            "torsion": {k: _sec(v) for k, v in res["torsion"].items()}, "margin_ok": res["margin_ok"]}


def interface(res: dict) -> dict:
    b3 = res["bearings"][3]
    return {"description": "M8 interfaces; generated by engine/M8_shaft_bearing/analysis/design.py, do not edit by hand",
            "icd_revision": res["icd_revision"],
            "interfaces": {
                "M9_forward_sump": {"x_m": C.r6(0.5 * (b3["x0"] + b3["x1"])), "r_m": C.r6(b3["r_out"]), "tag": "H",
                                    "note": "bearing #3 housing: inlet gearbox drive and forward sump oil feed (M9)"},
                "M9_aft_sump": {"x_m": C.r6(0.5 * (res["bearings"][5]["x0"] + res["bearings"][5]["x1"])),
                                "r_m": C.r6(res["bearings"][5]["r_out"]), "tag": "H",
                                "note": "bearing #5 housing: aft sump oil feed (M9)"},
            }}


def main() -> None:
    res = run()
    write_yaml(OUT_FILE, to_yaml(res))
    C.write_interface("M8", interface(res))
    print("M8 torsion", {k: round(v["margin"], 3) for k, v in res["torsion"].items()}, "ok", res["margin_ok"])


if __name__ == "__main__":
    main()
