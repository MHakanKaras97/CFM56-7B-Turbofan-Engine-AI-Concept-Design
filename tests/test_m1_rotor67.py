"""M1 analysis A-1: Rotor 67 table extraction and meanline validation.

Acceptance [T] (rules/analyses.md A-1): design point tip M1rel and PR within 2 %. The near peak efficiency
point (PR 2 %, efficiency 2 points) is an expected failure near choke: strict xfail with the deviation in
the reason, so it turns red when a later model change makes it pass. The model is not tuned to pass.
"""

from pathlib import Path

import pytest
import yaml

from core.toolpaths import ToolPathError, tool_path
from core.util import read_yaml
from engine.M1_inlet_fan.analysis import rotor67, rotor67_tables

ROOT = Path(__file__).resolve().parents[1]
LEARNING = ROOT / "engine" / "M1_inlet_fan" / "learning"
VALIDATION = ROOT / "engine" / "M1_inlet_fan" / "analysis" / "rotor67_validation.yaml"


def pdf_available() -> bool:
    try:
        tool_path("pdftotext")
    except ToolPathError:
        return False
    return rotor67_tables.PDF.is_file() and all((rotor67_tables.DIGITAL / name).is_file()
                                                for name, _ in rotor67_tables.DIGITAL_FILES.values())


@pytest.fixture(scope="module")
def validation():
    return rotor67.compare(read_yaml(rotor67.REFERENCE), read_yaml(rotor67.SURVEY))


def check(validation, item):
    return next(c for c in validation["checks"] if c["item"] == item)


