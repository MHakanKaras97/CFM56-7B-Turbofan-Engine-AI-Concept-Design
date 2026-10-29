"""M1 outlet guide vane row (M1.3), step 5e. CadQuery, frame.py axes.

Inputs: rev011 outer (bypass) tubes at the rotor exit (r2, Vt2, Vm2), the 5b flowpath (OGV placeholder x_ogv_le,
station 13, splitter radius, casing wall), ogv_params.yaml rules [T]/[G].
Per section (radius r): inlet flow angle alpha1 = atan(Vt2 / Vm2) at r (record tubes, interpolated in r2) [H];
metal kappa1 = alpha1 - incidence; exit metal kappa2 from Carter's rule for an axial exit [G]; chord from the axial
extent and the stagger; profile = R-AM.11 MCA family (blade_solid.section_points, front 0.5) [T].
The rotor turns positively about +X, so its exit swirl points to -Y at top dead centre: the vane sections are the
blade_solid construction mirrored in Y. Planar sections at constant z, leading edge stacked on x_ogv_le, y = 0
(radial leading edge) [T], lofted, trimmed to the bypass annulus (splitter wall to casing wall).
Row: V = ceil(rule x blade count) copies about +X [T] (open issue #14, count not verified).
"""

import math
from functools import lru_cache
from pathlib import Path

import cadquery as cq
import numpy as np

from core import records
from core.util import read_yaml
from engine.M1_inlet_fan.geometry import blade_solid as bs
from engine.M1_inlet_fan.geometry import fan_ring as ring
from engine.M1_inlet_fan.geometry import frame as fr
from engine.M1_inlet_fan.geometry import rotor_hardware as rh
from engine.M1_inlet_fan.geometry import spinner_case as sc

PARAMS = fr.HERE / "ogv_params.yaml"


def ogv_params() -> dict:
    return read_yaml(PARAMS)


def _p(key):
    return fr.v(ogv_params()[key])


def inlet_angles(res: dict) -> list[dict]:
    """OGV inlet flow angle per outer tube at its rotor-exit radius [H]."""
    out = []
    for t in res["tubes"]:
        if t["stream"] == "outer":
            out.append({"tube": t["name"], "r_m": t["r2_m"], "Vt_m_s": t["Vt2_m_s"], "Vm_m_s": t["Vm2_m_s"],
                        "alpha1_deg": math.degrees(math.atan2(t["Vt2_m_s"], t["Vm2_m_s"]))})
    return out


def alpha_at(tubes: list[dict], r: float) -> float:
    rs = [t["r_m"] for t in tubes]
    return math.radians(float(np.interp(r, rs, [t["alpha1_deg"] for t in tubes])))


def section(r: float, alpha1: float, L_ax: float, V: int) -> dict:
    """Section dict for blade_solid.section_points (unmirrored), Carter deviation for the exit flow angle [G]."""
    k1 = alpha1 - math.radians(_p("incidence"))
    a2 = math.radians(_p("exit_flow_angle"))
    s = {"kappa1": k1, "kappa2": a2, "front": _p("camber_front_share"), "x_max": _p("x_max"),
         "tc": _p("thickness_to_chord"), "chord": L_ax, "r": r}
    for _ in range(30):
        gamma = bs.chord_angle(s)
        chord = L_ax / math.cos(gamma)
        sigma = V * chord / (2 * math.pi * r)
        m = 0.23 + 0.1 * (math.degrees(gamma) / 50.0)
        delta = m * (k1 - s["kappa2"]) / math.sqrt(sigma)
        k2 = a2 - delta
        done = abs(k2 - s["kappa2"]) < 1e-10 and abs(chord - s["chord"]) < 1e-12
        s.update(kappa2=k2, chord=chord)
        if done:
            break
    s.update(gamma=gamma, sigma=sigma, m=m, delta=delta, alpha1=alpha1, alpha2=a2)
    return s


def section_wire(s: dict, x_le: float) -> cq.Wire:
    p = bs.section_points(s)

    def vec(q):
        return cq.Vector(x_le + q[0], -q[1], s["r"])  # mirrored in Y (rotor sense, see module docstring)

    up = cq.Edge.makeSpline([vec(q) for q in p["upper"]])
    lo = cq.Edge.makeSpline([vec(q) for q in p["lower"]])
    return cq.Wire.assembleEdges([up, lo])


def diffusion_factor(s: dict, Vm: float) -> float:
    """Lieblein DF with equal inlet and exit Vm and axial exit [G] (information)."""
    v1 = Vm / math.cos(s["alpha1"])
    v2 = Vm / math.cos(s["alpha2"])
    dvt = Vm * (math.tan(s["alpha1"]) - math.tan(s["alpha2"]))
    return 1 - v2 / v1 + abs(dvt) / (2 * s["sigma"] * v1)


