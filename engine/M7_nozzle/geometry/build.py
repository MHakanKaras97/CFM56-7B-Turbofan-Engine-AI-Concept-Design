"""M7 nozzle parts, BOM and STEP files (rules/design.md R-D7.1-4) from analysis/design.run.

Parts: M7.0.1 bypass duct outer wall, M7.0.2 bypass duct inner wall, M7.0.3 fan nozzle, M7.0.4 turbine rear frame
hub, M7.0.5 turbine rear frame case, M7.0.6 turbine rear frame strut, M7.0.7 core nozzle sleeve, M7.0.8 exhaust plug.
STEP: .cache/geometry/M7_nozzle/<revision>/.

Run: python -m engine.M7_nozzle.geometry.build
"""

from engine.M7_nozzle.analysis import design as D
from tools import concept as C

REVISION = "rev001"
SCRIPT = "engine/M7_nozzle/geometry/build.py"
NAME = "Nozzle"


def build(res: dict | None = None) -> C.Module:
    res = res or D.run()
    prm = res["params"]
    mat = C.v(prm["materials"])
    mod = C.Module("M7", NAME, REVISION)
    b, trf, nz, m1 = res["bypass"], res["trf"], res["nozzle"], res["m1"]
    t_o, t_i, t_f, t_n = (C.v(prm[k]) for k in ("outer_wall_thickness", "inner_wall_thickness", "trf_wall_thickness",
                                                 "nozzle_wall_thickness"))

    outer = b["outer"]
    mod.add(C.Part("M7.0.1", "Bypass Duct Outer Wall", C.shell(outer[:2], t_o), mat["bypass_duct"],
                   "Outer bypass flow-path wall from the M1 fan frame outer ring to the fan nozzle (R-D7.1)",
                   process="composite layup", joints=[("M7.0.3", "bolted_flange")],
                   notes="Thrust reverser and nacelle out of scope (architecture.md)."))
    mod.add(C.Part("M7.0.2", "Bypass Duct Inner Wall", C.shell(b["inner"], t_i, False), mat["bypass_duct"],
                   "Inner bypass flow-path wall (core fairing) from the M1 wall ring M1.4.6 to the fan nozzle exit plane",
                   process="composite layup", notes="Access panels and core compartment ventilation not modelled."))
    mod.add(C.Part("M7.0.3", "Fan Nozzle", C.shell(outer[1:], t_o), mat["fan_nozzle"],
                   "Convergent fan nozzle; exit annulus area = A18 of the ICD (R-D7.2)", process="machined forging"))

    mod.add(C.Part("M7.0.4", "Turbine Rear Frame Hub", C.ring(trf["x0"], trf["x1"], trf["r_hub"] - t_f, trf["r_hub"]),
                   mat["trf"], "Inner flow-path ring of the TRF; carries the bearing #5 support (M8)", process="casting",
                   joints=[("M7.0.6", "weld")]))
    mod.add(C.Part("M7.0.5", "Turbine Rear Frame Case", C.ring(trf["x0"], trf["x1"], trf["r_tip"], trf["r_tip"] + t_f),
                   mat["trf"], "Outer ring of the TRF; rear engine mount plane", process="casting",
                   joints=[("M6.0.3", "bolted_flange"), ("M7.0.6", "weld")], notes="Mount lugs not modelled."))
    L = trf["x1"] - trf["x0"]
    secs = [{"f": f, "c": trf["chord"], "k1": -trf["swirl_in"], "k2": 0.0, "tc": C.v(prm["trf_strut_tc"])}
            for f in (0.0, 1.0)]
    strut = C.blade(trf["x0"] + 0.5 * (L - trf["chord"]), trf["r_hub"], trf["r_tip"], secs)
    mod.add(C.Part("M7.0.6", "Turbine Rear Frame Strut", strut, mat["trf"],
                   "Radial strut hub -> case; turns the LPT exit swirl to axial (R-D7.3); oil lines to bearing #5 inside",
                   count=trf["n_struts"], count_tag="T", process="casting"))

    mod.add(C.Part("M7.0.7", "Core Nozzle Sleeve", C.shell([(nz["x6"], trf["r_tip"]), (nz["x8"], nz["r_sleeve8"])], t_n),
                   mat["nozzle"], "Outer wall of the convergent core nozzle; exit area A8 with the plug (R-D7.4)",
                   process="sheet", joints=[("M7.0.5", "bolted_flange")]))
    plug = C.revolve([(nz["x6"], trf["r_hub"]), (nz["x8"], nz["r_plug8"]), (nz["x_tip"], 0.0),
                      (nz["x_tip"] - 4 * t_n, 0.0), (nz["x8"], nz["r_plug8"] - t_n), (nz["x6"], trf["r_hub"] - t_n)])
    mod.add(C.Part("M7.0.8", "Exhaust Plug", plug, mat["nozzle"], "Centre body of the core nozzle (R-D7.4)",
                   process="sheet", joints=[("M7.0.4", "bolted_flange")]))
    return mod


def main() -> None:
    from core.util import write_yaml
    res = D.run()
    write_yaml(D.OUT_FILE, D.to_yaml(res))
    C.write_interface("M7", D.interface(res))
    mod = build(res)
    warn = mod.write_bom(SCRIPT)
    paths = mod.export()
    print("M7 mass", round(mod.mass(), 2), "kg; parts", len(mod.parts), "; warnings", len(warn), ";", paths["assembly"])


if __name__ == "__main__":
    main()
