"""NASA Rotor 67 validation case for the M1 streamline code (tools/meanline.py), analysis A-1.

Inputs, all from learning/ [KS] unless noted:
- design streamlines: Table IV radii and stream-tube areas at survey stations 1 and 2 (rotor_reference.yaml);
  the rotor inlet and exit of each tube are taken at these stations [T].
- endwall blockage: the Table IV areas are net of the authors' endwall blockage (about 1.5 % hub, 1.26 %
  tip), and all of the mass flow passes through them, so the blockage is in the model once; applying it
  again would count it twice. `endwall_blockage` reports the area check that shows this.
- blade metal angles at the leading and trailing edge per section (rotor67_geometry.yaml: digital copy
  plus checked and repaired OCR); flagged values are not used, the rest is interpolated linearly in
  section number. Section k sits at span fraction (k - 1) / 13 between hub (1) and casing (14)
  [T, LE radii are evenly spaced].
- solidity: hub 3.11 and tip 1.29 (Strazisar p. 2), linear in span fraction [T].
- shock expansion angle: suction surface = blade surface 1 (BETA1; the camber angle atan(r dtheta/dm) > 0 puts
  the relative flow toward +theta, so the blade turns toward -theta and its -theta face, surface 2, is the
  pressure side) [H]; its angle at the covered-passage entrance is interpolated along each section's
  meridional length and then in span (M1 step 4c).
- covered-passage entrance at meridional distance pitch x sin(kappa1) x cos(kappa1) from the leading
  edge, as a fraction of the meridional chord [T]; the camber angle is taken as linear along the chord [T].
- inlet: standard day, Tt 288.15 K, Pt 101325 Pa, no swirl (Table III reference conditions).
- endwall and tip clearance losses (tools/meanline.py `Endwall`): blade height = mean of the station 1 and 2
  annulus heights [T], chord = section chord interpolated in span, running tip clearance 1.0 mm (p. 2) [KS].
  Off for the acceptance checks (ENDWALL_LOSSES): with them on, the tip tubes choke at the exit and the design
  PR fails A-1 (user decision M1 step 3b: radial equilibrium first). The losses-on run is reported as a diagnostic.
- diffusion factor per stream tube at the design point is written to rotor67_reference.yaml
  (`computed_diffusion_factor`, [H] from the [KS] geometry) as the loading reference for the M1 fan.

Run: python -m engine.M1_inlet_fan.analysis.rotor67  (writes analysis/rotor67_validation.yaml and the
computed_diffusion_factor block of learning/rotor67_reference.yaml).

"""

import math
from pathlib import Path

from core.util import dump_yaml, read_yaml, write_yaml
from tools.meanline import (Endwall, Gas, LossMultipliers, Tube, loss_breakdown, mass_averaged, solve_rotor,
                            solve_rotor_re)

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
# Blade angle perturbation [T]: the largest last-digit OCR error left in the angle columns (status.md, M1 step 2b)
ANGLE_PERTURBATION = 0.22  # deg
ENDWALL_LOSSES = False  # endwall + tip clearance loss terms of tools/meanline.py; off until A-1 passes with them
RADIAL_EQUILIBRIUM = False  # simple radial equilibrium (solve_rotor_re); off until A-1 passes with the losses on
MM = 0.001


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


def suction_surface_angle(geometry: dict, f: float, fraction: float) -> float:
    """Suction-surface angle (deg, BETA1) at `fraction` of the meridional length of the blade section,
    interpolated linearly in span fraction f between the sections."""
    cols = geometry["points"]["columns"]
    iz, ir, ib = cols.index("Z"), cols.index("R"), cols.index("BETA1")
    points = []
    for n, sec in enumerate(geometry["points"]["sections"], 1):
        rows = sec["rows"]
        m = [0.0]
        for a, b in zip(rows, rows[1:]):
            m.append(m[-1] + math.hypot(b[iz] - a[iz], b[ir] - a[ir]))
        pts = [(mm / m[-1], r[ib]) for mm, r in zip(m, rows) if r[ib] is not None]
        points.append(((n - 1) / (N_SECTIONS - 1), interpolate(pts, fraction)))
    return interpolate(points, f)


