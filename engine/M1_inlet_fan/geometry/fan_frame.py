"""M1 fan frame (M1.4), step 5f, amended by CR-002 option a and CR-003 (rules/geometry.md R-G1.1-R-G1.11).
CadQuery, frame.py axes (this module is the fan frame part, not the axes module).

Parts [T sizes, fan_frame_params.yaml; M2 values read at run time via m2_boundary.py, never typed]:
- outer ring M1.4.2: bypass outer wall at the casing-wall radius from the OGV leading edge (front flange mating the
  case rear flange) to the bypass zone end; it is the outer duct wall over the OGV;
- no splitter ring: the core/bypass divider wall from station 21 to station 24 is the M2 casing M2.0.2 (CR-002);
  bypass struts M1.4.4 (bypass zone) stand on its outer face r_root = r_split2 + M2 casing thickness;
- core wall ring M1.4.6: divider wall continued from M2 station 24 to the core zone end, r_split2 to r_root;
- hub ring M1.4.1: core passage inner wall at the M2 station 24/25 hub radius in the core zone, with an inward
  bearing-support flange whose inner rim is the M8 boundary (shaft and bearings not designed);
- core struts M1.4.5 (hub ring to the M2 station 24/25 tip radius), flat plates trimmed to their annuli.
Zones (R-G1.1): bypass zone station 13 plane (OGV trailing edge) to station 13 + L; core zone M2 station 24 to
station 24 + L (CR-003). VBV openings are not modelled (R-G1.10, #48).
"""

from functools import lru_cache
from pathlib import Path

import cadquery as cq

from core import records
from core.util import read_yaml
from engine.M1_inlet_fan.geometry import fan_ring as ring
from engine.M1_inlet_fan.geometry import frame as fr
from engine.M1_inlet_fan.geometry import m2_boundary as m2b
from engine.M1_inlet_fan.geometry import ogv as ogvm
from engine.M1_inlet_fan.geometry import rotor_hardware as rh
from engine.M1_inlet_fan.geometry import spinner_case as sc

PARAMS = fr.HERE / "fan_frame_params.yaml"
PARTS = ("outer_ring", "hub_ring", "wall_ring", "bypass_strut", "core_strut")
RINGS = ("outer_ring", "hub_ring", "wall_ring")
PART_IDS = {"hub_ring": "M1.4.1", "outer_ring": "M1.4.2", "bypass_strut": "M1.4.4", "core_strut": "M1.4.5",
            "wall_ring": "M1.4.6"}


def frame_params() -> dict:
    return read_yaml(PARAMS)


def _p(key):
    return fr.v(frame_params()[key])


def layout(fp: dict, case_info: dict) -> dict:
    """Frame layout [H from T]. x0/x1/strut_x0: bypass zone (station 13 + L); xc0/xc1/core_strut_x0: core zone
    (M2 station 24 + L)."""
    m2 = m2b.m2_boundary()
    c_tip = fp["axial_chord_m"]["tip"]
    r_tip = fp["rotor_edges"]["le_tip"][1]
    length = _p("length_over_tip_axial_chord") * c_tip
    x0 = fp["stations"]["13"]["x_m"]
    x1 = x0 + length
    xc0 = m2["x24"]
    xc1 = xc0 + length
    if not xc0 > fp["stations"]["21"]["x_m"]:
        raise ValueError("M2 station 24 is not behind station 21")
    r_wall = fr.r_at(fp["curves"]["casing_wall"], x0)
    r_s = fp["r_split2_m"]
    r_root = fp["stations"]["13"]["r_inner_m"]  # R-G1.3 (flowpath.py: r_split2 + M2 casing thickness)
    r_h21 = fp["stations"]["21"]["r_hub_m"]
    t_o = _p("outer_ring_thickness_over_tip_radius") * r_tip
    t_ref = _p("reference_wall_thickness_over_split_radius") * r_s
    t_h = _p("hub_ring_thickness_over_split_thickness") * t_ref
    chord = _p("strut_chord_over_length") * length
    return {"x0": x0, "x1": x1, "xc0": xc0, "xc1": xc1, "length": length, "x_ogv_le": fp["x_ogv_le_m"],
            "x21": fp["stations"]["21"]["x_m"], "x24": xc0,
            "r_wall": r_wall, "r_split": r_s, "r_root": r_root, "r_hub": m2["r_core_hub"],
            "r_core_out": m2["r_core_tip"], "t_outer": t_o, "t_ref": t_ref, "t_hub": t_h,
            "t_wall": r_root - r_s, "r_bearing": _p("bearing_flange_inner_over_hub_radius") * r_h21,
            "t_bearing": _p("bearing_flange_thickness_over_split_thickness") * t_ref,
            "flange_t": case_info["flange_m"], "flange_h": _p("flange_height_over_outer_ring") * t_o,
            "strut_chord": chord, "strut_t": _p("strut_thickness_over_chord") * chord,
            "strut_x0": (x0 + x1 - chord) / 2, "core_strut_x0": (xc0 + xc1 - chord) / 2,
            "n_struts": int(_p("strut_count")), "m2_revision": m2["revision"]}


