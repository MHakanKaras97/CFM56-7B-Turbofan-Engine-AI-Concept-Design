"""CFM56-7B27 fan rotor design at the M0 design point (SLS ISA, max take-off), M1 step 4d (redesign).

Method (rules/aero_method.md R-AM.6, R-AM.7, R-AM.9, R-AM.10; ADR-015 budget-efficiency branch;
tools/meanline.py used unchanged):
- Budget and inlet state from the ICD (core.budgets.read_icd): W2, W21, W13, Tt2, Pt2, the stream
  targets FPR (outer) and pr_fan_inner (inner), the stream efficiencies, and the LP speed (Girão 2023
  nominal) [KS/H].
- Annulus: tip radius from the fan diameter, hub radius from the hub/tip ratio (analysis/fan_params.yaml);
  the annulus area is compared with the ICD fan_face_area. Exit hub and tip radii from the exit radius
  ratios [T].
- Splitter (R-AM.7): radius whose inner inlet annulus area share equals W21/W2 (uniform inlet: the solver
  splits the mass flow by inlet area); n_inner and n_outer tubes of equal inlet area within each stream.
  The exit areas start from exit_core_area_fraction and are then set by radial equilibrium.
- Loss model = rotor67.FULL_MODEL forms: radial equilibrium (solve_rotor_re), endwall and tip clearance
  losses (Endwall per tube: inlet span fraction, blade height = mean of inlet and exit annulus heights [T],
  chord = solidity x inlet pitch, running tip clearance [T]), no shock loss for subsonic inlet relative
  flow (subsonic_shock_taper False), all loss multipliers 1 (ADR-014 calibration not applied).
- Shock expansion angle (blading.shock_expansion): no measured CFM blade geometry, so no ss_turn of its own;
  "linear_camber" = tools/meanline.py default [T] (over-predicts the suction-surface Mach on Rotor 67, M1
  step 4c); option "rotor67_ss_turn" = Rotor 67's ss_turn at the same relative span [T analogue of KS data].
- Blading per tube: kappa1 = beta1 - design incidence [T]; kappa2 by bracketing + bisection for the tube
  target (blading.pr_distribution), then shifted per stream by the PR balance; solidity = lowest value
  meeting R-AM.9 against Rotor 67 at the same inlet span fraction (DF not above the Rotor 67 DF; above the
  sonic span also solidity not below the Rotor 67 solidity, hub 3.11 to tip 1.29 linear in span, Strazisar
  p. 2 [KS]). Rule not met even at solidity_max: supersonic zone keeps the Rotor 67 solidity floor (more
  solidity adds loss there without meeting the rule) [T], subsonic zone takes solidity_max; both reported.
- Coupling with radial equilibrium (see design()): blade shapes from a per-tube design on the initial layout,
  then fixed-blade solve_rotor_re with one kappa2 offset per stream (2x2 Newton) so that each stream's
  mass-averaged PR equals its target; R-AM.9 solidity pass on the equilibrium state; repeat.
- Efficiency (R-AM.10, ADR-015): the achieved stream efficiencies are the ICD budget values [T, M1's own
  prediction]; T13 and T21 = Tt2 (1 + (PR_target^((g-1)/g) - 1) / eta_budget); powers = W cp (Tt_exit - Tt2).
  The meanline's mass-averaged efficiencies are reported as information [H, unvalidated model].
- Mechanical check: centrifugal root stress of a blade with linear section-area taper between the inlet hub
  and tip radius, sigma = rho omega^2 L [r_h + L/2 - (1 - tau)(r_h/2 + L/3)], L = r_t - r_h [G]. Area taper
  tau = (t/c ratio tip/root) x (chord_tip / chord_root)^2 [G, similar sections]; the t/c ratio is that of
  Rotor 67 (max thickness / chord, sections 14 and 1, rotor67_geometry.yaml) [T analogue of KS data];
  chords of the hub and tip tubes.
  Not modelled: OGV, inlet recovery, streamline curvature, gas bending, dovetail.

Run: python -m engine.M1_inlet_fan.analysis.fan_design  (writes analysis/results.yaml).
"""

import math
from pathlib import Path

from core.budgets import check_budget, read_icd
from core.util import read_yaml, write_yaml
from tools.meanline import Endwall, Gas, Tube, loss_breakdown, mass_averaged, solve_rotor_re, solve_tube

M1 = Path(__file__).resolve().parents[1]
ROOT = M1.parents[1]
PARAMS = M1 / "analysis" / "fan_params.yaml"
OUT = M1 / "analysis" / "results.yaml"
MATERIALS = ROOT / "tools" / "data" / "materials.yaml"
R67_REFERENCE = M1 / "learning" / "rotor67_reference.yaml"
R67_GEOMETRY = M1 / "learning" / "rotor67_geometry.yaml"

INCH = 0.0254
MM = 0.001
KAPPA2_MIN = math.radians(-75.0)  # search bound of the exit metal angle [T]
AREA_CHECK = 0.01  # [T] allowed relative difference to the ICD fan_face_area
DF_TOL = 1e-4  # tolerance of the DF check
SIGMA_TOL = 1e-4  # bisection tolerance of the solidity search
PR_TOL = 1e-4  # stream PR after the final solve_rotor_re against its target (relative)
NEWTON_TOL = 2e-5  # stream PR balance tolerance (relative); solve_rotor_re stops at an area change of 1e-5 per pass
FD_STEP = math.radians(0.05)  # finite-difference step of the offset Jacobian
MAX_STEP = math.radians(3.0)  # largest Newton step of an offset
MAX_NEWTON = 15
SIGMA_STABLE = 1e-3  # outer-pass tolerance on the solidity change
MAX_OUTER = 10


