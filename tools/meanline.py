"""Streamline (stream-tube) analysis of one compressor or fan blade row, reusable by M1, M2 and M3.

Method: engine/M1_inlet_fan/rules/aero_method.md, steps 1-7, for a rotor without inlet swirl.
solve_tube() solves one stream tube with given inlet and exit radii and areas. solve_rotor() splits the
flow by inlet area and solves each tube on its own (no radial equilibrium). solve_rotor_re() adds radial
equilibrium (see there). Perfect gas with constant gamma (cold air) [G]. Angles in radians, measured from
the meridional direction, positive in the direction of rotation. SI units.

Correlations (tags as used here):
- Deviation: Carter's rule, delta = m * camber / sqrt(solidity), m = 0.23 (2a/c)^2 + kappa2/500 deg
  with a/c = 0.5 (circular-arc camber line) [G].
- Profile loss: Lieblein equivalent diffusion ratio D_eq [KS, Abrisha eq. 4.9; Sjögren eq. 2.11] and
  the wake momentum thickness fit theta/c = 0.004 (1 + 3.1 (D_eq - 1)^2 + 0.4 (D_eq - 1)^8) [G, Aungier
  2003 fit of Lieblein's data; not in the M1 source set].
- Shock loss: normal shock at the passage Mach number = mean of inlet relative Mach and the suction-
  surface Mach after a Prandtl-Meyer expansion to the covered-passage entrance (Schwenk / Miller-
  Lewis-Hartmann type) [KS, Sjögren p. 24; Visentin p. 32]; taper 0.8 < M1rel < 1.0 [KS, Sjögren p. 24].
  Expansion angle = inlet relative flow angle minus the suction-surface angle at the covered-passage
  entrance: from the blade geometry when the tube gives `ss_turn` (kappa1 minus that suction-surface angle),
  otherwise incidence + covered fraction x camber (camber taken as linear along the chord [T]). M1 step 4c:
  the linear-camber estimate over-predicts the measured pre-shock Mach of Rotor 67 (TP-2879 laser data).
  With `subsonic_shock_taper` False (M1 step 4d) there is no shock loss for a subsonic inlet relative flow
  (M1rel <= 1): TP-2879 Fig. 30 shows no passage shock at 70 % span from the tip, M1rel about 0.93.
- Endwall loss (only for tubes given `Endwall` data): Howell's annulus drag C_Da = 0.020 s/h and secondary
  drag C_Ds = 0.018 C_L^2, with the cascade lift coefficient C_L = 2 cos(beta_m) (tan beta1 - tan beta2) / sigma
  (profile drag term neglected), turned into a total pressure loss coefficient on the inlet dynamic head,
  sigma C_D cos^2(beta1) / cos^3(beta_m). Textbook form: Howell (1945) as given in Saravanamuttoo, Rogers, Cohen,
  Straznicky, Gas Turbine Theory (axial compressor design chapter: C_DA = 0.020 s/h, C_DS = 0.018 C_L^2) and
  Dixon & Hall, Fluid Mechanics and Thermodynamics of Turbomachinery (compressor cascade chapter: lift, drag
  and loss coefficient relations). [G]: these books are not in the M1 source set and were not re-read here;
  Howell is the secondary loss model of SATURN (Visentin p. 32) [KS]. The row value is spread over the span
  with the weight 3 (2f - 1)^2 (mean 1, largest at both walls) [T, after the parabolic endwall loss
  distribution of SC90C, Sjögren p. 22].
- Tip clearance loss: Lakshminarayana's efficiency debit d_eta = 0.7 (tau/h) psi / cos(beta_m)
  (1 + 10 sqrt((tau/c) AR / (psi cos(beta_m)))), psi = dh0 / U^2, AR = h/c. Form and coefficients 0.7 and 10:
  Lakshminarayana B., "Methods of predicting the tip clearance effects in axial flow turbomachinery",
  J. Basic Eng. 92 (1970) 467-482, also in his book Fluid Dynamics and Heat Transfer of Turbomachinery
  (1996) [G: not in the M1 source set; Visentin p. 32 names Yaras-Sjolander for SATURN]. Applied only in the
  tip region, span fraction f >= TIP_REGION_START = 0.8: measured Rotor 37 efficiency falls sharply above 80 %
  span from tip clearance flow, shock and casing boundary layer (Zanoni p. 7, PDF p. 16) [KS extent]; uniform
  weight 1 / 0.2 = 5 inside the region (mean 1 over the span) [T shape]. Applied as the total pressure loss of
  the matching entropy rise, ds = cp d_eta dTt / Tt2 [G]. (M1 step 4: weight 3 f^2 over the whole span.)
- Radial equilibrium (solve_rotor_re): simple radial equilibrium with enthalpy and entropy gradients,
  dh0/dr = T ds/dr + Vm dVm/dr + (Vt/r) d(r Vt)/dr [G, standard throughflow relation, e.g. Dixon & Hall,
  three-dimensional flows chapter], at the rotor inlet and exit. Streamline curvature and slope terms are
  neglected (limitation: the meridional flow is taken as parallel to the axis at each station).
"""

