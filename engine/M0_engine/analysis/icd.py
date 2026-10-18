"""M0 interface control document (ICD) and module budgets, generated from a recorded revision.

The revision's params.yaml is re-solved with the similarity condition (ADR-009); the solution is
checked against the recorded results, then station states, interfaces, module budgets, shafts
and secondary-air flows are written to engine/M0_engine/rules/icd.yaml. Ownership rule: the
upstream module owns its exit station (rules/station_ownership.md).

Usage:
    python -m engine.M0_engine.analysis.icd            # from the active M0 revision
"""

import sys
from dataclasses import replace
from pathlib import Path

from core.records import active_revision, module_dir
from core.util import read_yaml, write_yaml
from engine.M0_engine.analysis.cycle import (
    ETA,
    ROOT,
    egt_model_K,
    fan_face_area,
    load_inputs,
    similarity_solve,
    validation_velocity_ratio,
)

ICD_FILE = module_dir("M0", ROOT) / "rules" / "icd.yaml"
SIG_POINT = 12  # digits kept for the operating point, so the integration check reproduces it

# station: (owner, consumers, note); owner = upstream module whose exit it is
STATIONS = {
    "0": (None, ["M1"], "ambient, SLS ISA"),
    "2": ("M1", ["M1"], "fan face; inlet (M1) exit, P2/P1 inlet recovery"),
    "13": ("M1", ["M7"], "outer fan + OGV exit, bypass side"),
    "18": ("M7", [], "bypass nozzle inlet, after the P16/P13 duct (M7 internal)"),
    "21": ("M1", ["M2"], "fan hub (inner fan) exit, core side"),
    "24": ("M2", [], "booster exit before the transition duct (M2 internal)"),
    "25": ("M2", ["M3"], "booster + transition duct exit, HPC inlet"),
    "3": ("M3", ["M4", "M9"], "HPC exit; NGV and HPT rotor cooling extracted here (M9)"),
    "31": ("M9", ["M4"], "combustor inlet: W3 minus M9 extraction"),
    "4": ("M4", ["M5"], "combustor exit"),
    "41": ("M5", [], "HPT rotor inlet after NGV cooling mixes in (M5 internal)"),
    "43": ("M5", [], "HPT rotor exit before rotor cooling mixes in (M5 internal)"),
    "44": ("M5", ["M6"], "HPT exit after rotor cooling mixes in"),
    "45": ("M6", [], "LPT inlet after the inter-turbine duct and leak return (M6 internal)"),
    "5": ("M6", ["M7"], "LPT exit"),
    "8": ("M7", [], "core nozzle, after the P6/P5 duct"),
}

MODULES = {
    "M1": ("Inlet and Fan", ["2"], ["13", "21"]),
    "M2": ("Booster", ["21"], ["25"]),
    "M3": ("HP Compressor", ["25"], ["3"]),
    "M4": ("Combustor", ["31"], ["4"]),
    "M5": ("HP Turbine", ["4"], ["44"]),
    "M6": ("LP Turbine", ["44"], ["5"]),
    "M7": ("Nozzle", ["5", "13"], ["8", "18"]),
    "M8": ("Shaft and Bearing", [], []),
    "M9": ("Secondary Air and Oil", ["3"], ["31"]),
}


def _r(x: float, sig: int = 6) -> float:
    return float(f"{x:.{sig}g}")


def _q(value: float, unit: str, tag: str = "H", kind: str = "info", sig: int = 6) -> dict:
    return {"value": _r(value, sig), "unit": unit, "tag": tag, "kind": kind}


def solve_revision(rev: str):
    """Re-solve a recorded revision. Returns (Params, Targets, result, raw, refs)."""
    rev_dir = module_dir("M0", ROOT) / "records" / rev
    p, t, initial, raw, refs = load_inputs(rev_dir / "params.yaml")
    tol = float(raw["calibration"]["tolerance"]["value"])
    vr = validation_velocity_ratio(p, refs, initial, tol)
    refs["validation_velocity_ratio"] = vr
    t = replace(t, velocity_ratio=vr)
    _, r, _ = similarity_solve(p, t, initial, raw, refs, tol)
    if r is None:
        raise ArithmeticError(f"{rev}: no similarity solution")
    recorded = read_yaml(rev_dir / "results.yaml")["calibration"]
    for key in ("W2", "T4"):
        if abs(r[key] / recorded[key]["value"] - 1.0) > 1e-5:
            raise ArithmeticError(f"{rev}: re-solved {key} {r[key]} differs from recorded {recorded[key]['value']}")
    return r["params"], t, r, raw, refs


