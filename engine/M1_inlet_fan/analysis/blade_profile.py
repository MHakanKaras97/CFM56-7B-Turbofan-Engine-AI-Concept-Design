"""Blade section profile family of the M1 fan (rules/aero_method.md R-AM.11) and its check on Rotor 67.

Family: multiple-circular-arc (MCA) type section in the blade-to-blade (m, r theta) plane:
- camber line of two circular arcs joined with a common tangent at chord fraction X_TRANSITION [T]; the front
  arc takes the share `front` of the camber kappa1 - kappa2, the rear arc the rest; the camber-line angle falls
  linearly along each arc [G, circular arc: constant curvature], taken here as linear in chord fraction [T].
  front = 0.5 with the maximum thickness at mid chord is the double-circular-arc (DCA) section of NASA SP-36
  (circular-arc upper and lower surfaces, a high-speed profile; PDF p. 204, printed p. 186) [K]; the loss,
  stagger and suction-surface correlations used by SC90C are for DCA sections (Sjögren pp. 23-24) [KS].
- thickness: two parabolic arcs with zero slope at the maximum thickness position x_max [T] (the difference of
  two circular arcs is close to a parabola for thin sections [G]); leading- and trailing-edge circles ignored.
- suction surface = camber line + half the normal thickness on the convex side. In the (m, r theta) plane the
  tangential offset is t_n / (2 cos kappa_c), so tan(beta_ss) = tan(kappa_c) + t_n' / (2 cos kappa_c), with
  t_n' = d t_n / dm = (t/c) tau'(x) / cos(stagger) and stagger = (kappa1 + kappa2) / 2 (Sjögren eq. 2.9) [G thin
  blade; on the Rotor 67 sections this relation reproduces the tabulated suction-surface angle BETA1 from BETA
  and TNPC within about 1 deg, M1 step 4e check].

Rotor 67 (TP-2879) does not name its profile family: the report refers to its refs. 11 and 12 for the
aerodynamic design (PDF p. 6, printed p. 2); "MCA" for Rotor 67 is therefore doğrulanmadı in the M1 source
set. Its Table I sections show the trend that the MCA family captures [H from KS]: front camber share about 0.5
inboard (DCA-like), falling to 0.12 at the casing (flat front suction surface of a supersonic section).

The M1 fan has no measured sections, so its family parameters at a span fraction are Rotor 67 fits [T analogue
of KS data]: front share quadratic, t/c cubic and x_max linear in span (least squares over the 14 sections).
"""

import math
from pathlib import Path

from core.util import read_yaml

M1 = Path(__file__).resolve().parents[1]
R67_GEOMETRY = M1 / "learning" / "rotor67_geometry.yaml"
R67_REFERENCE = M1 / "learning" / "rotor67_reference.yaml"

X_TRANSITION = 0.5  # chord fraction of the camber-arc joint [T]
N_SECTIONS = 14


def polyval(coeffs: tuple[float, ...] | list[float], x: float) -> float:
    """c0 + c1 x + c2 x^2 + ... (ascending powers)."""
    return sum(c * x ** k for k, c in enumerate(coeffs))


def lstsq(rows: list[list[float]], ys: list[float]) -> list[float]:
    """Least-squares coefficients of sum(c_k row_k) ~ y by the normal equations, Gauss elimination."""
    n = len(rows[0])
    a = [[sum(r[i] * r[j] for r in rows) for j in range(n)] + [sum(r[i] * y for r, y in zip(rows, ys))]
         for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda q: abs(a[q][col]))
        a[col], a[piv] = a[piv], a[col]
        for q in range(n):
            if q != col:
                z = a[q][col] / a[col][col]
                a[q] = [u - z * w for u, w in zip(a[q], a[col])]
    return [a[i][n] / a[i][i] for i in range(n)]


def polyfit(xs: list[float], ys: list[float], degree: int) -> list[float]:
    """Least-squares polynomial (ascending coefficients)."""
    return lstsq([[x ** k for k in range(degree + 1)] for x in xs], ys)


def camber_angle(kappa1: float, kappa2: float, front: float, x: float, x_t: float = X_TRANSITION) -> float:
    """Camber-line angle (rad) at chord fraction x of a two-arc camber line."""
    theta = kappa1 - kappa2
    if x <= x_t:
        return kappa1 - front * theta * x / x_t
    return kappa1 - front * theta - (1 - front) * theta * (x - x_t) / (1 - x_t)


def thickness_slope(x: float, x_max: float) -> float:
    """d tau / dx of the normalised thickness tau (max 1 at x_max, 0 at both edges, parabolic arcs)."""
    return -2 * (x - x_max) / (x_max ** 2 if x <= x_max else (1 - x_max) ** 2)


def suction_surface_angle(kappa1: float, kappa2: float, front: float, tc: float, x_max: float, x: float) -> float:
    """Suction-surface angle (rad, from the meridional direction) at chord fraction x."""
    kc = camber_angle(kappa1, kappa2, front, x)
    stagger = (kappa1 + kappa2) / 2
    return math.atan(math.tan(kc) + 0.5 * tc * thickness_slope(x, x_max) / (math.cos(stagger) * math.cos(kc)))


