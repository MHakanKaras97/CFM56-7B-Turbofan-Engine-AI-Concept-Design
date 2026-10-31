"""M2 geometry step 4: booster assembly, station 25, BOM part list and mass table (rules/geometry.md R-G2.22-27).

Parts come from the step 1-3 builders (cached): blades.py (rotor airfoils, stator vanes) and hardware.py (drum M2.0.1
with forward cone and hub wall, casing M2.0.2, root blocks, inner shrouds, vane feet). A rotor blade M2.n.1 is its
airfoil plus its root block, a stator vane M2.n.2 is its vane plus its foot (R-G2.10/12: part of the blade, not
fused). Repeated parts are one shape placed by rotation about the engine axis (k x 360/N, R-G2.1). M1 rev015 parts
come from the M1 assembly builder (read-only import, no M1 file written).

Common volume (R-G2.27): every pair of M2 parts and every M2 part against every M1 part, over all instances, exact by
symmetry or by an axisymmetric superset (no sampling): x ranges disjoint -> 0; one side axisymmetric -> one boolean
with instance 0 of the other; drum -> its unslotted revolved superset first; two cyclic rows -> revolved envelope of
one row against instance 0 of the other, else every instance pair whose bounding boxes meet.

Run: python -m engine.M2_booster.geometry.assembly  (prints the tables, writes the STEP files to
.cache/geometry/M2_booster/rev002/)
"""

import hashlib
import math
from functools import lru_cache
from pathlib import Path

import cadquery as cq

from core import records
from engine.M2_booster.geometry import blades as B
from engine.M2_booster.geometry import flowpath as FP
from engine.M2_booster.geometry import hardware as HW
from engine.M2_booster.geometry import layout as L

DESIGN_REVISION = "rev002"  # M2 revision being prepared (STEP directory); inputs are the rev001 record
INPUT_REVISION = "rev001"  # record whose params/results the geometry is built from (fixed, R-G2.24)
ASSEMBLY_NAME = "m2_assembly"
LOLIS_ENGINE_KG = 2285.5  # Lolis 2014 Table 4.2 p. 125, estimated engine weight [KS weak] (rules/analyses.md)
LOLIS_BOOSTER_SHARE = 0.075  # Lolis 2014 Table 4.3 p. 126, "IPC" share of the engine weight [KS weak]
RECORD_FILES = ("analysis/booster_params.yaml", "analysis/meanline_results.yaml")


# --- part list (R-G2.24) ------------------------------------------------------------

