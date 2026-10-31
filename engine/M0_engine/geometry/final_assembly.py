"""M0 final engine assembly (docs/m3_m9_plan.md): every module's parts in one STEP, the cross-module common volume
check and the mass table.

Modules: M1 (accepted revision, engine/M1_inlet_fan/geometry/assembly.build), M2 (active revision,
engine/M2_booster/geometry/assembly.build), M3-M9 (geometry/build.build of each module, tools/concept.Module). All
read-only: M0 places the parts as their modules define them and edits nothing. Patterned parts are placed by rotation
about +X (M1 frame, R-G1/R-G2.1).

regenerate() re-runs M3 -> M9 in interface order (each module reads its upstream interface file).
Output: .cache/geometry/M0_engine/final/engine_assembly.step and final_report.yaml (derived).

Run: python -m engine.M0_engine.geometry.final_assembly [--regenerate]
"""

import importlib
import itertools
import math
import sys

import cadquery as cq

from core.records import ROOT
from core.util import write_yaml
from tools import concept as C

ORDER = ("M3", "M4", "M5", "M6", "M7", "M8", "M9")
BUILDERS = {"M3": "engine.M3_hp_compressor.geometry.build", "M4": "engine.M4_combustor.geometry.build",
            "M5": "engine.M5_hp_turbine.geometry.build", "M6": "engine.M6_lp_turbine.geometry.build",
            "M7": "engine.M7_nozzle.geometry.build", "M8": "engine.M8_shaft_bearing.geometry.build",
            "M9": "engine.M9_secondary_air_oil.geometry.build"}
OUT_DIR = ROOT / ".cache" / "geometry" / "M0_engine" / "final"
STEP_NAME = "engine_assembly.step"
FULL_PATTERN_MAX = 24  # patterned parts with more instances are checked with instance 0 only
# Known cross-module passages (M9 R-D9.4): service lines and drive shafts through other modules' struts and rings
KNOWN_PASSAGES = {("M1.4.1", "M9.0.2"), ("M1.4.2", "M9.0.2"), ("M1.4.4", "M9.0.2"), ("M1.4.5", "M9.0.2"),
                  ("M1.4.6", "M9.0.2"), ("M1.4.1", "M9.0.7"), ("M1.4.2", "M9.0.7"), ("M1.4.4", "M9.0.7"),
                  ("M1.4.5", "M9.0.7"), ("M1.4.6", "M9.0.7"), ("M7.0.4", "M9.0.8"), ("M7.0.5", "M9.0.8"),
                  ("M7.0.6", "M9.0.8"), ("M2.0.2", "M9.0.2"), ("M2.0.2", "M9.0.7")}


def regenerate() -> None:
    for m in ORDER:
        importlib.import_module(BUILDERS[m]).main()


def _parts_m1() -> list[dict]:
    from engine.M1_inlet_fan.geometry import assembly as A1
    model = A1.build()
    return [{"module": "M1", "pid": pid, "name": p["name"], "shape": p["shape"], "angles": list(p["angles"]),
             "material": p["material"], "revolved": p["qty"] == 1} for pid, p in model["parts"].items()]


def _parts_m2() -> list[dict]:
    from engine.M2_booster.geometry import assembly as A2
    model = A2.build()
    return [{"module": "M2", "pid": pid, "name": p["name"], "shape": p["shape"], "angles": list(p["angles"]),
             "material": p["material"], "revolved": bool(p["axisymmetric"])} for pid, p in model["parts"].items()]


def _parts_concept(module: str) -> tuple[list[dict], C.Module]:
    mod = importlib.import_module(BUILDERS[module]).build()
    out = []
    for p in mod.parts:
        ang = [p.phase_deg + 360.0 * i / p.count for i in range(p.count)] if p.patterned else [0.0]
        out.append({"module": module, "pid": p.pid, "name": p.name, "shape": p.shape, "angles": ang,
                    "material": p.material, "revolved": p.count == 1 and _is_revolved(p.shape), "mass": p.unit_mass,
                    "qty": p.count})
    return out, mod


def _is_revolved(s: cq.Shape) -> bool:
    bb = s.BoundingBox()
    return abs(bb.ymax + bb.ymin) < 1e-6 * max(1.0, bb.ymax) and abs(bb.zmax + bb.zmin) < 1e-6 * max(1.0, bb.zmax) \
        and abs(bb.ymax - bb.zmax) < 1e-6 * max(1.0, bb.zmax)


def collect() -> dict:
    parts = _parts_m1() + _parts_m2()
    modules = {}
    for m in ORDER:
        ps, mod = _parts_concept(m)
        parts += ps
        modules[m] = mod
    return {"parts": parts, "modules": modules}


