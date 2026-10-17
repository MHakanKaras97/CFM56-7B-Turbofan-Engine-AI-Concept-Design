"""M0 cycle v2: two-spool separate-flow turbofan with cooling air, SLS ISA, max take-off.

Stations (SAE AS755): 0 ambient, 2 fan face, 13 fan bypass exit, 18 bypass nozzle,
25 HPC inlet, 3 HPC exit, 4 combustor exit, 41 HPT rotor inlet (after NGV cooling mixes in),
45 LPT inlet (after rotor/LPT cooling mixes in), 5 LPT exit, 8 core nozzle.

Cooling air is bled at station 3 and bypasses the combustor. The NGV share mixes before the
HPT rotor and does HPT work; the rest mixes after the HPT rotor.

Calibration (Newton, finite-difference Jacobian) solves a chosen set of unknowns against the
same number of targets. Default: W2, T4, FPR, cooling fraction against thrust, fuel flow,
V18/V8 = eta_fan_is * eta_LPT_is and combustor air.

Usage:
    python -m engine.M0_engine.analysis.cycle      # writes analysis/results.yaml
"""

import math
import sys
from dataclasses import dataclass, replace
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
STATIONS = ("0", "2", "13", "18", "25", "3", "4", "41", "45", "5", "8")
UNKNOWNS = ("W2", "T4", "FPR", "cooling_fraction")
TARGETS = ("thrust", "fuel", "velocity_ratio", "combustor_air")
E_POLY = ("e_fan", "e_booster", "e_hpc", "e_hpt", "e_lpt")


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
    ngv_share: float = 0.0
    customer_bleed: float = 0.0     # kg/s
    hp_power_offtake: float = 0.0   # W
    include_fuel_mass: bool = True  # False only for the ideal closed-form comparison


@dataclass(frozen=True)
class Targets:
    thrust: float         # N
    fuel: float           # kg/s
    combustor_air: float  # kg/s


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

    gas, comp, dp, sec = raw["gas"], raw["components"], raw["design_point"], raw["secondary_air"]
    params = Params(
        T0=_value(dp["T0"]),
        P0=_value(dp["P0"]),
        opr=float(row["pressure_ratio"]),
        bpr=float(row["bpr"]),
        cold=Gas(_value(gas["cold_cp"]), _value(gas["cold_gamma"]), _value(gas["R"])),
        hot=Gas(_value(gas["hot_cp"]), _value(gas["hot_gamma"]), _value(gas["R"])),
        ngv_share=_value(sec["ngv_share"]),
        customer_bleed=_value(sec["customer_bleed"]),
        hp_power_offtake=_value(sec["hp_power_offtake"]),
        **{k: _value(comp[k]) for k in (
            "inlet_recovery", *E_POLY, "burner_eta", "burner_dp", "bypass_duct_dp",
            "mech_eff", "nozzle_cv", "LHV", "core_pr_25_2")},
    )
    targets = Targets(
        thrust=thrust_kn * 1000.0,
        fuel=float(row["fuel_flow_to_kg_s"]),
        combustor_air=_value(raw["calibration"]["targets"]["combustor_air"]),
    )
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

def _mix(W_hot: float, T_hot: float, W_cool: float, T_cool: float, cold: Gas, hot: Gas):
    """Adiabatic mixing of cooling air (cold cp) into hot gas; result treated as hot gas."""
    W = W_hot + W_cool
    return W, (W_hot * hot.cp * T_hot + W_cool * cold.cp * T_cool) / (W * hot.cp)


