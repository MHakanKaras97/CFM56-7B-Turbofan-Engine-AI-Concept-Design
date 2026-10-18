"""M0 cycle v4: two-spool separate-flow turbofan, CFM56-7B-specific inputs (Girão 2023), SLS ISA, max take-off.

Stations (SAE AS755 / GasTurb): 0 ambient, 2 fan face, 13 outer fan exit, 18 bypass nozzle (after
the P16/P13 duct), 21 inner fan exit, 24 booster exit, 25 HPC inlet (after the P25/P24 duct),
3 HPC exit, 31 combustor inlet (after secondary air bleed), 4 combustor exit, 41 HPT rotor inlet
(after NGV cooling mixes in), 43 HPT exit, 44 after HPT rotor cooling mixes in, 45 LPT inlet
(after leakage returns, P45/P44 duct), 5 LPT exit, 8 core nozzle (after the P6/P5 duct).

Gas properties: variable cp(T, FAR) from NASA polynomials (tools.thermo.NasaGas); a constant-cp
gas can be switched in for closed-form checks. Station FAR is carried through mixing.
Component efficiencies are isentropic (GasTurb inputs, Girão Fig. 4.9).

Secondary air, fractions of W25, bypasses the combustor: NGV cooling (HPC exit) mixes before
the HPT rotor and does HPT work; HPT rotor cooling (HPC exit) mixes at station 44; leakage
leaves the HPC at a fraction of its enthalpy rise and returns at station 45.

FPR is an input (ADR-008). Calibration (Newton, finite-difference Jacobian) solves W2 and T4
against thrust and fuel flow; optionally a third unknown (delta_eta or FPR) against the ideal
V18/V8 (fully expanded isentropic jet velocities).

Rated case (ICAO -7B27, ADR-009): similarity condition. The ideal V18/V8 of the Girão validation
point is imposed as a third target; the third unknown is a uniform delta_eta added to all
isentropic turbomachinery efficiencies, or (fallback) FPR with delta_eta = 0.

Usage:
    python -m engine.M0_engine.analysis.cycle              # writes analysis/results.yaml
    python -m engine.M0_engine.analysis.cycle --validate   # Girão validation case, prints only
    python -m engine.M0_engine.analysis.cycle --band       # delta_eta uncertainty band, prints only
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
    compressor_is,
    mix,
    nozzle,
    turbine_is_for_work,
)

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PARAMS_FILE = HERE / "cycle_params.yaml"
RESULTS_FILE = HERE / "results.yaml"
INCH = 0.0254
STATIONS = ("0", "2", "13", "18", "21", "24", "25", "3", "31", "4", "41", "43", "44", "45", "5", "8")
UNKNOWNS = ("W2", "T4")
TARGETS = ("thrust", "fuel")
SIMILARITY_TARGETS = (*TARGETS, "velocity_ratio")
STEP_FLOOR = {"W2": 1.0, "T4": 100.0, "delta_eta": 0.05, "FPR": 1.0}  # damping scale near zero
ETA = ("eta_fan_outer", "eta_fan_inner", "eta_booster", "eta_hpc", "eta_hpt", "eta_lpt")
ETA_GROUPS = {"compressors": ETA[:4], "turbines": ETA[4:], "uniform": ETA}
COMPONENTS = ("inlet_recovery", "FPR", *ETA, "pr_fan_inner", "pr_booster", "duct_25_24", "burner_eta",
              "burner_pr", "duct_45_44", "duct_6_5", "bypass_duct", "mech_eff", "cfg_18", "cfg_8", "cd_18",
              "cd_8", "LHV")
SECONDARY = ("ngv", "hpt_rotor", "leak", "leak_bleed_point", "customer_bleed", "hp_power_offtake")


@dataclass(frozen=True)
class Params:
    T0: float
    P0: float
    opr: float          # P3/P2
    bpr: float
    gas: object         # tools.thermo gas model (NasaGas or ConstantCp)
    inlet_recovery: float
    FPR: float           # outer fan P13/P2
    eta_fan_outer: float  # isentropic efficiencies
    eta_fan_inner: float
    eta_booster: float
    eta_hpc: float
    eta_hpt: float
    eta_lpt: float
    pr_fan_inner: float  # P21/P2
    pr_booster: float    # P24/P21
    duct_25_24: float
    burner_eta: float
    burner_pr: float     # P4/P3
    duct_45_44: float
    duct_6_5: float
    bypass_duct: float   # P16/P13
    mech_eff: float
    cfg_18: float        # nozzle thrust coefficients
    cfg_8: float
    cd_18: float         # nozzle discharge coefficients (area only)
    cd_8: float
    LHV: float
    ngv: float = 0.0        # secondary air, fractions of W25
    hpt_rotor: float = 0.0
    leak: float = 0.0
    leak_bleed_point: float = 0.5  # fraction of the HPC enthalpy rise where the leakage leaves
    customer_bleed: float = 0.0     # kg/s
    hp_power_offtake: float = 0.0   # W
    include_fuel_mass: bool = True  # False only for the ideal closed-form comparison

    @property
    def secondary_fraction(self) -> float:
        return self.ngv + self.hpt_rotor + self.leak

    @property
    def core_pr_25_2(self) -> float:
        return self.pr_fan_inner * self.pr_booster * self.duct_25_24


@dataclass(frozen=True)
class Targets:
    thrust: float  # N
    fuel: float    # kg/s
    velocity_ratio: float | None = None  # ideal V18/V8, similarity condition


# --- inputs ---------------------------------------------------------------------

def _value(q: dict) -> float:
    return float(q["value"])


def _dig(data: dict, dotted: str):
    for key in dotted.split("."):
        data = data[key]
    return data


def load_inputs(params_file: Path = PARAMS_FILE, root: Path = ROOT, raw: dict | None = None):
    """Return (Params, Targets, initial guess dict, raw params yaml, reference values).

    `raw` replaces the params file content (used to evaluate a params change before writing it).
    """
    raw = read_yaml(params_file) if raw is None else raw
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
        **{k: _value(sec[k]) for k in SECONDARY},
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

    Tt13, Pt13, w_fan = compressor_is(Tt2, Pt2, p.FPR, p.eta_fan_outer, gas)
    Tt18, Pt18 = Tt13, Pt13 * p.bypass_duct

    Tt21, Pt21, w_inner = compressor_is(Tt2, Pt2, p.pr_fan_inner, p.eta_fan_inner, gas)
    Tt24, Pt24, w_boost = compressor_is(Tt21, Pt21, p.pr_booster, p.eta_booster, gas)
    Tt25, Pt25 = Tt24, Pt24 * p.duct_25_24
    hpc_pr = p.opr / p.core_pr_25_2
    Tt3, Pt3, w_hpc = compressor_is(Tt25, Pt25, hpc_pr, p.eta_hpc, gas)

    # leakage leaves the HPC part-way: it absorbs only that part of the HPC work
    W_leak = p.leak * W_core
    h_leak = gas.h(Tt25) + p.leak_bleed_point * w_hpc
    T_leak = gas.T_from_h(h_leak)
    W3 = W_core - W_leak
    W_ngv = p.ngv * W_core
    W_rotor = p.hpt_rotor * W_core
    W_sec = W_ngv + W_rotor + W_leak
    W_comb = W3 - W_ngv - W_rotor - p.customer_bleed

    f = burner(Tt3, T4, p.burner_eta, p.LHV, gas)
    W_fuel = f * W_comb
    W4 = W_comb + W_fuel if p.include_fuel_mass else W_comb
    Pt4 = Pt3 * p.burner_pr

    W41, T41, f41 = mix(W4, T4, f, W_ngv, Tt3, 0.0, gas)
    Pt41 = Pt4

    P_fan = W_byp * w_fan
    P_boost = W_core * (w_inner + w_boost)  # inner fan + booster, core side
    P_hpc = W3 * w_hpc + W_leak * p.leak_bleed_point * w_hpc
    P_hpt = (P_hpc + p.hp_power_offtake) / p.mech_eff
    P_lpt = (P_fan + P_boost) / p.mech_eff
    Tt43, Pt43, hpt_pr = turbine_is_for_work(T41, Pt41, P_hpt / W41, p.eta_hpt, gas, f41)
    W44, Tt44, f44 = mix(W41, Tt43, f41, W_rotor, Tt3, 0.0, gas)
    Pt44 = Pt43
    W45, Tt45, f45 = mix(W44, Tt44, f44, W_leak, T_leak, 0.0, gas)
    Pt45 = Pt44 * p.duct_45_44
    Tt5, Pt5, lpt_pr = turbine_is_for_work(Tt45, Pt45, P_lpt / W45, p.eta_lpt, gas, f45)
    Tt8, Pt8, W8 = Tt5, Pt5 * p.duct_6_5, W45

    n18 = nozzle(Tt18, Pt18, p.P0, gas, cfg=p.cfg_18, cd=p.cd_18)
    n8 = nozzle(Tt8, Pt8, p.P0, gas, f45, cfg=p.cfg_8, cd=p.cd_8)
    F_byp = W_byp * n18.F_per_W
    F_core = W8 * n8.F_per_W
    thrust = F_byp + F_core  # no ram drag at M0 = 0

    # (Tt, Pt, W, FAR)
    stations = {
        "0": (Tt0, Pt0, W2, 0.0), "2": (Tt2, Pt2, W2, 0.0), "13": (Tt13, Pt13, W_byp, 0.0),
        "18": (Tt18, Pt18, W_byp, 0.0), "21": (Tt21, Pt21, W_core, 0.0), "24": (Tt24, Pt24, W_core, 0.0),
        "25": (Tt25, Pt25, W_core, 0.0), "3": (Tt3, Pt3, W3, 0.0), "31": (Tt3, Pt3, W_comb, 0.0),
        "4": (T4, Pt4, W4, f), "41": (T41, Pt41, W41, f41), "43": (Tt43, Pt43, W41, f41),
        "44": (Tt44, Pt44, W44, f44), "45": (Tt45, Pt45, W45, f45), "5": (Tt5, Pt5, W8, f45),
        "8": (Tt8, Pt8, W8, f45),
    }
    return {
        "stations": stations,
        "W2": W2, "T4": T4, "T41": T41, "Tt43": Tt43, "FPR": p.FPR,
        "W_core": W_core, "W_byp": W_byp, "W3": W3, "W_sec": W_sec, "W_ngv": W_ngv, "W_rotor": W_rotor,
        "W_leak": W_leak, "T_leak": T_leak, "W_comb": W_comb, "W8": W8, "f": f, "W_fuel": W_fuel,
        "hpc_pr": hpc_pr, "hpt_pr": hpt_pr, "lpt_pr": lpt_pr,
        "P_fan": P_fan, "P_boost": P_boost, "P_hpc": P_hpc, "P_hpt": P_hpt, "P_lpt": P_lpt,
        "n18": n18, "n8": n8, "F_byp": F_byp, "F_core": F_core, "thrust": thrust,
        "velocity_ratio": n18.V / n8.V,
        "velocity_ratio_ideal": n18.V_ideal / n8.V_ideal,
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
        return r["velocity_ratio_ideal"] / t.velocity_ratio - 1.0
    raise KeyError(name)


def _apply(p: Params, s: dict, eta_group: tuple[str, ...] = ETA) -> Params:
    """Params with the optional third unknown (delta_eta on eta_group, or FPR) applied."""
    if "delta_eta" in s:
        p = with_delta_eta(p, s["delta_eta"], eta_group)
    if "FPR" in s:
        p = replace(p, FPR=s["FPR"])
    return p


def calibrate(p: Params, t: Targets, initial: dict, tol: float = 1e-9, max_iter: int = 50,
              unknowns: tuple[str, ...] = UNKNOWNS, targets: tuple[str, ...] = TARGETS,
              eta_group: tuple[str, ...] = ETA):
    """Newton iteration; default W2, T4 against thrust and fuel flow.

    A third unknown (delta_eta on eta_group, or FPR) is applied to p before each evaluation.
    Returns (result dict, iterations); the result holds the applied Params under "params".
    """
    if len(unknowns) != len(targets):
        raise ValueError("number of unknowns must equal number of targets")
    state = {k: initial[k] for k in unknowns}

    def evaluate(s):
        pp = _apply(p, s, eta_group)
        r = run(pp, s["W2"], s["T4"])
        r["params"] = pp
        return r, [_residual(name, r, t) for name in targets]

    for it in range(max_iter + 1):
        r, res = evaluate(state)
        if max(abs(v) for v in res) < tol:
            return r, it
        J = [[0.0] * len(unknowns) for _ in targets]
        for j, name in enumerate(unknowns):
            h = 1e-6 * max(abs(state[name]), STEP_FLOOR[name] * 1e-2)
            _, res_p = evaluate(dict(state, **{name: state[name] + h}))
            for i in range(len(targets)):
                J[i][j] = (res_p[i] - res[i]) / h
        dx = _solve(J, [-v for v in res])
        # damping: at most 30 % change per variable (relative to a floor near zero)
        scale = min([1.0] + [0.3 * max(abs(state[n]), STEP_FLOOR[n]) / abs(d) for n, d in zip(unknowns, dx) if d])
        # backtrack if the step leaves the physical domain (e.g. nozzle Pt < P0)
        for _ in range(20):
            trial = {n: state[n] + scale * d for n, d in zip(unknowns, dx)}
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


def infeasible_results(p: Params, t: Targets, error: str, sweep: list[dict] | None = None) -> dict:
    envelope = thrust_envelope(p, t)
    best = max(envelope, key=lambda e: e["thrust_kN"])
    return {
        **({"delta_eta_sweep": sweep} if sweep is not None else {}),
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
    """Model vs Girão per item, in gas-path order: deviation and pass/fail against the kind's tolerance."""
    case = refs["girao"]["validation_case"]
    st = r["stations"]

    def T(s):
        return st[s][0]

    def P(s):
        return st[s][1] / 1000.0

    model = {
        "W2": r["W2"], "T13": T("13"), "P13": P("13"), "T21": T("21"), "T25": T("25"), "P25": P("25"),
        "T3": T("3"), "P3": P("3"), "W3": r["W3"], "W31": r["W_comb"], "T4": r["T4"], "T41": r["T41"],
        "T43": T("43"), "P44": P("44"), "T44": T("44"), "T45": T("45"), "T5": T("5"), "P5": P("5"),
        "EGT": egt_model_K(r, raw),
    }
    rows = []
    for name, ref in case["references"].items():
        if name not in model:
            continue
        dev = model[name] / ref["value"] - 1.0
        tol = case["tolerances"][ref["kind"]]["value"]
        rows.append({"item": name, "model": _r(model[name], 5), "girao": ref["value"], "unit": ref["unit"],
                     "deviation_pct": _r(100.0 * dev, 3), "tolerance_pct": _r(100.0 * tol, 3),
                     "result": "pass" if abs(dev) <= tol else "fail"})
    return rows


