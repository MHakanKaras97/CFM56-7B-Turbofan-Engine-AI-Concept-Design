"""Proposed tests for M2 geometry step 3b (rules/geometry.md R-G2.20, open issue #79): hub flow-path wall = forward
extension of the drum outer skin (M2.0.1) from the M1 platform aft end + joint gap to station 21.

Moved to tests/ by M0 from engine/M2_booster/agent/proposed_test_geometry3b.py (assertions unchanged). Imports from the repo root. No literal design value: everything
comes from the active record, geometry_params.yaml and the M1 code / M1 flowpath.yaml (read-only). Slow (~2 min,
M1 rotor build).
"""

import pytest

from engine.M2_booster.geometry import hardware as HW
from engine.M2_booster.geometry import layout as L


@pytest.fixture(scope="module")
def hb():
    return HW.build()


@pytest.fixture(scope="module")
def hw(hb):
    return HW.hub_wall_checks(hb)


def _gp(hb, key):
    return float(L.v(hb["model"]["params"][key]))


def test_step3b_rule_written_and_tagged():
    text = (L.M2_DIR / "rules" / "geometry.md").read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| R-G2.20 |"))
    assert row.split("|")[-2].strip() == "[T]"
    assert "hw_wall_joint_gap_over_wall" in row


def test_joint_gap_param_tagged(hb):
    p = hb["model"]["params"]["hw_wall_joint_gap_over_wall"]
    assert p["tag"] == "T" and p.get("note")


def test_built_without_stop_rule(hb):
    assert hb["hw"]["issues"] == []


def test_wall_inputs_from_m1(hb):
    """Platform aft end from the M1 code, wall radius = M1 station 21 hub radius (flowpath.yaml), never typed."""
    from engine.M1_inlet_fan.geometry import rotor_hardware
    w, m1 = hb["hw"]["hub_wall"], hb["hw"]["m1"]
    assert w["x_platform_aft"] == rotor_hardware.build()["platform"].BoundingBox().xmax
    assert w["r_out"] == pytest.approx(L.station_21()["r_hub"], abs=1e-12)
    assert w["r_m1_hub_at_x0"] == pytest.approx(w["r_out"], abs=1e-9)
    assert w["x1"] == hb["hw"]["x21"] and m1["x_blade_te_hub"] < w["x_platform_aft"] < w["x0"] < w["x1"]


def test_wall_thickness_and_gap_rule(hb):
    w, sh = hb["hw"]["hub_wall"], hb["hw"]["shrouds"][0]
    assert w["t"] == pytest.approx(_gp(hb, "hw_drum_wall_over_hub_radius") * sh["r_hub_min"], rel=1e-12)
    assert w["joint_gap"] == pytest.approx(_gp(hb, "hw_wall_joint_gap_over_wall") * w["t"], rel=1e-12)
    assert w["x0"] == pytest.approx(w["x_platform_aft"] + w["joint_gap"], abs=1e-12)


def test_wall_outer_radius_on_hub_flow_path(hw):
    for r in hw["r_out_measured"]:
        assert r == pytest.approx(hw["r_station_21_hub_m1"], abs=1e-5)


def test_wall_no_common_volume(hw, hb):
    tol = _gp(hb, "hw_common_volume_tolerance")
    names = {r["part"] for r in hw["interference"]}
    assert {"M1.1.1 fan blade (with root)", "M1.1.2 fan disk", "M1.1.4 shim", "M1.1.5 spacer", "M1.1.6 platform",
            "M1.1.3 spinner", "M2.0.1 forward cone"} <= names
    assert len([n for n in names if n.endswith(" root")]) == 3
    assert len([n for n in names if n.endswith(" airfoil") or n.endswith(" vane")]) == 6
    for r in hw["interference"]:
        assert r["pass"], r


def test_wall_is_part_of_drum(hb, hw):
    """Mass counted once: wall fused into M2.0.1 (one valid solid), no separate wall mass row."""
    P = hb["parts"]
    assert P["drum"].isValid() and len(P["drum"].Solids()) == 1
    names = [m["part"] for m in HW.masses(hb)]
    assert names.count("M2.0.1 drum") == 1 and not [n for n in names if "wall" in n]
    assert hw["hub_line"]["covered_drum"] and hw["hub_line"]["drum_gaps"] == []


def test_axial_joint_gap_measured(hw):
    hl = hw["hub_line"]
    assert hl["joint_gap_measured"] == pytest.approx(hl["joint_gap"], abs=1e-9)
    assert 0.0 < hl["joint_gap_measured"] <= hl["joint_gap"] * (1.0 + 1e-6)


@pytest.mark.xfail(strict=True, reason="#80: M1 platform top (rev014) lies below the M1 hub line between the blade "
                                       "TE and the platform aft end; M1 read-only, no M2 fix")
def test_hub_line_no_gap_larger_than_joint_gap(hw):
    """Literal check: hub line from the M1 blade TE to station 21, probed just below the hub radius."""
    assert hw["hub_line"]["max_gap"] <= hw["hub_line"]["joint_gap"] * (1.0 + 1e-6)


def test_platform_drop_reported(hw, capsys):
    """M1 platform top below the M1 hub line (report only, #80); falls to zero at the platform aft end."""
    d = hw["hub_line"]["platform_drop"]
    assert d[0]["drop"] > d[-1]["drop"] >= 0.0
    print(f"M1 platform drop max {hw['hub_line']['platform_drop_max'] * 1e3:.3f} mm at x {d[0]['x']:.6f}")


def test_wall_and_drum_mass_informational(hw, capsys):
    assert hw["wall_mass"] > 0 and hw["drum_mass"] > hw["wall_mass"]
    print(f"hub wall {hw['wall_mass']:.3f} kg, drum {hw['drum_mass']:.3f} kg (ti6al4v, information)")


def test_step_files_rebuilt(hb):
    paths = HW.export(hb)
    assert "M2_0_1_drum.step" in {p.name for p in paths} and len(paths) == 11
