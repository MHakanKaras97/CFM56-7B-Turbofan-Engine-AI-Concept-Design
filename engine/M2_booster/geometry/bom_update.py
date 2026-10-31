"""M2 bom.yaml from the step 4 assembly (rules/geometry.md R-G2.24, rules/bom.md). Nothing is written unless
apply(write=True); the data is validated with core.bom.check_data and written only through core.bom.write.

One entry per part id of assembly.build (one definition + qty, owner M2, parent null): drum M2.0.1, case M2.0.2,
rotor blades M2.n.1 (airfoil + root block), stator vanes M2.n.2 (vane + foot), inner shrouds M2.n.4. Unit mass [H]
from the solids (assembly.mass_table); tbd materials with the Ti-6Al-4V density placeholder (#71). Abradable liners
M2.n.3 and the joint set M2.0.3 have no geometry and are not BOM entries (rules/bom.md, step 4 amendment).
proposed() is idempotent: it rebuilds the whole part list from the geometry.

Usage (M0 / M2): from engine.M2_booster.geometry import bom_update as b; data, rep = b.apply()  # dry run
                 b.apply(write=True)
"""

from pathlib import Path

from core import bom as core_bom
from engine.M2_booster.geometry import assembly as A
from engine.M2_booster.geometry import layout as L

BOM = L.M2_DIR / "bom" / "bom.yaml"
FUNCTIONS = {
    1: "Add work to the core flow (stage {n} rotor row)",
    2: "Remove the swirl of the stage {n} rotor and carry the outer flow path at the vane tips (stage {n} stator row)",
    4: "Inner flow-path wall under the stage {n} stator vanes; seal land facing the drum seal teeth",
}
COMMON = {
    "M2.0.1": ("Booster rotor spool: carries the rotor blades, the hub flow-path wall and the interstage seal teeth; "
               "bolted to the fan disk aft face and driven through it (J2-1)"),
    "M2.0.2": "Core/bypass divider wall from station 21 to station 24; outer flow-path wall; carries the stator vanes",
}
QTY_TAG = {1: "KS", 2: "T", 4: "G", 0: "G"}  # rotor counts known_values.md [KS]; stator rule R-KV2.1 [T]
QTY_NOTE = {1: "Count {q} [KS] (known_values.md, #52).", 2: "Count {q} [T] (R-KV2.1 proportional rule, #65)."}
JOINTS = {"M2.0.1": [{"to": "M1.1.2", "type": "bolted_flange"}], 1: [{"to": "M2.0.1", "type": "dovetail"}],
          2: [{"to": "M2.0.2", "type": "other"}], 4: [{"to": "M2.{n}.2", "type": "other"}]}
FAILURE_MODES = {"M2.0.1": ["FM2-4"], "M2.0.2": ["FM2-3"], 1: ["FM2-1", "FM2-2", "FM2-3", "FM2-5"], 2: ["FM2-2", "FM2-5"]}
ANALYSES = {"M2.0.1": ["A-4"], 1: ["A-1", "A-3", "A-4"], 2: ["A-3"]}
EXTRA = {
    "M2.0.1": ("One solid with the forward cone (R-G2.18), the hub flow-path wall (R-G2.20), the stage 1 flange and the "
               "seal teeth (R-G2.11); straight slots along the slot axis (R-G2.19). Booster spool LLP 23,600 EFC, "
               "22,900 EFC for -7B27 (Owner's Guide mtce s. 19-20) [KS], conflict open (#49). Bolts and bolt holes "
               "not modelled (J2-1, #76)."),
    "M2.0.2": ("Revolved shell station 21 -> 24 with one vane groove per stator row (R-G2.12); ends at station 24, "
               "where M1.4.6 (M1) continues the divider wall (R-G2.23). Abradable liners M2.n.3 not modelled (R-G2.12)."),
    1: "Root block in a straight axial slot (R-G2.19); R1 inserted from aft against the hub wall (R-G2.21); retention not modelled (#82).",
    2: "Vane foot in the casing groove (R-G2.12); inner end on the M2.{n}.4 shroud, no attachment modelled (J2-3).",
    4: "Full ring at concept level (R-G2.11), seal land underneath.",
}


def _kind(pid: str):
    stage, k = (int(x) for x in pid.split(".")[1:])
    return (pid if stage == 0 else k), stage


def _material_note(p: dict) -> str:
    if p["material"] == "tbd":
        return (f"Material tbd (rules/materials.md); mass with the {p['rho_material']} density placeholder [T] "
                f"(#71).")
    return f"Material {p['material']} [T] (rules/materials.md, analogy with the M1 fan blade)."


def proposed(asm: dict | None = None) -> dict:
    """BOM data rebuilt from the assembly (not written)."""
    asm = asm or A.build()
    masses = A.mass_table(asm)["parts"]
    parts = []
    for pid, p in asm["parts"].items():
        key, n = _kind(pid)
        m = masses[pid]
        notes = [QTY_NOTE.get(key, "").format(q=p["qty"])]
        sub = " + ".join(f"{k} {v:.4f} kg" for k, v in m["sub_kg"].items())
        notes.append(f"Unit mass {m['unit_kg']:.4f} kg [H] = solid volume x density ({sub}); information only "
                     f"(A-5, check value Lolis about 171 kg [KS weak]).")
        notes.append(_material_note(p))
        notes.append(EXTRA[key].format(n=n))
        entry = {"id": pid, "name": p["name"], "parent": None,
                 "qty": {"value": p["qty"], "unit": "ea", "tag": QTY_TAG[0 if n == 0 else key]},
                 "function": COMMON[pid] if n == 0 else FUNCTIONS[key].format(n=n),
                 "material": p["material"], "status": "draft",
                 "mass": {"value": round(m["unit_kg"], 4), "unit": "kg", "tag": "H"},
                 "geometry": {"script": p["script"], "params": {"revision": A.INPUT_REVISION}},
                 "notes": " ".join(x for x in notes if x)}
        for field, table in (("joints", JOINTS), ("failure_modes", FAILURE_MODES), ("analyses", ANALYSES)):
            if key in table:
                entry[field] = [{"to": j["to"].format(n=n), "type": j["type"]} if isinstance(j, dict) else j
                                for j in table[key]]
        parts.append(entry)
    data = core_bom.load(BOM)
    return {"module_id": "M2", "module_name": data["module_name"], "revision": data["revision"], "parts": parts}


def apply(write: bool = False, path: Path = BOM) -> tuple[dict, object]:
    """Validate the proposed BOM; write it via core.bom.write only if write=True and there are no errors."""
    data = proposed()
    report = core_bom.check_data(data)
    if write:
        if report.errors:
            raise ValueError(f"proposed BOM has errors: {report.errors}")
        core_bom.write(path, data)
    return data, report


if __name__ == "__main__":
    d, rep = apply(write=False)
    print(core_bom.dump(d))
    print("errors", rep.errors, "warnings", rep.warnings)
