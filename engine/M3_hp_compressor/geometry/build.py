"""M3 HP compressor parts, BOM and STEP files (rules/design.md R-D3.6) from analysis/design.run.

Parts: M3.0.1 inlet duct, M3.0.2 IGV, M3.0.3/4 front/rear case, M3.0.5 forward shaft, M3.0.6 stage 1-2 spool,
M3.0.7 stage 4-9 spool, M3.0.8 CDP seal, M3.3.3 stage 3 disk, M3.n.1 rotor blades, M3.n.2 stator vanes.
STEP: .cache/geometry/M3_hp_compressor/<revision>/ (one file per part + m3_assembly.step).

Run: python -m engine.M3_hp_compressor.geometry.build
"""

import math

import cadquery as cq

from engine.M3_hp_compressor.analysis import design as D
from tools import concept as C

REVISION = "rev001"
SCRIPT = "engine/M3_hp_compressor/geometry/build.py"
NAME = "HP Compressor"


def _mat(res: dict, key: str, stage: int) -> str:
    m = C.v(res["params"]["materials"])
    return m[f"{key}_front"] if stage <= 4 else m[f"{key}_rear"]


def _blade(row: dict, tip_clear: float = 0.0) -> cq.Solid:
    secs = row["sections"]
    r_hub, r_tip = secs[0]["r"], secs[-1]["r"] - tip_clear
    return C.blade(row["x_le"], r_hub, r_tip, secs)


def _s_curve(x0: float, r0: float, x1: float, r1: float, n: int = 12) -> list[tuple[float, float]]:
    return [(C.lerp(x0, x1, i / n), r0 + (r1 - r0) * 0.5 * (1 - math.cos(math.pi * i / n))) for i in range(n + 1)]