@lru_cache(maxsize=1)
def build() -> dict:
    """Part id -> name, solids (instance 0), material, density material, qty, instance angles, symmetry."""
    hb = HW.build()
    model, H, P = hb["model"], hb["hw"], hb["parts"]
    gp = model["params"]
    rot = [r for r in model["rows"] if r["kind"] == "rotor"]
    sta = [r for r in model["rows"] if r["kind"] == "stator"]
    rotor_mat = L.v(gp["rotor_material"])
    stator_rho = L.v(gp["stator_mass_material"])

    def angles(n):
        return [k * 360.0 / n for k in range(n)]

    parts = {
        "M2.0.1": {"name": "Booster Drum", "solids": {"drum": P["drum"]}, "material": "ti6al4v",
                   "rho_material": "ti6al4v", "angles": [0.0], "axisymmetric": False,
                   "superset": P["drum_unslotted"], "script": "engine/M2_booster/geometry/hardware.py",
                   # over rim n (x_f..x_a) the slotted drum repeats every 360/N_n (only the rim n slots lie there)
                   "x_symmetry": [(rim["x_f"], rim["x_a"], rim["row"]["count"]) for rim in H["rims"]]},
        "M2.0.2": {"name": "Booster Case", "solids": {"casing": P["casing"]}, "material": "tbd",
                   "rho_material": stator_rho, "angles": [0.0], "axisymmetric": True, "superset": None,
                   "script": "engine/M2_booster/geometry/hardware.py"},
    }
    for r, root in zip(rot, P["roots"]):
        parts[f"M2.{r['stage']}.1"] = {
            "name": f"Booster Stage {r['stage']} Rotor Blade", "solids": {"airfoil": r["solid"], "root block": root},
            "material": rotor_mat, "rho_material": rotor_mat, "angles": angles(r["count"]), "axisymmetric": False,
            "superset": None, "script": "engine/M2_booster/geometry/blades.py"}
    for r, foot in zip(sta, P["feet"]):
        parts[f"M2.{r['stage']}.2"] = {
            "name": f"Booster Stage {r['stage']} Stator Vane", "solids": {"vane": r["solid"], "foot": foot},
            "material": "tbd", "rho_material": stator_rho, "angles": angles(r["count"]), "axisymmetric": False,
            "superset": None, "script": "engine/M2_booster/geometry/blades.py"}
    for r, sh in zip(sta, P["shrouds"]):
        parts[f"M2.{r['stage']}.4"] = {
            "name": f"Booster Stage {r['stage']} Inner Shroud", "solids": {"inner shroud": sh}, "material": "tbd",
            "rho_material": stator_rho, "angles": [0.0], "axisymmetric": True, "superset": None,
            "script": "engine/M2_booster/geometry/hardware.py"}
    for p in parts.values():
        p["qty"] = len(p["angles"])
        p["shape"] = (next(iter(p["solids"].values())) if len(p["solids"]) == 1
                      else cq.Compound.makeCompound(list(p["solids"].values())))
    order = sorted(parts, key=lambda pid: tuple(int(x) for x in pid.split(".")[1:]))
    return {"hb": hb, "parts": {pid: parts[pid] for pid in order}, "rotor_counts": [r["count"] for r in rot],
            "stator_counts": [r["count"] for r in sta]}


def mass_table(asm: dict | None = None) -> dict:
    """Unit mass = sum of the solid volumes x density, set = qty x unit [H]; tbd materials use the
    stator_mass_material density as placeholder (#71). Information only; check value Lolis about 171 kg."""
    asm = asm or build()
    rows = {}
    for pid, p in asm["parts"].items():
        rho = B.density(p["rho_material"])
        vols = {k: s.Volume() for k, s in p["solids"].items()}
        unit = sum(vols.values()) * rho
        rows[pid] = {"name": p["name"], "material": p["material"], "rho_material": p["rho_material"], "density": rho,
                     "qty": p["qty"], "volumes_m3": vols, "sub_kg": {k: v * rho for k, v in vols.items()},
                     "unit_kg": unit, "set_kg": unit * p["qty"]}
    total = sum(r["set_kg"] for r in rows.values())
    check = LOLIS_ENGINE_KG * LOLIS_BOOSTER_SHARE
    return {"parts": rows, "total_kg": total, "check_value_kg": check, "ratio_to_check": total / check}


# --- station 25 and the casing / wall ring boundary (R-G2.22, R-G2.23) -------------------

def m1_parts() -> dict:
    """M1 rev015 parts (instance 0, angles, axisymmetric flag) from the M1 assembly builder (read-only import)."""
    from engine.M1_inlet_fan.geometry import assembly as m1a
    axisym = {"M1.1.3", "M1.2.1", "M1.2.2", "M1.4.1", "M1.4.2", "M1.4.6"}  # revolved solids (M1 builders)
    out = {}
    for pid, p in m1a.build()["parts"].items():
        out[pid] = {"name": p["name"], "solids": {pid: p["shape"]}, "shape": p["shape"], "angles": p["angles"],
                    "qty": p["qty"], "axisymmetric": pid in axisym, "superset": None}
    return out


def station_25_checks(asm: dict | None = None) -> dict:
    """R-G2.22: station 25 x from the M1 code, its agreement with flowpath.yaml and with the M1 hardware ends; the
    duct annulus (M1 hub ring radius, wall ring inner radius) vs the M2 station 24 radii [H]."""
    asm = asm or build()
    s = FP.station_25()
    fp = L.read_yaml(L.M2_FLOWPATH)["interfaces"]["M3_station_25"]
    x24 = asm["hb"]["model"]["layout"]["x24"]
    return {**s, "x24_m2": x24, "x25_file": fp.get("x_m"), "duct_length": s["x25"] - x24,
            "d_x25_file": None if fp.get("x_m") is None else fp["x_m"] - s["x25"],
            "d_r_hub": s["r_hub_m1"] - float(fp["r_hub_m"]), "d_r_tip": s["r_tip_m1"] - float(fp["r_tip_m"])}


