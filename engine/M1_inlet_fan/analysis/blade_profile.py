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
Span fraction of a Rotor 67 section (M1 step 4g): leading-edge radius fraction between section 1 and section 14,
the same definition as the M1 blade (inlet radius between hub and tip); the sections are equally spaced in
leading-edge radius, so this equals the section index fraction to 4 decimals.

t/c benchmark (M1 step 4g, rotor67_tc_benchmark): t/c = largest tabulated TNPC of a section (thickness normal to
the mean camber line, TP-2879 Table I symbol list, PDF p. 22, printed p. 18 [KS]) divided by the section chord
(straight line between the extreme points of the edge circles in the (m, r theta) plane, rotor67_geometry.yaml
`chord` [H from KS]). Hub = section 1, tip = section 14, mid = linear interpolation at span fraction 0.5 between
sections 7 and 8 [H from KS]. Since M1 step 4i the M1 t/c is derived from its area law (fan_design.derived_tc);
the cubic fit of these 14 values is only the pass-0 start value of the profile builder.
"""

import math
from pathlib import Path

from core.util import read_yaml

M1 = Path(__file__).resolve().parents[1]
R67_GEOMETRY = M1 / "learning" / "rotor67_geometry.yaml"
R67_REFERENCE = M1 / "learning" / "rotor67_reference.yaml"

X_TRANSITION = 0.5  # chord fraction of the camber-arc joint [T]
N_SECTIONS = 14
# Section area / (max thickness x chord) of the R-AM.11 thickness form [H from the T form]: each parabolic arc
# with zero slope at x_max encloses 2/3 of its bounding rectangle, so A = (2/3) t c for any x_max (edge circles
# ignored). Rotor 67 Table I sections give 0.69-0.73 (rotor67_section_areas) [H from KS].
AREA_COEFFICIENT = 2.0 / 3.0


def polyval(coeffs: tuple[float, ...] | list[float], x: float) -> float:
    """c0 + c1 x + c2 x^2 + ... (ascending powers)."""
    return sum(c * x ** k for k, c in enumerate(coeffs))


def polyder(coeffs: tuple[float, ...] | list[float], x: float) -> float:
    """Derivative of polyval(coeffs, x) in x."""
    return sum(k * c * x ** (k - 1) for k, c in enumerate(coeffs) if k)


def section_area(chord: float, tc: float) -> float:
    """Blade section area of the R-AM.11 profile: AREA_COEFFICIENT x t/c x chord^2."""
    return AREA_COEFFICIENT * tc * chord * chord


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


def thickness(x: float, x_max: float) -> float:
    """Normalised thickness tau of the R-AM.11 profile: two parabolic arcs, 1 at x_max, 0 at both edges."""
    d = (x - x_max) / (x_max if x <= x_max else 1 - x_max)
    return 1 - d * d


def profile_area_coefficient(x_max: float, n: int = 2000) -> float:
    """A / (t_max x chord) of the R-AM.11 thickness distribution by Simpson's rule on n intervals (n even) [H]; the
    two parabolic arcs give 2/3 for any x_max (cross-check of AREA_COEFFICIENT, M1 step 4f mass review)."""
    h = 1.0 / n
    return h / 3 * sum((1 if j in (0, n) else (4 if j % 2 else 2)) * thickness(j * h, x_max) for j in range(n + 1))


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


def rotor67_section_spans(geometry: dict | None = None) -> list[float]:
    """Span fraction of every Table I section: leading-edge radius fraction between section 1 and section 14
    (M1 step 4g; same definition as rotor67_kappa2_curvature and as the M1 inlet span fraction)."""
    geo = geometry or read_yaml(R67_GEOMETRY)
    r = [s["le_radius"]["value"] for s in geo["sections"]]
    return [(x - r[0]) / (r[-1] - r[0]) for x in r]


def rotor67_sections(geometry: dict | None = None) -> list[dict]:
    """Per Table I section [H from KS]: span fraction, front camber share at X_TRANSITION (from the camber-line
    angle BETA along the meridional length), position of the largest normal thickness TNPC, and t/c (max
    thickness / chord)."""
    geo = geometry or read_yaml(R67_GEOMETRY)
    cols = geo["points"]["columns"]
    iz, ir, ib, it = (cols.index(k) for k in ("Z", "R", "BETA", "TNPC"))
    spans = rotor67_section_spans(geo)
    out = []
    for n, (pts, sec, span) in enumerate(zip(geo["points"]["sections"], geo["sections"], spans), 1):
        rows = pts["rows"]
        xs = _meridional_fractions(rows, iz, ir)
        beta = [(x, r[ib]) for x, r in zip(xs, rows) if r[ib] is not None]
        k1, k2 = beta[0][1], beta[-1][1]
        thick = [(x, r[it]) for x, r in zip(xs, rows) if r[it] is not None]
        out.append({"section": n, "span": span,
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


def rotor67_tc_benchmark(geometry: dict | None = None) -> dict:
    """Rotor 67 thickness / chord benchmark (M1 step 4g) [H from KS]: per Table I section the span fraction
    (rotor67_section_spans), the largest TNPC and the chord (cm) and t/c; hub (section 1), mid (span fraction 0.5,
    linear between the neighbouring sections) and tip (section 14); the cubic fit used for the M1 blade and its
    largest deviation from the sections."""
    geo = geometry or read_yaml(R67_GEOMETRY)
    fits = rotor67_fits(geo)
    rows = [{"section": s["section"], "span_fraction": round(f, 5),
             "max_thickness_cm": s["max_thickness"]["value"], "max_thickness_at_K": s["max_thickness"]["at_K"],
             "chord_cm": round(s["chord"]["value"], 5),
             "t_c": round(s["max_thickness"]["value"] / s["chord"]["value"], 5)}
            for s, f in zip(geo["sections"], rotor67_section_spans(geo))]
    pts = [(r["span_fraction"], r["max_thickness_cm"] / r["chord_cm"]) for r in rows]
    tc_fit = fits["coefficients"]["tc"]
    return {
        "method": "t/c = largest tabulated TNPC of the section (thickness normal to the mean camber line, TP-2879 "
                  "Table I symbol list, PDF p. 22, printed p. 18 [KS]) / section chord (straight line between the "
                  "extreme points of the edge circles in the (m, r theta) plane, rotor67_geometry.yaml chord [H "
                  "from KS]); span fraction = leading-edge radius fraction between section 1 and section 14; hub = "
                  "section 1, tip = section 14, mid = linear interpolation at 0.5 between the neighbouring sections",
        "tag": "H from KS",
        "hub": rows[0]["t_c"], "mid": round(_interp(pts, 0.5), 5), "tip": rows[-1]["t_c"],
        "sections": rows,
        "fit_cubic_coefficients": [round(c, 6) for c in tc_fit],
        "fit_max_abs_deviation": round(max(abs(polyval(tc_fit, f) - y) for f, y in pts), 6),
        "fit_note": "the M1 blade uses this cubic fit of the 14 section values in its own inlet span fraction "
                    "(smooth, C2) [T analogue: Rotor 67 thickness applied to the CFM56-7B27 fan, CFM56-7B thickness "
                    "doğrulanmadı]",
    }


def rotor67_section_areas(geometry: dict | None = None) -> dict:
    """Rotor 67 section areas from Table I [H from KS]: integral of the normal thickness TNPC along the camber
    line, ds = dm / cos(BETA) in the (m, r theta) plane, trapezoidal over the tabulated points (cm^2); the area
    coefficient A / (max thickness x chord) per section; and the tip/root area taper (section 14 / section 1)."""
    geo = geometry or read_yaml(R67_GEOMETRY)
    cols = geo["points"]["columns"]
    iz, ir, it, ib = (cols.index(k) for k in ("Z", "R", "TNPC", "BETA"))
    rows_out = []
    spans = rotor67_section_spans(geo)
    for n, (pts, sec, span) in enumerate(zip(geo["points"]["sections"], geo["sections"], spans), 1):
        rows = [r for r in pts["rows"] if r[it] is not None and r[ib] is not None]
        area = sum((p[it] + q[it]) / 2 * math.hypot(q[iz] - p[iz], q[ir] - p[ir]) / math.cos(math.radians((p[ib] + q[ib]) / 2))
                   for p, q in zip(rows, rows[1:]))
        rows_out.append({"section": n, "span": span, "area_cm2": area,
                         "area_coefficient": area / (sec["max_thickness"]["value"] * sec["chord"]["value"])})
    return {"sections": rows_out, "taper_tip_over_root": rows_out[-1]["area_cm2"] / rows_out[0]["area_cm2"]}


def rotor67_kappa2_curvature(geometry: dict | None = None) -> dict:
    """Spanwise curvature of the Rotor 67 exit metal angle [H from KS]: d2(kappa2)/df2 (deg per unit span
    fraction squared) by three-point finite differences on the uneven section spacing; kappa2 = Table I
    te_metal_angle, f = leading-edge radius fraction between section 1 and section 14."""
    geo = geometry or read_yaml(R67_GEOMETRY)
    k2 = [s["te_metal_angle"]["value"] for s in geo["sections"]]
    r = [s["le_radius"]["value"] for s in geo["sections"]]
    f = [(x - r[0]) / (r[-1] - r[0]) for x in r]
    d2 = [2 * ((k2[j + 1] - k2[j]) / (f[j + 1] - f[j]) - (k2[j] - k2[j - 1]) / (f[j] - f[j - 1])) / (f[j + 1] - f[j - 1])
          for j in range(1, len(k2) - 1)]
    return {"span": f[1:-1], "d2kappa2_df2_deg": d2, "max_abs_deg": max(abs(x) for x in d2)}


def second_differences(fs: list[float], ys: list[float]) -> list[float]:
    """Second divided differences 2 [(y3 - y2)/(f3 - f2) - (y2 - y1)/(f2 - f1)] / (f3 - f1) at the inner points
    (uneven spacing allowed); used by fan_design.smoothness (spanwise smoothness report)."""
    return [2 * ((ys[i + 1] - ys[i]) / (fs[i + 1] - fs[i]) - (ys[i] - ys[i - 1]) / (fs[i] - fs[i - 1]))
            / (fs[i + 1] - fs[i - 1]) for i in range(1, len(fs) - 1)]


def chord_roughness_metric(fs: list[float], chords: list[float]) -> dict:
    """R-AM.17 metric (M1 step 4i) [H]: chord roughness = largest |c/c_mean - q(f)| over the span stations, q =
    least-squares quadratic fit of c/c_mean over the same stations, c_mean = arithmetic mean of the station chords.
    A plain quadratic scores 0, a local bump high. Also where it occurs and the RMS residual."""
    c_mean = sum(chords) / len(chords)
    ys = [c / c_mean for c in chords]
    q = polyfit(fs, ys, 2)
    res = [y - polyval(q, f) for f, y in zip(fs, ys)]
    j = max(range(len(res)), key=lambda i: abs(res[i]))
    return {"metric": abs(res[j]), "at_station_0based": j, "at_span_fraction": fs[j], "c_mean": c_mean,
            "residuals": res, "rms": math.sqrt(sum(x * x for x in res) / len(res)), "fit": q}


def rotor67_chord_roughness(geometry: dict | None = None) -> dict:
    """R-AM.17 limit [H from KS]: chord_roughness_metric on the 14 Rotor 67 Table I sections, chord from
    rotor67_geometry.yaml (cm), span fraction = leading-edge radius fraction (rotor67_section_spans, as R-AM.14)."""
    geo = geometry or read_yaml(R67_GEOMETRY)
    fs = rotor67_section_spans(geo)
    chords = [s["chord"]["value"] for s in geo["sections"]]
    out = chord_roughness_metric(fs, chords)
    out["section"] = out.pop("at_station_0based") + 1
    out["c_mean_cm"] = out.pop("c_mean")
    return out


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