import math
from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class Gas:
    gamma: float = 1.4  # [G] cold air
    R: float = 287.0  # J/(kg K) [G]

    @property
    def cp(self) -> float:
        return self.gamma * self.R / (self.gamma - 1)

    @property
    def k(self) -> float:
        return self.gamma / (self.gamma - 1)


def mass_flux_function(M: float, gas: Gas) -> float:
    """m sqrt(R Tt) / (A Pt) for Mach M."""
    g = gas.gamma
    return math.sqrt(g) * M * (1 + (g - 1) / 2 * M * M) ** (-(g + 1) / (2 * (g - 1)))


def mach_from_flux(flux: float, gas: Gas) -> float:
    """Subsonic Mach number for a mass flux function value (bisection)."""
    if flux > mass_flux_function(1.0, gas):
        raise ValueError("stream tube is choked")
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if mass_flux_function(mid, gas) < flux else (lo, mid)
    return (lo + hi) / 2


def prandtl_meyer(M: float, gas: Gas) -> float:
    g = gas.gamma
    a = math.sqrt((g + 1) / (g - 1))
    return a * math.atan(math.sqrt((M * M - 1) / a / a)) - math.atan(math.sqrt(M * M - 1))


def mach_from_prandtl_meyer(nu: float, gas: Gas) -> float:
    lo, hi = 1.0, 5.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if prandtl_meyer(mid, gas) < nu else (lo, mid)
    return (lo + hi) / 2


def normal_shock_pt_ratio(M: float, gas: Gas) -> float:
    """Total pressure ratio across a normal shock at upstream Mach M (1 for M <= 1)."""
    if M <= 1.0:
        return 1.0
    g = gas.gamma
    a = ((g + 1) * M * M / ((g - 1) * M * M + 2)) ** (g / (g - 1))
    b = ((g + 1) / (2 * g * M * M - (g - 1))) ** (1 / (g - 1))
    return a * b


def carter_deviation(kappa1: float, kappa2: float, solidity: float) -> float:
    m = 0.23 * (2 * 0.5) ** 2 + math.degrees(kappa2) / 500
    return m * abs(kappa1 - kappa2) / math.sqrt(solidity)


def lieblein_deq(beta1: float, beta2: float, W1: float, W2: float, solidity: float) -> float:
    return W1 / W2 * (1.12 + 0.61 * math.cos(beta1) ** 2 / solidity * (math.tan(beta1) - math.tan(beta2)))


def profile_loss(beta1: float, beta2: float, deq: float, solidity: float) -> float:
    """Total pressure loss coefficient (Pt1rel - Pt2rel) / (Pt1rel - p1) from the wake momentum thickness."""
    theta_c = 0.004 * (1 + 3.1 * (deq - 1) ** 2 + 0.4 * (deq - 1) ** 8)
    return 2 * theta_c * solidity / math.cos(beta2) * (math.cos(beta1) / math.cos(beta2)) ** 2


def diffusion_factor(W1: float, W2: float, r1: float, r2: float, Wt1: float, Wt2: float, solidity: float) -> float:
    """Lieblein diffusion factor with radius change: 1 - W2/W1 + (r1 Wt1 - r2 Wt2) / ((r1 + r2) sigma W1)."""
    return 1 - W2 / W1 + (r1 * Wt1 - r2 * Wt2) / ((r1 + r2) * solidity * W1)


@dataclass(frozen=True)
class LossMultipliers:
    """One multiplier per loss mechanism (ADR-014); 1.0 = the correlation as written."""
    profile: float = 1.0
    shock: float = 1.0
    endwall: float = 1.0
    tip: float = 1.0