def build_assembly(data: dict) -> cq.Assembly:
    top = cq.Assembly(name="cfm56_7b27_concept")
    by_mod = {}
    for p in data["parts"]:
        by_mod.setdefault(p["module"], []).append(p)
    for m, ps in by_mod.items():
        sub = cq.Assembly(name=f"{m.lower()}_assembly")
        for p in ps:
            col = cq.Color(*C.COLOR.get(p["material"], (0.6, 0.6, 0.6)))
            for i, a in enumerate(p["angles"]):
                sub.add(p["shape"], name=f"{p['pid'].replace('.', '_')}_{i}",
                        loc=cq.Location(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), a), color=col)
        top.add(sub, name=f"{m.lower()}")
    return top


def _envelope(p: dict) -> tuple[float, float, float]:
    """(xmin, xmax, rmax) over all instances."""
    bb = p["shape"].BoundingBox()
    if len(p["angles"]) == 1 and not p["revolved"]:
        return bb.xmin, bb.xmax, -1.0  # sentinel: use the real box
    r = max(math.hypot(y, z) for y in (bb.ymin, bb.ymax) for z in (bb.zmin, bb.zmax))
    return bb.xmin, bb.xmax, r


def _boxes_overlap(a: dict, b: dict) -> bool:
    ba, bb_ = a["shape"].BoundingBox(), b["shape"].BoundingBox()
    if ba.xmax < bb_.xmin or bb_.xmax < ba.xmin:
        return False
    ea, eb = _envelope(a), _envelope(b)

    def box(p, e, bbx):
        if e[2] < 0:
            return (bbx.ymin, bbx.ymax, bbx.zmin, bbx.zmax)
        return (-e[2], e[2], -e[2], e[2])
    ya0, ya1, za0, za1 = box(a, ea, ba)
    yb0, yb1, zb0, zb1 = box(b, eb, bb_)
    return not (ya1 < yb0 or yb1 < ya0 or za1 < zb0 or zb1 < za0)


def _instances(p: dict) -> list[cq.Shape]:
    if len(p["angles"]) == 1:
        return [p["shape"]]
    angs = p["angles"] if len(p["angles"]) <= FULL_PATTERN_MAX else p["angles"][:1]
    return [C.rotate_x(p["shape"], a) for a in angs]


def interference(data: dict, min_mm3: float = 1.0) -> list[dict]:
    """Cross-module common volumes above min_mm3 (instance 0 of patterned parts against revolved parts; every
    instance up to FULL_PATTERN_MAX against non-revolved parts). M1-M2 pairs are M2's own check (step 4)."""
    out = []
    ps = data["parts"]
    for a, b in itertools.combinations(ps, 2):
        if a["module"] == b["module"] or {a["module"], b["module"]} == {"M1", "M2"}:
            continue
        if not _boxes_overlap(a, b):
            continue
        ia = [a["shape"]] if (a["revolved"] or b["revolved"]) else _instances(a)
        ib = [b["shape"]] if (a["revolved"] or b["revolved"]) else _instances(b)
        if a["revolved"] and not b["revolved"]:
            ib = _instances(b) if len(b["angles"]) > 1 else ib
        if b["revolved"] and not a["revolved"]:
            ia = _instances(a) if len(a["angles"]) > 1 else ia
        if a["revolved"] and b["revolved"]:
            ia, ib = [a["shape"]], [b["shape"]]
        v = 0.0
        for sa in ia:
            for sb in ib:
                v += C.common_volume(sa, sb)
        if v * 1e9 > min_mm3:
            key = tuple(sorted((a["pid"], b["pid"])))
            out.append({"a": key[0], "b": key[1], "mm3": round(v * 1e9, 1), "known": key in KNOWN_PASSAGES})
    return out


def mass_table(data: dict) -> dict:
    out = {}
    for m, mod in data["modules"].items():
        out[m] = round(mod.mass(), 2)
    return out


def export(data: dict) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / STEP_NAME
    build_assembly(data).export(str(path), exportType="STEP")
    bbs = [p["shape"].BoundingBox() for p in data["parts"]]
    report = {"description": "M0 final assembly report; generated by engine/M0_engine/geometry/final_assembly.py",
              "step": str(path.relative_to(ROOT).as_posix()),
              "instances": sum(len(p["angles"]) for p in data["parts"]),
              "parts": len(data["parts"]),
              "x_extent_m": [C.r6(min(b.xmin for b in bbs)), C.r6(max(b.xmax for b in bbs))],
              "mass_m3_m9_kg": mass_table(data)}
    return {"path": path, "report": report}


def main(argv: list[str]) -> None:
    if "--regenerate" in argv:
        regenerate()
    data = collect()
    res = export(data)
    rep = res["report"]
    rep["cross_module_common_volume"] = interference(data)
    write_yaml(OUT_DIR / "final_report.yaml", rep)
    unknown = [r for r in rep["cross_module_common_volume"] if not r["known"]]
    print(f"final assembly {res['path']} ({res['path'].stat().st_size / 1e6:.1f} MB), {rep['instances']} instances, "
          f"x {rep['x_extent_m']}, cross-module overlaps {len(rep['cross_module_common_volume'])} "
          f"(unknown {len(unknown)})")
    for r in unknown:
        print("  ", r)


if __name__ == "__main__":
    main(sys.argv[1:])
