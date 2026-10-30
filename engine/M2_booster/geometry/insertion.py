"""M2 geometry step 3c: blade root insertion as an exact swept solid (rules/geometry.md R-G2.19 amended, R-G2.21,
open issue #81).

Gate (R-G2.21): per rotor row the root block of blade 0 is moved along the straight slot axis (R-G2.19 amended) from
fully aft of the rim aft face (axial displacement = rim length) to the seated position. The volume it sweeps is built
exactly as one solid (start block, seated block and the prism of every face not parallel to the motion). The sweep is
clear only if the common volume of that swept solid with the drum (incl. the R-G2.20 hub wall and the seal teeth), the
forward cone (R-G2.18) and the seated neighbouring root blocks of the same row is at most `hw_common_volume_tolerance`
x block volume (R-G2.17 tolerance).

Information only (not a gate): the stator-1 hardware the R1 swept solid would cross if it were already fitted (R-G2.21
assembly sequence: stators after the rotor blades): inner shroud ring, seal land, vane airfoils, vane feet; common
volume and axial / radial extents.

No dimension is tuned; path and gate come from the rules. Inputs: hardware.build() (active record rev001, M1 rev014
read-only).

Run: python -m engine.M2_booster.geometry.insertion
"""

import math

import cadquery as cq
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Vec

from engine.M2_booster.geometry import hardware as HW
from engine.M2_booster.geometry import layout as L

PARALLEL_TOL = 1e-9  # |face normal . motion| below this: planar face parallel to the motion, no prism [T]


def insertion_path(H: dict, k: int = 0) -> dict:
    """R-G2.21 path of the root block of rotor row k [H]: straight line along the R-G2.19 (amended) slot axis of blade
    0 (displacement per axial metre (1, e_c,y / e_c,x, slot_slope)). Start: axial displacement u0 = rim length (block
    x_min on the rim aft face, block fully aft of the rim); end: u = 0 (seated)."""
    rim = H["rims"][k]
    d = HW.slot_axis_dir(rim)
    u0 = rim["x_a"] - rim["x_f"]
    return {"row": rim["row"]["part_id"], "direction_per_axial_m": d, "slope": rim["slot_slope"], "u_start": u0,
            "path_length": u0 * math.sqrt(sum(c * c for c in d))}


def _moved(s: cq.Shape, d: tuple, u: float) -> cq.Shape:
    return s.translate(cq.Vector(d[0] * u, d[1] * u, d[2] * u))


def _prism(f: cq.Face, v: cq.Vector) -> cq.Solid:
    return cq.Solid(BRepPrimAPI_MakePrism(f.wrapped, gp_Vec(v.x, v.y, v.z)).Shape())


def _halves_y0(f: cq.Face) -> list[cq.Face]:
    """Face split by the blade-0 meridian plane y = 0."""
    big = 10.0
    out = []
    for y0 in (-big, 0.0):
        box = cq.Solid.makeBox(2 * big, big, 2 * big, pnt=cq.Vector(-big, y0, -big))
        out += f.intersect(box).Faces()
    return out


def swept_solid(s: cq.Solid, v: cq.Vector) -> cq.Solid:
    """Exact volume swept by solid s translated along v: union of s, s + v and the prism of every face along v.
    A point of the swept volume outside s and s + v lies on a segment (direction v, length < |v|) that starts on a
    face of s, so it is inside that face's prism. Planar faces parallel to v give no volume and are skipped. A face
    whose prism is not valid (v tangent to the face inside it: the hub cone on the blade meridian, because the slot
    axis rises with the hub slope, R-G2.19) is split on the meridian plane y = 0 (the silhouette) and each half is
    extruded; if a half is still not valid the build stops."""
    vn = v.normalized()
    pieces = [_moved(s, (v.x, v.y, v.z), 1.0)]
    for f in s.Faces():
        if f.geomType() == "PLANE" and abs(f.normalAt().dot(vn)) < PARALLEL_TOL:
            continue
        p = _prism(f, v)
        if p.isValid():
            pieces.append(p)
            continue
        for h in _halves_y0(f):
            ph = _prism(h, v)
            if not ph.isValid():
                raise ValueError(f"prism of a {f.geomType()} face half is not valid")
            pieces.append(ph)
    out = s.fuse(*pieces).clean().Solids()
    if len(out) != 1 or not out[0].isValid():
        raise ValueError(f"swept solid: {len(out)} solids, expected one valid solid")
    return out[0]