def run(p: Params, W2: float, T4: float, FPR: float, cooling_fraction: float = 0.0) -> dict:
    """Evaluate the cycle. cooling_fraction is relative to core flow (station 25)."""
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

    W_cool = cooling_fraction * W_core
    W_ngv = p.ngv_share * W_cool
    W_rotor = W_cool - W_ngv
    W_comb = W_core - W_cool - p.customer_bleed

    f = burner(Tt3, T4, p.burner_eta, p.LHV, cold, hot)
    W_fuel = f * W_comb
    W4 = W_comb + W_fuel if p.include_fuel_mass else W_comb
    Pt4 = Pt3 * (1.0 - p.burner_dp)

    W41, T41 = _mix(W4, T4, W_ngv, Tt3, cold, hot)
    Pt41 = Pt4

    P_fan, P_boost, P_hpc = W_byp * w_fan, W_core * w_boost, W_core * w_hpc
    P_hpt = (P_hpc + p.hp_power_offtake) / p.mech_eff
    P_lpt = (P_fan + P_boost) / p.mech_eff
    Tt44, Pt44, hpt_pr = turbine_for_work(T41, Pt41, P_hpt / W41, p.e_hpt, hot)
    W45, Tt45 = _mix(W41, Tt44, W_rotor, Tt3, cold, hot)
    Pt45 = Pt44
    Tt5, Pt5, lpt_pr = turbine_for_work(Tt45, Pt45, P_lpt / W45, p.e_lpt, hot)
    Tt8, Pt8, W8 = Tt5, Pt5, W45

    n18 = nozzle(Tt18, Pt18, p.P0, p.nozzle_cv, cold)
    n8 = nozzle(Tt8, Pt8, p.P0, p.nozzle_cv, hot)
    F_byp = W_byp * n18.F_per_W
    F_core = W8 * n8.F_per_W
    thrust = F_byp + F_core  # no ram drag at M0 = 0

    stations = {
        "0": (Tt0, Pt0, W2), "2": (Tt2, Pt2, W2), "13": (Tt13, Pt13, W_byp), "18": (Tt18, Pt18, W_byp),
        "25": (Tt25, Pt25, W_core), "3": (Tt3, Pt3, W_core), "4": (T4, Pt4, W4),
        "41": (T41, Pt41, W41), "45": (Tt45, Pt45, W45), "5": (Tt5, Pt5, W8), "8": (Tt8, Pt8, W8),
    }
    return {
        "stations": stations,
        "W2": W2, "T4": T4, "T41": T41, "Tt44": Tt44, "FPR": FPR, "cooling_fraction": cooling_fraction,
        "W_core": W_core, "W_byp": W_byp, "W_cool": W_cool, "W_ngv": W_ngv, "W_rotor": W_rotor,
        "W_comb": W_comb, "W8": W8, "f": f, "W_fuel": W_fuel,
        "hpc_pr": hpc_pr, "hpt_pr": hpt_pr, "lpt_pr": lpt_pr,
        "P_fan": P_fan, "P_boost": P_boost, "P_hpc": P_hpc, "P_hpt": P_hpt, "P_lpt": P_lpt,
        "n18": n18, "n8": n8, "F_byp": F_byp, "F_core": F_core, "thrust": thrust,
        "eta_fan_is": compressor_isentropic_eff(FPR, p.e_fan, cold),
        "eta_lpt_is": turbine_isentropic_eff(lpt_pr, p.e_lpt, hot),
        "velocity_ratio": n18.V / n8.V,
    }


# --- calibration -------------------------------------------------------------------

def _solve(J: list[list[float]], b: list[float]) -> list[float]:
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


def _residual(name: str, r: dict, t: Targets) -> float:
    if name == "thrust":
        return r["thrust"] / t.thrust - 1.0
    if name == "fuel":
        return r["W_fuel"] / t.fuel - 1.0
    if name == "velocity_ratio":
        return r["velocity_ratio"] / (r["eta_fan_is"] * r["eta_lpt_is"]) - 1.0
    if name == "combustor_air":
        return r["W_comb"] / t.combustor_air - 1.0
    raise KeyError(name)


