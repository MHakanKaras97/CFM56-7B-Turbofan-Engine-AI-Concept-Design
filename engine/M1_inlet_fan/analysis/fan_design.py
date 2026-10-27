"""CFM56-7B27 fan rotor design at the M0 design point (SLS ISA, max take-off), M1 step 4f (smooth blade, structure-driven root).

Method (rules/aero_method.md R-AM.7, R-AM.9 (step 4e), R-AM.10, R-AM.11, R-AM.12, R-AM.13; ADR-015 budget-efficiency
branch; tools/meanline.py used unchanged):
- Budget and inlet state from the ICD (core.budgets.read_icd): W2, W21, W13, Tt2, Pt2, the stream targets FPR
  (outer) and pr_fan_inner (inner), the stream efficiencies, and the LP speed (Girão 2023 nominal) [KS/H].
- Annulus and splitter (R-AM.7) as in step 4d: tip radius from the fan diameter, hub from the hub/tip ratio, exit
  radii from the exit radius ratios [T]; splitter at the inlet radius whose inner area share is W21/W2; n_inner and
  n_outer tubes of equal inlet area within each stream. The splitter is downstream of the rotor: the blade is one
  continuous blade from hub to tip.
- One smooth blade (span fraction f = (r1 - r_hub1) / (r_tip1 - r_hub1) of the tube centre), few parameters:
  * kappa1(f) = beta1(f) - design incidence (uniform inlet: beta1 = atan(U / V1) is smooth in radius) [T incidence];
  * chord(f) quadratic (3 coefficients), solidity = chord x blade count / (2 pi r1);
  * kappa2(f) = cubic + k4 B(f) (5 coefficients, B = C2 quintic smoothstep across the splitter) plus one offset
    per stream applied through the same blend, delta_inner (1 - B) + delta_outer B (R-AM.12) [T]: a C2 term,
    so the offsets cannot put a kink into the continuous blade at the splitter;
  * section profile (R-AM.11): MCA camber line + parabolic thickness (analysis/blade_profile.py), front camber
    share, t/c and x_max smooth in span from Rotor 67 fits [T analogue]; it gives each tube's Tube.ss_turn.
- Loss model = rotor67.FULL_MODEL forms: radial equilibrium (solve_rotor_re), endwall and tip clearance losses
  (blade height = mean of inlet and exit annulus heights [T], chord from chord(f), running tip clearance [T]), no
  shock loss for subsonic inlet relative flow, all loss multipliers 1 (ADR-014 calibration not applied).
- Work distribution (R-AM.12): the blade shape is designed for a free vortex in each stream (dh0 constant, r Vt2
  constant without inlet swirl) [G] blended across the splitter with the C2 quintic smoothstep B(f) (blading
  splitter_blend_start / splitter_blend_width) [T]: dh0 = dh_inner (1 - B) + dh_outer B; dh_inner, dh_outer solved
  so that the stream mass-averaged Tt ratios equal the stream levels [H]. The fixed blade then sets the actual work
  in radial equilibrium.
- Coupling (design()): per pass (1) stream levels 1 + (PR_target^((g-1)/g) - 1) / eta (budget eta in pass 0, then
  the meanline stream eta of the last balanced solution); (2) design-mode radial equilibrium (design_state: every
  tube at its vortex Tt target and the stream eta, no loss correlation); on it the chord each tube needs under
  R-AM.9 (step 4e), the lowest quadratic chord(f) above all needs with the section-area taper band (linear
  programme, minimum mean chord) and the root chord raised until every section has the stress margin (R-AM.13),
  kappa2 per tube for its vortex target at the new chord, least-squares fit of the kappa2 basis with kappa2
  monotonic over the splitter blend (R-AM.12, step 4f); (3) 2x2 Newton on (delta_inner, delta_outer) with the fixed blade in solve_rotor_re until each
  stream's mass-averaged PR equals its ICD target, only physical solutions (RotorSolution.physical). Repeat until
  the reshaped chord and kappa2 stop moving; the last balanced blade is the result.
- R-AM.9 (step 4e): below the sonic span of this fan (M1rel < 1) DF <= Lieblein limit, linear in span from 0.6 at
  the hub to 0.4 at the tip (NASA SP-36 PDF p. 286, printed p. 268 [K]; interpolation [T]); above it solidity >=
  Rotor 67 solidity at the same relative span (3.11 hub to 1.29 tip, linear, Strazisar p. 2 [KS]).
- Efficiency (R-AM.10, ADR-015): achieved stream efficiencies = ICD budget values [T]; T13, T21 from target PR and
  budget efficiency; meanline efficiencies are information [H, unvalidated model].
- Structure (R-AM.13, step 4f): section area A(f) = (2/3) t/c(f) chord(f)^2 (parabolic thickness of R-AM.11)
  with the Rotor 67 t/c fit [T analogue]; centrifugal stress of every section and the blade mass integrated along
  the span between the inlet hub and tip radius [G]; A_tip/A_root within the taper band [G].
- Tip check (step 4f): tip-region meanline efficiency of this fan against the same model on Rotor 67 (tip_region).
  Not modelled: OGV, inlet recovery, streamline curvature, gas bending, dovetail.

Run: python -m engine.M1_inlet_fan.analysis.fan_design  (writes analysis/results.yaml).
"""

import itertools
import logging
import math
from pathlib import Path

from core.budgets import check_budget, read_icd
from core.util import read_yaml, write_yaml
from engine.M1_inlet_fan.analysis import blade_profile as bp
from tools.meanline import (Endwall, Gas, Tube, TubeResult, area_centre_radii, equilibrium_areas, loss_breakdown,
                            mass_averaged, solve_rotor_re, solve_tube)

M1 = Path(__file__).resolve().parents[1]
ROOT = M1.parents[1]
PARAMS = M1 / "analysis" / "fan_params.yaml"
OUT = M1 / "analysis" / "results.yaml"
MATERIALS = ROOT / "tools" / "data" / "materials.yaml"
R67_REFERENCE = M1 / "learning" / "rotor67_reference.yaml"

INCH = 0.0254
MM = 0.001
LOG = logging.getLogger(__name__)
KAPPA2_MIN = math.radians(-75.0)  # search bound of the exit metal angle [T]
AREA_CHECK = 0.01  # [T] allowed relative difference to the ICD fan_face_area
DF_TOL = 1e-4  # tolerance of the DF check
SIGMA_TOL = 1e-4  # bisection tolerance of the solidity search
PR_TOL = 1e-4  # stream PR after the final solve_rotor_re against its target (relative)
NEWTON_TOL = 2e-5  # stream PR balance tolerance (relative)
FD_STEP = math.radians(0.05)  # finite-difference step of the offset Jacobian
MAX_STEP = math.radians(3.0)  # largest Newton step of an offset
MAX_NEWTON = 15
CHORD_STABLE = 1e-4  # m, outer-pass tolerance on the chord at the tubes
KAPPA2_STABLE = math.radians(0.01)  # outer-pass tolerance on kappa2 at the tubes
MAX_OUTER = 12
RE_MAX_ITER = 1000  # solve_rotor_re pass limit (relaxation 0.1 needs more than the default 200 here)
DESIGN_RELAX = 0.3  # relaxation of the design-mode equilibrium (no loss feedback)
DESIGN_TOL = 1e-7
DESIGN_MAX_ITER = 2000
MECH_GRID = 200  # Simpson intervals of the section-area integrals (even)
STRESS_STEP = 1.01  # root chord lower bound raised by 1 % per stress-loop step
MAX_STRESS_STEPS = 300
K2_GRID = 40  # intervals of the kappa2 blend monotonicity constraint (R-AM.12, step 4f)
K2_CHECK_GRID = 400  # intervals of the reported kappa2 blend check
K2_MONOTONE_TOL = 1e-3  # deg, largest allowed reverse step of kappa2 over the blend region in the check


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


# --- R-AM.9 (step 4e) -------------------------------------------------------------------------------------

def rotor67_solidity_ends(ref: dict | None = None) -> dict:
    ref = ref or read_yaml(R67_REFERENCE)
    return {"hub": v(ref["design"]["solidity_hub"]), "tip": v(ref["design"]["solidity_tip"])}


def r67_solidity(r67: dict, span: float) -> float:
    return r67["hub"] + (r67["tip"] - r67["hub"]) * span


def df_limit(bl: dict, span: float) -> float:
    """Lieblein limit of the subsonic region, linear in span between the SP-36 hub and tip values [T]."""
    hub, tip = v(bl["df_limit_hub"]), v(bl["df_limit_tip"])
    return hub + (tip - hub) * span


# --- smooth blade --------------------------------------------------------------------------------------------

def covered_fraction(kappa1: float, kappa2: float, solidity: float) -> float:
    """Pitch sin(kappa1) cos(kappa1) over the meridional chord (chord x cos(stagger)), as in rotor67.py;
    stagger = mean of the metal angles [T]."""
    stagger = (kappa1 + kappa2) / 2
    return min(1.0, math.sin(kappa1) * math.cos(kappa1) / (solidity * math.cos(stagger)))


def pitch(t: dict, ctx: dict) -> float:
    return 2 * math.pi * t["r1"] / ctx["blades"]


def make_tube(t: dict, kappa1: float, kappa2: float, solidity: float, ctx: dict) -> Tube:
    """Stream tube with the FULL_MODEL loss forms and the ss_turn of the R-AM.11 section profile."""
    chord = solidity * pitch(t, ctx)
    ew = Endwall(t["span"], ctx["blade_height"], chord, ctx["tip_clearance"])
    cov = covered_fraction(kappa1, kappa2, solidity)
    fam = bp.family_at(ctx["profile_fits"], t["span"])
    return Tube(name=t["name"], r1=t["r1"], r2=t["r2"], A1=t["A1"], A2=t["A2"], kappa1=kappa1, kappa2=kappa2,
                solidity=solidity, covered_fraction=cov, endwall=ew,
                ss_turn=bp.ss_turn(kappa1, kappa2, fam["front"], fam["tc"], fam["x_max"], cov),
                subsonic_shock_taper=False)