def _box_around(shapes: list[cq.Shape], pad: float) -> cq.Solid:
    bb = [s.BoundingBox() for s in shapes]
    x0, y0, z0 = min(b.xmin for b in bb) - pad, min(b.ymin for b in bb) - pad, min(b.zmin for b in bb) - pad
    x1, y1, z1 = max(b.xmax for b in bb) + pad, max(b.ymax for b in bb) + pad, max(b.zmax for b in bb) + pad
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, pnt=cq.Vector(x0, y0, z0))


def _bb_hit(a: cq.Shape, b: cq.Shape) -> bool:
    ba, bb = a.BoundingBox(), b.BoundingBox()
    return not (ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin
                or ba.zmax < bb.zmin or bb.zmax < ba.zmin)


def _overlap(a: cq.Shape, b: cq.Shape) -> dict:
    """Common volume of a and b with its axial and radial extents (edge samples); zeros if no common solid."""
    zero = {"volume": 0.0, "x": None, "axial": 0.0, "r": None, "radial": 0.0}
    if not _bb_hit(a, b):
        return zero
    sol = a.intersect(b).Solids()
    vol = sum(s.Volume() for s in sol)
    if vol <= 0.0:
        return zero
    com = cq.Compound.makeCompound(sol)
    bb = com.BoundingBox()
    rs = [math.hypot(p.y, p.z) for e in com.Edges() for p in (e.positionAt(t) for t in (0.0, 0.25, 0.5, 0.75, 1.0))]
    return {"volume": vol, "x": (bb.xmin, bb.xmax), "axial": bb.xmax - bb.xmin, "r": (min(rs), max(rs)),
            "radial": max(rs) - min(rs)}