# --- sensitivity --------------------------------------------------------------------

def first_deviation(rows: list[dict], limit: float = 1.0) -> dict | None:
    """First validation item in gas-path order whose |deviation| exceeds `limit` percent."""
    return next((row for row in rows if abs(row["deviation_pct"]) > limit), None)


def sensitivity(p: Params, t: Targets, base: dict, raw: dict, tol: float) -> list[dict]:
    """Recalibrate W2, T4 after each efficiency step and each relative LHV step;
    report deltas of W2, T4 and EGT."""
    cfg = raw["sensitivity"]
    start = {k: base[k] for k in UNKNOWNS}
    egt0 = egt_model_K(base, raw)
    cases = [(f"{n} {s * cfg['eta_step']:+.2f}", {n: getattr(p, n) + s * cfg["eta_step"]})
             for n in ETA for s in (+1, -1)]
    cases += [(f"LHV {s * cfg['LHV_rel_step']:+.1%}", {"LHV": p.LHV * (1 + s * cfg["LHV_rel_step"])})
              for s in (+1, -1)]
    rows = []
    for label, change in cases:
        r, _ = calibrate(replace(p, **change), t, start, tol=tol)
        rows.append({
            "case": label,
            "dW2_kg_s": _r(round(r["W2"] - base["W2"], 6), 4),
            "dT4_K": _r(round(r["T4"] - base["T4"], 6), 4),
            "dEGT_K": _r(round(egt_model_K(r, raw) - egt0, 6), 4),
        })
    return rows


