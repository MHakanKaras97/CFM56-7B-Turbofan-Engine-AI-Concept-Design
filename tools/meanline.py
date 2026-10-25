"""Streamline (stream-tube) analysis of one compressor or fan blade row, reusable by M1, M2 and M3.

Method: engine/M1_inlet_fan/rules/aero_method.md, steps 1-7, for a rotor without inlet swirl.
Each stream tube is solved on its own (no radial equilibrium); its inlet and exit radii and areas
are given. Perfect gas with constant gamma (cold air) [G]. Angles in radians, measured from the
meridional direction, positive in the direction of rotation. SI units.

Correlations (tags as used here):
- Deviation: Carter's rule, delta = m * camber / sqrt(solidity), m = 0.23 (2a/c)^2 + kappa2/500 deg
  with a/c = 0.5 (circular-arc camber line) [G].
- Profile loss: Lieblein equivalent diffusion ratio D_eq [KS, Abrisha eq. 4.9; Sjögren eq. 2.11] and
  the wake momentum thickness fit theta/c = 0.004 (1 + 3.1 (D_eq - 1)^2 + 0.4 (D_eq - 1)^8) [G, Aungier
  2003 fit of Lieblein's data; not in the M1 source set].
- Shock loss: normal shock at the passage Mach number = mean of inlet relative Mach and the suction-
  surface Mach after a Prandtl-Meyer expansion to the covered-passage entrance (Schwenk / Miller-
  Lewis-Hartmann type) [KS, Sjögren p. 24; Visentin p. 32]; taper 0.8 < M1rel < 1.0 [KS, Sjögren p. 24].
- Endwall loss (only for tubes given `Endwall` data): Howell annulus drag C_Da = 0.020 s/h and secondary drag
  C_Ds = 0.018 C_L^2 with C_L = 2 cos(beta_m) (tan beta1 - tan beta2) / sigma, turned into a loss
  coefficient sigma C_D cos^2(beta1) / cos^3(beta_m) [G, Howell 1945 as given in turbomachinery textbooks; Howell
  is the secondary loss model of SATURN, Visentin p. 32; coefficients not in the M1 source set]. The row value is
  spread over the span with the weight 3 (2f - 1)^2 (mean 1, largest at both walls) [T, after the parabolic
  endwall loss distribution of SC90C, Sjögren p. 22].
- Tip clearance loss: Lakshminarayana's efficiency debit d_eta = 0.7 (tau/h) psi / cos(beta_m)
  (1 + 10 sqrt((tau/c) AR / (psi cos(beta_m)))), psi = dh0 / U^2, AR = h/c [G, Lakshminarayana 1970; not in the
  M1 source set, Visentin p. 32 names Yaras-Sjolander]. Spread with the weight 3 f^2 (mean 1, casing) [T] and
  applied as the total pressure loss of the matching entropy rise, ds = cp d_eta dTt / Tt2 [G].
"""

import math
from dataclasses import dataclass, field


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


def tip_weight(f: float) -> float:
    return 3 * f * f


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
    if M1rel > 0.8:
        M_up = max(M1rel, 1.0)
        turn = max(incidence, 0.0) + tube.covered_fraction * (tube.kappa1 - tube.kappa2)
        M_ss = mach_from_prandtl_meyer(prandtl_meyer(M_up, gas) + turn, gas)
        M_pass = (M_up + M_ss) / 2
        pt_ratio = normal_shock_pt_ratio(M_pass, gas)
        taper = min(1.0, (M1rel - 0.8) / 0.2)
        loss_shock = taper * (1 - pt_ratio) * Pt1rel / (Pt1rel - p1)

    # Exit: meridional velocity from continuity, on the subsonic branch of the mass flux curve
    U2 = omega * tube.r2
    Tt2rel = Tt1rel + (U2 * U2 - U1 * U1) / (2 * gas.cp)
    Pt2rel_ideal = Pt1rel * (Tt2rel / Tt1rel) ** k

    ew = tube.endwall
    loss_ew = 0.0
    if ew is not None:
        pitch = ew.chord / tube.solidity
        loss_ew = endwall_weight(ew.span_fraction) * howell_endwall_loss(beta1, beta2, tube.solidity, pitch,
                                                                           ew.blade_height)

    def tip_loss(Vm2):
        """Loss coefficient of the tip clearance efficiency debit at this exit state."""
        if ew is None:
            return 0.0
        work = U2 * (U2 - Vm2 * math.tan(beta2))  # Euler work, no inlet swirl
        if work <= 0:
            return 0.0
        d_eta = tip_weight(ew.span_fraction) * tip_clearance_debit(beta1, beta2, work / (U2 * U2), ew)
        Tt2 = Tt1 + work / gas.cp
        ds = gas.cp * d_eta * (Tt2 - Tt1) / Tt2
        return (1 - math.exp(-ds / gas.R)) * Pt2rel_ideal / (Pt1rel - p1)

    def exit_state(Vm2):
        Wt2 = Vm2 * math.tan(beta2)
        W2 = math.hypot(Vm2, Wt2)
        deq = lieblein_deq(beta1, beta2, W1, W2, tube.solidity)
        loss_p = profile_loss(beta1, beta2, deq, tube.solidity)
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
