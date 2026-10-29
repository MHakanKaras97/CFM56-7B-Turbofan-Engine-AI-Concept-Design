"""M1 blade root: shank + single-lobe axial-entry dovetail, slot, shim and spacer profiles (step 5c). frame.py axes.

Slot frame (blade 0, top dead centre): slot axis d = (cos g, sin g, 0) along the root-section chord angle g
(rotor_params.yaml dovetail.slot_axis) through the stacking axis; profile coordinates (w, z): w along
n = (-sin g, cos g, 0), z radial (+Z). Profiles are extruded along d and cut to the rotor slab x_a <= x <= x_b
(x_a, x_b = hub leading / trailing edge x of flowpath.rotor_edges) [H].
Sizes [H from T ratios]: neck width b_n = ratio x the airfoil base width normal to d (measured on the 5b trimmed
airfoil where it meets the hub line); every other size is a ratio of b_n (rotor_params.yaml). Radial levels:
rim top r_rim = r_hub1 - platform plate - clearance; neck to z1; flanks to z2; lobe sides to z3 (dovetail bottom);
shim t_sh round the lobe; spacer below with clearance; slot pocket bottom r_sb.
The 5b root stub (open issue #30) is replaced by the shank: the airfoil (5b trim, above the hub line) sits on the
shank, whose top is the hub line.
"""

import math
from functools import lru_cache
from pathlib import Path

import cadquery as cq
import numpy as np

from core import records
from core.util import read_yaml
from engine.M1_inlet_fan.geometry import blade_solid as bs
from engine.M1_inlet_fan.geometry import fan_ring as ring
from engine.M1_inlet_fan.geometry import flowpath as fpm
from engine.M1_inlet_fan.geometry import frame as fr

PARAMS = fr.HERE / "rotor_params.yaml"
BIG = 2.0  # m, extrusion half length and box size for construction solids


def rotor_params() -> dict:
    return read_yaml(PARAMS)


def _p(group: str, key: str) -> float:
    return fr.v(rotor_params()[group][key])


def base_points(airfoil: cq.Solid, hub_curve, tol: float = 2e-4, n: int = 400) -> np.ndarray:
    """Points of the airfoil edges that lie on the hub line (the airfoil base outline) [H, sampled]."""
    pts = [q for e in airfoil.Edges() for q in bs._edge_points(e, n) if abs(fr.radius(q) - fr.r_at(hub_curve, q[0])) < tol]
    if len(pts) < 20:
        raise ValueError("airfoil base outline not found on the hub line")
    return np.array(pts)


def layout(fp: dict, airfoil: cq.Solid) -> dict:
    """Slot frame and all root / slot levels and widths (metres) [H from T ratios]."""
    gamma = bs.chord_angle(fp["blade"]["sections"][0])
    d = np.array([math.cos(gamma), math.sin(gamma), 0.0])
    n = np.array([-math.sin(gamma), math.cos(gamma), 0.0])
    base = base_points(airfoil, fp["curves"]["hub"])
    w = base @ n
    footprint = float(w.max() - w.min())
    w_c = float((w.max() + w.min()) / 2)
    b_n = _p("dovetail", "neck_width_over_footprint") * footprint
    c = _p("dovetail", "fit_clearance") * 1e-3
    t_p = _p("platform", "plate_thickness_over_neck") * b_n
    t_sh = _p("dovetail", "shim_thickness_over_neck") * b_n
    t_sp = _p("dovetail", "spacer_thickness_over_neck") * b_n
    b_l = _p("dovetail", "lobe_width_over_neck") * b_n
    alpha = math.radians(_p("dovetail", "flank_angle_from_tangential"))
    e = fp["rotor_edges"]
    r_rim = e["le_hub"][1] - t_p - c
    z1 = r_rim - _p("dovetail", "neck_height_over_neck") * b_n
    z2 = z1 - (b_l - b_n) / 2 * math.tan(alpha)
    z3 = z2 - _p("dovetail", "lobe_side_height_over_neck") * b_n
    sp_top = z3 - t_sh - c
    sp_bot = sp_top - t_sp
    r_sb = sp_bot - c
    return {"gamma": gamma, "d": d, "n": n, "w_c": w_c, "footprint": footprint, "b_n": b_n, "b_l": b_l,
            "alpha": alpha, "c": c, "t_p": t_p, "t_sh": t_sh, "t_sp": t_sp, "r_rim": r_rim, "z1": z1, "z2": z2,
            "z3": z3, "spacer_top": sp_top, "spacer_bottom": sp_bot, "r_slot_bottom": r_sb,
            "x_a": e["le_hub"][0], "x_b": e["te_hub"][0], "z_top": e["te_hub"][1] + 0.05,
            "base_w_range": (float(w.min()), float(w.max()))}


def dovetail_profile(L: dict) -> list[tuple[float, float]]:
    """Blade root outline (w, z): neck from z_top down to z1, flanks to z2, lobe sides to z3, flat bottom."""
    hn, hl, wc = L["b_n"] / 2, L["b_l"] / 2, L["w_c"]
    right = [(wc + hn, L["z_top"]), (wc + hn, L["z1"]), (wc + hl, L["z2"]), (wc + hl, L["z3"])]
    left = [(2 * wc - u, z) for u, z in reversed(right)]
    return right + left


