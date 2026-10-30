"""M0 impact analysis of the two M1 change requests from open issue #77 (M2 learning note geometri_celiskileri.md).

Read-only: imports the M1 rev014 and M2 rev001 geometry code, builds modified M1 solids only inside this script,
writes no file and changes no parameter. Every value is [H] from the [T] geometry rules of both modules and the
active records; the ICD station 13 state (Tt, Pt, W) is [H] from the active M0 revision.

CR-A: divider wall. M1.4.3 (splitter ring) removed, the wall is M2.0.2 (M2 casing) from station 21 aft; OGV root
(M1.3.1) and bypass strut root (M1.4.4) raised to r_split2 + M2 casing thickness.
CR-B: core-side frame (hub ring M1.4.1 with the M8 bearing flange, core struts M1.4.5) moved aft so that the frame
starts at station 24 (M2 casing end); core passage radii = M2 station 24/25 annulus; a frame-zone core/bypass wall
ring (station 24 to the new frame end) replaces the removed splitter there. Evaluated on top of CR-A option (a).

Run: .venv/Scripts/python -m engine.M0_engine.analysis.cr_impact_77
"""

import math

from core.budgets import read_icd
from core.records import ROOT
from core.util import read_yaml
from engine.M1_inlet_fan.geometry import assembly as asm
from engine.M1_inlet_fan.geometry import fan_frame as ff
from engine.M1_inlet_fan.geometry import frame as fr
from engine.M1_inlet_fan.geometry import ogv as ogvm
from engine.M2_booster.analysis import conflicts_75_77 as cf
from engine.M2_booster.geometry import hardware as HW
from tools.meanline import Gas, mach_from_flux


def ring_area(ro: float, ri: float) -> float:
    return math.pi * (ro * ro - ri * ri)


def mach_13(area: float) -> float:
    """Station 13 Mach number for the ICD station 13 state and a given annulus area [H] (cold air [G])."""
    st = read_icd("M0 cr_impact_77")["stations"]["13"]
    gas = Gas()
    flux = st["W"]["value"] * math.sqrt(gas.R * st["Tt"]["value"]) / (area * st["Pt"]["value"] * 1e3)
    return mach_from_flux(flux, gas)


def m2_clash(solids: dict, hb: dict) -> float:
    """Total common volume of the given M1 solids with the M2 parts and clocking-free row bands (m3, instance 0)."""
    m2 = [s for _, s, _ in cf.m2_axisymmetric(hb)] + [s for _, s in cf.m2_row_bands(hb)]
    m2 += [s for n, _, s in HW.part_list(hb) if "airfoil" in n or "vane" in n or "root" in n or "foot" in n]
    total = 0.0
    for s1 in solids.values():
        for s2 in m2:
            c = cf.common(s2, s1)
            total += c["volume"] if c else 0.0
    return total


def budget_rows() -> dict:
    """M1 ICD budget check as recorded in the active M1 results (cycle items; geometry does not enter them)."""
    res = read_yaml(ROOT / "engine" / "M1_inlet_fan" / "analysis" / "results.yaml")
    rows = res["budget_check"]
    return {"passed": sum(r["result"] in ("pass", "info") for r in rows), "total": len(rows)}


def cr_a(m1: dict, hb: dict) -> dict:
    fp = m1["frame"]["flowpath"]
    L = m1["frame"]["layout"]
    rho = m1["frame_masses"]["bypass_strut"]["density"]
    r_s2 = fp["r_split2_m"]
    t_wall = hb["hw"]["casing_thickness"]
    r_new = r_s2 + t_wall
    r_tip2 = fp["stations"]["13"]["r_outer_m"]
    r_out_ogv = fr.r_at(fp["curves"]["casing_wall"], fp["x_ogv_le_m"])

    og0 = m1["ogv"]
    vane_kg0 = og0["vane"].Volume() * rho
    fp["r_split2_m"] = r_new  # cached flowpath dict, restored below
    try:
        og1 = ogvm.build.__wrapped__()
    finally:
        fp["r_split2_m"] = r_s2
    vane_kg1 = og1["vane"].Volume() * rho
    strut1 = ff.strut(L, r_new, L["r_wall"])
    strut_kg0 = m1["frame_masses"]["bypass_strut"]["mass_kg"]
    strut_kg1 = strut1.Volume() * rho
    split_kg = m1["frame_masses"]["splitter_ring"]["mass_kg"]
    V, n = og0["V"], L["n_struts"]
    d_mass = -split_kg + V * (vane_kg1 - vane_kg0) + n * (strut_kg1 - strut_kg0)
    # option (b): two walls, M1 splitter outside the M2 casing, splitter thickness by the M1 rule 0.02 r [T]
    t_b = fr.v(ff.frame_params()["splitter_thickness_over_split_radius"]) * r_new
    r_b = r_new + t_b
    a0, a1, ab = ring_area(r_tip2, r_s2), ring_area(r_tip2, r_new), ring_area(r_tip2, r_b)
    return {
        "r_split2": r_s2, "wall_t": t_wall, "r_root_new": r_new, "r_root_opt_b": r_b,
        "A13_before": a0, "A13_after": a1, "A13_opt_b": ab, "dA13_rel": a1 / a0 - 1,
        "M13_before": mach_13(a0), "M13_after": mach_13(a1), "M13_opt_b": mach_13(ab),
        "ogv_span_before": r_out_ogv - r_s2, "ogv_span_after": r_out_ogv - r_new, "ogv_span_opt_b": r_out_ogv - r_b,
        "ogv_vane_kg_before": vane_kg0, "ogv_vane_kg_after": vane_kg1,
        "bypass_strut_kg_before": strut_kg0, "bypass_strut_kg_after": strut_kg1,
        "splitter_kg": split_kg, "m1_mass_change": d_mass,
        "clash_before": m2_clash({"ogv": og0["vane"], "strut": m1["frame"]["parts"]["bypass_strut"]}, hb),
        "clash_after": m2_clash({"ogv": og1["vane"], "strut": strut1}, hb),
    }