def build_tubes(reference: dict | None = None, geometry: dict | None = None,
                losses: bool = ENDWALL_LOSSES, multipliers: LossMultipliers = LossMultipliers(),
                shock_taper: bool = True) -> list[Tube]:
    ref = reference or read_yaml(REFERENCE)
    geo = geometry or read_yaml(GEOMETRY)
    st1 = ref["survey_stations"]["station_1_upstream"]
    r_hub, r_tip = st1["hub_radius"]["value"], st1["shroud_radius"]["value"]
    blades = ref["design"]["blade_count"]["value"]
    sig_hub, sig_tip = ref["design"]["solidity_hub"]["value"], ref["design"]["solidity_tip"]["value"]
    k1, k2 = section_values(geo, "le_metal_angle"), section_values(geo, "te_metal_angle")
    chord_m = section_values(geo, "meridional_chord")
    chord = section_values(geo, "chord")
    st2 = ref["survey_stations"]["station_2_downstream"]
    height = ((r_tip - r_hub) + (st2["shroud_radius"]["value"] - st2["hub_radius"]["value"])) / 2 * CM
    clearance = ref["design"]["tip_clearance_running"]["value"] * MM
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
                          covered_fraction=covered,
                          endwall=Endwall(f, height, interpolate(chord, f) * CM, clearance) if losses else None,
                          ss_turn=kappa1 - math.radians(suction_surface_angle(geo, f, covered)),
                          multipliers=multipliers, subsonic_shock_taper=shock_taper))
    return tubes


def tip_relative_mach(ref: dict, results, gas: Gas) -> float:
    """Inlet relative Mach at the blade tip radius (inlet tip diameter / 2) with the axial Mach of the
    outermost stream tube."""
    r_tip = ref["design"]["inlet_tip_diameter"]["value"] / 2 * CM
    omega = ref["design"]["rotational_speed"]["value"] * 2 * math.pi / 60
    outer = results[0]
    T1 = T_REF - outer.V1 ** 2 / (2 * gas.cp)
    return math.hypot(outer.V1, omega * r_tip) / math.sqrt(gas.gamma * gas.R * T1)


def run(mass_flow: float, reference: dict | None = None, geometry: dict | None = None, gas: Gas = Gas(),
        losses: bool = ENDWALL_LOSSES, equilibrium: bool = RADIAL_EQUILIBRIUM,
        multipliers: LossMultipliers = LossMultipliers(), shock_taper: bool = True) -> dict:
    ref = reference or read_yaml(REFERENCE)
    omega = ref["design"]["rotational_speed"]["value"] * 2 * math.pi / 60
    tubes = build_tubes(ref, geometry, losses, multipliers, shock_taper)
    extra = {}
    if equilibrium:
        st2 = ref["survey_stations"]["station_2_downstream"]
        sol = solve_rotor_re(tubes, mass_flow, omega, T_REF, P_REF, st2["hub_radius"]["value"] * CM,
                             st2["shroud_radius"]["value"] * CM, gas)
        tubes, results = sol.tubes, sol.results
        extra = {"equilibrium": {"converged": sol.converged, "iterations": sol.iterations,
                                 "residual": float(f"{sol.residual:.2e}")}}
    else:
        results = solve_rotor(tubes, mass_flow, omega, T_REF, P_REF, gas)
    avg = mass_averaged(results, gas)
    return {"mass_flow": mass_flow, "tip_M1rel": tip_relative_mach(ref, results, gas), **avg, **extra,
            "streamlines": [{
                "name": r.name, "r2_cm": round(t.r2 / CM, 4), "M1rel": round(r.M1rel, 4),
                "incidence_deg": round(math.degrees(r.incidence), 2), "deviation_deg": round(math.degrees(r.deviation), 2),
                "beta1_deg": round(math.degrees(r.beta1), 2), "beta2_deg": round(math.degrees(r.beta2), 2),
                "diffusion_factor": round(r.diffusion_factor, 4), "D_eq": round(r.deq, 4),
                "loss_profile": round(r.loss_profile, 5), "loss_shock": round(r.loss_shock, 5),
                "loss_endwall": round(r.loss_endwall, 5), "loss_tip": round(r.loss_tip, 5),
                "M_passage": round(r.M_passage, 4), "Pt_ratio": round(r.Pt_ratio, 4), "Tt_ratio": round(r.Tt_ratio, 4),
                "efficiency": round(r.efficiency, 4), "mass_flow": round(r.mass_flow, 4),
                "loss_breakdown": {k: {"loss": round(v["loss"], 5), "delta_eta": round(v["delta_eta"], 5)}
                                   for k, v in loss_breakdown(r).items()},
                "notes": r.notes}
                for r, t in zip(results, tubes)]}