def _station(r: dict, s: str) -> dict:
    Tt, Pt, W, f = r["stations"][s]
    return {"Tt": _q(Tt, "K"), "Pt": _q(Pt / 1000.0, "kPa"), "W": _q(W, "kg/s"), "FAR": _q(f, "-")}


def module_budgets(p, r: dict, raw: dict) -> dict:
    """Required values per module; `kind` selects the allowed deviation (tolerances)."""
    st = r["stations"]

    def T(s):
        return _q(st[s][0], "K", kind="temperature")

    def W(s):
        return _q(st[s][2], "kg/s", kind="flow")

    def eff(name):
        return _q(getattr(p, name), "-", kind="efficiency")

    def pr(value, tag="KS"):
        return _q(value, "-", tag, kind="pressure_ratio")

    W_core = r["W_core"]
    gas = p.gas
    P_inner = W_core * (gas.h(st["21"][0]) - gas.h(st["2"][0]))
    P_boost = r["P_boost"] - P_inner
    return {
        "M1": {"FPR": pr(p.FPR), "eta_fan_outer": eff("eta_fan_outer"), "pr_fan_inner": pr(p.pr_fan_inner),
               "eta_fan_inner": eff("eta_fan_inner"), "inlet_recovery": pr(p.inlet_recovery),
               "W2": W("2"), "W13": W("13"), "W21": W("21"), "T13": T("13"), "T21": T("21"),
               "power_outer_fan": _q(r["P_fan"] / 1e6, "MW"), "power_inner_fan": _q(P_inner / 1e6, "MW")},
        "M2": {"pr_booster": pr(p.pr_booster), "eta_booster": eff("eta_booster"), "duct_25_24": pr(p.duct_25_24),
               "W25": W("25"), "T25": T("25"), "power": _q(P_boost / 1e6, "MW")},
        "M3": {"hpc_pr": pr(r["hpc_pr"], "H"), "eta_hpc": eff("eta_hpc"),
               "leak_bleed_point": _q(p.leak_bleed_point, "- of HPC enthalpy rise", "T"),
               "W3": W("3"), "T3": T("3"), "power": _q(r["P_hpc"] / 1e6, "MW")},
        "M4": {"burner_eta": eff("burner_eta"), "burner_pr": pr(p.burner_pr), "W31": W("31"), "T4": T("4"),
               "fuel_flow": _q(r["W_fuel"], "kg/s", "K", kind="flow"), "FAR": _q(r["f"], "-")},
        "M5": {"eta_hpt": eff("eta_hpt"), "hpt_pr": pr(r["hpt_pr"], "H"), "T41": T("41"), "T44": T("44"),
               "W44": W("44"), "power": _q(r["P_hpt"] / 1e6, "MW")},
        "M6": {"eta_lpt": eff("eta_lpt"), "lpt_pr": pr(r["lpt_pr"], "H"), "duct_45_44": pr(p.duct_45_44),
               "T45": T("45"), "T5": T("5"), "W5": W("5"), "power": _q(r["P_lpt"] / 1e6, "MW")},
        "M7": {"cfg_18": _q(p.cfg_18, "-", "KS", "efficiency"), "cfg_8": _q(p.cfg_8, "-", "T", "efficiency"),
               "cd_18": _q(p.cd_18, "-", "KS", "efficiency"), "cd_8": _q(p.cd_8, "-", "KS", "efficiency"),
               "duct_6_5": pr(p.duct_6_5), "bypass_duct": pr(p.bypass_duct),
               "A18": _q(r["n18"].A * r["W_byp"], "m2"), "A8": _q(r["n8"].A * r["W8"], "m2"),
               "V18_V8_ideal": _q(r["velocity_ratio_ideal"], "-")},
        "M8": {"mech_eff": _q(p.mech_eff, "-", "KS", "efficiency"),
               "hp_power_offtake": _q(p.hp_power_offtake / 1e3, "kW", "KS")},
        "M9": {"ngv": _q(p.ngv, "- of W25", "KS", "flow"), "hpt_rotor": _q(p.hpt_rotor, "- of W25", "KS", "flow"),
               "leak": _q(p.leak, "- of W25", "KS", "flow"),
               "customer_bleed": _q(p.customer_bleed, "kg/s", "T")},
    }


