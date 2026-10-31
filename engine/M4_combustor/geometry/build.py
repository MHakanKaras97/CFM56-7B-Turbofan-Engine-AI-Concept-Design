"""M4 combustor parts, BOM and STEP files (rules/design.md R-D4.1-5) from analysis/design.run.

Parts: M4.0.1 diffuser, M4.0.2 outer case, M4.0.3 inner case, M4.0.4 outer liner, M4.0.5 inner liner, M4.0.6 dome,
M4.0.7 fuel injector (20 [KS]). STEP: .cache/geometry/M4_combustor/<revision>/.

Run: python -m engine.M4_combustor.geometry.build
"""

import math

import cadquery as cq

from engine.M4_combustor.analysis import design as D
from tools import concept as C

REVISION = "rev001"
SCRIPT = "engine/M4_combustor/geometry/build.py"
NAME = "Combustor"


def injector_layout(res: dict) -> dict:
    prm, L, cs = res["params"], res["liner"], res["casing"]
    inj = C.v(prm["injector"])
    H = L["height"]
    r_l = C.v(prm["liner_mean_radius"])
    r_sw = C.v(prm["swirler_radius_over_height"]) * H
    x_stem = L["x_dome"] - 0.5 * (L["x_dome"] - res["prediffuser"]["x1"])
    return {"x_stem": x_stem, "r_l": r_l, "r_sw": r_sw, "stem_r": inj["stem_radius"],
            "tip_r": inj["tip_radius_over_swirler"] * r_sw, "tip_x1": L["x_dome"] + C.v(prm["dome_thickness"])
            + 0.25 * inj["tip_length"], "r_top": cs["r_out"] + C.v(prm["case_thickness"]) + inj["pad_height"]}


def build(res: dict | None = None) -> C.Module:
    res = res or D.run()
    prm = res["params"]
    mat = C.v(prm["materials"])
    mod = C.Module("M4", NAME, REVISION)
    s3, pd, cs, L, s4 = res["station_3"], res["prediffuser"], res["casing"], res["liner"], res["station_4"]
    tw, t, tl, td = (C.v(prm[k]) for k in ("diffuser_wall_thickness", "case_thickness", "liner_thickness",
                                            "dome_thickness"))

    outer_w = C.shell([(s3["x"], s3["r_tip"]), (pd["x1"], pd["r_tip1"])], tw, True)
    inner_w = C.shell([(s3["x"], s3["r_hub"]), (pd["x1"], pd["r_hub1"])], tw, False)
    mod.add(C.Part("M4.0.1", "Combustor Diffuser", cq.Compound.makeCompound([outer_w, inner_w]), mat["diffuser"],
                   "Prediffuser from station 3 to the dump region; turns the flow out to the liner radius (R-D4.1)",
                   process="machined casting", notes="Diffuser struts not modelled; walls in one part entry."))

    il = injector_layout(res)
    outer_case = C.revolve([(s3["x"], s3["r_tip"] + tw), (pd["x1"], cs["r_out"]), (s4["x"], cs["r_out"]),
                            (s4["x"], cs["r_out"] + t), (pd["x1"], cs["r_out"] + t), (s3["x"], s3["r_tip"] + tw + t)])
    n = int(C.v(prm["injectors"]))
    for i in range(n):
        hole = C.rotate_x(cq.Solid.makeCylinder(il["stem_r"] + 0.001, 0.2, cq.Vector(il["x_stem"], 0, cs["r_out"] - 0.05),
                                                cq.Vector(0, 0, 1)), 360.0 * i / n)
        outer_case = outer_case.cut(hole)
    mod.add(C.Part("M4.0.2", "Combustor Outer Case", outer_case.clean(), mat["case"],
                   "Pressure vessel around the combustor from the HPC rear case to the HPT case; injector bosses",
                   process="machined forging", joints=[("M3.0.4", "bolted_flange")],
                   notes=f"{n} injector holes cut (R-D4.5)."))
    def r_wall_bottom(x):  # underside of the sloped diffuser inner wall
        return C.lerp(s3["r_hub"], pd["r_hub1"], (x - s3["x"]) / (pd["x1"] - s3["x"])) - tw
    inner_case = C.revolve([(pd["x1"] - t, r_wall_bottom(pd["x1"] - t)), (pd["x1"], r_wall_bottom(pd["x1"])),
                            (pd["x1"], cs["r_in"] + t),
                            (s4["x"], cs["r_in"] + t), (s4["x"], cs["r_in"]), (pd["x1"] - t, cs["r_in"])])
    mod.add(C.Part("M4.0.3", "Combustor Inner Case", inner_case, mat["case"],
                   "Inner pressure wall under the liner; carries the diffuser inner wall and the NGV inner support",
                   process="machined forging"))

    outer_l = C.shell([(L["x_dome"], L["r_out"]), (L["x_straight_end"], L["r_out"]), (s4["x"], s4["r_tip"])], tl, True)
    inner_l = C.shell([(L["x_dome"], L["r_in"]), (L["x_straight_end"], L["r_in"]), (s4["x"], s4["r_hub"])], tl, False)
    mod.add(C.Part("M4.0.4", "Combustor Outer Liner", outer_l, mat["liner"],
                   "Outer flame tube wall, converging to the station 4 tip radius (R-D4.3)", process="sheet, laser drilled",
                   notes="Dilution and cooling holes not modelled."))
    mod.add(C.Part("M4.0.5", "Combustor Inner Liner", inner_l, mat["liner"],
                   "Inner flame tube wall, converging to the station 4 hub radius (R-D4.3)", process="sheet, laser drilled",
                   notes="Dilution and cooling holes not modelled."))

    dome = C.ring(L["x_dome"], L["x_dome"] + td, L["r_in"], L["r_out"])
    for i in range(n):
        dome = dome.cut(C.rotate_x(C.cylinder_x(L["x_dome"] - 0.01, L["x_dome"] + td + 0.01, il["r_sw"], 0, il["r_l"]),
                                   360.0 * i / n))
    mod.add(C.Part("M4.0.6", "Combustor Dome", dome.clean(), mat["dome"],
                   "Annular dome bulkhead with one swirler opening per injector (R-D4.5)", process="sheet",
                   joints=[("M4.0.4", "weld"), ("M4.0.5", "weld")], notes="Swirlers and heat shields not modelled."))

    stem = cq.Solid.makeCylinder(il["stem_r"], il["r_top"] - il["r_l"], cq.Vector(il["x_stem"], 0, il["r_l"]),
                                 cq.Vector(0, 0, 1))
    tip = C.cylinder_x(il["x_stem"], il["tip_x1"], il["tip_r"], 0, il["r_l"])
    mod.add(C.Part("M4.0.7", "Combustor Fuel Injector", stem.fuse(tip).clean(), mat["injector"],
                   "Twin-tip fuel injector: stem through the outer case, tip in the dome swirler (R-D4.5)",
                   count=n, count_tag="KS", process="machined, brazed", joints=[("M4.0.2", "bolted_flange")],
                   notes="Count [KS] (#52 manual text). Fuel manifold out of scope (architecture.md)."))
    return mod


def main() -> None:
    from core.util import write_yaml
    res = D.run()
    write_yaml(D.OUT_FILE, D.to_yaml(res))
    C.write_interface("M4", D.interface(res))
    mod = build(res)
    warn = mod.write_bom(SCRIPT)
    paths = mod.export()
    print("M4 mass", round(mod.mass(), 2), "kg; parts", len(mod.parts), "; warnings", len(warn), ";", paths["assembly"])


if __name__ == "__main__":
    main()