SHOCK_NOTES = {
    "linear_camber": "[T] tools/meanline.py default, incidence + covered fraction x camber (no measured CFM blade "
                     "geometry); on Rotor 67 it over-predicted the suction-surface Mach (M1 step 4c: tip M_ss 1.65 vs "
                     "measured maximum 1.42), so the shock loss is likely high",
    "rotor67_ss_turn": "[T] analogue: ss_turn (kappa1 minus the suction-surface angle at the covered-passage entrance) "
                       "taken from Rotor 67 at the same relative span (KS geometry, rotor67.build_tubes; held constant "
                       "outside span 0.11-0.92). No CFM blade geometry; on Rotor 67 this form gave M_ss within +0.04 to "
                       "+0.11 of the TP-2879 laser data (M1 step 4c)",
}


def v(q: dict) -> float:
    return float(q["value"])


def icd_inputs(icd: dict) -> dict:
    budget = icd["modules"]["M1"]["budget"]
    st2 = icd["stations"]["2"]
    assert st2["Pt"]["unit"] == "kPa" and st2["Tt"]["unit"] == "K"
    rpm = icd["shafts"]["LP"]["speed_refs"]["girao_nominal"]
    assert rpm["unit"] == "rpm"
    return {"W2": v(budget["W2"]), "W21": v(budget["W21"]), "W13": v(budget["W13"]),
            "FPR": v(budget["FPR"]), "pr_fan_inner": v(budget["pr_fan_inner"]),
            "eta_fan_outer": v(budget["eta_fan_outer"]), "eta_fan_inner": v(budget["eta_fan_inner"]),
            "Tt2": v(st2["Tt"]), "Pt2": v(st2["Pt"]) * 1e3, "rpm": v(rpm),
            "fan_face_area": v(icd["fan_face_area"])}


def annulus(p: dict, inp: dict) -> dict:
    a = p["annulus"]
    r_tip1 = v(a["fan_tip_diameter"]) * INCH / 2
    r_hub1 = v(a["hub_tip_ratio"]) * r_tip1
    r_tip2 = v(a["exit_tip_radius_ratio"]) * r_tip1
    r_hub2 = v(a["exit_hub_radius_ratio"]) * r_hub1
    core_share = inp["W21"] / inp["W2"]
    r_split1 = math.sqrt(r_hub1 ** 2 + core_share * (r_tip1 ** 2 - r_hub1 ** 2))
    f2 = v(a["exit_core_area_fraction"])
    r_split2 = math.sqrt(r_hub2 ** 2 + f2 * (r_tip2 ** 2 - r_hub2 ** 2))
    area1 = math.pi * (r_tip1 ** 2 - r_hub1 ** 2)
    return {"r_tip1": r_tip1, "r_hub1": r_hub1, "r_split1": r_split1, "r_tip2": r_tip2, "r_hub2": r_hub2,
            "r_split2": r_split2, "area1": area1, "area2": math.pi * (r_tip2 ** 2 - r_hub2 ** 2),
            "core_share": core_share, "fan_face_area_deviation": area1 / inp["fan_face_area"] - 1,
            "blade_height": ((r_tip1 - r_hub1) + (r_tip2 - r_hub2)) / 2}


def equal_area_rings(r_in: float, r_out: float, n: int) -> list[tuple[float, float]]:
    """n rings of equal area between r_in and r_out: (inner, outer) radii."""
    edges = [math.sqrt(r_in ** 2 + k / n * (r_out ** 2 - r_in ** 2)) for k in range(n + 1)]
    return list(zip(edges[:-1], edges[1:]))


def tube_layout(p: dict, ann: dict) -> list[dict]:
    """Inlet and (initial) exit radius and area of every tube, hub first, with its stream."""
    n_in, n_out = int(v(p["stream_tubes"]["n_inner"])), int(v(p["stream_tubes"]["n_outer"]))
    rings1 = equal_area_rings(ann["r_hub1"], ann["r_split1"], n_in) + equal_area_rings(ann["r_split1"], ann["r_tip1"], n_out)
    rings2 = equal_area_rings(ann["r_hub2"], ann["r_split2"], n_in) + equal_area_rings(ann["r_split2"], ann["r_tip2"], n_out)
    out = []
    for j, ((a, b), (c, d)) in enumerate(zip(rings1, rings2), 1):
        r1 = math.sqrt((a * a + b * b) / 2)
        out.append({"name": f"tube {j}", "stream": "inner" if j <= n_in else "outer",
                    "r1": r1, "r2": math.sqrt((c * c + d * d) / 2),
                    "A1": math.pi * (b * b - a * a), "A2": math.pi * (d * d - c * c),
                    "span": (r1 - ann["r_hub1"]) / (ann["r_tip1"] - ann["r_hub1"])})
    return out


# --- R-AM.9 reference: Rotor 67 at the same relative span --------------------------------------------------

def rotor67_loading(ref: dict | None = None) -> dict:
    """Rotor 67 DF points (span, DF) without exit-choked streamlines and the hub/tip solidity [H/KS]."""
    ref = ref or read_yaml(R67_REFERENCE)
    pts = sorted((s["span_fraction"], s["diffusion_factor"]) for s in ref["computed_diffusion_factor"]["streamlines"]
                 if not s["exit_choked"])
    return {"df_points": pts, "solidity_hub": v(ref["design"]["solidity_hub"]),
            "solidity_tip": v(ref["design"]["solidity_tip"])}


def rotor67_ss_turn_points() -> list[tuple[float, float]]:
    """(span fraction, ss_turn rad) of the Rotor 67 design streamlines: kappa1 minus the suction-surface angle at
    the covered-passage entrance from the KS geometry (analysis/rotor67.py build_tubes, M1 step 4c)."""
    from engine.M1_inlet_fan.analysis import rotor67
    ref = read_yaml(R67_REFERENCE)
    st1 = ref["survey_stations"]["station_1_upstream"]
    r_hub, r_tip = v(st1["hub_radius"]), v(st1["shroud_radius"])
    return sorted(((t.r1 / rotor67.CM - r_hub) / (r_tip - r_hub), t.ss_turn) for t in rotor67.build_tubes(ref))