def endwall_blockage(ref: dict) -> dict:
    """Sum of the Table IV stream tube areas against the annulus at stations 1 and 2, with and without the
    Table IV endwall blockage taken off the span at the hub and the tip."""
    b_hub, b_tip = ref["endwall_blockage"]["hub"]["value"], ref["endwall_blockage"]["tip"]["value"]
    out = {"hub": b_hub, "tip": b_tip}
    for name, station in (("station_1", "station_1_upstream"), ("station_2", "station_2_downstream")):
        st = ref["survey_stations"][station]
        r_hub, r_tip = st["hub_radius"]["value"], st["shroud_radius"]["value"]
        span = r_tip - r_hub
        annulus = math.pi * (r_tip ** 2 - r_hub ** 2)
        net = math.pi * ((r_tip - b_tip * span) ** 2 - (r_hub + b_hub * span) ** 2)
        tubes = sum(ref["stream_tube_areas"][name])
        out[name] = {"annulus_cm2": round(annulus, 2), "annulus_net_of_blockage_cm2": round(net, 2),
                     "table_IV_sum_cm2": round(tubes, 2), "sum_vs_net": round(tubes / net - 1, 4),
                     "sum_vs_annulus": round(tubes / annulus - 1, 4)}
    out["note"] = ("[H] the tubes carry all the mass flow, so their areas act as the flow area net of endwall "
                   "blockage; blockage is not applied a second time")
    return out


def perturbed(geometry: dict, keys: tuple[str, ...], delta: float) -> dict:
    """Copy of the geometry with every section's `keys` metal angles shifted by delta (deg)."""
    out = {**geometry, "sections": [dict(s) for s in geometry["sections"]]}
    for s in out["sections"]:
        for key in keys:
            if s[key]["value"] is not None:
                s[key] = {**s[key], "value": s[key]["value"] + delta}
    return out


def angle_sensitivity(ref: dict, geometry: dict | None = None, delta: float = ANGLE_PERTURBATION) -> dict:
    """Design-point PR and efficiency change when all LE, all TE, or all LE and TE metal angles are shifted
    by +-delta at every section (same sign at every section: an upper bound of a random OCR error)."""
    geo = geometry or read_yaml(GEOMETRY)
    mass_flow = ref["design"]["mass_flow"]["value"]
    base = run(mass_flow, ref, geo)
    cases = []
    for name, keys in (("LE", ("le_metal_angle",)), ("TE", ("te_metal_angle",)),
                       ("LE and TE", ("le_metal_angle", "te_metal_angle"))):
        for sign in (1, -1):
            r = run(mass_flow, ref, perturbed(geo, keys, sign * delta))
            cases.append({"angles": name, "delta_deg": sign * delta,
                          "delta_PR": round(r["Pt_ratio"] - base["Pt_ratio"], 4),
                          "delta_eta": round(r["efficiency"] - base["efficiency"], 4),
                          "delta_tip_M1rel": round(r["tip_M1rel"] - base["tip_M1rel"], 4)})
    return {"point": "design", "base_PR": round(base["Pt_ratio"], 4), "base_eta": round(base["efficiency"], 4),
            "perturbation_deg": delta, "cases": cases,
            "note": "[H] all sections shifted together; tag of the perturbation size [T] (largest residual "
                    "last-digit OCR error in the angle columns)"}