def splitter_blend(f: float, ctx: dict) -> float:
    """C2 quintic smoothstep 0 -> 1 above the splitter: x = (f - f_split - start) / width clipped to [0, 1],
    B = x^3 (10 - 15 x + 6 x^2) [T form]; f_split = inlet span fraction of the splitter radius."""
    x = min(1.0, max(0.0, (f - ctx["f_split"] - ctx["blend_start"]) / ctx["blend_width"]))
    return x ** 3 * (10 - 15 * x + 6 * x * x)


def kappa2_basis(f: float, ctx: dict) -> list[float]:
    """kappa2(f) basis: cubic polynomial plus the splitter blend."""
    return [1.0, f, f * f, f ** 3, splitter_blend(f, ctx)]


def splitter_blend_slope(f: float, ctx: dict) -> float:
    """dB/df of splitter_blend: 30 x^2 (1 - x)^2 / width inside the blend, 0 outside."""
    x = (f - ctx["f_split"] - ctx["blend_start"]) / ctx["blend_width"]
    return 30 * x * x * (1 - x) ** 2 / ctx["blend_width"] if 0 < x < 1 else 0.0


def kappa2_basis_slope(f: float, ctx: dict) -> list[float]:
    return [0.0, 1.0, 2 * f, 3 * f * f, splitter_blend_slope(f, ctx)]


def blend_region(ctx: dict) -> tuple[float, float]:
    """Span range of the splitter blend, clipped to the blade [0, 1]."""
    lo = ctx["f_split"] + ctx["blend_start"]
    return max(0.0, lo), min(1.0, lo + ctx["blend_width"])


def kappa2_fit(fs: list[float], k2: list[float], ctx: dict, offsets: dict) -> dict:
    """kappa2 basis coefficients: least squares over the tube values, subject to the R-AM.12 blend constraint
    (M1 step 4f): the total exit metal angle shape + delta_inner (1 - B) + delta_outer B (offsets of the last
    balance) is monotonic over the splitter blend region, s dkappa2/df >= 0 at K2_GRID + 1 points, s = +1 for
    blading.kappa2_blend_direction 'rising' (kappa2 rises from hub to tip over the whole blade) [T]; a direction
    taken from each pass's own fit flipped between passes (M1 step 4f trial). Inequality-constrained least
    squares by an active-set method on the KKT system (at most a few active points)."""
    rows = [kappa2_basis(f, ctx) for f in fs]
    n = len(rows[0])
    q_mat = [[2 * sum(r[i] * r[j] for r in rows) for j in range(n)] for i in range(n)]
    q_vec = [2 * sum(r[i] * y for r, y in zip(rows, k2)) for i in range(n)]
    free = bp.lstsq(rows, k2)
    lo, hi = blend_region(ctx)
    d_off = offsets["outer"] - offsets["inner"]

    s = ctx["k2_direction"]
    grid = [lo + (hi - lo) * j / K2_GRID for j in range(K2_GRID + 1)]
    g_rows = [[s * x for x in kappa2_basis_slope(f, ctx)] for f in grid]
    g_rhs = [-s * d_off * splitter_blend_slope(f, ctx) for f in grid]

    def slack(c):
        return [sum(a * x for a, x in zip(g, c)) - b for g, b in zip(g_rows, g_rhs)]

    active, c, it = [], free, 0
    for it in range(1, 101):
        if active:
            m = len(active)
            kkt = [q_mat[i] + [-g_rows[a][i] for a in active] + [q_vec[i]] for i in range(n)]
            kkt += [g_rows[a] + [0.0] * m + [g_rhs[a]] for a in active]
            sol = solve_linear(kkt)
            c, lam = sol[:n], sol[n:]
            if min(lam) < -1e-12:
                active.pop(lam.index(min(lam)))
                continue
        else:
            c = free
        sl = slack(c)
        worst = min(range(len(sl)), key=lambda j: sl[j])
        if sl[worst] >= -1e-12 or worst in active:
            break
        active.append(worst)
    else:
        raise ValueError("kappa2 monotonic fit: active set did not settle")
    return {"coefficients": c, "sign": s, "active_points": [round(grid[a], 5) for a in active],
            "constrained": bool(active), "iterations": it}


def blade_kappa2(blade: dict, f: float, ctx: dict) -> float:
    off, b = blade["offsets"], splitter_blend(f, ctx)
    shape = sum(c * x for c, x in zip(blade["kappa2"], kappa2_basis(f, ctx)))
    return shape + off["inner"] * (1 - b) + off["outer"] * b


def blade_solidity(blade: dict, t: dict, ctx: dict) -> float:
    return bp.polyval(blade["chord"], t["span"]) / pitch(t, ctx)


def blade_tubes(geo: list[dict], blade: dict, ctx: dict) -> list[Tube]:
    return [make_tube(t, k1, blade_kappa2(blade, t["span"], ctx), blade_solidity(blade, t, ctx), ctx)
            for t, k1 in zip(geo, ctx["kappa1"])]


def kappa2_for(t: dict, kappa1: float, solidity: float, goal: float, m: float, ctx: dict,
               guess: float | None) -> float:
    """Exit metal angle that gives the tube Tt ratio `goal`. Bracket from the guess in 1 deg steps, then
    bisection; the Tt ratio rises as kappa2 falls (more turning)."""
    def q(k2):
        return solve_tube(make_tube(t, kappa1, k2, solidity, ctx), m, ctx["omega"], ctx["Tt"], ctx["Pt"],
                          ctx["gas"]).Tt_ratio

    step, top = math.radians(1.0), kappa1 - math.radians(1.0)
    x = min(top, guess) if guess is not None else top
    if q(x) >= goal:
        lo = x
        while True:
            hi = min(top, lo + step)
            if hi == lo:
                raise ValueError(f"{t['name']}: Tt ratio {goal:.5f} below the 1 deg camber value")
            if q(hi) < goal:
                break
            lo = hi
    else:
        hi = x
        while True:
            lo = hi - step
            if lo < KAPPA2_MIN:
                raise ValueError(f"{t['name']}: Tt ratio {goal:.5f} not reached down to kappa2 "
                                 f"{math.degrees(KAPPA2_MIN)} deg")
            if q(lo) >= goal:
                break
            hi = lo
    for _ in range(36):  # invariant: q(lo) >= goal > q(hi)
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if q(mid) >= goal else (lo, mid)
    return (lo + hi) / 2


def vortex(geo: list[dict], masses: list[float], levels: dict, ctx: dict) -> dict:
    """Free vortex per stream with a smooth blend across the splitter (R-AM.12):
    dh0(f) = dh_inner (1 - B(f)) + dh_outer B(f), B = splitter_blend. dh_inner and dh_outer solve the two linear
    conditions that each stream's mass-averaged Tt ratio equals its level. Returns them and the tube Tt targets."""
    cpT = ctx["gas"].cp * ctx["Tt"]
    a, rhs = [], []
    for name in ("inner", "outer"):
        sel = [(m, splitter_blend(t["span"], ctx)) for t, m in zip(geo, masses) if t["stream"] == name]
        mass = sum(m for m, _ in sel)
        mb = sum(m * b for m, b in sel) / mass
        a.append((1 - mb, mb))
        rhs.append((levels[name] - 1) * cpT)
    det = a[0][0] * a[1][1] - a[0][1] * a[1][0]
    dh_in = (rhs[0] * a[1][1] - a[0][1] * rhs[1]) / det
    dh_out = (a[0][0] * rhs[1] - a[1][0] * rhs[0]) / det
    targets = [1 + (dh_in * (1 - b) + dh_out * b) / cpT for b in (splitter_blend(t["span"], ctx) for t in geo)]
    return {"dh_inner": dh_in, "dh_outer": dh_out, "targets": targets}


def required_solidity(t: dict, i: int, goal: float, m: float, ctx: dict, guess: float | None) -> dict:
    """Lowest solidity meeting R-AM.9 (step 4e) with the tube at its vortex Tt target: subsonic tube
    (M1rel < 1) DF <= df_limit; supersonic tube solidity >= Rotor 67 solidity at the same span."""
    bl, k1 = ctx["blading"], ctx["kappa1"][i]
    s_min, s_max = v(bl["solidity_min"]), v(bl["solidity_max"])
    if ctx["supersonic"][i]:
        return {"solidity": max(s_min, r67_solidity(ctx["r67"], t["span"])), "met": True}
    lim = df_limit(bl, t["span"])
    state = {"k2": guess}

    def df(sigma):
        state["k2"] = kappa2_for(t, k1, sigma, goal, m, ctx, state["k2"])
        return solve_tube(make_tube(t, k1, state["k2"], sigma, ctx), m, ctx["omega"], ctx["Tt"], ctx["Pt"],
                          ctx["gas"]).diffusion_factor

    if df(s_min) <= lim:
        return {"solidity": s_min, "met": True}
    if df(s_max) > lim:
        return {"solidity": s_max, "met": False}
    lo, hi = s_min, s_max
    while hi - lo > SIGMA_TOL:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if df(mid) > lim else (lo, mid)
    return {"solidity": hi, "met": True}