def interp_held(pts: list[tuple[float, float]], span: float) -> float:
    """Linear interpolation in span fraction, held constant outside the data range [T]."""
    if span <= pts[0][0]:
        return pts[0][1]
    if span >= pts[-1][0]:
        return pts[-1][1]
    i = next(i for i in range(len(pts) - 1) if pts[i][0] <= span <= pts[i + 1][0])
    (x0, y0), (x1, y1) = pts[i], pts[i + 1]
    return y0 + (y1 - y0) * (span - x0) / (x1 - x0)


def r67_df(r67: dict, span: float) -> float:
    """Rotor 67 DF at a span fraction: linear interpolation, held constant outside the data range [T]."""
    return interp_held(r67["df_points"], span)


def r67_solidity(r67: dict, span: float) -> float:
    return r67["solidity_hub"] + (r67["solidity_tip"] - r67["solidity_hub"]) * span


# --- tube construction and per-tube design -----------------------------------------------------------------

def covered_fraction(kappa1: float, kappa2: float, solidity: float) -> float:
    """Pitch sin(kappa1) cos(kappa1) over the meridional chord (chord x cos(stagger)), as in rotor67.py;
    stagger = mean of the metal angles [T]."""
    stagger = (kappa1 + kappa2) / 2
    return min(1.0, math.sin(kappa1) * math.cos(kappa1) / (solidity * math.cos(stagger)))


def make_tube(t: dict, kappa1: float, kappa2: float, solidity: float, ctx: dict) -> Tube:
    """Stream tube with the FULL_MODEL loss forms: Endwall data, no subsonic shock taper, multipliers 1."""
    chord = solidity * 2 * math.pi * t["r1"] / ctx["blades"]
    ew = Endwall(t["span"], ctx["blade_height"], chord, ctx["tip_clearance"])
    return Tube(name=t["name"], r1=t["r1"], r2=t["r2"], A1=t["A1"], A2=t["A2"], kappa1=kappa1, kappa2=kappa2,
                solidity=solidity, covered_fraction=covered_fraction(kappa1, kappa2, solidity), endwall=ew,
                ss_turn=interp_held(ctx["ss_turn_points"], t["span"]) if ctx["ss_turn_points"] else None,
                subsonic_shock_taper=False)


def kappa2_for(t: dict, kappa1: float, solidity: float, target: tuple[str, float], m: float, ctx: dict,
               guess: float | None) -> float:
    """Exit metal angle that gives the tube target (TubeResult attribute, value): "Pt_ratio" or "Tt_ratio".
    Bracket from the guess in 1 deg steps, then bisection; both rise as kappa2 falls (more turning)."""
    attr, goal = target

    def q(k2):
        return getattr(solve_tube(make_tube(t, kappa1, k2, solidity, ctx), m, ctx["omega"], ctx["Tt"], ctx["Pt"],
                                  ctx["gas"]), attr)

    step, top = math.radians(1.0), kappa1 - math.radians(1.0)
    x = min(top, guess) if guess is not None else top
    if q(x) >= goal:  # too much turning: move up until below the goal
        lo = x
        while True:
            hi = min(top, lo + step)
            if hi == lo:
                raise ValueError(f"{t['name']}: {attr} {goal:.5f} below the 1 deg camber value")
            if q(hi) < goal:
                break
            lo = hi
    else:  # move down until the goal is reached
        hi = x
        while True:
            lo = hi - step
            if lo < KAPPA2_MIN:
                raise ValueError(f"{t['name']}: {attr} {goal:.5f} not reached down to kappa2 "
                                 f"{math.degrees(KAPPA2_MIN)} deg")
            if q(lo) >= goal:
                break
            hi = lo
    # invariant: q(lo) >= goal > q(hi)
    for _ in range(36):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if q(mid) >= goal else (lo, mid)
    return (lo + hi) / 2


def design_tube(t: dict, target: tuple[str, float], m: float, ctx: dict, prev: dict | None) -> dict:
    """Metal angles and solidity of one tube on its current exit radius and area (R-AM.6, R-AM.9)."""
    bl, r67 = ctx["blading"], ctx["r67"]
    s_max = v(bl["solidity_max"])
    beta1 = solve_tube(make_tube(t, 1.0, 0.5, 1.5, ctx), m, ctx["omega"], ctx["Tt"], ctx["Pt"], ctx["gas"]).beta1
    kappa1 = beta1 - math.radians(v(bl["design_incidence"]))
    df_lim = r67_df(r67, t["span"])
    supersonic_zone = t["span"] > v(bl["rotor67_sonic_span"])
    floor = r67_solidity(r67, t["span"]) if supersonic_zone else v(bl["solidity_min"])
    guess = {"k2": prev["kappa2"] if prev else None}

    def at(sigma):
        k2 = kappa2_for(t, kappa1, sigma, target, m, ctx, guess["k2"])
        guess["k2"] = k2
        df = solve_tube(make_tube(t, kappa1, k2, sigma, ctx), m, ctx["omega"], ctx["Tt"], ctx["Pt"],
                        ctx["gas"]).diffusion_factor
        return k2, df

    k2, df = at(floor)
    if df <= df_lim:
        sigma, binding = floor, "Rotor 67 solidity floor" if supersonic_zone else "solidity lower bound"
    else:
        k2_max, df_max = at(s_max)
        if df_max > df_lim and supersonic_zone:  # rule not met: keep the Rotor 67 solidity floor [T]
            k2 = at(floor)[0]
            sigma, binding = floor, (f"rule not met: DF above the Rotor 67 DF even at solidity {s_max} "
                                     f"(DF there {df_max:.3f}); solidity kept at the Rotor 67 floor")
        elif df_max > df_lim:
            sigma, k2, binding = s_max, k2_max, "rule not met: solidity upper bound, DF above the Rotor 67 DF"
        else:
            lo, hi = floor, s_max
            if prev is not None and floor < prev["solidity"] < s_max:  # narrow the bracket around the last value
                a, b = max(floor, prev["solidity"] - 0.02), min(s_max, prev["solidity"] + 0.02)
                if at(a)[1] > df_lim:
                    lo = a
                if at(b)[1] <= df_lim:
                    hi = b
            while hi - lo > SIGMA_TOL:
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if at(mid)[1] > df_lim else (lo, mid)
            sigma, binding = hi, "Rotor 67 DF"
            k2 = at(sigma)[0]
    return {"kappa1": kappa1, "kappa2": k2, "solidity": sigma, "df_limit": df_lim, "solidity_floor": floor,
            "supersonic_zone": supersonic_zone, "binding": binding}


