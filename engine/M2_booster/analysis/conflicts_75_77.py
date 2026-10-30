"""Read-only analysis of the M2 geometry step 2 conflicts #75-#77 (rules/open_items.md).

Imports the M2 step 1/2 geometry (layout, blades, hardware) and the M1 rev014 geometry code read-only; writes no
file, changes no parameter. Every value printed is [H] from the [T] rules of geometry_params.yaml and the active
records (M2 rev001, M1 rev014). Temporary solids (row bands, the #76 forward cone) exist only inside this script.

Run: .venv/Scripts/python -m engine.M2_booster.analysis.conflicts_75_77
"""

import math

import cadquery as cq
import numpy as np

from engine.M2_booster.geometry import blades as B
from engine.M2_booster.geometry import hardware as HW
from engine.M2_booster.geometry import layout as L

N_SAMPLES = 16  # points per edge for the radius interval of an overlap [T]


# --- M1 parts (read-only) ------------------------------------------------------------

def m1_parts() -> dict:
    """M1 rev014 part solids (instance 0) with BOM id, qty and density id."""
    from engine.M1_inlet_fan.geometry import fan_frame, ogv, rotor_hardware
    ff = fan_frame.build()
    og = ogv.build()
    rot = rotor_hardware.build()
    sp = ff["spinner_case"]
    p = ff["parts"]
    n_s = ff["layout"]["n_struts"]
    out = {
        "M1.1.1 fan blade": (rot["blade"], rot["n"]), "M1.1.2 fan disk": (rot["disk"], 1),
        "M1.1.3 spinner": (sp["spinner"], 1), "M1.1.4 shim": (rot["shim"], rot["n"]),
        "M1.1.5 spacer": (rot["spacer"], rot["n"]), "M1.1.6 platform": (rot["platform"], rot["n"]),
        "M1.2.1 case shell": (sp["case_shell"], 1), "M1.2.2 containment ring": (sp["containment_ring"], 1),
        "M1.3.1 OGV vane": (og["vane"], og["V"]),
        "M1.4.1 hub ring": (p["hub_ring"], 1), "M1.4.2 outer ring": (p["outer_ring"], 1),
        "M1.4.3 splitter ring": (p["splitter_ring"], 1), "M1.4.4 bypass strut": (p["bypass_strut"], n_s),
        "M1.4.5 core strut": (p["core_strut"], n_s),
    }
    return {"parts": out, "frame": ff, "ogv": og, "rotor": rot,
            "frame_masses": fan_frame.masses(ff), "rotor_masses": rotor_hardware.masses(rot)}


# --- overlap measurement -----------------------------------------------------------------

def _bbox_disjoint(a: cq.Shape, b: cq.Shape) -> bool:
    ba, bb = a.BoundingBox(), b.BoundingBox()
    return (ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin
            or ba.zmax < bb.zmin or bb.zmax < ba.zmin)


def common(a: cq.Shape, b: cq.Shape) -> dict | None:
    """Common volume with its x and r intervals (r from vertices and edge samples) or None."""
    if _bbox_disjoint(a, b):
        return None
    c = a.intersect(b)
    sol = c.Solids()
    vol = sum(s.Volume() for s in sol) if sol else 0.0
    if vol <= 1e-12:
        return None
    rs = [math.hypot(v.Y, v.Z) for v in c.Vertices()]
    for e in c.Edges():
        for t in np.linspace(0.0, 1.0, N_SAMPLES):
            p = e.positionAt(float(t))
            rs.append(math.hypot(p.y, p.z))
    bb = c.BoundingBox()
    return {"volume": vol, "x": (bb.xmin, bb.xmax), "r": (min(rs), max(rs)),
            "fraction_of_smaller": vol / min(a.Volume(), b.Volume())}


def m2_axisymmetric(hb: dict) -> list[tuple[str, cq.Shape, int]]:
    """M2 parts whose overlap does not depend on clocking (drum, casing, shrouds), qty 1 each."""
    P = hb["parts"]
    out = [("M2.0.1 drum", P["drum"], 1), ("M2.0.2 casing", P["casing"], 1)]
    out += [(f"M2.{sh['row']['stage']}.4 inner shroud", s, 1) for sh, s in zip(hb["hw"]["shrouds"], P["shrouds"])]
    return out


