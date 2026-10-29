"""M1 meridional flowpath, stations 2 -> 13 (bypass) and 2 -> 21 (core), step 5b. CadQuery, frame.py axes.

Inputs: the active record (annulus radii r_hub1, r_tip1, r_split1, r_hub2, r_tip2; tube exit areas), the record's
running tip clearance (params losses.tip_clearance_running), the 5a blade solid (blade_solid.build, for the axial
positions of its edges), geometry_params.yaml ratios [T] and the ICD fan_face_area via core.budgets.read_icd.

Construction:
- Gas path = blade-swept annulus of the record: hub line r_hub1 -> r_hub2 and tip line r_tip1 -> r_tip2, straight
  between the rotor leading and trailing edges [T]. The edge points are where the blade's leading / trailing edge
  curve (on the solid) reaches the record radius, so the trimmed blade meets the record radii at its corners [H].
  Leading-edge hub: the planar root section lies above r_hub1 off the y = 0 line, so the leading-edge x of the root
  section is used (the root stub of fan_ring.py reaches the hub there).
- Splitter: dividing streamline r_split1 -> r_split2 through the rotor; r_split2 = exit radius that holds the
  record's inner-tube exit area (sum of tube A2, stream inner) [H]; the record's r_split2_initial is only the
  radial-equilibrium start value. Splitter lip (station 21 plane) at a gap [T] behind the rotor trailing edge at the
  splitter radius; the splitter wall then runs at r_split2 to station 13 [T].
- Station 2 plane: the most forward point of the blade [H]. Station 13 plane: OGV exit placed by [T] ratios (5e).
- Casing wall = gas-path tip line + running tip clearance, radially (case side of the clearance, open issue #24).
  The clearance annulus is outside the record's flow area (the meanline treats clearance only as a loss).
"""

import math
from functools import lru_cache
from pathlib import Path

import numpy as np

from core import records
from core.budgets import read_icd
from core.util import write_yaml
from engine.M1_inlet_fan.geometry import blade_solid as bs
from engine.M1_inlet_fan.geometry import frame as fr

OUT_YAML = fr.HERE / "flowpath.yaml"


@lru_cache(maxsize=2)
def raw_blade(rev: str, root: Path = records.ROOT) -> dict:
    """The 5a blade model (blade_solid.build), cached per revision."""
    return bs.build(rev, root=root)


def edge_curves(solid) -> dict:
    """Leading- and trailing-edge curves of the lofted airfoil: the two seam edges that run from root to tip,
    sampled root to tip as arrays of (x, y, z) [H]."""
    seams = [e for e in solid.Edges() if abs(e.startPoint().z - e.endPoint().z) > 0.1]
    if len(seams) != 2:
        raise ValueError(f"expected 2 root-to-tip seam edges, found {len(seams)}")
    pts = []
    for e in seams:
        p = bs._edge_points(e, 2000)
        pts.append(p if p[0, 2] < p[-1, 2] else p[::-1])
    le, te = sorted(pts, key=lambda p: p[:, 0].mean())
    return {"le": le, "te": te}


def x_at_radius(curve: np.ndarray, r: float) -> float:
    """Axial position where an edge curve (root to tip) reaches radius r; below its root end: the root x."""
    rad = np.hypot(curve[:, 1], curve[:, 2])
    if r <= rad[0]:
        return float(curve[0, 0])
    if r >= rad[-1]:
        raise ValueError(f"edge curve does not reach radius {r}")
    i = int(np.argmax(rad >= r))
    t = (r - rad[i - 1]) / (rad[i] - rad[i - 1])
    return float(curve[i - 1, 0] + t * (curve[i, 0] - curve[i - 1, 0]))


def _dedupe(points):
    out = []
    for p in points:
        if not out or abs(p[0] - out[-1][0]) > 1e-9 or abs(p[1] - out[-1][1]) > 1e-9:
            out.append(p)
    return out


