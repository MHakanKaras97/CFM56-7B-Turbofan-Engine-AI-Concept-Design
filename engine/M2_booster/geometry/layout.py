"""M2 geometry step 1: frame, record inputs, axial layout and flow path (rules/geometry.md R-G2.1, R-G2.2, R-G2.5).

All design values come from the active M2 record (results.yaml via core.records.read_revision) and from
geometry/flowpath.yaml after its sha256 is checked against the record manifest. Station 21 (x, tip radius) is read
from the M1 file engine/M1_inlet_fan/geometry/flowpath.yaml (read-only, interface M2_station_21). Rule constants are
in geometry/geometry_params.yaml.

Frame (R-G2.1, M1 convention, re-implemented locally, M1 not imported): X engine axis positive aft, origin on the
axis in the fan rotor stacking plane, Y/Z radial plane, metres; reference blade at +Z, tangential +Y; rotation
positive about +X (at +Z a rotor blade moves towards -Y).
"""

import hashlib
import math
from functools import lru_cache
from pathlib import Path

import cadquery as cq

from core import records
from core.util import read_yaml

HERE = Path(__file__).resolve().parent
M2_DIR = HERE.parent
ROOT = records.ROOT
PARAMS = HERE / "geometry_params.yaml"
M1_FLOWPATH = ROOT / "engine" / "M1_inlet_fan" / "geometry" / "flowpath.yaml"
M2_FLOWPATH = HERE / "flowpath.yaml"
CACHE = ROOT / ".cache" / "geometry" / "M2_booster"

AXIS_ORIGIN = (0.0, 0.0, 0.0)
AXIS_DIR = (1.0, 0.0, 0.0)
ROTATION_SIGN = +1  # positive about +X (R-G2.1)
# tangential sign (Y) of the rotor blade motion at +Z: d/dt of (0, 0, r) under +X rotation is -Y
ROTOR_MOTION_Y = -1


def v(q):
    return q["value"] if isinstance(q, dict) else q


def geometry_params() -> dict:
    return read_yaml(PARAMS)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=4)
def _record_cached(rev: str) -> dict:
    manifest = records.read_revision("M2", rev, "manifest.yaml")
    results = records.read_revision("M2", rev, "results.yaml")
    params = records.read_revision("M2", rev, "params.yaml")
    sha = {o["file"]: o["sha256"] for o in manifest["outputs"]}
    if _sha256(M2_FLOWPATH) != sha.get("geometry/flowpath.yaml"):
        raise ValueError(f"geometry/flowpath.yaml does not match record {rev}")
    return {"revision": rev, "manifest": manifest, "results": results, "params": params,
            "flowpath": read_yaml(M2_FLOWPATH)}


def record(rev: str | None = None) -> dict:
    return _record_cached(rev or records.active_revision("M2"))


def station_21() -> dict:
    """M1 interface M2_station_21 (x, hub, tip radius, area)."""
    s = read_yaml(M1_FLOWPATH)["interfaces"]["M2_station_21"]
    return {"x": float(s["x_m"]), "r_hub": float(s["r_hub_m"]), "r_tip": float(s["r_tip_m"]),
            "area": float(s["area_m2"])}


def _rows_table(sec: dict) -> dict:
    cols = sec["columns"]
    return {row[0]: dict(zip(cols, row)) for row in sec["rows"]}


def stagger(k1: float, k2: float) -> float:
    """Circular-arc stagger from the metal angles (R-G2.3), deg from axial."""
    return 0.5 * (k1 + k2)


def blade_rows(rev: str | None = None) -> list[dict]:
    """Rows R1 S1 R2 S2 R3 S3 with count, chord, hub/mean/tip sections (radius, metal angles, record solidity)."""
    rec = record(rev)
    rows = []
    for st in rec["results"]["stages"]:
        n = st["stage"]
        for kind, sec_key, ang, count_key, chord_key in (
                ("rotor", "rotor_sections", ("beta1", "beta2"), "rotor_blades", "rotor_chord"),
                ("stator", "stator_sections", ("alpha1", "alpha2"), "stator_vanes", "stator_chord")):
            table = _rows_table(st[sec_key])
            sections = []
            for name in ("hub", "mean", "tip"):
                t = table[name]
                sections.append({"name": name, "r_le": float(t["r_le"]), "r_te": float(t["r_te"]),
                                 "r": 0.5 * (float(t["r_le"]) + float(t["r_te"])),
                                 "k1": float(t[ang[0]]), "k2": float(t[ang[1]]),
                                 "solidity": float(t["solidity"]), "DF": float(t["DF"])})
            rows.append({"stage": n, "kind": kind, "part_id": f"M2.{n}.{1 if kind == 'rotor' else 2}",
                         "name": f"Booster Stage {n} {'Rotor Blade' if kind == 'rotor' else 'Stator Vane'}",
                         "count": int(v(st[count_key])), "chord": float(v(st[chord_key])), "sections": sections})
    return rows