def m2_row_bands(hb: dict) -> list[tuple[str, cq.Shape]]:
    """Temporary solids: the swept annulus of every blade row (hub line to casing over x_le..x_te), the vane foot
    rings (groove band) and the root block rings (rim band above the slot bottom). Clocking-independent stand-ins
    for the bladed parts: a rotor row sweeps its whole band; a stator row with 31-49 vanes cannot be clocked clear
    of a strut that crosses the annulus."""
    lay, H = hb["model"]["layout"], hb["hw"]
    out = []
    for r in hb["model"]["rows"]:
        out.append((f"{r['part_id']} {'rotor' if r['kind'] == 'rotor' else 'vane'} band",
                    L.band(lay["hub_line"], r["x_le"], r["x_te"], lay["r_casing"])))
    for g in H["grooves"]:
        (x0, x1), (r0, r1) = g["foot_x"], g["foot_r"]
        out.append((f"{g['row']['part_id']} foot ring", L.revolve_closed([(x0, r0), (x1, r0), (x1, r1), (x0, r1)])))
    for rim in H["rims"]:
        out.append((f"{rim['row']['part_id']} root ring",
                    HW.under_hub(lay["hub_line"], rim["x_f"], rim["x_a"], rim["r_slot_bottom"])))
    return out


def overlap_table(hb: dict, m1: dict) -> list[dict]:
    """Every (M2 part, M1 part) pair with common volume > 0. Axisymmetric M2 parts: exact, x M1 qty for the full
    set. Bladed M2 parts: instance 0 (as hardware.m1_overlap) and the clocking-free row band."""
    rows = []
    m2 = [(n, s, "exact") for n, s, _ in m2_axisymmetric(hb)]
    m2 += [(n, s, "instance0") for n, mot, s in HW.part_list(hb) if "airfoil" in n or "vane" in n
           or "root" in n or "foot" in n]
    m2 += [(n, s, "band") for n, s in m2_row_bands(hb)]
    for n2, s2, kind in m2:
        for n1, (s1, q1) in m1["parts"].items():
            c = common(s2, s1)
            if c:
                rows.append({"m2": n2, "m1": n1, "kind": kind, "m1_qty": q1,
                             "volume_set": c["volume"] * q1 if kind != "instance0" else None, **c})
    return rows


# --- #77 quantities ------------------------------------------------------------------------

def frame_numbers(hb: dict, m1: dict) -> dict:
    ff = m1["frame"]["layout"]
    lay = hb["model"]["layout"]
    rows = hb["model"]["rows"]
    H = hb["hw"]
    gap_f = float(L.v(hb["model"]["params"]["axial_gap_fraction"]))
    x21 = lay["station_21"]["x"]
    widths = [r["width"] for r in rows]
    gaps_ref = [rows[0]["width"]] + widths[:-1]  # R-G2.2: inlet gap from R1 width, then upstream row width
    length = sum(widths) + gap_f * sum(gaps_ref)
    strut_le = ff["strut_x0"]
    ogv = m1["ogv"]["vane"].BoundingBox()
    # gap fraction that would end S3 at the core strut leading edge / frame start (geometry [T] only)
    g_strut = (strut_le - x21 - sum(widths)) / sum(gaps_ref)
    g_frame = (ff["x0"] - x21 - sum(widths)) / sum(gaps_ref)
    rows_out = [{"row": r["part_id"], "x_le": r["x_le"], "x_te": r["x_te"], "width": r["width"],
                 "hub_le": r["hub_le"], "hub_te": r["hub_te"]} for r in rows]
    ogv_hub = None
    try:
        ogv_hub = min(math.hypot(v.Y, v.Z) for v in m1["ogv"]["vane"].Vertices())
    except Exception:  # noqa: BLE001
        pass
    return {"x21": x21, "x24": lay["x24"], "booster_length": length, "sum_widths": sum(widths),
            "gap_fraction": gap_f, "gap_fraction_to_strut_le": g_strut, "gap_fraction_to_frame_x0": g_frame,
            "space_x21_to_strut_le": strut_le - x21, "blading_shortfall_to_strut_le": sum(widths) - (strut_le - x21),
            "strut_shift_needed": lay["x24"] - strut_le, "frame_shift_needed": lay["x24"] - ff["x0"],
            "frame_x": (ff["x0"], ff["x1"]), "strut_x": (strut_le, strut_le + ff["strut_chord"]),
            "strut_t": ff["strut_t"], "r_split": ff["r_split"], "t_split": ff["t_split"],
            "r_core_out": ff["r_core_out"], "r_hub_frame": ff["r_hub"], "t_hub": ff["t_hub"],
            "r_bearing": ff["r_bearing"], "t_bearing": ff["t_bearing"], "x_ogv_le": ff["x_ogv_le"],
            "splitter_lip": ff["lip"], "ogv_x": (ogv.xmin, ogv.xmax), "ogv_r_min": ogv_hub,
            "r_casing": H["r_casing"], "casing_t": H["casing_thickness"], "rows": rows_out,
            "grooves": [{"row": g["row"]["part_id"], "x": (g["x0"], g["x1"]), "depth": g["depth"],
                         "wall_behind": g["wall_behind"]} for g in H["grooves"]]}