def build_icd(rev: str) -> dict:
    p, t, r, raw, refs = solve_revision(rev)
    st = r["stations"]
    budgets = module_budgets(p, r, raw)
    speeds = refs["girao"]["spool_speeds"]
    T_leak = r["T_leak"]
    return {
        "description": "M0 interface control document and module budgets; generated, do not edit by hand",
        "source": {"revision": rev, "params": f"engine/M0_engine/records/{rev}/params.yaml",
                   "generated_by": "engine/M0_engine/analysis/icd.py", "tag": "H"},
        "ownership_rule": "upstream module owns its exit station (rules/station_ownership.md)",
        "tolerances": {
            "description": "allowed deviation of an achieved module value before M0 re-balances",
            "pressure_ratio": {"value": 0.01, "type": "relative", "tag": "T"},
            "efficiency": {"value": 0.005, "type": "absolute", "tag": "T"},
            "flow": {"value": 0.01, "type": "relative", "tag": "T"},
            "temperature": {"value": 10.0, "type": "absolute", "unit": "K", "tag": "T"},
            "info": {"note": "reported, not checked"},
        },
        "integration": {
            "description": "cycle re-run at the operating point with achieved module values",
            "operating_point": {"W2": _r(r["W2"], SIG_POINT), "T4": _r(r["T4"], SIG_POINT),
                                "delta_eta": _r(p.eta_hpc - load_inputs(module_dir("M0", ROOT) / "records" / rev
                                                                       / "params.yaml")[0].eta_hpc, SIG_POINT),
                                "unit": {"W2": "kg/s", "T4": "K"}, "tag": "H"},
            "reference": {"thrust_kN": _r(r["thrust"] / 1000.0, 9), "sfc_g_kNs": _r(r["W_fuel"] / r["thrust"] * 1e6, 9),
                          "egt_model_K": _r(egt_model_K(r, raw), 9), "tag": "H"},
            "tolerances": {"thrust": {"value": 0.005, "type": "relative", "tag": "T"},
                           "sfc": {"value": 0.005, "type": "relative", "tag": "T"},
                           "egt": {"value": 10.0, "type": "absolute", "unit": "K", "tag": "T"}},
        },
        "stations": {s: {"owner": STATIONS[s][0], "consumers": STATIONS[s][1], "note": STATIONS[s][2],
                         **_station(r, s)} for s in STATIONS},
        "interfaces": [
            {"station": s, "from": owner, "to": to, **_station(r, s)}
            for s, (owner, consumers, _) in STATIONS.items() if owner
            for to in consumers if to != owner
        ],
        "modules": {
            m: {"name": name, "inlet_stations": ins, "exit_stations": outs, "budget": budgets[m]}
            for m, (name, ins, outs) in MODULES.items()
        },
        "shafts": {
            "owner": "M8",
            "LP": {"power_lpt": _q(r["P_lpt"] / 1e6, "MW"), "power_fan_and_booster": _q(
                       (r["P_fan"] + r["P_boost"]) / 1e6, "MW"),
                   "mech_eff": _q(p.mech_eff, "-", "KS"),
                   "speed_refs": {"girao_nominal": speeds["girao_nominal_lp"],
                                  "yilmaz_takeoff_mean": speeds["yilmaz_takeoff_mean_n1"]}},
            "HP": {"power_hpt": _q(r["P_hpt"] / 1e6, "MW"), "power_hpc": _q(r["P_hpc"] / 1e6, "MW"),
                   "hp_offtake": _q(p.hp_power_offtake / 1e3, "kW", "KS"), "mech_eff": _q(p.mech_eff, "-", "KS"),
                   "speed_refs": {"girao_nominal": speeds["girao_nominal_hp"],
                                  "yilmaz_takeoff_mean": speeds["yilmaz_takeoff_mean_n2"]}},
        },
        "secondary_air": {
            "owner": "M9",
            "flows": [
                {"name": "ngv_cooling", "fraction_of_W25": _q(p.ngv, "-", "KS"), "W": _q(r["W_ngv"], "kg/s"),
                 "extraction": "3", "T_extraction": _q(st["3"][0], "K"), "return": "41", "return_module": "M5"},
                {"name": "hpt_rotor_cooling", "fraction_of_W25": _q(p.hpt_rotor, "-", "KS"),
                 "W": _q(r["W_rotor"], "kg/s"), "extraction": "3", "T_extraction": _q(st["3"][0], "K"),
                 "return": "44", "return_module": "M5"},
                {"name": "interstage_leak", "fraction_of_W25": _q(p.leak, "-", "KS"), "W": _q(r["W_leak"], "kg/s"),
                 "extraction": f"HPC interstage at {p.leak_bleed_point:g} of the enthalpy rise (M3 port)",
                 "T_extraction": _q(T_leak, "K"), "return": "45", "return_module": "M6"},
            ],
        },
        "efficiencies_include_delta_eta": list(ETA),
        "fan_face_area": _q(fan_face_area(raw), "m2", "T"),
    }


def main(argv: list[str]) -> int:
    rev = argv[0] if argv else active_revision("M0")
    write_yaml(ICD_FILE, build_icd(rev))
    print(f"wrote {ICD_FILE.relative_to(ROOT).as_posix()} from {rev}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