def layout(rev: str | None = None) -> dict:
    """Axial layout (R-G2.2) and flow path lines (R-G2.5) in the frame.

    Plane radii: geometry/flowpath.yaml planes (station 21, then rotor TE / stator TE of each stage; a row's LE
    shares the plane of the upstream row TE). Casing radius = M1 station 21 tip radius."""
    rec = record(rev)
    gp = geometry_params()
    s21 = station_21()
    planes = rec["flowpath"]["planes"]
    if abs(planes[0]["r_hub_m"] - s21["r_hub"]) > 1e-9 or abs(planes[0]["r_tip_m"] - s21["r_tip"]) > 1e-9:
        raise ValueError("M2 station 21 plane does not match the M1 interface")
    r_casing = s21["r_tip"]
    rows = blade_rows(rev)
    gap_f = float(v(gp["axial_gap_fraction"]))
    for r in rows:
        r["width"] = max(r["chord"] * math.cos(math.radians(stagger(s["k1"], s["k2"]))) for s in r["sections"])
    x = s21["x"] + gap_f * rows[0]["width"]
    hub = [(s21["x"], planes[0]["r_hub_m"])]
    for i, r in enumerate(rows):
        r["x_le"], r["x_te"] = x, x + r["width"]
        r["x_stack"] = 0.5 * (r["x_le"] + r["x_te"])
        r["hub_le"], r["hub_te"] = planes[i]["r_hub_m"], planes[i + 1]["r_hub_m"]
        hub += [(r["x_le"], r["hub_le"]), (r["x_te"], r["hub_te"])]
        x = r["x_te"] + gap_f * r["width"]
    x24 = rows[-1]["x_te"]
    return {"revision": rec["revision"], "station_21": s21, "x24": x24, "r_casing": r_casing,
            "hub_line": hub, "rows": rows}


def r_at(curve: list[tuple[float, float]], x: float) -> float:
    """Radius of a piecewise-linear meridional curve at x (constant beyond its ends)."""
    if x <= curve[0][0]:
        return curve[0][1]
    for (x0, r0), (x1, r1) in zip(curve, curve[1:]):
        if x <= x1:
            return r0 if x1 == x0 else r0 + (r1 - r0) * (x - x0) / (x1 - x0)
    return curve[-1][1]


def revolve_closed(points: list[tuple[float, float]]) -> cq.Solid:
    """Axisymmetric solid from a closed meridional polygon of (x, r) points, full turn about X."""
    solid = cq.Workplane("XY").polyline(points).close().revolve(360.0, (0, 0, 0), (1, 0, 0)).val()
    if not solid.isValid() or solid.Volume() <= 0:
        raise ValueError("revolved solid is not valid")
    return solid


def band(hub: list[tuple[float, float]], x0: float, x1: float, r_out: float) -> cq.Solid:
    """Revolved region between the hub line and radius r_out over x0..x1."""
    pts = [(x0, r_at(hub, x0))] + [(x, r) for x, r in hub if x0 < x < x1] + [(x1, r_at(hub, x1))]
    pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
    return revolve_closed(pts + [(x1, r_out), (x0, r_out)])


def flowpath_solid(lay: dict) -> cq.Solid:
    """Annulus from station 21 to station 24 (hub line to casing)."""
    return band(lay["hub_line"], lay["station_21"]["x"], lay["x24"], lay["r_casing"])


def annulus_cut_area(solid: cq.Shape, x: float, size: float = 2.0) -> float:
    """Area of the planar cut of a solid at axial position x."""
    plane = cq.Face.makePlane(size, size, basePnt=cq.Vector(x, 0, 0), dir=cq.Vector(1, 0, 0))
    return solid.intersect(plane).Area()


def area_planes(lay: dict) -> list[dict]:
    """Record planes with their axial position and record area (station 21, row LE/TE planes)."""
    rec = record(lay["revision"])
    out = [{"plane": "station 21", "x": lay["station_21"]["x"], "area": float(rec["results"]["station_21"]["area"])}]
    for st in rec["results"]["stages"]:
        rot, sta = (r for r in lay["rows"] if r["stage"] == st["stage"])
        pl = st["planes"]
        out += [{"plane": f"stage {st['stage']} rotor LE", "x": rot["x_le"], "area": float(pl["rotor_le"]["area"])},
                {"plane": f"stage {st['stage']} rotor TE", "x": rot["x_te"], "area": float(pl["rotor_te"]["area"])},
                {"plane": f"stage {st['stage']} stator TE", "x": sta["x_te"], "area": float(pl["stator_te"]["area"])}]
    return out


def area_check(lay: dict | None = None) -> list[dict]:
    lay = lay or layout()
    tol = float(v(geometry_params()["area_tolerance"]))
    fp = flowpath_solid(lay)
    out = []
    x0, x1 = lay["station_21"]["x"], lay["x24"]
    for p in area_planes(lay):
        a = annulus_cut_area(fp, min(max(p["x"], x0 + 1e-7), x1 - 1e-7))  # end planes: cut just inside
        dev = a / p["area"] - 1.0
        out.append({**p, "area_geometry": a, "deviation": dev, "pass": abs(dev) <= tol})
    return out