# --- rated case ---------------------------------------------------------------------

def with_delta_eta(p: Params, delta_eta: float, names: tuple[str, ...] = ETA) -> Params:
    """Add delta_eta to the named isentropic turbomachinery efficiencies (default: all)."""
    return replace(p, **{n: getattr(p, n) + delta_eta for n in names})


def delta_eta_group(raw: dict) -> tuple[str, ...]:
    """Efficiencies shifted by delta_eta: all except those fixed by accepted module values."""
    excluded = set(raw["rated_case"].get("delta_eta_exclude", []))
    return tuple(n for n in ETA if n not in excluded)


def uncertainty_band(p: Params, t: Targets, initial: dict, raw: dict, tol: float) -> list[dict]:
    """Similarity solve (thrust, fuel, ideal V18/V8) with delta_eta on each efficiency group (info only)."""
    rows = []
    for group, names in ETA_GROUPS.items():
        try:
            r, _ = calibrate(p, t, dict(initial, delta_eta=0.0), tol=tol, unknowns=(*UNKNOWNS, "delta_eta"),
                             targets=SIMILARITY_TARGETS, eta_group=names)
        except ArithmeticError as exc:
            rows.append({"group": group, "solvable": False, "message": str(exc)})
            continue
        rows.append({"group": group, "solvable": True,
                     "delta_eta": _r(getattr(r["params"], names[0]) - getattr(p, names[0]), 4),
                     "W2_kg_s": _r(r["W2"], 5), "T4_K": _r(r["T4"], 5), "T41_K": _r(r["T41"], 5),
                     "EGT_model_C": _r(egt_model_K(r, raw) - 273.15, 4)})
    return rows


