"""M2 geometry step 2: rotor drum, blade root blocks, stator inner shrouds, casing and vane feet
(rules/geometry.md R-G2.9-17).

Inputs: the step 1 model (layout.py / blades.py, active record rev001) and the `hw_*` / `m1_disk_*` constants of
geometry/geometry_params.yaml (one tag per field). No value is tuned to pass a check; a part that cannot be built
within the rules gets the stop rule (issue string, placeholder) and the geometry continues.

Run: python -m engine.M2_booster.geometry.hardware  (prints the checks and writes one STEP per part to
.cache/geometry/M2_booster/<rev>/)
"""

import math
from functools import lru_cache
from pathlib import Path

import cadquery as cq
import numpy as np

from engine.M2_booster.geometry import blades as B
from engine.M2_booster.geometry import layout as L

N_EDGE_SAMPLES = 24  # points per edge for the radius checks [T]


def _p(gp: dict, key: str) -> float:
    return float(L.v(gp[key]))


def _dedupe(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out = []
    for p in pts:
        if not out or abs(p[0] - out[-1][0]) > 1e-12 or abs(p[1] - out[-1][1]) > 1e-12:
            out.append(p)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def hub_points(hub: list, x0: float, x1: float) -> list[tuple[float, float]]:
    """Hub line points from x0 to x1 (end points interpolated)."""
    return [(x0, L.r_at(hub, x0))] + [(x, r) for x, r in hub if x0 < x < x1] + [(x1, L.r_at(hub, x1))]


def under_hub(hub: list, x0: float, x1: float, r_in: float) -> cq.Solid:
    """Revolved region between radius r_in and the hub line over x0..x1."""
    return L.revolve_closed(_dedupe([(x0, r_in)] + hub_points(hub, x0, x1) + [(x1, r_in)]))


def rotate(s: cq.Shape, angle_deg: float) -> cq.Shape:
    return s.rotate(cq.Vector(*L.AXIS_ORIGIN), cq.Vector(*L.AXIS_DIR), L.ROTATION_SIGN * angle_deg)


# --- layout of the hardware (R-G2.9 - R-G2.13) ------------------------------------

def hw_layout(model: dict) -> dict:
    lay, gp = model["layout"], model["params"]
    rows = model["rows"]
    x21, x24, hub = lay["station_21"]["x"], lay["x24"], lay["hub_line"]
    gap_f, run_f = float(L.v(gp["axial_gap_fraction"])), _p(gp, "hw_running_gap_over_row_gap")
    issues = []
    # R-G2.9: front / aft limits of each row's hub hardware
    for i, r in enumerate(rows):
        if i == 0:
            r_front = x21
        else:
            g = r["x_le"] - rows[i - 1]["x_te"]
            r_front = 0.5 * (r["x_le"] + rows[i - 1]["x_te"]) + 0.5 * run_f * g
        if i == len(rows) - 1:
            r_aft = x24
        else:
            g = rows[i + 1]["x_le"] - r["x_te"]
            r_aft = 0.5 * (rows[i + 1]["x_le"] + r["x_te"]) - 0.5 * run_f * g
        r["hw_x"] = (r_front, r_aft)
    rotors = [r for r in rows if r["kind"] == "rotor"]
    stators = [r for r in rows if r["kind"] == "stator"]
    rims, shrouds = [], []
    for r in rotors:  # R-G2.10
        xf, xa = r["hw_x"]
        hub_min = min(L.r_at(hub, xf), L.r_at(hub, xa))
        d_s = _p(gp, "hw_slot_depth_over_rotor_chord") * r["chord"]
        r_sb = hub_min - d_s
        hs = next(s for s in r["sections"] if s["name"] == "hub")
        gam = L.stagger(hs["k1"], hs["k2"])
        pitch_n = 2.0 * math.pi * r["hub_le"] / r["count"] * math.cos(math.radians(gam))
        w = _p(gp, "hw_slot_width_over_normal_pitch") * pitch_n
        th = math.radians(hs["k1"] - hs["k2"])
        sag = 0.0 if abs(th) < 1e-9 else math.copysign(1.0, th) * 0.5 * r["chord"] * math.tan(abs(th) / 4.0)
        rims.append({"row": r, "x_f": xf, "x_a": xa, "hub_min": hub_min, "slot_depth": d_s, "r_slot_bottom": r_sb,
                     "r_inner_own": r_sb - _p(gp, "hw_rim_depth_over_slot_depth") * d_s, "stagger": gam,
                     "pitch_normal": pitch_n, "slot_width": w, "sag": sag,
                     "fit": _p(gp, "hw_fit_clearance_over_slot_width") * w})
    for j, s in enumerate(stators):  # R-G2.11
        xf, xa = s["hw_x"]
        up = rotors[j]
        clr_up = B.tip_clearance(up, lay, gp)
        r_hmin = min(L.r_at(hub, xf), L.r_at(hub, xa))
        t_sh = _p(gp, "hw_shroud_thickness_over_stator_chord") * s["chord"]
        t_land = _p(gp, "hw_land_thickness_over_stator_chord") * s["chord"]
        l_land = _p(gp, "hw_land_length_over_shroud_length") * (xa - xf)
        xc = 0.5 * (xf + xa)
        r_shi = r_hmin - t_sh
        r_li = r_shi - t_land
        c_seal = _p(gp, "hw_seal_clearance_over_tip_clearance") * clr_up
        r_tt = r_li - c_seal
        h_t = _p(gp, "hw_tooth_height_over_land_thickness") * t_land
        r_so = r_tt - h_t
        t_w = _p(gp, "hw_drum_wall_over_hub_radius") * r_hmin
        n_t = int(_p(gp, "hw_tooth_count"))
        w_t = _p(gp, "hw_tooth_width_over_land_length") * l_land
        x_l0 = xc - 0.5 * l_land
        teeth = [x_l0 + (k + 0.5) * l_land / n_t for k in range(n_t)]
        shrouds.append({"row": s, "x_f": xf, "x_a": xa, "r_hub_min": r_hmin, "t_shroud": t_sh, "r_shroud_in": r_shi,
                        "t_land": t_land, "land_x": (x_l0, x_l0 + l_land), "r_land_in": r_li, "seal_clearance": c_seal,
                        "r_tooth_tip": r_tt, "tooth_height": h_t, "tooth_width": w_t, "tooth_x": teeth,
                        "r_wall_out": r_so, "wall": t_w, "r_wall_in": r_so - t_w})
    for i, rim in enumerate(rims):  # rim reaches down to the adjacent wall inner radii
        adj = [shrouds[k]["r_wall_in"] for k in (i - 1, i) if 0 <= k < len(shrouds)]
        rim["r_inner"] = min([rim["r_inner_own"]] + adj)
        rim["live_rim"] = rim["r_slot_bottom"] - rim["r_inner"]
    for i, rim in enumerate(rims):  # R-G2.10 slot open at both rim faces: material ahead / behind below r_slot_bottom
        ahead = shrouds[i - 1]["r_wall_out"] if i > 0 else None  # rim 1: flange stays below the rim inner radius
        behind = shrouds[i]["r_wall_out"] if i < len(shrouds) else None
        rim["slot_open_front"] = ahead is None or ahead <= rim["r_slot_bottom"]
        rim["slot_open_aft"] = behind is None or behind <= rim["r_slot_bottom"]
        rim["slot_closed_height_aft"] = 0.0 if rim["slot_open_aft"] else behind - rim["r_slot_bottom"]
    t_min = _p(gp, "hw_min_wall_m")
    for k, sh in enumerate(shrouds):
        # the wall meets the rim faces below the hub line (rim k aft face, rim k+1 front face)
        nxt = L.r_at(hub, rims[k + 1]["x_f"]) if k + 1 < len(rims) else math.inf
        if not (sh["wall"] >= t_min and sh["r_wall_out"] < min(L.r_at(hub, rims[k]["x_a"]), nxt)):
            issues.append(f"drum wall under {sh['row']['part_id']} not buildable (stop rule)")
        if sh["r_land_in"] <= sh["r_wall_out"]:
            issues.append(f"seal stack under {sh['row']['part_id']} not buildable (stop rule)")
    for rim in rims:
        if rim["live_rim"] < t_min:
            issues.append(f"live rim of {rim['row']['part_id']} below hw_min_wall_m (stop rule)")
    # casing and vane grooves (R-G2.12)
    rc = lay["r_casing"]
    t_c = _p(gp, "hw_casing_thickness_over_radius") * rc
    grooves = []
    for s in stators:
        m = _p(gp, "hw_vane_slot_margin_over_row_width") * s["width"]
        d_g = _p(gp, "hw_vane_slot_depth_over_stator_chord") * s["chord"]
        x0, x1 = max(x21, s["x_le"] - m), min(x24, s["x_te"] + m)
        fit = _p(gp, "hw_fit_clearance_over_slot_width") * d_g
        grooves.append({"row": s, "x0": x0, "x1": x1, "depth": d_g, "fit": fit,
                        "foot_x": (x0 + fit if x0 > x21 else x0, x1 - fit), "foot_r": (rc, rc + d_g - fit),
                        "span_deg": _p(gp, "hw_foot_span_over_pitch") * 360.0 / s["count"],
                        "wall_behind": t_c - d_g})
        if t_c - d_g < t_min:
            issues.append(f"casing wall behind the {s['part_id']} groove below hw_min_wall_m (stop rule)")
    # forward flange (R-G2.13)
    t_fl = _p(gp, "hw_flange_thickness_over_drum_wall") * shrouds[0]["wall"]
    r_fl_in = _p(gp, "m1_disk_live_rim_inner_m")
    if not (x21 + t_fl < rims[0]["x_a"] and r_fl_in < rims[0]["r_inner"]):
        issues.append("forward flange not buildable (stop rule)")
    flange = {"x": (x21, x21 + t_fl), "r_inner": r_fl_in, "r_bolt_circle":
              0.5 * (r_fl_in + _p(gp, "m1_disk_slot_bottom_m")),
              "axial_gap_to_m1_disk": x21 - _p(gp, "m1_disk_aft_face_x_m")}
    return {"x21": x21, "x24": x24, "hub": hub, "r_casing": rc, "casing_thickness": t_c, "rims": rims,
            "shrouds": shrouds, "grooves": grooves, "flange": flange, "issues": issues}


# --- solids ------------------------------------------------------------------------

def drum_unslotted(H: dict) -> cq.Solid:
    """Drum meridional polygon (R-G2.10, R-G2.13, R-G2.14) revolved, with the seal teeth (R-G2.11) fused."""
    hub, rims, sh, fl = H["hub"], H["rims"], H["shrouds"], H["flange"]
    outer = [(H["x21"], fl["r_inner"])]
    for i, rim in enumerate(rims):
        outer += hub_points(hub, rim["x_f"], rim["x_a"])
        x_next = rims[i + 1]["x_f"] if i + 1 < len(rims) else H["x24"]
        outer += [(rim["x_a"], sh[i]["r_wall_out"]), (x_next, sh[i]["r_wall_out"])]
    inner = [(H["x24"], sh[-1]["r_wall_in"])]
    for i in range(len(rims) - 1, -1, -1):
        rim = rims[i]
        inner += [(rim["x_a"], sh[i]["r_wall_in"]), (rim["x_a"], rim["r_inner"])]
        x_front = fl["x"][1] if i == 0 else rim["x_f"]
        inner.append((x_front, rim["r_inner"]))
        if i > 0:
            inner.append((rim["x_f"], sh[i - 1]["r_wall_in"]))
    inner.append((fl["x"][1], fl["r_inner"]))
    body = L.revolve_closed(_dedupe(outer + inner))
    teeth = []
    for s in sh:
        for xc in s["tooth_x"]:
            x0, x1 = xc - 0.5 * s["tooth_width"], xc + 0.5 * s["tooth_width"]
            r0 = s["r_wall_out"] - 0.5 * s["wall"]  # overlap into the wall for a clean fuse
            teeth.append(L.revolve_closed([(x0, r0), (x1, r0), (x1, s["r_tooth_tip"]), (x0, s["r_tooth_tip"])]))
    fused = body.fuse(*teeth).clean()
    solids = fused.Solids()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError("drum with teeth is not one valid solid")
    return solids[0]


def _slot_frame(rim: dict) -> dict:
    row = rim["row"]
    sign = B.tangential_sign("rotor")
    g = math.radians(rim["stagger"])
    e_c = np.array([math.cos(g), sign * math.sin(g)])
    e_n = np.array([-math.sin(g), sign * math.cos(g)])
    centre = np.array([row["x_stack"], 0.0]) + rim["sag"] * 0.5 * e_n
    return {"e_c": e_c, "e_n": e_n, "centre": centre, "angle": sign * rim["stagger"]}


def _prism(rim: dict, width: float, r_lo: float, r_hi: float) -> cq.Solid:
    """Straight prism along the slot direction, rectangular section width x (r_lo..r_hi) in z (blade 0 at +Z)."""
    f = _slot_frame(rim)
    length = 4.0 * (rim["x_a"] - rim["x_f"]) / max(math.cos(math.radians(rim["stagger"])), 0.2)
    box = cq.Solid.makeBox(length, width, r_hi - r_lo, pnt=cq.Vector(-0.5 * length, -0.5 * width, r_lo))
    box = box.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), f["angle"])
    return box.translate(cq.Vector(f["centre"][0], f["centre"][1], 0.0))