def splitter_casing(hb: dict, m1: dict) -> dict:
    """M1 splitter ring vs M2 casing: common volume, distance and the shared surface (splitter outer face r_split =
    casing inner face r_casing)."""
    sp = m1["parts"]["M1.4.3 splitter ring"][0]
    cs = hb["parts"]["casing"]
    c = common(sp, cs)
    ff = m1["frame"]["layout"]
    H = hb["hw"]
    return {"common": c, "distance": sp.distance(cs), "r_split_minus_r_casing": ff["r_split"] - H["r_casing"],
            "shared_x": (max(ff["x21"] + ff["lip"], H["x21"]), min(ff["x1"], H["x24"])),
            "splitter_x": (ff["x21"], ff["x1"]), "casing_x": (H["x21"], H["x24"])}


def mass_numbers(hb: dict, m1: dict) -> dict:
    m2 = {m["part"]: m for m in HW.masses(hb)}
    fm = m1["frame_masses"]
    rho_ti = B.density("ti6al4v")
    rho_al = fm["splitter_ring"]["density"]
    vol_c = hb["parts"]["casing"].Volume()
    return {"splitter_ring_kg": fm["splitter_ring"]["mass_kg"], "splitter_volume": fm["splitter_ring"]["volume_m3"],
            "splitter_density": rho_al, "casing_kg": m2["M2.0.2 casing"]["mass"], "casing_volume": vol_c,
            "casing_density": rho_ti, "casing_kg_at_al_density": vol_c * rho_al}


# --- #76 drum forward cone (temporary solid) -----------------------------------------

def forward_space(hb: dict, m1: dict) -> dict:
    """Free space between the M1 disk aft face and the station 21 plane below the hub line, and the common volume
    of that region with every M1 part."""
    lay, H = hb["model"]["layout"], hb["hw"]
    rot = m1["rotor"]
    Lr = rot["layout"]
    x_b, x21 = Lr["x_b"], H["x21"]
    r_hub21 = lay["station_21"]["r_hub"]
    region = L.revolve_closed([(x_b, 0.0), (x21, 0.0), (x21, r_hub21), (x_b, r_hub21)])
    hits = {}
    for n1, (s1, _) in m1["parts"].items():
        c = common(region, s1)
        if c:
            hits[n1] = c
    prof = rot["disk_profile"]
    fe = rot["flowpath"]["rotor_edges"]
    return {"x_disk_aft": x_b, "x_disk_front": Lr["x_a"], "x21": x21, "axial_gap": x21 - x_b,
            "r_hub21": r_hub21, "r_disk_rim": Lr["r_rim"], "r_slot_bottom": Lr["r_slot_bottom"],
            "r_live_rim_inner": prof["r_rim_inner"], "r_bore": (prof["r_bore_in"], prof["r_bore_out"]),
            "disk_web": prof["t_web"], "disk_bore_width": prof["w_bore"], "x_disk_mid": prof["x_mid"],
            "fan_hub_te": fe["te_hub"], "region_hits": hits,
            "r_rim1_inner": H["rims"][0]["r_inner"], "r_rim1_slot_bottom": H["rims"][0]["r_slot_bottom"],
            "rim1_x": (H["rims"][0]["x_f"], H["rims"][0]["x_a"]), "flange": H["flange"],
            "wall1": H["shrouds"][0]["wall"]}


