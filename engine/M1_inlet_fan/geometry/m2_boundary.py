"""M2 booster values at the M1 frame boundary (rules/geometry.md R-G1.2, R-G1.3, R-G1.7), read at run time from the
M2 geometry code and files (read-only import; no M2 file is written, no value typed in M1).

- x24: station 24 plane (S3 trailing edge, M2 layout R-G2.2), start of the M1 core-side frame zone;
- r_casing, casing_thickness: M2.0.2 casing inner radius and wall thickness (M2 R-G2.12: ratio x casing radius);
  the M2 casing is the core/bypass divider wall from station 21 to station 24 (CR-002 option a);
- r_core_hub, r_core_tip: M2 station 24/25 annulus (M2 flowpath.yaml interfaces.M3_station_25, sha-checked against
  the M2 record by layout.record).

Only the cheap M2 layout is used here (no CadQuery solids); M2 hardware.build imports the M1 frame, so calling it from
the M1 build would recurse. `cross_check` compares these values with M2 hardware.build after the M1 build.
"""

from functools import lru_cache


@lru_cache(maxsize=1)
def m2_boundary() -> dict:
    from engine.M2_booster.geometry import layout as L2
    lay = L2.layout()
    gp = L2.geometry_params()
    st25 = L2.record()["flowpath"]["interfaces"]["M3_station_25"]
    r_c = lay["r_casing"]
    return {"revision": lay["revision"], "x24": lay["x24"], "x21": lay["station_21"]["x"], "r_casing": r_c,
            "casing_thickness": float(L2.v(gp["hw_casing_thickness_over_radius"])) * r_c,
            "r_core_hub": float(st25["r_hub_m"]), "r_core_tip": float(st25["r_tip_m"])}


def root_radius(r_split2: float, tol: float = 1e-6) -> float:
    """Bypass inner wall radius over the OGV and bypass struts = r_split2 + M2 casing thickness (R-G1.3) [H]."""
    b = m2_boundary()
    if abs(b["r_casing"] - r_split2) > tol:
        raise ValueError(f"M2 casing radius {b['r_casing']} differs from M1 r_split2 {r_split2}")
    return r_split2 + b["casing_thickness"]


def cross_check() -> dict:
    """Values above vs the M2 hardware model (call only after the M1 build; M2 hardware imports the M1 frame)."""
    from engine.M2_booster.geometry import hardware as HW
    hw = HW.build()["hw"]
    b = m2_boundary()
    return {"d_casing_thickness": b["casing_thickness"] - hw["casing_thickness"], "d_x24": b["x24"] - hw["x24"],
            "d_r_casing": b["r_casing"] - hw["r_casing"]}
