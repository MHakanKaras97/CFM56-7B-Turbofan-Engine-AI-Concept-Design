"""Gas-path thermodynamics (pure Python, SI units).

Two gas models share one interface:
- NasaGas: dry air and its lean C12H23 combustion products, variable cp(T, FAR) from the NASA
  7-coefficient polynomials in tools/data/nasa_glenn.yaml (McBride et al., NASA TM-4513).
- ConstantCp: one ideal gas with fixed cp and gamma; kept for closed-form checks.

h is the sensible enthalpy per kg of mixture referenced to T_REF = 298.15 K (the LHV reference),
so fuel injected at T_REF carries no sensible enthalpy [G]. It is one continuous function of
(T, f) for all stations (ADR-006). f is the fuel-air ratio (fuel mass / air mass), f = 0 is air.
Isentropic and polytropic steps use the entropy function phi(T, f) = s0(T, f) at reference
pressure: phi(T2) - phi(T1) = R_s * ln(P2/P1) for an isentropic step.
Total quantities: Tt [K], Pt [Pa]; specific work w [J/kg].
"""

import math
from dataclasses import dataclass
from pathlib import Path

import yaml

R_AIR = 287.0  # J/(kg K) [G]
T_REF = 298.15  # K [G]
DATA_FILE = Path(__file__).resolve().parent / "data" / "nasa_glenn.yaml"


def _solve_T(fun, slope, target: float, what: str, T_min: float, T_max: float, log: bool = False) -> float:
    """Newton iteration for fun(T) = target on [T_min, T_max]. log=True iterates on ln T
    (slope is then d fun / d ln T), which keeps entropy-function inversions well behaved."""
    T = 1000.0
    for _ in range(60):
        step = (fun(T) - target) / slope(T)
        T_new = min(max(T * math.exp(-step) if log else T - step, T_min), T_max)
        if abs(T_new - T) < 1e-10 * T:
            if T_new in (T_min, T_max) and abs(fun(T_new) - target) > 1e-6 * abs(slope(T_new)):
                break
            return T_new
        T = T_new
    raise ValueError(f"{what}: no temperature in {T_min:g}..{T_max:g} K for {target:.6g}")


# --- gas models -------------------------------------------------------------------

@dataclass(frozen=True)
class ConstantCp:
    """Ideal gas with constant cp and gamma. R_s = cp*(gamma-1)/gamma drives the isentropic
    relations (exact constant-gamma formulas); R is used for density only."""
    cp_value: float
    gamma_value: float
    R_value: float = R_AIR

    def cp(self, T: float, f: float = 0.0) -> float:
        return self.cp_value

    def h(self, T: float, f: float = 0.0) -> float:
        return self.cp_value * (T - T_REF)

    def T_from_h(self, h: float, f: float = 0.0) -> float:
        T = T_REF + h / self.cp_value
        if T <= 0.0:
            raise ValueError(f"enthalpy {h:.0f} J/kg below absolute zero")
        return T

    def phi(self, T: float, f: float = 0.0) -> float:
        return self.cp_value * math.log(T)

    def T_from_phi(self, phi: float, f: float = 0.0) -> float:
        return math.exp(phi / self.cp_value)

    def R(self, f: float = 0.0) -> float:
        return self.R_value

    def R_s(self, f: float = 0.0) -> float:
        return self.cp_value * (self.gamma_value - 1.0) / self.gamma_value

    def gamma(self, T: float, f: float = 0.0) -> float:
        return self.gamma_value