def stream_average(results, layout: list[dict], name: str, gas: Gas) -> dict:
    return mass_averaged([r for r, t in zip(results, layout) if t["stream"] == name], gas)


def design(layout: list[dict], stream_targets: dict, stream_eta: dict, masses: list[float], ctx: dict,
           ann: dict) -> dict:
    """Blading with radial equilibrium (solve_rotor_re) in the loop.

    1. Blade shapes on the initial layout (exit areas from exit_core_area_fraction): per tube kappa1 from the
       design incidence, solidity by R-AM.9 and kappa2 for the tube target of blading.pr_distribution:
       "constant_work" = same Tt ratio in every tube of a stream (free-vortex type, r Vt2 about constant without
       inlet swirl [G]) at the level 1 + (PR_target^((g-1)/g) - 1) / eta_budget; "uniform_pr" = tube PR = stream
       target (R-AM.6 of M1 step 3).
    2. Balance: solve_rotor_re with these blades (fixed metal angles; work, deviation and losses follow the
       equilibrium exit radii) and one kappa2 offset per stream, found by 2x2 Newton so that each stream's
       mass-averaged PR equals its ICD target (NEWTON_TOL). The outer offset is applied only below span
       blading.outer_offset_span_limit (tip tubes keep their shape) [T]; only physical equilibria are accepted
       (converged, no tube at exit choke). The spanwise work distribution is the equilibrium one.
    3. R-AM.9 pass on the equilibrium exit radii and areas: per tube the lowest solidity meeting the rule, with
       kappa2 re-found for the tube's equilibrium Tt ratio (work held). Repeat 2-3 until no solidity moves by
       more than SIGMA_STABLE, then balance once more.
    Why not a per-tube target inside the equilibrium: with the full loss model the tip tube entropy is high,
    and simple radial equilibrium at a prescribed work (dVm^2 = -2 T ds for constant work) drives the tip Vm2
    towards zero; prescribing uniform PR adds work where the loss is and runs away (M1 step 4d trials: tip tube
    at 63 % of the exit area, efficiency 0.24). With fixed blades the work rises as Vm2 falls, which is stable."""
    mode = ctx["pr_distribution"]
    gas = ctx["gas"]
    geo = [dict(t) for t in layout]
    if mode == "uniform_pr":
        level, attr = dict(stream_targets), "Pt_ratio"
    elif mode == "constant_work":
        level = {k: 1 + (stream_targets[k] ** (1 / gas.k) - 1) / stream_eta[k] for k in stream_targets}
        attr = "Tt_ratio"
    else:
        raise ValueError(f"unknown pr_distribution {mode}")

    def targets():
        return [(attr, level[t["stream"]]) for t in geo]

    streams = list(stream_targets)
    span_limit = ctx["offset_span_limit"]
    weight = [1.0 if t["stream"] == "inner" or t["span"] < span_limit else 0.0 for t in geo]

    def blades(shape, off):
        return [make_tube(t, d["kappa1"], d["kappa2"] + w * off[t["stream"]], d["solidity"], ctx)
                for t, d, w in zip(geo, shape, weight)]

    def re(shape, off):
        sol = solve_rotor_re(blades(shape, off), ctx["W2"], ctx["omega"], ctx["Tt"], ctx["Pt"], ann["r_hub2"],
                             ann["r_tip2"], gas)
        err = [stream_average(sol.results, geo, k, gas)["Pt_ratio"] / stream_targets[k] - 1 for k in streams]
        return sol, err

    def physical(sol):
        """Converged equilibrium with no tube at exit choke (solve_rotor_re also has collapsed branches in which
        one tube takes most of the exit area and the others choke)."""
        return sol.converged and not any(r.notes for r in sol.results)

    def balance(shape, off):
        """2x2 Newton on the per-stream kappa2 offsets (finite-difference Jacobian, one-sided, the other side if
        the first leaves the physical branch) with fixed-blade solve_rotor_re and backtracking; every solve
        warm-starts from the last accepted equilibrium."""
        log = []
        for it in range(1, MAX_NEWTON + 1):
            sol, err = re(shape, off)
            log.append({"iteration": it, "offset_deg": {k: round(math.degrees(off[k]), 5) for k in streams},
                        "PR_error": [float(f"{e:.2e}") for e in err], "re_iterations": sol.iterations,
                        "physical": physical(sol)})
            if not physical(sol):
                raise ValueError(f"stream PR balance left the physical branch: {log[-1]}")
            for t, st in zip(geo, sol.tubes):  # warm start of the FD and trial solves: this equilibrium
                t["r2"], t["A2"] = st.r2, st.A2
            if max(abs(e) for e in err) < NEWTON_TOL:
                return sol, off, log
            jac = []
            for k in streams:
                for h in (FD_STEP, -FD_STEP):
                    s_k, e_k = re(shape, dict(off, **{k: off[k] + h}))
                    if physical(s_k):
                        break
                else:
                    raise ValueError(f"stream PR balance at a fold of the equilibrium branch ({k}): {log[-1]}")
                jac.append([(x - y) / h for x, y in zip(e_k, err)])  # column k: d err / d off_k
            (a, c), (b, d) = jac  # jac[col][row] -> J = [[a, b], [c, d]]
            det = a * d - b * c
            step = [(-d * err[0] + b * err[1]) / det, (c * err[0] - a * err[1]) / det]
            scale = min(1.0, MAX_STEP / max(abs(x) for x in step))
            norm = max(abs(e) for e in err)
            for _ in range(10):  # backtracking: first step on the physical branch that lowers the largest error
                trial = {k: off[k] + scale * x for k, x in zip(streams, step)}
                s_t, e_t = re(shape, trial)
                if physical(s_t) and max(abs(e) for e in e_t) < norm:
                    break
                scale /= 2
            else:
                raise ValueError(f"stream PR balance: no step lowers the error on the physical branch: {log[-1]}")
            off = trial
        raise ValueError(f"stream PR balance did not converge: {log[-1]}")

    shape = [design_tube(t, tgt, m, ctx, None) for t, tgt, m in zip(geo, targets(), masses)]  # initial layout
    off = {k: 0.0 for k in streams}
    history = []
    converged = False
    for outer in range(1, MAX_OUTER + 1):
        sol, off, log = balance(shape, off)
        for t, st in zip(geo, sol.tubes):
            t["r2"], t["A2"] = st.r2, st.A2
        new = []
        for t, d, r, m, w in zip(geo, shape, sol.results, masses, weight):  # R-AM.9 on the equilibrium, work held
            k_off = w * off[t["stream"]]
            nd = design_tube(t, ("Tt_ratio", r.Tt_ratio), m, ctx, dict(d, kappa2=d["kappa2"] + k_off))
            nd["kappa2"] -= k_off
            new.append(nd)
        d_sigma = max(abs(n["solidity"] - p["solidity"]) for n, p in zip(new, shape))
        history.append({"outer_pass": outer, "newton": log, "max_solidity_change": round(d_sigma, 6)})
        shape = new
        if d_sigma < SIGMA_STABLE:
            converged = True
            break
    sol, off, log = balance(shape, off)
    history.append({"final_balance": log})
    designs = [dict(d, kappa2=d["kappa2"] + w * off[t["stream"]]) for t, d, w in zip(geo, shape, weight)]
    pr_err = max(abs(stream_average(sol.results, geo, k, gas)["Pt_ratio"] / stream_targets[k] - 1) for k in streams)
    check = {"re_converged": sol.converged, "re_iterations": sol.iterations,
             "max_stream_PR_error_after_re": float(f"{pr_err:.2e}"), "PR_tolerance_relative": PR_TOL}
    return {"designs": designs, "solution": sol, "history": history, "levels": level, "target_attribute": attr,
            "offsets_deg": {k: round(math.degrees(x), 5) for k, x in off.items()},
            "converged": converged and sol.converged and pr_err < PR_TOL, "final_check": check}


