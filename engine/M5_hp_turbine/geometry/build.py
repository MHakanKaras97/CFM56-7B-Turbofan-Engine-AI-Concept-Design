"""M5 HP turbine parts, BOM and STEP files (rules/design.md R-D5.5) from analysis/design.run.

Parts: M5.0.1 front shaft, M5.0.2 rear shaft, M5.0.3 front air seal, M5.0.4 case, M5.1.1 rotor blade (80 [KS]),
M5.1.2 NGV, M5.1.3 disk, M5.1.4 shroud, M5.1.5 NGV bands. STEP: .cache/geometry/M5_hp_turbine/<revision>/.

Run: python -m engine.M5_hp_turbine.geometry.build
"""

import cadquery as cq

from engine.M5_hp_turbine.analysis import design as D
from tools import concept as C

REVISION = "rev001"
SCRIPT = "engine/M5_hp_turbine/geometry/build.py"
NAME = "HP Turbine"


def build(res: dict | None = None) -> C.Module:
    res = res or D.run()
    prm = res["params"]
    mat = C.v(prm["materials"])
    mod = C.Module("M5", NAME, REVISION)
    ngv, rot, dk = res["ngv"], res["rotor"], res["disk"]
    fs, rs, sp = res["front_shaft"], res["rear_shaft"], res["seal_plate"]
    t_case, t_band, t_sh = (C.v(prm[k]) for k in ("case_thickness", "band_thickness", "shroud_thickness"))
    clear = C.v(prm["tip_clearance"])
    m4 = res["m4"]
    x4 = res["station_4"]["x"]
    r_co = float(m4["M5_outer_case_flange"]["r_in_m"])
    r_ci = float(m4["M5_inner_case_flange"]["r_m"])
    x_case = D.case_aft_x(res)

    t = fs["t"]
    mod.add(C.Part("M5.0.1", "HPT Front Shaft",
                   C.revolve([(fs["x0"], fs["r0"]), (fs["x1"], fs["r1"]), (fs["x1"], fs["r1"] + t), (fs["x0"], fs["r0"] + t)]),
                   mat["shaft"], "Torque path HPT disk -> HPC (bolted to the M3 CDP seal flange)", process="forging",
                   joints=[("M3.0.8", "bolted_flange"), ("M5.1.3", "bolted_flange")], notes="LLP 17,300 EFC [KS]."))
    mod.add(C.Part("M5.0.2", "HPT Rear Shaft",
                   C.revolve([(rs["x0"], rs["r0"]), (rs["x0"], rs["r0"] + rs["t"]), (rs["x1"], rs["r1"] + rs["t"]),
                              (rs["x2"], rs["r1"] + rs["t"]), (rs["x2"], rs["r1"]), (rs["x1"], rs["r1"])]),
                   mat["shaft"], "Carries the HP rotor aft end on the intershaft bearing #4 (M8)", process="forging",
                   joints=[("M5.1.3", "bolted_flange")], notes="LLP 20,000 EFC [KS]."))
    mod.add(C.Part("M5.0.3", "HPT Front Air Seal", C.ring(sp["x0"], sp["x1"], sp["r_in"], sp["r_out"]), mat["disk"],
                   "Rotating seal plate ahead of the disk rim; meters blade cooling air (not modelled)", process="forging",
                   joints=[("M5.1.3", "bolted_flange")], notes="LLP 17,300 EFC [KS]. Seal teeth not modelled."))
    mod.add(C.Part("M5.0.4", "HPT Case", C.ring(x4, x_case, r_co, r_co + t_case), mat["case"],
                   "Outer casing from the combustor outer case to the LPT; carries the shroud and the NGV outer web",
                   process="machined ring forging", joints=[("M4.0.2", "bolted_flange")]))

    def blade(row, tip_clear=0.0):
        s = row["sections"]
        return C.blade(row["x_le"], s[0]["r"], s[-1]["r"] - tip_clear, s)

    mod.add(C.Part("M5.1.1", "HPT Stage 1 Rotor Blade", blade(rot, clear), mat["blade"],
                   "Extract work for the HP spool (single-stage HPT rotor)", count=rot["count"], count_tag="KS",
                   process="single-crystal casting", joints=[("M5.1.3", "fir_tree")],
                   notes="Count [KS] (#52 p. 159); fir-tree root, platform and cooling passages not modelled."))
    mod.add(C.Part("M5.1.2", "HPT Stage 1 Nozzle Guide Vane", blade(ngv), mat["ngv"],
                   "Accelerate and turn the station 4 flow onto the rotor", count=ngv["count"], count_tag="T",
                   process="single-crystal casting", notes="Count [T] (R-KV5.1 solidity rule); cooling not modelled."))
    mod.add(C.Part("M5.1.3", "HPT Stage 1 Disk",
                   C.disk(dk["x_mid"], dk["r_bore_in"], dk["r_bore_out"], dk["w_bore"], dk["t_web"], dk["r_rim_in"],
                          dk["r_rim_out"], dk["w_rim"]), mat["disk"], "Carries the HPT rotor blades",
                   process="powder metal forging", notes="LLP 19,200 EFC [KS] (ISSUE39 20,000 doğrulanamadı)."))
    r_tip_b = rot["sections"][-1]["r"]
    x_s0 = rot["x_le"] - 0.5 * (rot["x_le"] - ngv["x_te"])
    shroud = C.ring(x_s0, x_case, r_tip_b, r_tip_b + t_sh).fuse(
        C.ring(x_case - t_sh, x_case, r_tip_b + t_sh, r_co)).clean()
    mod.add(C.Part("M5.1.4", "HPT Stage 1 Shroud", shroud, mat["shroud"],
                   "Stationary ring over the rotor tips (tip clearance), hung from the HPT case", process="casting",
                   joints=[("M5.0.4", "bolted_flange")], notes="Segments and clearance control not modelled."))
    r_root, r_tip = ngv["sections"][0]["r"], ngv["sections"][-1]["r"]
    inner = C.ring(x4, ngv["x_te"], r_root - t_band, r_root).fuse(C.ring(x4, x4 + t_band, r_ci, r_root - t_band)).clean()
    outer = C.ring(x4, ngv["x_te"], r_tip, r_tip + t_band).fuse(C.ring(x4, x4 + t_band, r_tip + t_band, r_co)).clean()
    mod.add(C.Part("M5.1.5", "HPT Stage 1 NGV Band", cq.Compound.makeCompound([inner, outer]), mat["band"],
                   "Inner and outer NGV platforms with the radial supports to the M4 inner case and the HPT case",
                   process="casting", joints=[("M4.0.3", "bolted_flange"), ("M5.0.4", "bolted_flange")],
                   notes="Inner and outer bands in one part entry."))
    return mod


def main() -> None:
    from core.util import write_yaml
    res = D.run()
    write_yaml(D.OUT_FILE, D.to_yaml(res))
    C.write_interface("M5", D.interface(res))
    mod = build(res)
    warn = mod.write_bom(SCRIPT)
    paths = mod.export()
    print("M5 mass", round(mod.mass(), 2), "kg; parts", len(mod.parts), "; warnings", len(warn), ";", paths["assembly"])


if __name__ == "__main__":
    main()
