"""M1 step 1 data: Rotor 67 reference, materials, BOM and agent definition."""

import math
import warnings
from pathlib import Path

import yaml

from core.bom import load as load_bom
from core.records import active_revision, design_drift, read_revision, reproduce, verify

ROOT = Path(__file__).resolve().parents[1]
M1 = ROOT / "engine" / "M1_inlet_fan"
TAGS = {"K", "KS", "H", "G", "T"}
GAMMA_AIR = 1.4  # [G] cold air, as used for the Rotor 67 check only


def read(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def quantities(node, path=""):
    """Every dict carrying a `value` key, with its path."""
    if isinstance(node, dict):
        if "value" in node:
            yield path, node
        for key, child in node.items():
            yield from quantities(child, f"{path}.{key}")
    elif isinstance(node, list):
        for i, child in enumerate(node):
            yield from quantities(child, f"{path}[{i}]")


def isentropic_efficiency(pr: float, tr: float) -> float:
    return (pr ** ((GAMMA_AIR - 1) / GAMMA_AIR) - 1) / (tr - 1)


def test_rotor67_values_are_tagged():
    data = read(M1 / "learning" / "rotor67_reference.yaml")
    found = list(quantities(data))
    assert len(found) > 20
    for path, q in found:
        assert q.get("tag") in TAGS, path
        assert "unit" in q, path


def test_rotor67_tip_speed_consistent_with_speed_and_diameter():
    design = read(M1 / "learning" / "rotor67_reference.yaml")["design"]
    omega = design["rotational_speed"]["value"] * 2 * math.pi / 60
    r_tip = design["inlet_tip_diameter"]["value"] / 2 / 100
    assert abs(omega * r_tip / design["tip_speed"]["value"] - 1) < 0.015


def test_rotor67_measured_efficiency_from_pr_and_tr():
    measured = read(M1 / "learning" / "rotor67_reference.yaml")["measured"]
    stall = measured["near_stall"]
    eta = isentropic_efficiency(stall["pressure_ratio"]["value"], stall["temperature_ratio"]["value"])
    assert abs(eta - stall["efficiency"]["value"]) < 0.005

    peak = measured["near_peak_efficiency"]
    eta_peak = isentropic_efficiency(peak["pressure_ratio"]["value"], peak["temperature_ratio"]["value"])
    assert peak["efficiency"]["tag"] == "H"
    assert round(eta_peak, 3) == peak["efficiency"]["value"]
    assert abs(eta_peak - 0.95) > 0.01, "OCR value 0.95 would be consistent; revisit the yaml note"


def test_rotor67_stream_tube_areas_cover_the_annulus():
    ref = read(M1 / "learning" / "rotor67_reference.yaml")
    stations = ref["survey_stations"]
    for name, key in (("station_1", "station_1_upstream"), ("station_2", "station_2_downstream")):
        r_o, r_i = stations[key]["shroud_radius"]["value"], stations[key]["hub_radius"]["value"]
        annulus = math.pi * (r_o ** 2 - r_i ** 2)
        fraction = sum(ref["stream_tube_areas"][name]) / annulus
        assert 0.95 < fraction < 1.0, (name, fraction)  # endwall blockage of a few percent


def test_materials_tagged_and_sourced():
    materials = read(ROOT / "tools" / "data" / "materials.yaml")["materials"]
    for mid, mat in materials.items():
        assert mat["source"]["primary"], mid
        for path, q in quantities(mat):
            assert q.get("tag") in TAGS, f"{mid}{path}"


def test_m1_bom_materials_known_and_blade_count():
    materials = read(ROOT / "tools" / "data" / "materials.yaml")["materials"]
    parts = load_bom(M1 / "bom" / "bom.yaml")["parts"]
    for part in parts:
        assert part["material"] in materials or part["material"] in (None, "tbd"), part["id"]
        assert part["status"] in ("draft", "review"), part["id"]  # step 5g: concept-built parts in review, none approved
        if "geometry" in part:
            assert part["geometry"]["script"].startswith("engine/M1_inlet_fan/geometry/"), part["id"]
    blade = next(p for p in parts if p["id"] == "M1.1.1")
    assert blade["qty"] == {"value": 24, "unit": "ea", "tag": "KS"}


def test_m1_active_record_verifies():
    rev = active_revision("M1")
    assert rev is not None
    assert verify("M1", rev) == []
    assert read_revision("M1", rev, "params.yaml") and read_revision("M1", rev, "results.yaml")  # else reproduce is empty
    assert reproduce("M1", rev) == []  # with the record's own code_commit (ADR-013)


def test_m1_design_drift_info():
    """Info only: current code differs from the active record -> new revision needed (ADR-013)."""
    rev = active_revision("M1")
    if keys := design_drift("M1", rev):
        warnings.warn(f"M1 {rev}: design drift, new revision needed ({len(keys)} keys: {', '.join(keys[:5])})")


def test_m1_agent_cannot_spawn_agents():
    text = (ROOT / ".claude" / "agents" / "m1-inlet-fan.md").read_text(encoding="utf-8")
    front = yaml.safe_load(text.split("---")[1])
    assert front["name"] == "m1-inlet-fan" and front["description"]
    tools = [t.strip() for t in front["tools"].split(",")]
    assert "Agent" not in tools