def slot_cutter(rim: dict, r_top: float) -> cq.Solid:
    w, r_sb = rim["slot_width"], rim["r_slot_bottom"]
    pr = _prism(rim, w, 0.8 * r_sb, r_top)
    band = L.revolve_closed([(rim["x_f"], r_sb), (rim["x_a"], r_sb), (rim["x_a"], r_top), (rim["x_f"], r_top)])
    return pr.intersect(band).Solids()[0]


def root_block(rim: dict, hub: list) -> cq.Solid:
    """Blade root block (R-G2.10): slot section shrunk by the fit clearance, top on the hub line."""
    c = rim["fit"]
    pr = _prism(rim, rim["slot_width"] - 2.0 * c, 0.8 * rim["r_slot_bottom"], rim["hub_min"] + 0.1)
    region = under_hub(hub, rim["x_f"], rim["x_a"], rim["r_slot_bottom"] + c)
    solids = pr.intersect(region).Solids()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError(f"root block of {rim['row']['part_id']} is not one valid solid")
    return solids[0]


def drum(H: dict, base: cq.Solid) -> cq.Solid:
    r_top = H["r_casing"]
    cutters = []
    for rim in H["rims"]:
        c0 = slot_cutter(rim, r_top)
        n = rim["row"]["count"]
        cutters += [rotate(c0, 360.0 * k / n) for k in range(n)]
    out = base.cut(cq.Compound.makeCompound(cutters)).Solids()
    if len(out) != 1 or not out[0].isValid():
        raise ValueError(f"slotted drum: {len(out)} solids, expected one valid solid")
    return out[0]


