"""Proposed M1 bom.yaml update for step 5g (draft for M0 review; nothing is written unless apply(write=True)).

Changes: materials for the tbd parts (all [T], aluminium per rules/materials.md), unit mass from the assembly mass
table [H], geometry script per part, notes with tags and sources, and the parts missing from the BOM: M1.3 becomes
the OGV row assembly with M1.3.1 the vane (qty 51 [T]); M1.4 becomes the frame assembly with M1.4.1, M1.4.2,
M1.4.4-M1.4.6. CR-002 option a / CR-003 (rules/geometry.md R-G1): M1.4.3 splitter ring removed (divider wall = M2.0.2),
M1.4.6 core wall ring added (status draft as approved in CR-003); the CR note sentences of M1.3.1, M1.4.1, M1.4.4,
M1.4.5 and M1.4.6 are generated from the frame layout (numbers from code, CR_MARKS).
Status: "review" for the parts built at concept level in steps 5a-5i; the disk M1.1.2 and the rotor assembly M1.1
are "review" only if the disk bore (R-DISK.1) and every dovetail / lug mode (R-DISK.2) meet the margin rule, else
"draft" (computed from rotor_hardware.stress). Never "approved". The M1.1.1 / M1.1.2 geometry notes are generated
with the current numbers (replacing any earlier "Geometry step 5" sentence).
proposed() is idempotent: applied to its own output it returns the same data. The BOM is written only through core.bom.write and validated with core.bom.check_data first.

Usage (M0): from engine.M1_inlet_fan.geometry import bom_update as b; data, rep = b.apply()  # dry run
            b.apply(write=True)  # writes bom.yaml after review
"""

import copy
from pathlib import Path

from core import bom as core_bom
from engine.M1_inlet_fan.geometry import assembly as asm
from engine.M1_inlet_fan.geometry import frame as fr
from engine.M1_inlet_fan.geometry import rotor_hardware as rh

BOM = fr.HERE.parent / "bom" / "bom.yaml"
GEOMETRY_REVISION = "rev011"  # record whose params/results the geometry inputs were built from (fixed, not ACTIVE)
GEN_MARK = " Geometry step 5"  # generated note text starts here (M1.1.1, M1.1.2)
ASSEMBLIES = ("M1.2", "M1.3", "M1.4")
M14_NOTE = ("Assembly of M1.4.1, M1.4.2, M1.4.4-M1.4.6 (step 5f, CR-003); divider wall is M2.0.2 (#77). VBV openings "
            "not modelled since M1.4.3 was removed; they would cut the divider wall (M2.0.2 or M1.4.6), owner open (#48) [T].")
M14_OLD_NOTES = ("Assembly of M1.4.1-M1.4.5 (step 5f).",)
REMOVED_PARTS = ("M1.4.3",)  # CR-002 option a: splitter ring removed, the divider wall is M2.0.2 (owned by M2)
DRAFT_PARTS = ("M1.4.6",)  # CR-003: new part, status draft (load path bypass strut -> M2 casing / wall ring not analysed)
CR_MARKS = {"M1.3.1": " Root at r ", "M1.4.1": " Frame zone x ", "M1.4.4": " Root on the M2.0.2",
            "M1.4.5": " Leading edge x ", "M1.4.6": " CR-003 (#77): "}  # generated CR note sentences start here
