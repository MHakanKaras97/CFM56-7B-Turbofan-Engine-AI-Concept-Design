"""M1 fan frame (M1.4), step 5f. CadQuery, frame.py axes (this module is the fan frame part, not the axes module).

Parts [T sizes, fan_frame_params.yaml]:
- outer ring: bypass outer wall at the casing-wall radius from the OGV leading edge (front flange mating the case
  rear flange) to the frame end; it is the outer duct wall over the OGV;
- splitter ring: from the station 21 lip (zero thickness, linear lip) to the frame end; outer face = bypass inner
  wall at r_split2 (under the OGV), inner face = core passage outer wall; 12 placeholder VBV openings in the frame
  zone (owner not set by M0);
- hub ring: core passage inner wall at r_hub2 in the frame zone, with an inward bearing-support flange whose inner
  rim is the M8 boundary (shaft and bearings not designed);
- bypass struts (splitter to outer ring) and core struts (hub to splitter), flat plates trimmed to their annuli.
Frame zone: station 13 plane (OGV trailing edge) to station 13 + length.
"""

import math
from functools import lru_cache
from pathlib import Path

import cadquery as cq

from core import records
from core.util import read_yaml
from engine.M1_inlet_fan.geometry import fan_ring as ring
from engine.M1_inlet_fan.geometry import frame as fr
from engine.M1_inlet_fan.geometry import ogv as ogvm
from engine.M1_inlet_fan.geometry import rotor_hardware as rh
from engine.M1_inlet_fan.geometry import spinner_case as sc

PARAMS = fr.HERE / "fan_frame_params.yaml"
PARTS = ("outer_ring", "splitter_ring", "hub_ring", "bypass_strut", "core_strut")


def frame_params() -> dict:
    return read_yaml(PARAMS)


def _p(key):
    return fr.v(frame_params()[key])


def layout(fp: dict, case_info: dict) -> dict:
    c_tip = fp["axial_chord_m"]["tip"]
    r_tip = fp["rotor_edges"]["le_tip"][1]
    x0 = fp["stations"]["13"]["x_m"]
    x1 = x0 + _p("length_over_tip_axial_chord") * c_tip
    r_wall = fr.r_at(fp["curves"]["casing_wall"], x0)
    r_s, r_h = fp["r_split2_m"], fp["stations"]["21"]["r_hub_m"]
    t_o = _p("outer_ring_thickness_over_tip_radius") * r_tip
    t_s = _p("splitter_thickness_over_split_radius") * r_s
    t_h = _p("hub_ring_thickness_over_split_thickness") * t_s
    chord = _p("strut_chord_over_length") * (x1 - x0)
    return {"x0": x0, "x1": x1, "x_ogv_le": fp["x_ogv_le_m"], "x21": fp["stations"]["21"]["x_m"],
            "r_wall": r_wall, "r_split": r_s, "r_hub": r_h, "t_outer": t_o, "t_split": t_s, "t_hub": t_h,
            "lip": _p("splitter_lip_length_over_thickness") * t_s,
            "r_core_out": r_s - t_s, "r_bearing": _p("bearing_flange_inner_over_hub_radius") * r_h,
            "t_bearing": _p("bearing_flange_thickness_over_split_thickness") * t_s,
            "flange_t": case_info["flange_m"], "flange_h": _p("flange_height_over_outer_ring") * t_o,
            "strut_chord": chord, "strut_t": _p("strut_thickness_over_chord") * chord,
            "strut_x0": (x0 + x1 - chord) / 2, "n_struts": int(_p("strut_count")), "n_vbv": int(_p("vbv_count"))}


def outer_ring(L: dict) -> cq.Solid:
    xa, xb, r, t = L["x_ogv_le"], L["x1"], L["r_wall"], L["t_outer"]
    tf, hf = L["flange_t"], L["flange_h"]
    return fr.revolve_closed([(xa, r), (xb, r), (xb, r + t), (xa + tf, r + t), (xa + tf, r + t + hf), (xa, r + t + hf)])


