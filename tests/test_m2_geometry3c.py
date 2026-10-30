"""Proposed tests for M2 geometry step 3c, second pass (rules/geometry.md R-G2.19 amended, R-G2.21; open issue #81).
Moved to tests/ by M0 from engine/M2_booster/agent/proposed_test_geometry3c.py (assertions unchanged); supersedes the
first-pass file (405-step sweep, curved slot bottom).

R-G2.19 (amended, user decision option 2): straight slot along the slot axis, bottom at least the stated depth below
the hub line at every rotor-row point. R-G2.21: aft insertion along the slot axis; gate = exact swept solid per stage
(R1, R2, R3) against the drum (incl. hub wall), the forward cone and the seated neighbouring root blocks.

Imports from the repo root. No literal design value: everything comes from the active record, geometry_params.yaml
and the M1 code (read-only). Slow (hardware build with M1 rotor, three swept solids).
"""

import re

import numpy as np
import pytest

from engine.M2_booster.geometry import hardware as HW
from engine.M2_booster.geometry import insertion as I
from engine.M2_booster.geometry import layout as L

TAG = r"\[(K|KS|H|G|T)\]"


@pytest.fixture(scope="module")
def hb():
    return HW.build()


@pytest.fixture(scope="module")
def sw(hb):
    return I.sweep(hb)


def _gp(hb, key):
    return float(L.v(hb["model"]["params"][key]))


def _row(rid):
    text = (L.M2_DIR / "rules" / "geometry.md").read_text(encoding="utf-8")
    return text, next(line for line in text.splitlines() if line.startswith(f"| {rid} |"))


def test_rule_r_g2_19_amended_row():
    """Plain row, exactly one tag in the whole row ([T] in the tag cell), change and reason stated."""
    _, row = _row("R-G2.19")
    assert len(re.findall(TAG, row)) == 1 and row.split("|")[-2].strip() == "[T]"
    for s in ("straight", "slot axis", "broached", "hw_slot_depth_over_rotor_chord", "every point of the bottom face",
              "rotor row", "not to pass the R-G2.21 gate", "aft-face margin > 0"):
        assert s in row, s


def test_rule_r_g2_21_row_and_numbering():
    text, row = _row("R-G2.21")
    assert len(re.findall(TAG, row)) == 1 and row.split("|")[-2].strip() == "[T]"
    assert "swept solid" in row and "hw_common_volume_tolerance" in row and "R-G2.20" in row
    ids = [int(m.group(1)) for m in re.finditer(r"^\| R-G2\.(\d+) \|", text, re.M)]
    assert ids == list(range(1, 22))


def test_no_new_constant():
    """The amendments add no hw_* key (slot slope, depth and path reuse R-G2.5/10/19 values)."""
    assert len([k for k in L.geometry_params() if k.startswith("hw_")]) == 21


def test_slot_axis_slope_and_path(hb):
    """Slot axis rises by the hub-line slope over the rotor row; the R-G2.21 path is the slot axis."""
    H = hb["hw"]
    for k, rim in enumerate(H["rims"]):
        row = rim["row"]
        s = (L.r_at(H["hub"], row["x_te"]) - L.r_at(H["hub"], row["x_le"])) / (row["x_te"] - row["x_le"])
        assert rim["slot_slope"] == pytest.approx(s, rel=1e-12)
        hp = HW.hub_points(H["hub"], rim["x_f"], rim["x_a"])  # = largest hub-line segment slope inside the rim
        assert s == pytest.approx(max((r1 - r0) / (x1 - x0) for (x0, r0), (x1, r1) in zip(hp, hp[1:])), rel=1e-9)
        p = I.insertion_path(H, k)
        d = p["direction_per_axial_m"]
        a = HW.slot_axes(rim)["a"]
        assert d[0] == 1.0 and d[1] == pytest.approx(a[1] / a[0], rel=1e-12) and d[2] == pytest.approx(s, rel=1e-12)
        assert p["u_start"] == pytest.approx(rim["x_a"] - rim["x_f"], abs=1e-12)


def test_slot_bottom_straight_on_solid(hb):
    """Root block: the bottom and both side faces are planes parallel to the slot axis (straight slot)."""
    for rim, s in zip(hb["hw"]["rims"], hb["parts"]["roots"]):
        a = HW.slot_axes(rim)["a"]
        par = [f for f in s.Faces() if f.geomType() == "PLANE" and abs(np.dot(f.normalAt().toTuple(), a)) < 1e-9]
        assert len(par) == 3, rim["row"]["part_id"]


def test_slot_bottom_depth_every_row_point(hb, capsys):
    """Depth >= stated depth at every rotor-row point (independent finer sample than the placement), equality at the
    deepest point; extra depth recorded per stage."""
    for rim in hb["hw"]["rims"]:
        row, d, half = rim["row"], rim["slot_depth"], 0.5 * rim["slot_width"]
        assert d == pytest.approx(_gp(hb, "hw_slot_depth_over_rotor_chord") * row["chord"], rel=1e-12)
        X, T = np.meshgrid(np.linspace(row["x_le"], row["x_te"], 5003), np.linspace(-half, half, 157))
        dep = HW.slot_bottom_depth(rim, X, T)
        assert dep.min() >= d - 1e-9, row["part_id"]
        assert dep.min() == pytest.approx(d, abs=1e-6)
        assert rim["slot_depth_min_row"] == pytest.approx(d, abs=1e-9)
        assert rim["slot_extra_depth"] == pytest.approx(dep.max() - d, abs=1e-6) and rim["slot_extra_depth"] > 0.0
        print(f"{row['part_id']}: extra depth {rim['slot_extra_depth'] * 1e3:.3f} mm, rim depth "
              f"{rim['slot_depth_min_rim'] * 1e3:.3f}-{rim['slot_depth_max_rim'] * 1e3:.3f} mm (stated {d * 1e3:.3f})")