SCRIPTS = {
    "M1.1.1": "engine/M1_inlet_fan/geometry/dovetail.py", "M1.1.2": "engine/M1_inlet_fan/geometry/rotor_hardware.py",
    "M1.1.3": "engine/M1_inlet_fan/geometry/spinner_case.py", "M1.1.4": "engine/M1_inlet_fan/geometry/dovetail.py",
    "M1.1.5": "engine/M1_inlet_fan/geometry/dovetail.py", "M1.1.6": "engine/M1_inlet_fan/geometry/rotor_hardware.py",
    "M1.2.1": "engine/M1_inlet_fan/geometry/spinner_case.py", "M1.2.2": "engine/M1_inlet_fan/geometry/spinner_case.py",
    "M1.3.1": "engine/M1_inlet_fan/geometry/ogv.py", "M1.4.1": "engine/M1_inlet_fan/geometry/fan_frame.py",
    "M1.4.2": "engine/M1_inlet_fan/geometry/fan_frame.py", "M1.4.4": "engine/M1_inlet_fan/geometry/fan_frame.py",
    "M1.4.5": "engine/M1_inlet_fan/geometry/fan_frame.py", "M1.4.6": "engine/M1_inlet_fan/geometry/fan_frame.py",
}
EXTRA_NOTES = {
    "M1.1.3": "engine/M1_inlet_fan/geometry/spinner_case.py", "M1.1.4": "engine/M1_inlet_fan/geometry/dovetail.py",
    "M1.1.5": "engine/M1_inlet_fan/geometry/dovetail.py", "M1.1.6": "engine/M1_inlet_fan/geometry/rotor_hardware.py",
    "M1.2.1": "engine/M1_inlet_fan/geometry/spinner_case.py", "M1.2.2": "engine/M1_inlet_fan/geometry/spinner_case.py",
    "M1.3.1": "engine/M1_inlet_fan/geometry/ogv.py", "M1.4.1": "engine/M1_inlet_fan/geometry/fan_frame.py",
    "M1.4.2": "engine/M1_inlet_fan/geometry/fan_frame.py", "M1.4.4": "engine/M1_inlet_fan/geometry/fan_frame.py",
    "M1.4.5": "engine/M1_inlet_fan/geometry/fan_frame.py", "M1.4.6": "engine/M1_inlet_fan/geometry/fan_frame.py",
}
EXTRA_NOTES = {
    "M1.1.1": "Geometry step 5a-5c: airfoil from the record, trimmed to the record annulus, shank and single-lobe dovetail [T] (open issues #29, #33-35).",
    "M1.1.2": "Geometry step 5c/5h: rim [T], web and bore sized by R-DISK.1 (rules/disk.md); analytic bore margin 1.007 meets the R-AM.13/15 rule; lug margin 0.715 below it (open issue #33).",
    "M1.1.3": "Material aluminium_alloy chosen [T] (rules/materials.md lists spinner, case, containment and OGV as aluminium or composite [T], no source); tangent ogive [T] (#41).",
    "M1.1.4": "Density 8193 kg/m3 [K] from tools/data/materials.yaml (Special Metals SMC-045, docs/sources.md #44).",
    "M1.1.6": "Aluminium density not in tools/data/materials.yaml (grade not stated); [T] 2800 kg/m3 fallback (#36).",
    "M1.2.1": "Material aluminium_alloy chosen [T]; inner surface = casing wall (tip line + 3.0 mm [T], #16, #28).",
    "M1.2.2": "Material aluminium_alloy placeholder [T], doğrulanamadı; thickness proportional rule [T] (#39, #40).",
}
STALE_NOTES = {  # outdated note texts removed by the update
    "M1.2.2": ["Material not selected."],
    "M1.1.4": ["Density not in tools/data/materials.yaml; [T] 8190 kg/m3 fallback (#36)."],
    "M1.1.6": ["Density not in tools/data/materials.yaml; [T] 2800 kg/m3 fallback (#36)."],
}
NEW_PARTS = [
    {"id": "M1.3.1", "name": "Fan Stage 1 Outlet Guide Vane", "parent": "M1.3",
     "qty": {"value": 51, "unit": "ea", "tag": "T"}, "function": "Remove the bypass swirl (station 13)",
     "material": "aluminium_alloy", "status": "draft", "failure_modes": ["FM-2"],
     "notes": "Count V = ceil(2.1 B) [T] (Tyler-Sofrin cut-off logic [G]); CFM56-7B count doğrulanmadı (#14, #42). "
              "Material aluminium [T] (BOM note aluminium or composite). Section MCA, Carter deviation [G/T] (#43)."},
    {"id": "M1.4.1", "name": "Fan Stage 1 Frame Hub Ring", "parent": "M1.4", "qty": {"value": 1, "unit": "ea", "tag": "G"},
     "function": "Core passage inner wall in the frame; bearing-support flange (M8 boundary)", "material": "aluminium_alloy",
     "status": "draft", "notes": "Bearing interface flange only; LP shaft and bearings 1-2 are M8 [T] (#47)."},
    {"id": "M1.4.2", "name": "Fan Stage 1 Frame Outer Ring", "parent": "M1.4", "qty": {"value": 1, "unit": "ea", "tag": "G"},
     "function": "Bypass outer wall over the OGV and frame; mates with the case rear flange", "material": "aluminium_alloy",
     "status": "draft", "joints": [{"to": "M1.2.1", "type": "bolted_flange"}], "notes": "Sizes [T] (fan_frame_params.yaml)."},
    {"id": "M1.4.4", "name": "Fan Stage 1 Frame Bypass Strut", "parent": "M1.4", "qty": {"value": 12, "unit": "ea", "tag": "T"},
     "function": "Carry the case and OGV loads to the frame hub across the bypass duct", "material": "aluminium_alloy",
     "status": "draft", "notes": "Strut count 12 [T], doğrulanamadı; flat plate (#46)."},
    {"id": "M1.4.5", "name": "Fan Stage 1 Frame Core Strut", "parent": "M1.4", "qty": {"value": 12, "unit": "ea", "tag": "T"},
     "function": "Carry the frame loads across the core passage to the hub ring", "material": "aluminium_alloy",
     "status": "draft", "notes": "Strut count 12 [T], doğrulanamadı; flat plate (#46)."},
    {"id": "M1.4.6", "name": "Fan Stage 1 Frame Core Wall Ring", "parent": "M1.4", "qty": {"value": 1, "unit": "ea", "tag": "G"},
     "function": "Core/bypass divider wall in the frame zone behind station 24 (continues M2.0.2); carries strut loads",
     "material": "aluminium_alloy", "status": "draft", "notes": ""},
]


