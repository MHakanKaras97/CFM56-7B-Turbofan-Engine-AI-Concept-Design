"""M0 cycle v4: two-spool separate-flow turbofan, CFM56-7B-specific inputs (Girão 2023), SLS ISA, max take-off.

Stations (SAE AS755): 0 ambient, 2 fan face, 13 fan bypass exit, 18 bypass nozzle (after the
P16/P13 duct), 24 booster exit, 25 HPC inlet, 3 HPC exit, 31 combustor inlet (after secondary
air bleed), 4 combustor exit, 41 HPT rotor inlet (after NGV cooling mixes in), 44 HPT exit,
45 LPT inlet (after rotor cooling and leakage mix in, P45/P44 duct), 5 LPT exit,
8 core nozzle (after the P6/P5 duct).

Gas properties: variable cp(T, FAR) from NASA polynomials (tools.thermo.NasaGas); a constant-cp
gas can be switched in for closed-form checks. Station FAR is carried through mixing.

Secondary air is bled at station 3 as fixed fractions of W25 and bypasses the combustor:
NGV cooling mixes before the HPT rotor and does HPT work; HPT rotor cooling and leakage mix
at station 45.

FPR is an input (ADR-008). Calibration (Newton, finite-difference Jacobian) solves W2 and T4
against thrust and fuel flow. V18/V8 is reported for information only.

Usage:
    python -m engine.M0_engine.analysis.cycle              # writes analysis/results.yaml
    python -m engine.M0_engine.analysis.cycle --validate   # Girão validation case, prints only
"""

import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path

from core.util import read_yaml, write_yaml
from tools.thermo import (
    ConstantCp,
    NasaGas,
    burner,
    choke_mass_flux,
    compressor,
    compressor_isentropic_eff,
    mix,
    nozzle,
    turbine_for_work,
    turbine_isentropic_eff,
)

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PARAMS_FILE = HERE / "cycle_params.yaml"
RESULTS_FILE = HERE / "results.yaml"
INCH = 0.0254
STATIONS = ("0", "2", "13", "18", "24", "25", "3", "31", "4", "41", "44", "45", "5", "8")
UNKNOWNS = ("W2", "T4")
TARGETS = ("thrust", "fuel")
E_POLY = ("e_fan", "e_booster", "e_hpc", "e_hpt", "e_lpt")
COMPONENTS = ("inlet_recovery", "FPR", *E_POLY, "core_pr_25_2", "duct_25_24", "burner_eta", "burner_pr",
              "duct_45_44", "duct_6_5", "bypass_duct", "mech_eff", "nozzle_cv", "LHV")


@dataclass(frozen=True)
class Params:
    T0: float
    P0: float
    opr: float          # P3/P2
    bpr: float
    gas: object         # tools.thermo gas model (NasaGas or ConstantCp)
    inlet_recovery: float
    FPR: float
    e_fan: float
    e_booster: float
    e_hpc: float
    e_hpt: float
    e_lpt: float
    core_pr_25_2: float  # P25/P2 including the P25/P24 duct
    duct_25_24: float
    burner_eta: float
    burner_pr: float     # P4/P3
    duct_45_44: float
    duct_6_5: float
    bypass_duct: float   # P16/P13
    mech_eff: float
    nozzle_cv: float
    LHV: float
    ngv: float = 0.0        # secondary air, fractions of W25
    hpt_rotor: float = 0.0
    leak: float = 0.0
    customer_bleed: float = 0.0     # kg/s
    hp_power_offtake: float = 0.0   # W
    include_fuel_mass: bool = True  # False only for the ideal closed-form comparison

    @property
    def secondary_fraction(self) -> float:
        return self.ngv + self.hpt_rotor + self.leak


@dataclass(frozen=True)
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
    girao = read_yaml(root / refs["girao"]["file"])

    gas, comp, dp, sec = raw["gas"], raw["components"], raw["design_point"], raw["secondary_air"]
    if gas["model"] == "nasa_glenn":
        gas_model = NasaGas(root / gas["data"])
    elif gas["model"] == "constant_cp":
        c = gas["constant_cp"]
        gas_model = ConstantCp(_value(c["cp"]), _value(c["gamma"]), _value(c["R"]))
    else:
        raise ValueError(f"unknown gas model {gas['model']!r}")
    params = Params(
        T0=_value(dp["T0"]),
        P0=_value(dp["P0"]),
        opr=float(row["pressure_ratio"]),
        bpr=float(row["bpr"]),
        gas=gas_model,
        **{k: _value(comp[k]) for k in COMPONENTS},
        **{k: _value(sec[k]) for k in ("ngv", "hpt_rotor", "leak", "customer_bleed", "hp_power_offtake")},
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
        "girao": girao,
    }
    return params, targets, initial, raw, references


