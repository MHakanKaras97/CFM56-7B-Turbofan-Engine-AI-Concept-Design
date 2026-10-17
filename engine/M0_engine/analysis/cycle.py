"""M0 cycle v1: two-spool separate-flow turbofan, design point SLS ISA, max take-off.

Stations (SAE AS755): 0 ambient, 2 fan face, 13 fan bypass exit, 18 bypass nozzle,
25 HPC inlet, 3 HPC exit, 4 HPT inlet, 45 LPT inlet, 5 LPT exit, 8 core nozzle.

Calibration unknowns W2, T4, FPR are solved (Newton, finite-difference Jacobian) so that
thrust and fuel flow match the [K] targets and V18/V8 = eta_fan_is * eta_LPT_is.

Usage:
    python -m engine.M0_engine.analysis.cycle      # writes analysis/results.yaml
"""

import math
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

from core.util import read_yaml, write_yaml
from tools.thermo import (
    Gas,
    burner,
    compressor,
    compressor_isentropic_eff,
    nozzle,
    turbine_for_work,
    turbine_isentropic_eff,
)

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PARAMS_FILE = HERE / "cycle_params.yaml"
RESULTS_FILE = HERE / "results.yaml"
INCH = 0.0254
STATIONS = ("0", "2", "13", "18", "25", "3", "4", "45", "5", "8")


@dataclass(frozen=True)
class Params:
    T0: float
    P0: float
    opr: float
    bpr: float
    cold: Gas
    hot: Gas
    inlet_recovery: float
    e_fan: float
    e_booster: float
    e_hpc: float
    e_hpt: float
    e_lpt: float
    burner_eta: float
    burner_dp: float
    bypass_duct_dp: float
    mech_eff: float
    nozzle_cv: float
    LHV: float
    core_pr_25_2: float
    include_fuel_mass: bool = True  # False only for the ideal closed-form comparison


@dataclass
class Targets:
    thrust: float  # N
    fuel: float    # kg/s


# --- inputs ---------------------------------------------------------------------

def _value(q: dict) -> float:
    return float(q["value"])


def _dig(data: dict, dotted: str):
    for key in dotted.split("."):
        data = data[key]
    return data


def load_inputs(params_file: Path = PARAMS_FILE, root: Path = ROOT):
    """Return (Params, Targets, initial guess dict, raw params yaml, reference values)."""
    raw = read_yaml(params_file)
    refs = raw["reference_data"]

    tcds = read_yaml(root / refs["thrust_to"]["file"])
    thrust_kn = _value(_dig(tcds, refs["thrust_to"]["key"]))
    icao = read_yaml(root / refs["icao_row"]["file"])
    row = next(r for r in icao["rows"] if r["uid"] == refs["icao_row"]["uid"])
    sfc_rows = read_yaml(root / refs["sfc_ref"]["file"])["rows"]
    sfc_ref = next(r for r in sfc_rows if r["uid"] == refs["sfc_ref"]["uid"])["sfc"]["value"]

    gas, comp, dp = raw["gas"], raw["components"], raw["design_point"]
    params = Params(
        T0=_value(dp["T0"]),
        P0=_value(dp["P0"]),
        opr=float(row["pressure_ratio"]),
        bpr=float(row["bpr"]),
        cold=Gas(_value(gas["cold_cp"]), _value(gas["cold_gamma"]), _value(gas["R"])),
        hot=Gas(_value(gas["hot_cp"]), _value(gas["hot_gamma"]), _value(gas["R"])),
        **{k: _value(comp[k]) for k in (
            "inlet_recovery", "e_fan", "e_booster", "e_hpc", "e_hpt", "e_lpt", "burner_eta",
            "burner_dp", "bypass_duct_dp", "mech_eff", "nozzle_cv", "LHV", "core_pr_25_2")},
    )
    targets = Targets(thrust=thrust_kn * 1000.0, fuel=float(row["fuel_flow_to_kg_s"]))
    initial = {k: _value(v) for k, v in raw["calibration"]["initial"].items()}
    egt_keys = raw["checks"]["egt_limit"]["keys"]
    references = {
        "thrust_kN": thrust_kn,
        "icao_uid": row["uid"],
        "sfc_ref": sfc_ref,
        "egt_limit_displayed_C": _value(_dig(tcds, egt_keys[0])),
        "egt_shunt_K": _value(_dig(tcds, egt_keys[1])),
    }
    return params, targets, initial, raw, references


# --- cycle ------------------------------------------------------------------------