def cr_b(m1: dict, hb: dict, a: dict, model: dict) -> dict:
    L0 = m1["frame"]["layout"]
    rho = m1["frame_masses"]["hub_ring"]["density"]
    x24 = hb["model"]["layout"]["x24"]
    shift = x24 - L0["x0"]
    strut_shift_min = x24 - L0["strut_x0"]
    st25 = read_yaml(ROOT / "engine" / "M2_booster" / "geometry" / "flowpath.yaml")["interfaces"]["M3_station_25"]
    r_hub, r_core_out = st25["r_hub_m"], st25["r_tip_m"]
    L1 = dict(L0, x0=L0["x0"] + shift, x1=L0["x1"] + shift, strut_x0=L0["strut_x0"] + shift, r_hub=r_hub,
              r_core_out=r_core_out)  # bearing flange inner radius kept (M8 boundary radius unchanged) [T]
    hub1 = ff.hub_ring(L1)
    core1 = ff.strut(L1, r_hub, r_core_out)
    wall = fr.revolve_closed([(x24, a["r_split2"]), (L1["x1"], a["r_split2"]), (L1["x1"], a["r_root_new"]),
                              (x24, a["r_root_new"])])
    n = L0["n_struts"]
    fm = m1["frame_masses"]
    old = fm["hub_ring"]["mass_kg"] + n * fm["core_strut"]["mass_kg"]
    new = (hub1.Volume() + n * core1.Volume() + wall.Volume()) * rho
    ext = asm.extent(model)
    fn = cf.frame_numbers(hb, m1)
    return {
        "m2_gap_ratio_to_strut_le": fn["gap_fraction_to_strut_le"], "m2_gap_ratio_to_frame_x0": fn["gap_fraction_to_frame_x0"],
        "m2_rows_width": fn["sum_widths"], "m2_rows_shortfall": fn["blading_shortfall_to_strut_le"],
        "x24": x24, "shift": shift, "strut_shift_min": strut_shift_min, "strut_le_new": L1["strut_x0"],
        "frame_x_new": (L1["x0"], L1["x1"]), "core_passage": (r_hub, r_core_out),
        "length_before": ext["length_m"], "length_after": L1["x1"] - ext["x_nose_m"],
        "x13": m1["frame"]["flowpath"]["stations"]["13"]["x_m"],
        "m8_face_before": (L0["x1"] - L0["t_bearing"], L0["x1"]), "m8_face_after": (L1["x1"] - L1["t_bearing"], L1["x1"]),
        "r_bearing": L0["r_bearing"], "hub_ring_kg_after": hub1.Volume() * rho, "core_strut_kg_after": core1.Volume() * rho,
        "wall_ring_kg": wall.Volume() * rho, "m1_mass_change": new - old,
        "clash_before": m2_clash({"hub": m1["frame"]["parts"]["hub_ring"], "core": m1["frame"]["parts"]["core_strut"]}, hb),
        "clash_after": m2_clash({"hub": hub1, "core": core1, "wall": wall}, hb),
    }


def run() -> dict:
    hb = HW.build()
    m1 = cf.m1_parts()
    model = asm.build()
    total = asm.mass_table(model)["total_kg"]
    a = cr_a(m1, hb)
    b = cr_b(m1, hb, a, model)
    return {"m1_total_kg": total, "A": a, "B": b, "budget": budget_rows()}


def main() -> None:
    out = run()
    print(f"M1 total {out['m1_total_kg']:.4f} kg; M1 budget rows {out['budget']}")
    for k in ("A", "B"):
        print(k)
        for key, v in out[k].items():
            print(f"  {key}: {tuple(round(x, 6) for x in v) if isinstance(v, tuple) else round(v, 6)}")


if __name__ == "__main__":
    main()