def test_aft_face_margins_positive(hb, capsys):
    """R-G2.19 check: aft-face margin > 0 at all three stages; front-face margins of R2/R3 > 0; slots open at the
    aft faces (and at the R2/R3 front faces)."""
    H = hb["hw"]
    for i, rim in enumerate(H["rims"]):
        assert rim["aft_face_margin"] == pytest.approx(rim["r_slot_bottom_aft"] - H["shrouds"][i]["r_wall_out"],
                                                       abs=1e-12)
        assert rim["aft_face_margin"] > 0.0 and rim["slot_open_aft"], rim["row"]["part_id"]
        if i > 0:
            assert rim["front_face_margin"] > 0.0 and rim["slot_open_front"], rim["row"]["part_id"]
        print(f"{rim['row']['part_id']}: aft margin {rim['aft_face_margin'] * 1e3:.3f} mm")


def test_live_rim_and_walls(hb):
    t_min = _gp(hb, "hw_min_wall_m")
    for rim in hb["hw"]["rims"]:
        assert rim["live_rim"] == pytest.approx(rim["r_slot_bottom_min"] - rim["r_inner"], abs=1e-12)
        assert rim["live_rim"] >= t_min
    for w in HW.walls(hb):
        assert w["pass_"], w


def test_root_block_fit_in_straight_slot(hb):
    tol = _gp(hb, "hw_common_volume_tolerance")
    slots = HW.slot_checks(hb)
    for s in slots:
        assert s["root_common_fraction"] <= tol, s
    for s in slots[1:]:
        assert 0.0 < s["root_distance"] <= s["fit"] * (1.0 + 1e-6), s


def test_start_fully_aft_of_rim(sw):
    for s in sw["stages"]:
        assert s["start_x_min"] >= s["x_rim_aft"] - 1e-9


def test_swept_solid_result_per_stage(sw, capsys):
    """R-G2.21 gate: common volume of the swept solid <= hw_common_volume_tolerance x block volume, per stage."""
    assert [s["path"]["row"] for s in sw["stages"]] == ["M2.1.1", "M2.2.1", "M2.3.1"]
    for s in sw["stages"]:
        assert set(s["gate"]) == {"M2.0.1 drum (incl. hub wall, teeth)", "M2.0.1 forward cone",
                                  "seated neighbour roots (-1, +1)"}
        assert s["swept_volume"] > s["block_volume"] > 0.0
        for n, g in s["gate"].items():
            assert g["fraction"] == pytest.approx(g["volume"] / s["block_volume"], rel=1e-12)
            assert g["pass"] == (g["fraction"] <= s["tolerance"])
            print(f"{s['path']['row']} {n}: {g['volume'] * 1e9:.6f} mm3 ({g['fraction']:.2e})")
        assert s["clear"], s["path"]["row"]
    assert sw["clear"]


def test_swept_solid_contains_start_and_seated(hb):
    """The swept solid contains the block at the start and at the seated position (exact construction check, R1)."""
    H, root = hb["hw"], hb["parts"]["roots"][0]
    p = I.insertion_path(H, 0)
    d, u0 = p["direction_per_axial_m"], p["u_start"]
    import cadquery as cq
    sw = I.swept_solid(root, cq.Vector(d[0] * u0, d[1] * u0, d[2] * u0))
    v = root.Volume()
    for blk in (root, I._moved(root, d, u0)):
        com = sum(s.Volume() for s in sw.intersect(blk).Solids())
        assert com == pytest.approx(v, rel=1e-6)


def test_seated_contact_on_forward_stop(hb):
    """R-G2.21 seated condition of R1: contact on the hub wall aft face (stop), fit check on the non-stop faces."""
    s = I.r1_seated_fit(hb)
    assert s["distance_stop"] == pytest.approx(0.0, abs=1e-7)
    assert 0.0 < s["distance_non_stop"] <= s["fit"] * (1.0 + 1e-6)
    assert s["common_fraction"] <= _gp(hb, "hw_common_volume_tolerance")


def test_stator1_crossing_reported(sw, capsys):
    """Information only: S1 hardware the R1 swept solid would cross if the stators were fitted first."""
    s1 = sw["stator1"]
    assert set(s1) == {"S1 inner shroud ring", "S1 seal land", "S1 drum seal teeth (in drum gate)",
                       "S1 vane airfoil", "S1 vane foot"}
    assert s1["S1 inner shroud ring"]["volume"] > 0.0  # stators cannot be fitted before R1
    assert s1["S1 drum seal teeth (in drum gate)"]["volume"] == 0.0
    for n, r in s1.items():
        print(n, f"{r['volume'] * 1e9:.1f} mm3 axial {r['axial'] * 1e3:.2f} mm radial {r['radial'] * 1e3:.2f} mm")


def test_stop_rule_state(hb):
    """Sweep clear at all stages: R-G2.21 applied, #81 removed from the stop-rule list; the R1 slot front opening is
    still recorded as covered by the wall (information, intended forward stop)."""
    H = hb["hw"]
    assert H["issues"] == []
    w = H["hub_wall"]
    assert w["slot_front_covered"] == pytest.approx(w["t"], rel=1e-12) and w["slot_front_window"] > 0.0
    assert H["rims"][0]["slot_open_front"] is False
