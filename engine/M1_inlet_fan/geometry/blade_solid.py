"""M1 fan rotor blade airfoil solid (M1.1.1, step 5a) from the active record, CadQuery.

Inputs: only the active record's params.yaml and results.yaml (records/ACTIVE), plus the Ti-6Al-4V density of
tools/data/materials.yaml (the same value fan_design.mechanical_inputs uses). No new design values.

Section at span fraction f (inlet radius r = r_hub1 + f (r_tip1 - r_hub1), the span variable of the record):
- chord: record chord law (quadratic, results blade.chord_law) [H];
- area: A(f) = A_root (1 - (1 - taper) f) (results blade.area_law) [H]; t/c = A / (k chord^2), k = 2/3 [H];
- kappa1 = atan(omega r / V1) - design incidence (results blade.kappa1_form; omega from the tube U1 / r1) [H];
- kappa2: record total coefficients on the basis 1, f, f^2, f^3, B(f) (B = splitter blend, C2 quintic) [H];
- profile: R-AM.11 MCA family (blade_profile.camber_angle, blade_profile.thickness), front camber share and x_max
  from the record's Rotor 67 fits [T analogue]. The camber line is built over the straight chord: chord fraction
  x along the chord line, slope tan(kappa_c(x) - gamma), gamma = chord angle so that the line closes at the
  trailing edge; normal thickness t/c x chord x tau(x) laid off on both sides normal to the camber line.

Geometric details with no sourced value [T] (docs/open_issues.md): planar sections at constant radius stacked
radially through the section centroids (no lean, sweep or wrap onto the cylinder, the same idealisation as the
mass integral of fan_design.blade_mechanics); sharp leading and trailing edges (zero edge radius, the R-AM.11
profile ignores edge circles); airfoil from r_hub1 to r_tip1 (no tip clearance cut, no root fillet, no
airfoil-to-root transition, no platform or dovetail; the rising exit hub line is not trimmed).

Axes: X engine axis (aft positive), Y tangential, Z radial (blade at top dead centre); metres.
"""

import math
from pathlib import Path

import cadquery as cq
import numpy as np

from core import records
from core.util import read_yaml
from engine.M1_inlet_fan.analysis import blade_profile as bp

ROOT = Path(__file__).resolve().parents[3]
MATERIALS = ROOT / "tools" / "data" / "materials.yaml"
CACHE = ROOT / ".cache" / "geometry" / "M1_inlet_fan"

N_SECTIONS = 21  # loft sections, equally spaced in span fraction [T]
N_POINTS = 81  # points per surface spline, chord fractions with cosine spacing [T]


def v(q):
    return q["value"] if isinstance(q, dict) else q


def blade_inputs(rev: str | None = None, root: Path = records.ROOT) -> dict:
    """Section laws of the blade from the record `rev` (default: the active revision)."""
    rev = rev or records.active_revision("M1", root)
    res = records.read_revision("M1", rev, "results.yaml", root)
    par = records.read_revision("M1", rev, "params.yaml", root)
    b, ann, bl = res["blade"], res["annulus"], par["blading"]
    tube = res["tubes"][0]
    fits = b["profile_fits_rotor67"]
    return {
        "revision": rev,
        "r_hub": ann["r_hub1_m"], "r_tip": ann["r_tip1_m"],
        "chord": b["chord_law"]["coefficients_m"],
        "A_root": b["area_law"]["A_root_cm2"] * 1e-4, "taper": b["area_law"]["taper"],
        "kappa2_deg": b["kappa2_deg_coefficients_total"],
        "f_split": ann["splitter_span_fraction"],
        "blend_start": v(bl["splitter_blend_start"]), "blend_width": v(bl["splitter_blend_width"]),
        "omega": tube["U1_m_s"] / tube["r1_m"], "V1": tube["V1_m_s"],
        "incidence": math.radians(v(bl["design_incidence"])),
        "fits": {"coefficients": {"front": fits["front_camber_share"], "tc": fits["t_c_pass0_start_only"],
                                  "x_max": fits["x_max"]}},
        "blades": int(v(bl["blade_count"])),
        "rho": v(read_yaml(MATERIALS)["materials"]["ti6al4v"]["density"]),
    }


def splitter_blend(f: float, inp: dict) -> float:
    """Same form as fan_design.splitter_blend (C2 quintic smoothstep)."""
    x = min(1.0, max(0.0, (f - inp["f_split"] - inp["blend_start"]) / inp["blend_width"]))
    return x ** 3 * (10 - 15 * x + 6 * x * x)