def delta_eta_sweep(p: Params, t: Targets, initial: dict, raw: dict, refs: dict, tol: float) -> list[dict]:
    """Calibrate W2, T4 (thrust, fuel only) at each delta_eta of the configured sweep; info table."""
    cfg = raw["rated_case"]["delta_eta_sweep"]
    n = int(round((cfg["max"] - cfg["min"]) / cfg["step"]))
    A_fan = fan_face_area(raw)
    guess = {k: initial[k] for k in UNKNOWNS}
    rows = []
    for i in range(n + 1):
        d = round(cfg["min"] + i * cfg["step"], 10)
        pd = with_delta_eta(p, d)
        try:
            r, _ = calibrate(pd, t, guess, tol=tol)
        except ArithmeticError:
            best = max(thrust_envelope(pd, t), key=lambda e: e["thrust_kN"])
            rows.append({"delta_eta": d, "solvable": False, "max_thrust_kN": best["thrust_kN"]})
            continue
        guess = {k: r[k] for k in UNKNOWNS}
        hard = all(c["result"] == "pass" for c in build_checks(r, pd, raw, refs) if c.get("hard"))
        rows.append({
            "delta_eta": d, "solvable": True, "hard_checks_passed": hard,
            "W2_kg_s": _r(r["W2"], 5), "W2_per_A": _r(r["W2"] / A_fan, 4),
            "T4_K": _r(r["T4"], 5), "T41_K": _r(r["T41"], 5),
            "EGT_model_C": _r(egt_model_K(r, raw) - 273.15, 4),
            "EGT_displayed_C": _r(egt_displayed_C(r, raw, refs), 4),
            "combustor_air_kg_s": _r(r["W_comb"], 4),
            "sfc_g_kNs": _r(r["W_fuel"] / r["thrust"] * 1e6, 5),
            "V18_V8_ideal": _r(r["velocity_ratio_ideal"], 4),
        })
    return rows