def build(rev: str | None = None, root: Path = records.ROOT) -> dict:
    """Meridional curves, stations and interface points [H]."""
    rec = fr.record(rev, root)
    rev, res, par = rec["revision"], rec["results"], rec["params"]
    gp = fr.geometry_params()["flowpath"]
    ann = res["annulus"]
    r_hub1, r_tip1, r_split1 = ann["r_hub1_m"], ann["r_tip1_m"], ann["r_split1_m"]
    r_hub2, r_tip2 = ann["r_hub2_m"], ann["r_tip2_m"]
    a2_inner = sum(t["A2_m2"] for t in res["tubes"] if t["stream"] == "inner")
    r_split2 = math.sqrt(r_hub2 ** 2 + a2_inner / math.pi)
    clearance = fr.v(par["losses"]["tip_clearance_running"]) * 1e-3

    blade = raw_blade(rev, root)
    ec = edge_curves(blade["solid"])
    pt = {name: (x_at_radius(ec[edge], r), r) for name, edge, r in
          (("le_hub", "le", r_hub1), ("te_hub", "te", r_hub2), ("le_split", "le", r_split1),
           ("te_split", "te", r_split2), ("le_tip", "le", r_tip1), ("te_tip", "te", r_tip2))}
    chord_ax = {k: pt[f"te_{k}"][0] - pt[f"le_{k}"][0] for k in ("hub", "split", "tip")}
    bb = blade["solid"].BoundingBox()
    x2 = min(bb.xmin, *(pt[k][0] for k in ("le_hub", "le_split", "le_tip")))
    x21 = pt["te_split"][0] + fr.v(gp["splitter_gap_over_axial_chord"]) * chord_ax["split"]
    x_ogv_le = pt["te_tip"][0] + fr.v(gp["rotor_ogv_gap_over_tip_axial_chord"]) * chord_ax["tip"]
    x13 = x_ogv_le + fr.v(gp["ogv_axial_chord_over_tip_axial_chord"]) * chord_ax["tip"]
    if not (x21 > pt["te_hub"][0] and x13 > x21 and x13 > bb.xmax):
        raise ValueError("station planes out of order (21 behind the hub trailing edge, 13 behind 21 and the blade)")

    curves = {
        "hub": _dedupe([(x2, r_hub1), pt["le_hub"], pt["te_hub"], (x21, r_hub2)]),
        "dividing_streamline": _dedupe([(x2, r_split1), pt["le_split"], pt["te_split"], (x21, r_split2)]),
        "splitter_wall": [(x21, r_split2), (x13, r_split2)],
        "tip": _dedupe([(x2, r_tip1), pt["le_tip"], pt["te_tip"], (x13, r_tip2)]),
    }
    curves["casing_wall"] = [(x, r + clearance) for x, r in curves["tip"]]

    def ring(ro, ri):
        return math.pi * (ro * ro - ri * ri)

    fan_face = fr.v(read_icd("M1 agent")["fan_face_area"])
    stations = {
        "2": {"x_m": x2, "r_hub_m": r_hub1, "r_split_m": r_split1, "r_tip_m": r_tip1,
              "area_m2": ring(r_tip1, r_hub1), "area_core_m2": ring(r_split1, r_hub1),
              "area_bypass_m2": ring(r_tip1, r_split1), "area_inside_casing_wall_m2": ring(r_tip1 + clearance, r_hub1),
              "icd_fan_face_area_m2": fan_face, "fan_face_area_deviation": ring(r_tip1, r_hub1) / fan_face - 1},
        "21": {"x_m": x21, "r_hub_m": r_hub2, "r_tip_m": r_split2, "area_m2": ring(r_split2, r_hub2)},
        "13": {"x_m": x13, "r_inner_m": r_split2, "r_outer_m": r_tip2, "area_m2": ring(r_tip2, r_split2),
               "r_casing_wall_m": r_tip2 + clearance, "area_inside_casing_wall_m2": ring(r_tip2 + clearance, r_split2)},
    }
    return {"revision": rev, "curves": curves, "stations": stations, "rotor_edges": pt, "axial_chord_m": chord_ax,
            "x_ogv_le_m": x_ogv_le, "tip_clearance_m": clearance, "r_split2_m": r_split2,
            "r_split2_initial_m_info": ann["r_split2_initial_m"],
            "blade_x_range_m": (bb.xmin, bb.xmax), "blade": blade}


