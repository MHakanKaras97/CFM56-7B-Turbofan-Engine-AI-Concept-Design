"""Proposed tests for M2 geometry step 1 (rules/geometry.md R-G2.1-8): flow path, blade solids, checks, STEP export.

Written as if located in tests/ (imports from the repo root). All design values come from the active record via
engine/M2_booster/geometry/layout.py; only the source counts 74/78/74 [KS] (known_values.md) are literal here.
Solids are built once per test module (blades.build is cached).
"""

import re

import pytest

from core import records
from core.util import read_yaml
from engine.M2_booster.geometry import blades as B
from engine.M2_booster.geometry import layout as L

ROOT = L.ROOT
M2 = ROOT / "engine" / "M2_booster"
RULES = M2 / "rules" / "geometry.md"
M1_FRAME = ROOT / "engine" / "M1_inlet_fan" / "geometry" / "frame.py"
TAGS = {"K", "KS", "H", "G", "T"}


@pytest.fixture(scope="module")
def model():
    return B.build()


@pytest.fixture(scope="module")
def result(model):
    return B.checks(model)


def test_rules_linked_and_tagged():
    assert "`geometry.md`" in (M2 / "rules" / "index.md").read_text(encoding="utf-8")
    rows = [l for l in RULES.read_text(encoding="utf-8").splitlines() if l.startswith("| R-G2.")]
    assert len(rows) == 8
    for row in rows:
        assert len(re.findall(r"\[(K|KS|H|G|T)\]", row.split("|")[-2])) == 1, row


def test_geometry_params_one_tag_per_field():
    for key, q in L.geometry_params().items():
        if key == "description":
            continue
        assert q["tag"] in TAGS and q.get("note"), key


def test_frame_matches_m1_convention():
    src = M1_FRAME.read_text(encoding="utf-8")  # read, not imported
    assert f"AXIS_DIR = {L.AXIS_DIR}" in src
    assert f"AXIS_ORIGIN = {L.AXIS_ORIGIN}" in src
    assert "ROTATION_SIGN = +1" in src and L.ROTATION_SIGN == +1


def test_inputs_from_active_record():
    lay = L.layout()
    assert lay["revision"] == records.active_revision("M2")
    m1 = read_yaml(ROOT / "engine" / "M1_inlet_fan" / "geometry" / "flowpath.yaml")["interfaces"]["M2_station_21"]
    assert lay["station_21"]["x"] == m1["x_m"]
    assert lay["r_casing"] == m1["r_tip_m"]
    res = records.read_revision("M2", lay["revision"], "results.yaml")
    assert lay["hub_line"][-1][1] == pytest.approx(res["station_24"]["r_hub"], abs=5e-6)
    assert lay["hub_line"][0][1] == pytest.approx(res["station_21"]["r_hub"], abs=5e-6)


def test_axial_layout_monotonic():
    lay = L.layout()
    xs = [lay["station_21"]["x"]] + [x for r in lay["rows"] for x in (r["x_le"], r["x_te"])]
    assert all(b > a for a, b in zip(xs, xs[1:]))
    assert [r["kind"] for r in lay["rows"]] == ["rotor", "stator"] * 3
    assert lay["x24"] == lay["rows"][-1]["x_te"]


def test_annulus_areas_within_tolerance(result):
    assert len(result["areas"]) == 10
    for a in result["areas"]:
        assert a["pass"], a


def test_blade_counts(model):
    res = records.read_revision("M2", model["layout"]["revision"], "results.yaml")
    rotors = [r["count"] for r in model["rows"] if r["kind"] == "rotor"]
    stators = [r["count"] for r in model["rows"] if r["kind"] == "stator"]
    assert rotors == [74, 78, 74]  # [KS] known_values.md
    assert stators == [s["stator_vanes"]["value"] for s in res["stages"]]


def test_rows_built_without_stop_rule(model):
    for r in model["rows"]:
        assert r["issues"] == [], (r["part_id"], r["issues"])
        assert r["solid"].isValid() and r["solid"].Volume() > 0


@pytest.mark.parametrize("i", range(6))
def test_mean_chord_and_solidity_vs_record(result, i):
    assert result["rows"][i]["chord_solidity"]["pass"], result["rows"][i]


@pytest.mark.parametrize("i", range(6))
def test_root_and_tip_radii_on_flowpath(result, model, i):
    rd, row = result["rows"][i]["radii"], model["rows"][i]
    assert rd["pass"], rd
    assert rd["r_max"] == pytest.approx(row["r_cut"], abs=1e-6)
    assert min(row["hub_le"], row["hub_te"]) - 1e-6 <= rd["r_min"] <= max(row["hub_le"], row["hub_te"]) + 1e-6


@pytest.mark.parametrize("i", range(6))
def test_no_intersection_between_neighbours(result, i):
    nb = result["rows"][i]["neighbour"]
    assert nb["pass"] and nb["common_volume"] == 0.0 and nb["min_distance"] > 0.0, nb


def test_rotor_tip_clearance_rule(model):
    gp = model["params"]
    ratio = L.v(gp["tip_clearance_source_cm"]) / L.v(gp["rig_blade_height_cm"])
    for r in model["rows"]:
        h = model["layout"]["r_casing"] - 0.5 * (r["hub_le"] + r["hub_te"])
        assert r["clearance"] == pytest.approx(ratio * h if r["kind"] == "rotor" else 0.0, rel=1e-12)


def test_mass_informational(result, capsys):
    for r in result["rows"]:
        m = r["mass"]
        assert m["volume_blade"] > 0 and m["mass_row"] > 0
        print(f"{r['part_id']} V {m['volume_blade'] * 1e6:.2f} cm3 m_row {m['mass_row']:.3f} kg ({m['material']})")


def test_step_export(model):
    paths = B.export(model)
    assert len(paths) == 7
    for p in paths:
        assert p.is_file() and p.stat().st_size > 0
        assert p.parent == L.CACHE / model["layout"]["revision"]
