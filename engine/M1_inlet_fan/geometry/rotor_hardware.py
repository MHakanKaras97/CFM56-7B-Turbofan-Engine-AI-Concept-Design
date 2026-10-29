"""M1 fan rotor hardware, step 5c: disk (M1.1.2), shim (M1.1.4), spacer (M1.1.5), platform (M1.1.6) with the
blade root of dovetail.py (M1.1.1). CadQuery, frame.py axes.

Disk: revolved rim / web / bore (rotor_params.yaml disk ratios [T]) with 24 slots (dovetail.slot_cutter turned by
the pitch). Platform: aluminium plate under the hub line with front and rear walls down to the rim (clearance), one
per blade gap, cut free of the shanks by the clearance. Analytic disk check [G]: analysis/disk_stress.py with the
rim dead load of blades + shims + spacers + platforms + disk lugs at N1 (ICD LP speed, Girão nominal [KS]);
allowable = yield / safety factor and margin rule of R-AM.13/15 (record params), same Ti-6Al-4V values as the blade.
"""

import math
from functools import lru_cache
from pathlib import Path

import cadquery as cq
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

from core import records
from core.budgets import read_icd
from core.util import read_yaml
from engine.M1_inlet_fan.analysis import disk_stress
from engine.M1_inlet_fan.geometry import dovetail as dv
from engine.M1_inlet_fan.geometry import frame as fr

MATERIALS = fr.ROOT / "tools" / "data" / "materials.yaml"


def densities() -> dict:
    """kg/m3 per material id; tools/data/materials.yaml first, rotor_params.yaml fallback [T] where it has none."""
    mats = read_yaml(MATERIALS)["materials"]
    fb = dv.rotor_params()["materials_fallback"]
    out = {}
    for mid, key in (("ti6al4v", None), ("alloy718", "alloy718_density"), ("aluminium_alloy", "aluminium_alloy_density")):
        if "density" in mats.get(mid, {}):
            out[mid] = {"value": fr.v(mats[mid]["density"]), "tag": mats[mid]["density"].get("tag"), "from": "materials.yaml"}
        else:
            out[mid] = {"value": fr.v(fb[key]), "tag": fb[key]["tag"], "from": "rotor_params.yaml fallback"}
    return out


def disk_profile(L: dict) -> dict:
    """Meridional rim / web / bore sizes [H from T ratios]."""
    g = dv.rotor_params()["disk"]
    W = L["x_b"] - L["x_a"]
    x_m = (L["x_a"] + L["x_b"]) / 2
    r_ri = L["r_slot_bottom"] - fr.v(g["rim_depth_below_slot_over_neck"]) * L["b_n"]
    t_w = fr.v(g["web_thickness_over_rim_width"]) * W
    w_b = fr.v(g["bore_width_over_rim_width"]) * W
    r_bi = fr.v(g["bore_inner_radius_over_rim_radius"]) * L["r_rim"]
    r_bo = r_bi + fr.v(g["bore_height_over_bore_width"]) * w_b
    if not r_bi < r_bo < r_ri < L["r_slot_bottom"]:
        raise ValueError("disk radii out of order (bore, web, rim, slot bottom)")
    pts = [(L["x_a"], r_ri), (L["x_a"], L["r_rim"]), (L["x_b"], L["r_rim"]), (L["x_b"], r_ri),
           (x_m + t_w / 2, r_ri), (x_m + t_w / 2, r_bo), (x_m + w_b / 2, r_bo), (x_m + w_b / 2, r_bi),
           (x_m - w_b / 2, r_bi), (x_m - w_b / 2, r_bo), (x_m - t_w / 2, r_bo), (x_m - t_w / 2, r_ri)]
    return {"W": W, "x_mid": x_m, "r_rim_inner": r_ri, "t_web": t_w, "w_bore": w_b, "r_bore_in": r_bi,
            "r_bore_out": r_bo, "points": pts}


def disk(L: dict, slot: cq.Solid, n: int) -> tuple[cq.Solid, dict]:
    prof = disk_profile(L)
    body = fr.revolve_closed(prof["points"])
    slots = cq.Compound.makeCompound([slot if k == 0 else fr.rotate_about_axis(slot, k * 360.0 / n) for k in range(n)])
    cut = body.cut(slots).Solids()
    if len(cut) != 1 or not cut[0].isValid():
        raise ValueError(f"slotted disk: {len(cut)} solids, expected one valid solid")
    return cut[0], prof