def forward_cone(hb: dict, fs: dict) -> cq.Solid:
    """Temporary drum forward cone (#76 option, not a design): aft-face flange ring on the M1 disk live rim
    (r_live_rim_inner .. r_slot_bottom, axial thickness = R-G2.13 flange thickness) and a conical shell of the
    stage 1 drum wall thickness from the flange at the bolt circle to the drum flange at station 21."""
    t_fl = fs["flange"]["x"][1] - fs["flange"]["x"][0]
    t = fs["wall1"]
    x0, x1 = fs["x_disk_aft"], fs["x21"]
    r0i, r0o = fs["r_live_rim_inner"], fs["r_slot_bottom"]
    ring = L.revolve_closed([(x0, r0i), (x0 + t_fl, r0i), (x0 + t_fl, r0o), (x0, r0o)])
    rb = fs["flange"]["r_bolt_circle"]
    r1 = fs["flange"]["r_inner"]  # drum flange inner radius at station 21 (= M1 live-rim inner radius)
    shell = L.revolve_closed([(x0 + t_fl, rb - 0.5 * t), (x1, r1), (x1, r1 + t), (x0 + t_fl, rb + 0.5 * t)])
    out = ring.fuse(shell).clean().Solids()
    return out[0]


def cone_check(hb: dict, m1: dict, fs: dict) -> dict:
    cone = forward_cone(hb, fs)
    rows = {}
    for n1, (s1, _) in m1["parts"].items():
        c = common(cone, s1)
        try:
            d = cone.distance(s1)
        except Exception:  # noqa: BLE001
            d = None
        rows[n1] = {"common": c, "distance": d}
    m2 = {}
    for n2, _, s2 in HW.part_list(hb):
        c = common(cone, s2)
        if c:
            m2[n2] = c
    rho = B.density("ti6al4v")
    return {"volume": cone.Volume(), "mass_ti": cone.Volume() * rho, "m1": rows, "m2_common": m2,
            "r_min": fs["r_live_rim_inner"], "margin_to_m8_r": fs["r_live_rim_inner"] - m1["frame"]["layout"]["r_bearing"]}


# --- #75 slot closure ----------------------------------------------------------------------