@lru_cache(maxsize=2)
def build(rev: str | None = None, root: Path = records.ROOT) -> dict:
    fp = sc.build(rev, root)["rotor"]["flowpath"]
    res = fr.record(fp["revision"])["results"]
    tubes = inlet_angles(res)
    V = math.ceil(_p("vane_count_rule") * fp["blade"]["inputs"]["blades"])
    x_le, x13 = fp["x_ogv_le_m"], fp["stations"]["13"]["x_m"]
    L_ax = x13 - x_le
    r_in = fp["r_split2_m"]
    r_out = fr.r_at(fp["curves"]["casing_wall"], x_le)
    if abs(fr.r_at(fp["curves"]["casing_wall"], x13) - r_out) > 1e-12:
        raise ValueError("casing wall is not constant over the OGV")
    n = int(_p("n_sections"))
    ext = 0.05 * (r_out - r_in)
    zs = np.linspace(r_in - ext, r_out + ext, n)
    secs = [section(float(z), alpha_at(tubes, float(z)), L_ax, V) for z in zs]
    raw = cq.Solid.makeLoft([section_wire(s, x_le) for s in secs], ruled=False)
    tool = fr.revolve_closed([(x_le - 0.05, r_in), (x_le - 0.05, r_out), (x13 + 0.05, r_out), (x13 + 0.05, r_in)])
    cut = fr.boolean("common", raw, tool).Solids()
    if len(cut) != 1 or not cut[0].isValid():
        raise ValueError(f"OGV vane: {len(cut)} solids, expected one valid solid")
    vane = cut[0]
    per_tube = []
    for t in tubes:
        s = section(t["r_m"], math.radians(t["alpha1_deg"]), L_ax, V)
        per_tube.append({"tube": t["tube"], "r_m": t["r_m"], "alpha1_deg": t["alpha1_deg"],
                         "kappa1_deg": math.degrees(s["kappa1"]), "kappa2_deg": math.degrees(s["kappa2"]),
                         "deviation_deg": math.degrees(s["delta"]), "flow_turning_deg": math.degrees(s["alpha1"] - s["alpha2"]),
                         "camber_deg": math.degrees(s["kappa1"] - s["kappa2"]), "stagger_deg": math.degrees(s["gamma"]),
                         "chord_m": s["chord"], "solidity": s["sigma"], "DF_info": diffusion_factor(s, t["Vm_m_s"])})
    return {"flowpath": fp, "vane": vane, "V": V, "sections": secs, "per_tube": per_tube,
            "x_le": x_le, "x_te": x13, "r_in": r_in, "r_out": r_out}


def row(vane: cq.Solid, V: int) -> list[cq.Solid]:
    return [vane if k == 0 else fr.rotate_about_axis(vane, k * 360.0 / V) for k in range(V)]


def checks(model: dict) -> dict:
    vane, V = model["vane"], model["V"]
    vanes = row(vane, V)
    extent = ring.angular_extent_deg(vane)
    inter = ring.interference(vanes, extent)
    sp = sc.build(model["flowpath"]["revision"])
    others = {"case_shell": sp["case_shell"], "containment_ring": sp["containment_ring"],
              "rotor_blade": sp["rotor"]["blade"]}
    clash = {k: {"common_volume_m3": fr.boolean("common", vane, s).Volume(), "distance_m": vane.distance(s)}
             for k, s in others.items()}
    vs = [fr.radius(p.Center()) for p in vane.Vertices()]
    rho = rh.densities()[fr.v(ogv_params()["material"])]
    vol = vane.Volume()
    return {"vane_count": V, "valid": vane.isValid(), "volume_m3": vol, "mass_kg": vol * rho["value"],
            "row_mass_kg": vol * rho["value"] * V, "density": rho["value"], "density_tag": rho["tag"],
            "angular_extent_deg": extent, "pitch_deg": 360.0 / V, "interference": inter, "clash": clash,
            "r_min_m": min(vs), "r_max_m": max(vs)}


def export(model: dict) -> dict:
    rev, V = model["flowpath"]["revision"], model["V"]
    inst = [(f"M1.3_{k:02d}", model["vane"], k * 360.0 / V) for k in range(V)]
    return {"ogv_vane": fr.export_step(model["vane"], "ogv_vane", rev),
            "ogv_row": fr.export_assembly(inst, "ogv_row", rev)}


def main() -> None:
    model = build()
    c = checks(model)
    print(f"V = {c['vane_count']}, vane {c['mass_kg']:.4f} kg, row {c['row_mass_kg']:.3f} kg ({c['density_tag']}), "
          f"r {c['r_min_m']:.5f}-{c['r_max_m']:.5f}, extent {c['angular_extent_deg']:.2f} deg pitch {c['pitch_deg']:.2f}")
    for t in model["per_tube"]:
        print("  " + ", ".join(f"{k} {v:.4g}" if isinstance(v, float) else f"{k} {v}" for k, v in t.items()))
    print("  interference", {k: (r["method"], r["common_volume_m3"]) for k, r in c["interference"]["pairs"].items()
                             if r["method"] != "bbox_disjoint"})
    for k, r in c["clash"].items():
        print(f"  {k}: common {r['common_volume_m3']:.2e}, distance {r['distance_m'] * 1e3:.3f} mm")
    for k, p in export(model).items():
        print(f"  STEP {k}: {p.name}")


if __name__ == "__main__":
    main()
