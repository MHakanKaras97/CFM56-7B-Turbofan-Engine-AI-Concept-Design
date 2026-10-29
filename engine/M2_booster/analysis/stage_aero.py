"""M2 shared meanline pieces: static states, annulus planes, spanwise section triangles, DF and solidity.

Used by the booster meanline (booster_meanline.py) and the A-1 validation (a1_validation.py), so that A-1
checks the same code path. Definitions: engine/M2_booster/rules/aero_method.md.
- Gas: any tools.thermo gas (NasaGas or ConstantCp): h, T_from_h, phi, R, R_s, gamma.
- Angles from the axial direction, degrees in outputs. Rotor relative tangential velocity Wt = U - Vt.
- Spanwise distribution (aero_method.md "Spanwise distribution"): each plane carries the 1-D axial velocity Vx
  (continuity, used by the annulus rule) and the swirl constant K = r Vt at the mean radius; hub/tip sections use
  shape ratios: Vx_sec = vx_shape[sec] x Vx and, behind a rotor, Vt_sec from Euler with work w_sec = g_sec x w
  (rotor_exit_swirl). Default shapes (all 1, vt_sec None) are the free vortex [G]: r Vt constant, uniform Vx.
- DF: Lieblein with radius change (tools.meanline.diffusion_factor, RM E53D01 eq. 13) [K form].
- Solidity: sigma = c z / (2 pi (r_LE + r_TE) / 2) [H definition, aero_method.md].
Efficiency is never predicted here (ADR-015): total states come from the caller.
"""

import math
from dataclasses import dataclass, replace

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
    vx_shape: tuple = (1.0, 1.0, 1.0)  # Vx_sec / Vx for (hub, mean, tip)
    vt_sec: tuple | None = None  # section Vt (hub, mean, tip); None -> free vortex K / r

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

    def vx_at(self, section: str) -> float:
        return self.Vx * self.vx_shape[SECTIONS.index(section)]

    def vt_at(self, section: str) -> float:
        if self.vt_sec is None:
            return self.vt(self.radius(section))
        return self.vt_sec[SECTIONS.index(section)]

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


def with_profile(plane: Plane, vx_shape: tuple, vt_sec: tuple | None = None) -> Plane:
    """Same 1-D plane with section shapes attached (annulus and mean-line state unchanged)."""
    return replace(plane, vx_shape=tuple(vx_shape), vt_sec=None if vt_sec is None else tuple(vt_sec))


def rotor_exit_swirl(inlet: Plane, exit_: Plane, omega: float, w: float, work_shape: tuple) -> tuple:
    """Section exit swirl from Euler with section work g_sec x w: Vt2 = (g w + U1 Vt1) / U2."""
    out = []
    for sec, g in zip(SECTIONS, work_shape):
        r1, r2 = inlet.radius(sec), exit_.radius(sec)
        out.append((g * w + omega * r1 * inlet.vt_at(sec)) / (omega * r2))
    return tuple(out)


def simpson_closure(plane: Plane, work_shape: tuple | None = None) -> dict:
    """Three-point (Simpson 1/4/1 on r Vx, uniform density) mass-flow ratio of the section profile against the
    1-D continuity value, and the mass-averaged work ratio (aero_method.md: reported, not re-normalised)."""
    wts = (1.0, 4.0, 1.0)
    r = [plane.radius(s) for s in SECTIONS]
    m = [k * ri * f for k, ri, f in zip(wts, r, plane.vx_shape)]
    out = {"mass_flow_ratio": sum(m) / sum(k * ri for k, ri in zip(wts, r))}
    if work_shape is not None:
        out["work_ratio"] = sum(mi * g for mi, g in zip(m, work_shape)) / sum(m)
    return out


def solidity(chord: float, z: int, r_le: float, r_te: float) -> float:
    return chord * z / (2 * math.pi * (r_le + r_te) / 2)


def rotor_section(gas, inlet: Plane, exit_: Plane, omega: float, section: str, chord: float, z: int) -> dict:
    """Rotor triangles at one section (LE radius on the inlet plane, TE radius on the exit plane)."""
    r1, r2 = inlet.radius(section), exit_.radius(section)
    U1, U2 = omega * r1, omega * r2
    Vt1, Vt2 = inlet.vt_at(section), exit_.vt_at(section)
    Vx1, Vx2 = inlet.vx_at(section), exit_.vx_at(section)
    Wt1, Wt2 = U1 - Vt1, U2 - Vt2
    W1, W2 = math.hypot(Vx1, Wt1), math.hypot(Vx2, Wt2)
    s1 = static_state(gas, inlet.Tt, inlet.Pt, math.hypot(Vx1, Vt1))
    sig = solidity(chord, z, r1, r2)
    return {
        "r_le": r1, "r_te": r2, "U1": U1, "U2": U2, "Vx1": Vx1, "Vx2": Vx2, "Vt1": Vt1, "Vt2": Vt2,
        "W1": W1, "W2": W2, "beta1": math.degrees(math.atan2(Wt1, Vx1)),
        "beta2": math.degrees(math.atan2(Wt2, Vx2)), "alpha2": math.degrees(math.atan2(Vt2, Vx2)),
        "M1rel": W1 / s1.a, "W2_W1": W2 / W1, "solidity": sig,
        "DF": diffusion_factor(W1, W2, r1, r2, Wt1, Wt2, sig),
    }


def stator_section(gas, inlet: Plane, exit_: Plane, section: str, chord: float, z: int) -> dict:
    """Stator triangles in the absolute frame at one section."""
    r1, r2 = inlet.radius(section), exit_.radius(section)
    Vt1, Vt2 = inlet.vt_at(section), exit_.vt_at(section)
    Vx1, Vx2 = inlet.vx_at(section), exit_.vx_at(section)
    V1, V2 = math.hypot(Vx1, Vt1), math.hypot(Vx2, Vt2)
    s1 = static_state(gas, inlet.Tt, inlet.Pt, V1)
    sig = solidity(chord, z, r1, r2)
    return {
        "r_le": r1, "r_te": r2, "Vx1": Vx1, "Vx2": Vx2, "Vt1": Vt1, "Vt2": Vt2, "V1": V1, "V2": V2,
        "alpha1": math.degrees(math.atan2(Vt1, Vx1)), "alpha2": math.degrees(math.atan2(Vt2, Vx2)),
        "M1": V1 / s1.a, "V2_V1": V2 / V1, "solidity": sig,
        "DF": diffusion_factor(V1, V2, r1, r2, Vt1, Vt2, sig),
    }
