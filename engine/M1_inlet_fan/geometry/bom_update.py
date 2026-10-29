"""Proposed M1 bom.yaml update for step 5g (draft for M0 review; nothing is written unless apply(write=True)).

Changes: materials for the tbd parts (all [T], aluminium per rules/materials.md), unit mass from the assembly mass
table [H], geometry script per part, notes with tags and sources, and the parts missing from the BOM: M1.3 becomes
the OGV row assembly with M1.3.1 the vane (qty 51 [T]); M1.4 becomes the frame assembly with M1.4.1-M1.4.5.
Status: "review" for the parts built at concept level in steps 5a-5f; "draft" for the disk M1.1.2 (analytic bore
margin 0.717 below the rule, open issue #32) and for the rotor assembly M1.1 that contains it. Never "approved".
proposed() is idempotent: applied to its own output it returns the same data. The BOM is written only through core.bom.write and validated with core.bom.check_data first.

Usage (M0): from engine.M1_inlet_fan.geometry import bom_update as b; data, rep = b.apply()  # dry run
            b.apply(write=True)  # writes bom.yaml after review
"""

import copy
from pathlib import Path

from core import bom as core_bom
from engine.M1_inlet_fan.geometry import assembly as asm
from engine.M1_inlet_fan.geometry import frame as fr

BOM = fr.HERE.parent / "bom" / "bom.yaml"
GEOMETRY_REVISION = "rev011"  # record whose params/results the geometry inputs were built from (fixed, not ACTIVE)
STATUS = {"M1.1": "draft", "M1.1.2": "draft"}  # every other part listed in SCRIPTS or ASSEMBLIES: "review"
ASSEMBLIES = ("M1.2", "M1.3", "M1.4")
M14_NOTE = "Assembly of M1.4.1-M1.4.5 (step 5f)."
SCRIPTS = {
    "M1.1.1": "engine/M1_inlet_fan/geometry/dovetail.py", "M1.1.2": "engine/M1_inlet_fan/geometry/rotor_hardware.py",
    "M1.1.3": "engine/M1_inlet_fan/geometry/spinner_case.py", "M1.1.4": "engine/M1_inlet_fan/geometry/dovetail.py",
    "M1.1.5": "engine/M1_inlet_fan/geometry/dovetail.py", "M1.1.6": "engine/M1_inlet_fan/geometry/rotor_hardware.py",
    "M1.2.1": "engine/M1_inlet_fan/geometry/spinner_case.py", "M1.2.2": "engine/M1_inlet_fan/geometry/spinner_case.py",
    "M1.3.1": "engine/M1_inlet_fan/geometry/ogv.py", "M1.4.1": "engine/M1_inlet_fan/geometry/fan_frame.py",
    "M1.4.2": "engine/M1_inlet_fan/geometry/fan_frame.py", "M1.4.3": "engine/M1_inlet_fan/geometry/fan_frame.py",
    "M1.4.4": "engine/M1_inlet_fan/geometry/fan_frame.py", "M1.4.5": "engine/M1_inlet_fan/geometry/fan_frame.py",
}
EXTRA_NOTES = {
    "M1.1.1": "Geometry step 5a-5c: airfoil from the record, trimmed to the record annulus, shank and single-lobe dovetail [T] (open issues #29, #33-35).",
    "M1.1.2": "Geometry step 5c: rim/web/bore [T]; analytic bore margin 0.717 below the R-AM.13/15 rule (open issue #32).",
    "M1.1.3": "Material aluminium_alloy chosen [T] (rules/materials.md lists spinner, case, containment and OGV as aluminium or composite [T], no source); tangent ogive [T] (#41).",
    "M1.1.4": "Density not in tools/data/materials.yaml; [T] 8190 kg/m3 fallback (#36).",
    "M1.1.6": "Density not in tools/data/materials.yaml; [T] 2800 kg/m3 fallback (#36).",
    "M1.2.1": "Material aluminium_alloy chosen [T]; inner surface = casing wall (tip line + 3.0 mm [T], #16, #28).",
    "M1.2.2": "Material aluminium_alloy placeholder [T], doğrulanamadı; thickness proportional rule [T] (#39, #40).",
}
STALE_NOTES = {"M1.2.2": "Material not selected."}  # outdated note text removed by the update
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
    {"id": "M1.4.3", "name": "Fan Stage 1 Frame Splitter Ring", "parent": "M1.4", "qty": {"value": 1, "unit": "ea", "tag": "G"},
     "function": "Separate core and bypass flow from the station 21 lip; bypass inner wall; VBV openings",
     "material": "aluminium_alloy", "status": "draft",
     "notes": "Girão 2023 PDF p. 36-37 [KS]: frame separates primary and secondary flow and houses the VBVs; VBV owner "
              "not set by M0, openings placeholder [T] (#48)."},
    {"id": "M1.4.4", "name": "Fan Stage 1 Frame Bypass Strut", "parent": "M1.4", "qty": {"value": 12, "unit": "ea", "tag": "T"},
     "function": "Carry the case and OGV loads to the frame hub across the bypass duct", "material": "aluminium_alloy",
     "status": "draft", "notes": "Strut count 12 [T], doğrulanamadı; flat plate (#46)."},
    {"id": "M1.4.5", "name": "Fan Stage 1 Frame Core Strut", "parent": "M1.4", "qty": {"value": 12, "unit": "ea", "tag": "T"},
     "function": "Carry the frame loads across the core passage to the hub ring", "material": "aluminium_alloy",
     "status": "draft", "notes": "Strut count 12 [T], doğrulanamadı; flat plate (#46)."},
]


def proposed(model: dict | None = None, path: Path = BOM) -> dict:
    """Updated BOM data (not written)."""
    model = model or asm.build()
    masses = asm.mass_table(model)["parts"]
    data = copy.deepcopy(core_bom.load(path))
    parts = data["parts"]
    by_id = {p["id"]: p for p in parts}
    for p in NEW_PARTS:
        if p["id"] not in by_id:
            parts.append(copy.deepcopy(p))
            by_id[p["id"]] = parts[-1]
    by_id["M1.3"].update(material=None, name="Fan Stage 1 Outlet Guide Vane Row", qty={"value": 1, "unit": "ea", "tag": "G"},
                         notes="One vane row (assembly); vanes M1.3.1.")
    note = by_id["M1.4"].get("notes", "")
    by_id["M1.4"].update(material=None, notes=note if M14_NOTE in note else (note + " " + M14_NOTE).strip())
    for pid, row in masses.items():
        p = by_id[pid]
        if p.get("material") == "tbd":
            p["material"] = row["material"]
        p["mass"] = {"value": round(row["unit_kg"], 4), "unit": "kg", "tag": "H"}
        p["geometry"] = {"script": SCRIPTS[pid], "params": {"revision": GEOMETRY_REVISION}}
        if pid in STALE_NOTES:
            p["notes"] = p.get("notes", "").replace(STALE_NOTES[pid], "").strip()
        if pid in EXTRA_NOTES and EXTRA_NOTES[pid] not in p.get("notes", ""):
            p["notes"] = (p.get("notes", "") + " " + EXTRA_NOTES[pid]).strip()
    for pid in ("M1.1", *ASSEMBLIES, *SCRIPTS):
        by_id[pid]["status"] = STATUS.get(pid, "review")
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
