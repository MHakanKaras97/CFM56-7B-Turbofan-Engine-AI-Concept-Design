"""M8 shaft and bearing parts, BOM and STEP files (rules/design.md R-D8.1-5) from analysis/design.run.

Parts: M8.0.1 fan shaft, M8.0.2 LP shaft, M8.n.1 bearing No. n (n = 1-5), M8.1.2 forward bearing support (#1/#2),
M8.3.2 No. 3 bearing support, M8.5.2 No. 5 bearing support. STEP: .cache/geometry/M8_shaft_bearing/<revision>/.

Run: python -m engine.M8_shaft_bearing.geometry.build
"""

from engine.M8_shaft_bearing.analysis import design as D
from tools import concept as C

REVISION = "rev001"
SCRIPT = "engine/M8_shaft_bearing/geometry/build.py"
NAME = "Shaft and Bearing"

BEARINGS = {1: ("No. 1 Ball Bearing", "Fan thrust bearing on the fan shaft (forward sump)", "M8.0.1"),
            2: ("No. 2 Roller Bearing", "Fan shaft radial bearing (forward sump)", "M8.0.1"),
            3: ("No. 3 Ball Bearing", "HP rotor thrust bearing on the HPC forward shaft journal", "M3.0.5"),
            4: ("No. 4 Roller Bearing", "Intershaft bearing: HPT rear shaft on the LP shaft", "M8.0.2"),
            5: ("No. 5 Roller Bearing", "LPT shaft aft radial bearing under the turbine rear frame", "M6.0.1")}


def build(res: dict | None = None) -> C.Module:
    res = res or D.run()
    prm = res["params"]
    mat = C.v(prm["materials"])
    t_h = C.v(prm["housing_thickness"])
    mod = C.Module("M8", NAME, REVISION)
    fs, lp = res["fan_shaft"], res["lp_shaft"]
    f_in, f_out, f_len = fs["flange"]
    fan = C.ring(fs["x0"], fs["x1"], fs["r_in"], fs["r_out"]).fuse(C.ring(fs["x0"], fs["x0"] + f_len, fs["r_out"], f_out))
    mod.add(C.Part("M8.0.1", "Fan Shaft", fan.clean(), mat["fan_shaft"],
                   "Torque path LP shaft -> fan disk; carries bearings #1 and #2 (R-D8.2)", process="forging",
                   joints=[("M1.1.2", "bolted_flange"), ("M8.0.2", "spline")],
                   notes=f"LLP 30,000 EFC [KS]. Torsion margin {res['torsion']['fan_shaft']['margin']:.3f} [H] (R-D8.3)."))
    mod.add(C.Part("M8.0.2", "LP Shaft", C.ring(lp["x0"], lp["x1"], lp["r_in"], lp["r_out"]), mat["lp_shaft"],
                   "Torque path LPT shaft (M6) -> fan shaft; inner race of the intershaft bearing #4 (R-D8.3)",
                   process="forging", joints=[("M6.0.1", "spline")],
                   notes=f"Torsion margin {res['torsion']['lp_shaft']['margin']:.3f} [H] (R-D8.3, target 1.0)."))
    for n, (name, func, journal) in BEARINGS.items():
        b = res["bearings"][n]
        mod.add(C.Part(f"M8.{n}.1", name, C.ring(b["x0"], b["x1"], b["r_in"], b["r_out"]), mat["bearing"], func,
                       process="through-hardened bearing steel", joints=[(journal, "shrink_fit")],
                       notes="Envelope ring (R-D8.4); rolling elements, cage and races not modelled."))
    mod.add(C.Part("M8.1.2", "Forward Bearing Support", C.shell(res["fwd_support_curve"], t_h, False), mat["support_fwd"],
                   "Cone from the M1 fan frame flange to the #2 and #1 bearing housings (forward sump, R-D8.5)",
                   process="machined forging", joints=[("M1.4.1", "bolted_flange")],
                   notes="Sump wall, seals and oil jets not modelled."))
    mod.add(C.Part("M8.3.2", "No. 3 Bearing Support", C.revolve(res["support_3"]), mat["support_fwd"],
                   "Housing of bearing #3 hung from the aft face of the M1 fan frame flange (R-D8.5)",
                   process="machined forging", joints=[("M1.4.1", "bolted_flange")]))
    s5 = res["support_5"]
    sup5 = C.revolve(s5["cone"]).fuse(C.ring(*s5["housing"])).clean()
    mod.add(C.Part("M8.5.2", "No. 5 Bearing Support", sup5, mat["support_aft"],
                   "Housing of bearing #5 hung from the M7 turbine rear frame hub (aft sump, R-D8.5)",
                   process="machined forging", joints=[("M7.0.4", "bolted_flange")]))
    return mod


def main() -> None:
    from core.util import write_yaml
    res = D.run()
    write_yaml(D.OUT_FILE, D.to_yaml(res))
    C.write_interface("M8", D.interface(res))
    mod = build(res)
    warn = mod.write_bom(SCRIPT)
    paths = mod.export()
    print("M8 mass", round(mod.mass(), 2), "kg; parts", len(mod.parts), "; warnings", len(warn), ";", paths["assembly"])


if __name__ == "__main__":
    main()
