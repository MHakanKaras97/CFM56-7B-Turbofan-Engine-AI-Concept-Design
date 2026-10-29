"""M2 geometry step 1: blade solids of the 3 rotor and 3 stator rows (rules/geometry.md R-G2.3, R-G2.4, R-G2.6-8).

Each blade is lofted from planar hub/mean/tip sections (record radii, flow angles as metal angles, record chord) plus
one extension copy beyond hub and tip, then cut by the revolved flow path (rotor: hub line to casing - tip
clearance; stator: hub line to casing). Sections: circular-arc camber line, parabolic thickness with blunt edges.

Run: python -m engine.M2_booster.geometry.blades  (prints the checks and writes one STEP per part to
.cache/geometry/M2_booster/<rev>/)
"""

import math
from functools import lru_cache
from pathlib import Path

import cadquery as cq
import numpy as np

from core.util import read_yaml
from engine.M2_booster.geometry import layout as L

MATERIALS = L.ROOT / "tools" / "data" / "materials.yaml"
N_POINTS = 40  # points per surface spline [T]


def _d(a_deg: float, sign: int) -> np.ndarray:
    a = math.radians(a_deg)
    return np.array([math.cos(a), sign * math.sin(a)])


def tangential_sign(kind: str) -> int:
    """Y sign of the tangential flow component seen by the row (R-G2.1): rotor relative flow runs against the
    blade motion, stator absolute swirl runs with it."""
    return -L.ROTOR_MOTION_Y if kind == "rotor" else L.ROTOR_MOTION_Y


def thickness_ratio(kind: str, section: str, gp: dict) -> float:
    if kind == "stator":
        return float(L.v(gp["stator_tc"]))
    hub, tip = float(L.v(gp["rotor_tc_hub"])), float(L.v(gp["rotor_tc_tip"]))
    return {"hub": hub, "mean": 0.5 * (hub + tip), "tip": tip}[section]


def section_points(c: float, k1: float, k2: float, tc: float, te_c: float, sign: int, x_mid: float,
                   n: int = N_POINTS) -> tuple[np.ndarray, np.ndarray]:
    """Upper and lower surface points (x, y) of one section, LE -> TE (R-G2.3). Chord midpoint at (x_mid, 0)."""
    gam, th = L.stagger(k1, k2), k1 - k2
    e_c, e_n = _d(gam, sign), _d(gam + 90.0, sign)
    u = 0.5 * c * (1.0 - np.cos(np.linspace(0.0, math.pi, n + 1)))
    s = u - 0.5 * c
    if abs(th) < 1e-6:
        h, dh = np.zeros_like(u), np.zeros_like(u)
    else:
        R = c / (2.0 * math.sin(abs(math.radians(th)) / 2.0))
        sg = math.copysign(1.0, th)
        root = np.sqrt(R * R - s * s)
        h = sg * (root - math.sqrt(R * R - 0.25 * c * c))
        dh = -sg * s / root
    t = te_c * c + (tc - te_c) * c * (1.0 - (2.0 * u / c - 1.0) ** 2)
    cam = np.array([x_mid, 0.0]) + np.outer(s, e_c) + np.outer(h, e_n)
    phi = gam + np.degrees(np.arctan(dh))
    nn = np.stack([-np.sin(np.radians(phi)), sign * np.cos(np.radians(phi))], axis=1)
    return cam + 0.5 * t[:, None] * nn, cam - 0.5 * t[:, None] * nn


def section_wire(upper: np.ndarray, lower: np.ndarray, z: float) -> cq.Wire:
    up = [cq.Vector(x, y, z) for x, y in upper]
    lo = [cq.Vector(x, y, z) for x, y in lower[::-1]]
    edges = [cq.Edge.makeSpline(up), cq.Edge.makeLine(up[-1], lo[0]), cq.Edge.makeSpline(lo),
             cq.Edge.makeLine(lo[-1], up[0])]
    return cq.Wire.assembleEdges(edges)


def tip_clearance(row: dict, lay: dict, gp: dict) -> float:
    """R-G2.6; rotors only."""
    if row["kind"] != "rotor":
        return 0.0
    ratio = float(L.v(gp["tip_clearance_source_cm"])) / float(L.v(gp["rig_blade_height_cm"]))
    return ratio * row_height(row, lay)


