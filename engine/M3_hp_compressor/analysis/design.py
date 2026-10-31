"""M3 HP compressor system design (rules/design.md R-D3.1-8): flow path, stage work and pressure, velocity triangles,
blade rows and the station 3 interface.

Inputs: read_icd("M3 design") and the M2 interface M3_station_25 (engine/M2_booster/geometry/flowpath.yaml,
read-only); design choices in analysis/hpc_params.yaml. Writes analysis/hpc_results.yaml and the derived
geometry/flowpath.yaml (interfaces for M4, M5, M8, M9).

Run: python -m engine.M3_hp_compressor.analysis.design
"""

import math
from pathlib import Path

from core.budgets import read_icd
from core.util import read_yaml, write_yaml
from tools import concept as C

HERE = Path(__file__).resolve().parent
PARAMS_FILE = HERE / "hpc_params.yaml"
OUT_FILE = HERE / "hpc_results.yaml"
N_STAGES = 9


def p(params: dict, key: str):
    return C.v(params[key])


def _lin(pair, t: float) -> float:
    return C.lerp(float(pair[0]), float(pair[1]), t)


def run(params: dict | None = None, icd: dict | None = None) -> dict:
    params = params or read_yaml(PARAMS_FILE)
    icd = icd or read_icd("M3 design")
    st = icd["stations"]
    W25, T25, P25 = (float(st["25"][k]["value"]) for k in ("W", "Tt", "Pt"))
    W3, T3, P3 = (float(st["3"][k]["value"]) for k in ("W", "Tt", "Pt"))
    N = float(icd["shafts"]["HP"]["speed_refs"]["girao_nominal"]["value"])
    omega = N * 2 * math.pi / 60
    s25 = C.read_interface("M2")["interfaces"]["M3_station_25"]
    x25, rh25, rt25 = float(s25["x_m"]), float(s25["r_hub_m"]), float(s25["r_tip_m"])

    counts = [int(n) for n in p(params, "rotor_blades")]
    assert len(counts) == N_STAGES

    # R-D3.1 rotor 1 inlet annulus
    r_tip1 = p(params, "tip_speed_rotor1") / omega
    A1 = C.area_for(W25, T25, P25, p(params, "mach_inlet"))
    r_hub1, _ = C.radii_tip(A1, r_tip1)
    r_m = 0.5 * (r_hub1 + r_tip1)
    U_m = omega * r_m

    # R-D3.2 / R-D3.3 planes: 0 = rotor 1 LE, then rotor TE / stator TE of each stage
    dT = (T3 - T25) / N_STAGES
    n_exp = math.log(P3 / P25) / math.log(T3 / T25)
    n_planes = 2 * N_STAGES + 1
    planes = []
    for j in range(n_planes):
        stage = (j + 1) // 2
        Tt = T25 + stage * dT
        Pt = P25 * (Tt / T25) ** n_exp
        W = W25 if (j < 2 * p(params, "bleed_after_stage")) else W3
        M = C.lerp(p(params, "mach_inlet"), p(params, "mach_exit"), j / (n_planes - 1))
        A = C.area_for(W, Tt, Pt, M)
        rh, rt = C.radii_mean(A, r_m)
        planes.append({"j": j, "Tt": Tt, "Pt": Pt, "W": W, "mach": M, "area": A, "r_hub": rh, "r_tip": rt,
                       "Vx": C.axial_velocity(Tt, M)})

    # R-D3.4 / R-D3.5 rows
    R = p(params, "reaction")
    m = p(params, "carter_m")
    rtc = p(params, "rotor_tc")
    rows = []
    for i in range(N_STAGES):
        for kind in ("rotor", "stator"):
            j_in = 2 * i if kind == "rotor" else 2 * i + 1
            a, b = planes[j_in], planes[j_in + 1]
            Tm = 0.5 * (a["Tt"] + b["Tt"])
            cp = C._GAS.cp(Tm)
            psi = cp * dT / U_m ** 2
            Vx = 0.5 * (a["Vx"] + b["Vx"])
            tri = C.stage_triangles(psi, Vx / U_m, R)
            vt_in, vt_out = (tri["vt1"], tri["vt2"]) if kind == "rotor" else (tri["vt2"], tri["vt1"])
            if kind == "stator" and i == N_STAGES - 1:
                vt_out = 0.0  # stage 9 stator = outlet guide vane, axial exit to the diffuser (R-D3.4)
            h = 0.5 * ((a["r_tip"] - a["r_hub"]) + (b["r_tip"] - b["r_hub"]))
            radii = {"hub": max(a["r_hub"], b["r_hub"]), "mean": r_m, "tip": min(a["r_tip"], b["r_tip"])}
            if kind == "rotor":
                n = counts[i]
                sigma = p(params, "rotor_solidity")
                chord = max(sigma * 2 * math.pi * r_m / n, p(params, "min_chord"))
                tc = {"hub": rtc[0], "mean": 0.5 * (rtc[0] + rtc[1]), "tip": rtc[1]}
            else:
                ar = _lin(p(params, "stator_aspect_ratio"), i / (N_STAGES - 1))
                chord = max(h / ar, p(params, "min_chord"))
                n = round(p(params, "stator_solidity") * 2 * math.pi * r_m / chord)
                neighbours = {counts[i], counts[i + 1] if i + 1 < N_STAGES else -1}
                while n in neighbours:
                    n += 1
                tc = {k: p(params, "stator_tc") for k in ("hub", "mean", "tip")}
            sigma_m = chord * n / (2 * math.pi * r_m)
            secs = C.free_vortex_sections(radii, r_m, U_m, Vx, vt_in * U_m, vt_out * U_m, kind == "rotor", chord,
                                          tc, sigma_m, m)
            rows.append({"stage": i + 1, "kind": kind, "count": n, "count_tag": "KS" if kind == "rotor" else "T",
                         "chord": chord, "solidity_mean": sigma_m, "height": h, "aspect_ratio": h / chord,
                         "psi": psi, "phi": Vx / U_m, "sections": secs, "width": C.axial_width(secs),
                         "hub_le": a["r_hub"], "hub_te": b["r_hub"], "tip_le": a["r_tip"], "tip_te": b["r_tip"]})

    # IGV: axial inflow to the rotor 1 inlet swirl (R-D3.4)
    a0 = planes[0]
    tri1 = C.stage_triangles(rows[0]["psi"], rows[0]["phi"], R)
    h0 = a0["r_tip"] - a0["r_hub"]
    igv_chord = max(h0 / _lin(p(params, "stator_aspect_ratio"), 0.0), p(params, "min_chord"))
    igv_n = int(p(params, "igv_count"))
    igv_secs = C.free_vortex_sections({"hub": a0["r_hub"], "mean": r_m, "tip": a0["r_tip"]}, r_m, U_m, a0["Vx"], 0.0,
                                      tri1["vt1"] * U_m, False, igv_chord,
                                      {k: p(params, "stator_tc") for k in ("hub", "mean", "tip")},
                                      igv_chord * igv_n / (2 * math.pi * r_m), m)
    igv = {"stage": 0, "kind": "igv", "count": igv_n, "count_tag": "T", "chord": igv_chord, "sections": igv_secs,
           "width": C.axial_width(igv_secs), "hub_le": a0["r_hub"], "hub_te": a0["r_hub"], "tip_le": a0["r_tip"],
           "tip_te": a0["r_tip"]}

    # axial layout (R-D3.6)
    g = p(params, "axial_gap_over_chord")
    x = x25 + p(params, "inlet_duct_length")
    igv["x_le"], igv["x_te"] = x, x + igv["width"]
    x = igv["x_te"] + g * igv["chord"]
    for r in rows:
        r["x_le"], r["x_te"] = x, x + r["width"]
        x = r["x_te"] + g * r["chord"]
    for j, pl in enumerate(planes):
        pl["x"] = rows[0]["x_le"] if j == 0 else rows[j - 1]["x_te"]

    s3 = planes[-1]
    bleed = rows[2 * p(params, "bleed_after_stage") - 1]
    hw = hardware_layout(params, rows)
    return {"params": params, "omega": omega, "N": N, "r_mean": r_m, "U_mean": U_m, "r_tip1": r_tip1,
            "station_25": {"x": x25, "r_hub": rh25, "r_tip": rt25}, "planes": planes, "rows": rows, "igv": igv,
            "hardware": hw,
            "station_3": s3, "bleed_port": {"x": bleed["x_te"], "r": bleed["tip_te"],
                                            "Pt": planes[2 * p(params, "bleed_after_stage")]["Pt"]},
            "budget": {"hpc_pr": P3 / P25, "T3": s3["Tt"], "W3": s3["W"], "eta_hpc": "M0 budget (R-D3.8)",
                       "power_MW": None},
            "icd_revision": icd["source"]["revision"]}


