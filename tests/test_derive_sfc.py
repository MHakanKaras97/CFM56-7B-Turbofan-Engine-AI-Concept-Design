import pytest

from tools.derive_sfc import (
    DEFAULT_OUT,
    RULES,
    derive,
    g_per_kn_s_to_lb_per_lbf_h,
    sfc_g_per_kn_s,
)
from core.util import read_yaml


def test_sfc_formula():
    assert sfc_g_per_kn_s(1.0, 100.0) == pytest.approx(10.0)


def test_unit_conversion():
    # 1 lb/(lbf*h) = 28.3255 g/(kN*s)
    assert g_per_kn_s_to_lb_per_lbf_h(28.3255) == pytest.approx(1.0, rel=1e-5)


def test_superseded_rows_skipped():
    icao = {"rows": [
        {"uid": "A", "engine": "X", "superseded": None, "fuel_flow_to_kg_s": 1.0},
        {"uid": "B", "engine": "X", "superseded": "Yes", "fuel_flow_to_kg_s": 1.0},
    ]}
    tcds = {"ratings": {"CFM56-7B27": {"takeoff_thrust": {"value": 100.0}}}}
    assert [r["uid"] for r in derive(icao, tcds)["rows"]] == ["A"]


def test_committed_output_is_current():
    data = derive(read_yaml(RULES / "icao_edb_cfm56_7b27.yaml"), read_yaml(RULES / "tcds_e004.yaml"))
    assert read_yaml(DEFAULT_OUT) == data
    assert all(r["in_sanity_range"] for r in data["rows"])
