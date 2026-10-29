"""M1 full assembly (step 5g): every M1 part placed once per instance in one STEP, a mass table per BOM part id and
the M1 total, and the ICD comparison of the totals.

Parts come from the stage builders (cached): rotor (rotor_hardware: blade with root, disk, shim, spacer, platform),
spinner_case (spinner, case shell, containment ring), ogv (vane row), fan_frame (rings and struts). Repeated parts are
one shape placed by rotation about the engine axis (frame.export_assembly). Part ids follow the proposed BOM of
bom_update.py.
"""

import math
from functools import lru_cache
from pathlib import Path

from core import records
from core.budgets import read_icd
from engine.M1_inlet_fan.geometry import fan_frame as ff
from engine.M1_inlet_fan.geometry import fan_ring as ring
from engine.M1_inlet_fan.geometry import frame as fr
from engine.M1_inlet_fan.geometry import ogv as ogvm
from engine.M1_inlet_fan.geometry import rotor_hardware as rh
from engine.M1_inlet_fan.geometry import spinner_case as sc
from engine.M1_inlet_fan.geometry import flowpath as fpm

ASSEMBLY_NAME = "m1_assembly"


@lru_cache(maxsize=2)
def build(rev: str | None = None, root: Path = records.ROOT) -> dict:
    """Part list: id -> name, shape, material id, qty, instance angles (deg, rotor sense)."""
    frm = ff.build(rev, root)
    sp = frm["spinner_case"]
    rot = sp["rotor"]
    og = ogvm.build(rev, root)
    n, V, S = rot["n"], og["V"], frm["layout"]["n_struts"]
    mat_frame = fr.v(ff.frame_params()["material"])
    cp = sc.case_params()

    def angles(k):
        return [j * 360.0 / k for j in range(k)]

    parts = {
        "M1.1.1": ("Fan Stage 1 Rotor Blade", rot["blade"], "ti6al4v", angles(n)),
        "M1.1.2": ("Fan Stage 1 Disk", rot["disk"], "ti6al4v", [0.0]),
        "M1.1.3": ("Fan Stage 1 Spinner", sp["spinner"], fr.v(cp["spinner"]["material"]), [0.0]),
        "M1.1.4": ("Fan Stage 1 Dovetail Shim", rot["shim"], "alloy718", angles(n)),
        "M1.1.5": ("Fan Stage 1 Blade Spacer", rot["spacer"], "ti6al4v", angles(n)),
        "M1.1.6": ("Fan Stage 1 Blade Platform", rot["platform"], "aluminium_alloy", angles(n)),
        "M1.2.1": ("Fan Stage 1 Case Shell", sp["case_shell"], fr.v(cp["case"]["material"]), [0.0]),
        "M1.2.2": ("Fan Stage 1 Containment Ring", sp["containment_ring"], fr.v(cp["containment"]["material"]), [0.0]),
        "M1.3.1": ("Fan Stage 1 Outlet Guide Vane", og["vane"], fr.v(ogvm.ogv_params()["material"]), angles(V)),
        "M1.4.1": ("Fan Stage 1 Frame Hub Ring", frm["parts"]["hub_ring"], mat_frame, [0.0]),
        "M1.4.2": ("Fan Stage 1 Frame Outer Ring", frm["parts"]["outer_ring"], mat_frame, [0.0]),
        "M1.4.3": ("Fan Stage 1 Frame Splitter Ring", frm["parts"]["splitter_ring"], mat_frame, [0.0]),
        "M1.4.4": ("Fan Stage 1 Frame Bypass Strut", frm["parts"]["bypass_strut"], mat_frame, angles(S)),
        "M1.4.5": ("Fan Stage 1 Frame Core Strut", frm["parts"]["core_strut"], mat_frame, angles(S)),
    }
    return {"revision": rot["flowpath"]["revision"], "frame": frm, "ogv": og,
            "parts": {pid: {"name": nm, "shape": s, "material": m, "angles": a, "qty": len(a)}
                      for pid, (nm, s, m, a) in parts.items()}}


def mass_table(model: dict) -> dict:
    """Mass per part id: unit mass = volume x density, set = qty x unit [H]; density tags from materials.yaml or the
    [T] fallback."""
    rho = rh.densities()
    rows = {}
    for pid, p in model["parts"].items():
        vol = p["shape"].Volume()
        d = rho[p["material"]]
        rows[pid] = {"name": p["name"], "material": p["material"], "qty": p["qty"], "volume_m3": vol,
                     "density": d["value"], "density_tag": d["tag"], "unit_kg": vol * d["value"],
                     "set_kg": vol * d["value"] * p["qty"], "tag": "H"}
    groups = {}
    for pid, r in rows.items():
        g = ".".join(pid.split(".")[:2])
        groups[g] = groups.get(g, 0.0) + r["set_kg"]
    return {"parts": rows, "groups_kg": groups, "total_kg": sum(r["set_kg"] for r in rows.values()), "tag": "H"}


