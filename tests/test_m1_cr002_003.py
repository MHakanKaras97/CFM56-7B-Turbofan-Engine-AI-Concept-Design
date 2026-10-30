"""Tests for M1 CR-002 option (a) and CR-003 (rules/geometry.md R-G1.1-R-G1.11), proposed by m1-inlet-fan.

Targets are read from the approved change requests (engine/M0_engine/requests/CR-002.yaml, CR-003.yaml: impact
metrics and BOM changes computed by engine/M0_engine/analysis/cr_impact_77.py), never typed here. Tolerances are
rounding of the CR values (6 decimals for lengths/areas, 4 for kg). The M2 overlap test builds the M2 hardware (slow,
about 2 min).
"""

import copy
import hashlib
import re

import pytest

from core import bom as core_bom
from core import records
from core.util import read_yaml
from engine.M1_inlet_fan.geometry import assembly as asm
from engine.M1_inlet_fan.geometry import bom_update as bu
from engine.M1_inlet_fan.geometry import fan_frame as ff
from engine.M1_inlet_fan.geometry import flowpath as fpm
from engine.M1_inlet_fan.geometry import m2_boundary as m2b
from engine.M1_inlet_fan.geometry import ogv as ogvm

ROOT = records.ROOT
REQ = ROOT / "engine" / "M0_engine" / "requests"
TOL_M = 5e-7  # 6-decimal rounding of the CR lengths / areas
TOL_KG = 5e-4  # 4-decimal rounding of the CR masses (sums of rounded terms)


def _metrics(cr: str) -> dict:
    return {k: v["value"] for k, v in read_yaml(REQ / f"{cr}.yaml")["impact"]["metrics"].items()}


def _bom_change(cr: str, path: str):
    return next(c["new"] for c in read_yaml(REQ / f"{cr}.yaml")["changes"] if c["path"] == path)


@pytest.fixture(scope="module")
def cr_a():
    return _metrics("CR-002")


@pytest.fixture(scope="module")
def cr_b():
    return _metrics("CR-003")


@pytest.fixture(scope="module")
def model():
    return asm.build()


@pytest.fixture(scope="module")
def frame(model):
    return model["frame"]


@pytest.fixture(scope="module")
def L(frame):
    return frame["layout"]


# --- rules file -------------------------------------------------------------------------------

def test_geometry_rules_rows_plain_one_tag_consecutive():
    text = (ROOT / "engine" / "M1_inlet_fan" / "rules" / "geometry.md").read_text(encoding="utf-8")
    rows = [r for r in text.splitlines() if r.startswith("| R-G1.")]
    ids = [int(re.match(r"\| R-G1\.(\d+) \|", r).group(1)) for r in rows]
    assert ids == list(range(1, len(ids) + 1)) and len(ids) >= 11
    for r in rows:
        assert "**" not in r
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        assert cells[-1] in ("[K]", "[KS]", "[H]", "[G]", "[T]")
        assert len(re.findall(r"\[(K|KS|H|G|T)\]", r)) == 1


# --- CR-002 option a ----------------------------------------------------------------------------

def test_no_splitter_ring_and_wall_ring_present(frame, model):
    assert "splitter_ring" not in frame["parts"] and "wall_ring" in frame["parts"]
    assert "M1.4.3" not in model["parts"] and model["parts"]["M1.4.6"]["name"] == "Fan Stage 1 Frame Core Wall Ring"


def test_root_radius_from_m2_casing(L, frame):
    """R-G1.3: r_root = r_split2 + M2 casing thickness, both from code (M2 hardware.build for the cross-check)."""
    from engine.M2_booster.geometry import hardware as HW
    hw = HW.build()["hw"]
    fp = frame["flowpath"]
    assert L["r_root"] == pytest.approx(fp["r_split2_m"] + hw["casing_thickness"], abs=1e-12)
    assert hw["r_casing"] == pytest.approx(fp["r_split2_m"], abs=1e-6)
    assert all(abs(v) < 1e-12 for v in m2b.cross_check().values())


def test_station_13_inner_radius_and_area(frame, cr_a):
    st = frame["flowpath"]["stations"]["13"]
    assert st["r_inner_m"] == pytest.approx(cr_a["M7_r13_inner_after"], abs=TOL_M)
    assert st["area_m2"] == pytest.approx(cr_a["A13_after"], abs=TOL_M)
    itf = read_yaml(fpm.OUT_YAML)["interfaces"]["M7_station_13"]
    assert itf["r_inner_m"] == round(st["r_inner_m"], 6) and itf["area_m2"] == round(st["area_m2"], 6)