def chord_constraints(fs: list[float], needs: list[float], ctx: dict, root_chord_min: float = 0.0) -> list[tuple]:
    """Linear constraints (a, b), a . (c0, c1, c2) >= b, on the quadratic chord c(f) = c0 + c1 f + c2 f^2:
    - R-AM.9 need at every tube: c(f_i) >= need_i;
    - section-area taper A(1)/A(0) = (t/c tip / t/c root) (c(1)/c(0))^2 within [area_taper_min, area_taper_max]
      (R-AM.13): c(1) - a_lo c(0) >= 0 and a_hi c(0) - c(1) >= 0, a = sqrt(taper / tc_ratio);
    - root chord at least root_chord_min (raised by the stress loop of reshape until every section has the
      required stress margin).
    No monotonic-area constraint: with the Rotor 67 t/c analogue it ties the root chord to the mid-span chord
    (root chord 0.29-0.35 m, hub solidity about 4-5) and the stream PR balance then failed (M1 step 4f trials).
    All constraints are linear in the coefficients."""
    rows = [([1.0, f, f * f], n) for f, n in zip(fs, needs)]
    tcr = ctx["tc_ratio"]
    a_lo, a_hi = math.sqrt(ctx["taper_min"] / tcr), math.sqrt(ctx["taper_max"] / tcr)
    rows += [([1 - a_lo, 1.0, 1.0], 0.0), ([a_hi - 1, -1.0, -1.0], 0.0)]
    rows.append(([1.0, 0.0, 0.0], root_chord_min))
    return rows


def lowest_quadratic_above(rows: list[tuple]) -> list[float]:
    """Quadratic c(f) = c0 + c1 f + c2 f^2 with the smallest mean over 0 <= f <= 1 (c0 + c1/2 + c2/3) subject to
    the linear constraints `rows` (chord_constraints). Linear programme in 3 unknowns, solved by checking every
    vertex (three active constraints)."""
    best = None
    for idx in itertools.combinations(range(len(rows)), 3):
        try:
            c = solve_linear([rows[i][0] + [rows[i][1]] for i in idx])
        except ZeroDivisionError:
            continue
        if all(sum(a * x for a, x in zip(row, c)) >= b - 1e-12 for row, b in rows):
            obj = c[0] + c[1] / 2 + c[2] / 3
            if best is None or obj < best[0] - 1e-15:
                best = (obj, c)
    if best is None:
        raise ValueError("no quadratic chord distribution meets the requirements")
    return best[1]


def solve_linear(rows: list[list[float]]) -> list[float]:
    """Gauss-Jordan elimination with partial pivoting of an n x (n + 1) augmented matrix."""
    n = len(rows)
    a = [r[:] for r in rows]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[piv][col]) < 1e-14:
            raise ZeroDivisionError
        a[col], a[piv] = a[piv], a[col]
        for r in range(n):
            if r != col:
                q = a[r][col] / a[col][col]
                a[r] = [u - q * w for u, w in zip(a[r], a[col])]
    return [a[i][n] / a[i][i] for i in range(n)]


def size_chord(fs: list[float], needs: list[float], ctx: dict, stress: bool = True) -> tuple[list[float], dict, int]:
    """R-AM.13 chord sizing: lowest quadratic chord under chord_constraints, then (stress True) the root chord
    lower bound raised in STRESS_STEP steps until every section has the required stress margin.
    Returns (chord coefficients, blade_mechanics result, number of stress steps)."""
    root_min, steps = 0.0, 0
    while True:
        chord = lowest_quadratic_above(chord_constraints(fs, needs, ctx, root_min))
        mech = blade_mechanics(chord, ctx)
        if not stress or mech["margin"] >= ctx["mech"]["margin_min"]:
            return chord, mech, steps
        steps += 1
        if steps > MAX_STRESS_STEPS:
            raise ValueError(f"root stress margin {mech['margin']:.3f} not reached by raising the root chord")
        root_min = chord[0] * STRESS_STEP


# --- blade mechanics (R-AM.13) --------------------------------------------------------------------------------

def blade_mechanics(chord: list[float], ctx: dict) -> dict:
    """Section area A(f) = k t/c(f) chord(f)^2 (k = blade_profile.AREA_COEFFICIENT) of the smooth blade between
    the inlet hub (root) and tip radius, r = r_hub1 + f L; Simpson's rule over MECH_GRID intervals [H]:
    root centrifugal stress rho omega^2 int(A r dr) / A(0), the largest section stress
    rho omega^2 int_f^1 (A r dr) / A(f), and the blade mass rho int(A dr) (airfoil only)."""
    m = ctx["mech"]
    rho, omega, r_h, L = m["rho"], ctx["omega"], m["r_hub"], m["span"]
    tc = ctx["profile_fits"]["coefficients"]["tc"]
    n = MECH_GRID
    fs = [j / n for j in range(n + 1)]
    area = [bp.section_area(bp.polyval(chord, f), bp.polyval(tc, f)) for f in fs]
    w = [1 if j in (0, n) else (4 if j % 2 else 2) for j in range(n + 1)]
    h = L / n

    def simpson(vals, j0=0):  # integral from fs[j0] to 1 (j0 even)
        return h / 3 * sum((1 if j in (j0, n) else (4 if (j - j0) % 2 else 2)) * vals[j] for j in range(j0, n + 1))

    ar = [a * (r_h + f * L) for a, f in zip(area, fs)]
    moment = h / 3 * sum(wj * x for wj, x in zip(w, ar))
    sigma_root = rho * omega ** 2 * moment / area[0]
    sections = [(fs[j], rho * omega ** 2 * simpson(ar, j) / area[j]) for j in range(0, n, 2)]
    f_max, sigma_max = max(sections, key=lambda s: s[1])
    mass = rho * h / 3 * sum(wj * a for wj, a in zip(w, area))
    return {"area": area, "fs": fs, "sigma_root": sigma_root, "sigma_max": sigma_max, "f_sigma_max": f_max,
            "margin_root": m["allowable"] / sigma_root - 1, "margin": m["allowable"] / sigma_max - 1, "mass": mass,
            "taper": area[-1] / area[0]}


def stream_average(results, layout: list[dict], name: str, gas: Gas) -> dict:
    return mass_averaged([r for r, t in zip(results, layout) if t["stream"] == name], gas)


def design_state(layout: list[dict], masses: list[float], tt_targets: list[float], etas: list[float], ctx: dict,
                 ann: dict) -> list[dict]:
    """Design-mode simple radial equilibrium (R-AM.12): every tube at its prescribed Tt ratio and efficiency
    (no blade, no loss correlation), Vt2 = dh0 / U2 (no inlet swirl), Vm2 from continuity on the subsonic branch;
    exit areas and area-centre radii moved (relaxation DESIGN_RELAX) until tools.meanline.equilibrium_areas holds.
    Returns a copy of the layout with the design exit radii and areas."""
    gas, omega, Tt, Pt = ctx["gas"], ctx["omega"], ctx["Tt"], ctx["Pt"]
    k, cp = gas.k, gas.cp
    geo = [dict(t) for t in layout]
    area_total = sum(t["A2"] for t in geo)
    for _ in range(DESIGN_MAX_ITER):
        res = []
        for t, m, tr, eta in zip(geo, masses, tt_targets, etas):
            Tt2, pr = tr * Tt, (1 + eta * (tr - 1)) ** k
            vt = cp * Tt * (tr - 1) / (omega * t["r2"])

            def flux(vm):
                T2 = Tt2 - (vm * vm + vt * vt) / (2 * cp)
                return pr * Pt * (T2 / Tt2) ** k / (gas.R * T2) * vm * t["A2"] if T2 > 0 else 0.0

            vmax = math.sqrt(max(0.0, 2 * cp * Tt2 - vt * vt))
            vm_peak = max((vmax * (i + 1) / 400 for i in range(399)), key=flux)
            if flux(vm_peak) < m:
                raise ValueError(f"design state: {t['name']} choked at the exit")
            lo, hi = 0.0, vm_peak
            for _ in range(80):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if flux(mid) < m else (lo, mid)
            res.append(TubeResult(name=t["name"], mass_flow=m, U1=0.0, V1=0.0, W1=0.0, beta1=0.0, M1rel=0.0,
                                  incidence=0.0, deviation=0.0, beta2=0.0, Vm2=(lo + hi) / 2, Vt2=vt, W2=0.0,
                                  M2rel=0.0, diffusion_factor=0.0, deq=0.0, loss_profile=0.0, loss_shock=0.0,
                                  M_passage=0.0, Tt_ratio=tr, Pt_ratio=pr, efficiency=eta))
        target = equilibrium_areas(res, [t["r2"] for t in geo], area_total, Tt, Pt, gas)
        new = [t["A2"] + DESIGN_RELAX * (a - t["A2"]) for t, a in zip(geo, target)]
        new = [a * area_total / sum(new) for a in new]
        residual = max(abs(a / t["A2"] - 1) for a, t in zip(new, geo))
        order = sorted(range(len(geo)), key=lambda i: geo[i]["r2"])
        radii = area_centre_radii([new[i] for i in order], ann["r_hub2"], ann["r_tip2"])
        for j, i in enumerate(order):
            geo[i]["A2"], geo[i]["r2"] = new[i], radii[j]
        if residual < DESIGN_TOL:
            return geo
    raise ValueError("design-mode radial equilibrium did not converge")


