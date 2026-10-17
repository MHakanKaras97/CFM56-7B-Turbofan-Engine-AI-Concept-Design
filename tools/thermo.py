"""Gas-path component relations (pure Python, SI units).

Two gas regions [G]: cold (air, up to burner inlet) and hot (combustion products).
Enthalpy uses cp; density uses R. Total quantities: Tt [K], Pt [Pa]; specific work w [J/kg].
"""

import math
from dataclasses import dataclass

R_AIR = 287.0  # J/(kg K) [G]


@dataclass(frozen=True)
class Gas:
    cp: float
    gamma: float
    R: float = R_AIR

    @property
    def k(self) -> float:
        """(gamma - 1) / gamma"""
        return (self.gamma - 1.0) / self.gamma


COLD = Gas(cp=1005.0, gamma=1.40)  # [G]
HOT = Gas(cp=1150.0, gamma=1.33)   # [G]


def compressor(Tt: float, Pt: float, pi: float, e_poly: float, gas: Gas = COLD):
    """Compression by total pressure ratio pi. Returns (Tt_out, Pt_out, w)."""
    Tt_out = Tt * pi ** (gas.k / e_poly)
    return Tt_out, Pt * pi, gas.cp * (Tt_out - Tt)


def turbine_for_work(Tt: float, Pt: float, w: float, e_poly: float, gas: Gas = HOT):
    """Expansion delivering specific work w. Returns (Tt_out, Pt_out, pi) with pi = Pt_in / Pt_out > 1."""
    Tt_out = Tt - w / gas.cp
    if Tt_out <= 0:
        raise ValueError(f"turbine work {w:.0f} J/kg exceeds available enthalpy at Tt={Tt:.1f} K")
    pi = (Tt / Tt_out) ** (1.0 / (gas.k * e_poly))
    return Tt_out, Pt / pi, pi


def burner(Tt_in: float, T4: float, eta_b: float, LHV: float, cold: Gas = COLD, hot: Gas = HOT) -> float:
    """Fuel-air ratio f from W*cp_c*Tt_in + eta_b*f*W*LHV = W*(1+f)*cp_h*T4."""
    return (hot.cp * T4 - cold.cp * Tt_in) / (eta_b * LHV - hot.cp * T4)


@dataclass(frozen=True)
class Nozzle:
    V: float          # exit velocity incl. cv [m/s]
    A: float          # geometric exit area per unit mass flow [m2 per kg/s]
    choked: bool
    p_exit: float     # exit static pressure [Pa]
    F_per_W: float    # gross thrust per unit mass flow [N per kg/s]


def nozzle(Tt: float, Pt: float, P0: float, cv: float, gas: Gas) -> Nozzle:
    """Convergent nozzle. Choked: exit at critical pressure, pressure thrust A*(p_exit - P0).

    cv scales the velocity only; the area comes from the ideal (isentropic) exit state.
    """
    p_crit = Pt * (2.0 / (gas.gamma + 1.0)) ** (1.0 / gas.k)
    choked = p_crit > P0
    p_exit = p_crit if choked else P0
    T_exit = Tt * (p_exit / Pt) ** gas.k
    V_is = math.sqrt(2.0 * gas.cp * (Tt - T_exit))
    rho = p_exit / (gas.R * T_exit)
    A = 1.0 / (rho * V_is)
    V = cv * V_is
    return Nozzle(V=V, A=A, choked=choked, p_exit=p_exit, F_per_W=V + A * (p_exit - P0))


def compressor_isentropic_eff(pi: float, e_poly: float, gas: Gas = COLD) -> float:
    return (pi ** gas.k - 1.0) / (pi ** (gas.k / e_poly) - 1.0)


def turbine_isentropic_eff(pi: float, e_poly: float, gas: Gas = HOT) -> float:
    """pi = Pt_in / Pt_out > 1."""
    return (1.0 - pi ** (-gas.k * e_poly)) / (1.0 - pi ** (-gas.k))