def extent(model: dict) -> dict:
    """Axial and radial extent of the assembly [H] (from the axisymmetric parts and the stations)."""
    sp = model["frame"]["spinner_case"]
    x0 = sp["info"]["spinner"]["x_nose_m"]
    x1 = model["frame"]["layout"]["x1"]
    bb = [model["parts"][k]["shape"].BoundingBox() for k in ("M1.2.1", "M1.2.2", "M1.4.2")]
    r_max = max(max(b.zmax, -b.zmin, b.ymax, -b.ymin) for b in bb)
    return {"x_nose_m": x0, "x_rear_m": x1, "length_m": x1 - x0, "r_max_m": r_max}


def icd_comparison(model: dict) -> dict:
    """M1 total mass and length against the ICD. The ICD M1 budget lists only cycle items (read_icd); if no mass or
    length item exists the comparison is reported as not possible (no check_budget call, nothing relaxed)."""
    icd = read_icd("M1 agent")
    items = icd["modules"]["M1"]["budget"]
    found = {k: items[k] for k in items if any(w in k.lower() for w in ("mass", "weight", "length"))}
    m = mass_table(model)
    return {"icd_items": found, "total_kg": m["total_kg"], "length_m": extent(model)["length_m"],
            "status": "compared" if found else "no mass or length item in the ICD M1 budget; not compared"}


def interference_summary(model: dict) -> dict:
    """Common volumes of the cross-stage neighbours not already covered by the stage checks [H]."""
    p = model["parts"]
    pairs = {"spinner-case": ("M1.1.3", "M1.2.1"), "ogv-containment": ("M1.3.1", "M1.2.2"),
             "frame_outer-case": ("M1.4.2", "M1.2.1"), "frame_splitter-blade": ("M1.4.3", "M1.1.1"),
             "frame_splitter-disk": ("M1.4.3", "M1.1.2"), "frame_hub-disk": ("M1.4.1", "M1.1.2")}
    out = {}
    for name, (a, b) in pairs.items():
        sa, sb = p[a]["shape"], p[b]["shape"]
        out[name] = (0.0 if not ring._bbox_overlap(sa, sb) else fr.boolean("common", sa, sb).Volume())
    return out


def export(model: dict, per_part: bool = True) -> dict:
    """One STEP with every instance; with per_part also the per-part STEPs of the stage modules."""
    rev = model["revision"]
    inst = []
    for pid, p in model["parts"].items():
        for j, a in enumerate(p["angles"]):
            inst.append((pid if p["qty"] == 1 else f"{pid}_{j:02d}", p["shape"], a))
    paths = {ASSEMBLY_NAME: fr.export_assembly(inst, ASSEMBLY_NAME, rev)}
    if per_part:
        fp = model["frame"]["flowpath"]
        for name, s in fpm.solids(fp).items():
            paths[name] = fr.export_step(s, name, rev)
        fr.export_step(fp["blade"]["solid"], "fan_blade", rev)
        paths.update(rh.export(model["frame"]["spinner_case"]["rotor"]))
        paths.update(sc.export(model["frame"]["spinner_case"]))
        paths.update(ogvm.export(model["ogv"]))
        paths.update(ff.export(model["frame"]))
    return paths


def main() -> None:
    model = build()
    m = mass_table(model)
    for pid, r in m["parts"].items():
        print(f"  {pid:7s} {r['name']:36s} {r['qty']:3d} x {r['unit_kg']:8.3f} = {r['set_kg']:8.3f} kg "
              f"({r['material']}, rho {r['density_tag']})")
    print("  groups", {k: round(v, 2) for k, v in m["groups_kg"].items()}, f"total {m['total_kg']:.2f} kg [H]")
    print("  extent", {k: round(v, 4) for k, v in extent(model).items()})
    print("  icd", icd_comparison(model)["status"])
    print("  cross-stage common volumes", interference_summary(model))
    paths = export(model)
    print(f"  STEP {paths[ASSEMBLY_NAME]} ({paths[ASSEMBLY_NAME].stat().st_size / 1e6:.1f} MB), {len(paths)} files")


if __name__ == "__main__":
    main()