def splitter_ring(L: dict) -> cq.Solid:
    xa, xb, r, t = L["x21"], L["x1"], L["r_split"], L["t_split"]
    body = fr.revolve_closed([(xa, r), (xb, r), (xb, r - t), (xa + L["lip"], r - t)])
    n = L["n_vbv"]
    a = _p("vbv_axial_over_length") * (L["x1"] - L["x0"])
    w = _p("vbv_tangential_over_gap") * 2 * math.pi * r / n
    box = cq.Solid.makeBox(a, w, 3 * t, pnt=cq.Vector((L["x0"] + L["x1"] - a) / 2, -w / 2, r - 2 * t))
    cuts = cq.Compound.makeCompound([fr.rotate_about_axis(box, (k + 0.5) * 360.0 / n) for k in range(n)])
    out = body.cut(cuts).Solids()
    if len(out) != 1:
        raise ValueError("splitter ring with VBV openings is not one solid")
    return out[0]


def hub_ring(L: dict) -> cq.Solid:
    xa, xb, r, t = L["x0"], L["x1"], L["r_hub"], L["t_hub"]
    tb, rb = L["t_bearing"], L["r_bearing"]
    return fr.revolve_closed([(xa, r), (xb, r), (xb, rb), (xb - tb, rb), (xb - tb, r - t), (xa, r - t)])


def strut(L: dict, r_in: float, r_out: float) -> cq.Solid:
    """Flat strut plate at top dead centre trimmed to the annulus r_in..r_out."""
    c, t = L["strut_chord"], L["strut_t"]
    box = cq.Solid.makeBox(c, t, r_out - r_in + 0.1, pnt=cq.Vector(L["strut_x0"], -t / 2, r_in - 0.05))
    ann = fr.revolve_closed([(L["x0"] - 0.01, r_in), (L["x0"] - 0.01, r_out), (L["x1"] + 0.01, r_out), (L["x1"] + 0.01, r_in)])
    return fr.boolean("common", box, ann).Solids()[0]


@lru_cache(maxsize=2)
def build(rev: str | None = None, root: Path = records.ROOT) -> dict:
    sp = sc.build(rev, root)
    fp = sp["rotor"]["flowpath"]
    L = layout(fp, sp["info"]["case_shell"])
    parts = {"outer_ring": outer_ring(L), "splitter_ring": splitter_ring(L), "hub_ring": hub_ring(L),
             "bypass_strut": strut(L, L["r_split"], L["r_wall"]), "core_strut": strut(L, L["r_hub"], L["r_core_out"])}
    return {"flowpath": fp, "layout": L, "parts": parts, "spinner_case": sp}


def interfaces(model: dict) -> dict:
    """Interface points of M1 at its boundaries [H from T]."""
    L, fp = model["layout"], model["flowpath"]
    st = fp["stations"]
    return {
        "M2_station_21": {"x_m": st["21"]["x_m"], "r_hub_m": st["21"]["r_hub_m"], "r_tip_m": st["21"]["r_tip_m"],
                          "core_passage_in_frame_m": [L["r_hub"], L["r_core_out"]], "x_frame_m": [L["x0"], L["x1"]],
                          "note": "splitter lip; the core wall inside the frame is a placeholder for the M2 flowpath"},
        "M7_station_13": {"x_m": st["13"]["x_m"], "r_inner_m": st["13"]["r_inner_m"], "r_outer_m": st["13"]["r_outer_m"],
                          "r_casing_wall_m": L["r_wall"], "bypass_duct_at_frame_end_x_m": L["x1"]},
        "M8_bearing_support": {"x_face_m": [L["x1"] - L["t_bearing"], L["x1"]], "r_inner_m": L["r_bearing"],
                               "note": "flange inner rim only; LP shaft and bearings 1-2 are M8 (CR via M0)"},
        "nacelle_inlet": {"x_m": model["spinner_case"]["info"]["case_shell"]["x_front_m"],
                          "note": "case front flange; inlet lip not M1 (open issue #38)"},
        "VBV": {"count": L["n_vbv"], "x_m": [L["x0"], L["x1"]], "r_m": [L["r_core_out"], L["r_split"]],
                "note": "placeholder openings; owner not set by M0"},
    }


