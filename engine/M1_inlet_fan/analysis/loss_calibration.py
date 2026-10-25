"""ADR-014 option (a): one multiplier per loss mechanism (profile, shock, endwall, tip), calibrated on Rotor 67.

Model: tools/meanline.py with radial equilibrium and all four loss mechanisms (analysis/rotor67.py run with
losses=True, equilibrium=True). Calibration data [KS] (rotor67_reference.yaml, rotor67_survey.yaml):
- design point PR 1.63 (TP-2879 gives no design efficiency),
- near peak efficiency point: PR 1.642, eta 0.928 and the Table III(b) radial PR profile (survey rows flagged
  'local_efficiency_implausible' or 'unreadable' excluded, as in the A-1 rms).
Residuals are scaled by the A-1 limits (PR 2 % relative, eta 2 points) and minimised by Levenberg-Marquardt
with forward-difference derivatives, from all multipliers = 1. A multiplier is kept above MIN_MULTIPLIER only
so that the loss stays non-negative.
The near stall point (Table III(a): PR 1.728, eta 0.901) is not used; it is the independent acceptance point.
Condition (user, M1 step 4c) [T]: every multiplier within BOUNDS; otherwise the result is NOT applied and is
reported as a model-form problem. `applied` in the output records the outcome; nothing else reads the
multipliers unless applied is true.

Run: python -m engine.M1_inlet_fan.analysis.loss_calibration  (about 10 min; writes analysis/loss_calibration.yaml).
"""

from pathlib import Path

from core.util import read_yaml, write_yaml
from engine.M1_inlet_fan.analysis import rotor67 as R
from tools.meanline import LossMultipliers

M1 = Path(__file__).resolve().parents[1]
OUT = M1 / "analysis" / "loss_calibration.yaml"
NAMES = ("profile", "shock", "endwall", "tip")
BOUNDS = (0.5, 2.0)  # [T] user condition, M1 step 4c
MIN_MULTIPLIER = 0.05
SCALE_PR, SCALE_ETA = R.LIMITS["pr_rel"], R.LIMITS["eta_abs"]
MAX_ITER = 25


def _run(ref: dict, mass_flow: float, k: list[float]) -> dict:
    return R.run(mass_flow, ref, losses=True, equilibrium=True, multipliers=LossMultipliers(*k))


def residuals(k: list[float], ref: dict, survey: dict) -> tuple[list[float], list[str]]:
    design, peak = ref["design"], ref["measured"]["near_peak_efficiency"]
    bad = {f["row"] for f in survey["flags"] if f["check"] in ("local_efficiency_implausible", "unreadable")}
    d = _run(ref, design["mass_flow"]["value"], k)
    p = _run(ref, peak["mass_flow_table_III"]["value"], k)
    res = [(d["Pt_ratio"] / design["pressure_ratio"]["value"] - 1) / SCALE_PR,
           (p["Pt_ratio"] / peak["pressure_ratio"]["value"] - 1) / SCALE_PR,
           (p["efficiency"] - peak["efficiency"]["value"]) / SCALE_ETA]
    names = ["design PR", "near peak PR", "near peak eta"]
    for j, (row, s) in enumerate(zip(survey["station_2"], p["streamlines"]), 1):
        if j not in bad:
            res.append((s["Pt_ratio"] / row["Pt_ratio"] - 1) / SCALE_PR)
            names.append(f"near peak radial PR, streamline {j}")
    return res, names


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    m = [row[:] + [v] for row, v in zip(a, b)]
    for i in range(n):
        piv = max(range(i, n), key=lambda r: abs(m[r][i]))
        m[i], m[piv] = m[piv], m[i]
        for r in range(n):
            if r != i:
                f = m[r][i] / m[i][i]
                m[r] = [x - f * y for x, y in zip(m[r], m[i])]
    return [m[i][n] / m[i][i] for i in range(n)]


