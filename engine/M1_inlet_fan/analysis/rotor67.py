"""NASA Rotor 67 validation case for the M1 streamline code (tools/meanline.py), analysis A-1.

Inputs, all from learning/ [KS] unless noted:
- design streamlines: Table IV radii and stream-tube areas at survey stations 1 and 2 (rotor_reference.yaml);
  the rotor inlet and exit of each tube are taken at these stations [T].
- blade metal angles at the leading and trailing edge per section (rotor67_geometry.yaml); only values
  that passed the plausibility checks are used, interpolated linearly in section number. Section k sits
  at span fraction (k - 1) / 13 between hub (1) and casing (14) [T, LE radii are evenly spaced].
- solidity: hub 3.11 and tip 1.29 (Strazisar p. 2), linear in span fraction [T].
- covered-passage entrance at meridional distance pitch x sin(kappa1) x cos(kappa1) from the leading
  edge, as a fraction of the meridional chord [T]; the camber angle is taken as linear along the chord [T].
- inlet: standard day, Tt 288.15 K, Pt 101325 Pa, no swirl (Table III reference conditions).

Run: python -m engine.M1_inlet_fan.analysis.rotor67  (writes analysis/rotor67_validation.yaml).
"""

import math
from pathlib import Path

from core.util import read_yaml, write_yaml
from tools.meanline import Gas, Tube, mass_averaged, solve_rotor

M1 = Path(__file__).resolve().parents[1]
REFERENCE = M1 / "learning" / "rotor67_reference.yaml"
GEOMETRY = M1 / "learning" / "rotor67_geometry.yaml"
SURVEY = M1 / "learning" / "rotor67_survey.yaml"
OUT = M1 / "analysis" / "rotor67_validation.yaml"

T_REF, P_REF = 288.15, 101325.0  # Table III reference conditions [KS]
N_SECTIONS = 14
CM = 0.01
CM2 = 1e-4

# Acceptance limits [T], rules/analyses.md A-1
LIMITS = {"tip_M1rel_rel": 0.02, "pr_rel": 0.02, "eta_abs": 0.02}


def section_values(geometry: dict, key: str) -> list[tuple[float, float]]:
    """(span fraction, value) of the sections whose `key` passed the plausibility checks."""
    out = []
    for s in geometry["sections"]:
        q = s[key]
        if q["value"] is not None and not q.get("flagged"):
            out.append(((s["section"] - 1) / (N_SECTIONS - 1), q["value"]))
    return out


def interpolate(points: list[tuple[float, float]], f: float) -> float:
    """Linear interpolation in span fraction; linear extrapolation from the two nearest points."""
    pts = sorted(points)
    if f <= pts[0][0]:
        (x0, y0), (x1, y1) = pts[0], pts[1]
    elif f >= pts[-1][0]:
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
    else:
        i = next(i for i in range(len(pts) - 1) if pts[i][0] <= f <= pts[i + 1][0])
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
    return y0 + (y1 - y0) * (f - x0) / (x1 - x0)


def build_tubes(reference: dict | None = None, geometry: dict | None = None) -> list[Tube]:
    ref = reference or read_yaml(REFERENCE)
    geo = geometry or read_yaml(GEOMETRY)
    st1 = ref["survey_stations"]["station_1_upstream"]
    r_hub, r_tip = st1["hub_radius"]["value"], st1["shroud_radius"]["value"]
    blades = ref["design"]["blade_count"]["value"]
    sig_hub, sig_tip = ref["design"]["solidity_hub"]["value"], ref["design"]["solidity_tip"]["value"]
    k1, k2 = section_values(geo, "le_metal_angle"), section_values(geo, "te_metal_angle")
    chord_m = section_values(geo, "meridional_chord")
    tubes = []
    radii, areas = ref["design_streamline_radii"], ref["stream_tube_areas"]
    for j, (r1, r2, A1, A2) in enumerate(zip(radii["station_1"], radii["station_2"],
                                             areas["station_1"], areas["station_2"]), 1):
        f = (r1 - r_hub) / (r_tip - r_hub)
        kappa1, kappa2 = math.radians(interpolate(k1, f)), math.radians(interpolate(k2, f))
        pitch = 2 * math.pi * r1 / blades
        covered = min(1.0, pitch * math.sin(kappa1) * math.cos(kappa1) / interpolate(chord_m, f))
        tubes.append(Tube(name=f"streamline {j}", r1=r1 * CM, r2=r2 * CM, A1=A1 * CM2, A2=A2 * CM2,
                          kappa1=kappa1, kappa2=kappa2, solidity=sig_hub + (sig_tip - sig_hub) * f,
                          covered_fraction=covered))
    return tubes


def tip_relative_mach(ref: dict, results, gas: Gas) -> float:
    """Inlet relative Mach at the blade tip radius (inlet tip diameter / 2) with the axial Mach of the
    outermost stream tube."""
    r_tip = ref["design"]["inlet_tip_diameter"]["value"] / 2 * CM
    omega = ref["design"]["rotational_speed"]["value"] * 2 * math.pi / 60
    outer = results[0]
    T1 = T_REF - outer.V1 ** 2 / (2 * gas.cp)
    return math.hypot(outer.V1, omega * r_tip) / math.sqrt(gas.gamma * gas.R * T1)