def read_yaml_roundtrip(data):
    return yaml.safe_load(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def test_validation_file_is_current(validation):
    assert read_yaml(VALIDATION) == read_yaml_roundtrip(validation)


def test_design_point_tip_relative_mach(validation):
    assert check(validation, "design point tip M1rel")["result"] == "pass"


def test_design_point_pressure_ratio(validation):
    assert check(validation, "design point PR")["result"] == "pass"


NEAR_CHOKE = "near choke (99% of 34.96 kg/s), meanline limit"


@pytest.mark.xfail(strict=True, reason=f"{NEAR_CHOKE}: PR -6.4 %, the two tip stream tubes choke at the exit")
def test_near_peak_pressure_ratio(validation):
    assert check(validation, "near peak efficiency PR")["result"] == "pass"


@pytest.mark.xfail(strict=True, reason=f"{NEAR_CHOKE}: eta -2.8 points (model 0.900 vs 0.928)")
def test_near_peak_efficiency(validation):
    assert check(validation, "near peak efficiency eta")["result"] == "pass"


def test_near_peak_failures_are_marked_expected(validation):
    for item in ("near peak efficiency PR", "near peak efficiency eta"):
        assert check(validation, item)["expected_failure"].startswith(NEAR_CHOKE)


def test_endwall_blockage_is_in_table_iv_areas(validation):
    blockage = validation["endwall_blockage"]
    assert (blockage["hub"], blockage["tip"]) == (0.015, 0.0126)
    assert abs(blockage["station_2"]["sum_vs_net"]) < 0.005  # areas are net of the stated blockage
    assert blockage["station_2"]["sum_vs_annulus"] < -0.02


def test_radial_profile_is_reported(validation):
    rows = validation["radial_profile_near_peak"]["rows"]
    assert len(rows) == 9
    assert all({"measured_Pt_ratio", "model_Pt_ratio", "difference"} <= set(r) for r in rows)


def test_all_sections_used_and_flagged_values_unused():
    geo = read_yaml(LEARNING / "rotor67_geometry.yaml")
    assert len(rotor67.build_tubes(geometry=geo)) == 9
    for key in ("le_metal_angle", "te_metal_angle", "meridional_chord"):
        assert len(rotor67.section_values(geo, key)) == 14, key
    geo["sections"][6]["le_metal_angle"]["flagged"] = True
    assert 6 / 13 not in [f for f, _ in rotor67.section_values(geo, "le_metal_angle")]


def section(geo, n):
    return geo["sections"][n - 1]


def test_geometry_matches_user_checked_values():
    """Values checked by the user against the TP-2879 scan (M1 step 2b)."""
    geo = read_yaml(LEARNING / "rotor67_geometry.yaml")
    assert round(section(geo, 4)["le_radius"]["value"], 2) == 13.27
    assert round(section(geo, 5)["le_radius"]["value"], 2) == 14.50
    assert round(section(geo, 12)["le_radius"]["value"], 2) == 23.09
    assert round(section(geo, 13)["te_radius"]["value"], 2) == 23.78
    assert section(geo, 4)["le_metal_angle"]["value"] == 43.42
    t_max = section(geo, 9)["max_thickness"]
    # Page image 0.42137 (override; OCR 0.42157, coordinate reference 0.42139). Location K=20 agrees.
    assert t_max["at_K"] == 20 and t_max["value"] == 0.42137
    assert section(geo, 7)["le_metal_angle"]["value"] == 51.41  # printed value, OCR 51.61
    s9 = {e["K"]: e for e in geo["value_log"] if e.get("section") == 9 and e["field"] == "TNPC"}
    assert s9[14]["read"] == 0.57605 and s9[14]["value"] == 0.37605  # 0.576 misread of 0.376, not the max


def test_overrides_are_applied_and_logged():
    geo = read_yaml(LEARNING / "rotor67_geometry.yaml")
    overrides = read_yaml(rotor67_tables.OVERRIDES)["overrides"]
    logged = {(e["section"], e["K"], e["field"]): e for e in geo["value_log"] if e["status"] == "override"}
    assert len(logged) == len(overrides) == 2
    for o in overrides:
        assert {"value", "evidence", "verified_by"} <= set(o)
        e = logged[(o["section"], o["K"], o["field"])]
        assert e["value"] == o["value"] and e["evidence"] == o["evidence"]
        column = 1 + rotor67_tables.ROW_FIELDS.index(o["field"])
        assert geo["points"]["sections"][o["section"] - 1]["rows"][o["K"] - 1][column] == o["value"]
    assert sum(1 for e in geo["value_log"] if (e.get("section"), e["K"], e["field"]) == (9, 20, "TNPC")) == 1


def test_angle_sensitivity_is_small(validation):
    """+-0.22 deg on all metal angles moves the design point PR by under 1 % and eta by under 0.5 point."""
    sens = validation["angle_sensitivity"]
    assert len(sens["cases"]) == 6
    for c in sens["cases"]:
        assert abs(c["delta_PR"]) / sens["base_PR"] < 0.01 and abs(c["delta_eta"]) < 0.005, c


def test_digital_copy_agrees_with_unflagged_ocr():
    geo = read_yaml(LEARNING / "rotor67_geometry.yaml")
    unflagged = geo["digital_vs_ocr"]["by_ocr_status"]["unflagged"]
    assert unflagged["compared"] > 1700 and unflagged["other"] == 0  # every difference is a 3/5, 4/6, 8/3 digit
    assert unflagged["equal_fraction"] > 0.85
    assert geo["digital_vs_ocr"]["unflagged_other_mismatches"] == []


def test_flowpath_ocr_repairs():
    geo = read_yaml(LEARNING / "rotor67_geometry.yaml")
    z = {p["K"]: p["Z"] for p in geo["flowpath"]["points"]}
    assert (z[1], z[2], z[5], z[6], z[7]) == (-18.05981, -17.38257, -15.35085, -14.67361, -13.99657)
    assert z[15] is None  # unreadable, left open
    assert len(geo["sections"]) == 14 and len(geo["flowpath"]["points"]) == 80
    survey = read_yaml(LEARNING / "rotor67_survey.yaml")
    assert {f["row"] for f in survey["flags"] if f["check"] == "radius_vs_table_IV"} == {1, 5, 8, 9}


def test_repair_value_prefers_fewest_substitutions():
    assert rotor67_tables.repair_value(63.42, 43.62, 0.6, 2) == (43.42, "repaired")  # not the 2-digit 43.62
    assert rotor67_tables.repair_value(42.0, 42.3, 0.6, 2) == (42.0, "as_read")
    assert rotor67_tables.repair_value(588.87, 38.42, 0.6, 2)[1] == "unresolved"
    assert rotor67_tables.fine_repair(0.42157, 0.42139, 0.00015, 0.004, 5) == (0.42137, "repaired_last_digit")
    assert rotor67_tables.fine_repair(43.42, 43.62, 0.015, 0.05, 2) == (43.42, "as_read")  # beyond the ceiling


@pytest.mark.skipif(not pdf_available(), reason="TP-2879 PDF or pdftotext not on this machine")
def test_extraction_reproduces_committed_yaml():
    geometry, survey = rotor67_tables.extract()
    assert read_yaml(rotor67_tables.GEOMETRY_OUT) == read_yaml_roundtrip(geometry)
    assert read_yaml(rotor67_tables.SURVEY_OUT) == read_yaml_roundtrip(survey)


def test_robust_outliers_do_not_condemn_neighbours():
    values = [0.27 * i for i in range(20)]
    values[6] += 2.0
    values[7] += 0.2
    assert set(rotor67_tables.robust_outliers(values, 0.02)) == {6, 7}


def test_read_stream_joins_split_decimals_and_skips_labels():
    rows, repairs = rotor67_tables.read_stream("12 4 06025 l0.75022 0 24212 -0 16572 0.80290 42 05 11.91 2808".split(),
                                               (5, 5, 5, 5, 5, 2, 2, 2), 1)
    assert rows == [[4.06025, 10.75022, 0.24212, -0.16572, 0.80290, 42.05, 11.91, 28.08]]
    assert any("-> 28.08" in r for r in repairs)