def hardware_layout(params: dict, rows: list[dict]) -> dict:
    """Disks, spool drums, forward shaft journal and CDP seal (R-D3.6) [H from T ratios]."""
    d = p(params, "disk")
    rotors = [r for r in rows if r["kind"] == "rotor"]
    stators = [r for r in rows if r["kind"] == "stator"]
    disks = []
    for r in rotors:
        w_rim = d["rim_width_over_rotor_width"] * r["width"]
        r_rim = r["hub_te"]  # rim outer radius = rotor root (higher hub of the row, R-D3.6)
        x_mid = 0.5 * (r["x_le"] + r["x_te"])
        disks.append({"stage": r["stage"], "x_mid": x_mid, "w_rim": w_rim, "r_rim_out": r_rim,
                      "r_rim_in": r_rim - d["rim_depth_over_width"] * w_rim,
                      "t_web": d["web_over_rim_width"] * w_rim, "w_bore": d["bore_width_over_rim_width"] * w_rim,
                      "r_bore_in": d["bore_inner_radius"],
                      "r_bore_out": d["bore_inner_radius"] + d["bore_height_over_rim_width"] * w_rim})
    drums = []
    for a, b, s in zip(disks, disks[1:], stators):
        r_out = s["hub_le"] - p(params, "seal_gap")
        drums.append({"from": a["stage"], "to": b["stage"], "x0": a["x_mid"] + a["w_rim"] / 2,
                      "x1": b["x_mid"] - b["w_rim"] / 2, "r_out": r_out, "r_in": r_out - d["drum_thickness"]})
    fs = p(params, "forward_shaft")
    d1 = disks[0]
    fwd = {"x_disk": d1["x_mid"] - d1["t_web"] / 2, "r_disk": 0.5 * (d1["r_bore_out"] + d1["r_rim_in"]),
           "x_journal_aft": rotors[0]["x_le"] - fs["x_ahead_of_rotor1"], "r_journal": fs["r_journal"],
           "t": fs["thickness"], "journal_length": fs["journal_length"]}
    fwd["x_journal_fwd"] = fwd["x_journal_aft"] - fs["journal_length"]
    cs = p(params, "cdp_seal")
    d9 = disks[-1]
    cdp = {"x0": d9["x_mid"] + d9["t_web"] / 2, "x1": d9["x_mid"] + d9["t_web"] / 2 + cs["length"],
           "r_in": cs["r_in"], "t": cs["thickness"]}
    return {"disks": disks, "drums": drums, "forward_shaft": fwd, "cdp_seal": cdp}