def design(layout: list[dict], stream_targets: dict, stream_eta: dict, masses: list[float], ctx: dict,
           ann: dict) -> dict:
    """Smooth blade with radial equilibrium in the loop (see the module docstring, Coupling)."""
    gas = ctx["gas"]
    geo = [dict(t) for t in layout]
    streams = list(stream_targets)
    fs = [t["span"] for t in geo]

    def re(blade):
        sol = solve_rotor_re(blade_tubes(geo, blade, ctx), ctx["W2"], ctx["omega"], ctx["Tt"], ctx["Pt"],
                             ann["r_hub2"], ann["r_tip2"], gas, max_iter=RE_MAX_ITER)
        err = [stream_average(sol.results, geo, k, gas)["Pt_ratio"] / stream_targets[k] - 1 for k in streams]
        return sol, err

    def with_off(blade, off):
        return dict(blade, offsets=dict(off))

    def balance(blade):
        """2x2 Newton on the stream offsets (delta_inner, delta_outer) (finite-difference Jacobian, the other side
        if the first leaves the physical branch, backtracking); every solve warm-starts from the last accepted
        equilibrium."""
        off, log = dict(blade["offsets"]), []
        keys = ("inner", "outer")
        for it in range(1, MAX_NEWTON + 1):
            sol, err = re(with_off(blade, off))
            log.append({"iteration": it, "offset_deg": {k: round(math.degrees(off[k]), 5) for k in keys},
                        "PR_error": [float(f"{e:.2e}") for e in err], "re_iterations": sol.iterations,
                        "physical": sol.physical})
            LOG.info("balance %s", log[-1])
            if not sol.physical:
                raise ValueError(f"stream PR balance left the physical branch: {sol.issues} {log[-1]}")
            for t, st in zip(geo, sol.tubes):
                t["r2"], t["A2"] = st.r2, st.A2
            if max(abs(e) for e in err) < NEWTON_TOL:
                return sol, with_off(blade, off), log
            jac = []
            for k in keys:
                for h in (FD_STEP, -FD_STEP):
                    s_k, e_k = re(with_off(blade, dict(off, **{k: off[k] + h})))
                    if s_k.physical:
                        break
                else:
                    raise ValueError(f"stream PR balance at a fold of the equilibrium branch ({k}): {log[-1]}")
                jac.append([(x - y) / h for x, y in zip(e_k, err)])  # column k: d err / d off_k
            (a, c), (b, d) = jac
            det = a * d - b * c
            step = [(-d * err[0] + b * err[1]) / det, (c * err[0] - a * err[1]) / det]
            scale = min(1.0, MAX_STEP / max(abs(x) for x in step))
            norm = max(abs(e) for e in err)
            for _ in range(10):
                trial = {k: off[k] + scale * x for k, x in zip(keys, step)}
                s_t, e_t = re(with_off(blade, trial))
                if s_t.physical and max(abs(e) for e in e_t) < norm:
                    break
                scale /= 2
            else:
                raise ValueError(f"stream PR balance: no step lowers the error on the physical branch: {log[-1]}")
            off = trial
        raise ValueError(f"stream PR balance did not converge: {log[-1]}")

    def reshape(eta, offsets):
        """Design-mode state for the vortex targets at the stream levels of `eta`, chord needs on it, lowest
        quadratic chord under the R-AM.13 taper band, root chord raised until every section has the stress margin,
        kappa2 per tube at the new chord, monotonic-blend least-squares fit of the kappa2 basis (offsets of the
        last balance in the blend constraint)."""
        levels = {k: 1 + (stream_targets[k] ** (1 / gas.k) - 1) / eta[k] for k in streams}
        vt = vortex(layout, masses, levels, ctx)
        dgeo = design_state(layout, masses, vt["targets"], [eta[t["stream"]] for t in layout], ctx, ann)
        needs, met = [], []
        for i, (t, goal, m) in enumerate(zip(dgeo, vt["targets"], masses)):
            req = required_solidity(t, i, goal, m, ctx, None)
            needs.append(req["solidity"] * pitch(t, ctx))
            met.append(req["met"])
        chord, mech, stress_steps = size_chord(fs, needs, ctx)
        k2 = [kappa2_for(t, ctx["kappa1"][i], bp.polyval(chord, t["span"]) / pitch(t, ctx), goal, m, ctx, None)
              for i, (t, goal, m) in enumerate(zip(dgeo, vt["targets"], masses))]
        fit = kappa2_fit(fs, k2, ctx, offsets)
        new = {"chord": chord, "kappa2": fit["coefficients"], "offsets": {"inner": 0.0, "outer": 0.0}}
        resid = max(abs(blade_kappa2(new, f, ctx) - k) for f, k in zip(fs, k2))
        info = {"design_efficiency": {k: round(x, 6) for k, x in eta.items()},
                "levels": {k: round(x, 6) for k, x in levels.items()},
                "vortex_dh_J_kg": {"inner": round(vt["dh_inner"], 1), "outer": round(vt["dh_outer"], 1)},
                "design_exit_area_share": [round(t["A2"] / sum(x["A2"] for x in dgeo), 5) for t in dgeo],
                "chord_needs_m": [round(x, 5) for x in needs], "need_met": met,
                "root_stress_steps": stress_steps, "stress_margin": round(mech["margin"], 4),
                "area_taper": round(mech["taper"], 4),
                "kappa2_per_tube_deg": [round(math.degrees(x), 4) for x in k2],
                "kappa2_fit_max_residual_deg": round(math.degrees(resid), 4),
                "kappa2_blend_constraint": {"sign": fit["sign"], "active_points": fit["active_points"],
                                            "offsets_used_deg": {k: round(math.degrees(x), 5) for k, x in offsets.items()}}}
        return new, info, vt

    eta = dict(stream_eta)  # pass 0: budget efficiencies
    history, converged, shape, blade, sol, vt = [], False, None, None, None, None
    for p in range(MAX_OUTER + 1):
        new, info, vt_new = reshape(eta, blade["offsets"] if blade else {"inner": 0.0, "outer": 0.0})
        LOG.info("pass %d reshape: chord %s stress margin %s taper %s k2 %s active %s", p, [round(c, 5) for c in new["chord"]],
                 info["stress_margin"], info["area_taper"], info["kappa2_per_tube_deg"], info["kappa2_blend_constraint"])
        if shape is not None:
            d_c = max(abs(bp.polyval(new["chord"], f) - bp.polyval(shape["chord"], f)) for f in fs)
            d_k = max(abs(blade_kappa2(new, f, ctx) - blade_kappa2(shape, f, ctx)) for f in fs)
            info.update(max_chord_change_m=round(d_c, 6), max_kappa2_change_deg=round(math.degrees(d_k), 5))
            if d_c < CHORD_STABLE and d_k < KAPPA2_STABLE:
                converged = True
                history.append({"pass": p, **info, "note": "shape stable: the last balanced blade is kept"})
                break
        shape, vt = new, vt_new
        sol, blade, log = balance(dict(new, offsets=blade["offsets"] if blade else new["offsets"]))
        eta = {k: stream_average(sol.results, geo, k, gas)["efficiency"] for k in streams}
        history.append({"pass": p, **info, "newton": log,
                        "offsets_deg": {k: round(math.degrees(x), 5) for k, x in blade["offsets"].items()},
                        "meanline_efficiency": {k: round(x, 6) for k, x in eta.items()}})
    pr_err = max(abs(stream_average(sol.results, geo, k, gas)["Pt_ratio"] / stream_targets[k] - 1) for k in streams)
    check = {"re_converged": sol.converged, "re_iterations": sol.iterations, "physical": sol.physical,
             "issues": list(sol.issues), "max_stream_PR_error_after_re": float(f"{pr_err:.2e}"),
             "PR_tolerance_relative": PR_TOL}
    return {"blade": blade, "solution": sol, "history": history, "vortex": vt, "geo": geo,
            "converged": converged and sol.physical and pr_err < PR_TOL, "final_check": check}


# --- outputs -----------------------------------------------------------------------------------------------

def tip_relative_mach(r_tip: float, omega: float, outer, Tt: float, gas: Gas) -> float:
    """Inlet relative Mach at the tip radius with the axial velocity of the outermost tube."""
    T1 = Tt - outer.V1 ** 2 / (2 * gas.cp)
    return math.hypot(outer.V1, omega * r_tip) / math.sqrt(gas.gamma * gas.R * T1)


def sonic_span(V1: float, omega: float, Tt: float, ann: dict, gas: Gas) -> float:
    """Span fraction where the inlet relative Mach is 1 (uniform axial inlet velocity V1)."""
    T1 = Tt - V1 ** 2 / (2 * gas.cp)
    a1 = math.sqrt(gas.gamma * gas.R * T1)
    r = math.sqrt(a1 ** 2 - V1 ** 2) / omega
    return (r - ann["r_hub1"]) / (ann["r_tip1"] - ann["r_hub1"])


def root_stress(rho: float, omega: float, r_hub: float, r_tip: float, taper: float) -> float:
    """Centrifugal stress at the root of a blade whose section area falls linearly from root to tip."""
    L = r_tip - r_hub
    return rho * omega ** 2 * L * (r_hub + L / 2 - (1 - taper) * (r_hub / 2 + L / 3))


def mechanical_inputs(p: dict, ann: dict) -> dict:
    """Material, safety factor and blade span for blade_mechanics (R-AM.13)."""
    ti = read_yaml(MATERIALS)["materials"]["ti6al4v"]
    mech = p["mechanical"]
    assert mech["area_method"]["value"] == "integrated_section_area"
    rho, sy, uts = v(ti["density"]), v(ti["yield_strength"]), v(ti["ultimate_tensile_strength"])
    sf = v(mech["safety_factor"])
    return {"rho": rho, "yield_MPa": sy, "uts_MPa": uts, "safety_factor": sf, "allowable": sy * 1e6 / sf,
            "margin_min": v(mech["stress_margin_min"]), "r_hub": ann["r_hub1"], "span": ann["r_tip1"] - ann["r_hub1"]}