def losses_on_diagnostic(ref: dict, survey: dict) -> dict:
    """Design and near-peak points with the endwall and tip clearance losses on, against the acceptance run
    (losses off) and the measured radial PR profile (near peak efficiency)."""
    design, peak = ref["design"], ref["measured"]["near_peak_efficiency"]
    out = {"note": "[H] diagnostic, not an acceptance check: endwall (Howell) + tip clearance (Lakshminarayana) "
                   "losses on [G]; tip tubes choke at the exit without radial equilibrium"}
    for name, m in (("design_point", design["mass_flow"]["value"]),
                    ("near_peak_efficiency_point", peak["mass_flow_table_III"]["value"])):
        off, on = run(m, ref, losses=False), run(m, ref, losses=True)
        out[name] = {"PR_off": round(off["Pt_ratio"], 4), "PR_on": round(on["Pt_ratio"], 4),
                     "eta_off": round(off["efficiency"], 4), "eta_on": round(on["efficiency"], 4),
                     "choked_tubes_on": [s["name"] for s in on["streamlines"] if s["notes"]]}
        if name == "design_point":
            out[name]["PR_vs_measured_on"] = round(on["Pt_ratio"] / design["pressure_ratio"]["value"] - 1, 4)
        else:
            out[name]["radial_profile"] = [
                {"streamline": j, "measured": row["Pt_ratio"], "off": a["Pt_ratio"], "on": b["Pt_ratio"],
                 "change": round(b["Pt_ratio"] - a["Pt_ratio"], 4),
                 "loss_endwall": b["loss_endwall"], "loss_tip": b["loss_tip"]}
                for j, (row, a, b) in enumerate(zip(survey["station_2"], off["streamlines"], on["streamlines"]), 1)]
    return out


def radial_equilibrium_diagnostic(ref: dict, survey: dict) -> dict:
    """A-1 with simple radial equilibrium (M1 step 4): design point PR and tip M1rel against the A-1 limits
    for radial equilibrium with and without the endwall + tip clearance losses (and each loss alone), and
    the near peak efficiency radial PR profile against Table III(b)."""
    design, peak = ref["design"], ref["measured"]["near_peak_efficiency"]
    m_design, m_peak = design["mass_flow"]["value"], peak["mass_flow_table_III"]["value"]
    pr_ref, mrel_ref = design["pressure_ratio"]["value"], design["tip_relative_mach_inlet"]["value"]
    cases = []
    for name, kw in (("no RE, no losses (acceptance run)", {"losses": False, "equilibrium": False}),
                     ("no RE, losses on", {"losses": True, "equilibrium": False}),
                     ("RE, no losses", {"losses": False, "equilibrium": True}),
                     ("RE, losses on", {"losses": True, "equilibrium": True})):
        r = run(m_design, ref, **kw)
        dev_pr, dev_m = r["Pt_ratio"] / pr_ref - 1, r["tip_M1rel"] / mrel_ref - 1
        cases.append({"case": name, "PR": round(r["Pt_ratio"], 4), "PR_deviation": round(dev_pr, 4),
                      "tip_M1rel_deviation": round(dev_m, 4), "eta": round(r["efficiency"], 4),
                      "exit_choked": [s["name"] for s in r["streamlines"] if s["notes"]],
                      "converged": r.get("equilibrium", {}).get("converged"),
                      "A1_design_point": "pass" if abs(dev_pr) <= LIMITS["pr_rel"] and abs(dev_m) <= LIMITS["tip_M1rel_rel"]
                      else "fail"})
    off = run(m_peak, ref, losses=False, equilibrium=False)
    on = run(m_peak, ref, losses=True, equilibrium=True)
    profile = [{"streamline": j, "measured": row["Pt_ratio"], "no_RE_no_losses": a["Pt_ratio"], "RE_losses_on": b["Pt_ratio"],
                "r2_cm_RE": b["r2_cm"], "exit_choked_RE": bool(b["notes"])}
               for j, (row, a, b) in enumerate(zip(survey["station_2"], off["streamlines"], on["streamlines"]), 1)]
    return {"note": "[H] simple radial equilibrium at rotor inlet (uniform) and exit, streamline curvature "
                    "neglected; losses are the [G] Howell endwall and Lakshminarayana tip clearance terms. Not tuned",
            "design_point": cases, "near_peak_radial_profile": profile,
            "near_peak_RE_losses_on": {"PR": round(on["Pt_ratio"], 4), "eta": round(on["efficiency"], 4),
                                       "converged": on["equilibrium"]["converged"]}}