# --- outputs -----------------------------------------------------------------------------------------------

def tip_relative_mach(r_tip: float, omega: float, outer, Tt: float, gas: Gas) -> float:
    """Inlet relative Mach at the tip radius with the axial velocity of the outermost tube."""
    T1 = Tt - outer.V1 ** 2 / (2 * gas.cp)
    return math.hypot(outer.V1, omega * r_tip) / math.sqrt(gas.gamma * gas.R * T1)


def root_stress(rho: float, omega: float, r_hub: float, r_tip: float, taper: float) -> float:
    """Centrifugal stress at the root of a blade whose section area falls linearly from root to tip."""
    L = r_tip - r_hub
    return rho * omega ** 2 * L * (r_hub + L / 2 - (1 - taper) * (r_hub / 2 + L / 3))


def rotor67_tc_ratio() -> dict:
    """Max thickness / chord of Rotor 67 at the hub (section 1) and casing (section 14) sections."""
    secs = {s["section"]: s for s in read_yaml(R67_GEOMETRY)["sections"]}
    hub, tip = secs[1], secs[max(secs)]
    tc_hub = v(hub["max_thickness"]) / v(hub["chord"])
    tc_tip = v(tip["max_thickness"]) / v(tip["chord"])
    return {"tc_hub": tc_hub, "tc_tip": tc_tip, "ratio": tc_tip / tc_hub}


