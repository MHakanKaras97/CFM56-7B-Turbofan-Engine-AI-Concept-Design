"""M2 shared meanline pieces: static states, annulus planes, free-vortex section triangles, DF and solidity.

Used by the booster meanline (booster_meanline.py) and the A-1 validation (a1_validation.py), so that A-1
checks the same code path. Definitions: engine/M2_booster/rules/aero_method.md.
- Gas: any tools.thermo gas (NasaGas or ConstantCp): h, T_from_h, phi, R, R_s, gamma.
- Angles from the axial direction, degrees in outputs. Rotor relative tangential velocity Wt = U - Vt.
- Free vortex [G]: no inlet swirl, exit Vt(r) = w / (omega r), so the Euler work w is the same on every streamline
  and the axial velocity is uniform over the span (simple radial equilibrium); one axial velocity per plane.
- DF: Lieblein with radius change (tools.meanline.diffusion_factor, RM E53D01 eq. 13) [K form].
- Solidity: sigma = c z / (2 pi (r_LE + r_TE) / 2) [H definition, aero_method.md].
Efficiency is never predicted here (ADR-015): total states come from the caller.
"""

import math
from dataclasses import dataclass

from tools.meanline import diffusion_factor

SECTIONS = ("hub", "mean", "tip")


@dataclass(frozen=True)
class Static:
    T: float
    p: float
    rho: float
    a: float


def static_state(gas, Tt: float, Pt: float, V: float) -> Static:
    T = gas.T_from_h(gas.h(Tt) - V * V / 2)
    p = Pt * math.exp((gas.phi(T) - gas.phi(Tt)) / gas.R_s())
    R = gas.R()
    return Static(T, p, p / (R * T), math.sqrt(gas.gamma(T) * R * T))


@dataclass(frozen=True)
class Plane:
    """One axial plane: total state, annulus, uniform axial velocity, swirl constant K = r Vt."""
    Tt: float
    Pt: float
    r_hub: float
    r_tip: float
    Vx: float
    K: float  # r Vt [m2/s]

    @property
    def r_mean(self) -> float:
        return (self.r_hub + self.r_tip) / 2

    @property
    def area(self) -> float:
        return math.pi * (self.r_tip ** 2 - self.r_hub ** 2)

    @property
    def height(self) -> float:
        return self.r_tip - self.r_hub

    @property
    def hub_tip(self) -> float:
        return self.r_hub / self.r_tip

    def radius(self, section: str) -> float:
        return {"hub": self.r_hub, "mean": self.r_mean, "tip": self.r_tip}[section]

    def vt(self, r: float) -> float:
        return self.K / r

    def mean_static(self, gas) -> Static:
        return static_state(gas, self.Tt, self.Pt, math.hypot(self.Vx, self.vt(self.r_mean)))


def _fixed_point(f, x0: float, what: str, tol: float = 1e-10, n: int = 200) -> float:
    x = x0
    for _ in range(n):
        x_new = f(x)
        if abs(x_new - x) <= tol * max(1.0, abs(x)):
            return x_new
        x = x_new
    raise ValueError(f"{what}: no convergence")


def plane_from_area(gas, Tt: float, Pt: float, W: float, r_hub: float, r_tip: float, K: float) -> Plane:
    """Given annulus: uniform axial velocity from continuity (subsonic branch), mean-line static state."""
    area = math.pi * (r_tip ** 2 - r_hub ** 2)
    rm = (r_hub + r_tip) / 2
    vt = K / rm

    def update(vx):
        rho = static_state(gas, Tt, Pt, math.hypot(vx, vt)).rho
        return W / (rho * area)

    rho_t = static_state(gas, Tt, Pt, 0.0).rho
    Vx = _fixed_point(update, W / (rho_t * area), "plane_from_area")
    return Plane(Tt, Pt, r_hub, r_tip, Vx, K)