def solids(fp: dict) -> dict:
    """Gas-path volumes (core 2 -> 21, bypass 2 -> 13) and the casing wall surface."""
    c = fp["curves"]
    core = fr.revolve_closed(c["hub"] + c["dividing_streamline"][::-1])
    bypass = fr.revolve_closed(c["dividing_streamline"] + c["splitter_wall"][1:] + c["tip"][::-1])
    return {"flowpath_core": core, "flowpath_bypass": bypass, "casing_wall_surface": fr.revolve_open(c["casing_wall"])}


def rotor_trim_tool(fp: dict, margin: float = 0.05) -> "fr.cq.Solid":
    """Blade-swept annulus around the rotor (hub line to tip line, constant beyond the edges), used to trim the
    blade to the record radii."""
    lo, hi = fp["blade_x_range_m"][0] - margin, fp["blade_x_range_m"][1] + margin
    e = fp["rotor_edges"]
    hub = [(lo, e["le_hub"][1]), e["le_hub"], e["te_hub"], (hi, e["te_hub"][1])]
    tip = [(lo, e["le_tip"][1]), e["le_tip"], e["te_tip"], (hi, e["te_tip"][1])]
    return fr.revolve_closed(hub + tip[::-1])


def _r6(x):
    if isinstance(x, float):
        return round(x, 6)
    if isinstance(x, dict):
        return {k: _r6(val) for k, val in x.items()}
    if isinstance(x, (list, tuple)):
        return [_r6(val) for val in x]
    return x


def write_interface(fp: dict, path: Path = OUT_YAML) -> Path:
    """Derived interface yaml (do not edit; regenerate with python -m engine.M1_inlet_fan.geometry.flowpath)."""
    data = {
        "description": f"DERIVED, do not edit: generated by engine/M1_inlet_fan/geometry/flowpath.py from M1 record "
                       f"{fp['revision']} and geometry_params.yaml. Frame: engine/M1_inlet_fan/geometry/frame.py "
                       "(x engine axis aft, origin at the fan rotor stacking plane), metres.",
        "revision": fp["revision"],
        "tags": {"radii": "H (record annulus and tubes)", "axial_positions": "H from T ratios (geometry_params.yaml)",
                 "tip_clearance": "T (record params losses.tip_clearance_running, open issue #16)"},
        "stations": fp["stations"],
        "interfaces": {
            "M2_station_21": {"x_m": fp["stations"]["21"]["x_m"], "r_hub_m": fp["stations"]["21"]["r_hub_m"],
                              "r_tip_m": fp["stations"]["21"]["r_tip_m"], "area_m2": fp["stations"]["21"]["area_m2"],
                              "note": "core annulus at the splitter lip plane; zero splitter thickness until step 5d"},
            "M7_station_13": {"x_m": fp["stations"]["13"]["x_m"], "r_inner_m": fp["stations"]["13"]["r_inner_m"],
                              "r_outer_m": fp["stations"]["13"]["r_outer_m"],
                              "area_m2": fp["stations"]["13"]["area_m2"],
                              "note": "bypass annulus at the OGV exit plane (placeholder until step 5e)"},
        },
        "rotor_edges_x_r_m": fp["rotor_edges"],
        "rotor_axial_chord_m": fp["axial_chord_m"],
        "splitter": {"r_split1_m": fp["stations"]["2"]["r_split_m"], "r_split2_m": fp["r_split2_m"],
                     "r_split2_initial_m_info": fp["r_split2_initial_m_info"], "x_lip_m": fp["stations"]["21"]["x_m"]},
        "x_ogv_le_m": fp["x_ogv_le_m"],
        "tip_clearance_m": fp["tip_clearance_m"],
        "curves_x_r_m": fp["curves"],
    }
    write_yaml(path, _r6(data))
    return path


def main() -> None:
    fp = build()
    path = write_interface(fp)
    for name, s in solids(fp).items():
        print(f"{name}: {fr.export_step(s, name, fp['revision'])}")
    for k, st in fp["stations"].items():
        print(k, {a: round(b, 5) for a, b in st.items()})
    print(f"r_split2 {fp['r_split2_m']:.5f} m, tip clearance {fp['tip_clearance_m'] * 1e3:.2f} mm; yaml: {path}")


if __name__ == "__main__":
    main()