def outer_ring(L: dict) -> cq.Solid:
    xa, xb, r, t = L["x_ogv_le"], L["x1"], L["r_wall"], L["t_outer"]
    tf, hf = L["flange_t"], L["flange_h"]
    return fr.revolve_closed([(xa, r), (xb, r), (xb, r + t), (xa + tf, r + t), (xa + tf, r + t + hf), (xa, r + t + hf)])


def wall_ring(L: dict) -> cq.Solid:
    """Core/bypass divider wall in the core zone (R-G1.2): continues M2.0.2 from station 24, r_split2 to r_root."""
    xa, xb = L["xc0"], L["xc1"]
    return fr.revolve_closed([(xa, L["r_split"]), (xb, L["r_split"]), (xb, L["r_root"]), (xa, L["r_root"])])


def hub_ring(L: dict) -> cq.Solid:
    xa, xb, r, t = L["xc0"], L["xc1"], L["r_hub"], L["t_hub"]
    tb, rb = L["t_bearing"], L["r_bearing"]
    return fr.revolve_closed([(xa, r), (xb, r), (xb, rb), (xb - tb, rb), (xb - tb, r - t), (xa, r - t)])


def strut(L: dict, r_in: float, r_out: float, zone: str = "bypass") -> cq.Solid:
    """Flat strut plate at top dead centre in its zone (R-G1.5, R-G1.9), trimmed to the annulus r_in..r_out."""
    xa, xb, xs = ((L["x0"], L["x1"], L["strut_x0"]) if zone == "bypass" else
                  (L["xc0"], L["xc1"], L["core_strut_x0"]))
    c, t = L["strut_chord"], L["strut_t"]
    box = cq.Solid.makeBox(c, t, r_out - r_in + 0.1, pnt=cq.Vector(xs, -t / 2, r_in - 0.05))
    ann = fr.revolve_closed([(xa - 0.01, r_in), (xa - 0.01, r_out), (xb + 0.01, r_out), (xb + 0.01, r_in)])
    return fr.boolean("common", box, ann).Solids()[0]


@lru_cache(maxsize=2)
def build(rev: str | None = None, root: Path = records.ROOT) -> dict:
    sp = sc.build(rev, root)
    fp = sp["rotor"]["flowpath"]
    L = layout(fp, sp["info"]["case_shell"])
    parts = {"outer_ring": outer_ring(L), "hub_ring": hub_ring(L), "wall_ring": wall_ring(L),
             "bypass_strut": strut(L, L["r_root"], L["r_wall"], "bypass"),
             "core_strut": strut(L, L["r_hub"], L["r_core_out"], "core")}
    return {"flowpath": fp, "layout": L, "parts": parts, "spinner_case": sp}