def run(mass_flow: float, reference: dict | None = None, geometry: dict | None = None, gas: Gas = Gas()) -> dict:
    ref = reference or read_yaml(REFERENCE)
    omega = ref["design"]["rotational_speed"]["value"] * 2 * math.pi / 60
    results = solve_rotor(build_tubes(ref, geometry), mass_flow, omega, T_REF, P_REF, gas)
    avg = mass_averaged(results, gas)
    return {"mass_flow": mass_flow, "tip_M1rel": tip_relative_mach(ref, results, gas), **avg,
            "streamlines": [{
                "name": r.name, "r2_cm": round(t.r2 / CM, 4), "M1rel": round(r.M1rel, 4),
                "incidence_deg": round(math.degrees(r.incidence), 2), "deviation_deg": round(math.degrees(r.deviation), 2),
                "beta1_deg": round(math.degrees(r.beta1), 2), "beta2_deg": round(math.degrees(r.beta2), 2),
                "diffusion_factor": round(r.diffusion_factor, 4), "D_eq": round(r.deq, 4),
                "loss_profile": round(r.loss_profile, 5), "loss_shock": round(r.loss_shock, 5),
                "M_passage": round(r.M_passage, 4), "Pt_ratio": round(r.Pt_ratio, 4), "Tt_ratio": round(r.Tt_ratio, 4),
                "efficiency": round(r.efficiency, 4), "notes": r.notes}
                for r, t in zip(results, build_tubes(ref, geometry))]}


def compare(ref: dict, survey: dict) -> dict:
    """Design and near-peak-efficiency points against the measured values; radial PR profile against
    Table III(b) station 2 (rows whose survey flags concern the Pt/Tt pair are reported, not compared)."""
    design = ref["design"]
    peak = ref["measured"]["near_peak_efficiency"]
    design_run = run(design["mass_flow"]["value"], ref)
    peak_run = run(peak["mass_flow_table_III"]["value"], ref)
    bad_rows = {f["row"] for f in survey["flags"] if f["check"] in ("local_efficiency_implausible", "unreadable")}
    profile = []
    for j, (row, model) in enumerate(zip(survey["station_2"], peak_run["streamlines"]), 1):
        profile.append({"streamline": j, "r2_cm": model["r2_cm"], "measured_Pt_ratio": row["Pt_ratio"],
                        "model_Pt_ratio": model["Pt_ratio"], "difference": round(model["Pt_ratio"] - row["Pt_ratio"], 4),
                        "measured_flagged": j in bad_rows})
    used = [p for p in profile if not p["measured_flagged"]]

    def check(name, model, measured, limit, relative):
        dev = model / measured - 1 if relative else model - measured
        return {"item": name, "model": round(model, 4), "measured": measured, "deviation": round(dev, 4),
                "limit": limit, "deviation_type": "relative" if relative else "absolute",
                "result": "pass" if abs(dev) <= limit else "fail"}

    checks = [
        check("design point tip M1rel", design_run["tip_M1rel"], design["tip_relative_mach_inlet"]["value"],
              LIMITS["tip_M1rel_rel"], True),
        check("design point PR", design_run["Pt_ratio"], design["pressure_ratio"]["value"], LIMITS["pr_rel"], True),
        check("near peak efficiency PR", peak_run["Pt_ratio"], peak["pressure_ratio"]["value"], LIMITS["pr_rel"], True),
        check("near peak efficiency eta", peak_run["efficiency"], peak["efficiency"]["value"], LIMITS["eta_abs"], False),
    ]
    model_prs = [p["model_Pt_ratio"] for p in used]
    meas_prs = [p["measured_Pt_ratio"] for p in used]
    rms = math.sqrt(sum((a - b) ** 2 for a, b in zip(model_prs, meas_prs)) / len(used))
    return {
        "description": "Rotor 67 validation of tools/meanline.py (analysis A-1); generated by "
                       "engine/M1_inlet_fan/analysis/rotor67.py, do not edit",
        "acceptance": "[T] tip M1rel and PR within 2 % relative, efficiency within 2 points; not tuned",
        "checks": checks,
        "radial_profile_near_peak": {"rows": profile, "rms_difference_unflagged": round(rms, 4),
                                     "note": "measured Pt/Pref with Pt1 = Pref; rows flagged in rotor67_survey.yaml excluded from the rms"},
        "design_point": design_run,
        "near_peak_efficiency_point": peak_run,
    }


def main() -> None:
    result = compare(read_yaml(REFERENCE), read_yaml(SURVEY))
    write_yaml(OUT, result)
    for c in result["checks"]:
        print(f"{c['result']:4} {c['item']}: model {c['model']} measured {c['measured']} deviation {c['deviation']}")
    print("radial PR rms (unflagged rows):", result["radial_profile_near_peak"]["rms_difference_unflagged"])


if __name__ == "__main__":
    main()