def passage_mach_comparison(ref: dict) -> dict:
    """Model passage-shock Mach numbers at the near peak point against the TP-2879 laser readings
    (rotor67_reference.yaml measured_passage_mach). M_ss = suction-surface Mach after the Prandtl-Meyer
    expansion, M_pass = mean of max(M1rel, 1) and M_ss; interpolated in span fraction between the tubes."""
    st1 = ref["survey_stations"]["station_1_upstream"]
    r_hub, r_tip = st1["hub_radius"]["value"], st1["shroud_radius"]["value"]
    r = run(ref["measured"]["near_peak_efficiency"]["mass_flow_table_III"]["value"], ref)
    rows = []
    for r1, s in zip(ref["design_streamline_radii"]["station_1"], r["streamlines"]):
        f = (r1 - r_hub) / (r_tip - r_hub)
        m_up = max(s["M1rel"], 1.0)
        rows.append((f, s["M1rel"], s["M_passage"], 2 * s["M_passage"] - m_up if s["M1rel"] > 0.8 else None))
    out = []
    for span in ref["measured_passage_mach"]["spans"]:
        f = 1 - span["span_from_tip"]
        m1 = interpolate([(x[0], x[1]) for x in rows], f)
        mp = interpolate([(x[0], x[2]) for x in rows], f)
        mss = interpolate([(x[0], x[3]) for x in rows if x[3] is not None], f)
        meas = span["pre_shock_by_pitch"]
        entry = {"span_from_tip": span["span_from_tip"], "model_M1rel": round(m1, 3), "model_M_pass": round(mp, 3),
                 "model_M_ss": round(mss, 3), "measured_upstream_M1rel": span["upstream_M1rel"]}
        if meas:
            mean, top = sum(meas.values()) / len(meas), max(meas.values())
            entry.update({"measured_pre_shock_mean": round(mean, 3), "measured_pre_shock_max": top,
                          "M_pass_minus_measured_mean": round(mp - mean, 3), "M_ss_minus_measured_max": round(mss - top, 3)})
        else:
            entry["measured"] = "no passage shock (leading-edge spike only, max %.2f)" % max(span["leading_edge_peak_by_pitch"].values())
        out.append(entry)
    return {"note": "[H] model vs [KS read from plot]; near peak efficiency; suction-surface expansion from the blade "
                    "surface 1 angle at the covered-passage entrance (M1 step 4c)", "spans": out}


# Full model for the loss review and the calibration (M1 step 4d): radial equilibrium, all four loss
# mechanisms, no shock loss for a subsonic inlet relative flow (B1, TP-2879 Fig. 30).
FULL_MODEL = {"losses": True, "equilibrium": True, "shock_taper": False}
LOSS_FORM_STEPS = (
    ("M1 step 4c model (tapered subsonic shock, Lieblein profile)", {"losses": True, "equilibrium": True,
                                                                     "shock_taper": True}),
    ("B1: no shock loss for subsonic inlet flow", FULL_MODEL),
)
SKIPPED_STEPS = {
    "B2: Koch-Smith profile loss": "doğrulanmadı: Abrisha (PDF pp. 38-39, eqs. 4.11-4.15) gives the circulation "
    "parameter, area contraction, throat density and equivalent diffusion, but the DF-to-loss step only by "
    "reference (Cetin et al.); Visentin p. 32 and Zanoni p. 20 only name the model; no Mach, Reynolds or "
    "thickness correction is given in the source set; the throat density term 1 / (1 - M1^2) does not hold "
    "for the supersonic tip tubes. Not implemented."}