# --- cycle ------------------------------------------------------------------------

def run(p: Params, W2: float, T4: float) -> dict:
    """Evaluate the cycle at fan flow W2 [kg/s] and combustor exit temperature T4 [K]."""
    gas = p.gas
    W_core = W2 / (1.0 + p.bpr)
    W_byp = W2 - W_core

    Tt0, Pt0 = p.T0, p.P0  # M0 = 0
    Tt2, Pt2 = Tt0, Pt0 * p.inlet_recovery

    Tt13, Pt13, w_fan = compressor(Tt2, Pt2, p.FPR, p.e_fan, gas)
    Tt18, Pt18 = Tt13, Pt13 * p.bypass_duct

    Tt24, Pt24, w_boost = compressor(Tt2, Pt2, p.core_pr_25_2 / p.duct_25_24, p.e_booster, gas)
    Tt25, Pt25 = Tt24, Pt24 * p.duct_25_24
    hpc_pr = p.opr / p.core_pr_25_2
    Tt3, Pt3, w_hpc = compressor(Tt25, Pt25, hpc_pr, p.e_hpc, gas)

    W_ngv = p.ngv * W_core
    W_rotor = p.hpt_rotor * W_core
    W_leak = p.leak * W_core
    W_sec = W_ngv + W_rotor + W_leak
    W_comb = W_core - W_sec - p.customer_bleed

    f = burner(Tt3, T4, p.burner_eta, p.LHV, gas)
    W_fuel = f * W_comb
    W4 = W_comb + W_fuel if p.include_fuel_mass else W_comb
    Pt4 = Pt3 * p.burner_pr

    W41, T41, f41 = mix(W4, T4, f, W_ngv, Tt3, 0.0, gas)
    Pt41 = Pt4

    P_fan, P_boost, P_hpc = W_byp * w_fan, W_core * w_boost, W_core * w_hpc
    P_hpt = (P_hpc + p.hp_power_offtake) / p.mech_eff
    P_lpt = (P_fan + P_boost) / p.mech_eff
    Tt44, Pt44, hpt_pr = turbine_for_work(T41, Pt41, P_hpt / W41, p.e_hpt, gas, f41)
    W45, Tt45, f45 = mix(W41, Tt44, f41, W_rotor + W_leak, Tt3, 0.0, gas)
    Pt45 = Pt44 * p.duct_45_44
    Tt5, Pt5, lpt_pr = turbine_for_work(Tt45, Pt45, P_lpt / W45, p.e_lpt, gas, f45)
    Tt8, Pt8, W8 = Tt5, Pt5 * p.duct_6_5, W45

    n18 = nozzle(Tt18, Pt18, p.P0, p.nozzle_cv, gas)
    n8 = nozzle(Tt8, Pt8, p.P0, p.nozzle_cv, gas, f45)
    F_byp = W_byp * n18.F_per_W
    F_core = W8 * n8.F_per_W
    thrust = F_byp + F_core  # no ram drag at M0 = 0

    # (Tt, Pt, W, FAR)
    stations = {
        "0": (Tt0, Pt0, W2, 0.0), "2": (Tt2, Pt2, W2, 0.0), "13": (Tt13, Pt13, W_byp, 0.0),
        "18": (Tt18, Pt18, W_byp, 0.0), "24": (Tt24, Pt24, W_core, 0.0), "25": (Tt25, Pt25, W_core, 0.0),
        "3": (Tt3, Pt3, W_core, 0.0), "31": (Tt3, Pt3, W_comb, 0.0), "4": (T4, Pt4, W4, f),
        "41": (T41, Pt41, W41, f41), "44": (Tt44, Pt44, W41, f41), "45": (Tt45, Pt45, W45, f45),
        "5": (Tt5, Pt5, W8, f45), "8": (Tt8, Pt8, W8, f45),
    }
    return {
        "stations": stations,
        "W2": W2, "T4": T4, "T41": T41, "Tt44": Tt44, "FPR": p.FPR,
        "W_core": W_core, "W_byp": W_byp, "W_sec": W_sec, "W_ngv": W_ngv, "W_rotor": W_rotor, "W_leak": W_leak,
        "W_comb": W_comb, "W8": W8, "f": f, "W_fuel": W_fuel,
        "hpc_pr": hpc_pr, "hpt_pr": hpt_pr, "lpt_pr": lpt_pr,
        "P_fan": P_fan, "P_boost": P_boost, "P_hpc": P_hpc, "P_hpt": P_hpt, "P_lpt": P_lpt,
        "n18": n18, "n8": n8, "F_byp": F_byp, "F_core": F_core, "thrust": thrust,
        "eta_fan_is": compressor_isentropic_eff(Tt2, p.FPR, p.e_fan, gas),
        "eta_lpt_is": turbine_isentropic_eff(Tt45, lpt_pr, p.e_lpt, gas, f45),
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
    raise KeyError(name)


def calibrate(p: Params, t: Targets, initial: dict, tol: float = 1e-9, max_iter: int = 50):
    """Newton iteration for W2, T4 against thrust and fuel flow. Returns (result dict, iterations)."""
    state = {k: initial[k] for k in UNKNOWNS}

    def evaluate(s):
        r = run(p, s["W2"], s["T4"])
        return r, [_residual(name, r, t) for name in TARGETS]

    for it in range(max_iter + 1):
        r, res = evaluate(state)
        if max(abs(v) for v in res) < tol:
            return r, it
        J = [[0.0] * len(UNKNOWNS) for _ in TARGETS]
        for j, name in enumerate(UNKNOWNS):
            h = 1e-6 * abs(state[name])
            _, res_p = evaluate(dict(state, **{name: state[name] + h}))
            for i in range(len(TARGETS)):
                J[i][j] = (res_p[i] - res[i]) / h
        dx = _solve(J, [-v for v in res])
        # damping: at most 30 % change per variable
        scale = min([1.0] + [0.3 * abs(state[n]) / abs(d) for n, d in zip(UNKNOWNS, dx) if d])
        # backtrack if the step leaves the physical domain (e.g. nozzle Pt < P0)
        for _ in range(20):
            trial = {n: state[n] + scale * d for n, d in zip(UNKNOWNS, dx)}
            try:
                evaluate(trial)
                break
            except ValueError:
                scale *= 0.5
        else:
            raise ArithmeticError("calibration step left the physical domain")
        state = trial
    raise ArithmeticError(f"calibration did not converge in {max_iter} iterations; residuals {res}")


# --- feasibility --------------------------------------------------------------------

def T4_for_fuel(p: Params, W2: float, fuel: float, T4: float = 1600.0, tol: float = 1e-10) -> tuple[float, dict]:
    """Newton on T4 so that the fuel flow matches at fixed W2. Returns (T4, result dict)."""
    for _ in range(50):
        r = run(p, W2, T4)
        res = r["W_fuel"] / fuel - 1.0
        if abs(res) < tol:
            return T4, r
        slope = (run(p, W2, T4 + 0.1)["W_fuel"] / fuel - 1.0 - res) / 0.1
        T4 -= res / slope
    raise ArithmeticError(f"no T4 matches fuel {fuel} kg/s at W2 = {W2} kg/s")


def thrust_envelope(p: Params, t: Targets, W2_min: float = 300.0, W2_max: float = 500.0,
                    step: float = 5.0) -> list[dict]:
    """Thrust at the target fuel flow over a W2 grid; points outside the physical domain are skipped."""
    out, T4 = [], 1700.0
    for i in range(int(round((W2_max - W2_min) / step)) + 1):
        W2 = W2_min + i * step
        try:
            T4, r = T4_for_fuel(p, W2, t.fuel, T4)
        except (ValueError, ArithmeticError):
            continue
        out.append({"W2_kg_s": _r(W2, 5), "T4_K": _r(T4, 5), "thrust_kN": _r(r["thrust"] / 1000.0, 5)})
    return out


def infeasible_results(p: Params, t: Targets, error: str) -> dict:
    envelope = thrust_envelope(p, t)
    best = max(envelope, key=lambda e: e["thrust_kN"])
    return {
        "model": MODEL,
        "status": "infeasible",
        "reason": "no W2, T4 matches thrust and fuel flow with the current inputs",
        "solver_message": error,
        "max_reachable_thrust": {"value": best["thrust_kN"], "unit": "kN", "tag": "H",
                                 "at_W2_kg_s": best["W2_kg_s"], "at_T4_K": best["T4_K"]},
        "target_thrust": _q(t.thrust / 1000.0, "kN", "K"),
        "target_fuel": _q(t.fuel, "kg/s", "K"),
        "envelope": {"description": "fuel flow matched by T4 at each W2; thrust is the free output",
                     "points": envelope},
    }


# --- derived quantities -----------------------------------------------------------

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


def egt_model_K(r: dict, raw: dict) -> float:
    return egt_estimate(raw, r["stations"]["45"][0], r["stations"]["5"][0])


def egt_displayed_C(r: dict, raw: dict, refs: dict) -> float:
    return egt_model_K(r, raw) - 273.15 + refs["egt_shunt_K"]


# --- validation -------------------------------------------------------------------

def validation_case(p: Params, refs: dict) -> tuple[Params, Targets]:
    """Girão 2023 design point: same component inputs, its thrust, fuel, BPR and OPR."""
    c = refs["girao"]["validation_case"]["inputs"]
    return (replace(p, bpr=_value(c["bpr"]), opr=_value(c["opr"])),
            Targets(thrust=_value(c["thrust"]) * 1000.0, fuel=_value(c["fuel"])))


def validation_rows(r: dict, raw: dict, refs: dict) -> list[dict]:
    """Model vs Girão per item: deviation and pass/fail against the kind's tolerance."""
    case = refs["girao"]["validation_case"]
    st = r["stations"]
    model = {
        "W2": r["W2"], "T3": st["3"][0], "P3": st["3"][1] / 1000.0, "T4": r["T4"], "T41": r["T41"],
        "T45": st["45"][0], "T5": st["5"][0], "P5": st["5"][1] / 1000.0, "EGT": egt_model_K(r, raw),
    }
    rows = []
    for name, ref in case["references"].items():
        dev = model[name] / ref["value"] - 1.0
        tol = case["tolerances"][ref["kind"]]["value"]
        rows.append({"item": name, "model": _r(model[name], 5), "girao": ref["value"], "unit": ref["unit"],
                     "deviation_pct": _r(100.0 * dev, 3), "tolerance_pct": _r(100.0 * tol, 3),
                     "result": "pass" if abs(dev) <= tol else "fail"})
    return rows


# --- sensitivity --------------------------------------------------------------------

def sensitivity(p: Params, t: Targets, base: dict, raw: dict, tol: float) -> list[dict]:
    """Recalibrate W2, T4 after each e_poly step; report deltas of W2, T4 and EGT."""
    step0 = raw["sensitivity"]["e_poly_step"]
    start = {k: base[k] for k in UNKNOWNS}
    egt0 = egt_model_K(base, raw)
    rows = []
    for name in E_POLY:
        for sign in (+1, -1):
            step = sign * step0
            r, _ = calibrate(replace(p, **{name: getattr(p, name) + step}), t, start, tol=tol)
            rows.append({
                "case": f"{name} {step:+.2f}",
                "dW2_kg_s": _r(round(r["W2"] - base["W2"], 6), 4),
                "dT4_K": _r(round(r["T4"] - base["T4"], 6), 4),
                "dEGT_K": _r(round(egt_model_K(r, raw) - egt0, 6), 4),
            })
    return rows


# --- outputs ------------------------------------------------------------------------

def build_checks(r: dict, p: Params, raw: dict, refs: dict) -> list[dict]:
    cfg = raw["checks"]
    girao = refs["girao"]
    sfc = r["W_fuel"] / r["thrust"] * 1e6
    A_fan = fan_face_area(raw)
    w2a = r["W2"] / A_fan
    choke = choke_mass_flux(p.T0, p.P0, p.gas)
    w2_ref = cfg["w2_ref"]
    lo, hi = cfg["w2a_range"]["min"], cfg["w2a_range"]["max"]
    c_lo, c_hi = cfg["cooling_range"]["min"], cfg["cooling_range"]["max"]
    egt_disp = egt_displayed_C(r, raw, refs)
    egt_model_C = egt_model_K(r, raw) - 273.15
    egt_girao_C = girao["validation_case"]["references"]["EGT"]["value"] - 273.15
    air_refs = {k: _value(v) for k, v in cfg["combustor_air_refs"].items()}
    vr_ideal = _value(girao["info_refs"]["velocity_ratio_ideal_takeoff"])
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
        {"name": "Total secondary air fraction", "value": _r(p.secondary_fraction, 4), "reference": [c_lo, c_hi],
         "unit": "- of W25", "criterion": f"{c_lo:g} <= c <= {c_hi:g} (input, Girão 2023)",
         "result": verdict(c_lo <= p.secondary_fraction <= c_hi)},
        {"name": "SFC vs ICAO/TCDS", "value": _r(sfc), "reference": refs["sfc_ref"], "unit": "g/(kN s)",
         "criterion": f"within {cfg['sfc_tolerance']['value']:.1%}",
         "result": verdict(abs(sfc / refs["sfc_ref"] - 1.0) <= cfg["sfc_tolerance"]["value"])},
        {"name": "EGT displayed vs TCDS limit", "value": _r(egt_disp, 4), "reference": refs["egt_limit_displayed_C"],
         "unit": "degC", "margin": _r(refs["egt_limit_displayed_C"] - egt_disp, 4),
         "criterion": f"model + {refs['egt_shunt_K']:g} K shunt < {refs['egt_limit_displayed_C']:g}",
         "result": verdict(egt_disp < refs["egt_limit_displayed_C"])},
        {"name": "EGT model vs Girão", "value": _r(egt_model_C, 4), "reference": _r(egt_girao_C, 4), "unit": "degC",
         "criterion": "info only (Girão at 125.73 kN, formula value without shunt)", "result": "info"},
        {"name": "Combustor air W31 vs references", "value": _r(r["W_comb"], 4), "reference": air_refs,
         "unit": "kg/s", "deviation": {k: _r(r["W_comb"] / v - 1.0, 3) for k, v in air_refs.items()},
         "criterion": "info only (Lopez-Pintor modeled, ADR-007; Girão at 125.73 kN)", "result": "info"},
        {"name": "V18/V8", "value": _r(r["velocity_ratio"], 4),
         "reference": {"girao_ideal_takeoff": vr_ideal,
                       "eta_fan_is_x_eta_lpt_is": _r(r["eta_fan_is"] * r["eta_lpt_is"], 4)},
         "unit": "-", "criterion": "info only (ADR-008)", "result": "info"},
        {"name": "T4 vs references", "value": _r(r["T4"], 5), "reference": T4_refs, "unit": "K",
         "deviation": {k: _r(r["T4"] / v - 1.0, 3) for k, v in T4_refs.items()},
         "criterion": "info only", "result": "info"},
        {"name": "T3 vs test cell", "value": _r(T3, 5), "reference": T3_ref, "unit": "K",
         "deviation": _r(T3 / T3_ref - 1.0, 3), "criterion": "info only (test cell T0 298 K, not ISA)",
         "result": "info"},
    ]


