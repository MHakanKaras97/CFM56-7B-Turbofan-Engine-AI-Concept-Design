"""M1 step 5b: flowpath (geometry/flowpath.py) and 24-blade ring (geometry/fan_ring.py) from the active record.

Acceptance (M0 step 5b): blade count copies, no pairwise interference (common volume 0), blade corner radii equal the
record annulus radii within 1e-3 relative, positive tip clearance to the casing wall, valid solids with volume > 0,
per-part STEP exports. Heavy solids are built once per module (about 50 s in total).
"""

import math

import cadquery as cq
import pytest

from core import records
from core.util import read_yaml
from engine.M1_inlet_fan.geometry import fan_ring as ring
from engine.M1_inlet_fan.geometry import flowpath as fpm
from engine.M1_inlet_fan.geometry import frame as fr

RADIUS_TOL = 1e-3  # relative, M0 step 5b acceptance


@pytest.fixture(scope="module")
def model():
    return ring.build()


@pytest.fixture(scope="module")
def fp(model):
    return model["flowpath"]


@pytest.fixture(scope="module")
def chk(model):
    return ring.checks(model)


@pytest.fixture(scope="module")
def res(fp):
    return records.read_revision("M1", fp["revision"], "results.yaml")


def test_inputs_from_active_record(fp):
    assert fp["revision"] == records.active_revision("M1")


def test_station_radii_equal_record(fp, res):
    ann, st = res["annulus"], fp["stations"]
    assert st["2"]["r_hub_m"] == ann["r_hub1_m"] and st["2"]["r_tip_m"] == ann["r_tip1_m"]
    assert st["2"]["r_split_m"] == ann["r_split1_m"]
    assert st["21"]["r_hub_m"] == ann["r_hub2_m"] and st["13"]["r_outer_m"] == ann["r_tip2_m"]
    assert st["2"]["area_m2"] == pytest.approx(ann["inlet_area_m2"], rel=1e-4)
    assert abs(st["2"]["fan_face_area_deviation"]) <= 1e-4


def test_exit_splitter_holds_inner_tube_area(fp, res):
    ann = res["annulus"]
    a_inner = sum(t["A2_m2"] for t in res["tubes"] if t["stream"] == "inner")
    assert fp["stations"]["21"]["area_m2"] == pytest.approx(a_inner, rel=1e-9)
    frac = fp["stations"]["21"]["area_m2"] / ann["exit_area_m2"]
    assert frac == pytest.approx(ann["exit_core_area_fraction_equilibrium"], abs=2e-4)


def test_station_planes_in_order(fp):
    e, st = fp["rotor_edges"], fp["stations"]
    assert st["2"]["x_m"] <= min(e["le_hub"][0], e["le_split"][0], e["le_tip"][0])
    assert max(e["te_hub"][0], e["te_split"][0]) < st["21"]["x_m"] < fp["x_ogv_le_m"] < st["13"]["x_m"]
    assert e["te_tip"][0] < fp["x_ogv_le_m"]


def test_interface_yaml_is_regenerated(fp, tmp_path):
    fresh = fpm.write_interface(fp, tmp_path / "flowpath.yaml")
    assert read_yaml(fresh) == read_yaml(fpm.OUT_YAML), "flowpath.yaml is stale: run python -m engine.M1_inlet_fan.geometry.flowpath"


def test_flowpath_solids_valid(fp):
    s = fpm.solids(fp)
    for name in ("flowpath_core", "flowpath_bypass"):
        assert s[name].isValid() and s[name].Volume() > 0, name
    assert s["casing_wall_surface"].Area() > 0


def test_blade_count_and_valid(chk, model):
    assert chk["blade_count"] == model["flowpath"]["blade"]["inputs"]["blades"] == 24
    assert chk["valid"] and chk["volume_m3"] > 0


@pytest.mark.parametrize("corner", ["le_hub", "te_hub", "le_tip", "te_tip"])
def test_corner_radii_equal_record(chk, corner):
    row = chk["corners"][corner]
    assert abs(row["rel"]) <= RADIUS_TOL, row


def test_no_interference(chk):
    inter = chk["interference"]
    assert len(inter["pairs"]) == 12
    assert 1 in inter["boolean_pairs"]
    assert inter["max_common_volume_m3"] <= 1e-12
    assert chk["angular_extent_deg"] < 2 * chk["pitch_deg"]


def test_tip_clearance_positive_and_as_record(chk, fp):
    tc = chk["tip_clearance"]
    assert tc["min_distance_m"] > 0
    for gap in tc["radial_gap_at_corners_m"].values():
        assert gap == pytest.approx(fp["tip_clearance_m"], abs=1e-6)
    # shortest distance is normal to the converging casing: c cos(cone angle) <= d <= c
    e = fp["rotor_edges"]
    cone = math.atan2(e["le_tip"][1] - e["te_tip"][1], e["te_tip"][0] - e["le_tip"][0])
    assert fp["tip_clearance_m"] * math.cos(cone) * 0.99 <= tc["min_distance_m"] <= fp["tip_clearance_m"] * 1.001


def test_rotation_sense(model):
    """Blade 1 is blade 0 turned +360/N about +X: its centroid moves towards -Y from top dead centre."""
    c0, c1 = model["blades"][0].Center(), model["blades"][1].Center()
    assert c0.y == pytest.approx(0.0, abs=0.02) and c1.y < c0.y
    assert math.degrees(math.atan2(-c1.y, c1.z)) - math.degrees(math.atan2(-c0.y, c0.z)) == pytest.approx(15.0, abs=1e-6)


def test_step_exports(model, chk):
    paths = ring.export(model)
    for p in paths.values():
        assert p.exists() and p.stat().st_size > 0
    back = cq.importers.importStep(str(paths["fan_blade_trimmed"])).val()
    assert back.Volume() == pytest.approx(chk["volume_m3"], rel=1e-3)  # STEP spline round trip, about 1e-4 [T]
    for name, s in fpm.solids(model["flowpath"]).items():
        assert fr.export_step(s, name, model["flowpath"]["revision"]).stat().st_size > 0