def calibrate(
    p: Params,
    t: Targets,
    initial: dict,
    unknowns: tuple[str, ...] = UNKNOWNS,
    targets: tuple[str, ...] = TARGETS,
    tol: float = 1e-9,
    max_iter: int = 50,
):
    """Newton iteration. Variables not in `unknowns` stay at their `initial` value.

    Returns (result dict, iterations).
    """
    if len(unknowns) != len(targets):
        raise ValueError("number of unknowns must equal number of targets")
    state = {k: initial.get(k, 0.0) for k in UNKNOWNS}

    def evaluate(s):
        r = run(p, s["W2"], s["T4"], s["FPR"], s["cooling_fraction"])
        return r, [_residual(name, r, t) for name in targets]

    for it in range(max_iter + 1):
        r, res = evaluate(state)
        if max(abs(v) for v in res) < tol:
            return r, it
        J = [[0.0] * len(unknowns) for _ in targets]
        for j, name in enumerate(unknowns):
            h = 1e-6 * max(abs(state[name]), 1e-3)
            probe = dict(state, **{name: state[name] + h})
            _, res_p = evaluate(probe)
            for i in range(len(targets)):
                J[i][j] = (res_p[i] - res[i]) / h
        dx = _solve(J, [-v for v in res])
        # damping: at most 30 % change per variable, keep FPR > 1 and 0 <= cooling < 0.5
        scale = 1.0
        for j, name in enumerate(unknowns):
            if dx[j]:
                scale = min(scale, 0.3 * max(abs(state[name]), 0.05) / abs(dx[j]))
        for j, name in enumerate(unknowns):
            new = state[name] + scale * dx[j]
            if name == "FPR" and new <= 1.0:
                scale = min(scale, 0.5 * (state[name] - 1.0) / abs(dx[j]))
            if name == "cooling_fraction" and not 0.0 <= new < 0.5:
                limit = state[name] if dx[j] < 0 else 0.5 - state[name]
                scale = min(scale, 0.5 * limit / abs(dx[j]))
        # backtrack if the step leaves the physical domain (e.g. nozzle Pt < P0)
        for _ in range(20):
            trial = dict(state, **{name: state[name] + scale * dx[j] for j, name in enumerate(unknowns)})
            try:
                evaluate(trial)
                break
            except ValueError:
                scale *= 0.5
        else:
            raise ArithmeticError("calibration step left the physical domain")
        state = trial
    raise ArithmeticError(f"calibration did not converge in {max_iter} iterations; residuals {res}")


# --- derived quantities -----------------------------------------------------------

def _r(x: float, sig: int = 6) -> float:
    return float(f"{x:.{sig}g}")


def _q(value: float, unit: str, tag: str = "H", sig: int = 6) -> dict:
    return {"value": _r(value, sig), "unit": unit, "tag": tag}


def fan_face_area(raw: dict) -> float:
    g = raw["geometry"]
    D = _value(g["fan_diameter"]) * INCH
    return math.pi / 4.0 * D * D * (1.0 - _value(g["fan_hub_tip"]) ** 2)


def choke_mass_flux(Pt: float, Tt: float, gas: Gas) -> float:
    """Maximum mass flow per unit area (M = 1) for total conditions Pt, Tt."""
    g = gas.gamma
    return Pt / math.sqrt(Tt) * math.sqrt(g / gas.R) * (2.0 / (g + 1.0)) ** ((g + 1.0) / (2.0 * (g - 1.0)))


def egt_estimate(raw: dict, T45: float, T5: float) -> float:
    c = raw["checks"]["egt"]
    return c["a"] * (T45 - c["b"] * (T45 - T5))


def egt_displayed_C(r: dict, raw: dict, refs: dict) -> float:
    return egt_estimate(raw, r["stations"]["45"][0], r["stations"]["5"][0]) - 273.15 + refs["egt_shunt_K"]


# --- sensitivity --------------------------------------------------------------------

def sensitivity(p: Params, t: Targets, base: dict, raw: dict, refs: dict, tol: float) -> list[dict]:
    """Recalibrate after each perturbation; report deltas of W2, T4 and displayed EGT.

    e_poly steps: all four unknowns re-solved. Cooling steps: cooling fixed at base +/- step,
    combustor-air target dropped, other three unknowns re-solved.
    """
    cfg = raw["sensitivity"]
    start = {k: base[k] for k in UNKNOWNS}
    egt0 = egt_displayed_C(base, raw, refs)
    rows = []

    def record(label, r):
        rows.append({
            "case": label,
            "dW2_kg_s": _r(r["W2"] - base["W2"], 4),
            "dT4_K": _r(r["T4"] - base["T4"], 4),
            "dEGT_K": _r(egt_displayed_C(r, raw, refs) - egt0, 4),
        })

    for name in E_POLY:
        for sign in (+1, -1):
            step = sign * cfg["e_poly_step"]
            r, _ = calibrate(replace(p, **{name: getattr(p, name) + step}), t, start, tol=tol)
            record(f"{name} {step:+.2f}", r)
    for sign in (+1, -1):
        step = sign * cfg["cooling_step"]
        fixed = dict(start, cooling_fraction=base["cooling_fraction"] + step)
        r, _ = calibrate(p, t, fixed, unknowns=UNKNOWNS[:3], targets=TARGETS[:3], tol=tol)
        record(f"cooling_fraction {step:+.2f}", r)
    return rows