def inner_shroud(sh: dict, hub: list) -> cq.Solid:
    """R-G2.11: full ring, outer surface on the hub line, seal land underneath."""
    xf, xa = sh["x_f"], sh["x_a"]
    l0, l1 = sh["land_x"]
    pts = [(xf, sh["r_shroud_in"])] + hub_points(hub, xf, xa) + [
        (xa, sh["r_shroud_in"]), (l1, sh["r_shroud_in"]), (l1, sh["r_land_in"]), (l0, sh["r_land_in"]),
        (l0, sh["r_shroud_in"])]
    return L.revolve_closed(_dedupe(pts))


def casing(H: dict) -> cq.Solid:
    """R-G2.12: shell station 21 -> 24 with one vane groove per stator row."""
    rc, t = H["r_casing"], H["casing_thickness"]
    shell = L.revolve_closed([(H["x21"], rc), (H["x24"], rc), (H["x24"], rc + t), (H["x21"], rc + t)])
    cuts = []
    for g in H["grooves"]:
        x0 = g["x0"] - (1e-4 if g["x0"] <= H["x21"] else 0.0)
        x1 = g["x1"] + (1e-4 if g["x1"] >= H["x24"] else 0.0)
        cuts.append(L.revolve_closed([(x0, rc - 1e-3), (x1, rc - 1e-3), (x1, rc + g["depth"]),
                                      (x0, rc + g["depth"])]))
    out = shell.cut(cq.Compound.makeCompound(cuts)).Solids()
    if len(out) != 1 or not out[0].isValid():
        raise ValueError("grooved casing is not one valid solid")
    return out[0]