def validation_velocity_ratio(p: Params, refs: dict, initial: dict, tol: float) -> float:
    """Ideal V18/V8 of our own model at the Girão validation point (similarity target)."""
    pv, tv = validation_case(p, refs)
    r, _ = calibrate(pv, tv, initial, tol=tol)
    return r["velocity_ratio_ideal"]


def similarity_solve(p: Params, t: Targets, initial: dict, raw: dict, refs: dict, tol: float):
    """ADR-009: thrust, fuel and ideal V18/V8 as targets.

    Attempt 1: unknowns W2, T4, delta_eta. Accepted if it solves, delta_eta <= limit and HARD passes.
    Attempt 2 (only if 1 is not accepted): delta_eta = 0, unknowns W2, T4, FPR.
    Returns (attempts, chosen result or None, chosen iterations).
    """
    limit = raw["rated_case"]["delta_eta_limit"]["value"]
    group = delta_eta_group(raw)
    tries = [("delta_eta", dict(initial, delta_eta=0.0)), ("FPR", dict(initial, FPR=p.FPR))]
    attempts, chosen, chosen_it = [], None, 0
    for name, guess in tries:
        if chosen is not None:
            break
        entry = {"third_unknown": name}
        try:
            r, it = calibrate(p, t, guess, tol=tol, unknowns=(*UNKNOWNS, name), targets=SIMILARITY_TARGETS,
                              eta_group=group)
        except ArithmeticError as exc:
            attempts.append(dict(entry, solvable=False, message=str(exc)))
            continue
        pp = r["params"]
        hard = all(c["result"] == "pass" for c in build_checks(r, pp, raw, refs) if c.get("hard"))
        value = getattr(pp, group[0]) - getattr(p, group[0]) if name == "delta_eta" else pp.FPR
        ok = hard and (name != "delta_eta" or value <= limit + 1e-12)
        attempts.append(dict(entry, solvable=True, value=_r(value, 5), hard_checks_passed=hard,
                             W2_kg_s=_r(r["W2"], 5), T4_K=_r(r["T4"], 5), accepted=ok,
                             **({} if ok or name != "delta_eta" else
                                {"flag": f"delta_eta > {limit:g}: another assumption is likely wrong"})))
        if ok:
            chosen, chosen_it = r, it
    return attempts, chosen, chosen_it


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
        {"name": "V18/V8 ideal", "value": _r(r["velocity_ratio_ideal"], 4),
         "reference": {"girao_ideal_takeoff": vr_ideal,
                       **({"model_at_girao_point": _r(refs["validation_velocity_ratio"], 4)}
                          if "validation_velocity_ratio" in refs else {})},
         "unit": "-", "criterion": "info only (similarity target, ADR-009)", "result": "info"},
        {"name": "T4 vs references", "value": _r(r["T4"], 5), "reference": T4_refs, "unit": "K",
         "deviation": {k: _r(r["T4"] / v - 1.0, 3) for k, v in T4_refs.items()},
         "criterion": "info only", "result": "info"},
        {"name": "T3 vs test cell", "value": _r(T3, 5), "reference": T3_ref, "unit": "K",
         "deviation": _r(T3 / T3_ref - 1.0, 3), "criterion": "info only (test cell T0 298 K, not ISA)",
         "result": "info"},
    ]