def platform(fp: dict, L: dict, slot: cq.Solid, n: int) -> cq.Solid:
    """Platform in the gap between blade 0 and blade 1 (turned +1 pitch). Cut free of the blades by the slot
    cutters (dovetail + shim + clearance): with the planar slot section the dovetail shoulders rise above r_rim
    towards the slab ends, so a shank-only cut would leave the platform touching them."""
    e = fp["rotor_edges"]
    hub = [e["le_hub"], e["te_hub"]]
    xa, xb, t, c = L["x_a"], L["x_b"], L["t_p"], L["c"]
    r0 = L["r_rim"] + c
    h = lambda x: fr.r_at(hub, x)  # noqa: E731
    pts = [(xa, h(xa)), (xb, h(xb)), (xb, r0), (xb - t, r0), (xb - t, h(xb - t) - t), (xa + t, h(xa + t) - t),
           (xa + t, r0), (xa, r0)]
    band = fr.revolve_closed(pts)
    shanks = cq.Compound.makeCompound([slot if k == 0 else fr.rotate_about_axis(slot, k * 360.0 / n) for k in range(n)])
    pieces = band.cut(shanks).Solids()
    a = math.radians(180.0 / n)  # mid-gap at x = 0, rotor sense
    r = h(0.0) - t / 2
    probe = cq.Vector(0.0, -r * math.sin(a) * fr.ROTATION_SIGN, r * math.cos(a))
    hit = [s for s in pieces if s.isInside(probe)]
    if len(hit) != 1:
        raise ValueError("platform piece between blade 0 and blade 1 not found")
    return hit[0]


def lug_ring(disk_solid: cq.Solid, L: dict) -> cq.Solid:
    """Slotted rim above the slot-bottom radius (the 24 lugs and the material under the slot ends): dead load."""
    ring = fr.revolve_closed([(L["x_a"] - 0.01, L["r_slot_bottom"]), (L["x_a"] - 0.01, L["r_rim"] + 0.01),
                              (L["x_b"] + 0.01, L["r_rim"] + 0.01), (L["x_b"] + 0.01, L["r_slot_bottom"])])
    return max(fr.boolean("common", disk_solid, ring).Solids(), key=lambda s: s.Volume())


def ring_pull_per_slot(solid: cq.Solid, rho: float, omega: float, n: int) -> dict:
    """Centrifugal pull of an n-fold symmetric ring per slot: rho omega^2 int r dV / n, with
    int r dV ~ sqrt(V int r^2 dV) (exact for a thin ring; the slotted rim spans 0.20-0.23 m) [H]."""
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(solid.wrapped, props)
    vol = props.Mass()
    c = props.CentreOfMass()
    i_axis = props.MatrixOfInertia().Value(1, 1) + vol * (c.Y() ** 2 + c.Z() ** 2)
    r_eff = math.sqrt(i_axis / vol)
    return {"mass_kg": rho * vol / n, "r_cg_m": r_eff, "pull_N": rho * omega ** 2 * math.sqrt(vol * i_axis) / n}


def pull(solid: cq.Solid, rho: float, omega: float) -> dict:
    """Centrifugal pull of a part: m omega^2 r_cg (r_cg = distance of the centre of mass from the axis) [H]."""
    m = solid.Volume() * rho
    r = fr.radius(solid.Center())
    return {"mass_kg": m, "r_cg_m": r, "pull_N": m * omega ** 2 * r}


@lru_cache(maxsize=2)
def build(rev: str | None = None, root: Path = records.ROOT) -> dict:
    root_model = dv.build(rev, root)
    fp, L = root_model["flowpath"], root_model["layout"]
    n = fp["blade"]["inputs"]["blades"]
    d, prof = disk(L, root_model["slot"], n)
    return dict(root_model, disk=d, disk_profile=prof, platform=platform(fp, L, root_model["slot"], n), lug=lug_ring(d, L), n=n)