def vane_foot(g: dict) -> cq.Solid:
    """R-G2.12: annular sector in the groove, centred on the vane stacking line (+Z)."""
    (x0, x1), (r0, r1) = g["foot_x"], g["foot_r"]
    s = cq.Workplane("XY").polyline([(x0, r0), (x1, r0), (x1, r1), (x0, r1)]).close() \
        .revolve(g["span_deg"], (0, 0, 0), (1, 0, 0)).val()
    c = s.Center()
    ang = math.degrees(math.atan2(c.z, c.y))
    return s.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90.0 - ang)


@lru_cache(maxsize=2)
def build(rev: str | None = None) -> dict:
    model = B.build(rev)
    H = hw_layout(model)
    base = drum_unslotted(H)
    parts = {"drum_unslotted": base, "drum": drum(H, base), "casing": casing(H),
             "roots": [root_block(rim, H["hub"]) for rim in H["rims"]],
             "shrouds": [inner_shroud(sh, H["hub"]) for sh in H["shrouds"]],
             "feet": [vane_foot(g) for g in H["grooves"]]}
    return {"model": model, "hw": H, "parts": parts}


# --- checks (R-G2.17) -----------------------------------------------------------------

def radii_at(solid: cq.Shape, x: float) -> tuple[float, float]:
    """Smallest and largest radius on the boundary of the planar cut at x (edge samples)."""
    plane = cq.Face.makePlane(2.0, 2.0, basePnt=cq.Vector(x, 0, 0), dir=cq.Vector(1, 0, 0))
    rs = []
    for e in solid.intersect(plane).Edges():
        for t in np.linspace(0.0, 1.0, N_EDGE_SAMPLES):
            p = e.positionAt(float(t))
            rs.append(math.hypot(p.y, p.z))
    return min(rs), max(rs)


