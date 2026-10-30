"""Tests for M2 geometry step 2 (rules/geometry.md R-G2.9-17): drum, root blocks, inner shrouds, casing,
vane feet; M1 interface (read-only) and the known M1 overlap (#77, strict xfail).

Imports from the repo root. All design values come from the active record via the
step 1 model and from geometry_params.yaml; no literal design value here. Solids are built once (hardware.build is
cached); the M1 checks import M1 geometry code read-only and are slower (~1.5 min).
"""

import re

import pytest

from engine.M2_booster.geometry import hardware as HW
from engine.M2_booster.geometry import layout as L

RULES = L.M2_DIR / "rules" / "geometry.md"


@pytest.fixture(scope="module")
def hb():
    return HW.build()


@pytest.fixture(scope="module")
def res(hb):
    return HW.checks(hb)


def test_step2_rules_written_and_tagged():
    rows = [l for l in RULES.read_text(encoding="utf-8").splitlines() if l.startswith("| R-G2.")]
    ids = [int(re.search(r"R-G2\.(\d+)", r).group(1)) for r in rows]
    assert ids == list(range(1, 18))
    rows = rows[8:]
    for row in rows:
        assert len(re.findall(r"\[(K|KS|H|G|T)\]", row.split("|")[-2])) == 1, row


def test_hw_params_tagged():
    gp = L.geometry_params()
    keys = [k for k in gp if k.startswith(("hw_", "m1_disk_"))]
    assert len(keys) == 24
    for k in keys:
        assert gp[k]["tag"] in ({"H"} if k.startswith("m1_disk_") else {"T"}) and gp[k].get("note"), k


def test_built_without_stop_rule(hb, res):
    assert res["issues"] == []
    P = hb["parts"]
    for s in [P["drum"], P["casing"], *P["roots"], *P["shrouds"], *P["feet"]]:
        assert s.isValid() and s.Volume() > 0


def test_slots_cut(hb):
    """Slotted drum volume = unslotted - slots (no slot lost or merged)."""
    P, H = hb["parts"], hb["hw"]
    removed = P["drum_unslotted"].Volume() - P["drum"].Volume()
    expected = sum(HW.slot_cutter(r, H["r_casing"]).intersect(P["drum_unslotted"]).Volume() * r["row"]["count"]
                   for r in H["rims"])
    assert removed == pytest.approx(expected, rel=1e-4)


def test_hub_and_tip_radii_on_flowpath(res):
    assert len(res["radii"]) == 9 + 9 + 3 + 6
    for r in res["radii"]:
        assert r["pass"], r


def test_no_common_volume_between_m2_parts(res):
    assert len(res["interference"]) == 17 * 16 // 2 + 6
    for r in res["interference"]:
        assert r["pass"], r


def test_running_clearances(res, hb):
    for r in res["running"]:
        assert r["distance"] > 0.0, r
        if r["ref"] is not None:
            assert r["distance"] == pytest.approx(r["ref"], rel=1e-4), r


def test_tip_clearance_rule_to_casing(res, hb):
    rot = [r for r in hb["model"]["rows"] if r["kind"] == "rotor"]
    got = [r["distance"] for r in res["running"] if r["b"] == "casing" and "airfoil" in r["a"]]
    assert got == pytest.approx([r["clearance"] for r in rot], rel=1e-4)


def test_blade_and_vane_footprints_fit(res):
    assert len(res["footprints"]) == 6
    for r in res["footprints"]:
        assert r["pass"], r


def test_nothing_ahead_of_station_21(res):
    for r in res["station_21"]:
        assert r["pass"], r


def test_walls(res):
    for w in res["walls"]:
        assert w["pass_"], w


def test_slot_aft_face_known_deviation(hb):
    """#75: slots open at the front face; aft face partly closed by the next drum wall (reported, not tuned)."""
    for rim in hb["hw"]["rims"]:
        assert rim["slot_open_front"]
        assert not rim["slot_open_aft"] and rim["slot_closed_height_aft"] > 0


def test_masses_informational(res, capsys):
    for m in res["masses"]:
        assert m["mass"] > 0
        print(f"{m['part']} {m['mass']:.3f} kg ({m['material']})")


def test_step_export(hb):
    paths = HW.export(hb)
    assert len(paths) == 11
    for p in paths:
        assert p.is_file() and p.stat().st_size > 0 and p.parent == L.CACHE / hb["model"]["layout"]["revision"]


@pytest.fixture(scope="module")
def m1(hb):
    return HW.m1_overlap(hb)


def test_m1_disk_copy_matches_m1_code(m1):
    gp = L.geometry_params()
    d = m1["m1_disk"]
    for key, val in (("m1_disk_aft_face_x_m", d["x_aft_face"]), ("m1_disk_live_rim_inner_m", d["r_live_rim_inner"]),
                     ("m1_disk_slot_bottom_m", d["r_slot_bottom"]), ("m1_disk_rim_m", d["r_rim"])):
        assert L.v(gp[key]) == pytest.approx(val, abs=5e-7), key


def test_m1_interface_gap_reported(hb):
    """#76: the drum flange sits on the station 21 plane, aft of the M1 disk aft face."""
    fl = hb["hw"]["flange"]
    assert fl["x"][0] == hb["hw"]["x21"] and fl["axial_gap_to_m1_disk"] > 0


@pytest.mark.xfail(strict=True, reason="#77: M1 rev014 fan frame / splitter / OGV overlap the booster (M0 decision)")
def test_no_overlap_with_m1(m1):
    assert m1["overlaps"] == []