def interfaces(model: dict) -> dict:
    """Interface points of M1 at its boundaries [H from T and M2 values read at run time]."""
    L, fp = model["layout"], model["flowpath"]
    st = fp["stations"]
    return {
        "M2_station_21": {"x_m": st["21"]["x_m"], "r_hub_m": st["21"]["r_hub_m"], "r_tip_m": st["21"]["r_tip_m"],
                          "core_passage_in_frame_m": [L["r_hub"], L["r_core_out"]], "x_frame_m": [L["xc0"], L["xc1"]],
                          "divider_wall": {"part": "M2.0.2", "x_m": [st["21"]["x_m"], L["x24"]],
                                           "r_m": [L["r_split"], L["r_root"]]},
                          "note": "splitter lip plane; divider wall M2.0.2 (M2) from station 21 to 24, then M1.4.6; "
                                  "core passage in the frame = M2 station 24/25 annulus (CR-002, CR-003)"},
        "M7_station_13": {"x_m": st["13"]["x_m"], "r_inner_m": st["13"]["r_inner_m"], "r_outer_m": st["13"]["r_outer_m"],
                          "r_casing_wall_m": L["r_wall"], "bypass_duct_at_frame_end_x_m": L["x1"]},
        "M8_bearing_support": {"x_face_m": [L["xc1"] - L["t_bearing"], L["xc1"]], "r_inner_m": L["r_bearing"],
                               "note": "flange inner rim only; LP shaft and bearings 1-2 are M8 (CR via M0); radius "
                                       "kept by CR-003, M8 reviews it when M8 starts"},
        "nacelle_inlet": {"x_m": model["spinner_case"]["info"]["case_shell"]["x_front_m"],
                          "note": "case front flange; inlet lip not M1 (open issue #38)"},
        "VBV": {"modelled": False,
                "candidate_walls_x_m": {"M2.0.2": [st["21"]["x_m"], L["x24"]], "M1.4.6": [L["xc0"], L["xc1"]]},
                "r_m": [L["r_split"], L["r_root"]],
                "note": "openings not modelled (former M1.4.3 placeholder removed with the splitter ring, CR-002); "
                        "they would cut the divider wall; owner not set by M0 (#48)"},
    }


def masses(model: dict) -> dict:
    rho = rh.densities()[fr.v(frame_params()["material"])]
    n = model["layout"]["n_struts"]
    qty = {"outer_ring": 1, "hub_ring": 1, "wall_ring": 1, "bypass_strut": n, "core_strut": n}
    return {k: {"volume_m3": s.Volume(), "density": rho["value"], "density_tag": rho["tag"],
                "mass_kg": s.Volume() * rho["value"], "qty": qty[k], "set_kg": s.Volume() * rho["value"] * qty[k]}
            for k, s in model["parts"].items()}


def checks(model: dict) -> dict:
    """Common volume and distance of the frame parts with the OGV vanes, case, containment ring, rotor and among
    themselves [H]. Rings are axisymmetric (vane 0 stands for all vanes); struts are checked against all vanes whose
    bounding box meets theirs; strut-to-ring pairs for strut 0 only (rings axisymmetric). Bounding-box prefilter:
    disjoint boxes give common volume 0 without a boolean (distance not computed). M2 parts: m2_checks."""
    p, n = model["parts"], model["layout"]["n_struts"]
    sp = model["spinner_case"]
    og = ogvm.build(model["flowpath"]["revision"])
    vanes = ogvm.row(og["vane"], og["V"])
    struts = {f"bypass_strut_{k:02d}": fr.rotate_about_axis(p["bypass_strut"], k * 360.0 / n) for k in range(n)}
    struts.update({f"core_strut_{k:02d}": fr.rotate_about_axis(p["core_strut"], k * 360.0 / n) for k in range(n)})
    out = {}

    def row(a, b):
        if not ring._bbox_overlap(a, b):
            return {"method": "bbox_disjoint", "common_volume_m3": 0.0, "distance_m": None}
        return {"method": "boolean", "common_volume_m3": fr.boolean("common", a, b).Volume(), "distance_m": a.distance(b)}

    for ring_name in RINGS:
        out[f"{ring_name}-ogv0"] = row(p[ring_name], og["vane"])
        out[f"{ring_name}-case"] = row(p[ring_name], sp["case_shell"])
        out[f"{ring_name}-rotor_blade"] = row(p[ring_name], sp["rotor"]["blade"])
        out[f"{ring_name}-disk"] = row(p[ring_name], sp["rotor"]["disk"])
    vane_boxes = [v.BoundingBox() for v in vanes]  # computed once (spline solids)
    for name, s in struts.items():
        sb = s.BoundingBox()
        for k, (vane, vb) in enumerate(zip(vanes, vane_boxes)):
            if sb.xmin <= vb.xmax and vb.xmin <= sb.xmax and sb.ymin <= vb.ymax and vb.ymin <= sb.ymax \
                    and sb.zmin <= vb.zmax and vb.zmin <= sb.zmax:
                out[f"{name}-ogv{k:02d}"] = row(s, vane)
    out["struts-ogv_row"] = {"method": "bbox_disjoint" if not any(k.startswith(("bypass_strut_", "core_strut_"))
                                                                   for k in out) else "boolean",
                             "common_volume_m3": 0.0, "distance_m": None}
    for name in ("bypass_strut", "core_strut"):
        for ring_name in RINGS:
            out[f"{name}-{ring_name}"] = row(p[name], p[ring_name])
    out["outer_ring-containment"] = row(p["outer_ring"], sp["containment_ring"])
    out["wall_ring-hub_ring"] = row(p["wall_ring"], p["hub_ring"])
    return out