def cr_notes(L: dict) -> dict:
    """CR-002 / CR-003 note sentences with the numbers of the current frame layout [H] (each starts with CR_MARKS)."""
    m = CR_MARKS
    return {
        "M1.3.1": f"{m['M1.3.1']}{L['r_root']:.6f} m = r_split2 + M2.0.2 casing thickness (#77) [H].",
        "M1.4.1": f"{m['M1.4.1']}{L['xc0']:.6f}-{L['xc1']:.6f} m behind station 24, core inner wall r {L['r_hub']:.6f} m "
                  f"(M2 station 24/25); M8 flange face x {L['xc1'] - L['t_bearing']:.6f}-{L['xc1']:.6f} m, inner radius "
                  f"{L['r_bearing']:.6f} m kept, M8 reviews it when M8 starts (#77) [H].",
        "M1.4.4": f"{m['M1.4.4']} casing outer face, r {L['r_root']:.6f} m (#77) [H].",
        "M1.4.5": f"{m['M1.4.5']}{L['core_strut_x0']:.6f} m behind station 24; core passage r {L['r_hub']:.6f}-"
                  f"{L['r_core_out']:.6f} m (#77) [H].",
        "M1.4.6": f"{m['M1.4.6']}r {L['r_split']:.6f}-{L['r_root']:.6f} m (r_split2 to r_split2 + M2 casing thickness), "
                  f"x {L['xc0']:.6f}-{L['xc1']:.6f} m (station 24 to the frame end) [H]; rules/geometry.md R-G1.2; load "
                  f"path not analysed [T].",
    }