@dataclass(frozen=True)
class Endwall:
    """Blade-row data for the endwall and tip clearance losses of one tube: span fraction of the tube centre
    (0 hub, 1 casing), blade height h, chord c and running tip clearance tau of the row (m)."""
    span_fraction: float
    blade_height: float
    chord: float
    tip_clearance: float


def howell_endwall_loss(beta1: float, beta2: float, solidity: float, pitch: float, height: float) -> float:
    """Row loss coefficient of annulus + secondary drag (Howell), on the inlet relative dynamic head."""
    beta_m = math.atan((math.tan(beta1) + math.tan(beta2)) / 2)
    c_l = 2 * math.cos(beta_m) * (math.tan(beta1) - math.tan(beta2)) / solidity
    c_d = 0.020 * pitch / height + 0.018 * c_l * c_l
    return solidity * c_d * math.cos(beta1) ** 2 / math.cos(beta_m) ** 3


def tip_clearance_debit(beta1: float, beta2: float, psi: float, ew: Endwall) -> float:
    """Row efficiency debit of tip leakage (Lakshminarayana); 0 without clearance or work."""
    if ew.tip_clearance <= 0 or psi <= 0:
        return 0.0
    cos_m = math.cos(math.atan((math.tan(beta1) + math.tan(beta2)) / 2))
    aspect = ew.blade_height / ew.chord
    tau_h, tau_c = ew.tip_clearance / ew.blade_height, ew.tip_clearance / ew.chord
    return 0.7 * tau_h * psi / cos_m * (1 + 10 * math.sqrt(tau_c * aspect / (psi * cos_m)))


def endwall_weight(f: float) -> float:
    return 3 * (2 * f - 1) ** 2


TIP_REGION_START = 0.8  # span fraction where the tip clearance loss region starts [KS, Zanoni p. 7]


def tip_weight(f: float) -> float:
    return 1 / (1 - TIP_REGION_START) if f >= TIP_REGION_START else 0.0


@dataclass
class Tube:
    """One stream tube through a rotor. Geometry at the blade row: metal angles kappa1/kappa2,
    solidity, and the fraction of meridional chord to the covered-passage entrance (shock model)."""
    name: str
    r1: float
    r2: float
    A1: float
    A2: float
    kappa1: float
    kappa2: float
    solidity: float
    covered_fraction: float
    endwall: Endwall | None = None  # None: no endwall or tip clearance loss
    ss_turn: float | None = None  # kappa1 - suction-surface angle at the covered-passage entrance (geometry)
    multipliers: LossMultipliers = LossMultipliers()
    subsonic_shock_taper: bool = True  # shock loss tapered in for 0.8 < M1rel < 1 (Sjögren p. 24); False: M1rel > 1 only


@dataclass
class TubeResult:
    name: str
    mass_flow: float
    U1: float
    V1: float
    W1: float
    beta1: float
    M1rel: float
    incidence: float
    deviation: float
    beta2: float
    Vm2: float
    Vt2: float
    W2: float
    M2rel: float
    diffusion_factor: float
    deq: float
    loss_profile: float
    loss_shock: float
    M_passage: float
    Tt_ratio: float
    Pt_ratio: float
    efficiency: float
    notes: list[str] = field(default_factory=list)
    loss_endwall: float = 0.0
    loss_tip: float = 0.0