def stress(model: dict) -> dict:
    """Analytic disk check at N1 [G method, H values]."""
    fp, L, prof, n = model["flowpath"], model["layout"], model["disk_profile"], model["n"]
    rec = fr.record(fp["revision"])
    mech = rec["params"]["mechanical"]
    ti = read_yaml(MATERIALS)["materials"]["ti6al4v"]
    rho_d = densities()
    rpm = fr.v(read_icd("M1 agent")["shafts"]["LP"]["speed_refs"]["girao_nominal"])
    omega = rpm * 2 * math.pi / 60
    parts = {"blade": ("blade", "ti6al4v"), "shim": ("shim", "alloy718"), "spacer": ("spacer", "ti6al4v"),
             "platform": ("platform", "aluminium_alloy")}
    loads = {k: pull(model[s], rho_d[m]["value"], omega) for k, (s, m) in parts.items()}
    loads["lug"] = ring_pull_per_slot(model["lug"], rho_d["ti6al4v"]["value"], omega, n)
    per_slot = sum(x["pull_N"] for x in loads.values())
    F = per_slot * n
    segs = [(prof["r_bore_in"], prof["r_bore_out"], prof["w_bore"]), (prof["r_bore_out"], prof["r_rim_inner"], prof["t_web"]),
            (prof["r_rim_inner"], L["r_slot_bottom"], prof["W"])]
    E, nu, rho = fr.v(ti["youngs_modulus"]) * 1e9, fr.v(ti["poissons_ratio"]), rho_d["ti6al4v"]["value"]
    sigma_rim = F / (2 * math.pi * L["r_slot_bottom"] * prof["W"])
    sol = disk_stress.solve(segs, rho, omega, E, nu, sigma_rim)
    allowable = fr.v(ti["yield_strength"]) * 1e6 / fr.v(mech["safety_factor"])
    m_min = fr.v(mech["stress_margin_min"])
    peak = sol["peak"]
    margin = allowable / peak["von_mises"] - 1
    # local root checks [G]: blade neck tension and lug tension at the lobe level (average stress)
    length = (L["x_b"] - L["x_a"]) / math.cos(L["gamma"])
    pitch_n = 2 * math.pi * L["z2"] / n * math.cos(L["gamma"])
    lug_w = pitch_n - (L["b_l"] + 2 * (L["t_sh"] + L["c"]))
    blade_side = loads["blade"]["pull_N"] + loads["shim"]["pull_N"] + loads["platform"]["pull_N"]
    neck = blade_side / (L["b_n"] * length)
    lug_s = blade_side / (lug_w * length) if lug_w > 0 else math.inf
    return {
        "rpm": rpm, "omega_rad_s": omega, "loads_per_slot": loads, "rim_load_total_N": F,
        "sigma_rim_MPa": sigma_rim / 1e6, "segments": segs,
        "bore": {k: sol["bore"][k] / 1e6 for k in ("sigma_r", "sigma_t", "von_mises")},
        "peak": {"r_m": peak["r"], "segment": peak["segment"], "von_mises_MPa": peak["von_mises"] / 1e6,
                 "sigma_t_MPa": peak["sigma_t"] / 1e6, "sigma_r_MPa": peak["sigma_r"] / 1e6},
        "mean_hoop_MPa": disk_stress.mean_hoop_stress(segs, rho, omega, F) / 1e6,
        "allowable_MPa": allowable / 1e6, "margin": margin, "margin_min": m_min,
        "check": "pass" if margin >= m_min else "fail",
        "neck": {"stress_MPa": neck / 1e6, "margin": allowable / neck - 1},
        "lug": {"width_at_lobe_m": lug_w, "stress_MPa": lug_s / 1e6,
                "margin": allowable / lug_s - 1 if lug_w > 0 else -1.0},
    }


def masses(model: dict) -> dict:
    rho = densities()
    items = {"M1.1.1 blade with root": ("blade", "ti6al4v", model["n"]), "M1.1.2 disk": ("disk", "ti6al4v", 1),
             "M1.1.4 shim": ("shim", "alloy718", model["n"]), "M1.1.5 spacer": ("spacer", "ti6al4v", model["n"]),
             "M1.1.6 platform": ("platform", "aluminium_alloy", model["n"])}
    out = {}
    for name, (key, mid, qty) in items.items():
        vol = model[key].Volume()
        out[name] = {"volume_m3": vol, "density": rho[mid]["value"], "density_tag": rho[mid]["tag"],
                     "mass_kg": vol * rho[mid]["value"], "qty": qty, "set_kg": vol * rho[mid]["value"] * qty}
    return out