def run(p: Params, W2: float, T4: float, FPR: float) -> dict:
    """Evaluate the cycle for given W2 [kg/s], T4 [K], FPR. Returns stations and performance."""
    cold, hot = p.cold, p.hot
    W_core = W2 / (1.0 + p.bpr)
    W_byp = W2 - W_core

    Tt0, Pt0 = p.T0, p.P0  # M0 = 0
    Tt2, Pt2 = Tt0, Pt0 * p.inlet_recovery

    Tt13, Pt13, w_fan = compressor(Tt2, Pt2, FPR, p.e_fan, cold)
    Tt18, Pt18 = Tt13, Pt13 * (1.0 - p.bypass_duct_dp)

    Tt25, Pt25, w_boost = compressor(Tt2, Pt2, p.core_pr_25_2, p.e_booster, cold)
    hpc_pr = p.opr / p.core_pr_25_2
    Tt3, Pt3, w_hpc = compressor(Tt25, Pt25, hpc_pr, p.e_hpc, cold)

    f = burner(Tt3, T4, p.burner_eta, p.LHV, cold, hot)
    W_fuel = f * W_core
    W_hot = W_core + W_fuel if p.include_fuel_mass else W_core
    Pt4 = Pt3 * (1.0 - p.burner_dp)

    P_fan, P_boost, P_hpc = W_byp * w_fan, W_core * w_boost, W_core * w_hpc
    P_hpt = P_hpc / p.mech_eff
    P_lpt = (P_fan + P_boost) / p.mech_eff
    Tt45, Pt45, hpt_pr = turbine_for_work(T4, Pt4, P_hpt / W_hot, p.e_hpt, hot)
    Tt5, Pt5, lpt_pr = turbine_for_work(Tt45, Pt45, P_lpt / W_hot, p.e_lpt, hot)
    Tt8, Pt8 = Tt5, Pt5

    n18 = nozzle(Tt18, Pt18, p.P0, p.nozzle_cv, cold)
    n8 = nozzle(Tt8, Pt8, p.P0, p.nozzle_cv, hot)
    F_byp = W_byp * n18.F_per_W
    F_core = W_hot * n8.F_per_W
    thrust = F_byp + F_core  # no ram drag at M0 = 0

    eta_fan_is = compressor_isentropic_eff(FPR, p.e_fan, cold)
    eta_lpt_is = turbine_isentropic_eff(lpt_pr, p.e_lpt, hot)

    stations = {
        "0": (Tt0, Pt0, W2), "2": (Tt2, Pt2, W2), "13": (Tt13, Pt13, W_byp), "18": (Tt18, Pt18, W_byp),
        "25": (Tt25, Pt25, W_core), "3": (Tt3, Pt3, W_core), "4": (T4, Pt4, W_hot),
        "45": (Tt45, Pt45, W_hot), "5": (Tt5, Pt5, W_hot), "8": (Tt8, Pt8, W_hot),
    }
    return {
        "stations": stations,
        "W2": W2, "T4": T4, "FPR": FPR, "W_core": W_core, "W_byp": W_byp, "W_hot": W_hot,
        "f": f, "W_fuel": W_fuel, "hpc_pr": hpc_pr, "hpt_pr": hpt_pr, "lpt_pr": lpt_pr,
        "P_fan": P_fan, "P_boost": P_boost, "P_hpc": P_hpc, "P_hpt": P_hpt, "P_lpt": P_lpt,
        "n18": n18, "n8": n8, "F_byp": F_byp, "F_core": F_core, "thrust": thrust,
        "eta_fan_is": eta_fan_is, "eta_lpt_is": eta_lpt_is,
        "velocity_ratio": n18.V / n8.V,
    }


# --- calibration -------------------------------------------------------------------