def mechanical(p: dict, ann: dict, omega: float, chord_root: float, chord_tip: float) -> dict:
    ti = read_yaml(MATERIALS)["materials"]["ti6al4v"]
    rho, sy, uts = v(ti["density"]), v(ti["yield_strength"]), v(ti["ultimate_tensile_strength"])
    mech = p["mechanical"]
    assert mech["area_taper_method"]["value"] == "rotor67_tc_chord_squared"
    sf = v(mech["safety_factor"])
    tc = rotor67_tc_ratio()
    taper = tc["ratio"] * (chord_tip / chord_root) ** 2
    sigma = root_stress(rho, omega, ann["r_hub1"], ann["r_tip1"], taper) / 1e6
    sigma_uniform = root_stress(rho, omega, ann["r_hub1"], ann["r_tip1"], 1.0) / 1e6
    allowable = sy / sf
    return {
        "method": "[G] centrifugal stress at the blade root, linear section-area taper from inlet hub to tip "
                  "radius (root at the inlet hub radius, the longer span); no gas bending, dovetail or platform load",
        "density_kg_m3": rho, "density_tag": "KS (tools/data/materials.yaml ti6al4v, Mirghani 2023 Table 2 p. 17)",
        "chord_root_m": round(chord_root, 5), "chord_tip_m": round(chord_tip, 5),
        "chord_note": "[H] chords of the hub and tip stream tubes (taken as root and tip chords)",
        "tc_root_rotor67": round(tc["tc_hub"], 5), "tc_tip_rotor67": round(tc["tc_tip"], 5),
        "tc_note": "[T] Rotor 67 max thickness / chord at sections 1 and 14 (rotor67_geometry.yaml, KS data) used "
                   "as an analogue; CFM56-7B blade thickness doğrulanmadı",
        "taper_ratio": round(taper, 4),
        "taper_tag": "H from T: (t/c tip / t/c root) x (chord tip / chord root)^2, similar section shapes",
        "root_stress_MPa": round(sigma, 1), "root_stress_uniform_blade_MPa": round(sigma_uniform, 1),
        "strength_used": "yield_strength", "yield_strength_MPa": sy, "uts_MPa": uts,
        "strength_note": "[KS] yield, not UTS: the root must not yield under steady load; safety factor [T]",
        "safety_factor": sf, "allowable_MPa": round(allowable, 1),
        "margin": round(allowable / sigma - 1, 3), "margin_uniform_blade": round(allowable / sigma_uniform - 1, 3),
        "tag": "H",
    }


def deg(x: float) -> float:
    return round(math.degrees(x), 3)


def budget_exit_temperature(Tt: float, pr: float, eta: float, gas: Gas) -> float:
    """ADR-015: Tt_exit = Tt2 (1 + (PR^((g-1)/g) - 1) / eta)."""
    return Tt * (1 + (pr ** (1 / gas.k) - 1) / eta)


