"""Tests for M2 geometry step 3a (rules/geometry.md R-G2.18-19, step 3a changes of R-G2.9/13/17):
drum forward cone (#76) and sloped rotor slot bottom (#75). Replace the old-rule tests removed from
tests/test_m2_geometry2.py; the strict xfail test_no_overlap_with_m1 (#77) stays there.

Imports from the repo root. No literal design value: everything comes from the active record,
geometry_params.yaml and the M1 code. M1 code is imported read-only; slow (~2 min, M1 rotor build).
"""

import pytest

from engine.M2_booster.geometry import hardware as HW
from engine.M2_booster.geometry import layout as L


@pytest.fixture(scope="module")
def hb():
    return HW.build()


@pytest.fixture(scope="module")
def res(hb):
    return HW.checks(hb)


@pytest.fixture(scope="module")
def cone(hb):
    return HW.cone_checks(hb)


@pytest.fixture(scope="module")
def slots(hb):
    return HW.slot_checks(hb)


def test_step3a_rules_written_and_tagged():
    text = (L.M2_DIR / "rules" / "geometry.md").read_text(encoding="utf-8")
    for rid in ("R-G2.18", "R-G2.19"):
        row = next(line for line in text.splitlines() if line.startswith(f"| **{rid}**"))
        assert row.split("|")[-2].strip() == "[T]", rid
    assert "This removes \"nothing ahead of station 21\" as a hardware rule" in text
    assert "no M2 part crosses station 21\" no longer applies" in text


def test_hw_params_tagged_step3a():
    gp = L.geometry_params()
    assert not [k for k in gp if k.startswith("m1_disk_")]
    keys = [k for k in gp if k.startswith("hw_")]
    assert len(keys) == 20
    for k in keys:
        assert gp[k]["tag"] == "T" and gp[k].get("note"), k


def test_m1_interface_read_from_m1_code(hb):
    from engine.M1_inlet_fan.geometry import fan_frame, rotor_hardware
    rot = rotor_hardware.build()
    m1 = hb["hw"]["m1"]
    assert m1["x_aft_face"] == rot["layout"]["x_b"]
    assert m1["r_live_rim_inner"] == rot["disk_profile"]["r_rim_inner"]
    assert m1["r_slot_bottom"] == rot["layout"]["r_slot_bottom"]
    assert m1["r_bolt_circle"] == pytest.approx(0.5 * (m1["r_live_rim_inner"] + m1["r_slot_bottom"]), abs=1e-12)
    assert m1["r_m8_boundary"] == fan_frame.interfaces(fan_frame.build())["M8_bearing_support"]["r_inner_m"]


def test_built_without_stop_rule(res):
    assert res["issues"] == []


def test_nothing_ahead_of_m1_disk_aft_face(res, hb):
    assert len(res["boundary"]) == 17
    for r in res["boundary"]:
        assert r["pass"], r
    drum = next(r for r in res["boundary"] if r["part"] == "drum")
    assert drum["x_min"] == pytest.approx(hb["hw"]["m1"]["x_aft_face"], abs=1e-7)
    assert drum["x_min"] < hb["hw"]["x21"]  # station 21 is no longer a hardware limit


def test_cone_no_common_volume_with_m1_rotor_parts(cone, hb):
    tol = float(L.v(hb["model"]["params"]["hw_common_volume_tolerance"]))
    names = {r["m1"] for r in cone["m1"]}
    assert {"M1.1.1 fan blade (with root)", "M1.1.2 fan disk", "M1.1.4 shim", "M1.1.5 spacer",
            "M1.1.6 platform", "M1.1.3 spinner"} == names
    for r in cone["m1"]:
        assert r["cone_common_fraction"] <= tol and r["drum_common_fraction"] <= tol, r


def test_cone_contacts_disk_aft_face(cone):
    assert cone["disk_distance"] == pytest.approx(0.0, abs=1e-7)
    assert cone["cone_x_min"] == pytest.approx(cone["x_disk_aft_face"], abs=1e-9)
    others = [r["cone_distance"] for r in cone["m1"] if r["m1"] != "M1.1.2 fan disk"]
    assert min(others) > 0.0


def test_cone_m8_clearance_positive(cone, hb):
    assert cone["m8_clearance"] > 0.0
    assert cone["m8_clearance"] == pytest.approx(hb["hw"]["cone"]["m8_clearance"], abs=1e-6)


def test_cone_is_part_of_drum(hb, cone):
    """Mass counted once: the cone is fused into M2.0.1 (one valid solid), no separate cone mass row."""
    P = hb["parts"]
    assert P["drum"].isValid() and len(P["drum"].Solids()) == 1
    assert P["drum"].BoundingBox().xmin == pytest.approx(cone["x_disk_aft_face"], abs=1e-9)
    names = [m["part"] for m in HW.masses(hb)]
    assert names.count("M2.0.1 drum") == 1 and not [n for n in names if "cone" in n]


def test_cone_and_drum_mass_informational(cone, capsys):
    assert cone["cone_mass"] > 0 and cone["drum_mass"] > cone["cone_mass"]
    print(f"cone {cone['cone_mass']:.3f} kg, drum {cone['drum_mass']:.3f} kg (ti6al4v, information)")


def test_slot_bottom_parallel_to_hub(hb):
    H = hb["hw"]
    ratio = float(L.v(hb["model"]["params"]["hw_slot_depth_over_rotor_chord"]))
    for rim in H["rims"]:
        d = ratio * rim["row"]["chord"]
        assert rim["slot_depth"] == pytest.approx(d, rel=1e-12)
        assert rim["r_slot_bottom_front"] == pytest.approx(L.r_at(H["hub"], rim["x_f"]) - d, abs=1e-12)
        assert rim["r_slot_bottom_aft"] == pytest.approx(L.r_at(H["hub"], rim["x_a"]) - d, abs=1e-12)
        assert rim["r_slot_bottom"] == pytest.approx(min(rim["r_slot_bottom_front"], rim["r_slot_bottom_aft"]),
                                                     abs=1e-12)


def test_slot_aft_face_margins(slots, hb):
    """#75 option 1: aft-face margin > 0 at all three stages (structural-stage check, not a pass)."""
    assert len(slots) == 3
    for s in slots:
        assert s["aft_face_margin"] > 0.0, s
        if s["front_face_margin"] is not None:
            assert s["front_face_margin"] > 0.0, s
    for rim in hb["hw"]["rims"]:
        assert rim["slot_open_front"] and rim["slot_open_aft"]


def test_root_block_fits_slot(slots, hb):
    tol = float(L.v(hb["model"]["params"]["hw_common_volume_tolerance"]))
    for s in slots:
        assert s["root_common_fraction"] <= tol, s
        assert 0.0 < s["root_distance"] <= s["fit"] * (1.0 + 1e-6), s


def test_step_files_rebuilt(hb):
    paths = HW.export(hb)
    names = {p.name for p in paths}
    assert "M2_0_1_drum.step" in names and len(paths) == 11