def _solve3(J: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(J)]
    for c in range(n):
        pivot = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[pivot][c]) < 1e-14:
            raise ArithmeticError("singular Jacobian")
        M[c], M[pivot] = M[pivot], M[c]
        for r in range(c + 1, n):
            factor = M[r][c] / M[c][c]
            for k in range(c, n + 1):
                M[r][k] -= factor * M[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (M[r][n] - sum(M[r][k] * x[k] for k in range(r + 1, n))) / M[r][r]
    return x


def residuals(p: Params, t: Targets, x: list[float]) -> list[float]:
    r = run(p, *x)
    return [
        r["thrust"] / t.thrust - 1.0,
        r["W_fuel"] / t.fuel - 1.0,
        r["velocity_ratio"] / (r["eta_fan_is"] * r["eta_lpt_is"]) - 1.0,
    ]


def calibrate(p: Params, t: Targets, initial: dict, tol: float = 1e-9, max_iter: int = 50):
    """Newton iteration on (W2, T4, FPR). Returns (result dict, iterations)."""
    x = [initial["W2"], initial["T4"], initial["FPR"]]
    for it in range(1, max_iter + 1):
        r0 = residuals(p, t, x)
        if max(abs(v) for v in r0) < tol:
            return run(p, *x), it - 1
        J = [[0.0] * 3 for _ in range(3)]
        for j in range(3):
            h = 1e-6 * abs(x[j])
            xp = x[:]
            xp[j] += h
            rp = residuals(p, t, xp)
            for i in range(3):
                J[i][j] = (rp[i] - r0[i]) / h
        dx = _solve3(J, [-v for v in r0])
        # damp steps that would push FPR to <= 1 or change a variable by more than 30 %
        scale = min([1.0] + [0.3 * abs(x[j]) / abs(dx[j]) for j in range(3) if dx[j]])
        if x[2] + scale * dx[2] <= 1.0:
            scale = min(scale, 0.5 * (x[2] - 1.0) / abs(dx[2]))
        x = [x[j] + scale * dx[j] for j in range(3)]
    raise ArithmeticError(f"calibration did not converge in {max_iter} iterations; residuals {r0}")


# --- outputs ------------------------------------------------------------------------

def _r(x: float, sig: int = 6) -> float:
    return float(f"{x:.{sig}g}")


def _q(value: float, unit: str, tag: str = "H", sig: int = 6) -> dict:
    return {"value": _r(value, sig), "unit": unit, "tag": tag}


def fan_face_area(raw: dict) -> float:
    g = raw["geometry"]
    D = _value(g["fan_diameter"]) * INCH
    return math.pi / 4.0 * D * D * (1.0 - _value(g["fan_hub_tip"]) ** 2)


def egt_estimate(raw: dict, T45: float, T5: float) -> float:
    c = raw["checks"]["egt"]
    return c["a"] * (T45 - c["b"] * (T45 - T5))


def build_results(r: dict, p: Params, t: Targets, raw: dict, refs: dict, iterations: int) -> dict:
    sfc = r["W_fuel"] / (r["thrust"] / 1000.0) * 1000.0  # g/(kN s)
    A_fan = fan_face_area(raw)
    w2a = r["W2"] / A_fan
    T45, T5 = r["stations"]["45"][0], r["stations"]["5"][0]
    egt_K = egt_estimate(raw, T45, T5)
    egt_C = egt_K - 273.15
    egt_displayed_C = egt_C + refs["egt_shunt_K"]
    egt_limit_C = refs["egt_limit_displayed_C"]
    T3 = r["stations"]["3"][0]

    checks_cfg = raw["checks"]
    w2_ref = checks_cfg["w2_ref"]
    lo, hi = checks_cfg["w2a_range"]["min"], checks_cfg["w2a_range"]["max"]
    air_refs = {k: _value(v) for k, v in checks_cfg["core_air_refs"].items()}
    air_dev = {k: r["W_core"] / v - 1.0 for k, v in air_refs.items()}
    closest = min(air_dev, key=lambda k: abs(air_dev[k]))

    checks = [
        {
            "name": "SFC vs ICAO/TCDS",
            "value": _r(sfc), "reference": refs["sfc_ref"], "unit": "g/(kN s)",
            "criterion": f"within {checks_cfg['sfc_tolerance']['value']:.1%}",
            "result": "pass" if abs(sfc / refs["sfc_ref"] - 1.0) <= checks_cfg["sfc_tolerance"]["value"] else "fail",
        },
        {
            "name": "Fan specific flow W2/A",
            "value": _r(w2a, 4), "reference": [lo, hi], "unit": "kg/(s m2)",
            "criterion": f"{lo:g} <= W2/A <= {hi:g}",
            "result": "pass" if lo <= w2a <= hi else "fail",
        },
        {
            "name": "W2 vs estimate",
            "value": _r(r["W2"], 5), "reference": w2_ref["value"], "unit": "kg/s",
            "deviation": _r(r["W2"] / w2_ref["value"] - 1.0, 3),
            "criterion": f"within {w2_ref['tolerance']:.0%}",
            "result": "pass" if abs(r["W2"] / w2_ref["value"] - 1.0) <= w2_ref["tolerance"] else "fail",
        },
        {
            "name": "EGT (displayed) vs TCDS limit",
            "value": _r(egt_displayed_C, 4), "reference": egt_limit_C, "unit": "degC",
            "margin": _r(egt_limit_C - egt_displayed_C, 4),
            "criterion": f"model EGT + {refs['egt_shunt_K']:g} K shunt < {egt_limit_C:g} degC",
            "result": "pass" if egt_displayed_C < egt_limit_C else "fail",
        },
        {
            "name": "Core air vs references",
            "value": _r(r["W_core"], 5), "reference": air_refs, "unit": "kg/s",
            "deviation": {k: _r(v, 3) for k, v in air_dev.items()},
            "criterion": f"closest: {closest}",
            "result": "info",
        },
        {
            "name": "T3 vs test cell",
            "value": _r(T3, 5), "reference": _value(checks_cfg["T3_ref"]), "unit": "K",
            "deviation": _r(T3 / _value(checks_cfg["T3_ref"]) - 1.0, 3),
            "criterion": "info only (test cell T0 298 K, not ISA)",
            "result": "info",
        },
    ]

    return {
        "model": "M0 cycle v1, two-spool separate-flow, no cooling bleed",
        "design_point": {"condition": "SLS ISA, max take-off", "icao_uid": refs["icao_uid"],
                         "T0": _q(p.T0, "K", "G"), "P0": _q(p.P0, "Pa", "G")},
        "calibration": {
            "iterations": iterations,
            "targets": {"thrust": _q(t.thrust / 1000.0, "kN", "K"), "fuel_flow": _q(t.fuel, "kg/s", "K"),
                        "velocity_ratio": "V18/V8 = eta_fan_is * eta_LPT_is"},
            "W2": _q(r["W2"], "kg/s"), "T4": _q(r["T4"], "K"), "FPR": _q(r["FPR"], "-"),
        },
        "stations": [
            {"station": s, "Tt_K": _r(v[0], 5), "Pt_kPa": _r(v[1] / 1000.0, 5), "W_kg_s": _r(v[2], 5)}
            for s, v in ((s, r["stations"][s]) for s in STATIONS)
        ],
        "performance": {
            "thrust": _q(r["thrust"] / 1000.0, "kN"),
            "thrust_bypass": _q(r["F_byp"] / 1000.0, "kN"),
            "thrust_core": _q(r["F_core"] / 1000.0, "kN"),
            "fuel_flow": _q(r["W_fuel"], "kg/s"),
            "fuel_air_ratio": _q(r["f"], "-"),
            "sfc": _q(sfc, "g/(kN s)"),
            "specific_thrust": _q(r["thrust"] / r["W2"], "N/(kg/s)"),
            "opr": _q(p.opr, "-", "K"),
            "bpr": _q(p.bpr, "-", "K"),
            "core_pr_25_2": _q(p.core_pr_25_2, "-", "T"),
            "hpc_pr": _q(r["hpc_pr"], "-"),
            "hpt_pr": _q(r["hpt_pr"], "-"),
            "lpt_pr": _q(r["lpt_pr"], "-"),
            "W_core": _q(r["W_core"], "kg/s"),
            "W_bypass": _q(r["W_byp"], "kg/s"),
            "V18": _q(r["n18"].V, "m/s"), "V8": _q(r["n8"].V, "m/s"),
            "velocity_ratio": _q(r["velocity_ratio"], "-"),
            "eta_fan_is": _q(r["eta_fan_is"], "-"), "eta_lpt_is": _q(r["eta_lpt_is"], "-"),
            "A18": _q(r["n18"].A * r["W_byp"], "m2"), "A8": _q(r["n8"].A * r["W_hot"], "m2"),
            "nozzle18_choked": r["n18"].choked, "nozzle8_choked": r["n8"].choked,
        },
        "shaft_power_MW": {
            "fan": _q(r["P_fan"] / 1e6, "MW"), "booster": _q(r["P_boost"] / 1e6, "MW"),
            "hpc": _q(r["P_hpc"] / 1e6, "MW"), "hpt": _q(r["P_hpt"] / 1e6, "MW"),
            "lpt": _q(r["P_lpt"] / 1e6, "MW"),
        },
        "fan": {"face_area": _q(A_fan, "m2", "T"), "specific_flow": _q(w2a, "kg/(s m2)")},
        "egt": {"model_K": _q(egt_K, "K", "T"), "model_C": _q(egt_C, "degC", "T"),
                "displayed_C": _q(egt_displayed_C, "degC", "T"),
                "note": "CFM56-3 form via Martins 2015, applied in K; displayed = model + SAC shunt"},
        "checks": checks,
    }


def main(argv: list[str]) -> int:
    p, t, initial, raw, refs = load_inputs()
    tol = _value(raw["calibration"]["tolerance"])
    r, iterations = calibrate(p, t, initial, tol=tol)
    results = build_results(r, p, t, raw, refs, iterations)
    write_yaml(RESULTS_FILE, results)
    perf = results["performance"]
    print(f"W2={r['W2']:.2f} kg/s  T4={r['T4']:.1f} K  FPR={r['FPR']:.4f}  ({iterations} it)")
    print(f"F={perf['thrust']['value']} kN  SFC={perf['sfc']['value']} g/kNs  HPC PR={perf['hpc_pr']['value']}")
    for c in results["checks"]:
        print(f"  [{c['result']:>4}] {c['name']}: {c['value']} (ref {c['reference']})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