def run(params: dict | None = None, icd: dict | None = None, gas: Gas = Gas()) -> dict:
    p = params or read_yaml(PARAMS)
    icd = icd or read_icd("M1 agent")
    inp = icd_inputs(icd)
    ann = annulus(p, inp)
    omega = inp["rpm"] * 2 * math.pi / 60
    Tt, Pt = inp["Tt2"], inp["Pt2"]
    layout = tube_layout(p, ann)
    total_area = sum(t["A1"] for t in layout)
    bl = p["blading"]
    ctx = {"omega": omega, "Tt": Tt, "Pt": Pt, "gas": gas, "W2": inp["W2"], "blading": bl,
           "blades": int(v(bl["blade_count"])), "blade_height": ann["blade_height"],
           "tip_clearance": v(p["losses"]["tip_clearance_running"]) * MM, "r67": rotor67_loading(),
           "pr_distribution": bl["pr_distribution"]["value"], "shock_expansion": bl["shock_expansion"]["value"],
           "offset_span_limit": v(bl["outer_offset_span_limit"])}
    if ctx["shock_expansion"] == "rotor67_ss_turn":
        ctx["ss_turn_points"] = rotor67_ss_turn_points()
    elif ctx["shock_expansion"] == "linear_camber":
        ctx["ss_turn_points"] = None
    else:
        raise ValueError(f"unknown shock_expansion {ctx['shock_expansion']}")
    masses = [inp["W2"] * t["A1"] / total_area for t in layout]
    out = design(layout, {"outer": inp["FPR"], "inner": inp["pr_fan_inner"]},
                 {"outer": inp["eta_fan_outer"], "inner": inp["eta_fan_inner"]}, masses, ctx, ann)
    designs, sol = out["designs"], out["solution"]
    tubes, res = sol.tubes, sol.results

    rows = []
    for t, d, tube, r in zip(layout, designs, tubes, res):
        pitch = 2 * math.pi * t["r1"] / ctx["blades"]
        df_ok = r.diffusion_factor <= d["df_limit"] + DF_TOL
        sol_ok = tube.solidity >= d["solidity_floor"] - SIGMA_TOL
        rows.append({
            "name": t["name"], "stream": t["stream"], "span_fraction": round(t["span"], 4),
            "r1_m": round(t["r1"], 5), "r2_m": round(tube.r2, 5),
            "A1_m2": round(t["A1"], 5), "A2_m2": round(tube.A2, 5), "mass_flow_kg_s": round(r.mass_flow, 4),
            "U1_m_s": round(r.U1, 2), "U2_m_s": round(tube.r2 * omega, 2), "V1_m_s": round(r.V1, 2),
            "W1_m_s": round(r.W1, 2), "beta1_deg": deg(r.beta1), "M1rel": round(r.M1rel, 4),
            "Vm2_m_s": round(r.Vm2, 2), "Vt2_m_s": round(r.Vt2, 2), "V2_m_s": round(math.hypot(r.Vm2, r.Vt2), 2),
            "W2_m_s": round(r.W2, 2), "beta2_deg": deg(r.beta2), "M2rel": round(r.M2rel, 4),
            "Vm2_over_Vm1": round(r.Vm2 / r.V1, 4),
            "kappa1_deg": deg(tube.kappa1), "kappa2_deg": deg(tube.kappa2), "camber_deg": deg(tube.kappa1 - tube.kappa2),
            "incidence_deg": deg(r.incidence), "deviation_deg": deg(r.deviation),
            "solidity": round(tube.solidity, 4), "pitch_m": round(pitch, 5), "chord_m": round(tube.endwall.chord, 5),
            "covered_fraction": round(tube.covered_fraction, 4),
            "diffusion_factor": round(r.diffusion_factor, 4), "D_eq": round(r.deq, 4),
            "R_AM9": {"zone": "supersonic (DF and solidity)" if d["supersonic_zone"] else "subsonic (DF)",
                      "DF_limit_rotor67": round(d["df_limit"], 4),
                      "solidity_floor": round(d["solidity_floor"], 4), "binding": d["binding"],
                      "DF_check": "pass" if df_ok else "fail", "solidity_check": "pass" if sol_ok else "fail"},
            "M_passage": round(r.M_passage, 4),
            "loss_breakdown": {k: {"loss": round(x["loss"], 5), "delta_eta": round(x["delta_eta"], 5)}
                               for k, x in loss_breakdown(r).items()},
            "Pt_ratio": round(r.Pt_ratio, 5), "Tt_ratio": round(r.Tt_ratio, 5),
            "efficiency_meanline": round(r.efficiency, 5), "notes": r.notes,
        })

    streams = {}
    for name, pr_t, eta_b in (("outer", inp["FPR"], inp["eta_fan_outer"]), ("inner", inp["pr_fan_inner"], inp["eta_fan_inner"])):
        sel = [r for r, t in zip(res, layout) if t["stream"] == name]
        avg = mass_averaged(sel, gas)
        Tt_exit = budget_exit_temperature(Tt, pr_t, eta_b, gas)
        streams[name] = {"mass_flow_kg_s": avg["mass_flow"], "Pt_ratio_meanline": avg["Pt_ratio"],
                         "efficiency_budget": eta_b, "efficiency_meanline": avg["efficiency"],
                         "Tt_ratio_meanline": avg["Tt_ratio"], "Tt_exit_K": Tt_exit,
                         "power_MW": avg["mass_flow"] * gas.cp * (Tt_exit - Tt) / 1e6}
    overall = mass_averaged(res, gas)

    achieved = {
        "FPR": streams["outer"]["Pt_ratio_meanline"], "eta_fan_outer": inp["eta_fan_outer"],
        "pr_fan_inner": streams["inner"]["Pt_ratio_meanline"], "eta_fan_inner": inp["eta_fan_inner"],
        "W2": overall["mass_flow"], "W13": streams["outer"]["mass_flow_kg_s"], "W21": streams["inner"]["mass_flow_kg_s"],
        "T13": streams["outer"]["Tt_exit_K"], "T21": streams["inner"]["Tt_exit_K"],
        "power_outer_fan": streams["outer"]["power_MW"], "power_inner_fan": streams["inner"]["power_MW"],
    }
    checks = check_budget("M1", achieved)
    dfs = [r.diffusion_factor for r in res]
    sols = [t.solidity for t in tubes]
    chords = [row["chord_m"] for row in rows]
    tip_mrel = tip_relative_mach(ann["r_tip1"], omega, res[-1], Tt, gas)
    rule_fail = [row["name"] for row in rows if "fail" in (row["R_AM9"]["DF_check"], row["R_AM9"]["solidity_check"])]
    tip_sigma, r67_tip = tubes[-1].solidity, ctx["r67"]["solidity_tip"]

    return {
        "description": "M1 fan rotor design at the M0 design point (SLS ISA, max take-off), M1 step 4d redesign; "
                       "generated by engine/M1_inlet_fan/analysis/fan_design.py, do not edit",
        "icd_revision": icd["source"]["revision"],
        "inputs": {"tag": "H/KS from the ICD", "W2_kg_s": inp["W2"], "W21_kg_s": inp["W21"], "Tt2_K": Tt,
                   "Pt2_Pa": Pt, "rotor_speed_rpm": inp["rpm"], "rotor_speed_tag": "KS (Girão 2023 via ICD)",
                   "FPR_target": inp["FPR"], "pr_fan_inner_target": inp["pr_fan_inner"],
                   "eta_fan_outer_budget": inp["eta_fan_outer"], "eta_fan_inner_budget": inp["eta_fan_inner"]},
        "model": {
            "tag": "T (model choice)",
            "radial_equilibrium": "solve_rotor_re, exit annulus r_hub2..r_tip2",
            "losses": "profile (Lieblein D_eq) + shock + endwall (Howell) + tip clearance (Lakshminarayana), "
                      "multipliers 1 (ADR-014 calibration not applied)",
            "subsonic_shock_taper": False,
            "shock_expansion": ctx["shock_expansion"],
            "shock_expansion_note": SHOCK_NOTES[ctx["shock_expansion"]],
            "blade_height_m": round(ann["blade_height"], 5), "blade_height_tag": "T (mean of inlet and exit annulus heights)",
            "tip_clearance_m": ctx["tip_clearance"], "tip_clearance_tag": "T (fan_params.yaml losses)",
            "efficiency_rule": "R-AM.10 / ADR-015: achieved efficiencies = budget [T]; meanline efficiency = information "
                               "[H, unvalidated model]",
        },
        "annulus": {
            "tag": "H from T inputs",
            "r_tip1_m": round(ann["r_tip1"], 5), "r_hub1_m": round(ann["r_hub1"], 5),
            "r_split1_m": round(ann["r_split1"], 5), "r_tip2_m": round(ann["r_tip2"], 5),
            "r_hub2_m": round(ann["r_hub2"], 5),
            "r_split2_initial_m": round(ann["r_split2"], 5),
            "exit_core_area_fraction_equilibrium": round(sum(t.A2 for t, l in zip(tubes, layout) if l["stream"] == "inner")
                                                         / sum(t.A2 for t in tubes), 5),
            "inlet_area_m2": round(ann["area1"], 5), "exit_area_m2": round(ann["area2"], 5),
            "icd_fan_face_area_m2": inp["fan_face_area"],
            "fan_face_area_deviation": round(ann["fan_face_area_deviation"], 5),
            "fan_face_area_check": "pass" if abs(ann["fan_face_area_deviation"]) <= AREA_CHECK else "fail",
            "core_share_W21_W2": round(ann["core_share"], 5),
            "splitter_method": "inlet area share of the core tubes = W21/W2 (uniform inlet, split by area)",
        },
        "convergence": {"converged": out["converged"],
                        "outer_passes": sum(1 for h in out["history"] if "outer_pass" in h),
                        "scheme": "blade shapes on the initial layout; per-stream kappa2 offsets by 2x2 Newton with "
                                  "fixed-blade solve_rotor_re until each stream PR = target; R-AM.9 solidity pass on "
                                  "the equilibrium state with tube work held; repeat until solidity is stable",
                        "tolerances": {"stream_PR_newton": NEWTON_TOL, "stream_PR_final": PR_TOL,
                                       "solidity_search": SIGMA_TOL, "solidity_stable": SIGMA_STABLE,
                                       "fd_step_deg": round(math.degrees(FD_STEP), 4)},
                        "kappa2_offsets_deg": out["offsets_deg"],
                        "final_check": out["final_check"],
                        "pr_distribution": ctx["pr_distribution"], "tube_target": out["target_attribute"],
                        "initial_shape_levels": {k: round(x, 6) for k, x in out["levels"].items()},
                        "radial_equilibrium_residual": float(f"{sol.residual:.2e}"),
                        "history": out["history"]},
        "summary": {
            "tag": "H",
            "tip_M1rel": round(tip_mrel, 4), "U_tip_m_s": round(omega * ann["r_tip1"], 2),
            "DF_min": round(min(dfs), 4), "DF_max": round(max(dfs), 4),
            "loading_rule": "R-AM.9: DF <= Rotor 67 DF at the same span; above span "
                            f"{v(bl['rotor67_sonic_span'])} also solidity >= Rotor 67 solidity "
                            f"({ctx['r67']['solidity_hub']} hub to {r67_tip} tip, linear, Strazisar p. 2 [KS])",
            "R_AM9_check": "pass" if not rule_fail else "fail", "R_AM9_failed_tubes": rule_fail,
            "solidity_min": round(min(sols), 4), "solidity_max": round(max(sols), 4),
            "chord_min_m": min(chords), "chord_max_m": max(chords),
            "tip_solidity_sanity": f"tip tube solidity {tip_sigma:.3f} (chord {rows[-1]['chord_m']:.3f} m at pitch "
                                   f"{rows[-1]['pitch_m']:.3f} m) against Rotor 67 tip {r67_tip}: "
                                   + ("at or above the Rotor 67 value; a wide-chord fan has few long-chord blades, so a "
                                      "tip solidity of this order is plausible [G]; CFM56-7B tip chord doğrulanmadı"
                                      if tip_sigma >= r67_tip else "below the Rotor 67 tip solidity (check)"),
            "outer": {k: round(x, 5) for k, x in streams["outer"].items()},
            "inner": {k: round(x, 5) for k, x in streams["inner"].items()},
            "overall_meanline": {k: round(x, 5) for k, x in overall.items()},
            "efficiency_note": "efficiency_budget is the achieved value [T, ADR-015]; efficiency_meanline is "
                               "information only [H, unvalidated model: about 7 points low on Rotor 67 near peak]",
            "not_modelled": "OGV loss, inlet recovery, streamline curvature, incidence-dependent deviation and loss",
        },
        "tubes": rows,
        "mechanical": mechanical(p, ann, omega, rows[0]["chord_m"], rows[-1]["chord_m"]),
        "achieved": {k: round(x, 6) for k, x in achieved.items()},
        "achieved_tags": {"FPR": "H (meanline)", "pr_fan_inner": "H (meanline)", "eta_fan_outer": "T (budget, ADR-015)",
                          "eta_fan_inner": "T (budget, ADR-015)", "W2": "H", "W13": "H", "W21": "H",
                          "T13": "H from target FPR and budget eta", "T21": "H from target PR and budget eta",
                          "power_outer_fan": "H", "power_inner_fan": "H"},
        "budget_check": checks,
    }