def pr_band(ref: dict, mass_flow: float, delta: float = ANGLE_PERTURBATION, **kw) -> list[float]:
    """PR with all LE and TE metal angles shifted by -delta and +delta (geometry digitisation uncertainty)."""
    geo = read_yaml(GEOMETRY)
    keys = ("le_metal_angle", "te_metal_angle")
    prs = [run(mass_flow, ref, perturbed(geo, keys, d), **kw)["Pt_ratio"] for d in (-delta, delta)]
    return [round(min(prs), 4), round(max(prs), 4)]


def validate(ref: dict, **kw) -> dict:
    """Loss breakdown at the design point and the validation checks of one model form: design PR and tip
    M1rel, near peak PR and eta, near stall PR and eta. Every PR carries the band from the geometry
    digitisation uncertainty (all metal angles +-ANGLE_PERTURBATION)."""
    design, stall = ref["design"], ref["measured"]["near_stall"]
    peak = ref["measured"]["near_peak_efficiency"]
    points = {"design": design["mass_flow"]["value"], "near_peak": peak["mass_flow_table_III"]["value"],
              "near_stall": stall["mass_flow_orifice"]["value"]}
    runs = {k: run(m, ref, **kw) for k, m in points.items()}
    bands = {k: pr_band(ref, m, **kw) for k, m in points.items()}
    d = runs["design"]
    m = sum(t["mass_flow"] for t in d["streamlines"])
    shares = {k: round(sum(t["mass_flow"] * t["loss_breakdown"][k]["delta_eta"] for t in d["streamlines"]) / m, 4)
              for k in ("profile", "shock", "endwall", "tip")}

    def check(name, model, measured, limit, relative, band=None):
        dev = model / measured - 1 if relative else model - measured
        out = {"item": name, "model": round(model, 4), "measured": measured, "deviation": round(dev, 4),
               "limit": limit, "result": "pass" if abs(dev) <= limit else "fail"}
        if band:
            out["PR_band_geometry"] = band
        return out

    checks = [check("design point PR", d["Pt_ratio"], design["pressure_ratio"]["value"], LIMITS["pr_rel"], True,
                    bands["design"]),
              check("design point tip M1rel", d["tip_M1rel"], design["tip_relative_mach_inlet"]["value"],
                    LIMITS["tip_M1rel_rel"], True),
              check("near peak PR", runs["near_peak"]["Pt_ratio"], peak["pressure_ratio"]["value"], LIMITS["pr_rel"],
                    True, bands["near_peak"]),
              check("near peak eta", runs["near_peak"]["efficiency"], peak["efficiency"]["value"], LIMITS["eta_abs"],
                    False),
              check("near stall PR", runs["near_stall"]["Pt_ratio"], stall["pressure_ratio"]["value"], LIMITS["pr_rel"],
                    True, bands["near_stall"]),
              check("near stall eta", runs["near_stall"]["efficiency"], stall["efficiency"]["value"], LIMITS["eta_abs"],
                    False)]
    return {"model": {k: v for k, v in kw.items() if k != "multipliers"},
            "design_point": {"PR": round(d["Pt_ratio"], 4), "eta": round(d["efficiency"], 4),
                             "delta_eta_mass_averaged": shares,
                             "tubes": [{"name": t["name"], "Pt_ratio": t["Pt_ratio"], "efficiency": t["efficiency"],
                                        **t["loss_breakdown"]} for t in d["streamlines"]]},
            "converged": {k: r.get("equilibrium", {}).get("converged") for k, r in runs.items()},
            "checks": checks,
            "result": "pass" if all(c["result"] == "pass" for c in checks) else "fail"}


