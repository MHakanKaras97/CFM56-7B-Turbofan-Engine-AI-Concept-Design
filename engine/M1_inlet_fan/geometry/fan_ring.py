"""M1 fan rotor blade ring (M1.1.1 x blade count), step 5b. CadQuery, frame.py axes.

Blade: the 5a airfoil (blade_solid.build, design values unchanged) plus a prismatic root stub [T]
(geometry_params.yaml rotor.root_stub_depth_over_span), trimmed by the blade-swept annulus of the record
(flowpath.rotor_trim_tool): hub line r_hub1 -> r_hub2, tip line r_tip1 -> r_tip2. The trim removes the parts of
the planar 5a sections that lie outside the record annulus (tip corners above r_tip1 off the y = 0 line, root
below the rising hub line, open issues #25, #26) [H].
Ring: blade count copies turned by 360 / N about +X in the rotor sense (frame.ROTATION_SIGN) [T].
Checks [H]: corner radii vs the record, pairwise interference (common volume), tip clearance to the casing wall.
"""

import math
from pathlib import Path

import cadquery as cq

from core import records
from engine.M1_inlet_fan.geometry import blade_solid as bs
from engine.M1_inlet_fan.geometry import flowpath as fpm
from engine.M1_inlet_fan.geometry import frame as fr


def trimmed_blade(fp: dict) -> dict:
    """Blade 0 (top dead centre) trimmed to the record annulus."""
    model = fp["blade"]
    inp = model["inputs"]
    raw = model["solid"]
    depth = fr.v(fr.geometry_params()["rotor"]["root_stub_depth_over_span"]) * (inp["r_tip"] - inp["r_hub"])
    root_face = bs.end_face(raw, inp["r_hub"])
    stub = cq.Solid.extrudeLinear(root_face, cq.Vector(0, 0, -depth))
    fused = fr.boolean("fuse", raw, stub, glue=True)  # stub shares the root face of the loft
    cut = fr.boolean("common", fused, fpm.rotor_trim_tool(fp)).Solids()
    if len(cut) != 1 or not cut[0].isValid():
        raise ValueError(f"trimmed blade: {len(cut)} solids, expected one valid solid")
    return {"solid": cut[0], "raw_volume_m3": raw.Volume(), "stub_depth_m": depth, "rho": inp["rho"]}


def corner_radii(solid: cq.Solid, r_mid: float) -> dict:
    """Radius and x of the four corner vertices: leading / trailing edge (min / max x) on the hub and tip sides."""
    vs = [(p.x, fr.radius(p)) for p in (vt.Center() for vt in solid.Vertices())]
    hub = [q for q in vs if q[1] < r_mid]
    tip = [q for q in vs if q[1] >= r_mid]
    return {"le_hub": min(hub), "te_hub": max(hub), "le_tip": min(tip), "te_tip": max(tip)}


def angular_extent_deg(solid: cq.Solid, n: int = 200) -> float:
    """Tangential angle range of the blade about the axis, from vertices and edge samples [H, sampled]. The extremes
    lie on the tip and root corner edges; a surface tessellation (0.2 mm) gave the same value at rev011."""
    pts = [vt.Center().toTuple() for vt in solid.Vertices()]
    for e in solid.Edges():
        pts.extend(map(tuple, bs._edge_points(e, n)))
    ang = [math.degrees(math.atan2(y, z)) for _, y, z in pts]
    return max(ang) - min(ang)


def ring(blade: cq.Solid, n: int) -> list[cq.Solid]:
    return [blade if k == 0 else fr.rotate_about_axis(blade, k * 360.0 / n) for k in range(n)]


def _bbox_overlap(a: cq.Shape, b: cq.Shape) -> bool:
    ba, bb = a.BoundingBox(), b.BoundingBox()
    return (ba.xmin <= bb.xmax and bb.xmin <= ba.xmax and ba.ymin <= bb.ymax and bb.ymin <= ba.ymax
            and ba.zmin <= bb.zmax and bb.zmin <= ba.zmax)