MODEL = ("M0 cycle v4.2, two-spool separate-flow, CFM56-7B inputs (Girão 2023), secondary air from HPC exit, "
         "isentropic component efficiencies, variable cp(T, FAR) NASA 7-coefficient polynomials "
         "(ADR-006, ADR-007, ADR-008)")


def build_results(r: dict, p: Params, t: Targets, raw: dict, refs: dict, iterations: int,
                  sens: list[dict] | None = None, rated: dict | None = None) -> dict:
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
            "pr_fan_inner": _q(p.pr_fan_inner, "-", "KS"),
            "pr_booster": _q(p.pr_booster, "-", "KS"),
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
            "W3": _q(r["W3"], "kg/s"),
            "V18": _q(r["n18"].V, "m/s"), "V8": _q(r["n8"].V, "m/s"),
            "velocity_ratio": _q(r["velocity_ratio"], "-"),
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
    if rated is not None:
        results["rated_case"] = rated
    if sens is not None:
        results["sensitivity"] = {"method": "W2, T4 recalibrated per isentropic-efficiency or LHV step",
                                  "cases": sens}
    return results


def solve_rated(p: Params, t: Targets, initial: dict, raw: dict, refs: dict, tol: float):
    """Rated case with the similarity condition (ADR-009); no files written.

    Returns (results, result dict or None, Params used, iterations, attempts, delta_eta sweep).
    """
    vr = validation_velocity_ratio(p, refs, initial, tol)
    refs["validation_velocity_ratio"] = vr
    t = replace(t, velocity_ratio=vr)
    sweep = delta_eta_sweep(p, t, initial, raw, refs, tol)
    attempts, r, iterations = similarity_solve(p, t, initial, raw, refs, tol)
    if r is None:
        results = infeasible_results(p, t, "no similarity solution with all HARD checks passed", sweep)
        results["similarity_attempts"] = attempts
        return results, None, p, 0, attempts, sweep
    group = delta_eta_group(raw)
    p0, p = p, r["params"]
    delta_eta = getattr(p, group[0]) - getattr(p0, group[0])
    ceiling = max(thrust_envelope(p, t), key=lambda e: e["thrust_kN"])
    rated = {
        "description": "ICAO -7B27 rating with the similarity condition (ADR-009)",
        "similarity_target": {
            "V18_V8_ideal": _q(vr, "-", "T"),
            "basis": "our model's ideal V18/V8 at the Girão validation point (same family, take-off)",
            "girao_reported": _value(refs["girao"]["info_refs"]["velocity_ratio_ideal_takeoff"]),
        },
        "attempts": attempts,
        "delta_eta": _q(delta_eta, "-", "H"),
        **({"delta_eta_excluded": [n for n in ETA if n not in group]} if len(group) < len(ETA) else {}),
        "FPR": _q(p.FPR, "-", "KS" if p.FPR == p0.FPR else "H"),
        "efficiencies_used": {n: _q(getattr(p, n), "-", "H") for n in ETA},
        "thrust_ceiling": {"value": ceiling["thrust_kN"], "unit": "kN", "tag": "H",
                           "at_W2_kg_s": ceiling["W2_kg_s"],
                           "margin": _r(ceiling["thrust_kN"] / (t.thrust / 1000.0) - 1.0, 4),
                           "note": "max thrust at the target fuel flow over W2"},
        "delta_eta_sweep": {"method": "thrust and fuel only, delta_eta fixed per row (info)", "rows": sweep},
        "validation": "Girão 125.73 kN design point, 18 of 19 items pass (analysis/validation_girao.md)",
    }
    sens = sensitivity(p, t, r, raw, tol)
    return build_results(r, p, t, raw, refs, iterations, sens, rated), r, p, iterations, attempts, sweep