MODEL = ("M0 cycle v4, two-spool separate-flow, CFM56-7B inputs (Girão 2023), secondary air from HPC exit, "
         "variable cp(T, FAR) NASA 7-coefficient polynomials (ADR-006, ADR-007, ADR-008)")


def build_results(r: dict, p: Params, t: Targets, raw: dict, refs: dict, iterations: int,
                  sens: list[dict] | None = None) -> dict:
    sfc = r["W_fuel"] / r["thrust"] * 1e6  # g/(kN s)
    A_fan = fan_face_area(raw)
    egt_K = egt_model_K(r, raw)
    checks = build_checks(r, p, raw, refs)
    results = {
        "model": MODEL,
        "gas_model": raw["gas"]["model"],
        "design_point": {"condition": "SLS ISA, max take-off", "icao_uid": refs["icao_uid"],
                         "T0": _q(p.T0, "K", "G"), "P0": _q(p.P0, "Pa", "G")},
        "calibration": {
            "iterations": iterations,
            "unknowns": list(UNKNOWNS),
            "targets": {"thrust": _q(t.thrust / 1000.0, "kN", "K"), "fuel_flow": _q(t.fuel, "kg/s", "K")},
            "inputs": {"FPR": _q(p.FPR, "-", "KS"),
                       "secondary_air_fraction": _q(p.secondary_fraction, "- of W25", "KS")},
            "W2": _q(r["W2"], "kg/s"), "T4": _q(r["T4"], "K"),
        },
        "stations": [
            {"station": s, "Tt_K": _r(v[0], 5), "Pt_kPa": _r(v[1] / 1000.0, 5), "W_kg_s": _r(v[2], 5),
             "FAR": _r(v[3], 5)}
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
            "fpr": _q(p.FPR, "-", "KS"),
            "core_pr_25_2": _q(p.core_pr_25_2, "-", "KS"),
            "hpc_pr": _q(r["hpc_pr"], "-"),
            "hpt_pr": _q(r["hpt_pr"], "-"),
            "lpt_pr": _q(r["lpt_pr"], "-"),
            "T4": _q(r["T4"], "K"),
            "T41": _q(r["T41"], "K"),
            "W_core": _q(r["W_core"], "kg/s"),
            "W_bypass": _q(r["W_byp"], "kg/s"),
            "W_combustor": _q(r["W_comb"], "kg/s"),
            "W_secondary": _q(r["W_sec"], "kg/s"),
            "W_cooling_ngv": _q(r["W_ngv"], "kg/s"),
            "W_cooling_hpt_rotor": _q(r["W_rotor"], "kg/s"),
            "W_leak": _q(r["W_leak"], "kg/s"),
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
                "choke_mass_flux": _q(choke_mass_flux(p.T0, p.P0, p.gas), "kg/(s m2)")},
        "egt": {"model_K": _q(egt_K, "K", "T"), "model_C": _q(egt_K - 273.15, "degC", "T"),
                "displayed_C": _q(egt_K - 273.15 + refs["egt_shunt_K"], "degC", "T"),
                "note": "a = 0.976 (Girão Fig. 4.10; text gives 0.9664); displayed = model + SAC shunt"},
        "checks": checks,
        "hard_checks_passed": all(c["result"] == "pass" for c in checks if c.get("hard")),
    }
    if sens is not None:
        results["sensitivity"] = {"method": "W2, T4 recalibrated per e_poly step", "cases": sens}
    return results