def _planes(x0: float, x1: float) -> list[float]:
    d = 0.02 * (x1 - x0)
    return [x0 + d, 0.5 * (x0 + x1), x1 - d]


def flowpath_radius_checks(hb: dict, tol: float) -> list[dict]:
    H, P = hb["hw"], hb["parts"]
    out = []
    for rim in H["rims"]:
        for x in _planes(rim["x_f"], rim["x_a"]):
            r = radii_at(P["drum"], x)[1]
            out.append({"part": "drum", "row": rim["row"]["part_id"], "x": x, "r": r, "r_ref": L.r_at(H["hub"], x),
                        "pass": abs(r - L.r_at(H["hub"], x)) <= tol})
    for sh, s in zip(H["shrouds"], P["shrouds"]):
        for x in _planes(sh["x_f"], sh["x_a"]):
            r = radii_at(s, x)[1]
            out.append({"part": "inner_shroud", "row": sh["row"]["part_id"], "x": x, "r": r,
                        "r_ref": L.r_at(H["hub"], x), "pass": abs(r - L.r_at(H["hub"], x)) <= tol})
    for rim in H["rims"]:  # over the rotors the casing inner surface is the tip flow path
        x = rim["row"]["x_stack"]
        r = radii_at(P["casing"], x)[0]
        out.append({"part": "casing", "row": rim["row"]["part_id"], "x": x, "r": r, "r_ref": H["r_casing"],
                    "pass": abs(r - H["r_casing"]) <= tol})
    for g, f in zip(H["grooves"], P["feet"]):  # groove bottom; the foot inner face carries the tip flow path
        x = g["row"]["x_stack"]
        r = radii_at(P["casing"], x)[0]
        out.append({"part": "casing groove", "row": g["row"]["part_id"], "x": x, "r": r,
                    "r_ref": H["r_casing"] + g["depth"], "pass": abs(r - H["r_casing"] - g["depth"]) <= tol})
        r = radii_at(f, x)[0]
        out.append({"part": "vane foot", "row": g["row"]["part_id"], "x": x, "r": r, "r_ref": H["r_casing"],
                    "pass": abs(r - H["r_casing"]) <= tol})
    return out


def common_fraction(a: cq.Shape, b: cq.Shape) -> float:
    ba, bb = a.BoundingBox(), b.BoundingBox()
    if (ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin
            or ba.zmax < bb.zmin or bb.zmax < ba.zmin):
        return 0.0
    com = a.intersect(b)
    vol = sum(s.Volume() for s in com.Solids()) if com.Solids() else 0.0
    return vol / min(a.Volume(), b.Volume())