def section_laws(f: float, inp: dict) -> dict:
    """Radius, chord, area, t/c, metal angles (rad) and profile parameters at span fraction f."""
    r = inp["r_hub"] + f * (inp["r_tip"] - inp["r_hub"])
    chord = bp.polyval(inp["chord"], f)
    area = inp["A_root"] * (1 - (1 - inp["taper"]) * f)
    basis = [1.0, f, f * f, f ** 3, splitter_blend(f, inp)]
    kappa2 = math.radians(sum(c * x for c, x in zip(inp["kappa2_deg"], basis)))
    kappa1 = math.atan(inp["omega"] * r / inp["V1"]) - inp["incidence"]
    fam = bp.family_at(inp["fits"], f)
    return {"f": f, "r": r, "chord": chord, "area": area, "tc": area / (bp.AREA_COEFFICIENT * chord * chord),
            "kappa1": kappa1, "kappa2": kappa2, "front": fam["front"], "x_max": fam["x_max"]}


def _camber_offsets(s: dict, gamma: float, xs: list[float], n: int = 2000) -> list[float]:
    """Camber-line offset from the chord line (per unit chord) at chord fractions xs, trapezoidal integration of
    tan(kappa_c - gamma) on n intervals."""
    grid = np.linspace(0.0, 1.0, n + 1)
    key = (s["kappa1"], s["kappa2"], s["front"], n)
    if s.get("_kc_key") != key:  # camber angles on the grid, cached on the section dict
        s["_kc_key"], s["_kc"] = key, np.array([bp.camber_angle(s["kappa1"], s["kappa2"], s["front"], x) for x in grid])
    slope = np.tan(s["_kc"] - gamma)
    y = np.concatenate(([0.0], np.cumsum((slope[1:] + slope[:-1]) / (2 * n))))
    return list(np.interp(xs, grid, y))


def chord_angle(s: dict) -> float:
    """Chord-line angle gamma (rad from the engine axis) at which the camber line closes on the chord line."""
    lo, hi = s["kappa2"] - 0.5, s["kappa1"] + 0.5
    for _ in range(80):
        mid = (lo + hi) / 2
        if _camber_offsets(s, mid, [1.0])[0] > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def section_points(s: dict, n: int = N_POINTS) -> dict:
    """Suction and pressure surface points (axial x, tangential y) of section s, leading edge to trailing edge,
    origin at the leading edge; sharp edges [T]."""
    gamma = chord_angle(s)
    xs = [(1 - math.cos(math.pi * j / (n - 1))) / 2 for j in range(n)]
    ys = _camber_offsets(s, gamma, xs)
    c, t = s["chord"], s["tc"] * s["chord"]
    cg, sg = math.cos(gamma), math.sin(gamma)
    upper, lower = [], []
    for x, y in zip(xs, ys):
        phi = bp.camber_angle(s["kappa1"], s["kappa2"], s["front"], x) - gamma  # camber slope angle to the chord
        half = 0.5 * t * bp.thickness(x, s["x_max"])
        for sign, pts in ((1, upper), (-1, lower)):
            u = c * x - sign * half * math.sin(phi)  # along the chord
            w = c * y + sign * half * math.cos(phi)  # normal to the chord
            pts.append((u * cg - w * sg, u * sg + w * cg))
    upper[0] = lower[0] = (0.0, 0.0)
    te = (c * cg, c * sg)
    upper[-1] = lower[-1] = te
    return {"upper": upper, "lower": lower, "gamma": gamma}


def polygon_area_centroid(pts: list[tuple[float, float]]) -> tuple[float, float, float]:
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        cr = x0 * y1 - x1 * y0
        a += cr
        cx += (x0 + x1) * cr
        cy += (y0 + y1) * cr
    a /= 2
    return abs(a), cx / (6 * a), cy / (6 * a)


def section_wire(s: dict) -> tuple[cq.Wire, dict]:
    """Closed wire of section s at height z = r, stacked on its centroid at x = y = 0 (radial stacking) [T]."""
    p = section_points(s)
    _, x0, y0 = polygon_area_centroid(p["upper"] + p["lower"][-2:0:-1])
    z = s["r"]

    def vec(q):
        return cq.Vector(q[0] - x0, q[1] - y0, z)

    up = cq.Edge.makeSpline([vec(q) for q in p["upper"]])
    lo = cq.Edge.makeSpline([vec(q) for q in p["lower"]])
    return cq.Wire.assembleEdges([up, lo]), p


def build(rev: str | None = None, n_sections: int = N_SECTIONS, root: Path = records.ROOT) -> dict:
    """Lofted airfoil solid and its section laws."""
    inp = blade_inputs(rev, root)
    secs = [section_laws(j / (n_sections - 1), inp) for j in range(n_sections)]
    wires = [section_wire(s)[0] for s in secs]
    solid = cq.Solid.makeLoft(wires, ruled=False)
    if not solid.isValid():
        raise ValueError("blade loft is not a valid solid")
    return {"inputs": inp, "sections": secs, "solid": solid}


def slice_section(solid: cq.Solid, z: float) -> cq.Face:
    """Planar cut of the solid at radius z (largest face of the intersection with the plane z)."""
    plane = cq.Face.makePlane(4.0, 4.0, basePnt=cq.Vector(0, 0, z), dir=cq.Vector(0, 0, 1))
    return max(solid.intersect(plane).Faces(), key=lambda fc: fc.Area())


