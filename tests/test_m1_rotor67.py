"""M1 analysis A-1: Rotor 67 table extraction and meanline validation.

Acceptance [T] (rules/analyses.md A-1): tip M1rel and PR within 2 %, efficiency within 2 points.
Checks that do not meet it are strict xfail with the deviation in the reason: the model is not tuned
to pass, and a strict xfail turns red when a later model change makes the check pass.
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
    return rotor67_tables.PDF.is_file()


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


@pytest.mark.xfail(strict=True, reason="near peak efficiency PR -5.8 %: the two tip stream tubes choke at the exit")
def test_near_peak_pressure_ratio(validation):
    assert check(validation, "near peak efficiency PR")["result"] == "pass"


@pytest.mark.xfail(strict=True, reason="near peak efficiency eta -2.7 points (model 0.901 vs 0.928)")
def test_near_peak_efficiency(validation):
    assert check(validation, "near peak efficiency eta")["result"] == "pass"


def test_radial_profile_is_reported(validation):
    rows = validation["radial_profile_near_peak"]["rows"]
    assert len(rows) == 9
    assert all({"measured_Pt_ratio", "model_Pt_ratio", "difference"} <= set(r) for r in rows)


def test_streamline_count_and_flagged_values_unused():
    geo = read_yaml(LEARNING / "rotor67_geometry.yaml")
    tubes = rotor67.build_tubes(geometry=geo)
    assert 3 <= len(tubes) <= 9
    used = rotor67.section_values(geo, "le_metal_angle")
    flagged = {s["section"] for s in geo["sections"] if s["le_metal_angle"]["flagged"]}
    assert flagged and all((k - 1) / 13 not in [f for f, _ in used] for k in flagged)


def test_geometry_flags_known_ocr_errors():
    geo = read_yaml(LEARNING / "rotor67_geometry.yaml")
    hit = [f for f in geo["flags"] if f.get("section") == 1 and f.get("field") == "Z" and f.get("K") == 15]
    assert hit and 3.79207 in hit[0]["ocr_candidates"]  # 5.79207 printed, Z must increase by about 0.27
    assert len(geo["sections"]) == 14 and len(geo["flowpath"]["points"]) == 80
    survey = read_yaml(LEARNING / "rotor67_survey.yaml")
    assert {f["row"] for f in survey["flags"] if f["check"] == "radius_vs_table_IV"} == {1, 5, 8, 9}


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