def main() -> None:
    result = run()
    write_yaml(OUT, result)
    s, c = result["summary"], result["convergence"]
    print(f"converged {c['converged']} in {c['outer_passes']} outer passes, offsets {c['kappa2_offsets_deg']} deg, "
          f"{c['final_check']}")
    print(f"tip M1rel {s['tip_M1rel']}  DF {s['DF_min']}..{s['DF_max']}  solidity {s['solidity_min']}..{s['solidity_max']}"
          f"  R-AM.9 {s['R_AM9_check']} {s['R_AM9_failed_tubes']}")
    for r in result["tubes"]:
        q = r["R_AM9"]
        print(f"{r['name']} {r['stream']:5} span {r['span_fraction']:.3f} M1rel {r['M1rel']:.3f} k1 {r['kappa1_deg']:6.2f} "
              f"k2 {r['kappa2_deg']:6.2f} sig {r['solidity']:.3f}/{q['solidity_floor']:.3f} c {r['chord_m']:.3f} "
              f"DF {r['diffusion_factor']:.3f}/{q['DF_limit_rotor67']:.3f} PR {r['Pt_ratio']:.4f} "
              f"eta {r['efficiency_meanline']:.4f} [{q['binding']}] {r['notes']}")
    for k in ("outer", "inner"):
        print(k, s[k])
    m = result["mechanical"]
    print(f"root stress {m['root_stress_MPa']} MPa (taper {m['taper_ratio']}, uniform {m['root_stress_uniform_blade_MPa']}), "
          f"allowable {m['allowable_MPa']}, margin {m['margin']}")
    for row in result["budget_check"]:
        print(f"{row['result']:4} {row['item']}: achieved {row['achieved']:.5g} budget {row['budget']} dev {row.get('deviation', '')}")


if __name__ == "__main__":
    main()