def root_radii(model: dict) -> dict:
    """Smallest vertex radius of the OGV vane 0 and the bypass strut vs r_root (R-G1.4, R-G1.5) [H]."""
    og = ogvm.build(model["flowpath"]["revision"])

    def r_min(s):
        return min(fr.radius(v.Center()) for v in s.Vertices())

    return {"r_root": model["layout"]["r_root"], "ogv_root": r_min(og["vane"]),
            "bypass_strut_root": r_min(model["parts"]["bypass_strut"])}


def m2_checks(model: dict) -> dict:
    """M1 frame and OGV against the M2 hardware (R-G1.11): common volumes from M2 hardware.m1_overlap (read-only),
    mating distances to the M2 casing, and the m2_boundary values vs M2 hardware.build. Call after build()."""
    from engine.M2_booster.geometry import hardware as HW
    hb = HW.build()
    cas = hb["parts"]["casing"]
    og = ogvm.build(model["flowpath"]["revision"])
    p = model["parts"]
    return {"overlaps": HW.m1_overlap(hb)["overlaps"], "boundary": m2b.cross_check(),
            "distance_m": {"ogv0-m2_casing": og["vane"].distance(cas),
                           "bypass_strut-m2_casing": p["bypass_strut"].distance(cas),
                           "wall_ring-m2_casing": p["wall_ring"].distance(cas)}}


def export(model: dict) -> dict:
    rev, n = model["flowpath"]["revision"], model["layout"]["n_struts"]
    paths = {k: fr.export_step(s, f"frame_{k}", rev) for k, s in model["parts"].items()}
    p = model["parts"]
    inst = [(PART_IDS[k], p[k], 0.0) for k in RINGS]
    for k in range(n):
        a = k * 360.0 / n
        inst += [(f"M1.4.4_{k:02d}", p["bypass_strut"], a), (f"M1.4.5_{k:02d}", p["core_strut"], a)]
    paths["fan_frame"] = fr.export_assembly(inst, "fan_frame", rev)
    return paths


def main() -> None:
    model = build()
    print({k: round(v, 6) if isinstance(v, float) else v for k, v in model["layout"].items()})
    for k, r in masses(model).items():
        print(f"  {k}: {r['mass_kg']:.4f} kg x {r['qty']} = {r['set_kg']:.4f} kg ({r['density_tag']})")
    for k, r in checks(model).items():
        d = "-" if r["distance_m"] is None else f"{r['distance_m'] * 1e3:.3f} mm"
        print(f"  {k}: {r['method']}, common {r['common_volume_m3']:.2e}, distance {d}")
    print("  root radii", root_radii(model))
    for k, v in interfaces(model).items():
        print(f"  {k}: {v}")
    for k, p in export(model).items():
        print(f"  STEP {k}: {p.name}")


if __name__ == "__main__":
    main()