def part_list(hb: dict) -> list[tuple[str, str, cq.Shape]]:
    """(name, motion, solid) of every M2 part instance at index 0 (blade/vane 0 of each row)."""
    P, rows = hb["parts"], hb["model"]["rows"]
    rot = [r for r in rows if r["kind"] == "rotor"]
    sta = [r for r in rows if r["kind"] == "stator"]
    out = [("drum", "rot", P["drum"]), ("casing", "stat", P["casing"])]
    out += [(f"{r['part_id']} airfoil", "rot", r["solid"]) for r in rot]
    out += [(f"{r['part_id']} root", "rot", s) for r, s in zip(rot, P["roots"])]
    out += [(f"{r['part_id']} vane", "stat", r["solid"]) for r in sta]
    out += [(f"{r['part_id']} foot", "stat", s) for r, s in zip(sta, P["feet"])]
    out += [(f"M2.{r['stage']}.4 inner shroud", "stat", s) for r, s in zip(sta, P["shrouds"])]
    return out


def interference_checks(hb: dict, tol: float) -> list[dict]:
    parts = part_list(hb)
    out = []
    for i, (na, _, a) in enumerate(parts):
        for nb, _, b in parts[i + 1:]:
            f = common_fraction(a, b)
            out.append({"a": na, "b": nb, "common_fraction": f, "pass": f <= tol})
    H, P = hb["hw"], hb["parts"]
    for rim, s in zip(H["rims"], P["roots"]):
        f = common_fraction(s, rotate(s, 360.0 / rim["row"]["count"]))
        out.append({"a": f"{rim['row']['part_id']} root", "b": "neighbour root", "common_fraction": f,
                    "pass": f <= tol})
    for g, s in zip(H["grooves"], P["feet"]):
        f = common_fraction(s, rotate(s, 360.0 / g["row"]["count"]))
        out.append({"a": f"{g['row']['part_id']} foot", "b": "neighbour foot", "common_fraction": f, "pass": f <= tol})
    return out


def running_clearances(hb: dict) -> list[dict]:
    """Distance between rotating and stationary parts that face each other (> 0); unslotted drum (slots only remove
    material, so the distance can only grow)."""
    H, P, rows = hb["hw"], hb["parts"], hb["model"]["rows"]
    rot = [r for r in rows if r["kind"] == "rotor"]
    out = []
    for r in rot:
        d = r["solid"].distance(P["casing"])
        out.append({"a": f"{r['part_id']} airfoil", "b": "casing", "distance": d, "ref": r["clearance"]})
    for sh, s in zip(H["shrouds"], P["shrouds"]):
        d = P["drum_unslotted"].distance(s)
        out.append({"a": "drum", "b": f"{sh['row']['part_id']} inner shroud", "distance": d,
                    "ref": min(sh["seal_clearance"], hb_running_gap(sh, H))})
    out.append({"a": "drum", "b": "casing", "distance": P["drum_unslotted"].distance(P["casing"]), "ref": None})
    return out


def hb_running_gap(sh: dict, H: dict) -> float:
    """Axial running gap ahead of a shroud (R-G2.9)."""
    return sh["x_f"] - max(r["x_a"] for r in H["rims"] if r["x_a"] <= sh["x_f"])


def footprint_checks(hb: dict) -> list[dict]:
    """Airfoil hub-section footprint inside its root block top; vane tip footprint inside its foot (R-G2.17)."""
    model, H = hb["model"], hb["hw"]
    gp = model["params"]
    te_c = float(L.v(gp["edge_thickness_ratio"]))
    out = []
    for rim in H["rims"]:
        row = rim["row"]
        s = next(s for s in row["sections"] if s["name"] == "hub")
        up, lo = B.section_points(row["chord"], s["k1"], s["k2"], B.thickness_ratio("rotor", "hub", gp), te_c,
                                  B.tangential_sign("rotor"), row["x_stack"])
        f = _slot_frame(rim)
        pts = np.vstack([up, lo]) - f["centre"]
        n = pts @ f["e_n"]
        half = 0.5 * rim["slot_width"] - rim["fit"]
        xs = np.vstack([up, lo])[:, 0]
        ok = bool(np.max(np.abs(n)) <= half and xs.min() >= rim["x_f"] and xs.max() <= rim["x_a"])
        out.append({"row": row["part_id"], "n_max": float(np.max(np.abs(n))), "half_width": half,
                    "x_range": (float(xs.min()), float(xs.max())), "pass": ok})
    for g in H["grooves"]:
        row = g["row"]
        s = next(s for s in row["sections"] if s["name"] == "tip")
        up, lo = B.section_points(row["chord"], s["k1"], s["k2"], B.thickness_ratio("stator", "tip", gp), te_c,
                                  B.tangential_sign("stator"), row["x_stack"])
        pts = np.vstack([up, lo])
        phi = np.degrees(np.abs(pts[:, 1]) / H["r_casing"])
        ok = bool(phi.max() <= 0.5 * g["span_deg"] and pts[:, 0].min() >= g["foot_x"][0]
                  and pts[:, 0].max() <= g["foot_x"][1])
        out.append({"row": row["part_id"], "phi_max_deg": float(phi.max()), "half_span_deg": 0.5 * g["span_deg"],
                    "x_range": (float(pts[:, 0].min()), float(pts[:, 0].max())), "pass": ok})
    return out