def test_station_21_unchanged_for_m2(frame):
    """M2 reads station 21 from flowpath.yaml; CR-002 must not move it (tip = r_split2)."""
    st = frame["flowpath"]["stations"]["21"]
    assert st["r_tip_m"] == frame["flowpath"]["r_split2_m"]


def test_ogv_span_and_roots(frame, cr_a):
    og = ogvm.build()
    assert og["r_out"] - og["r_in"] == pytest.approx(cr_a["ogv_span_after"], abs=TOL_M)
    rr = ff.root_radii(frame)
    assert rr["ogv_root"] == pytest.approx(rr["r_root"], abs=1e-9)
    assert rr["bypass_strut_root"] == pytest.approx(rr["r_root"], abs=1e-9)


# --- CR-003 -------------------------------------------------------------------------------------

def test_core_zone_behind_station_24(L, frame, cr_b):
    m2 = m2b.m2_boundary()
    assert L["xc0"] == m2["x24"] and L["xc1"] - L["xc0"] == pytest.approx(L["x1"] - L["x0"], abs=1e-12)
    assert L["xc0"] - L["x0"] == pytest.approx(cr_b["frame_shift"], abs=TOL_M)
    assert L["x0"] == frame["flowpath"]["stations"]["13"]["x_m"] == pytest.approx(cr_b["x13_after"], abs=TOL_M)
    assert L["core_strut_x0"] - L["strut_x0"] == pytest.approx(cr_b["frame_shift"], abs=TOL_M)


def test_core_passage_is_m2_station_24_25(L):
    st25 = read_yaml(ROOT / "engine" / "M2_booster" / "geometry" / "flowpath.yaml")["interfaces"]["M3_station_25"]
    assert (L["r_hub"], L["r_core_out"]) == (st25["r_hub_m"], st25["r_tip_m"])
    assert L["r_bearing"] < L["r_hub"] - L["t_hub"] < L["r_hub"] < L["r_core_out"] <= L["r_root"] < L["r_wall"]


def test_m8_flange(frame, cr_b):
    m8 = ff.interfaces(frame)["M8_bearing_support"]
    assert m8["x_face_m"][1] == pytest.approx(cr_b["M8_flange_x_aft_after"], abs=TOL_M)
    assert m8["r_inner_m"] == pytest.approx(cr_b["M8_flange_r_inner"], abs=TOL_M)


def test_length(model, cr_b):
    assert asm.extent(model)["length_m"] == pytest.approx(cr_b["M1_length_after"], abs=TOL_M)


def test_wall_ring_continues_m2_casing(L):
    from engine.M2_booster.geometry import hardware as HW
    cas = HW.build()["parts"]["casing"]
    w = ff.build()["parts"]["wall_ring"]
    bb = w.BoundingBox()
    assert bb.xmin == pytest.approx(L["x24"], abs=1e-9) and bb.xmax == pytest.approx(L["xc1"], abs=1e-9)
    assert w.distance(cas) <= 1e-6


# --- masses -------------------------------------------------------------------------------------

@pytest.mark.parametrize("pid,cr", [("M1.3.1", "CR-002"), ("M1.4.4", "CR-002"), ("M1.4.1", "CR-003"),
                                    ("M1.4.5", "CR-003")])
def test_unit_masses_match_cr(model, pid, cr):
    m = asm.mass_table(model)["parts"][pid]["unit_kg"]
    assert m == pytest.approx(_bom_change(cr, f"parts[{pid}].mass")["value"], abs=5e-5)


def test_wall_ring_mass_matches_cr(model):
    new = _bom_change("CR-003", "parts[M1.4.6]")
    assert asm.mass_table(model)["parts"]["M1.4.6"]["unit_kg"] == pytest.approx(new["mass"]["value"], abs=5e-5)