def row_height(row: dict, lay: dict) -> float:
    return lay["r_casing"] - 0.5 * (row["hub_le"] + row["hub_te"])


def build_row(row: dict, lay: dict, gp: dict) -> dict:
    sign = tangential_sign(row["kind"])
    te_c = float(L.v(gp["edge_thickness_ratio"]))
    secs = {s["name"]: s for s in row["sections"]}
    ext = float(L.v(gp["span_extension_ratio"])) * row_height(row, lay)
    hub_min = min(row["hub_le"], row["hub_te"])
    clr = tip_clearance(row, lay, gp)
    r_cut = lay["r_casing"] - clr
    issues = []
    if secs["hub"]["r"] - ext >= hub_min or secs["tip"]["r"] + ext <= r_cut:
        issues.append("span extension does not reach the flow path (stop rule)")
    wires = []
    for name, z in (("hub", secs["hub"]["r"] - ext), ("hub", secs["hub"]["r"]), ("mean", secs["mean"]["r"]),
                    ("tip", secs["tip"]["r"]), ("tip", secs["tip"]["r"] + ext)):
        s = secs[name]
        up, lo = section_points(row["chord"], s["k1"], s["k2"], thickness_ratio(row["kind"], name, gp), te_c,
                                sign, row["x_stack"])
        wires.append(section_wire(up, lo, z))
    loft = cq.Solid.makeLoft(wires, False)
    trim = L.band(lay["hub_line"], row["x_le"] - row["width"], row["x_te"] + row["width"], r_cut)
    blade = loft.intersect(trim)
    solids = blade.Solids()
    if len(solids) != 1 or not solids[0].isValid():
        issues.append("trimmed blade is not one valid solid (stop rule)")
    return {**row, "solid": solids[0] if solids else blade, "clearance": clr, "r_cut": r_cut, "extension": ext,
            "issues": issues}


@lru_cache(maxsize=2)
def build(rev: str | None = None) -> dict:
    lay = L.layout(rev)
    gp = L.geometry_params()
    rows = [build_row(r, lay, gp) for r in lay["rows"]]
    return {"layout": lay, "rows": rows, "params": gp}


# --- checks (R-G2.8) -----------------------------------------------------------

def mean_section(row: dict) -> cq.Shape:
    s = next(s for s in row["sections"] if s["name"] == "mean")
    plane = cq.Face.makePlane(1.0, 1.0, basePnt=cq.Vector(row["x_stack"], 0, s["r"]), dir=cq.Vector(0, 0, 1))
    return row["solid"].intersect(plane)


def measured_chord(row: dict) -> float:
    """Chord of the mean section cut [H]: distance between the midpoints of its two blunt edge lines (LE, TE), i.e.
    the camber line end points (aero_method.md chord: straight line LE to TE)."""
    edges = sorted(mean_section(row).Edges(), key=lambda e: e.Length())[:2]
    a, b = (e.positionAt(0.5) for e in edges)
    return (a - b).Length


def chord_solidity_check(row: dict, tol: float) -> dict:
    s = next(s for s in row["sections"] if s["name"] == "mean")
    c = measured_chord(row)
    r_m = 0.5 * (s["r_le"] + s["r_te"])
    sol = c * row["count"] / (2.0 * math.pi * r_m)
    dc, ds = c / row["chord"] - 1.0, sol / s["solidity"] - 1.0
    return {"chord": c, "chord_record": row["chord"], "chord_dev": dc, "solidity": sol,
            "solidity_record": s["solidity"], "solidity_dev": ds, "pass": abs(dc) <= tol and abs(ds) <= tol}


def radius_check(row: dict, lay: dict, tol: float) -> dict:
    """Root vertices on the hub line, tip vertices on casing - clearance."""
    mid = 0.5 * (row["hub_le"] + row["r_cut"])
    root, tip = [], []
    for vx in row["solid"].Vertices():
        r = math.hypot(vx.Y, vx.Z)
        if r < mid:
            root.append(abs(r - L.r_at(lay["hub_line"], vx.X)))
        else:
            tip.append(abs(r - row["r_cut"]))
    rs = [math.hypot(vx.Y, vx.Z) for vx in row["solid"].Vertices()]
    return {"r_min": min(rs), "r_max": max(rs), "root_dev_max": max(root), "tip_dev_max": max(tip),
            "n_root": len(root), "n_tip": len(tip), "pass": bool(root and tip and max(root + tip) <= tol)}


