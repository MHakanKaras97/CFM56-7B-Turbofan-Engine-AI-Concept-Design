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


def disk_profile(L: dict, step: int = 0) -> dict:
    """Meridional rim / web / bore sizes [H from T ratios] after `step` growth steps of R-DISK.1 (rules/disk.md):
    bore width, bore height and web thickness = initial x (1 + step_fraction x step), each capped by its envelope
    (bore width <= rim width; web thickness <= bore width; bore outer radius <= live-rim inner radius - minimum web
    height). Fixed: slots, slot bottom, live rim (depth, width), bore inner radius, disk axial centre."""
    g = dv.rotor_params()["disk"]
    sz = dv.rotor_params()["disk_sizing"]
    W = L["x_b"] - L["x_a"]
    x_m = (L["x_a"] + L["x_b"]) / 2
    r_ri = L["r_slot_bottom"] - fr.v(g["rim_depth_below_slot_over_neck"]) * L["b_n"]
    r_bi = fr.v(g["bore_inner_radius_over_rim_radius"]) * L["r_rim"]
    t_w0 = fr.v(g["web_thickness_over_rim_width"]) * W
    w_b0 = fr.v(g["bore_width_over_rim_width"]) * W
    h_b0 = fr.v(g["bore_height_over_bore_width"]) * w_b0
    h_max = r_ri - fr.v(sz["web_height_min_over_neck"]) * L["b_n"] - r_bi
    f = 1 + fr.v(sz["step_fraction"]) * step
    w_b = min(W, w_b0 * f)
    h_b = min(h_max, h_b0 * f)
    t_w = min(w_b, t_w0 * f)
    caps = {"bore_width": w_b >= W, "bore_height": h_b >= h_max, "web_thickness": t_w >= w_b}
    r_bo = r_bi + h_b
    if not r_bi < r_bo < r_ri < L["r_slot_bottom"]:
        raise ValueError("disk radii out of order (bore, web, rim, slot bottom)")
    pts = [(L["x_a"], r_ri), (L["x_a"], L["r_rim"]), (L["x_b"], L["r_rim"]), (L["x_b"], r_ri),
           (x_m + t_w / 2, r_ri), (x_m + t_w / 2, r_bo), (x_m + w_b / 2, r_bo), (x_m + w_b / 2, r_bi),
           (x_m - w_b / 2, r_bi), (x_m - w_b / 2, r_bo), (x_m - t_w / 2, r_bo), (x_m - t_w / 2, r_ri)]
    pts = [q for i, q in enumerate(pts) if q != pts[i - 1]]  # coinciding corners when a variable is capped
    return {"W": W, "x_mid": x_m, "r_rim_inner": r_ri, "t_web": t_w, "w_bore": w_b, "r_bore_in": r_bi,
            "r_bore_out": r_bo, "points": pts, "step": step, "caps": caps, "all_capped": all(caps.values())}


def disk(L: dict, slot: cq.Solid, n: int, step: int = 0) -> tuple[cq.Solid, dict]:
    prof = disk_profile(L, step)
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
    pts = [q for i, q in enumerate(pts) if max(abs(q[0] - pts[i - 1][0]), abs(q[1] - pts[i - 1][1])) > 1e-9]
    band = fr.revolve_closed(pts)  # wall of zero height dropped where the plate already sits on the rim
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


def lug_above(disk_solid: cq.Solid, L: dict, r_from: float) -> cq.Solid:
    """Slotted rim above radius r_from (lug material carried by the lug section at r_from)."""
    ring = fr.revolve_closed([(L["x_a"] - 0.01, r_from), (L["x_a"] - 0.01, L["r_rim"] + 0.01),
                              (L["x_b"] + 0.01, L["r_rim"] + 0.01), (L["x_b"] + 0.01, r_from)])
    return cq.Compound.makeCompound(fr.boolean("common", disk_solid, ring).Solids())