def calibrate(ref: dict, survey: dict) -> dict:
    k = [1.0] * 4
    r, names = residuals(k, ref, survey)
    cost0 = cost = sum(x * x for x in r)
    lam, history = 1e-2, []
    for it in range(1, MAX_ITER + 1):
        jac = []
        for i in range(4):
            kk = list(k)
            h = 1e-3 * max(abs(k[i]), 0.1)
            kk[i] += h
            jac.append([(a - b) / h for a, b in zip(residuals(kk, ref, survey)[0], r)])
        jtj = [[sum(jac[i][m] * jac[j][m] for m in range(len(r))) for j in range(4)] for i in range(4)]
        jtr = [sum(jac[i][m] * r[m] for m in range(len(r))) for i in range(4)]
        step = [0.0] * 4
        while lam <= 1e6:
            a = [[jtj[i][j] + (lam * jtj[i][i] if i == j else 0.0) for j in range(4)] for i in range(4)]
            step = _solve(a, [-x for x in jtr])
            cand = [max(MIN_MULTIPLIER, x + s) for x, s in zip(k, step)]
            rc = residuals(cand, ref, survey)[0]
            cc = sum(x * x for x in rc)
            if cc < cost:
                k, r, cost, lam = cand, rc, cc, lam / 3
                break
            lam *= 4
        history.append({"iteration": it, "multipliers": [round(x, 4) for x in k], "cost": round(cost, 4)})
        if max(abs(s) for s in step) < 1e-4 or lam > 1e6:
            break
    return {"multipliers": k, "residuals": r, "names": names, "cost_initial": cost0, "cost": cost, "history": history}


def run() -> dict:
    ref, survey = read_yaml(R.REFERENCE), read_yaml(R.SURVEY)
    cal = calibrate(ref, survey)
    k = cal["multipliers"]
    lo, hi = BOUNDS
    outside = [n for n, v in zip(NAMES, k) if not lo <= v <= hi]
    stall = ref["measured"]["near_stall"]
    s = _run(ref, stall["mass_flow_orifice"]["value"], k)
    stall_checks = {"PR": {"model": round(s["Pt_ratio"], 4), "measured": stall["pressure_ratio"]["value"],
                           "deviation": round(s["Pt_ratio"] / stall["pressure_ratio"]["value"] - 1, 4),
                           "limit": SCALE_PR},
                    "eta": {"model": round(s["efficiency"], 4), "measured": stall["efficiency"]["value"],
                            "deviation": round(s["efficiency"] - stall["efficiency"]["value"], 4), "limit": SCALE_ETA}}
    for c in stall_checks.values():
        c["result"] = "pass" if abs(c["deviation"]) <= c["limit"] else "fail"
    return {
        "description": "ADR-014 option (a) loss calibration on Rotor 67; generated by "
                       "engine/M1_inlet_fan/analysis/loss_calibration.py, do not edit",
        "tag": "H",
        "data": "design PR; near peak PR, eta and radial PR profile (unflagged rows) [KS]; near stall not used",
        "multipliers": {n: round(v, 4) for n, v in zip(NAMES, k)},
        "at_lower_clamp": [n for n, v in zip(NAMES, k) if v <= MIN_MULTIPLIER + 1e-3],
        "bounds": list(BOUNDS),
        "outside_bounds": outside,
        "applied": not outside,
        "decision": ("not applied: multiplier(s) outside the bounds; reported as a model-form problem (user rule, "
                     "M1 step 4c)") if outside else "within bounds",
        "fit": {"cost_initial": round(cal["cost_initial"], 3), "cost": round(cal["cost"], 3),
                "residuals_scaled": {n: round(v, 3) for n, v in zip(cal["names"], cal["residuals"])},
                "history": cal["history"]},
        "near_stall_with_multipliers": stall_checks,
    }


def main() -> None:
    result = run()
    write_yaml(OUT, result)
    print("multipliers", result["multipliers"], "outside", result["outside_bounds"], "applied", result["applied"])
    print("near stall", result["near_stall_with_multipliers"])


if __name__ == "__main__":
    main()