def proposed(model: dict | None = None, path: Path = BOM) -> dict:
    """Updated BOM data (not written)."""
    model = model or asm.build()
    masses = asm.mass_table(model)["parts"]
    data = copy.deepcopy(core_bom.load(path))
    parts = data["parts"]
    by_id = {p["id"]: p for p in parts}
    parts[:] = [p for p in parts if p["id"] not in REMOVED_PARTS]
    by_id = {p["id"]: p for p in parts}
    for p in NEW_PARTS:
        if p["id"] not in by_id:
            parts.append(copy.deepcopy(p))
            by_id[p["id"]] = parts[-1]
    by_id["M1.3"].update(material=None, name="Fan Stage 1 Outlet Guide Vane Row", qty={"value": 1, "unit": "ea", "tag": "G"},
                         notes="One vane row (assembly); vanes M1.3.1.")
    note = by_id["M1.4"].get("notes", "")
    for old in M14_OLD_NOTES:
        note = " ".join(note.replace(old, "").split())
    by_id["M1.4"].update(material=None, notes=note if M14_NOTE in note else (note + " " + M14_NOTE).strip())
    for pid, row in masses.items():
        p = by_id[pid]
        if p.get("material") == "tbd":
            p["material"] = row["material"]
        p["mass"] = {"value": round(row["unit_kg"], 4), "unit": "kg", "tag": "H"}
        p["geometry"] = {"script": SCRIPTS[pid], "params": {"revision": GEOMETRY_REVISION}}
        if pid in STALE_NOTES:
            for old in STALE_NOTES[pid]:
                p["notes"] = " ".join(p.get("notes", "").replace(old, "").split())
        if pid in EXTRA_NOTES and EXTRA_NOTES[pid] not in p.get("notes", ""):
            p["notes"] = (p.get("notes", "") + " " + EXTRA_NOTES[pid]).strip()
    st = rh.stress(model["frame"]["spinner_case"]["rotor"])
    rm, rot = st["root_modes"], model["frame"]["spinner_case"]["rotor"]
    ok = st["check"] == "pass" and rm["pass"]
    gen = {
        "M1.1.1": f"Geometry step 5a-5i: airfoil from the record trimmed to the record annulus; shank and single-lobe "
                  f"dovetail [T], slab {rot['layout']['x_b'] - rot['layout']['x_a']:.4f} m by R-DISK.2 (rules/disk.md); "
                  f"blade neck margin {rm['modes']['blade_neck_tension']['margin']:.3f} [H] (open issues #29, #34, #35).",
        "M1.1.2": f"Geometry step 5c-5i: rim [T]; slab by R-DISK.2, web and bore by R-DISK.1 (rules/disk.md); bore "
                  f"margin {st['margin']:.3f}, smallest dovetail/lug margin {rm['min_margin']:.3f} "
                  f"({rm['governing']}) [H]; rule {'met' if ok else 'not met'}.",
    }
    for pid, text in gen.items():
        base = by_id[pid].get("notes", "").split(GEN_MARK)[0]
        by_id[pid]["notes"] = (base + " " + text).strip()
    for pid, text in cr_notes(model["frame"]["layout"]).items():
        base = by_id[pid].get("notes", "").split(CR_MARKS[pid].strip())[0].rstrip()
        by_id[pid]["notes"] = (base + text).strip()
    status = {"M1.1": "review" if ok else "draft", "M1.1.2": "review" if ok else "draft"}
    for pid in ("M1.1", *ASSEMBLIES, *SCRIPTS):
        by_id[pid]["status"] = status.get(pid, "draft" if pid in DRAFT_PARTS else "review")
    parts.sort(key=lambda q: tuple(int(x) for x in q["id"].split(".")[1:]))  # children after their parent
    return data


def apply(write: bool = False, path: Path = BOM) -> tuple[dict, object]:
    """Validate the proposed BOM; write it via core.bom.write only if write=True and there are no errors."""
    data = proposed(path=path)
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