def mass_diagnosis(blade: dict, layout: list[dict], needs: list[float], ctx: dict, check_per_blade: float) -> dict:
    """M1 step 4f: why the airfoil mass differs from the check value [H]. Factors of the mass rho k int(t/c c^2 dr):
    density (materials.yaml), area coefficient k (profile integral vs Rotor 67 Table I), t/c (Rotor 67 fit) and
    chord (R-AM.9 needs + R-AM.13 stress loop). Chord attribution by re-sizing (size_chord) with the stress loop
    off and with each active chord need dropped in turn: sensitivities only, those blades are not valid designs."""
    mi, fits = ctx["mech"], ctx["profile_fits"]
    base = blade_mechanics(blade["chord"], ctx)
    m0, grid, n = base["mass"], base["fs"], MECH_GRID
    w = [1 if j in (0, n) else (4 if j % 2 else 2) for j in range(n + 1)]

    def integ(vals):  # int_0^1 ... df
        return sum(wj * x for wj, x in zip(w, vals)) / (3 * n)

    c = [bp.polyval(blade["chord"], f) for f in grid]
    tc = [bp.polyval(fits["coefficients"]["tc"], f) for f in grid]
    mean_chord = integ(c)
    eq_thickness = integ(base["area"]) / mean_chord
    tc_eff = integ([t * x * x for t, x in zip(tc, c)]) / integ([x * x for x in c])
    k_profile = [bp.profile_area_coefficient(bp.family_at(fits, f)["x_max"]) for f in (0.0, 0.5, 1.0)]
    k_r67 = [s["area_coefficient"] for s in bp.rotor67_section_areas()["sections"]]
    fs = [t["span"] for t in layout]
    root_pitch = 2 * math.pi * mi["r_hub"] / ctx["blades"]

    def variant(chord, mech, label, steps=None):
        return {"case": label, "chord_root_m": round(chord[0], 5),
                "chord_max_m": round(max(bp.polyval(chord, f) for f in grid), 5),
                "mass_kg": round(mech["mass"], 3), "mass_over_design": round(mech["mass"] / m0, 4),
                "margin": round(mech["margin"], 3), "taper": round(mech["taper"], 4),
                **({} if steps is None else {"stress_steps": steps})}

    ch_ns, mech_ns, _ = size_chord(fs, needs, ctx, stress=False)
    variants = [variant(ch_ns, mech_ns, "stress loop off (LP chord only, R-AM.13 margin not met)")]
    active = [i for i, (f, nd) in enumerate(zip(fs, needs)) if bp.polyval(blade["chord"], f) - nd < 1e-4]
    for i in active:
        drop = [0.0 if j == i else nd for j, nd in enumerate(needs)]
        ch, mech, st = size_chord(fs, drop, ctx)
        variants.append({**variant(ch, mech, f"need of {layout[i]['name']} dropped (stress loop on)", st),
                         "tube": layout[i]["name"], "span_fraction": round(fs[i], 4),
                         "need_m": round(needs[i], 5), "need_solidity": round(needs[i] / pitch(layout[i], ctx), 4)})
    reductions = [(m0 - v_["mass_kg"], v_["case"]) for v_ in variants]
    dominant = max(reductions)
    ratio = m0 / check_per_blade
    return {
        "method": "[H] mass = rho k int(t/c chord^2 dr); factors and re-sized chord variants (fan_design."
                  "mass_diagnosis); variants are sensitivities, not valid blades",
        "mass_over_check": round(ratio, 4),
        "check_note": "check value is a whole blade (airfoil + dovetail) set mass [KS weak]; this mass is the "
                      "airfoil only, so the airfoil-to-airfoil ratio is at least this value",
        "density": {"value_kg_m3": mi["rho"], "tag": "KS", "note": "Ti-6Al-4V handbook value; not a driver"},
        "area_coefficient": {"used": round(bp.AREA_COEFFICIENT, 5),
                             "profile_integral_f0_f05_f1": [round(x, 5) for x in k_profile],
                             "rotor67": [round(min(k_r67), 4), round(max(k_r67), 4)],
                             "mass_factor_if_rotor67": [round(min(k_r67) / bp.AREA_COEFFICIENT, 4),
                                                        round(max(k_r67) / bp.AREA_COEFFICIENT, 4)],
                             "note": "[H] k = 2/3 is already the integral of the R-AM.11 profile (not a t x c "
                                     "rectangle); the Rotor 67 sections would make the blade heavier, so k is not "
                                     "the cause"},
        "thickness": {"tc_chord2_weighted": round(tc_eff, 5), "tc_root": round(tc[0], 5), "tc_tip": round(tc[-1], 5),
                      "equivalent_mean_thickness_mm": round(eq_thickness * 1e3, 2),
                      "tag": "T analogue (Rotor 67 fit); CFM56-7B thickness doğrulanmadı",
                      "tc_scale_for_check": round(check_per_blade / m0, 4)},
        "chord": {"mean_chord_m": round(mean_chord, 5), "root_solidity": round(c[0] / root_pitch, 4),
                  "chord_scale_for_check": round(math.sqrt(check_per_blade / m0), 4),
                  "needs_m": [round(x, 5) for x in needs],
                  "active_needs": [layout[i]["name"] for i in active]},
        "variants": variants,
        "dominant_chord_driver": dominant[1],
        "dominant_chord_driver_mass_reduction_kg": round(dominant[0], 3),
        "tag": "H",
    }