def end_face(solid: cq.Solid, z: float) -> cq.Face:
    """Planar end face of the loft at radius z (root or tip section)."""
    return min(solid.Faces(), key=lambda fc: abs(fc.Center().z - z) + (0 if fc.geomType() == "PLANE" else 1))


def _edge_points(edge: cq.Edge, n: int) -> np.ndarray:
    """n + 1 points equally spaced in the curve parameter (arc-length spacing is far slower on spline edges)."""
    u0, u1 = edge._bounds()
    return np.array([edge.positionAt(u0 + (u1 - u0) * j / n, mode="parameter").toTuple() for j in range(n + 1)])


def face_chord_thickness(face: cq.Face, n: int = 2000) -> dict:
    """Chord and largest normal thickness of a section face [H, from the solid]: chord = distance between the two
    sharp-edge vertices of the outer wire (one edge per surface); thickness = largest over one surface of the
    shortest distance to the other surface (n points per surface)."""
    edges = face.outerWire().Edges()
    if len(edges) != 2:
        raise ValueError(f"section wire has {len(edges)} edges, expected 2 (suction and pressure surface)")
    a, b = edges[0], edges[1]
    p0, p1 = a.startPoint(), a.endPoint()
    pa, pb = _edge_points(a, n), _edge_points(b, n)
    dist = np.sqrt(((pa[:, None, :] - pb[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
    chord = (p1 - p0).Length
    return {"chord": chord, "thickness": float(dist.max()), "tc": float(dist.max()) / chord}


def acceptance(model: dict, record: dict) -> dict:
    """Numbers measured on the solid against the record [H]: volume x density vs the code airfoil mass, root and
    tip chord, root area and area ratio, t/c at hub, mid and tip (span fraction 0, 0.5, 1)."""
    solid, inp = model["solid"], model["inputs"]
    vol = solid.Volume()
    mass = vol * inp["rho"]
    zs = {"hub": inp["r_hub"], "mid": (inp["r_hub"] + inp["r_tip"]) / 2, "tip": inp["r_tip"]}
    faces = {"hub": end_face(solid, zs["hub"]), "mid": slice_section(solid, zs["mid"]), "tip": end_face(solid, zs["tip"])}
    meas = {k: dict(face_chord_thickness(fc), area=fc.Area()) for k, fc in faces.items()}

    def rel(a, b):
        return a / b - 1

    m_rec = record["mass_kg"]
    rows = {
        "mass_kg": (mass, m_rec),
        "chord_root_m": (meas["hub"]["chord"], record["chord_root_m"]),
        "chord_tip_m": (meas["tip"]["chord"], record["chord_tip_m"]),
        "A_root_cm2": (meas["hub"]["area"] * 1e4, record["A_root_cm2"]),
        "area_ratio": (meas["tip"]["area"] / meas["hub"]["area"], record["taper"]),
        "tc_hub": (meas["hub"]["tc"], record["tc"]["hub"]),
        "tc_mid": (meas["mid"]["tc"], record["tc"]["mid"]),
        "tc_tip": (meas["tip"]["tc"], record["tc"]["tip"]),
    }
    return {"volume_m3": vol, "mass_kg": mass,
            "rows": {k: {"solid": a, "record": b, "rel": rel(a, b)} for k, (a, b) in rows.items()}}


def record_values(rev: str | None = None, root: Path = records.ROOT) -> dict:
    """Acceptance reference values from the record's results.yaml [H]."""
    rev = rev or records.active_revision("M1", root)
    res = records.read_revision("M1", rev, "results.yaml", root)
    mech = res["mechanical"]
    pts = mech["thickness_check"]["points"]
    return {"mass_kg": mech["blade_mass"]["per_blade_kg"], "chord_root_m": mech["chord_root_m"],
            "chord_tip_m": mech["chord_tip_m"], "A_root_cm2": mech["area_root_cm2"], "taper": mech["taper_ratio"],
            "tc": {k: pts[k]["t_c"] for k in ("hub", "mid", "tip")}}


def export_step(model: dict, path: Path | None = None) -> Path:
    path = path or CACHE / model["inputs"]["revision"] / "fan_blade.step"
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(cq.Workplane().add(model["solid"]), str(path), exportType="STEP")
    return path


def main() -> None:
    model = build()
    acc = acceptance(model, record_values())
    path = export_step(model)
    print(f"{model['inputs']['revision']}: volume {acc['volume_m3']:.6e} m3, mass {acc['mass_kg']:.4f} kg")
    for k, row in acc["rows"].items():
        print(f"  {k:14s} solid {row['solid']:.5g}  record {row['record']:.5g}  rel {row['rel']:+.2e}")
    print(f"STEP: {path}")


if __name__ == "__main__":
    main()