def interference(blades: list[cq.Solid], extent_deg: float, sector_margin_deg: float = 2.0) -> dict:
    """Common volume of blade 0 with blade k, k = 1 .. N/2. Every pair (i, j) is blade 0 with blade (j - i) mod N
    turned by i pitches, and (0, k) is congruent to (0, N - k), so these pairs cover all pairs [H].
    Prefilters: (1) bounding boxes disjoint; (2) angular sectors disjoint: blade k is blade 0 turned by k pitches, so
    it cannot meet blade 0 when k * pitch > extent + margin (extent sampled, margin [T]). Otherwise the boolean
    common volume is computed."""
    n = len(blades)
    pitch = 360.0 / n
    rows = {}
    for k in range(1, n // 2 + 1):
        if not _bbox_overlap(blades[0], blades[k]):
            rows[k] = {"method": "bbox_disjoint", "common_volume_m3": 0.0}
        elif k * pitch > extent_deg + sector_margin_deg:
            rows[k] = {"method": "sector_disjoint", "common_volume_m3": 0.0}
        else:
            rows[k] = {"method": "boolean", "common_volume_m3": fr.boolean("common", blades[0], blades[k]).Volume()}
    return {"pairs": rows, "max_common_volume_m3": max(r["common_volume_m3"] for r in rows.values()),
            "boolean_pairs": [k for k, r in rows.items() if r["method"] == "boolean"]}


def tip_clearance(blade: cq.Solid, casing: cq.Shape, fp: dict) -> dict:
    """Shortest distance blade to casing wall (normal to the cone) and radial gap at the tip corners [H]."""
    corners = corner_radii(blade, (fp["stations"]["2"]["r_hub_m"] + fp["stations"]["2"]["r_tip_m"]) / 2)
    radial = {k: fr.r_at(fp["curves"]["casing_wall"], x) - r for k, (x, r) in corners.items() if k.endswith("tip")}
    return {"min_distance_m": blade.distance(casing), "radial_gap_at_corners_m": radial,
            "design_radial_clearance_m": fp["tip_clearance_m"]}


def corner_check(blade: cq.Solid, fp: dict) -> dict:
    """Corner radii of the trimmed blade against the record radii (relative difference) [H]."""
    st = fp["stations"]
    rec = {"le_hub": st["2"]["r_hub_m"], "te_hub": st["21"]["r_hub_m"], "le_tip": st["2"]["r_tip_m"],
           "te_tip": st["13"]["r_outer_m"]}
    got = corner_radii(blade, (st["2"]["r_hub_m"] + st["2"]["r_tip_m"]) / 2)
    return {k: {"solid_m": got[k][1], "record_m": rec[k], "rel": got[k][1] / rec[k] - 1, "x_m": got[k][0]} for k in rec}


def build(rev: str | None = None, root: Path = records.ROOT) -> dict:
    fp = fpm.build(rev, root)
    tb = trimmed_blade(fp)
    n = fp["blade"]["inputs"]["blades"]
    blades = ring(tb["solid"], n)
    return {"flowpath": fp, "blade": tb, "blades": blades, "n": n}


def checks(model: dict) -> dict:
    fp, tb = model["flowpath"], model["blade"]
    casing = fpm.solids(fp)["casing_wall_surface"]
    vol = tb["solid"].Volume()
    extent = angular_extent_deg(tb["solid"])
    return {
        "blade_count": len(model["blades"]),
        "valid": all(b.isValid() for b in model["blades"]),
        "volume_m3": vol, "mass_kg": vol * tb["rho"], "raw_volume_m3": tb["raw_volume_m3"],
        "volume_change_by_trim": vol / tb["raw_volume_m3"] - 1,
        "corners": corner_check(tb["solid"], fp),
        "angular_extent_deg": extent, "pitch_deg": 360.0 / model["n"],
        "interference": interference(model["blades"], extent),
        "tip_clearance": tip_clearance(tb["solid"], casing, fp),
    }


def export(model: dict) -> dict:
    """STEP files: the trimmed blade (one part) and the ring as an assembly of N instances of that part."""
    rev = model["flowpath"]["revision"]
    blade = model["blade"]["solid"]
    n = model["n"]
    instances = [(f"M1.1.1_{k:02d}", blade, k * 360.0 / n) for k in range(n)]
    return {"fan_blade_trimmed": fr.export_step(blade, "fan_blade_trimmed", rev),
            "fan_blade_ring": fr.export_assembly(instances, "fan_blade_ring", rev)}


def main() -> None:
    model = build()
    c = checks(model)
    print(f"{model['flowpath']['revision']}: {c['blade_count']} blades, valid {c['valid']}")
    print(f"  blade volume {c['volume_m3']:.6e} m3, mass {c['mass_kg']:.4f} kg, trim {c['volume_change_by_trim']:+.4f}")
    for k, row in c["corners"].items():
        print(f"  {k}: r {row['solid_m']:.5f} record {row['record_m']:.5f} rel {row['rel']:+.2e} x {row['x_m']:+.4f}")
    print(f"  angular extent {c['angular_extent_deg']:.2f} deg, pitch {c['pitch_deg']:.2f} deg")
    for k, row in c["interference"]["pairs"].items():
        print(f"  pair 0-{k}: {row['method']}, common volume {row['common_volume_m3']:.3e} m3")
    tc = c["tip_clearance"]
    print(f"  tip: min distance {tc['min_distance_m'] * 1e3:.3f} mm, radial gaps "
          + ", ".join(f"{k} {g * 1e3:.3f} mm" for k, g in tc["radial_gap_at_corners_m"].items()))
    for k, p in export(model).items():
        print(f"  STEP {k}: {p}")


if __name__ == "__main__":
    main()