# --- feasibility --------------------------------------------------------------------

def thrust_envelope(p: Params, t: Targets, initial: dict, raw: dict, tol: float,
                    c_max: float = 0.40, step: float = 0.01) -> list[dict]:
    """Thrust reachable when fuel, V18/V8 and combustor air are matched, for each cooling fraction.

    Uses continuation: each point starts from the previous solution.
    """
    guess = dict(initial, cooling_fraction=0.0)
    guess.update(W2=t.combustor_air * (1.0 + p.bpr), FPR=2.0)
    A_fan = fan_face_area(raw)
    out = []
    for i in range(int(round(c_max / step)) + 1):
        guess["cooling_fraction"] = i * step
        r, _ = calibrate(p, t, guess, unknowns=UNKNOWNS[:3],
                         targets=("fuel", "velocity_ratio", "combustor_air"), tol=tol)
        guess.update({k: r[k] for k in UNKNOWNS[:3]})
        out.append({
            "cooling_fraction": _r(i * step, 3),
            "thrust_kN": _r(r["thrust"] / 1000.0, 5),
            "W2_kg_s": _r(r["W2"], 4),
            "FPR": _r(r["FPR"], 4),
            "T4_K": _r(r["T4"], 4),
            "W2_per_A": _r(r["W2"] / A_fan, 4),
        })
    return out


# --- outputs ------------------------------------------------------------------------

def build_checks(r: dict, p: Params, raw: dict, refs: dict) -> list[dict]:
    cfg = raw["checks"]
    sfc = r["W_fuel"] / r["thrust"] * 1e6
    A_fan = fan_face_area(raw)
    w2a = r["W2"] / A_fan
    choke = choke_mass_flux(p.P0, p.T0, p.cold)
    w2_ref = cfg["w2_ref"]
    lo, hi = cfg["w2a_range"]["min"], cfg["w2a_range"]["max"]
    c_lo, c_hi = cfg["cooling_range"]["min"], cfg["cooling_range"]["max"]
    egt_disp = egt_displayed_C(r, raw, refs)
    band = cfg["egt_display_band"]
    T4_refs = {k: _value(v) for k, v in cfg["T4_refs"].items()}
    T3, T3_ref = r["stations"]["3"][0], _value(cfg["T3_ref"])

    def verdict(ok: bool) -> str:
        return "pass" if ok else "fail"

    return [
        {"name": "Fan choke (HARD)", "hard": True, "value": _r(w2a, 4), "reference": _r(choke, 4),
         "unit": "kg/(s m2)", "criterion": "W2/A < choke mass flux at SLS ISA", "result": verdict(w2a < choke)},
        {"name": "Fan specific flow W2/A", "value": _r(w2a, 4), "reference": [lo, hi], "unit": "kg/(s m2)",
         "criterion": f"{lo:g} <= W2/A <= {hi:g}", "result": verdict(lo <= w2a <= hi)},
        {"name": "W2 vs estimate", "value": _r(r["W2"], 5), "reference": w2_ref["value"], "unit": "kg/s",
         "deviation": _r(r["W2"] / w2_ref["value"] - 1.0, 3), "criterion": f"within {w2_ref['tolerance']:.0%}",
         "result": verdict(abs(r["W2"] / w2_ref["value"] - 1.0) <= w2_ref["tolerance"])},
        {"name": "Total cooling fraction", "value": _r(r["cooling_fraction"], 4), "reference": [c_lo, c_hi],
         "unit": "- of core flow", "criterion": f"{c_lo:g} <= c <= {c_hi:g}",
         "result": verdict(c_lo <= r["cooling_fraction"] <= c_hi)},
        {"name": "SFC vs ICAO/TCDS", "value": _r(sfc), "reference": refs["sfc_ref"], "unit": "g/(kN s)",
         "criterion": f"within {cfg['sfc_tolerance']['value']:.1%}",
         "result": verdict(abs(sfc / refs["sfc_ref"] - 1.0) <= cfg["sfc_tolerance"]["value"])},
        {"name": "EGT displayed vs TCDS limit", "value": _r(egt_disp, 4), "reference": refs["egt_limit_displayed_C"],
         "unit": "degC", "margin": _r(refs["egt_limit_displayed_C"] - egt_disp, 4),
         "criterion": f"model + {refs['egt_shunt_K']:g} K shunt < {refs['egt_limit_displayed_C']:g}",
         "result": verdict(egt_disp < refs["egt_limit_displayed_C"])},
        {"name": "EGT displayed vs expected band", "value": _r(egt_disp, 4), "reference": [band["min"], band["max"]],
         "unit": "degC", "criterion": "info only",
         "in_band": band["min"] <= egt_disp <= band["max"], "result": "info"},
        {"name": "T4 vs references", "value": _r(r["T4"], 5), "reference": T4_refs, "unit": "K",
         "deviation": {k: _r(r["T4"] / v - 1.0, 3) for k, v in T4_refs.items()},
         "criterion": "info only", "result": "info"},
        {"name": "T3 vs test cell", "value": _r(T3, 5), "reference": T3_ref, "unit": "K",
         "deviation": _r(T3 / T3_ref - 1.0, 3), "criterion": "info only (test cell T0 298 K, not ISA)",
         "result": "info"},
    ]