def interference(model: dict) -> dict:
    """Slot 0 pairs (and the platform with both neighbouring blade roots): common volume and shortest distance [H].
    By the rotational symmetry of the ring every slot has the same result. The airfoils lie above the hub line
    (radius >= r_hub1) and every rotor hardware part below it, so they are checked through the root part only."""
    n = model["n"]
    root1 = fr.rotate_about_axis(model["root"], 360.0 / n)
    plat_1 = fr.rotate_about_axis(model["platform"], 360.0 / n)
    pairs = {"root-disk": ("root", "disk"), "shim-disk": ("shim", "disk"), "spacer-disk": ("spacer", "disk"),
             "spacer-shim": ("spacer", "shim"), "spacer-root": ("spacer", "root"), "shim-root": ("shim", "root"),
             "platform-disk": ("platform", "disk"), "platform-root0": ("platform", "root"),
             "platform-root1": ("platform", root1), "platform-platform1": ("platform", plat_1)}
    out = {}
    for name, (a, b) in pairs.items():
        sa = model[a]
        sb = model[b] if isinstance(b, str) else b
        out[name] = {"common_volume_m3": fr.boolean("common", sa, sb).Volume(), "distance_m": sa.distance(sb)}
    return out


def export(model: dict) -> dict:
    rev, n = model["flowpath"]["revision"], model["n"]
    parts = {"fan_blade_with_root": model["blade"], "fan_disk": model["disk"], "dovetail_shim": model["shim"],
             "blade_spacer": model["spacer"], "blade_platform": model["platform"]}
    paths = {k: fr.export_step(s, k, rev) for k, s in parts.items()}
    inst = [("M1.1.2", model["disk"], 0.0)]
    for k in range(n):
        a = k * 360.0 / n
        inst += [(f"M1.1.1_{k:02d}", model["blade"], a), (f"M1.1.4_{k:02d}", model["shim"], a),
                 (f"M1.1.5_{k:02d}", model["spacer"], a), (f"M1.1.6_{k:02d}", model["platform"], a)]
    paths["fan_rotor_assembly"] = fr.export_assembly(inst, "fan_rotor_assembly", rev)
    return paths


def main() -> None:
    model = build()
    L = model["layout"]
    print(f"{model['flowpath']['revision']}: slot angle {math.degrees(L['gamma']):.2f} deg, footprint "
          f"{L['footprint'] * 1e3:.2f} mm, neck {L['b_n'] * 1e3:.2f} mm, lobe {L['b_l'] * 1e3:.2f} mm, "
          f"r_rim {L['r_rim']:.5f}, slot bottom {L['r_slot_bottom']:.5f} m")
    for k, row in masses(model).items():
        print(f"  {k}: {row['mass_kg']:.4f} kg x {row['qty']} = {row['set_kg']:.3f} kg ({row['density_tag']})")
    s = stress(model)
    print(f"  N1 {s['rpm']} rpm, rim load {s['rim_load_total_N'] / 1e6:.3f} MN, sigma_rim {s['sigma_rim_MPa']:.1f} MPa")
    print(f"  bore sigma_t {s['bore']['sigma_t']:.1f} MPa, peak VM {s['peak']['von_mises_MPa']:.1f} MPa at r "
          f"{s['peak']['r_m']:.4f}, mean hoop {s['mean_hoop_MPa']:.1f} MPa, allowable {s['allowable_MPa']:.1f}, "
          f"margin {s['margin']:.3f} ({s['check']})")
    print(f"  neck {s['neck']['stress_MPa']:.1f} MPa margin {s['neck']['margin']:.3f}; lug width "
          f"{s['lug']['width_at_lobe_m'] * 1e3:.2f} mm, {s['lug']['stress_MPa']:.1f} MPa margin {s['lug']['margin']:.3f}")
    for k, row in interference(model).items():
        print(f"  {k}: common {row['common_volume_m3']:.2e} m3, distance {row['distance_m'] * 1e3:.3f} mm")
    for k, p in export(model).items():
        print(f"  STEP {k}: {p.name}")


if __name__ == "__main__":
    main()