def mechanical(p: dict, ann: dict, omega: float, blade: dict, ctx: dict,
               diagnosis: dict | None = None) -> dict:
    mi, fits = ctx["mech"], ctx["profile_fits"]
    mech = p["mechanical"]
    res = blade_mechanics(blade["chord"], ctx)
    c_root, c_tip = bp.polyval(blade["chord"], 0.0), bp.polyval(blade["chord"], 1.0)
    tc_root, tc_tip = bp.family_at(fits, 0.0)["tc"], bp.family_at(fits, 1.0)["tc"]
    a_root, a_tip = res["area"][0], res["area"][-1]
    sigma = res["sigma_root"] / 1e6
    sigma_linear = root_stress(mi["rho"], omega, ann["r_hub1"], ann["r_tip1"], res["taper"]) / 1e6
    sigma_uniform = root_stress(mi["rho"], omega, ann["r_hub1"], ann["r_tip1"], 1.0) / 1e6
    allowable = mi["allowable"] / 1e6
    n_blades = ctx["blades"]
    set_check = v(mech["blade_set_mass_check"])
    r67 = bp.rotor67_section_areas()
    coeffs = [s["area_coefficient"] for s in r67["sections"]]
    step = max(1, len(res["fs"]) // 20)
    return {
        "method": "[G] centrifugal stress at the blade root (inlet hub radius, the longer span) from the integrated "
                  "section area A(f) = k t/c(f) chord(f)^2 of the smooth blade (Simpson, "
                  f"{MECH_GRID} intervals): sigma_root = rho omega^2 int(A r dr) / A_root; no gas bending, dovetail "
                  "or platform load (R-AM.13)",
        "density_kg_m3": mi["rho"], "density_tag": "KS (tools/data/materials.yaml ti6al4v, Mirghani 2023 Table 2 p. 17)",
        "area_coefficient": round(bp.AREA_COEFFICIENT, 5),
        "area_coefficient_tag": "H from T: two parabolic thickness arcs of the R-AM.11 profile enclose 2/3 of t x c",
        "area_coefficient_rotor67": [round(min(coeffs), 4), round(max(coeffs), 4)],
        "area_coefficient_rotor67_tag": "H from KS (Table I TNPC integrated along the camber line)",
        "chord_root_m": round(c_root, 5), "chord_tip_m": round(c_tip, 5),
        "chord_note": "[H] chord(f) of the smooth blade at f = 0 (inlet hub) and f = 1 (inlet tip); the root chord "
                      "is the smallest that meets the R-AM.9 needs, the taper band and the stress margin (R-AM.13)",
        "tc_root": round(tc_root, 5), "tc_tip": round(tc_tip, 5),
        "tc_note": "[T] Rotor 67 t/c fit (blade_profile.rotor67_fits, KS sections) at f = 0 and 1 used as an "
                   "analogue (fixed t/c); CFM56-7B blade thickness doğrulanmadı",
        "thickness_root_mm": round(tc_root * c_root * 1e3, 2), "thickness_tip_mm": round(tc_tip * c_tip * 1e3, 2),
        "area_root_cm2": round(a_root * 1e4, 3), "area_tip_cm2": round(a_tip * 1e4, 3),
        "taper_ratio": round(res["taper"], 4),
        "taper_tag": "H (A_tip / A_root of the designed blade)",
        "taper_band": [v(mech["area_taper_min"]), v(mech["area_taper_max"])],
        "taper_band_tag": "G (no source with a page in the M1 source set; doğrulanmadı)",
        "taper_rotor67": round(r67["taper_tip_over_root"], 4),
        "taper_rotor67_tag": "H from KS (Table I section 14 / section 1 area)",
        "area_profile_cm2": [[round(res["fs"][j], 3), round(res["area"][j] * 1e4, 3)]
                             for j in range(0, len(res["fs"]), step)],
        "area_max_over_root": round(max(res["area"]) / res["area"][0], 4),
        "area_max_span_fraction": round(res["fs"][res["area"].index(max(res["area"]))], 3),
        "root_stress_MPa": round(sigma, 1),
        "max_section_stress_MPa": round(res["sigma_max"] / 1e6, 1),
        "max_section_stress_span_fraction": round(res["f_sigma_max"], 3),
        "root_stress_linear_taper_MPa": round(sigma_linear, 1),
        "root_stress_linear_taper_note": "[H] cross-check: same taper, area linear in radius",
        "root_stress_uniform_blade_MPa": round(sigma_uniform, 1),
        "strength_used": "yield_strength", "yield_strength_MPa": mi["yield_MPa"], "uts_MPa": mi["uts_MPa"],
        "strength_note": "[KS] yield, not UTS: the root must not yield under steady load; safety factor [T]",
        "safety_factor": mi["safety_factor"], "allowable_MPa": round(allowable, 1),
        "margin_root": round(allowable / sigma - 1, 3),
        "margin": round(res["margin"], 3), "margin_required": mi["margin_min"],
        "margin_note": "[H] margin = allowable / largest section stress - 1 (the design requirement, R-AM.13); "
                       "margin_root at the root section",
        "margin_uniform_blade": round(allowable / sigma_uniform - 1, 3),
        "blade_mass": {
            "method": "[H] rho x integral of the section area from the inlet hub to the tip radius (airfoil only: "
                      "no dovetail, platform, edge circles or fillets)",
            "per_blade_kg": round(res["mass"], 3), "blade_count": n_blades,
            "set_kg": round(res["mass"] * n_blades, 2),
            "check_set_kg": set_check, "check_per_blade_kg": round(set_check / n_blades, 3),
            "check_tag": "KS weak (Mirghani 2023 Table 3, printed p. 49, PDF p. 67, citing other sources)",
            "set_over_check": round(res["mass"] * n_blades / set_check, 4)},
        **({"mass_diagnosis": diagnosis} if diagnosis is not None else {}),
        "tag": "H",
    }


def deg(x: float) -> float:
    return round(math.degrees(x), 3)


def budget_exit_temperature(Tt: float, pr: float, eta: float, gas: Gas) -> float:
    """ADR-015: Tt_exit = Tt2 (1 + (PR^((g-1)/g) - 1) / eta)."""
    return Tt * (1 + (pr ** (1 / gas.k) - 1) / eta)


def second_differences(fs: list[float], ys: list[float]) -> list[float]:
    """Second divided differences 2 [(y3 - y2)/(f3 - f2) - (y2 - y1)/(f2 - f1)] / (f3 - f1) at the inner points."""
    return [2 * ((ys[i + 1] - ys[i]) / (fs[i + 1] - fs[i]) - (ys[i] - ys[i - 1]) / (fs[i] - fs[i - 1]))
            / (fs[i + 1] - fs[i - 1]) for i in range(1, len(fs) - 1)]


def smoothness(rows: list[dict], n_inner: int) -> dict:
    """Per quantity: largest |second difference| over the tubes, the one at the splitter neighbours (the last
    inner and the first outer tube), and the first-difference ratio across the splitter to its neighbours."""
    fs = [r["span_fraction"] for r in rows]
    out = {"note": "[H] second divided differences in span fraction over the tube values; the blade functions "
                   "are smooth (chord quadratic, kappa2 cubic + C2 splitter blend, t/c cubic, kappa1 from radius), so there is "
                   "no jump at the splitter by construction",
           "splitter_between": [rows[n_inner - 1]["name"], rows[n_inner]["name"]]}
    for key in ("chord_m", "solidity", "kappa1_deg", "kappa2_deg", "t_c"):
        ys = [r[key] for r in rows]
        d2 = second_differences(fs, ys)
        slope = [(ys[i + 1] - ys[i]) / (fs[i + 1] - fs[i]) for i in range(len(fs) - 1)]
        s = n_inner - 1  # slope index across the splitter
        nb = [slope[j] for j in (s - 1, s + 1) if 0 <= j < len(slope)]
        out[key] = {"max_abs_second_difference": round(max(abs(x) for x in d2), 4),
                    "second_difference_at_splitter": [round(d2[s - 1], 4), round(d2[s], 4)],
                    "slope_across_splitter": round(slope[s], 4),
                    "slope_neighbours": [round(x, 4) for x in nb]}
    return out


def loading_coefficients(inp: dict, omega: float, ann: dict, gas: Gas) -> dict:
    """psi = dh0 / U_tip^2 (U_tip at the inlet tip radius). M1 fan: dh0 of the outer (bypass) stream from the
    target FPR and the budget efficiency (= cp (T13 - Tt2)). Rotor 67: dh0 = cp T_ref (TR - 1) with the measured
    near-peak TR at design speed and the design tip speed (the design efficiency is not in TP-2879)."""
    ref = read_yaml(R67_REFERENCE)
    u_tip = omega * ann["r_tip1"]
    dh_ours = gas.cp * (budget_exit_temperature(inp["Tt2"], inp["FPR"], inp["eta_fan_outer"], gas) - inp["Tt2"])
    tr67 = v(ref["measured"]["near_peak_efficiency"]["temperature_ratio"])
    u67 = v(ref["design"]["tip_speed"])
    dh67 = gas.cp * 288.15 * (tr67 - 1)
    return {"definition": "psi = dh0 / U_tip^2, U_tip at the inlet tip radius; M1: dh0 = cp (T13 - Tt2) of the "
                          "outer stream (target FPR, budget eta); Rotor 67: dh0 = cp 288.15 K (TR - 1), measured "
                          "near-peak TR at design speed (Table III(b) [KS]), design tip speed (p. 2 [KS])",
            "tag": "H", "psi_tip_M1": round(dh_ours / u_tip ** 2, 4), "U_tip_M1_m_s": round(u_tip, 2),
            "dh0_M1_J_kg": round(dh_ours, 1), "psi_tip_rotor67": round(dh67 / u67 ** 2, 4),
            "U_tip_rotor67_m_s": u67, "dh0_rotor67_J_kg": round(dh67, 1),
            "consequence": "the M1 tip is more highly loaded than Rotor 67, so the Rotor 67 solidity floor of the "
                           "supersonic region is a minimum, not a sufficient condition for the loading"}


def kappa2_blend_check(blade: dict, ctx: dict, ann: dict) -> dict:
    """R-AM.12 (step 4f) check of the final blade (shape + offsets): kappa2 monotonic over the splitter blend region
    on K2_CHECK_GRID intervals (largest reverse step <= K2_MONOTONE_TOL), and its second derivative (finite
    differences) as information."""
    lo, hi = blend_region(ctx)
    fs = [lo + (hi - lo) * j / K2_CHECK_GRID for j in range(K2_CHECK_GRID + 1)]
    k = [math.degrees(blade_kappa2(blade, f, ctx)) for f in fs]
    s = ctx["k2_direction"]
    steps = [s * (b - a) for a, b in zip(k, k[1:])]
    h = fs[1] - fs[0]
    d2 = [(k[j + 1] - 2 * k[j] + k[j - 1]) / (h * h) for j in range(1, len(k) - 1)]
    reverse = max(0.0, -min(steps))
    curv = max(abs(x) for x in d2)
    curv_limit = bp.rotor67_kappa2_curvature()["max_abs_deg"]
    L = ann["r_tip1"] - ann["r_hub1"]
    return {"rule": "R-AM.12 (M1 step 4f): kappa2(f) monotonic over the splitter blend region (no local minimum or "
                    "maximum, no dip); enforced in the kappa2 fit at "
                    f"{K2_GRID + 1} points (s dkappa2/df >= 0), checked here on {K2_CHECK_GRID + 1} points [T]",
            "region_span_fraction": [round(lo, 5), round(hi, 5)],
            "direction": "rising" if s > 0 else "falling",
            "kappa2_ends_deg": [round(k[0], 4), round(k[-1], 4)],
            "largest_reverse_step_deg": round(reverse, 6), "tolerance_deg": K2_MONOTONE_TOL,
            "max_abs_d2kappa2_df2_deg": round(curv, 2),
            "max_abs_d2kappa2_dr2_deg_per_m2": round(curv / L ** 2, 1),
            "curvature_limit_deg": round(curv_limit, 2),
            "curvature_limit_tag": "H from KS (largest |d2 kappa2/df2| of Rotor 67, Table I te_metal_angle; "
                                   "blading.kappa2_blend_curvature_limit)",
            "curvature_check": "pass" if curv <= curv_limit else "fail",
            "check": "pass" if reverse <= K2_MONOTONE_TOL else "fail", "tag": "H"}


def tip_region(p: dict, res, layout: list[dict], gas: Gas) -> dict:
    """Tip-region meanline efficiency, like for like (M1 step 4f): the same model (solve_rotor_re with
    max_iter RE_MAX_ITER, rotor67.FULL_MODEL loss forms, multipliers 1, tip clearance 0.39 % of the tip radius on
    both) on the M1 fan design point and on Rotor 67 at its design mass flow; tip region = stream tubes whose
    inlet centre span fraction is at or above the band limit [T], mass-averaged with tools.meanline.mass_averaged
    (mass-averaged Tt ratio, energy-averaged PR)."""
    from engine.M1_inlet_fan.analysis import rotor67  # local: rotor67 is only needed for this comparison
    tc = p["tip_check"]
    bands = [v(tc["band_span_min"]), v(tc["band_span_min_sensitivity"])]
    limit = v(tc["eta_gap_limit"])
    ref = read_yaml(R67_REFERENCE)
    fm = rotor67.FULL_MODEL
    assert fm["losses"] and fm["equilibrium"]
    tubes = rotor67.build_tubes(ref, None, losses=fm["losses"], shock_taper=fm["shock_taper"])
    st1, st2 = ref["survey_stations"]["station_1_upstream"], ref["survey_stations"]["station_2_downstream"]
    omega = v(ref["design"]["rotational_speed"]) * 2 * math.pi / 60
    sol = solve_rotor_re(tubes, v(ref["design"]["mass_flow"]), omega, rotor67.T_REF, rotor67.P_REF,
                         v(st2["hub_radius"]) * rotor67.CM, v(st2["shroud_radius"]) * rotor67.CM, gas,
                         max_iter=RE_MAX_ITER)
    r_h, r_t = v(st1["hub_radius"]), v(st1["shroud_radius"])
    span67 = [(t.r1 / rotor67.CM - r_h) / (r_t - r_h) for t in sol.tubes]
    span_m1 = [t["span"] for t in layout]
    out = {"definition": "tubes with inlet centre span fraction f >= band, mass-averaged (tools.meanline."
                         "mass_averaged); same solver and loss settings on both: solve_rotor_re (max_iter "
                         f"{RE_MAX_ITER}), rotor67.FULL_MODEL forms (endwall + tip clearance, no shock loss for a "
                         "subsonic inlet relative flow), multipliers 1",
           "rotor67_case": "design mass flow 33.25 kg/s, design speed, Table IV streamlines and Table I geometry [KS]",
           "rotor67_solution": {"converged": sol.converged, "physical": sol.physical, "iterations": sol.iterations},
           "tubes_M1": [[round(f, 4), round(r.efficiency, 4)] for f, r in zip(span_m1, res)],
           "tubes_rotor67": sorted([[round(f, 4), round(r.efficiency, 4)] for f, r in zip(span67, sol.results)]),
           "eta_gap_limit": limit, "eta_gap_limit_tag": "T (user rule, M1 step 4f)", "bands": [], "tag": "H"}
    for band in bands:
        ours = mass_averaged([r for r, f in zip(res, span_m1) if f >= band], gas)
        r67 = mass_averaged([r for r, f in zip(sol.results, span67) if f >= band], gas)
        out["bands"].append({"band_span_min": band, "eta_M1": round(ours["efficiency"], 5),
                             "eta_rotor67_model": round(r67["efficiency"], 5),
                             "gap_M1_minus_rotor67": round(ours["efficiency"] - r67["efficiency"], 5),
                             "tubes_M1": sum(1 for f in span_m1 if f >= band),
                             "tubes_rotor67": sum(1 for f in span67 if f >= band)})
    gap = out["bands"][0]["gap_M1_minus_rotor67"]
    out["decision"] = ("controlled vortex required (gap below -limit)" if gap < -limit
                       else "within the limit: free vortex kept")
    return out


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
    assert bl["profile_family"]["value"] == "MCA" and bl["vortex"]["value"] == "free_vortex_splitter_blend"
    assert bl["offset_blend"]["value"] == "splitter_blend"
    fits = bp.rotor67_fits()
    ctx = {"omega": omega, "Tt": Tt, "Pt": Pt, "gas": gas, "W2": inp["W2"], "blading": bl,
           "blades": int(v(bl["blade_count"])), "blade_height": ann["blade_height"],
           "tip_clearance": v(p["losses"]["tip_clearance_running"]) * MM, "r67": rotor67_solidity_ends(),
           "profile_fits": fits, "r_tip2": ann["r_tip2"],
           "taper_min": v(p["mechanical"]["area_taper_min"]), "taper_max": v(p["mechanical"]["area_taper_max"]),
           "tc_ratio": bp.family_at(fits, 1.0)["tc"] / bp.family_at(fits, 0.0)["tc"],
           "mech": mechanical_inputs(p, ann),
           "f_split": (ann["r_split1"] - ann["r_hub1"]) / (ann["r_tip1"] - ann["r_hub1"]),
           "blend_start": v(bl["splitter_blend_start"]), "blend_width": v(bl["splitter_blend_width"]),
           "k2_direction": {"rising": 1.0, "falling": -1.0}[bl["kappa2_blend_direction"]["value"]]}
    assert bl["kappa2_blend_curvature_limit"]["value"] == "rotor67_max"
    masses = [inp["W2"] * t["A1"] / total_area for t in layout]
    inlet = [solve_tube(make_tube(t, 1.0, 0.5, 1.5, ctx), m, omega, Tt, Pt, gas) for t, m in zip(layout, masses)]
    incidence = math.radians(v(bl["design_incidence"]))
    ctx["kappa1"] = [r.beta1 - incidence for r in inlet]
    ctx["supersonic"] = [r.M1rel > 1.0 for r in inlet]
    f_sonic = sonic_span(inlet[0].V1, omega, Tt, ann, gas)
    out = design(layout, {"outer": inp["FPR"], "inner": inp["pr_fan_inner"]},
                 {"outer": inp["eta_fan_outer"], "inner": inp["eta_fan_inner"]}, masses, ctx, ann)
    blade, sol = out["blade"], out["solution"]
    tubes, res = sol.tubes, sol.results
    n_inner = sum(1 for t in layout if t["stream"] == "inner")

    rows = []
    for i, (t, tube, r) in enumerate(zip(layout, tubes, res)):
        fam = bp.family_at(fits, t["span"])
        sup = ctx["supersonic"][i]
        lim = df_limit(bl, t["span"])
        floor = r67_solidity(ctx["r67"], t["span"]) if sup else v(bl["solidity_min"])
        df_ok = r.diffusion_factor <= lim + DF_TOL
        sol_ok = tube.solidity >= floor - SIGMA_TOL
        rows.append({
            "name": t["name"], "stream": t["stream"], "span_fraction": round(t["span"], 4),
            "r1_m": round(t["r1"], 5), "r2_m": round(tube.r2, 5),
            "A1_m2": round(t["A1"], 5), "A2_m2": round(tube.A2, 5), "mass_flow_kg_s": round(r.mass_flow, 4),
            "U1_m_s": round(r.U1, 2), "U2_m_s": round(tube.r2 * omega, 2), "V1_m_s": round(r.V1, 2),
            "W1_m_s": round(r.W1, 2), "beta1_deg": deg(r.beta1), "M1rel": round(r.M1rel, 4),
            "Vm2_m_s": round(r.Vm2, 2), "Vt2_m_s": round(r.Vt2, 2), "rVt2_m2_s": round(tube.r2 * r.Vt2, 3),
            "V2_m_s": round(math.hypot(r.Vm2, r.Vt2), 2),
            "W2_m_s": round(r.W2, 2), "beta2_deg": deg(r.beta2), "M2rel": round(r.M2rel, 4),
            "Vm2_over_Vm1": round(r.Vm2 / r.V1, 4),
            "kappa1_deg": deg(tube.kappa1), "kappa2_deg": deg(tube.kappa2), "camber_deg": deg(tube.kappa1 - tube.kappa2),
            "incidence_deg": deg(r.incidence), "deviation_deg": deg(r.deviation),
            "solidity": round(tube.solidity, 4), "pitch_m": round(pitch(t, ctx), 5), "chord_m": round(tube.endwall.chord, 5),
            "t_c": round(fam["tc"], 5), "front_camber_share": round(fam["front"], 4), "x_max": round(fam["x_max"], 4),
            "covered_fraction": round(tube.covered_fraction, 4), "ss_turn_deg": deg(tube.ss_turn),
            "diffusion_factor": round(r.diffusion_factor, 4), "D_eq": round(r.deq, 4),
            "R_AM9": {"zone": "supersonic (solidity floor)" if sup else "subsonic (Lieblein DF limit)",
                      "DF_limit": round(lim, 4) if not sup else None,
                      "DF_limit_info": round(lim, 4),
                      "solidity_floor": round(floor, 4),
                      "DF_check": ("pass" if df_ok else "fail") if not sup else "not applied",
                      "solidity_check": "pass" if sol_ok else "fail",
                      "rule": "pass" if (sol_ok if sup else df_ok) else "fail"},
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
                         "efficiency_bias_meanline_minus_budget": avg["efficiency"] - eta_b,
                         "Tt_ratio_meanline": avg["Tt_ratio"], "Tt_exit_K": Tt_exit,
                         "power_MW": avg["mass_flow"] * gas.cp * (Tt_exit - Tt) / 1e6}
    overall = mass_averaged(res, gas)
    m_all = streams["outer"]["mass_flow_kg_s"] + streams["inner"]["mass_flow_kg_s"]
    tr_b = sum(s["mass_flow_kg_s"] * s["Tt_exit_K"] for s in streams.values()) / (m_all * Tt)
    pr_b = (sum(s["mass_flow_kg_s"] * pr ** (1 / gas.k) for s, pr in
                ((streams["outer"], inp["FPR"]), (streams["inner"], inp["pr_fan_inner"]))) / m_all) ** gas.k
    eta_overall_budget = (pr_b ** (1 / gas.k) - 1) / (tr_b - 1)

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
    rule_fail = [row["name"] for row in rows if row["R_AM9"]["rule"] == "fail"]
    vt = out["vortex"]
    off = blade["offsets"]
    k2_total = list(blade["kappa2"])
    k2_total[0] += off["inner"]
    k2_total[4] += off["outer"] - off["inner"]
    work = [gas.cp * Tt * (r.Tt_ratio - 1) for r in res]
    tip = tip_region(p, res, layout, gas)
    controlled = tip["decision"].startswith("controlled vortex required")
    if controlled:
        raise NotImplementedError("tip check asks for a controlled vortex (R-AM.12 / tip_check); not implemented")
    diag = mass_diagnosis(blade, layout, out["history"][-1]["chord_needs_m"], ctx,
                          v(p["mechanical"]["blade_set_mass_check"]) / ctx["blades"])

    return {
        "description": "M1 fan rotor design at the M0 design point (SLS ISA, max take-off), M1 step 4f smooth "
                       "blade; generated by engine/M1_inlet_fan/analysis/fan_design.py, do not edit",
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
            "shock_expansion": "R-AM.11 section profile: ss_turn = kappa1 - suction-surface angle of the MCA "
                               "section at the covered-passage entrance (blade_profile.py)",
            "blade_height_m": round(ann["blade_height"], 5), "blade_height_tag": "T (mean of inlet and exit annulus heights)",
            "tip_clearance_m": ctx["tip_clearance"], "tip_clearance_tag": "T (fan_params.yaml losses)",
            "efficiency_rule": "R-AM.10 / ADR-015: achieved efficiencies = budget [T]; meanline efficiency = information "
                               "[H, unvalidated model]",
            "physical_check": "tools.meanline RotorSolution.physical / issues (no local guard)",
        },
        "blade": {
            "tag": "H (parameters from the design loop; forms T)",
            "span_variable": "f = (r1 - r_hub1) / (r_tip1 - r_hub1), inlet radius of the tube centre",
            "chord_m_coefficients": [round(c, 6) for c in blade["chord"]],
            "chord_form": "chord(f) = c0 + c1 f + c2 f^2 [T form]; lowest mean chord with every tube at or above "
                          "its R-AM.9 need (linear programme)",
            "kappa2_deg_coefficients_shape": [round(math.degrees(c), 5) for c in blade["kappa2"]],
            "kappa2_offsets_deg": {k: round(math.degrees(x), 5) for k, x in blade["offsets"].items()},
            "kappa2_deg_coefficients_total": [round(math.degrees(c), 5) for c in k2_total],
            "kappa2_form": "kappa2(f) = k0 + k1 f + k2 f^2 + k3 f^3 + k4 B(f) (least squares over the tubes at their "
                           "vortex targets) + delta_inner (1 - B(f)) + delta_outer B(f); B = C2 quintic smoothstep "
                           f"from f_split + {ctx['blend_start']} to f_split + {ctx['blend_start'] + ctx['blend_width']} "
                           f"(f_split {round(ctx['f_split'], 5)}) [T]; total coefficients include the offsets",
            "kappa1_form": "kappa1 = atan(omega r1 / V1) - design incidence (uniform axial inlet, V1 = "
                           f"{round(inlet[0].V1, 3)} m/s) [H]; incidence {v(bl['design_incidence'])} deg [T]",
            "profile_family": "MCA (R-AM.11): two-arc camber line, transition at chord fraction "
                              f"{bp.X_TRANSITION} [T], parabolic thickness [T]",
            "profile_fits_rotor67": {"front_camber_share": [round(c, 6) for c in fits["coefficients"]["front"]],
                                     "t_c": [round(c, 6) for c in fits["coefficients"]["tc"]],
                                     "x_max": [round(c, 6) for c in fits["coefficients"]["x_max"]],
                                     "rms": {k: round(x, 5) for k, x in fits["rms"].items()},
                                     "tag": "H fit of KS sections (Table I), used for the M1 fan as T analogue"},
            "vortex": {"law": "free_vortex",
                       "law_statement": "free vortex in each stream (r Vt2 constant, dh0 constant) with the C2 "
                                        "splitter blend; no controlled vortex: tip-region meanline eta of this fan "
                                        f"minus the Rotor 67 model {tip['bands'][0]['gap_M1_minus_rotor67']:+.4f} "
                                        f"(limit -{tip['eta_gap_limit']}), tip_region.decision [H, rule T]",
                       "controlled_vortex": controlled,
                       "form": "free vortex (dh0 = U2 Vt2 constant, r Vt2 constant without inlet swirl) in each stream "
                               "[G], blended across the splitter: dh0(f) = dh_inner (1 - B(f)) + dh_outer B(f) [T blend]",
                       "dh_inner_J_kg": round(vt["dh_inner"], 1), "dh_outer_J_kg": round(vt["dh_outer"], 1),
                       "tag": "H (dh_inner, dh_outer solved for the achieved stream levels of the last pass)",
                       "tube_work_design_J_kg": [round((x - 1) * gas.cp * Tt, 1) for x in vt["targets"]],
                       "tube_work_equilibrium_J_kg": [round(x, 1) for x in work],
                       "note": "[H] the fixed blade sets the actual work in radial equilibrium; the design values are "
                               "the vortex targets the kappa2 shape was fitted to"},
        },
        "profile_check_rotor67": {
            "tag": "H (builder) vs H from KS geometry (rotor67.build_tubes ss_turn)",
            "note": "ss_turn of the profile builder with the Rotor 67 metal angles and covered fractions; "
                    "'sections' = family parameters interpolated between the Table I sections, 'smooth_fit' = the "
                    "spanwise fits used for the M1 fan, 'dca' = front share 0.5 and x_max 0.5 (plain DCA). Only "
                    "the supersonic streamlines (M1rel > 1, span above about 0.45) carry a shock loss",
            **bp.rotor67_check(fits)},
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
            "splitter_span_fraction": round((ann["r_split1"] - ann["r_hub1"]) / (ann["r_tip1"] - ann["r_hub1"]), 5),
        },
        "convergence": {"converged": out["converged"],
                        "outer_passes": sum(1 for h in out["history"] if h.get("pass", 0) >= 1),
                        "scheme": "pass: stream levels from the target PR and the stream eta (budget in pass 0, then "
                                  "meanline); design-mode radial equilibrium at the vortex targets; R-AM.9 chord needs, "
                                  "lowest quadratic chord with the taper bound, kappa2 basis fit (cubic + splitter "
                                  "blend); 2x2 Newton on the blended stream offsets with fixed-blade solve_rotor_re "
                                  "until each stream PR = target (physical solutions only); repeat until the reshaped "
                                  "chord and kappa2 are stable",
                        "tolerances": {"stream_PR_newton": NEWTON_TOL, "stream_PR_final": PR_TOL,
                                       "solidity_search": SIGMA_TOL, "chord_stable_m": CHORD_STABLE,
                                       "kappa2_stable_deg": round(math.degrees(KAPPA2_STABLE), 4),
                                       "fd_step_deg": round(math.degrees(FD_STEP), 4)},
                        "final_check": out["final_check"],
                        "radial_equilibrium_residual": float(f"{sol.residual:.2e}"),
                        "history": out["history"]},
        "summary": {
            "tag": "H",
            "tip_M1rel": round(tip_mrel, 4), "U_tip_m_s": round(omega * ann["r_tip1"], 2),
            "sonic_span_fraction": round(f_sonic, 4),
            "vortex_law": "free vortex per stream, C2 splitter blend (no controlled vortex; blade.vortex.law_statement)",
            "DF_min": round(min(dfs), 4), "DF_max": round(max(dfs), 4),
            "loading_rule": "R-AM.9 (step 4e): span below the sonic span of this fan: DF <= "
                            f"{v(bl['df_limit_hub'])} (hub) to {v(bl['df_limit_tip'])} (tip), linear in span [T] "
                            "(NASA SP-36 PDF p. 286 [K]); above: solidity >= Rotor 67 solidity "
                            f"({ctx['r67']['hub']} hub to {ctx['r67']['tip']} tip, linear, Strazisar p. 2 [KS])",
            "R_AM9_check": "pass" if not rule_fail else "fail", "R_AM9_failed_tubes": rule_fail,
            "solidity_min": round(min(sols), 4), "solidity_max": round(max(sols), 4),
            "chord_min_m": min(chords), "chord_max_m": max(chords),
            "loading_coefficient": loading_coefficients(inp, omega, ann, gas),
            "outer": {k: round(x, 5) for k, x in streams["outer"].items()},
            "inner": {k: round(x, 5) for k, x in streams["inner"].items()},
            "overall_meanline": {k: round(x, 5) for k, x in overall.items()},
            "overall_efficiency_budget": round(eta_overall_budget, 5),
            "overall_efficiency_bias_meanline_minus_budget": round(overall["efficiency"] - eta_overall_budget, 5),
            "efficiency_note": "efficiency_budget is the achieved value [T, ADR-015]; efficiency_meanline is "
                               "information only [H, unvalidated model: about 7 points low on Rotor 67 near peak]; "
                               "overall budget efficiency from the mass-averaged budget Tt ratio and the energy-"
                               "averaged target PR [H]",
            "not_modelled": "OGV loss, inlet recovery, streamline curvature, incidence-dependent deviation and loss",
        },
        "smoothness": smoothness(rows, n_inner),
        "tubes": rows,
        "kappa2_blend_check": kappa2_blend_check(blade, ctx, ann),
        "tip_region": tip,
        "mechanical": mechanical(p, ann, omega, blade, ctx, diag),
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
    s, c, b = result["summary"], result["convergence"], result["blade"]
    print(f"converged {c['converged']} in {c['outer_passes']} passes, {c['final_check']}")
    print(f"chord {b['chord_m_coefficients']}  kappa2 total {b['kappa2_deg_coefficients_total']}  "
          f"offsets {b['kappa2_offsets_deg']}  vortex {b['vortex']['dh_inner_J_kg']} / {b['vortex']['dh_outer_J_kg']}")
    print(f"tip M1rel {s['tip_M1rel']} sonic span {s['sonic_span_fraction']} DF {s['DF_min']}..{s['DF_max']}  "
          f"R-AM.9 {s['R_AM9_check']} {s['R_AM9_failed_tubes']}  psi {s['loading_coefficient']['psi_tip_M1']} "
          f"vs R67 {s['loading_coefficient']['psi_tip_rotor67']}")
    for r in result["tubes"]:
        q = r["R_AM9"]
        print(f"{r['name']} {r['stream']:5} f {r['span_fraction']:.3f} M1rel {r['M1rel']:.3f} c {r['chord_m']:.4f} "
              f"sig {r['solidity']:.3f}/{q['solidity_floor']:.3f} t/c {r['t_c']:.4f} k1 {r['kappa1_deg']:6.2f} "
              f"k2 {r['kappa2_deg']:6.2f} ss {r['ss_turn_deg']:5.2f} DF {r['diffusion_factor']:.3f}/{q['DF_limit_info']:.3f} "
              f"PR {r['Pt_ratio']:.4f} eta {r['efficiency_meanline']:.4f} [{q['zone']}: {q['rule']}] {r['notes']}")
    for k in ("outer", "inner"):
        print(k, s[k])
    print("overall eta budget", s["overall_efficiency_budget"], "bias", s["overall_efficiency_bias_meanline_minus_budget"])
    m = result["mechanical"]
    print(f"root stress {m['root_stress_MPa']} MPa (taper {m['taper_ratio']}), allowable {m['allowable_MPa']}, "
          f"margin {m['margin']}; chord root {m['chord_root_m']} tip {m['chord_tip_m']}, thickness root "
          f"{m['thickness_root_mm']} mm; mass {m['blade_mass']['per_blade_kg']} kg x {m['blade_mass']['blade_count']} = "
          f"{m['blade_mass']['set_kg']} kg (check {m['blade_mass']['check_set_kg']})")
    d = m["mass_diagnosis"]
    print(f"mass/check {d['mass_over_check']}; dominant chord driver: {d['dominant_chord_driver']} "
          f"(-{d['dominant_chord_driver_mass_reduction_kg']} kg)")
    for x in d["variants"]:
        print("  ", x)
    print("kappa2 blend", result["kappa2_blend_check"])
    print("tip region", result["tip_region"]["bands"], result["tip_region"]["decision"])
    for row in result["budget_check"]:
        print(f"{row['result']:4} {row['item']}: achieved {row['achieved']:.5g} budget {row['budget']} dev {row.get('deviation', '')}")


if __name__ == "__main__":
    main()