def slot_closure(hb: dict) -> list[dict]:
    """Terms of the aft-face slot closure per rotor: slot bottom vs the tooth root (drum wall outer radius) of the
    next stator. r_wall_out = r_hub_min(S) - (shroud + land + tooth) - seal clearance, with shroud/land/tooth =
    (0.08 + 0.06 + 0.06 x 1.0) x stator chord; r_slot_bottom = r_hub_min(R) - 0.25 x rotor chord."""
    H = hb["hw"]
    out = []
    for i, rim in enumerate(H["rims"]):
        sh = H["shrouds"][i] if i < len(H["shrouds"]) else None
        prev = H["shrouds"][i - 1] if i > 0 else None
        d = {"row": rim["row"]["part_id"], "rotor_chord": rim["row"]["chord"], "hub_min_rotor": rim["hub_min"],
             "slot_depth": rim["slot_depth"], "r_slot_bottom": rim["r_slot_bottom"], "r_inner": rim["r_inner"],
             "live_rim": rim["live_rim"], "slot_open_front": rim["slot_open_front"],
             "slot_open_aft": rim["slot_open_aft"], "closed_aft": rim["slot_closed_height_aft"],
             "rim_x": (rim["x_f"], rim["x_a"]),
             "hub_front": L.r_at(H["hub"], rim["x_f"]), "hub_aft": L.r_at(H["hub"], rim["x_a"])}
        # alternative bottom (information): slot bottom parallel to the local hub line, same depth
        d["sloped_bottom_front"] = d["hub_front"] - rim["slot_depth"]
        d["sloped_bottom_aft"] = d["hub_aft"] - rim["slot_depth"]
        if prev:
            d["sloped_front_margin"] = d["sloped_bottom_front"] - prev["r_wall_out"]
        if prev:
            d["front_wall_out"] = prev["r_wall_out"]
            d["front_margin"] = rim["r_slot_bottom"] - prev["r_wall_out"]
        if sh:
            stack = sh["t_shroud"] + sh["t_land"] + sh["tooth_height"]
            d.update({"stator": sh["row"]["part_id"], "stator_chord": sh["row"]["chord"],
                      "hub_min_stator": sh["r_hub_min"], "hub_rise": sh["r_hub_min"] - rim["hub_min"],
                      "seal_stack": stack, "seal_stack_over_stator_chord": stack / sh["row"]["chord"],
                      "seal_clearance": sh["seal_clearance"], "r_wall_out": sh["r_wall_out"],
                      "wall": sh["wall"], "r_wall_in": sh["r_wall_in"],
                      # closure height = hub_rise + slot_depth - seal_stack - seal_clearance
                      "closure_check": sh["r_wall_out"] - rim["r_slot_bottom"],
                      # alternative values (information, not applied)
                      "slot_depth_ratio_to_open": (rim["hub_min"] - sh["r_wall_out"]) / rim["row"]["chord"],
                      "depth_shallow_slot": rim["hub_min"] - sh["r_wall_out"],
                      "wall_drop_needed": sh["r_wall_out"] - rim["r_slot_bottom"],
                      "tooth_height_if_wall_at_slot_bottom": sh["r_tooth_tip"] - (rim["r_slot_bottom"]),
                      "sloped_aft_margin": d["sloped_bottom_aft"] - sh["r_wall_out"],
                      "seal_stack_ratio_to_open": (sh["r_hub_min"] - rim["r_slot_bottom"] - sh["seal_clearance"])
                      / sh["row"]["chord"]})
        out.append(d)
    return out


def run() -> dict:
    hb = HW.build()
    m1 = m1_parts()
    fs = forward_space(hb, m1)
    return {"overlaps": overlap_table(hb, m1), "frame": frame_numbers(hb, m1), "mass": mass_numbers(hb, m1),
            "forward": fs, "cone": cone_check(hb, m1, fs), "slots": slot_closure(hb),
            "splitter_casing": splitter_casing(hb, m1)}


def _fmt(t):
    return f"{t[0]:.5f}-{t[1]:.5f}"


def main() -> None:
    res = run()
    print("== #77 overlaps (volume m3; set = x M1 qty for exact/band) ==")
    for r in res["overlaps"]:
        vs = "" if r["volume_set"] is None else f" set {r['volume_set']:.3e}"
        print(f"{r['kind']:<9} {r['m2']:<26} x {r['m1']:<24} V {r['volume']:.3e}{vs} frac {r['fraction_of_smaller']:.3f}"
              f" x {_fmt(r['x'])} r {_fmt(r['r'])}")
    f = res["frame"]
    print("== #77 layout ==")
    for k, v in f.items():
        if k not in ("rows", "grooves"):
            print(k, v)
    for r in f["rows"]:
        print(r)
    for g in f["grooves"]:
        print(g)
    print("== mass ==", res["mass"])
    print("== splitter vs casing ==", res["splitter_casing"])
    print("== #76 forward space ==")
    fs = res["forward"]
    for k, v in fs.items():
        if k != "region_hits":
            print(k, v)
    for k, v in fs["region_hits"].items():
        print("region hit", k, v)
    c = res["cone"]
    print("== #76 cone ==", "volume", c["volume"], "mass_ti", c["mass_ti"], "margin_to_m8_r", c["margin_to_m8_r"])
    for k, v in c["m1"].items():
        print("cone vs", k, "common", v["common"], "distance", v["distance"])
    for k, v in c["m2_common"].items():
        print("cone vs M2", k, v)
    print("== #75 slots ==")
    for s in res["slots"]:
        print(s)


if __name__ == "__main__":
    main()