def masses(model: dict) -> dict:
    rho = rh.densities()[fr.v(frame_params()["material"])]
    n = model["layout"]["n_struts"]
    qty = {"outer_ring": 1, "splitter_ring": 1, "hub_ring": 1, "bypass_strut": n, "core_strut": n}
    return {k: {"volume_m3": s.Volume(), "density": rho["value"], "density_tag": rho["tag"],
                "mass_kg": s.Volume() * rho["value"], "qty": qty[k], "set_kg": s.Volume() * rho["value"] * qty[k]}
            for k, s in model["parts"].items()}


def checks(model: dict) -> dict:
    """Common volume and distance of the frame parts with the OGV vanes, case, containment ring, rotor and among
    themselves [H]. Rings are axisymmetric (vane 0 stands for all vanes); struts are checked against all vanes whose
    bounding box meets theirs; strut-to-ring pairs for strut 0 only (rings axisymmetric). Bounding-box prefilter:
    disjoint boxes give common volume 0 without a boolean (distance not computed)."""
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

    for ring_name in ("outer_ring", "splitter_ring", "hub_ring"):
        out[f"{ring_name}-ogv0"] = row(p[ring_name], og["vane"])
        out[f"{ring_name}-case"] = row(p[ring_name], sp["case_shell"])
        out[f"{ring_name}-rotor_blade"] = row(p[ring_name], sp["rotor"]["blade"])
        out[f"{ring_name}-disk"] = row(p[ring_name], sp["rotor"]["disk"])
    vane_boxes = [v.BoundingBox() for v in vanes]  # computed once (spline solids)
    for name, s in struts.items():
        sb = s.BoundingBox()
        for k, (vane, vb) in enumerate(zip(vanes, vane_boxes)):
            if sb.xmin <= vb.xmax and vb.xmin <= sb.xmax and sb.ymin <= vb.ymax and vb.ymin <= sb.ymax                     and sb.zmin <= vb.zmax and vb.zmin <= sb.zmax:
                out[f"{name}-ogv{k:02d}"] = row(s, vane)
    out["struts-ogv_row"] = {"method": "bbox_disjoint" if not any(k.startswith(("bypass_strut_", "core_strut_"))
                                                                   for k in out) else "boolean",
                             "common_volume_m3": 0.0, "distance_m": None}
    for name in ("bypass_strut", "core_strut"):
        for ring_name in ("outer_ring", "splitter_ring", "hub_ring"):
            out[f"{name}-{ring_name}"] = row(p[name], p[ring_name])
    out["outer_ring-containment"] = row(p["outer_ring"], sp["containment_ring"])
    out["splitter_ring-hub_ring"] = row(p["splitter_ring"], p["hub_ring"])
    return out


def export(model: dict) -> dict:
    rev, n = model["flowpath"]["revision"], model["layout"]["n_struts"]
    paths = {k: fr.export_step(s, f"frame_{k}", rev) for k, s in model["parts"].items()}
    p = model["parts"]
    inst = [("M1.4.1", p["hub_ring"], 0.0), ("M1.4.2", p["outer_ring"], 0.0), ("M1.4.3", p["splitter_ring"], 0.0)]
    for k in range(n):
        a = k * 360.0 / n
        inst += [(f"M1.4.4_{k:02d}", p["bypass_strut"], a), (f"M1.4.5_{k:02d}", p["core_strut"], a)]
    paths["fan_frame"] = fr.export_assembly(inst, "fan_frame", rev)
    return paths


def main() -> None:
    model = build()
    print({k: round(v, 5) if isinstance(v, float) else v for k, v in model["layout"].items()})
    for k, r in masses(model).items():
        print(f"  {k}: {r['mass_kg']:.3f} kg x {r['qty']} = {r['set_kg']:.3f} kg ({r['density_tag']})")
    for k, r in checks(model).items():
        d = "-" if r["distance_m"] is None else f"{r['distance_m'] * 1e3:.3f} mm"
        print(f"  {k}: {r['method']}, common {r['common_volume_m3']:.2e}, distance {d}")
    for k, v in interfaces(model).items():
        print(f"  {k}: {v}")
    for k, p in export(model).items():
        print(f"  STEP {k}: {p.name}")


if __name__ == "__main__":
    main()