class NasaGas:
    """Air + lean C12H23 combustion products, NASA 7-coefficient species data.

    Per kg of air the mixture holds n_air[i] mol of species i; burning f kg of fuel per kg of air
    adds f*dn_fuel[i] mol (CO2, H2O up; O2 down). Properties per kg of mixture divide by (1 + f).
    """

    def __init__(self, data_file: Path = DATA_FILE):
        data = yaml.safe_load(Path(data_file).read_text(encoding="utf-8"))
        self.Ru = float(data["universal_gas_constant"]["value"])
        self.T_ref = float(data["reference_temperature"]["value"])
        atoms = {k: v["value"] * 1e-3 for k, v in data["atomic_weights"].items() if isinstance(v, dict)}
        self.names = list(data["species"])
        spec = data["species"]
        self._ranges = [spec[s]["T_ranges"] for s in self.names]
        self._coef = [(spec[s]["low"], spec[s]["high"]) for s in self.names]
        self.M = [sum(n * atoms[a] for a, n in spec[s]["composition"].items()) for s in self.names]

        x_air = data["air"]["mole_fractions"]
        x_sum = sum(x_air.values())
        M_air = sum(x / x_sum * self.M[self.names.index(s)] for s, x in x_air.items())
        self.n_air = [x_air.get(s, 0.0) / x_sum / M_air for s in self.names]

        fuel = data["fuel"]["composition"]
        C, H = fuel["C"], fuel["H"]
        n_fuel = 1.0 / (C * atoms["C"] + H * atoms["H"])  # mol fuel per kg fuel
        delta = {"CO2": C, "H2O": H / 2.0, "O2": -(C + H / 4.0)}
        self.dn_fuel = [delta.get(s, 0.0) * n_fuel for s in self.names]
        self.f_stoich = self.n_air[self.names.index("O2")] / -self.dn_fuel[self.names.index("O2")]
        self.T_limits = (max(r[0] for r in self._ranges), min(r[2] for r in self._ranges))
        self._h_ref = [self._h_species(i, self.T_ref) for i in range(len(self.names))]

    # species functions, per mol, divided by Ru
    def _a(self, i: int, T: float):
        lo, mid, hi = self._ranges[i]
        if not lo <= T <= hi:
            raise ValueError(f"T = {T:.1f} K outside NASA polynomial range {lo:g}..{hi:g} K")
        return self._coef[i][0] if T <= mid else self._coef[i][1]

    def _cp_species(self, i: int, T: float) -> float:
        a = self._a(i, T)
        return a[0] + T * (a[1] + T * (a[2] + T * (a[3] + T * a[4])))

    def _h_species(self, i: int, T: float) -> float:
        a = self._a(i, T)
        return T * (a[0] + T * (a[1] / 2 + T * (a[2] / 3 + T * (a[3] / 4 + T * a[4] / 5)))) + a[5]

    def _s_species(self, i: int, T: float) -> float:
        a = self._a(i, T)
        return a[0] * math.log(T) + T * (a[1] + T * (a[2] / 2 + T * (a[3] / 3 + T * a[4] / 4))) + a[6]

    def moles(self, f: float) -> list[float]:
        """mol of each species per kg of mixture."""
        if not 0.0 <= f <= self.f_stoich:
            raise ValueError(f"fuel-air ratio {f:.5f} outside 0..{self.f_stoich:.5f} (lean combustion)")
        return [(n + f * d) / (1.0 + f) for n, d in zip(self.n_air, self.dn_fuel)]

    def cp(self, T: float, f: float = 0.0) -> float:
        return self.Ru * sum(n * self._cp_species(i, T) for i, n in enumerate(self.moles(f)))

    def h(self, T: float, f: float = 0.0) -> float:
        return self.Ru * sum(n * (self._h_species(i, T) - self._h_ref[i]) for i, n in enumerate(self.moles(f)))

    def phi(self, T: float, f: float = 0.0) -> float:
        return self.Ru * sum(n * self._s_species(i, T) for i, n in enumerate(self.moles(f)))

    def T_from_h(self, h: float, f: float = 0.0) -> float:
        return _solve_T(lambda T: self.h(T, f), lambda T: self.cp(T, f), h, "T_from_h", *self.T_limits)

    def T_from_phi(self, phi: float, f: float = 0.0) -> float:
        return _solve_T(lambda T: self.phi(T, f), lambda T: self.cp(T, f), phi, "T_from_phi",
                        *self.T_limits, log=True)

    def R(self, f: float = 0.0) -> float:
        return self.Ru * sum(self.moles(f))

    R_s = R

    def gamma(self, T: float, f: float = 0.0) -> float:
        cp = self.cp(T, f)
        return cp / (cp - self.R(f))