def root_modes(L: dict, inp: dict, n: int) -> dict:
    """R-DISK.2 dovetail / lug modes, closed form, average stresses [G], margin = allowable / sigma_eq - 1 [H].
    F = blade (airfoil + root) + shim + platform pull per slot; each lug carries one blade pull (half of each
    neighbour), plus its own material above the checked section."""
    ld, a = inp["loads"], inp["allowable"]
    F = ld["blade"]["pull_N"] + ld["shim"]["pull_N"] + ld["platform"]["pull_N"]
    length = (L["x_b"] - L["x_a"]) / math.cos(L["gamma"])  # slot length along the slot axis
    g = L["t_sh"] + L["c"]
    pn = 2 * math.pi / n * math.cos(L["gamma"])  # slot pitch normal to the slot axis per unit radius
    w_lobe = pn * L["z2"] - (L["b_l"] + 2 * g)
    w_neck = pn * L["z1"] - (L["b_n"] + 2 * g)
    h_ear = L["r_rim"] - L["z2"]  # ear over the lobe, radial plane at the lobe-max line
    e = (L["b_l"] - L["b_n"]) / 4  # flank load line to the ear root plane
    s = {
        "lug_tension_lobe": (F + ld["lug_above_z2"]["pull_N"]) / (w_lobe * length) if w_lobe > 0 else math.inf,
        "lug_tension_neck": (F + ld["lug_above_z1"]["pull_N"]) / (w_neck * length) if w_neck > 0 else math.inf,
        "flank_bearing": (F / (2 * math.cos(L["alpha"]))) / ((L["b_l"] - L["b_n"]) / 2 / math.cos(L["alpha"]) * length),
        "ear_shear_vm": math.sqrt(3) * (F / 2) / (h_ear * length),
        "ear_bending": (F / 2) * e / (length * h_ear ** 2 / 6),
        "blade_neck_tension": ld["blade"]["pull_N"] / (L["b_n"] * length),
    }
    rows = {k: {"stress_MPa": v / 1e6, "margin": a / v - 1} for k, v in s.items()}
    worst = min(rows, key=lambda k: rows[k]["margin"])
    return {"modes": rows, "governing": worst, "min_margin": rows[worst]["margin"], "F_N": F, "slot_length_m": length,
            "lug_width_lobe_m": w_lobe, "lug_width_neck_m": w_neck, "ear_height_m": h_ear,
            "pass": rows[worst]["margin"] >= inp["margin_min"]}


def _slab_state(rev, root, k: int) -> dict:
    """Rotor parts at slab step k (disk at R-DISK.1 step 0), loads and root modes."""
    P = dv.parts(rev, root, k)
    fp, L = P["flowpath"], P["layout"]
    n = fp["blade"]["inputs"]["blades"]
    d0, prof0 = disk(L, P["slot"], n, 0)
    m = dict(P, blade=cq.Compound.makeCompound([P["airfoil"], P["root"]]), disk=d0, disk_profile=prof0,
             platform=platform(fp, L, P["slot"], n), lug=lug_ring(d0, L), n=n)
    m["lug_z1"], m["lug_z2"] = lug_above(d0, L, L["z1"]), lug_above(d0, L, L["z2"])
    inp = _inputs(m)
    return {"model": m, "inputs": inp, "modes": root_modes(L, inp, n)}


@lru_cache(maxsize=2)
def build(rev: str | None = None, root: Path = records.ROOT) -> dict:
    """Rotor hardware. R-DISK.2: slab step k = 0, 1, ... until every root mode passes (rules/disk.md); then the
    disk web and bore by R-DISK.1 with the loads of that slab (the rim dead loads do not depend on web and bore)."""
    k_max = int(_p_dv("slab_max_steps"))
    history = []
    for k in range(k_max + 1):
        st = _slab_state(rev, root, k)
        history.append({"step": k, "slab_m": st["model"]["layout"]["x_b"] - st["model"]["layout"]["x_a"],
                        "min_margin": st["modes"]["min_margin"], "governing": st["modes"]["governing"],
                        "modes": {a: b["margin"] for a, b in st["modes"]["modes"].items()}})
        if st["modes"]["pass"]:
            break
    slab = {"step": k, "result": "pass" if st["modes"]["pass"] else "not_converged", "history": history}
    root_model = dv.build(rev, root, k)
    fp, L = root_model["flowpath"], root_model["layout"]
    n = fp["blade"]["inputs"]["blades"]
    sm = st["model"]
    model = dict(root_model, disk=sm["disk"], disk_profile=sm["disk_profile"], platform=sm["platform"], lug=sm["lug"],
                 lug_z1=sm["lug_z1"], lug_z2=sm["lug_z2"], n=n, slab_sizing=slab)
    sizing = size_disk(L, _inputs(model))
    d, prof = disk(L, root_model["slot"], n, sizing["step"])
    model.update(disk=d, disk_profile=prof, disk_initial=sm["disk"], disk_profile_initial=sm["disk_profile"],
                 disk_sizing=sizing)
    return model


def _p_dv(key):
    return fr.v(dv.rotor_params()["dovetail"][key])


