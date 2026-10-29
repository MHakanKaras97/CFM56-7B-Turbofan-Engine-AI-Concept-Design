"""Shared M1 geometry frame and helpers (step 5b); every M1 part script places its solids in this frame.

Frame [T]:
- X = engine axis, positive aft (flow direction); Y, Z radial plane; metres.
- Origin on the engine axis in the fan rotor stacking plane: x = 0 is where blade_solid stacks the section centroids.
- Reference blade (blade index 0) at top dead centre: radial = +Z, tangential = +Y. The 5a blade (blade_solid.py:
  X axial aft, Y tangential, Z radial) is already in this frame: identity transform, no design value changed.
- Rotor sense of rotation: positive about +X by the right-hand rule (geometry_params.yaml rotor.rotation_sense);
  blade k sits at angle k * 360 / N about +X.
- Meridional curves are lists of (x, r) points; revolving them about X gives the axisymmetric solids and surfaces.
"""

import math
from functools import lru_cache
from pathlib import Path

import cadquery as cq
from OCP.BOPAlgo import BOPAlgo_GlueFull
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Fuse
from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol
from OCP.TopTools import TopTools_ListOfShape
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt

from core import records
from core.util import read_yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PARAMS = HERE / "geometry_params.yaml"
CACHE = ROOT / ".cache" / "geometry" / "M1_inlet_fan"

AXIS_ORIGIN = (0.0, 0.0, 0.0)
AXIS_DIR = (1.0, 0.0, 0.0)
ROTATION_SIGN = +1  # positive about +X [T]


def v(q):
    return q["value"] if isinstance(q, dict) else q


def geometry_params() -> dict:
    return read_yaml(PARAMS)


@lru_cache(maxsize=4)
def _record(rev: str, name: str, root: Path):
    return records.read_revision("M1", rev, name, root)


def record(rev: str | None = None, root: Path = records.ROOT) -> dict:
    """results.yaml and params.yaml of the record `rev` (default: the active revision)."""
    rev = rev or records.active_revision("M1", root)
    return {"revision": rev, "results": _record(rev, "results.yaml", root), "params": _record(rev, "params.yaml", root)}


def radius(p) -> float:
    """Distance of a point (cq.Vector or tuple) from the engine axis."""
    y, z = (p.y, p.z) if hasattr(p, "y") else (p[1], p[2])
    return math.hypot(y, z)


def rotate_about_axis(shape: cq.Shape, angle_deg: float) -> cq.Shape:
    """Shape turned by angle_deg about the engine axis in the rotor sense."""
    return shape.rotate(cq.Vector(*AXIS_ORIGIN), cq.Vector(*AXIS_DIR), ROTATION_SIGN * angle_deg)


def revolve_closed(points: list[tuple[float, float]]) -> cq.Solid:
    """Axisymmetric solid from a closed meridional polygon of (x, r) points (r > 0), full turn about X."""
    wp = cq.Workplane("XY").polyline([(x, r) for x, r in points]).close()
    solid = wp.revolve(360.0, (0, 0, 0), (1, 0, 0)).val()
    if not solid.isValid() or solid.Volume() <= 0:
        raise ValueError("revolved solid is not valid")
    return solid


def revolve_open(points: list[tuple[float, float]]) -> cq.Shape:
    """Axisymmetric surface (shell) from an open meridional polyline of (x, r) points, full turn about X."""
    edges = [cq.Edge.makeLine(cq.Vector(x0, r0, 0), cq.Vector(x1, r1, 0))
             for (x0, r0), (x1, r1) in zip(points, points[1:]) if (x0, r0) != (x1, r1)]
    wire = cq.Wire.assembleEdges(edges)
    mk = BRepPrimAPI_MakeRevol(wire.wrapped, gp_Ax1(gp_Pnt(*AXIS_ORIGIN), gp_Dir(*AXIS_DIR)), 2 * math.pi)
    return cq.Shape.cast(mk.Shape())


def r_at(curve: list[tuple[float, float]], x: float) -> float:
    """Radius of a piecewise-linear meridional curve at axial position x (constant beyond its ends)."""
    if x <= curve[0][0]:
        return curve[0][1]
    for (x0, r0), (x1, r1) in zip(curve, curve[1:]):
        if x <= x1:
            return r0 if x1 == x0 else r0 + (r1 - r0) * (x - x0) / (x1 - x0)
    return curve[-1][1]


def boolean(kind: str, a: cq.Shape, b: cq.Shape, glue: bool = False) -> cq.Shape:
    """OCCT boolean ("common" or "fuse") with parallel run and oriented-bounding-box prefilter (same result as
    cq.Shape.intersect / fuse, faster on lofted solids). glue=True (full glue) only for shapes that touch on
    coincident faces and do not otherwise overlap."""
    op = {"common": BRepAlgoAPI_Common, "fuse": BRepAlgoAPI_Fuse}[kind]()
    args, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(a.wrapped)
    tools.Append(b.wrapped)
    op.SetArguments(args)
    op.SetTools(tools)
    op.SetRunParallel(True)
    op.SetUseOBB(True)
    if glue:
        op.SetGlue(BOPAlgo_GlueFull)
    op.Build()
    if not op.IsDone():
        raise RuntimeError(f"boolean {kind} failed")
    return cq.Shape.cast(op.Shape())


def step_dir(rev: str) -> Path:
    return CACHE / rev


def export_step(shape, name: str, rev: str, path: Path | None = None) -> Path:
    """One STEP per part: <cache>/<rev>/<name>.step."""
    path = path or step_dir(rev) / f"{name}.step"
    path.parent.mkdir(parents=True, exist_ok=True)
    wp = cq.Workplane()
    for s in shape if isinstance(shape, (list, tuple)) else [shape]:
        wp = wp.add(s)
    cq.exporters.export(wp, str(path), exportType="STEP")
    return path


def export_assembly(instances: list[tuple[str, cq.Shape, float]], name: str, rev: str, path: Path | None = None) -> Path:
    """STEP assembly of (instance name, shape, angle about the engine axis in the rotor sense in deg); repeated
    shapes are written once and placed by location (one part definition + qty)."""
    path = path or step_dir(rev) / f"{name}.step"
    path.parent.mkdir(parents=True, exist_ok=True)
    assy = cq.Assembly(name=name)
    for inst, shape, angle in instances:
        loc = cq.Location(cq.Vector(*AXIS_ORIGIN), cq.Vector(*AXIS_DIR), ROTATION_SIGN * angle)
        assy.add(shape, name=inst, loc=loc)
    assy.export(str(path), exportType="STEP")
    return path
