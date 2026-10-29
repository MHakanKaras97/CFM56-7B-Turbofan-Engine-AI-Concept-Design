"""M1 step 5g: full assembly (geometry/assembly.py) and the applied BOM update (geometry/bom_update.py).

Acceptance: one STEP with every M1 instance plus the per-part STEPs, mass table per part id with the M1 total,
ICD comparison reported (not relaxed); bom.yaml equals the proposed update (idempotent, top-level revision ignored),
is valid, has the new parts, no tbd material, and its masses match the assembly mass table.
"""

import copy

import pytest

from core import bom as core_bom
from engine.M1_inlet_fan.geometry import assembly as asm
from engine.M1_inlet_fan.geometry import bom_update as bu


@pytest.fixture(scope="module")
def model():
    return asm.build()


@pytest.fixture(scope="module")
def bom():
    return core_bom.load(bu.BOM)


def _no_rev(d):
    d = copy.deepcopy(d)
    d.pop("revision", None)
    return core_bom.canonical(d)


def test_all_parts_and_counts(model):
    p = model["parts"]
    assert set(p) == set(bu.SCRIPTS)
    assert p["M1.1.1"]["qty"] == p["M1.1.4"]["qty"] == p["M1.1.5"]["qty"] == p["M1.1.6"]["qty"] == 24
    assert p["M1.3.1"]["qty"] == model["ogv"]["V"]
    assert p["M1.4.4"]["qty"] == p["M1.4.5"]["qty"] == model["frame"]["layout"]["n_struts"]
    for pid, part in p.items():
        assert part["shape"].isValid() and part["shape"].Volume() > 0, pid


def test_mass_table(model):
    m = asm.mass_table(model)
    for r in m["parts"].values():
        assert r["set_kg"] == pytest.approx(r["qty"] * r["volume_m3"] * r["density"], rel=1e-12)
    assert m["total_kg"] == pytest.approx(sum(m["groups_kg"].values()), rel=1e-12)
    assert m["total_kg"] > 0


def test_icd_comparison_reported(model):
    c = asm.icd_comparison(model)
    assert c["total_kg"] > 0 and c["length_m"] > 0
    assert c["status"].startswith("compared") or not c["icd_items"]


def test_cross_stage_no_interference(model):
    assert all(v <= 1e-12 for v in asm.interference_summary(model).values())


def test_assembly_step(model):
    paths = asm.export(model)
    p = paths[asm.ASSEMBLY_NAME]
    assert p.name == "m1_assembly.step" and p.parent.name == model["revision"]
    assert p.stat().st_size > 0 and len(paths) > 15
    assert all(q.exists() for q in paths.values())


def test_bom_valid(bom):
    rep = core_bom.check_data(bom)
    assert rep.errors == [] and rep.warnings == []


def test_bom_equals_proposed_update(model, bom):
    assert _no_rev(bu.proposed(model)) == _no_rev(bom)


def test_bom_parts_materials_status(bom):
    by_id = {p["id"]: p for p in bom["parts"]}
    assert set(bu.SCRIPTS) | {"M1.1", "M1.2", "M1.3", "M1.4"} <= set(by_id)
    assert all(p["material"] != "tbd" for p in bom["parts"])
    assert all(p["status"] in ("draft", "review") for p in bom["parts"])
    assert by_id["M1.1.2"]["status"] == "draft" and by_id["M1.1"]["status"] == "draft"  # disk margin, #32
    assert by_id["M1.3"]["material"] is None and by_id["M1.4"]["material"] is None
    for pid in bu.SCRIPTS:
        assert by_id[pid]["geometry"] == {"script": bu.SCRIPTS[pid], "params": {"revision": bu.GEOMETRY_REVISION}}


def test_bom_masses_match_assembly(model, bom):
    by_id = {p["id"]: p for p in bom["parts"]}
    m = asm.mass_table(model)["parts"]
    for pid, r in m.items():
        assert by_id[pid]["mass"] == {"value": round(r["unit_kg"], 4), "unit": "kg", "tag": "H"}, pid
        assert by_id[pid]["qty"]["value"] == r["qty"], pid