def station21_check(hb: dict) -> list[dict]:
    x21 = hb["hw"]["x21"]
    return [{"part": n, "x_min": s.BoundingBox().xmin, "pass": s.BoundingBox().xmin >= x21 - 1e-7}
            for n, _, s in part_list(hb)]


def masses(hb: dict) -> list[dict]:
    """Information only (R-G2.16); placeholder density for tbd materials (#71)."""
    rho = B.density("ti6al4v")
    P, H = hb["parts"], hb["hw"]
    out = [{"part": "M2.0.1 drum", "material": "ti6al4v", "qty": 1, "mass": P["drum"].Volume() * rho},
           {"part": "M2.0.2 casing", "material": "tbd (ti6al4v density)", "qty": 1, "mass": P["casing"].Volume() * rho}]
    for rim, s in zip(H["rims"], P["roots"]):
        n = rim["row"]["count"]
        out.append({"part": f"{rim['row']['part_id']} root block", "material": "ti6al4v", "qty": n,
                    "mass": s.Volume() * rho * n})
    for sh, s in zip(H["shrouds"], P["shrouds"]):
        out.append({"part": f"M2.{sh['row']['stage']}.4 inner shroud", "material": "tbd (ti6al4v density)", "qty": 1,
                    "mass": s.Volume() * rho})
    for g, s in zip(H["grooves"], P["feet"]):
        n = g["row"]["count"]
        out.append({"part": f"{g['row']['part_id']} vane foot", "material": "tbd (ti6al4v density)", "qty": n,
                    "mass": s.Volume() * rho * n})
    return out


def walls(hb: dict) -> list[dict]:
    H = hb["hw"]
    t_min = _p(hb["model"]["params"], "hw_min_wall_m")
    out = [{"wall": f"live rim {r['row']['part_id']}", "t": r["live_rim"]} for r in H["rims"]]
    out += [{"wall": f"drum wall under {s['row']['part_id']}", "t": s["wall"]} for s in H["shrouds"]]
    out += [{"wall": f"casing behind {g['row']['part_id']} groove", "t": g["wall_behind"]} for g in H["grooves"]]
    return [dict(w, pass_=w["t"] >= t_min) for w in out]


def checks(hb: dict | None = None) -> dict:
    hb = hb or build()
    gp = hb["model"]["params"]
    tol_r = float(L.v(gp["radius_tolerance_m"]))
    return {"issues": hb["hw"]["issues"], "radii": flowpath_radius_checks(hb, tol_r),
            "interference": interference_checks(hb, _p(gp, "hw_common_volume_tolerance")),
            "running": running_clearances(hb), "footprints": footprint_checks(hb), "station_21": station21_check(hb),
            "walls": walls(hb), "masses": masses(hb)}


# --- M1 neighbours (read-only, report only; R-G2.13, R-G2.17) --------------------------