# --- components ---------------------------------------------------------------------

def compressor(Tt: float, Pt: float, pi: float, e_poly: float, gas, f: float = 0.0):
    """Polytropic compression by total pressure ratio pi. Returns (Tt_out, Pt_out, w)."""
    Tt_out = gas.T_from_phi(gas.phi(Tt, f) + gas.R_s(f) / e_poly * math.log(pi), f)
    return Tt_out, Pt * pi, gas.h(Tt_out, f) - gas.h(Tt, f)


def turbine_for_work(Tt: float, Pt: float, w: float, e_poly: float, gas, f: float = 0.0):
    """Polytropic expansion delivering specific work w. Returns (Tt_out, Pt_out, pi), pi = Pt_in/Pt_out > 1."""
    try:
        Tt_out = gas.T_from_h(gas.h(Tt, f) - w, f)
    except ValueError:
        raise ValueError(f"turbine work {w:.0f} J/kg exceeds available enthalpy at Tt={Tt:.1f} K") from None
    pi = math.exp((gas.phi(Tt, f) - gas.phi(Tt_out, f)) / (e_poly * gas.R_s(f)))
    return Tt_out, Pt / pi, pi


def compressor_is(Tt: float, Pt: float, pi: float, eta_is: float, gas, f: float = 0.0):
    """Compression by total pressure ratio pi with isentropic efficiency. Returns (Tt_out, Pt_out, w)."""
    h = gas.h(Tt, f)
    T_is = gas.T_from_phi(gas.phi(Tt, f) + gas.R_s(f) * math.log(pi), f)
    w = (gas.h(T_is, f) - h) / eta_is
    return gas.T_from_h(h + w, f), Pt * pi, w


def turbine_is_for_work(Tt: float, Pt: float, w: float, eta_is: float, gas, f: float = 0.0):
    """Expansion delivering specific work w with isentropic efficiency.
    Returns (Tt_out, Pt_out, pi), pi = Pt_in/Pt_out > 1."""
    h = gas.h(Tt, f)
    try:
        Tt_out = gas.T_from_h(h - w, f)
        T_is = gas.T_from_h(h - w / eta_is, f)
    except ValueError:
        raise ValueError(f"turbine work {w:.0f} J/kg exceeds available enthalpy at Tt={Tt:.1f} K") from None
    pi = math.exp((gas.phi(Tt, f) - gas.phi(T_is, f)) / gas.R_s(f))
    return Tt_out, Pt / pi, pi


def burner(Tt_in: float, T_out: float, eta_b: float, LHV: float, gas) -> float:
    """Fuel-air ratio f from h_air(Tt_in) + eta_b*f*LHV = (1 + f)*h(T_out, f); fuel enters at T_REF."""
    h_in = gas.h(Tt_in, 0.0)
    f = 0.0
    for _ in range(50):
        h_out = gas.h(T_out, f)
        f_new = (h_out - h_in) / (eta_b * LHV - h_out)
        if abs(f_new - f) < 1e-15:
            return f_new
        f = f_new
    raise ArithmeticError("burner fuel-air ratio did not converge")


def mix(W_a: float, T_a: float, f_a: float, W_b: float, T_b: float, f_b: float, gas):
    """Adiabatic mixing of two streams. Returns (W, T, f)."""
    W = W_a + W_b
    fuel = W_a * f_a / (1.0 + f_a) + W_b * f_b / (1.0 + f_b)
    f = fuel / (W - fuel)
    h = (W_a * gas.h(T_a, f_a) + W_b * gas.h(T_b, f_b)) / W
    return W, gas.T_from_h(h, f), f


@dataclass(frozen=True)
class Nozzle:
    V: float          # effective exit velocity, thrust coefficient * ideal velocity [m/s]
    A: float          # geometric exit area per unit mass flow, effective area / CD [m2 per kg/s]
    choked: bool
    p_exit: float     # exit static pressure [Pa]
    F_per_W: float    # gross thrust per unit mass flow [N per kg/s]