def _q(value, unit, tag, note=None):
    out = {"value": C.r6(value) if isinstance(value, float) else value, "unit": unit, "tag": tag}
    if note:
        out["note"] = note
    return out


def to_yaml(res: dict) -> dict:
    rows = []
    for r in [res["igv"]] + res["rows"]:
        rows.append({"stage": r["stage"], "kind": r["kind"], "count": _q(r["count"], "ea", r["count_tag"]),
                     "chord": _q(r["chord"], "m", "H"), "width": _q(r["width"], "m", "H"),
                     "x_le": _q(r["x_le"], "m", "H"), "x_te": _q(r["x_te"], "m", "H"),
                     "solidity_mean": _q(r.get("solidity_mean", 0.0), "-", "H"),
                     "sections": [{k: C.r6(s[k]) if isinstance(s[k], float) else s[k]
                                   for k in ("name", "r", "k1", "k2", "flow_in", "flow_out", "tc", "solidity")}
                                  for s in r["sections"]]})
    return {
        "description": "M3 HPC concept design results; generated by engine/M3_hp_compressor/analysis/design.py",
        "icd_revision": res["icd_revision"],
        "hp_speed": _q(res["N"], "rpm", "KS", "ICD shafts.HP girao_nominal"),
        "r_mean": _q(res["r_mean"], "m", "H"), "U_mean": _q(res["U_mean"], "m/s", "H"),
        "r_tip_rotor1": _q(res["r_tip1"], "m", "H"),
        "hpc_pr": _q(res["budget"]["hpc_pr"], "-", "H"), "T3": _q(res["budget"]["T3"], "K", "H"),
        "W3": _q(res["budget"]["W3"], "kg/s", "H"),
        "planes": [{k: C.r6(pl[k]) for k in ("x", "Tt", "Pt", "W", "mach", "area", "r_hub", "r_tip")}
                   for pl in res["planes"]],
        "rows": rows,
    }