def m1_overlap(hb: dict | None = None) -> dict:
    """Common volume of M2 parts with M1 rev014 parts (fan frame, OGV vane 0, fan disk), report only. Imports M1
    geometry code read-only (no M1 file is written)."""
    from engine.M1_inlet_fan.geometry import fan_frame, ogv, rotor_hardware
    hb = hb or build()
    ff = fan_frame.build()
    m1 = dict(ff["parts"])
    m1["ogv_vane"] = ogv.build()["vane"]
    rot = rotor_hardware.build()
    m1["fan_disk"] = rot["disk"]
    rows = []
    for n2, _, s2 in part_list(hb):
        for n1, s1 in m1.items():
            f = common_fraction(s2, s1)
            if f > 0.0:
                rows.append({"m2": n2, "m1": n1, "common_fraction_of_smaller": f})
    lay = rot["layout"]
    disk = {"x_aft_face": lay["x_b"], "r_rim": lay["r_rim"], "r_slot_bottom": lay["r_slot_bottom"],
            "r_live_rim_inner": rot["disk_profile"]["r_rim_inner"]}
    return {"overlaps": rows, "m1_disk": disk, "m1_frame_x": (ff["layout"]["x0"], ff["layout"]["x1"])}


# --- export ------------------------------------------------------------------------

def export(hb: dict | None = None) -> list[Path]:
    hb = hb or build()
    rev = hb["model"]["layout"]["revision"]
    d = B.step_dir(rev)
    d.mkdir(parents=True, exist_ok=True)
    P, rows = hb["parts"], hb["model"]["rows"]
    items = [("M2_0_1_drum", P["drum"]), ("M2_0_2_casing", P["casing"])]
    items += [(f"M2_{r['stage']}_1_root_block", s) for r, s in zip([r for r in rows if r["kind"] == "rotor"],
                                                                     P["roots"])]
    sta = [r for r in rows if r["kind"] == "stator"]
    items += [(f"M2_{r['stage']}_2_vane_foot", s) for r, s in zip(sta, P["feet"])]
    items += [(f"M2_{r['stage']}_4_inner_shroud", s) for r, s in zip(sta, P["shrouds"])]
    out = []
    for name, s in items:
        p = d / f"{name}.step"
        cq.exporters.export(cq.Workplane().add(s), str(p), exportType="STEP")
        out.append(p)
    return out


def main() -> None:
    hb = build()
    H = hb["hw"]
    res = checks(hb)
    print("issues", res["issues"] or "none")
    for rim in H["rims"]:
        print(f"rim {rim['row']['part_id']} x {rim['x_f']:.5f}-{rim['x_a']:.5f} hub_min {rim['hub_min']:.5f} "
              f"slot w {rim['slot_width'] * 1e3:.2f} mm d {rim['slot_depth'] * 1e3:.2f} mm r_sb {rim['r_slot_bottom']:.5f}"
              f" r_in {rim['r_inner']:.5f} live {rim['live_rim'] * 1e3:.2f} mm open front/aft "
              f"{rim['slot_open_front']}/{rim['slot_open_aft']} closed aft {rim['slot_closed_height_aft'] * 1e3:.2f} mm")
    for sh in H["shrouds"]:
        print(f"shroud {sh['row']['part_id']} x {sh['x_f']:.5f}-{sh['x_a']:.5f} r_in {sh['r_shroud_in']:.5f} "
              f"land {sh['r_land_in']:.5f} tooth tip {sh['r_tooth_tip']:.5f} seal {sh['seal_clearance'] * 1e3:.3f} mm "
              f"wall {sh['r_wall_in']:.5f}-{sh['r_wall_out']:.5f}")
    for g in H["grooves"]:
        print(f"groove {g['row']['part_id']} x {g['x0']:.5f}-{g['x1']:.5f} d {g['depth'] * 1e3:.2f} mm "
              f"wall behind {g['wall_behind'] * 1e3:.2f} mm span {g['span_deg']:.3f} deg")
    print("flange", H["flange"], "casing t", H["casing_thickness"])
    print("radii fail", [r for r in res["radii"] if not r["pass"]] or "none")
    print("interference fail", [r for r in res["interference"] if not r["pass"]] or "none")
    for r in res["running"]:
        print("running", r)
    for r in res["footprints"]:
        print("footprint", r)
    print("station 21 fail", [r for r in res["station_21"] if not r["pass"]] or "none")
    for w in res["walls"]:
        print("wall", w)
    for m in res["masses"]:
        print(f"mass {m['part']:<26} {m['mass']:.3f} kg  qty {m['qty']}  {m['material']}")
    for p in export(hb):
        print("STEP", p)


if __name__ == "__main__":
    main()