def solve_tube(tube: Tube, mass_flow: float, omega: float, Tt1: float, Pt1: float, gas: Gas = Gas()) -> TubeResult:
    """Rotor stream tube without inlet swirl: inlet state from continuity, Euler work, Carter
    deviation, profile + shock loss, exit state from continuity (fixed-point on exit density)."""
    k = gas.k
    notes = []
    # Inlet (axial, uniform in the tube)
    M1 = mach_from_flux(mass_flow * math.sqrt(gas.R * Tt1) / (tube.A1 * Pt1), gas)
    T1 = Tt1 / (1 + (gas.gamma - 1) / 2 * M1 * M1)
    p1 = Pt1 * (T1 / Tt1) ** k
    a1 = math.sqrt(gas.gamma * gas.R * T1)
    V1 = M1 * a1
    U1 = omega * tube.r1
    W1 = math.hypot(V1, U1)
    beta1 = math.atan2(U1, V1)
    M1rel = W1 / a1
    Tt1rel = T1 + W1 * W1 / (2 * gas.cp)
    Pt1rel = p1 * (Tt1rel / T1) ** k
    incidence = beta1 - tube.kappa1

    # Exit relative flow angle
    deviation = carter_deviation(tube.kappa1, tube.kappa2, tube.solidity)
    beta2 = tube.kappa2 + deviation

    # Shock loss (independent of exit state)
    loss_shock, M_pass = 0.0, M1rel
    if M1rel > (0.8 if tube.subsonic_shock_taper else 1.0):
        M_up = max(M1rel, 1.0)
        if tube.ss_turn is None:
            turn = max(incidence, 0.0) + tube.covered_fraction * (tube.kappa1 - tube.kappa2)
        else:
            turn = max(incidence + tube.ss_turn, 0.0)
        M_ss = mach_from_prandtl_meyer(prandtl_meyer(M_up, gas) + turn, gas)
        M_pass = (M_up + M_ss) / 2
        pt_ratio = normal_shock_pt_ratio(M_pass, gas)
        taper = min(1.0, (M1rel - 0.8) / 0.2)
        loss_shock = tube.multipliers.shock * taper * (1 - pt_ratio) * Pt1rel / (Pt1rel - p1)

    # Exit: meridional velocity from continuity, on the subsonic branch of the mass flux curve
    U2 = omega * tube.r2
    Tt2rel = Tt1rel + (U2 * U2 - U1 * U1) / (2 * gas.cp)
    Pt2rel_ideal = Pt1rel * (Tt2rel / Tt1rel) ** k

    ew = tube.endwall
    loss_ew = 0.0
    if ew is not None:
        pitch = ew.chord / tube.solidity
        loss_ew = tube.multipliers.endwall * endwall_weight(ew.span_fraction) * howell_endwall_loss(
            beta1, beta2, tube.solidity, pitch, ew.blade_height)

    def tip_loss(Vm2):
        """Loss coefficient of the tip clearance efficiency debit at this exit state."""
        if ew is None:
            return 0.0
        work = U2 * (U2 - Vm2 * math.tan(beta2))  # Euler work, no inlet swirl
        if work <= 0:
            return 0.0
        d_eta = tube.multipliers.tip * tip_weight(ew.span_fraction) * tip_clearance_debit(beta1, beta2, work / (U2 * U2), ew)
        Tt2 = Tt1 + work / gas.cp
        ds = gas.cp * d_eta * (Tt2 - Tt1) / Tt2
        return (1 - math.exp(-ds / gas.R)) * Pt2rel_ideal / (Pt1rel - p1)

    def exit_state(Vm2):
        Wt2 = Vm2 * math.tan(beta2)
        W2 = math.hypot(Vm2, Wt2)
        deq = lieblein_deq(beta1, beta2, W1, W2, tube.solidity)
        loss_p = tube.multipliers.profile * profile_loss(beta1, beta2, deq, tube.solidity)
        loss_t = tip_loss(Vm2)
        Pt2rel = Pt2rel_ideal - (loss_p + loss_shock + loss_ew + loss_t) * (Pt1rel - p1)
        T2 = Tt2rel - W2 * W2 / (2 * gas.cp)
        if T2 <= 0 or Pt2rel <= 0:
            return None
        rho2 = Pt2rel * (T2 / Tt2rel) ** k / (gas.R * T2)
        return rho2 * Vm2 * tube.A2, deq, loss_p, Pt2rel

    vm_max = math.sqrt(2 * gas.cp * Tt2rel) * abs(math.cos(beta2))
    grid = [vm_max * (i + 1) / 400 for i in range(399)]
    fluxes = [(vm, exit_state(vm)) for vm in grid]
    fluxes = [(vm, s) for vm, s in fluxes if s is not None]
    vm_peak, s_peak = max(fluxes, key=lambda x: x[1][0])
    if s_peak[0] < mass_flow:
        notes.append("exit choked: required mass flow above the tube's maximum; exit at the choke point")
        Vm2 = vm_peak
    else:
        # lowest meridional velocity with a valid exit state (very low velocity means unbounded loss)
        lo, hi = next(vm for vm, _ in fluxes if vm <= vm_peak), vm_peak
        for _ in range(100):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if exit_state(mid)[0] < mass_flow else (lo, mid)
        Vm2 = (lo + hi) / 2
    _, deq, loss_profile, Pt2rel = exit_state(Vm2)
    Wt2 = Vm2 * math.tan(beta2)
    W2 = math.hypot(Vm2, Wt2)
    Vt2 = U2 - Wt2
    T2 = Tt2rel - W2 * W2 / (2 * gas.cp)
    Tt2 = T2 + (Vm2 * Vm2 + Vt2 * Vt2) / (2 * gas.cp)
    Pt2 = Pt2rel * (Tt2 / Tt2rel) ** k
    a2 = math.sqrt(gas.gamma * gas.R * T2)
    TR, PR = Tt2 / Tt1, Pt2 / Pt1
    eta = (PR ** (1 / k) - 1) / (TR - 1) if TR > 1 else float("nan")
    DF = diffusion_factor(W1, W2, tube.r1, tube.r2, U1, Wt2, tube.solidity)
    return TubeResult(tube.name, mass_flow, U1, V1, W1, beta1, M1rel, incidence, deviation, beta2, Vm2, Vt2,
                      W2, W2 / a2, DF, deq, loss_profile, loss_shock, M_pass, TR, PR, eta, notes,
                      loss_endwall=loss_ew, loss_tip=tip_loss(Vm2))


