"""M1 spinner (M1.1.3), case shell (M1.2.1) and containment ring (M1.2.2), step 5d. CadQuery, frame.py axes.

Spinner: tangent-ogive shell from the nose point on the axis to r_hub1, tangent to the constant-radius hub line,
aft edge one fit clearance ahead of the rotor slab (x_a, platform and dovetail fronts); inward aft flange to the disk
live-rim inner radius, bolted to the disk rim front face (bolts not modelled) [T].
Case shell: inner surface = 5b casing wall (gas-path tip line + running tip clearance 3.0 mm, flowpath.curves
casing_wall), from the front flange (inlet / nacelle attach, not M1) to the rear flange at the OGV leading edge [T].
Containment ring: wrapped on the case outer surface over the blade tip chord with margin; thickness by a
proportional rule [T] (no energy-balance rule in the M1 rules). Blade-off kinetic energy reported for A-8 [H].
Sizes: case_params.yaml. Densities: rotor_hardware.densities (materials.yaml, else [T] fallback).
"""

import math
from functools import lru_cache
from pathlib import Path

import cadquery as cq

from core import records
from core.util import read_yaml
from engine.M1_inlet_fan.geometry import frame as fr
from engine.M1_inlet_fan.geometry import rotor_hardware as rh

PARAMS = fr.HERE / "case_params.yaml"
N_OGIVE = 60  # polyline points on the ogive [T]


def case_params() -> dict:
    return read_yaml(PARAMS)


def _p(group: str, key: str) -> float:
    return fr.v(case_params()[group][key])


def ogive(R: float, L: float, x_nose: float, n: int = N_OGIVE) -> list[tuple[float, float]]:
    """Tangent ogive (x, r) from the nose (r = 0) to the base (r = R, slope 0) [G]."""
    rho = (R * R + L * L) / (2 * R)
    pts = []
    for j in range(n + 1):
        s = L * (1 - math.cos(math.pi * j / (2 * n)))  # denser near the nose
        pts.append((x_nose + s, math.sqrt(max(rho * rho - (L - s) ** 2, 0.0)) + R - rho))
    pts[0], pts[-1] = (x_nose, 0.0), (x_nose + L, R)
    return pts


def spinner(model: dict) -> tuple[cq.Solid, dict]:
    L, prof = model["layout"], model["disk_profile"]
    R = model["flowpath"]["rotor_edges"]["le_hub"][1]
    length = _p("spinner", "length_over_hub_radius") * R
    t = _p("spinner", "shell_thickness_over_hub_radius") * R
    t_f = _p("spinner", "flange_thickness_over_shell") * t
    x_end = L["x_a"] - L["c"]
    x_nose = x_end - length
    outer = ogive(R, length, x_nose)
    r_fl = prof["r_rim_inner"]
    x_fl = x_end - t_f
    inner = [(x, r - t) for x, r in outer if r - t > 0 and x < x_fl]
    rho = (R * R + length * length) / (2 * R)
    r_in_fl = math.sqrt(rho * rho - (length - (x_fl - x_nose)) ** 2) + R - rho - t
    x_in0 = inner[0][0]
    pts = outer + [(x_end, r_fl), (x_fl, r_fl), (x_fl, r_in_fl)] + inner[::-1] + [(x_in0, 0.0)]
    solid = fr.revolve_closed(pts)
    return solid, {"length_m": length, "shell_m": t, "flange_m": t_f, "x_nose_m": x_nose, "x_end_m": x_end,
                   "flange_inner_radius_m": r_fl}


def case_shell(fp: dict) -> tuple[cq.Solid, dict]:
    e = fp["rotor_edges"]
    c_tip = fp["axial_chord_m"]["tip"]
    r_tip = e["le_tip"][1]
    t = _p("case", "shell_thickness_over_tip_radius") * r_tip
    h_f = _p("case", "flange_height_over_shell") * t
    t_f = _p("case", "flange_thickness_over_shell") * t
    x0 = e["le_tip"][0] - _p("case", "front_margin_over_tip_axial_chord") * c_tip
    x1 = fp["x_ogv_le_m"]
    wall = fp["curves"]["casing_wall"]
    xs = sorted({x0, x1, *(x for x, _ in wall if x0 < x < x1)})
    inner = [(x, fr.r_at(wall, x)) for x in xs]
    r0, r1 = inner[0][1], inner[-1][1]
    outer = [(x, r + t) for x, r in inner]
    # flanges: rear flange on [x1 - t_f, x1], front flange on [x0, x0 + t_f]; outer surface between them
    mid = [p for p in outer if x0 + t_f < p[0] < x1 - t_f]
    pts = (inner + [(x1, r1 + t + h_f), (x1 - t_f, r1 + t + h_f), (x1 - t_f, fr.r_at(outer, x1 - t_f))]
           + mid[::-1] + [(x0 + t_f, fr.r_at(outer, x0 + t_f)), (x0 + t_f, r0 + t + h_f), (x0, r0 + t + h_f)])
    solid = fr.revolve_closed(pts)
    return solid, {"thickness_m": t, "x_front_m": x0, "x_rear_m": x1, "flange_height_m": h_f, "flange_m": t_f,
                   "outer_curve": outer}


