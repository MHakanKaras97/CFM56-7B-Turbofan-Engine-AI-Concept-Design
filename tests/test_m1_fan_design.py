"""M1 first fan design (analysis/fan_design.py -> analysis/results.yaml), recorded as M1 rev002.

Reads the generated results only; the full re-run is covered by core.records.verify/reproducible.
"""

from core.budgets import read_icd
from core.records import ROOT, module_dir, verify
from core.util import read_yaml

RESULTS = module_dir("M1", ROOT) / "analysis" / "results.yaml"


def results():
    return read_yaml(RESULTS)


def test_annulus_matches_icd_fan_face_area():
    assert results()["annulus"]["fan_face_area_check"] == "pass"


def test_each_tube_meets_its_stream_pressure_ratio():
    budget = read_icd("M1 test")["modules"]["M1"]["budget"]
    target = {"outer": budget["FPR"]["value"], "inner": budget["pr_fan_inner"]["value"]}
    tubes = results()["tubes"]
    assert len(tubes) == 9
    for t in tubes:
        assert abs(t["Pt_ratio"] - target[t["stream"]]) <= 1e-4, t["name"]


def test_core_mass_flow_is_w21():
    w21 = read_icd("M1 test")["modules"]["M1"]["budget"]["W21"]["value"]
    inner = sum(t["mass_flow_kg_s"] for t in results()["tubes"] if t["stream"] == "inner")
    assert abs(inner / w21 - 1) <= 1e-6


def test_root_stress_has_margin():
    assert results()["mechanical"]["margin"] > 0


def test_budget_rows_cover_achieved_items():
    r = results()
    assert [row["item"] for row in r["budget_check"]] == list(r["achieved"])


def test_rev002_record_verifies():
    assert verify("M1", "rev002") == []