def solve_rotor(tubes: list[Tube], mass_flow: float, omega: float, Tt1: float, Pt1: float,
                gas: Gas = Gas()) -> list[TubeResult]:
    """Split the mass flow over the tubes in proportion to inlet area (uniform inlet) and solve each."""
    total_area = sum(t.A1 for t in tubes)
    return [solve_tube(t, mass_flow * t.A1 / total_area, omega, Tt1, Pt1, gas) for t in tubes]


def mass_averaged(results: list[TubeResult], gas: Gas = Gas()) -> dict:
    """Mass-averaged total temperature ratio, energy-averaged total pressure ratio (mass average of
    PR^((g-1)/g)), and the efficiency from these two."""
    m = sum(r.mass_flow for r in results)
    TR = sum(r.mass_flow * r.Tt_ratio for r in results) / m
    PR = (sum(r.mass_flow * r.Pt_ratio ** (1 / gas.k) for r in results) / m) ** gas.k
    return {"mass_flow": m, "Tt_ratio": TR, "Pt_ratio": PR, "efficiency": (PR ** (1 / gas.k) - 1) / (TR - 1)}


@dataclass
class RotorSolution:
    """Radial equilibrium solution: tubes with their equilibrium exit radii and areas, the tube results,
    and the convergence record (residual = largest relative exit-area change of the last iteration)."""
    tubes: list[Tube]
    results: list[TubeResult]
    iterations: int
    converged: bool
    residual: float


def exit_state(r: TubeResult, Tt1: float, Pt1: float, gas: Gas = Gas()) -> dict:
    """Exit static state, total enthalpy and entropy (relative to the inlet) of a tube result."""
    Tt2 = r.Tt_ratio * Tt1
    T2 = Tt2 - (r.Vm2 ** 2 + r.Vt2 ** 2) / (2 * gas.cp)
    p2 = r.Pt_ratio * Pt1 * (T2 / Tt2) ** gas.k
    s = gas.cp * math.log(r.Tt_ratio) - gas.R * math.log(r.Pt_ratio)
    return {"T": T2, "rho": p2 / (gas.R * T2), "h0": gas.cp * Tt2, "s": s}


def area_centre_radii(areas: list[float], r_hub: float, r_tip: float) -> list[float]:
    """Radii of the area centres of tubes laid side by side from hub to tip, in the given order. The
    areas are flow areas (net of blockage) and are scaled to the geometric annulus."""
    scale = math.pi * (r_tip ** 2 - r_hub ** 2) / sum(areas)
    out, below = [], 0.0
    for a in areas:
        out.append(math.sqrt(r_hub ** 2 + (below + a * scale / 2) / math.pi))
        below += a * scale
    return out