def neighbour_check(row: dict) -> dict:
    a = row["solid"]
    b = a.rotate(cq.Vector(*L.AXIS_ORIGIN), cq.Vector(*L.AXIS_DIR), L.ROTATION_SIGN * 360.0 / row["count"])
    common = a.intersect(b)
    vol = sum(s.Volume() for s in common.Solids()) if common.Solids() else 0.0
    dist = a.distance(b)
    return {"common_volume": vol, "min_distance": dist, "pass": vol == 0.0 and dist > 0.0}


def density(material: str) -> float:
    return float(read_yaml(MATERIALS)["materials"][material]["density"]["value"])


def mass(row: dict, gp: dict) -> dict:
    mat = L.v(gp["rotor_material"] if row["kind"] == "rotor" else gp["stator_mass_material"])
    vol = row["solid"].Volume()
    rho = density(mat)
    return {"material": mat, "volume_blade": vol, "mass_blade": vol * rho, "mass_row": vol * rho * row["count"]}


def checks(model: dict | None = None) -> dict:
    model = model or build()
    gp, lay = model["params"], model["layout"]
    tol_c, tol_r = float(L.v(gp["chord_solidity_tolerance"])), float(L.v(gp["radius_tolerance_m"]))
    out = {"areas": L.area_check(lay), "rows": []}
    for r in model["rows"]:
        out["rows"].append({"part_id": r["part_id"], "count": r["count"], "issues": r["issues"],
                            "x_le": r["x_le"], "x_te": r["x_te"], "clearance": r["clearance"],
                            "chord_solidity": chord_solidity_check(r, tol_c), "radii": radius_check(r, lay, tol_r),
                            "neighbour": neighbour_check(r), "mass": mass(r, gp)})
    return out


# --- export --------------------------------------------------------------------

def step_dir(rev: str) -> Path:
    return L.CACHE / rev


def export(model: dict | None = None) -> list[Path]:
    """One STEP per part (one blade per row) and the flow path reference solid."""
    model = model or build()
    rev = model["layout"]["revision"]
    out = []
    for r in model["rows"]:
        path = step_dir(rev) / f"{r['part_id'].replace('.', '_')}_{r['kind']}.step"
        path.parent.mkdir(parents=True, exist_ok=True)
        cq.exporters.export(cq.Workplane().add(r["solid"]), str(path), exportType="STEP")
        out.append(path)
    path = step_dir(rev) / "flowpath_reference.step"
    cq.exporters.export(cq.Workplane().add(L.flowpath_solid(model["layout"])), str(path), exportType="STEP")
    return out + [path]


def main() -> None:
    model = build()
    res = checks(model)
    lay = model["layout"]
    print(f"revision {lay['revision']}  x21 {lay['station_21']['x']:.6f}  x24 {lay['x24']:.6f}  "
          f"r_casing {lay['r_casing']:.6f}")
    for a in res["areas"]:
        print(f"area {a['plane']:<20} x {a['x']:.5f}  geo {a['area_geometry']:.6f}  rec {a['area']:.5f}  "
              f"dev {a['deviation']:+.2e}  {'pass' if a['pass'] else 'FAIL'}")
    for r in res["rows"]:
        cs, rd, nb, m = r["chord_solidity"], r["radii"], r["neighbour"], r["mass"]
        print(f"{r['part_id']} N {r['count']:>2}  x {r['x_le']:.5f}-{r['x_te']:.5f}  clr {r['clearance'] * 1e3:.3f} mm  "
              f"c {cs['chord']:.5f}/{cs['chord_record']:.5f} ({cs['chord_dev']:+.1e})  "
              f"sig {cs['solidity']:.4f}/{cs['solidity_record']:.4f} ({cs['solidity_dev']:+.1e})  "
              f"r {rd['r_min']:.5f}-{rd['r_max']:.5f} dev {max(rd['root_dev_max'], rd['tip_dev_max']):.1e}  "
              f"nb V {nb['common_volume']:.1e} d {nb['min_distance'] * 1e3:.2f} mm  "
              f"V {m['volume_blade'] * 1e6:.2f} cm3  m_row {m['mass_row']:.3f} kg  {r['issues'] or ''}")
    for p in export(model):
        print("STEP", p)


if __name__ == "__main__":
    main()