def axial_mach(gas, plane: Plane) -> float:
    return plane.Vx / plane.mean_static(gas).a


def plane_from_mach(gas, Tt: float, Pt: float, W: float, r_hub: float, mach_x: float, K: float,
                    r_tip_guess: float) -> Plane:
    """Constant hub radius, axial Mach (mean-line static) given: tip radius from continuity [T, plan step 5]."""

    def solve_vx(rm):
        vt = K / rm
        return _fixed_point(lambda vx: mach_x * static_state(gas, Tt, Pt, math.hypot(vx, vt)).a, 100.0,
                            "axial velocity at the given Mach")

    def update(r_tip):
        rm = (r_hub + r_tip) / 2
        vx = solve_vx(rm)
        rho = static_state(gas, Tt, Pt, math.hypot(vx, K / rm)).rho
        return math.sqrt(r_hub ** 2 + W / (rho * vx) / math.pi)

    r_tip = _fixed_point(update, r_tip_guess, "plane_from_mach")
    return Plane(Tt, Pt, r_hub, r_tip, solve_vx((r_hub + r_tip) / 2), K)


def solidity(chord: float, z: int, r_le: float, r_te: float) -> float:
    return chord * z / (2 * math.pi * (r_le + r_te) / 2)


def rotor_section(gas, inlet: Plane, exit_: Plane, omega: float, section: str, chord: float, z: int) -> dict:
    """Rotor triangles at one section (LE radius on the inlet plane, TE radius on the exit plane)."""
    r1, r2 = inlet.radius(section), exit_.radius(section)
    U1, U2 = omega * r1, omega * r2
    Vt1, Vt2 = inlet.vt(r1), exit_.vt(r2)
    Wt1, Wt2 = U1 - Vt1, U2 - Vt2
    W1, W2 = math.hypot(inlet.Vx, Wt1), math.hypot(exit_.Vx, Wt2)
    s1 = static_state(gas, inlet.Tt, inlet.Pt, math.hypot(inlet.Vx, Vt1))
    sig = solidity(chord, z, r1, r2)
    return {
        "r_le": r1, "r_te": r2, "U1": U1, "U2": U2, "Vx1": inlet.Vx, "Vx2": exit_.Vx, "Vt1": Vt1, "Vt2": Vt2,
        "W1": W1, "W2": W2, "beta1": math.degrees(math.atan2(Wt1, inlet.Vx)),
        "beta2": math.degrees(math.atan2(Wt2, exit_.Vx)), "alpha2": math.degrees(math.atan2(Vt2, exit_.Vx)),
        "M1rel": W1 / s1.a, "W2_W1": W2 / W1, "solidity": sig,
        "DF": diffusion_factor(W1, W2, r1, r2, Wt1, Wt2, sig),
    }


def stator_section(gas, inlet: Plane, exit_: Plane, section: str, chord: float, z: int) -> dict:
    """Stator triangles in the absolute frame at one section."""
    r1, r2 = inlet.radius(section), exit_.radius(section)
    Vt1, Vt2 = inlet.vt(r1), exit_.vt(r2)
    V1, V2 = math.hypot(inlet.Vx, Vt1), math.hypot(exit_.Vx, Vt2)
    s1 = static_state(gas, inlet.Tt, inlet.Pt, V1)
    sig = solidity(chord, z, r1, r2)
    return {
        "r_le": r1, "r_te": r2, "Vx1": inlet.Vx, "Vx2": exit_.Vx, "Vt1": Vt1, "Vt2": Vt2, "V1": V1, "V2": V2,
        "alpha1": math.degrees(math.atan2(Vt1, inlet.Vx)), "alpha2": math.degrees(math.atan2(Vt2, exit_.Vx)),
        "M1": V1 / s1.a, "V2_V1": V2 / V1, "solidity": sig,
        "DF": diffusion_factor(V1, V2, r1, r2, Vt1, Vt2, sig),
    }