def test_total_mass_after_cr002_and_cr003(model, cr_a, cr_b):
    m = asm.mass_table(model)
    assert m["total_kg"] == pytest.approx(cr_b["M1_mass_after_A_and_B"], abs=TOL_KG)
    # CR-002 alone: undo CR-003 with the pre-CR-003 core-side parts rebuilt from the same rules (bypass-zone x,
    # station 21 hub radius, core passage outer radius r_split2 - t_ref)
    L = model["frame"]["layout"]
    st21 = model["frame"]["flowpath"]["stations"]["21"]
    L0 = dict(L, xc0=L["x0"], xc1=L["x1"], core_strut_x0=L["strut_x0"], r_hub=st21["r_hub_m"],
              r_core_out=L["r_split"] - L["t_ref"])
    rho = m["parts"]["M1.4.1"]["density"]
    old_b = (ff.hub_ring(L0).Volume() + L["n_struts"] * ff.strut(L0, L0["r_hub"], L0["r_core_out"], "core").Volume()) * rho
    new_b = m["parts"]["M1.4.1"]["set_kg"] + m["parts"]["M1.4.5"]["set_kg"] + m["parts"]["M1.4.6"]["set_kg"]
    assert m["total_kg"] - new_b + old_b == pytest.approx(cr_a["M1_mass_after"], abs=TOL_KG)
    assert new_b - old_b == pytest.approx(cr_b["dM1_mass"], abs=TOL_KG)


# --- BOM ------------------------------------------------------------------------------------------

def test_bom_cr_parts():
    by_id = {p["id"]: p for p in core_bom.load(bu.BOM)["parts"]}
    assert "M1.4.3" not in by_id
    new = _bom_change("CR-003", "parts[M1.4.6]")
    w = by_id["M1.4.6"]
    for k in ("name", "parent", "qty", "function", "material", "status", "mass"):
        assert w[k] == new[k], k
    for pid, cr in (("M1.3.1", "CR-002"), ("M1.4.4", "CR-002"), ("M1.4.1", "CR-003"), ("M1.4.5", "CR-003")):
        cr_note = _bom_change(cr, f"parts[{pid}].notes")
        old_note = next(c["old"] for c in read_yaml(REQ / f"{cr}.yaml")["changes"] if c["path"] == f"parts[{pid}].notes")
        assert by_id[pid]["notes"].startswith(old_note), pid  # old text kept, CR sentence appended
        for num in re.findall(r"\d+\.\d{6}", cr_note):  # every CR number is in the generated note
            assert num in by_id[pid]["notes"], (pid, num)
    assert "M2.0.2" in by_id["M1.4"]["notes"] and "#48" in by_id["M1.4"]["notes"]


def test_bom_idempotent_and_valid(model):
    data = core_bom.load(bu.BOM)

    def nr(d):
        d = copy.deepcopy(d)
        d.pop("revision", None)
        return core_bom.canonical(d)

    assert nr(bu.proposed(model)) == nr(data)
    rep = core_bom.check_data(data)
    assert rep.errors == [] and rep.warnings == []


def test_rotor_case_bom_entries_unchanged():
    """Parts outside the CR scope equal the active record BOM (fan blade, disk, case, ...)."""
    rec = {p["id"]: p for p in records.read_revision("M1", records.active_revision("M1"), "bom.yaml")["parts"]}
    cur = {p["id"]: p for p in core_bom.load(bu.BOM)["parts"]}
    cr_scope = {"M1.3.1", "M1.4", "M1.4.1", "M1.4.3", "M1.4.4", "M1.4.5", "M1.4.6"}
    for pid in set(rec) - cr_scope:
        assert cur[pid] == rec[pid], pid


def test_fan_params_and_results_unchanged():
    """analysis/fan_params.yaml and results.yaml keep the sha256 of the active record (cycle and blade unchanged)."""
    rev = records.active_revision("M1")
    man = records.read_revision("M1", rev, "manifest.yaml")
    base = ROOT / "engine" / "M1_inlet_fan"
    for o in man["outputs"]:
        if o["file"] in ("analysis/fan_params.yaml", "analysis/results.yaml"):
            assert hashlib.sha256((base / o["file"]).read_bytes()).hexdigest() == o["sha256"], o["file"]


# --- interference -------------------------------------------------------------------------------

def test_no_interference_inside_m1(frame, model):
    bad = {k: r["common_volume_m3"] for k, r in ff.checks(frame).items() if r["common_volume_m3"] > 1e-12}
    assert not bad
    assert all(v <= 1e-12 for v in asm.interference_summary(model).values())


def test_no_common_volume_with_m2(frame, cr_a, cr_b):
    """R-G1.11: M2 hardware.m1_overlap (read-only) finds no common volume; CR after-values are 0."""
    c = ff.m2_checks(frame)
    assert c["overlaps"] == [] and cr_a["M2_common_volume_after"] == cr_b["M2_common_volume_after"] == 0.0
    assert all(d <= 1e-6 for d in c["distance_m"].values())