def _instances(s: cq.Shape, n: int, region: cq.Shape) -> list[cq.Shape]:
    out = []
    for k in range(-(n // 2), n - n // 2):
        sk = HW.rotate(s, 360.0 * k / n) if k else s
        if _bb_hit(sk, region):
            out.append(sk)
    return out


def stator1_parts(hb: dict) -> dict:
    """Stator-1 hardware (information only): shroud ring (R-G2.11, without the land), seal land ring, vane airfoil and
    vane foot (blade 0; instances near the path are added by the caller), and the drum seal teeth under S1 (part of
    M2.0.1, already in the drum gate)."""
    H, rows = hb["hw"], hb["model"]["rows"]
    sh = H["shrouds"][0]
    s1 = next(r for r in rows if r["kind"] == "stator")
    ring = L.revolve_closed(HW._dedupe([(sh["x_f"], sh["r_shroud_in"])] + HW.hub_points(H["hub"], sh["x_f"], sh["x_a"])
                                       + [(sh["x_a"], sh["r_shroud_in"])]))
    (l0, l1) = sh["land_x"]
    land = L.revolve_closed([(l0, sh["r_land_in"]), (l1, sh["r_land_in"]), (l1, sh["r_shroud_in"]),
                             (l0, sh["r_shroud_in"])])
    teeth = []
    for xc in sh["tooth_x"]:
        x0, x1 = xc - 0.5 * sh["tooth_width"], xc + 0.5 * sh["tooth_width"]
        teeth.append(L.revolve_closed([(x0, sh["r_wall_out"]), (x1, sh["r_wall_out"]), (x1, sh["r_tooth_tip"]),
                                       (x0, sh["r_tooth_tip"])]))
    return {"part_id": s1["part_id"], "count": s1["count"], "shroud_ring": ring, "seal_land": land,
            "seal_teeth (drum)": teeth, "vane": s1["solid"], "foot": hb["parts"]["feet"][0]}


def _rows(sw: cq.Solid, named: dict, ref_volume: float, tol: float | None) -> dict:
    """Common volume of the swept solid with every named list of solids (summed), extents of the largest piece."""
    out = {}
    for n, lst in named.items():
        o = [_overlap(sw, s) for s in lst]
        vol = sum(r["volume"] for r in o)
        big = max(o, key=lambda r: r["volume"]) if o else {"x": None, "axial": 0.0, "r": None, "radial": 0.0}
        row = {"volume": vol, "fraction": vol / ref_volume, "instances": len(lst), "x": big["x"],
               "axial": big["axial"], "r": big["r"], "radial": big["radial"]}
        if tol is not None:
            row["pass"] = row["fraction"] <= tol
        out[n] = row
    return out


def sweep_stage(hb: dict, k: int, info: bool = False) -> dict:
    """R-G2.21 gate of rotor row k (aft insertion, exact swept solid) [H]; info: stator-1 crossing (row 0 only)."""
    H, P = hb["hw"], hb["parts"]
    tol = HW._p(hb["model"]["params"], "hw_common_volume_tolerance")
    path = insertion_path(H, k)
    d, u0 = path["direction_per_axial_m"], path["u_start"]
    rim, root = H["rims"][k], P["roots"][k]
    sw = swept_solid(root, cq.Vector(d[0] * u0, d[1] * u0, d[2] * u0))
    region = _box_around([sw], 2.0 * rim["slot_width"])
    n = rim["row"]["count"]
    gate = {"M2.0.1 drum (incl. hub wall, teeth)": [P["drum"].intersect(region)],
            "M2.0.1 forward cone": [HW.forward_cone(H)],
            "seated neighbour roots (-1, +1)": [HW.rotate(root, -360.0 / n), HW.rotate(root, 360.0 / n)]}
    v_blk = root.Volume()
    rows = _rows(sw, gate, v_blk, tol)
    out = {"path": path, "block_volume": v_blk, "swept_volume": sw.Volume(), "tolerance": tol, "gate": rows,
           "clear": all(r["pass"] for r in rows.values()), "start_x_min": _moved(root, d, u0).BoundingBox().xmin,
           "x_rim_aft": rim["x_a"]}
    if info:
        s1 = stator1_parts(hb)
        infos = {"S1 inner shroud ring": [s1["shroud_ring"]], "S1 seal land": [s1["seal_land"]],
                 "S1 drum seal teeth (in drum gate)": s1["seal_teeth (drum)"],
                 "S1 vane airfoil": _instances(s1["vane"], s1["count"], region),
                 "S1 vane foot": _instances(s1["foot"], s1["count"], region)}
        out["stator1"] = _rows(sw, infos, v_blk, None)
    return out


def sweep(hb: dict | None = None, info: bool = True) -> dict:
    """R-G2.21 gate for R1, R2, R3 (one swept solid and one boolean per obstacle per stage) [H]."""
    hb = hb or HW.build()
    stages = [sweep_stage(hb, k, info=info and k == 0) for k in range(len(hb["hw"]["rims"]))]
    return {"stages": stages, "clear": all(s["clear"] for s in stages), "stator1": stages[0].get("stator1", {})}


def r1_seated_fit(hb: dict | None = None) -> dict:
    """R-G2.21 seated condition of the R1 root block [H]: distance to the hub wall region of the drum (x < station 21,
    stop face, contact expected) and to the drum region x >= station 21 (non-stop faces: slot sides and bottom,
    R-G2.19 fit check), common volume with the whole drum."""
    hb = hb or HW.build()
    H, P = hb["hw"], hb["parts"]
    rim, root = H["rims"][0], P["roots"][0]
    region = _box_around([root], 2.0 * rim["slot_width"])
    local = P["drum"].intersect(region)
    bb = region.BoundingBox()
    ahead = cq.Solid.makeBox(H["x21"] - bb.xmin + 1.0, 2.0, 2.0, pnt=cq.Vector(bb.xmin - 1.0, -1.0, -1.0))
    return {"row": rim["row"]["part_id"], "fit": rim["fit"], "distance_stop": root.distance(local.intersect(ahead)),
            "distance_non_stop": root.distance(local.cut(ahead)),
            "common_fraction": HW.common_fraction(root, P["drum"])}


def main() -> None:
    hb = HW.build()
    print("seated", r1_seated_fit(hb))
    for rim in hb["hw"]["rims"]:
        keys = ("slot_slope", "slot_extra_depth", "slot_depth_min_rim", "slot_depth", "aft_face_margin",
                "front_face_margin", "live_rim")
        print("slot", rim["row"]["part_id"], {k: rim[k] for k in keys})
    res = sweep(hb)
    print("clear", res["clear"])
    for s in res["stages"]:
        print("stage", s["path"]["row"], "clear", s["clear"], "block", s["block_volume"], "swept", s["swept_volume"])
        for n, g in s["gate"].items():
            print("  gate", n, g)
    for n, r in res["stator1"].items():
        print("S1 info", n, r)


if __name__ == "__main__":
    main()
