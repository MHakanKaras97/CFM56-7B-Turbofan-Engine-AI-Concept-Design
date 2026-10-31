"""M6 LP turbine parts, BOM and STEP files (rules/design.md R-D6.4-6) from analysis/design.run.

Parts: M6.0.1 LPT shaft, M6.0.2 conical support, M6.0.3 case, M6.0.4 transition duct inner wall, M6.n.1 rotor blades
(162/150/150/134 [KS]), M6.n.2 NGVs, M6.n.3 disks (with the forward drum), M6.n.4 NGV inner shrouds.
STEP: .cache/geometry/M6_lp_turbine/<revision>/.

Run: python -m engine.M6_lp_turbine.geometry.build
"""

from engine.M6_lp_turbine.analysis import design as D
from tools import concept as C

REVISION = "rev001"
SCRIPT = "engine/M6_lp_turbine/geometry/build.py"
NAME = "LP Turbine"


def build(res: dict | None = None) -> C.Module:
    res = res or D.run()
    prm = res["params"]
    mat = C.v(prm["materials"])
    mod = C.Module("M6", NAME, REVISION)
    rows, disks, drums = res["rows"], res["disks"], res["drums"]
    t_case, t_duct, t_sh = (C.v(prm[k]) for k in ("case_thickness", "duct_wall_thickness", "shroud_thickness"))
    clear = C.v(prm["tip_clearance"])
    ds, sh, cn = res["duct_start"], res["shaft"], res["cone"]

    mod.add(C.Part("M6.0.1", "LPT Shaft", C.ring(sh["x0"], sh["x1"], sh["r_in"], sh["r_out"]), mat["shaft"],
                   "LPT torque to the M8 LP shaft (spline at the forward end); bearing #5 journal at the aft end",
                   process="forging", joints=[("M6.0.2", "bolted_flange")], notes="LLP 25,000 EFC [KS]."))
    t = cn["t"]
    mod.add(C.Part("M6.0.2", "LPT Conical Support",
                   C.revolve([(cn["x0"], cn["r0"] - t / 2), (cn["x0"], cn["r0"] + t / 2), (cn["x1"], cn["r1"] + t),
                              (cn["x1"], cn["r1"])]), mat["disk"],
                   "Cone from the stage 4 disk to the LPT shaft", process="forging",
                   joints=[("M6.4.3", "bolted_flange")], notes="LLP 16,300 EFC [KS] (ISSUE39 25,000 doğrulanamadı)."))
    tip = [(ds["x"], ds["r_tip"])]
    for r in rows:
        tip += [(r["x_le"], r["tip_le"]), (r["x_te"], r["tip_te"])]
    mod.add(C.Part("M6.0.3", "LPT Case", C.shell(tip, t_case), mat["case"],
                   "Outer flow-path wall from the HPT shroud through the transition duct and the 4 stages; carries the NGVs",
                   process="machined ring forging", joints=[("M5.0.4", "bolted_flange")]))
    mod.add(C.Part("M6.0.4", "LPT Transition Duct Inner Wall",
                   C.shell([(ds["x"], ds["r_hub"]), (rows[0]["x_le"], rows[0]["hub_le"])], t_duct, False), mat["shroud"],
                   "Inner wall of the inter-turbine duct 44 -> 45 (R-D6.4)", process="sheet",
                   notes="Support to the stage 1 NGV inner shroud not modelled."))

    drum_of = {i + 2: dr for i, dr in enumerate(drums)}  # drum ahead of disk n (forward arm)
    for r in rows:
        n = r["stage"]
        s = r["sections"]
        if r["kind"] == "rotor":
            mod.add(C.Part(f"M6.{n}.1", f"LPT Stage {n} Rotor Blade", C.blade(r["x_le"], s[0]["r"], s[-1]["r"] - clear, s),
                           mat["blade"], f"Extract work for the LP spool (stage {n} rotor)", count=r["count"],
                           count_tag="KS", process="casting", joints=[(f"M6.{n}.3", "dovetail")],
                           notes="Count [KS] (#52 p. 159); tip shroud and dovetail not modelled."))
            dk = disks[n - 1]
            solid = C.disk(dk["x_mid"], dk["r_bore_in"], dk["r_bore_out"], dk["w_bore"], dk["t_web"], dk["r_rim_in"],
                           dk["r_rim_out"], dk["w_rim"])
            if n in drum_of:
                dr = drum_of[n]
                solid = solid.fuse(C.ring(dr["x0"], dr["x1"], dr["r_in"], dr["r_out"])).clean()
            mod.add(C.Part(f"M6.{n}.3", f"LPT Stage {n} Disk", solid, mat["disk"],
                           f"Carries the stage {n} rotor blades" + ("; forward drum to the stage %d disk" % (n - 1) if n > 1 else ""),
                           process="forging", joints=[(f"M6.{n - 1}.3", "bolted_flange")] if n > 1 else [],
                           notes=("LLP 23,900 EFC [KS]." if n == 4 else "LLP 25,000 EFC [KS].")))
        else:
            mod.add(C.Part(f"M6.{n}.2", f"LPT Stage {n} Nozzle Guide Vane", C.blade(r["x_le"], s[0]["r"], s[-1]["r"], s),
                           mat["ngv"], f"Turn the flow onto the stage {n} rotor", count=r["count"], count_tag="T",
                           process="casting", notes="Count [T] (R-KV6.1 solidity rule)."))
            root = s[0]["r"]
            mod.add(C.Part(f"M6.{n}.4", f"LPT Stage {n} NGV Inner Shroud", C.ring(r["x_le"], r["x_te"], root - t_sh, root),
                           mat["shroud"], f"Inner flow-path platform of the stage {n} NGV; seal land over the drum",
                           process="casting", notes="Seal honeycomb not modelled."))
    return mod


def main() -> None:
    from core.util import write_yaml
    res = D.run()
    write_yaml(D.OUT_FILE, D.to_yaml(res))
    C.write_interface("M6", D.interface(res))
    mod = build(res)
    warn = mod.write_bom(SCRIPT)
    paths = mod.export()
    print("M6 mass", round(mod.mass(), 2), "kg; parts", len(mod.parts), "; warnings", len(warn), ";", paths["assembly"])


if __name__ == "__main__":
    main()