def _static(Tt: float, Pt: float, p: float, gas, f: float) -> tuple[float, float]:
    """Isentropic static temperature and ideal velocity at static pressure p."""
    Ts = gas.T_from_phi(gas.phi(Tt, f) + gas.R_s(f) * math.log(p / Pt), f)
    return Ts, math.sqrt(max(2.0 * (gas.h(Tt, f) - gas.h(Ts, f)), 0.0))


def critical_pressure(Tt: float, Pt: float, gas, f: float = 0.0) -> float:
    """Static pressure where the isentropic velocity equals the local speed of sound (secant)."""
    def mismatch(p):
        Ts, V = _static(Tt, Pt, p, gas, f)
        return V * V / (gas.gamma(Ts, f) * gas.R_s(f) * Ts) - 1.0

    g = gas.gamma(Tt, f)
    p1 = Pt * (2.0 / (g + 1.0)) ** (g / (g - 1.0))
    p0, m0 = 1.02 * p1, mismatch(1.02 * p1)
    for _ in range(50):
        m1 = mismatch(p1)
        if abs(m1) < 1e-12 or m1 == m0:
            return p1
        p0, p1, m0 = p1, p1 - m1 * (p1 - p0) / (m1 - m0), m1
    raise ArithmeticError("critical pressure did not converge")


def nozzle(Tt: float, Pt: float, P0: float, gas, f: float = 0.0, cfg: float = 1.0, cd: float = 1.0) -> Nozzle:
    """Convergent nozzle. Choked: exit at critical pressure, pressure thrust A_eff*(p_exit - P0).

    Gross thrust = cfg * ideal gross thrust (momentum + pressure term). CD scales the area only:
    A_geometric = A_effective / cd, where A_effective comes from the ideal (isentropic) exit state.
    """
    if Pt <= P0:
        raise ValueError(f"nozzle total pressure {Pt:.0f} Pa <= ambient {P0:.0f} Pa")
    p_crit = critical_pressure(Tt, Pt, gas, f)
    choked = p_crit > P0
    p_exit = p_crit if choked else P0
    T_exit, V_is = _static(Tt, Pt, p_exit, gas, f)
    A_eff = 1.0 / (p_exit / (gas.R(f) * T_exit) * V_is)
    return Nozzle(V=cfg * V_is, A=A_eff / cd, choked=choked, p_exit=p_exit,
                  F_per_W=cfg * (V_is + A_eff * (p_exit - P0)))


def choke_mass_flux(Tt: float, Pt: float, gas, f: float = 0.0) -> float:
    """Maximum mass flow per unit area (M = 1) for total conditions Pt, Tt."""
    p = critical_pressure(Tt, Pt, gas, f)
    Ts, V = _static(Tt, Pt, p, gas, f)
    return p / (gas.R(f) * Ts) * V


def compressor_isentropic_eff(Tt: float, pi: float, e_poly: float, gas, f: float = 0.0) -> float:
    phi = gas.phi(Tt, f)
    T_is = gas.T_from_phi(phi + gas.R_s(f) * math.log(pi), f)
    T_out = gas.T_from_phi(phi + gas.R_s(f) / e_poly * math.log(pi), f)
    h = gas.h(Tt, f)
    return (gas.h(T_is, f) - h) / (gas.h(T_out, f) - h)


def turbine_isentropic_eff(Tt: float, pi: float, e_poly: float, gas, f: float = 0.0) -> float:
    """pi = Pt_in / Pt_out > 1."""
    phi = gas.phi(Tt, f)
    T_is = gas.T_from_phi(phi - gas.R_s(f) * math.log(pi), f)
    T_out = gas.T_from_phi(phi - gas.R_s(f) * e_poly * math.log(pi), f)
    h = gas.h(Tt, f)
    return (h - gas.h(T_out, f)) / (h - gas.h(T_is, f))