def _inputs(model: dict) -> dict:
    """Speed, material values, allowable and the rim dead load (blade, shim, spacer, platform, lug per slot) [H]."""
    fp, n = model["flowpath"], model["n"]
    mech = fr.record(fp["revision"])["params"]["mechanical"]
    ti = read_yaml(MATERIALS)["materials"]["ti6al4v"]
    rho_d = densities()
    rpm = fr.v(read_icd("M1 agent")["shafts"]["LP"]["speed_refs"]["girao_nominal"])
    omega = rpm * 2 * math.pi / 60
    parts = {"blade": ("blade", "ti6al4v"), "shim": ("shim", "alloy718"), "spacer": ("spacer", "ti6al4v"),
             "platform": ("platform", "aluminium_alloy")}
    loads = {k: pull(model[s], rho_d[m]["value"], omega) for k, (s, m) in parts.items()}
    loads["lug"] = ring_pull_per_slot(model["lug"], rho_d["ti6al4v"]["value"], omega, n)
    F = sum(x["pull_N"] for x in loads.values()) * n  # rim dead load
    for z in ("z1", "z2"):  # lug material above the R-DISK.2 sections (not added to the rim load again)
        if f"lug_{z}" in model:
            loads[f"lug_above_{z}"] = ring_pull_per_slot(model[f"lug_{z}"], rho_d["ti6al4v"]["value"], omega, n)
    return {"rpm": rpm, "omega": omega, "loads": loads, "F": F,
            "E": fr.v(ti["youngs_modulus"]) * 1e9, "nu": fr.v(ti["poissons_ratio"]), "rho": rho_d["ti6al4v"]["value"],
            "allowable": fr.v(ti["yield_strength"]) * 1e6 / fr.v(mech["safety_factor"]),
            "margin_min": fr.v(mech["stress_margin_min"])}


def solve_profile(prof: dict, L: dict, inp: dict) -> dict:
    """Stepped-disk solution of a profile; margin = allowable / largest von Mises over all sections - 1 [H]."""
    segs = [(prof["r_bore_in"], prof["r_bore_out"], prof["w_bore"]),
            (prof["r_bore_out"], prof["r_rim_inner"], prof["t_web"]),
            (prof["r_rim_inner"], L["r_slot_bottom"], prof["W"])]
    sigma_rim = inp["F"] / (2 * math.pi * L["r_slot_bottom"] * prof["W"])
    sol = disk_stress.solve(segs, inp["rho"], inp["omega"], inp["E"], inp["nu"], sigma_rim)
    return {"segments": segs, "sigma_rim": sigma_rim, "sol": sol,
            "margin": inp["allowable"] / sol["peak"]["von_mises"] - 1}


def size_disk(L: dict, inp: dict) -> dict:
    """R-DISK.1 (rules/disk.md): steps 0, 1, 2, ...; stop at the first step with margin >= margin_min over all
    sections, or at the first step where every growth variable is at its envelope cap (rule not met)."""
    history = []
    for step in range(int(fr.v(dv.rotor_params()["disk_sizing"]["max_steps"])) + 1):
        prof = disk_profile(L, step)
        m = solve_profile(prof, L, inp)["margin"]
        history.append({"step": step, "margin": m, "w_bore": prof["w_bore"],
                        "h_bore": prof["r_bore_out"] - prof["r_bore_in"], "t_web": prof["t_web"],
                        "caps": dict(prof["caps"])})
        if m >= inp["margin_min"]:
            return {"step": step, "result": "pass", "history": history}
        if prof["all_capped"]:
            return {"step": step, "result": "envelope", "history": history,
                    "binding": "bore width = rim width, bore height at the minimum web height, web = bore width"}
    return {"step": step, "result": "max_steps", "history": history}


def stress(model: dict) -> dict:
    """Analytic disk check at N1 [G method, H values] of the sized disk."""
    L, prof, n = model["layout"], model["disk_profile"], model["n"]
    inp = _inputs(model)
    rpm, omega, loads, F = inp["rpm"], inp["omega"], inp["loads"], inp["F"]
    sp = solve_profile(prof, L, inp)
    segs, sigma_rim, sol, margin = sp["segments"], sp["sigma_rim"], sp["sol"], sp["margin"]
    rho, allowable, m_min = inp["rho"], inp["allowable"], inp["margin_min"]
    peak = sol["peak"]
    rm = root_modes(L, inp, n)
    return {
        "rpm": rpm, "omega_rad_s": omega, "loads_per_slot": loads, "rim_load_total_N": F,
        "sigma_rim_MPa": sigma_rim / 1e6, "segments": segs,
        "bore": {k: sol["bore"][k] / 1e6 for k in ("sigma_r", "sigma_t", "von_mises")},
        "peak": {"r_m": peak["r"], "segment": peak["segment"], "von_mises_MPa": peak["von_mises"] / 1e6,
                 "sigma_t_MPa": peak["sigma_t"] / 1e6, "sigma_r_MPa": peak["sigma_r"] / 1e6},
        "mean_hoop_MPa": disk_stress.mean_hoop_stress(segs, rho, omega, F) / 1e6,
        "allowable_MPa": allowable / 1e6, "margin": margin, "margin_min": m_min,
        "check": "pass" if margin >= m_min else "fail", "sizing": model.get("disk_sizing"),
        "root_modes": rm, "slab_sizing": model.get("slab_sizing"),
        "neck": dict(rm["modes"]["blade_neck_tension"]),
        "lug": dict(rm["modes"]["lug_tension_lobe"], width_at_lobe_m=rm["lug_width_lobe_m"]),
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