def ss_turn(kappa1: float, kappa2: float, front: float, tc: float, x_max: float, covered: float) -> float:
    """kappa1 minus the suction-surface angle at the covered-passage entrance (tools/meanline.py Tube.ss_turn)."""
    return kappa1 - suction_surface_angle(kappa1, kappa2, front, tc, x_max, covered)


# --- Rotor 67 section data and fits ------------------------------------------------------------------------

def _meridional_fractions(rows: list, iz: int, ir: int) -> list[float]:
    m = [0.0]
    for a, b in zip(rows, rows[1:]):
        m.append(m[-1] + math.hypot(b[iz] - a[iz], b[ir] - a[ir]))
    return [x / m[-1] for x in m]


def _interp(pts: list[tuple[float, float]], x: float) -> float:
    pts = sorted(pts)
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    i = next(i for i in range(len(pts) - 1) if pts[i][0] <= x <= pts[i + 1][0])
    (x0, y0), (x1, y1) = pts[i], pts[i + 1]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def rotor67_sections(geometry: dict | None = None) -> list[dict]:
    """Per Table I section [H from KS]: span fraction, front camber share at X_TRANSITION (from the camber-line
    angle BETA along the meridional length), position of the largest normal thickness TNPC, and t/c (max
    thickness / chord)."""
    geo = geometry or read_yaml(R67_GEOMETRY)
    cols = geo["points"]["columns"]
    iz, ir, ib, it = (cols.index(k) for k in ("Z", "R", "BETA", "TNPC"))
    out = []
    for n, (pts, sec) in enumerate(zip(geo["points"]["sections"], geo["sections"]), 1):
        rows = pts["rows"]
        xs = _meridional_fractions(rows, iz, ir)
        beta = [(x, r[ib]) for x, r in zip(xs, rows) if r[ib] is not None]
        k1, k2 = beta[0][1], beta[-1][1]
        thick = [(x, r[it]) for x, r in zip(xs, rows) if r[it] is not None]
        out.append({"section": n, "span": (n - 1) / (N_SECTIONS - 1),
                    "front": (k1 - _interp(beta, X_TRANSITION)) / (k1 - k2),
                    "x_max": max(thick, key=lambda p: p[1])[0],
                    "tc": sec["max_thickness"]["value"] / sec["chord"]["value"]})
    return out


def rotor67_fits(geometry: dict | None = None) -> dict:
    """Smooth spanwise family parameters fitted to the Rotor 67 sections (ascending polynomial coefficients)."""
    secs = rotor67_sections(geometry)
    f = [s["span"] for s in secs]
    fits = {"front": polyfit(f, [s["front"] for s in secs], 2),
            "tc": polyfit(f, [s["tc"] for s in secs], 3),
            "x_max": polyfit(f, [s["x_max"] for s in secs], 1)}
    rms = {k: math.sqrt(sum((polyval(c, s["span"]) - s[k]) ** 2 for s in secs) / len(secs)) for k, c in fits.items()}
    return {"coefficients": fits, "rms": rms, "sections": secs}


def family_at(fits: dict, span: float) -> dict:
    c = fits["coefficients"]
    return {"front": min(1.0, max(0.0, polyval(c["front"], span))), "tc": polyval(c["tc"], span),
            "x_max": polyval(c["x_max"], span)}


def rotor67_check(fits: dict | None = None) -> dict:
    """Profile builder against the KS geometry-based ss_turn of the Rotor 67 design streamlines
    (analysis/rotor67.py build_tubes): builder with the section values interpolated in span, with the smooth
    fits (as used for the M1 fan), and as a plain DCA (front 0.5, x_max 0.5) for contrast."""
    from engine.M1_inlet_fan.analysis import rotor67
    fits = fits or rotor67_fits()
    secs = fits["sections"]
    ref = read_yaml(R67_REFERENCE)
    st1 = ref["survey_stations"]["station_1_upstream"]
    r_hub, r_tip = st1["hub_radius"]["value"], st1["shroud_radius"]["value"]
    rows = []
    for t in rotor67.build_tubes(ref):
        f = (t.r1 / rotor67.CM - r_hub) / (r_tip - r_hub)
        sec = {k: _interp([(s["span"], s[k]) for s in secs], f) for k in ("front", "tc", "x_max")}
        fam = family_at(fits, f)
        vals = {"sections": ss_turn(t.kappa1, t.kappa2, sec["front"], sec["tc"], sec["x_max"], t.covered_fraction),
                "smooth_fit": ss_turn(t.kappa1, t.kappa2, fam["front"], fam["tc"], fam["x_max"], t.covered_fraction),
                "dca": ss_turn(t.kappa1, t.kappa2, 0.5, sec["tc"], 0.5, t.covered_fraction)}
        rows.append({"name": t.name, "span_fraction": round(f, 4), "covered_fraction": round(t.covered_fraction, 4),
                     "ss_turn_geometry_deg": round(math.degrees(t.ss_turn), 3),
                     **{f"ss_turn_{k}_deg": round(math.degrees(x), 3) for k, x in vals.items()},
                     **{f"diff_{k}_deg": round(math.degrees(x - t.ss_turn), 3) for k, x in vals.items()}})
    return {"streamlines": rows}