def casing_boundary(asm: dict | None = None) -> dict:
    """R-G2.23: M2.0.2 ends at station 24, M1.4.6 starts there with the same radii; common volume, distance and the
    axial overlap of the two walls (0: the divider wall mass is counted once) [H]."""
    asm = asm or build()
    cas = asm["parts"]["M2.0.2"]["shape"]
    m1 = m1_parts()["M1.4.6"]["shape"]
    bc, bw = cas.BoundingBox(), m1.BoundingBox()
    H = asm["hb"]["hw"]
    from engine.M1_inlet_fan.geometry import assembly as m1a
    m1_mass = m1a.mass_table(m1a.build())["parts"]["M1.4.6"]
    return {"x_casing": (bc.xmin, bc.xmax), "x24": H["x24"], "x_wall_ring": (bw.xmin, bw.xmax),
            "axial_overlap": max(0.0, min(bc.xmax, bw.xmax) - max(bc.xmin, bw.xmin)),
            "common_volume_m3": _common(cas, m1), "distance_m": cas.distance(m1),
            "r_casing": (H["r_casing"], H["r_casing"] + H["casing_thickness"]),
            "casing_mass_kg": mass_table(asm)["parts"]["M2.0.2"]["unit_kg"], "wall_ring_mass_kg": m1_mass["unit_kg"],
            "wall_ring_material": m1_mass["material"]}


# --- common volume over all instances (R-G2.27) ---------------------------------------

def _common(a: cq.Shape, b: cq.Shape) -> float:
    ba, bb = a.BoundingBox(), b.BoundingBox()
    if (ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin
            or ba.zmax < bb.zmin or bb.zmax < ba.zmin):
        return 0.0
    com = a.intersect(b)
    return sum(s.Volume() for s in com.Solids()) if com.Solids() else 0.0


def _x_range(s: cq.Shape) -> tuple[float, float]:
    b = s.BoundingBox()
    return b.xmin, b.xmax


def _envelope(s: cq.Shape) -> cq.Solid:
    """Revolved superset of every rotated instance of s: x over its bounding box, r from 0 to a bound of its largest
    radius (corner of the bounding box in the Y/Z plane)."""
    b = s.BoundingBox()
    r = math.hypot(max(abs(b.ymin), abs(b.ymax)), max(abs(b.zmin), abs(b.zmax))) * (1.0 + 1e-6)
    return L.revolve_closed([(b.xmin, 0.0), (b.xmax, 0.0), (b.xmax, r), (b.xmin, r)])


def _instances(s: cq.Shape, angles: list[float]) -> list[cq.Shape]:
    return [s if a == 0.0 else HW.rotate(s, a) for a in angles]