def equilibrium_areas(results: list[TubeResult], radii: list[float], area_total: float, Tt1: float, Pt1: float,
                      gas: Gas = Gas()) -> list[float]:
    """Exit flow areas (same order as `results`) that satisfy simple radial equilibrium with the tubes'
    current exit h0, s, Vt and density and carry their mass flows in `area_total`.

    Between neighbouring tubes j, j+1 (by radius): Vm^2 changes by
    2 [dh0 - T ds - (Vt/r) d(r Vt)], with T, Vt, r the means of the pair. The hub meridional velocity is
    found so that sum(m / (rho Vm)) equals area_total."""
    order = sorted(range(len(results)), key=lambda i: radii[i])
    st = [exit_state(results[i], Tt1, Pt1, gas) for i in order]
    rs = [radii[i] for i in order]
    vt = [results[i].Vt2 for i in order]
    m = [results[i].mass_flow for i in order]
    rise = [0.0]
    for j in range(len(order) - 1):
        T, v, r = (st[j]["T"] + st[j + 1]["T"]) / 2, (vt[j] + vt[j + 1]) / 2, (rs[j] + rs[j + 1]) / 2
        d = (st[j + 1]["h0"] - st[j]["h0"]) - T * (st[j + 1]["s"] - st[j]["s"]) - v / r * (rs[j + 1] * vt[j + 1] - rs[j] * vt[j])
        rise.append(rise[-1] + 2 * d)

    def area(vm0):
        return sum(mj / (s["rho"] * math.sqrt(vm0 ** 2 + q)) for mj, s, q in zip(m, st, rise))

    lo = math.sqrt(max(0.0, -min(rise))) + 1e-6
    hi = lo + 1.0
    while area(hi) > area_total:
        hi *= 2
    if area(lo) < area_total:
        raise ValueError("radial equilibrium: no hub velocity fits the exit area")
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if area(mid) > area_total else (lo, mid)
    vm0 = (lo + hi) / 2
    out = [0.0] * len(order)
    for j, i in enumerate(order):
        out[i] = m[j] / (st[j]["rho"] * math.sqrt(vm0 ** 2 + rise[j]))
    return out


def solve_rotor_re(tubes: list[Tube], mass_flow: float, omega: float, Tt1: float, Pt1: float,
                   exit_hub: float, exit_tip: float, gas: Gas = Gas(), relax: float = 0.1, tol: float = 1e-5,
                   max_iter: int = 200) -> RotorSolution:
    """Rotor with simple radial equilibrium at inlet and exit, iterated with the losses.

    Inlet: uniform Tt, Pt and no swirl make dh0/dr = ds/dr = 0 and r Vt = 0, so equilibrium needs a
    uniform meridional velocity; the flow is split by inlet area (as solve_rotor) and the inlet tube
    positions stay as given. Exit: the tube mass flows are fixed by the inlet; the exit areas (and the
    area-centre radii within the exit annulus exit_hub..exit_tip) are moved, with under-relaxation, until
    simple radial equilibrium holds (equilibrium_areas). Every pass re-solves the tubes, so work, deviation
    and losses follow the new exit radii. The total exit flow area is that of the given tubes.
    Streamline curvature is neglected."""
    total_inlet = sum(t.A1 for t in tubes)
    masses = [mass_flow * t.A1 / total_inlet for t in tubes]
    area_total = sum(t.A2 for t in tubes)
    current = list(tubes)
    residual, results = float("inf"), []
    for it in range(1, max_iter + 1):
        results = [solve_tube(t, m, omega, Tt1, Pt1, gas) for t, m in zip(current, masses)]
        target = equilibrium_areas(results, [t.r2 for t in current], area_total, Tt1, Pt1, gas)
        new = [t.A2 + relax * (a - t.A2) for t, a in zip(current, target)]
        new = [a * area_total / sum(new) for a in new]
        residual = max(abs(a / t.A2 - 1) for a, t in zip(new, current))
        order = sorted(range(len(current)), key=lambda i: current[i].r2)
        radii = area_centre_radii([new[i] for i in order], exit_hub, exit_tip)
        r2 = [0.0] * len(current)
        for j, i in enumerate(order):
            r2[i] = radii[j]
        current = [replace(t, A2=a, r2=r) for t, a, r in zip(current, new, r2)]
        if residual < tol:
            results = [solve_tube(t, m, omega, Tt1, Pt1, gas) for t, m in zip(current, masses)]
            return RotorSolution(current, results, it, True, residual)
    return RotorSolution(current, results, max_iter, False, residual)


def loss_breakdown(r: TubeResult) -> dict:
    """Loss coefficient of each mechanism (profile, shock, endwall, tip; on the inlet relative dynamic head)
    and its share of the efficiency deficit 1 - eta, split in proportion to the loss coefficients (with no
    loss the model gives eta = 1, so the shares add up to the deficit)."""
    terms = {"profile": r.loss_profile, "shock": r.loss_shock, "endwall": r.loss_endwall, "tip": r.loss_tip}
    total = sum(terms.values())
    deficit = 1 - r.efficiency
    return {name: {"loss": w, "delta_eta": deficit * w / total if total > 0 else 0.0} for name, w in terms.items()}