def build_results(r: dict, p: Params, t: Targets, raw: dict, refs: dict, iterations: int,
                  sens: list[dict] | None = None) -> dict:
    sfc = r["W_fuel"] / r["thrust"] * 1e6  # g/(kN s)
    A_fan = fan_face_area(raw)
    T45, T5 = r["stations"]["45"][0], r["stations"]["5"][0]
    egt_K = egt_estimate(raw, T45, T5)
    checks = build_checks(r, p, raw, refs)
    results = {
        "model": "M0 cycle v2, two-spool separate-flow, cooling air from HPC exit",
        "design_point": {"condition": "SLS ISA, max take-off", "icao_uid": refs["icao_uid"],
                         "T0": _q(p.T0, "K", "G"), "P0": _q(p.P0, "Pa", "G")},
        "calibration": {
            "iterations": iterations,
            "targets": {"thrust": _q(t.thrust / 1000.0, "kN", "K"), "fuel_flow": _q(t.fuel, "kg/s", "K"),
                        "velocity_ratio": "V18/V8 = eta_fan_is * eta_LPT_is",
                        "combustor_air": _q(t.combustor_air, "kg/s", "KS")},
            "W2": _q(r["W2"], "kg/s"), "T4": _q(r["T4"], "K"), "FPR": _q(r["FPR"], "-"),
            "cooling_fraction": _q(r["cooling_fraction"], "- of core flow"),
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
            "T4": _q(r["T4"], "K"),
            "T41": _q(r["T41"], "K"),
            "Tt44_hpt_exit_before_mixing": _q(r["Tt44"], "K"),
            "W_core": _q(r["W_core"], "kg/s"),
            "W_bypass": _q(r["W_byp"], "kg/s"),
            "W_combustor": _q(r["W_comb"], "kg/s"),
            "W_cooling": _q(r["W_cool"], "kg/s"),
            "W_cooling_ngv": _q(r["W_ngv"], "kg/s"),
            "W_cooling_rotor_lpt": _q(r["W_rotor"], "kg/s"),
            "V18": _q(r["n18"].V, "m/s"), "V8": _q(r["n8"].V, "m/s"),
            "velocity_ratio": _q(r["velocity_ratio"], "-"),
            "eta_fan_is": _q(r["eta_fan_is"], "-"), "eta_lpt_is": _q(r["eta_lpt_is"], "-"),
            "A18": _q(r["n18"].A * r["W_byp"], "m2"), "A8": _q(r["n8"].A * r["W8"], "m2"),
            "nozzle18_choked": r["n18"].choked, "nozzle8_choked": r["n8"].choked,
        },
        "shaft_power_MW": {
            "fan": _q(r["P_fan"] / 1e6, "MW"), "booster": _q(r["P_boost"] / 1e6, "MW"),
            "hpc": _q(r["P_hpc"] / 1e6, "MW"), "hpt": _q(r["P_hpt"] / 1e6, "MW"),
            "lpt": _q(r["P_lpt"] / 1e6, "MW"), "hp_offtake": _q(p.hp_power_offtake / 1e6, "MW", "T"),
        },
        "fan": {"face_area": _q(A_fan, "m2", "T"), "specific_flow": _q(r["W2"] / A_fan, "kg/(s m2)"),
                "choke_mass_flux": _q(choke_mass_flux(p.P0, p.T0, p.cold), "kg/(s m2)")},
        "egt": {"model_K": _q(egt_K, "K", "T"), "model_C": _q(egt_K - 273.15, "degC", "T"),
                "displayed_C": _q(egt_K - 273.15 + refs["egt_shunt_K"], "degC", "T"),
                "note": "CFM56-3 form via Martins 2015, applied in K; displayed = model + SAC shunt"},
        "checks": checks,
        "hard_checks_passed": all(c["result"] == "pass" for c in checks if c.get("hard")),
    }
    if sens is not None:
        results["sensitivity"] = {
            "method": "recalibrated per case; cooling cases fix cooling and drop the combustor-air target",
            "cases": sens,
        }
    return results