def pair_common(a: dict, sa: cq.Shape, b: dict, sb: cq.Shape, same: bool = False) -> dict:
    """Largest common volume of any instance pair of solid sa (part a) and solid sb (part b) [H]; same = the two are
    the same solid of the same part (neighbour instances only). Returns method, number of booleans, max volume."""
    (xa0, xa1), (xb0, xb1) = _x_range(sa), _x_range(sb)
    if xa1 < xb0 or xb1 < xa0:
        return {"method": "x_disjoint", "booleans": 0, "max_m3": 0.0}
    if a["axisymmetric"] or b["axisymmetric"]:
        return {"method": "axisymmetric", "booleans": 1, "max_m3": 0.0 if same else _common(sa, sb)}
    n_bool = 0
    for sup, other in ((a["superset"], sb), (b["superset"], sa)):
        if sup is not None:
            n_bool += 1
            if _common(sup, other) == 0.0:
                return {"method": "axisymmetric_superset", "booleans": n_bool, "max_m3": 0.0}
    for p, sp, q, sq in ((a, sa, b, sb), (b, sb, a, sa)):  # q's solid inside one rim of the drum p, same count
        x0, x1 = _x_range(sq)
        for r0, r1, n in p.get("x_symmetry", []):
            if r0 - 1e-6 <= x0 and x1 <= r1 + 1e-6 and len(q["angles"]) == n and len(p["angles"]) == 1:
                return {"method": "rim_symmetry", "booleans": n_bool + 1, "max_m3": _common(sp, sq)}
    if len(a["angles"]) == 1 and len(b["angles"]) == 1:
        return {"method": "single", "booleans": 1, "max_m3": _common(sa, sb)}
    if not same:
        for env, other in ((sa, sb), (sb, sa)):
            n_bool += 1
            if _common(_envelope(env), other) == 0.0:
                return {"method": "envelope", "booleans": n_bool, "max_m3": 0.0}
    # relative angles: same count -> instance 0 of a against every instance of b is exhaustive
    if same or a["angles"] == b["angles"]:
        pairs = [(sa, t) for k, t in enumerate(_instances(sb, b["angles"])) if not (same and k == 0)]
    else:
        ia, ib = _instances(sa, a["angles"]), _instances(sb, b["angles"])
        pairs = [(p, q) for p in ia for q in ib]
    vmax = 0.0
    for p, q in pairs:
        v = _common(p, q)
        n_bool += 1
        vmax = max(vmax, v)
    return {"method": "instances", "booleans": n_bool, "max_m3": vmax}


def _solids(parts: dict) -> list[tuple[str, dict, str, cq.Shape]]:
    return [(pid, p, k, s) for pid, p in parts.items() for k, s in p["solids"].items()]


def common_volume_checks(asm: dict | None = None, with_m1: bool = True) -> dict:
    """R-G2.27: all M2-M2 solid pairs (incl. neighbour instances of the same solid; airfoil and root block of one
    blade are separate solids that touch) and all M2-M1 solid pairs; fraction = max common volume / smaller solid."""
    asm = asm or build()
    tol = float(L.v(asm["hb"]["model"]["params"]["hw_common_volume_tolerance"]))
    m2 = _solids(asm["parts"])
    rows = []

    def add(group, x, y, same=False):
        (pa, a, ka, sa), (pb, b, kb, sb) = x, y
        r = pair_common(a, sa, b, sb, same)
        r["fraction"] = r["max_m3"] / min(sa.Volume(), sb.Volume())
        rows.append({"group": group, "a": f"{pa} {ka}", "b": f"{pb} {kb}", **r, "pass": r["fraction"] <= tol})

    for i, x in enumerate(m2):
        if len(x[1]["angles"]) > 1:
            add("M2-M2", x, x, same=True)
        for y in m2[i + 1:]:
            add("M2-M2", x, y)
    if with_m1:
        for x in m2:
            for y in _solids(m1_parts()):
                add("M2-M1", x, y)
    return {"rows": rows, "tolerance": tol,
            "summary": {g: {"pairs": sum(1 for r in rows if r["group"] == g),
                            "max_fraction": max((r["fraction"] for r in rows if r["group"] == g), default=0.0),
                            "max_m3": max((r["max_m3"] for r in rows if r["group"] == g), default=0.0),
                            "fail": [(r["a"], r["b"]) for r in rows if r["group"] == g and not r["pass"]]}
                        for g in ("M2-M2", "M2-M1")}}