def main(argv: list[str]) -> int:
    p, t, initial, raw, refs = load_inputs()
    tol = _value(raw["calibration"]["tolerance"])
    if "--validate" in argv:
        pv, tv = validation_case(p, refs)
        r, _ = calibrate(pv, tv, initial, tol=tol)
        for row in validation_rows(r, raw, refs):
            print(f"  [{row['result']:>4}] {row['item']:<4} model {row['model']:>9} girao {row['girao']:>9} "
                  f"{row['unit']:<5} dev {row['deviation_pct']:>7} % (tol {row['tolerance_pct']} %)")
        return 0
    try:
        r, iterations = calibrate(p, t, initial, tol=tol)
    except ArithmeticError as exc:
        results = infeasible_results(p, t, str(exc))
        write_yaml(RESULTS_FILE, results)
        m = results["max_reachable_thrust"]
        print(f"INFEASIBLE: max thrust {m['value']} kN at W2 {m['at_W2_kg_s']} kg/s, T4 {m['at_T4_K']} K "
              f"(target {results['target_thrust']['value']} kN at {t.fuel} kg/s fuel)")
        return 1
    sens = sensitivity(p, t, r, raw, tol)
    results = build_results(r, p, t, raw, refs, iterations, sens)
    write_yaml(RESULTS_FILE, results)
    print(f"W2={r['W2']:.2f} kg/s  T4={r['T4']:.1f} K  T41={r['T41']:.1f} K  FPR={p.FPR:.4f}  ({iterations} it)")
    for c in results["checks"]:
        print(f"  [{c['result']:>4}] {c['name']}: {c['value']} (ref {c['reference']})")
    for s in sens:
        print(f"  {s['case']:<24} dW2={s['dW2_kg_s']:>8} dT4={s['dT4_K']:>8} dEGT={s['dEGT_K']:>8}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