def main(argv: list[str]) -> int:
    p, t, initial, raw, refs = load_inputs()
    tol = _value(raw["calibration"]["tolerance"])
    if "--band" in argv:
        vr = validation_velocity_ratio(p, refs, initial, tol)
        for row in uncertainty_band(p, replace(t, velocity_ratio=vr), initial, raw, tol):
            print("  " + "  ".join(f"{k}={v}" for k, v in row.items()))
        return 0
    if "--validate" in argv:
        pv, tv = validation_case(p, refs)
        r, _ = calibrate(pv, tv, initial, tol=tol)
        rows = validation_rows(r, raw, refs)
        for row in rows:
            print(f"  [{row['result']:>4}] {row['item']:<4} model {row['model']:>9} girao {row['girao']:>9} "
                  f"{row['unit']:<5} dev {row['deviation_pct']:>7} % (tol {row['tolerance_pct']} %)")
        first = first_deviation(rows)
        print(f"  first item beyond 1 %: {first['item'] if first else 'none'}")
        for s in sensitivity(pv, tv, r, raw, tol):
            print(f"  {s['case']:<24} dW2={s['dW2_kg_s']:>8} dT4={s['dT4_K']:>8} dEGT={s['dEGT_K']:>8}")
        return 0
    results, r, p, iterations, attempts, sweep = solve_rated(p, t, initial, raw, refs, tol)
    write_yaml(RESULTS_FILE, results)
    for row in sweep + attempts:
        print("  " + "  ".join(f"{k}={v}" for k, v in row.items()))
    if r is None:
        print("INFEASIBLE: no similarity solution")
        return 1
    delta_eta = results["rated_case"]["delta_eta"]["value"]
    sens = results["sensitivity"]["cases"]
    print(f"delta_eta={delta_eta:.5f}  W2={r['W2']:.2f} kg/s  T4={r['T4']:.1f} K  T41={r['T41']:.1f} K  FPR={p.FPR:.4f}  ({iterations} it)")
    for c in results["checks"]:
        print(f"  [{c['result']:>4}] {c['name']}: {c['value']} (ref {c['reference']})")
    for s in sens:
        print(f"  {s['case']:<24} dW2={s['dW2_kg_s']:>8} dT4={s['dT4_K']:>8} dEGT={s['dEGT_K']:>8}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