# --- record agreement (R-G2.27) ---------------------------------------------------------

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_checks(asm: dict | None = None) -> dict:
    """Blade counts vs the record, annulus areas of the revolved flow path vs the record areas, flowpath.yaml radii vs
    the record radii, and the rev001 params/results files unchanged (sha256 vs the input record manifest) [H]."""
    asm = asm or build()
    lay = asm["hb"]["model"]["layout"]
    rec = L.record(INPUT_REVISION)
    res = rec["results"]
    counts_rec = ([int(L.v(s["rotor_blades"])) for s in res["stages"]],
                  [int(L.v(s["stator_vanes"])) for s in res["stages"]])
    areas = L.area_check(lay)
    fp = L.read_yaml(L.M2_FLOWPATH)
    mine = [(p["r_hub_m"], p["r_tip_m"]) for p in fp["planes"]]
    st25 = fp["interfaces"]["M3_station_25"]
    radii_rec = L._results_planes(res) + [(res["station_24"]["r_hub"], res["station_24"]["r_tip"])]
    mine.append((st25["r_hub_m"], st25["r_tip_m"]))
    d_r = max(abs(float(x) - float(y)) for a, b in zip(mine, radii_rec) for x, y in zip(a, b))
    manifest = {o["file"]: o["sha256"] for o in rec["manifest"]["outputs"]}
    unchanged = {f: _sha256(L.M2_DIR / f) == manifest[f] for f in RECORD_FILES}
    return {"rotor_counts": asm["rotor_counts"], "stator_counts": asm["stator_counts"], "counts_record": counts_rec,
            "area_max_rel_dev": max(abs(a["deviation"]) for a in areas), "areas_pass": all(a["pass"] for a in areas),
            "radius_max_abs_dev_m": d_r, "radius_dev_half_digits": L.flowpath_radii_deviation(fp, res),
            "flowpath_check": rec["flowpath_check"], "record_files_unchanged": unchanged}


# --- export -------------------------------------------------------------------------

def step_dir() -> Path:
    return L.CACHE / DESIGN_REVISION


def _export_step(shape: cq.Shape, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(cq.Workplane().add(shape), str(path), exportType="STEP")
    return path


def export(asm: dict | None = None) -> dict:
    """m2_assembly.step (every instance, one shape per part placed by rotation, R-G2.1 sense) and one STEP per part
    in .cache/geometry/M2_booster/rev002/ (R-G2.25)."""
    asm = asm or build()
    d = step_dir()
    paths = {}
    assy = cq.Assembly(name=ASSEMBLY_NAME)
    for pid, p in asm["parts"].items():
        paths[pid] = _export_step(p["shape"], d / f"{pid.replace('.', '_')}_{p['name'].split()[-1].lower()}.step")
        for j, a in enumerate(p["angles"]):
            loc = cq.Location(cq.Vector(*L.AXIS_ORIGIN), cq.Vector(*L.AXIS_DIR), L.ROTATION_SIGN * a)
            assy.add(p["shape"], name=pid if p["qty"] == 1 else f"{pid}_{j:02d}", loc=loc)
    paths["flowpath_reference"] = _export_step(L.flowpath_solid(asm["hb"]["model"]["layout"]),
                                               d / "flowpath_reference.step")
    path = d / f"{ASSEMBLY_NAME}.step"
    d.mkdir(parents=True, exist_ok=True)
    assy.export(str(path), exportType="STEP")
    paths[ASSEMBLY_NAME] = path
    return paths


def main() -> None:
    asm = build()
    m = mass_table(asm)
    for pid, r in m["parts"].items():
        sub = ", ".join(f"{k} {v:.4f}" for k, v in r["sub_kg"].items()) if len(r["sub_kg"]) > 1 else ""
        print(f"  {pid:7s} {r['name']:34s} {r['qty']:3d} x {r['unit_kg']:9.4f} = {r['set_kg']:9.3f} kg "
              f"({r['material']}, rho {r['rho_material']}) {sub}")
    print(f"  total {m['total_kg']:.3f} kg [H]; check value {m['check_value_kg']:.2f} kg [KS weak], "
          f"ratio {m['ratio_to_check']:.3f} (information)")
    print("  station 25", station_25_checks(asm))
    print("  casing boundary", casing_boundary(asm))
    print("  record", record_checks(asm))
    cv = common_volume_checks(asm)
    for g, s in cv["summary"].items():
        print(f"  common volume {g}: {s}")
    methods = {}
    for r in cv["rows"]:
        methods[(r["group"], r["method"])] = methods.get((r["group"], r["method"]), 0) + 1
    print("  methods", methods, "booleans", sum(r["booleans"] for r in cv["rows"]))
    for k, p in export(asm).items():
        print(f"  STEP {k}: {p}")


if __name__ == "__main__":
    main()