def loss_review(ref: dict) -> dict:
    """Loss forms one at a time (M1 step 4d): breakdown and validation after each change."""
    stall, peak = ref["measured"]["near_stall"], ref["measured"]["near_peak_efficiency"]
    return {"note": "[H] radial equilibrium + profile, shock, endwall and tip clearance losses (tip loss only above "
                    "80 % span, Zanoni p. 16); delta_eta = share of 1 - eta split in proportion to the loss "
                    "coefficients; PR_band_geometry = PR with all metal angles -/+0.22 deg; not tuned",
            "measured_eta": {"near_peak_efficiency": peak["efficiency"]["value"],
                             "near_stall": stall["efficiency"]["value"],
                             "design": "not stated in TP-2879 (doğrulanmadı)"},
            "steps": [{"step": name, **validate(ref, **kw)} for name, kw in LOSS_FORM_STEPS],
            "skipped": SKIPPED_STEPS}


def diffusion_factor_reference(ref: dict, geometry: dict | None = None) -> dict:
    """Lieblein DF per design streamline at the design point (acceptance configuration), with its span
    fraction at the rotor inlet, for the M1 fan loading limits."""
    geo = geometry or read_yaml(GEOMETRY)
    st1 = ref["survey_stations"]["station_1_upstream"]
    r_hub, r_tip = st1["hub_radius"]["value"], st1["shroud_radius"]["value"]
    r = run(ref["design"]["mass_flow"]["value"], ref, geo)
    rows = [{"streamline": j, "span_fraction": round((r1 - r_hub) / (r_tip - r_hub), 4),
             "diffusion_factor": s["diffusion_factor"], "D_eq": s["D_eq"], "M1rel": s["M1rel"],
             "exit_choked": bool(s["notes"])}
            for j, (r1, s) in enumerate(zip(ref["design_streamline_radii"]["station_1"], r["streamlines"]), 1)]
    return {"tag": "H", "point": "design (Table 1 mass flow and speed)",
            "generated_by": "engine/M1_inlet_fan/analysis/rotor67.py (diffusion_factor_reference), do not edit",
            "basis": "tools/meanline.py as validated in A-1 (design point within 2 %), KS geometry from "
                     "rotor67_geometry.yaml; span_fraction 0 = hub, 1 = casing at station 1",
            "caution": "Lieblein DF is a subsonic cascade loading measure; in the supersonic tip region (M1rel > 1) "
                       "the diffusion is set largely by the passage shock, so DF there is less meaningful",
            "streamlines": rows}


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

    choke = ref["measured"]["choke_mass_flow"]["value"]
    near_choke = (f"near choke ({peak_run['mass_flow'] / choke:.0%} of {choke} kg/s), meanline limit; "
                  "the design point is the acceptance criterion")
    checks = [
        check("design point tip M1rel", design_run["tip_M1rel"], design["tip_relative_mach_inlet"]["value"],
              LIMITS["tip_M1rel_rel"], True),
        dict(check("design point PR", design_run["Pt_ratio"], design["pressure_ratio"]["value"], LIMITS["pr_rel"], True),
             PR_band_geometry=pr_band(ref, design["mass_flow"]["value"])),
        dict(check("near peak efficiency PR", peak_run["Pt_ratio"], peak["pressure_ratio"]["value"], LIMITS["pr_rel"],
                   True), expected_failure=near_choke, PR_band_geometry=pr_band(ref, peak["mass_flow_table_III"]["value"])),
        dict(check("near peak efficiency eta", peak_run["efficiency"], peak["efficiency"]["value"], LIMITS["eta_abs"],
                   False), expected_failure=near_choke),
    ]
    model_prs = [p["model_Pt_ratio"] for p in used]
    meas_prs = [p["measured_Pt_ratio"] for p in used]
    rms = math.sqrt(sum((a - b) ** 2 for a, b in zip(model_prs, meas_prs)) / len(used))
    return {
        "description": "Rotor 67 validation of tools/meanline.py (analysis A-1); generated by "
                       "engine/M1_inlet_fan/analysis/rotor67.py, do not edit",
        "acceptance": "[T] design point: tip M1rel and PR within 2 % relative; not tuned. Near peak efficiency "
                      "(PR 2 %, efficiency 2 points) is reported; a failure there is expected near choke",
        "checks": checks,
        "endwall_blockage": endwall_blockage(ref),
        "radial_profile_near_peak": {"rows": profile, "rms_difference_unflagged": round(rms, 4),
                                     "note": "measured Pt/Pref with Pt1 = Pref; rows flagged in rotor67_survey.yaml excluded from the rms"},
        "angle_sensitivity": angle_sensitivity(ref),
        "losses_on_diagnostic": losses_on_diagnostic(ref, survey),
        "radial_equilibrium_diagnostic": radial_equilibrium_diagnostic(ref, survey),
        "loss_review": loss_review(ref),
        "passage_mach_comparison": passage_mach_comparison(ref),
        "design_point": design_run,
        "near_peak_efficiency_point": peak_run,
    }