def _prism(L: dict, face_or_pts, length: float = BIG) -> cq.Solid:
    """Profile in the slot plane (w, z) extruded along d over +-length."""
    plane = cq.Plane(origin=(0, 0, 0), xDir=tuple(L["n"]), normal=tuple(L["d"]))
    wp = cq.Workplane(plane)
    if isinstance(face_or_pts, list):
        wp = wp.polyline(face_or_pts).close()
        return wp.extrude(length, both=True).val()
    return cq.Solid.extrudeLinear(face_or_pts, cq.Vector(*L["d"]) * (2 * length)).translate(cq.Vector(*L["d"]) * -length)


def _wire(L: dict, pts) -> cq.Wire:
    plane = cq.Plane(origin=(0, 0, 0), xDir=tuple(L["n"]), normal=tuple(L["d"]))
    return cq.Wire.makePolygon([plane.toWorldCoords(p) for p in pts], close=True)


def _offset_prism(L: dict, pts, offset: float) -> cq.Solid:
    wire = _wire(L, pts).offset2D(offset, "intersection")[0]
    return _prism(L, cq.Face.makeFromWires(wire))


def slab(L: dict) -> cq.Solid:
    """Axial slab x_a <= x <= x_b (large in y, z)."""
    return cq.Solid.makeBox(L["x_b"] - L["x_a"], 2 * BIG, 2 * BIG, pnt=cq.Vector(L["x_a"], -BIG, -BIG))


def below_hub(fp: dict, r_min: float = 0.02) -> cq.Solid:
    """Axisymmetric region between r_min and the hub line (constant beyond the edges)."""
    e = fp["rotor_edges"]
    lo, hi = e["le_hub"][0] - 0.5, e["te_hub"][0] + 0.5
    return fr.revolve_closed([(lo, r_min), (lo, e["le_hub"][1]), e["le_hub"], e["te_hub"], (hi, e["te_hub"][1]),
                              (hi, r_min)])


def blade_root(fp: dict, L: dict) -> cq.Solid:
    """Shank + dovetail of blade 0: dovetail prism, cut to the slab and to below the hub line."""
    p = fr.boolean("common", _prism(L, dovetail_profile(L)), slab(L))
    return fr.boolean("common", p, below_hub(fp)).Solids()[0]


def shim(L: dict) -> cq.Solid:
    """Alloy 718 sheet round the dovetail lobe below the neck (flanks, sides, bottom), on the blade surface."""
    prof = dovetail_profile(L)
    outer = _offset_prism(L, prof, L["t_sh"])
    sheet = outer.cut(_prism(L, prof))
    below_neck = cq.Solid.makeBox(4 * BIG, 4 * BIG, BIG, pnt=cq.Vector(-2 * BIG, -2 * BIG, L["z1"] - BIG))
    out = fr.boolean("common", fr.boolean("common", sheet, below_neck), slab(L)).Solids()
    return max(out, key=lambda s: s.Volume())


def spacer(L: dict) -> cq.Solid:
    hw, wc = L["b_l"] / 2 + L["t_sh"], L["w_c"]
    pts = [(wc - hw, L["spacer_bottom"]), (wc + hw, L["spacer_bottom"]), (wc + hw, L["spacer_top"]),
           (wc - hw, L["spacer_top"])]
    return fr.boolean("common", _prism(L, pts), slab(L)).Solids()[0]


def slot_cutter(L: dict) -> cq.Solid:
    """Disk slot of blade 0 (not cut to the slab): dovetail outline offset by shim + clearance, plus the spacer
    pocket (spacer width + 2 clearance, down to r_slot_bottom)."""
    off = _offset_prism(L, dovetail_profile(L), L["t_sh"] + L["c"])
    hw, wc = L["b_l"] / 2 + L["t_sh"] + L["c"], L["w_c"]
    pocket = _prism(L, [(wc - hw, L["r_slot_bottom"]), (wc + hw, L["r_slot_bottom"]), (wc + hw, L["z3"] - L["t_sh"]),
                        (wc - hw, L["z3"] - L["t_sh"])])
    return fr.boolean("fuse", off, pocket).Solids()[0]


@lru_cache(maxsize=2)
def build(rev: str | None = None, root: Path = records.ROOT) -> dict:
    """Blade 0 with root (airfoil from the 5b trim + shank/dovetail), shim and spacer of slot 0, and the layout."""
    fp = fpm.build(rev, root)
    airfoil = ring.trimmed_blade(fp)["solid"]
    L = layout(fp, airfoil)
    root_part = blade_root(fp, L)
    blade = fr.boolean("fuse", airfoil, root_part).Solids()
    if len(blade) != 1 or not blade[0].isValid():
        raise ValueError(f"blade with root: {len(blade)} solids, expected one valid solid")
    return {"flowpath": fp, "layout": L, "airfoil": airfoil, "root": root_part, "blade": blade[0],
            "shim": shim(L), "spacer": spacer(L), "slot": slot_cutter(L)}