def infeasible_results(p: Params, t: Targets, initial: dict, raw: dict, tol: float, error: str) -> dict:
    envelope = thrust_envelope(p, t, initial, raw, tol)
    best = max(envelope, key=lambda e: e["thrust_kN"])
    return {
        "model": "M0 cycle v2, two-spool separate-flow, cooling air from HPC exit",
        "status": "infeasible",
        "reason": "no solution matches all calibration targets with the current assumptions",
        "solver_message": error,
        "max_reachable_thrust": {"value": best["thrust_kN"], "unit": "kN", "tag": "H",
                                 "at_cooling_fraction": best["cooling_fraction"]},
        "target_thrust": _q(t.thrust / 1000.0, "kN", "K"),
        "envelope": {
            "description": "fuel, V18/V8 and combustor air matched; thrust is the free output",
            "points": envelope,
        },
    }


def main(argv: list[str]) -> int:
    p, t, initial, raw, refs = load_inputs()
    tol = _value(raw["calibration"]["tolerance"])
    try:
        r, iterations = calibrate(p, t, initial, tol=tol)
    except ArithmeticError as exc:
        results = infeasible_results(p, t, initial, raw, tol, str(exc))
        write_yaml(RESULTS_FILE, results)
        m = results["max_reachable_thrust"]
        print(f"INFEASIBLE: max thrust {m['value']} kN at cooling {m['at_cooling_fraction']} "
              f"(target {results['target_thrust']['value']} kN)")
        return 1
    sens = sensitivity(p, t, r, raw, refs, tol)
    results = build_results(r, p, t, raw, refs, iterations, sens)
    write_yaml(RESULTS_FILE, results)
    print(f"W2={r['W2']:.2f} kg/s  T4={r['T4']:.1f} K  T41={r['T41']:.1f} K  FPR={r['FPR']:.4f}  "
          f"cool={r['cooling_fraction']:.4f}  ({iterations} it)")
    for c in results["checks"]:
        print(f"  [{c['result']:>4}] {c['name']}: {c['value']} (ref {c['reference']})")
    for s in sens:
        print(f"  {s['case']:<24} dW2={s['dW2_kg_s']:>8} dT4={s['dT4_K']:>8} dEGT={s['dEGT_K']:>8}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