def containment_ring(fp: dict, case_info: dict) -> tuple[cq.Solid, dict]:
    e = fp["rotor_edges"]
    c_tip = fp["axial_chord_m"]["tip"]
    t = _p("containment", "thickness_over_tip_radius") * e["le_tip"][1]
    m = _p("containment", "axial_margin_over_tip_axial_chord") * c_tip
    x0, x1 = e["le_tip"][0] - m, e["te_tip"][0] + m
    outer_case = case_info["outer_curve"]
    if not (case_info["x_front_m"] + case_info["flange_m"] < x0 and x1 < case_info["x_rear_m"] - case_info["flange_m"]):
        raise ValueError("containment ring does not fit between the case flanges")
    xs = sorted({x0, x1, *(x for x, _ in outer_case if x0 < x < x1)})
    inner = [(x, fr.r_at(outer_case, x)) for x in xs]
    solid = fr.revolve_closed(inner + [(x, r + t) for x, r in inner[::-1]])
    return solid, {"thickness_m": t, "x_front_m": x0, "x_rear_m": x1}


@lru_cache(maxsize=2)
def build(rev: str | None = None, root: Path = records.ROOT) -> dict:
    rotor = rh.build(rev, root)
    fp = rotor["flowpath"]
    sp, sp_info = spinner(rotor)
    cs, cs_info = case_shell(fp)
    cr, cr_info = containment_ring(fp, cs_info)
    return {"rotor": rotor, "spinner": sp, "case_shell": cs, "containment_ring": cr,
            "info": {"spinner": sp_info, "case_shell": {k: v for k, v in cs_info.items() if k != "outer_curve"},
                     "containment_ring": cr_info}}


def masses(model: dict) -> dict:
    rho = rh.densities()
    out = {}
    for name, key, group in (("M1.1.3 spinner", "spinner", "spinner"), ("M1.2.1 case shell", "case_shell", "case"),
                             ("M1.2.2 containment ring", "containment_ring", "containment")):
        mid = fr.v(case_params()[group]["material"])
        vol = model[key].Volume()
        out[name] = {"material": mid, "volume_m3": vol, "density": rho[mid]["value"], "density_tag": rho[mid]["tag"],
                     "mass_kg": vol * rho[mid]["value"]}
    return out


def checks(model: dict) -> dict:
    """Common volume and shortest distance [H]. Spinner, case and ring are axisymmetric, so blade 0, platform 0 and
    slot 0 hardware stand for all slots."""
    r = model["rotor"]
    pairs = {"case-airfoil": ("case_shell", r["airfoil"]), "case-containment": ("case_shell", model["containment_ring"]),
             "spinner-disk": ("spinner", r["disk"]), "spinner-blade": ("spinner", r["blade"]),
             "spinner-platform": ("spinner", r["platform"]), "spinner-shim": ("spinner", r["shim"]),
             "spinner-spacer": ("spinner", r["spacer"])}
    out = {}
    for name, (a, b) in pairs.items():
        sa = model[a]
        out[name] = {"common_volume_m3": fr.boolean("common", sa, b).Volume(), "distance_m": sa.distance(b)}
    return out


def blade_off_energy(model: dict) -> dict:
    """Kinetic energy of a released blade (airfoil + root, released whole) at N1, translational about the axis
    speed of its centre of mass, for A-8 [H, information; no containment check]."""
    s = rh.stress(model["rotor"])
    b = s["loads_per_slot"]["blade"]
    v = s["omega_rad_s"] * b["r_cg_m"]
    return {"mass_kg": b["mass_kg"], "r_cg_m": b["r_cg_m"], "speed_m_s": v, "energy_kJ": 0.5 * b["mass_kg"] * v * v / 1e3}


def export(model: dict) -> dict:
    rev = model["rotor"]["flowpath"]["revision"]
    return {k: fr.export_step(model[k], k, rev) for k in ("spinner", "case_shell", "containment_ring")}


def main() -> None:
    model = build()
    for k, info in model["info"].items():
        print(k, {a: round(b, 5) for a, b in info.items()})
    for k, row in masses(model).items():
        print(f"  {k}: {row['mass_kg']:.3f} kg ({row['material']}, {row['density_tag']})")
    for k, row in checks(model).items():
        print(f"  {k}: common {row['common_volume_m3']:.2e} m3, distance {row['distance_m'] * 1e3:.3f} mm")
    print("  blade-off", {a: round(b, 3) for a, b in blade_off_energy(model).items()})
    for k, p in export(model).items():
        print(f"  STEP {k}: {p.name}")


if __name__ == "__main__":
    main()