def interface(res: dict) -> dict:
    s3 = res["station_3"]
    fwd, cdp = res["hardware"]["forward_shaft"], res["hardware"]["cdp_seal"]
    return {
        "description": "M3 HPC interfaces; generated by engine/M3_hp_compressor/analysis/design.py, do not edit by hand",
        "icd_revision": res["icd_revision"],
        "interfaces": {
            "M4_station_3": {"x_m": C.r6(s3["x"]), "r_hub_m": C.r6(s3["r_hub"]), "r_tip_m": C.r6(s3["r_tip"]),
                             "area_m2": C.r6(s3["area"]), "tag": "H",
                             "note": "HPC exit = stage 9 stator (OGV) trailing edge plane (R-D3.7)"},
            "M9_bleed_port": {"x_m": C.r6(res["bleed_port"]["x"]), "r_m": C.r6(res["bleed_port"]["r"]),
                              "r_case_out_m": C.r6(res["bleed_port"]["r"] + C.v(res["params"]["case_thickness"])),
                              "Pt_kpa": C.r6(res["bleed_port"]["Pt"]), "tag": "H",
                              "note": "stage 5 bleed (interstage leak, R-D3.3) on the case inner wall"},
            "M8_bearing_3_journal": {"x_fwd_m": C.r6(fwd["x_journal_fwd"]), "x_aft_m": C.r6(fwd["x_journal_aft"]),
                                     "r_inner_m": C.r6(fwd["r_journal"]), "r_outer_m": C.r6(fwd["r_journal"] + fwd["t"]),
                                     "tag": "H", "note": "HPC forward shaft journal; bearing #3 (M8) inner race on its "
                                                         "outer face (R-D3.6)"},
            "M5_cdp_flange": {"x_m": C.r6(cdp["x1"]), "r_in_m": C.r6(cdp["r_in"]), "r_out_m": C.r6(cdp["r_in"] + cdp["t"]),
                              "tag": "H", "note": "aft face of the CDP seal; HPT front shaft (M5) bolts here"},
            "M4_case_flange": {"x_m": C.r6(res["station_3"]["x"]), "r_in_m": C.r6(res["station_3"]["r_tip"]),
                               "r_out_m": C.r6(res["station_3"]["r_tip"] + C.v(res["params"]["case_thickness"])),
                               "tag": "H", "note": "aft end of the HPC rear case; M4 outer case continues here"},
            "M4_inner_flange": {"x_m": C.r6(cdp["x1"]), "r_m": C.r6(res["station_3"]["r_hub"]), "tag": "H",
                                "note": "reference for the M4 inner casing (CDP seal stator side)"},
        },
        "planes": [{"x_m": C.r6(pl["x"]), "r_hub_m": C.r6(pl["r_hub"]), "r_tip_m": C.r6(pl["r_tip"])}
                   for pl in res["planes"]],
    }


def main() -> None:
    res = run()
    write_yaml(OUT_FILE, to_yaml(res))
    C.write_interface("M3", interface(res))
    print("M3: r_mean", round(res["r_mean"], 4), "station 3", {k: round(res["station_3"][k], 4)
                                                               for k in ("x", "r_hub", "r_tip", "area")})


if __name__ == "__main__":
    main()