def write_generated_block(path: Path, key: str, value: dict) -> None:
    """Replace (or append) the top-level `key` block at the end of a hand-kept YAML file, leaving the rest of
    the text as written."""
    text = path.read_text(encoding="utf-8")
    head = text.split(f"\n{key}:", 1)[0].rstrip("\n") + "\n"
    path.write_text(head + dump_yaml({key: value}), encoding="utf-8", newline="\n")


def main() -> None:
    ref = read_yaml(REFERENCE)
    ref["computed_diffusion_factor"] = diffusion_factor_reference(ref)
    write_generated_block(REFERENCE, "computed_diffusion_factor", ref["computed_diffusion_factor"])
    result = compare(ref, read_yaml(SURVEY))
    write_yaml(OUT, result)
    for c in result["checks"]:
        expected = " (expected: " + c["expected_failure"] + ")" if "expected_failure" in c else ""
        band = f" band {c['PR_band_geometry']}" if "PR_band_geometry" in c else ""
        print(f"{c['result']:4} {c['item']}: model {c['model']} measured {c['measured']} deviation {c['deviation']}{band}{expected}")
    print("radial PR rms (unflagged rows):", result["radial_profile_near_peak"]["rms_difference_unflagged"])
    for c in result["angle_sensitivity"]["cases"]:
        print(f"{c['angles']:9} {c['delta_deg']:+.2f} deg: dPR {c['delta_PR']:+.4f} deta {c['delta_eta']:+.4f}")
    d = result["losses_on_diagnostic"]
    print("losses on, design point:", {k: v for k, v in d["design_point"].items()})
    for row in d["near_peak_efficiency_point"]["radial_profile"]:
        print(f"  near peak streamline {row['streamline']}: measured {row['measured']} off {row['off']} on {row['on']}")
    re = result["radial_equilibrium_diagnostic"]
    for c in re["design_point"]:
        print(f"{c['case']:34} PR {c['PR']} ({c['PR_deviation']:+.4f}) eta {c['eta']} choked {c['exit_choked']} "
              f"A-1 {c['A1_design_point']}")
    for row in re["near_peak_radial_profile"]:
        print(f"  near peak {row['streamline']}: measured {row['measured']} old {row['no_RE_no_losses']} "
              f"RE+losses {row['RE_losses_on']}")
    for row in result["passage_mach_comparison"]["spans"]:
        print("passage Mach", row)
    for step in result["loss_review"]["steps"]:
        print("loss review:", step["step"], "| design eta", step["design_point"]["eta"], "shares",
              step["design_point"]["delta_eta_mass_averaged"])
        for c in step["checks"]:
            print(f"  {c['result']:4} {c['item']}: model {c['model']} measured {c['measured']} deviation "
                  f"{c['deviation']} band {c.get('PR_band_geometry', '')}")
    for row in ref["computed_diffusion_factor"]["streamlines"]:
        print(f"DF streamline {row['streamline']} span {row['span_fraction']}: {row['diffusion_factor']} "
              f"(M1rel {row['M1rel']})")


if __name__ == "__main__":
    main()