def build(res: dict | None = None) -> C.Module:
    res = res or D.run()
    prm = res["params"]
    mod = C.Module("M3", NAME, REVISION)
    hw = res["hardware"]
    rows, igv = res["rows"], res["igv"]
    t_case = C.v(prm["case_thickness"])
    t_duct = C.v(prm["duct_wall_thickness"])
    clear = C.v(prm["tip_clearance"])

    # inlet S-duct (station 25 -> IGV LE), outer wall outward, inner wall inward
    s25 = res["station_25"]
    outer = _s_curve(s25["x"], s25["r_tip"], igv["x_le"], igv["tip_le"])
    inner = _s_curve(s25["x"], s25["r_hub"], igv["x_le"], igv["hub_le"])
    duct = cq.Compound.makeCompound([C.shell(outer, t_duct, True), C.shell(inner, t_duct, False)])
    mod.add(C.Part("M3.0.1", "HP Compressor Inlet Duct", duct, C.v(prm["materials"])["duct"],
                   "S-duct from station 25 (M1 frame core passage) down to the HPC rotor 1 radius (R-D3.1)",
                   process="machined forging", notes="Outer and inner walls in one part entry."))

    mod.add(C.Part("M3.0.2", "HP Compressor Stage 0 Inlet Guide Vane", _blade(igv), C.v(prm["materials"])["stator_front"],
                   "Variable inlet guide vane: sets the rotor 1 inlet swirl (R-D3.4)", count=igv["count"],
                   count_tag="T", process="forging", notes="Variable pivot and actuation not modelled."))

    # case: tip line from the IGV LE to station 3, split after stage 4 stator
    tip = [(igv["x_le"], igv["tip_le"])]
    for r in rows:
        tip += [(r["x_le"], r["tip_le"]), (r["x_te"], r["tip_te"])]
    x_split = 0.5 * (rows[7]["x_te"] + rows[8]["x_le"])
    split_r = C.lerp(rows[7]["tip_te"], rows[8]["tip_le"], 0.5)
    front = [pt for pt in tip if pt[0] < x_split] + [(x_split, split_r)]
    rear = [(x_split, split_r)] + [pt for pt in tip if pt[0] > x_split]
    mod.add(C.Part("M3.0.3", "HP Compressor Front Case", C.shell(front, t_case), C.v(prm["materials"])["case"],
                   "Outer flow-path wall IGV to stage 4; carries the IGV and the variable stator vanes 1-3 [KS]",
                   process="machined ring forging"))
    mod.add(C.Part("M3.0.4", "HP Compressor Rear Case", C.shell(rear, t_case), C.v(prm["materials"])["case"],
                   "Outer flow-path wall stages 5-9; stage 5 bleed port (M9) and station 3 flange to M4",
                   process="machined ring forging", notes="Bleed port opening not modelled."))

    disks = {d["stage"]: C.disk(d["x_mid"], d["r_bore_in"], d["r_bore_out"], d["w_bore"], d["t_web"], d["r_rim_in"],
                                d["r_rim_out"], d["w_rim"]) for d in hw["disks"]}
    drums = {(dr["from"], dr["to"]): C.ring(dr["x0"], dr["x1"], dr["r_in"], dr["r_out"]) for dr in hw["drums"]}

    def fuse(shapes):
        out = shapes[0]
        for s in shapes[1:]:
            out = out.fuse(s)
        return out.clean()

    fw = hw["forward_shaft"]
    cone = C.revolve([(fw["x_disk"], fw["r_disk"]), (fw["x_disk"], fw["r_disk"] + fw["t"]),
                      (fw["x_journal_aft"], fw["r_journal"] + fw["t"]), (fw["x_journal_fwd"], fw["r_journal"] + fw["t"]),
                      (fw["x_journal_fwd"], fw["r_journal"]), (fw["x_journal_aft"], fw["r_journal"])])
    mod.add(C.Part("M3.0.5", "HP Compressor Forward Shaft", cone, _mat(res, "disk", 1),
                   "Carries the HP rotor forward end on bearing #3 (M8); torque path to the inlet gearbox (M9)",
                   process="forging", joints=[("M3.0.6", "bolted_flange")],
                   notes="LLP 20,000 EFC [KS] (rules/known_values.md)."))
    mod.add(C.Part("M3.0.6", "HP Compressor Stage 1-2 Spool", fuse([disks[1], disks[2], drums[(1, 2)], drums[(2, 3)]]),
                   _mat(res, "disk", 1), "Stage 1 and 2 disks with the interstage drum", process="forging",
                   joints=[("M3.3.3", "bolted_flange")], notes="LLP 20,000 EFC [KS]."))
    mod.add(C.Part("M3.3.3", "HP Compressor Stage 3 Disk", disks[3], _mat(res, "disk", 3), "Stage 3 disk",
                   process="forging", joints=[("M3.0.7", "bolted_flange")], notes="LLP 20,000 EFC [KS]."))
    rear_spool = fuse([disks[s] for s in range(4, 10)] + [drums[(s, s + 1)] for s in range(3, 9)])
    mod.add(C.Part("M3.0.7", "HP Compressor Stage 4-9 Spool", rear_spool, _mat(res, "disk", 9),
                   "Stage 4 to 9 disks with the interstage drums (welded spool [G])", process="forging, inertia welded",
                   joints=[("M3.0.8", "bolted_flange")], notes="LLP 20,000 EFC [KS]."))
    cs = hw["cdp_seal"]
    mod.add(C.Part("M3.0.8", "HP Compressor CDP Seal", C.ring(cs["x0"], cs["x1"], cs["r_in"], cs["r_in"] + cs["t"]),
                   _mat(res, "disk", 9), "Compressor discharge pressure seal; flange to the HPT front shaft (M5)",
                   process="forging", notes="Seal teeth not modelled. LLP 20,000 EFC [KS]."))

    for r in rows:
        n = r["stage"]
        if r["kind"] == "rotor":
            mod.add(C.Part(f"M3.{n}.1", f"HP Compressor Stage {n} Rotor Blade", _blade(r, clear), _mat(res, "rotor", n),
                           f"Add work to the core flow (stage {n} rotor row)", count=r["count"], count_tag="KS",
                           process="forging", joints=[(f"M3.0.6" if n <= 2 else ("M3.3.3" if n == 3 else "M3.0.7"),
                                                       "dovetail")],
                           notes="Count [KS] (#52 p. 159); dovetail root not modelled (blade on the rim)."))
        else:
            mod.add(C.Part(f"M3.{n}.2", f"HP Compressor Stage {n} Stator Vane", _blade(r), _mat(res, "stator", n),
                           (f"Stage {n} stator row" + (", variable [KS]" if n <= 3 else "")
                            + (", outlet guide vane (axial exit)" if n == 9 else "")),
                           count=r["count"], count_tag="T", process="forging",
                           notes="Count [T] (R-KV3.1 solidity rule); inner shroud and seal not modelled."))
    return mod


def main() -> None:
    from core.util import write_yaml
    res = D.run()
    write_yaml(D.OUT_FILE, D.to_yaml(res))
    C.write_interface("M3", D.interface(res))
    mod = build(res)
    warn = mod.write_bom(SCRIPT)
    paths = mod.export()
    print("M3 mass", round(mod.mass(), 2), "kg; parts", len(mod.parts), "; warnings", len(warn), ";",
          paths["assembly"])


if __name__ == "__main__":
    main()
