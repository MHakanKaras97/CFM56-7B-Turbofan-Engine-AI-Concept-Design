"""Proposed tests for M2 geometry step 4 (rules/geometry.md R-G2.22-27; open issue #73): station 25 from the M1 frame
code, divider wall split at station 24, BOM from the geometry, assembly STEP, common volume over all instances,
record agreement. M0 moves this file to tests/test_m2_geometry4.py.

Imports from the repo root. No literal design value: counts, radii and areas come from the rev001 record, x values
from the M1 rev015 geometry code (read-only), tolerances from geometry_params.yaml. Slow (M2 hardware, M1 assembly,
all-instance common volume checks, STEP export).
"""

import re

import pytest

from core import bom as core_bom
from core import records
from core.util import read_yaml
from engine.M2_booster.analysis import calc
from engine.M2_booster.geometry import assembly as A
from engine.M2_booster.geometry import bom_update as BU
from engine.M2_booster.geometry import flowpath as FP
from engine.M2_booster.geometry import layout as L

TAG = r"\[(K|KS|H|G|T)\]"
RULES = L.M2_DIR / "rules" / "geometry.md"


@pytest.fixture(scope="module")
def asm():
    return A.build()


@pytest.fixture(scope="module")
def cv(asm):
    return A.common_volume_checks(asm)


def _gp(key):
    return float(L.v(L.geometry_params()[key]))


def test_step4_rules_plain_one_tag():
    text = RULES.read_text(encoding="utf-8")
    assert "## Geometry step 4: assembly, station 25, BOM" in text
    for n in range(22, 28):
        row = next(line for line in text.splitlines() if line.startswith(f"| R-G2.{n} |"))
        assert len(re.findall(TAG, row)) == 1, n
    assert "R-G2.24" in (L.M2_DIR / "rules" / "bom.md").read_text(encoding="utf-8")


def test_station_25_from_m1_code():
    """R-G2.22: x25 = aft end of the M1 frame core zone; hub ring and wall ring end there; struts end ahead; the duct
    walls are the station 24 radii; flowpath.yaml holds the same x (6 digits)."""
    s = FP.station_25()
    assert s["x25"] > s["x24"] == pytest.approx(L.layout()["x24"], abs=1e-12)
    assert s["x_end_hub_ring"] == pytest.approx(s["x25"], abs=1e-9)
    assert s["x_end_wall_ring"] == pytest.approx(s["x25"], abs=1e-9)
    assert s["x_end_core_strut"] < s["x25"]
    st25 = read_yaml(FP.OUT_FILE)["interfaces"]["M3_station_25"]
    assert st25["x_m"] == round(s["x25"], 6)
    assert s["r_hub_m1"] == pytest.approx(st25["r_hub_m"], abs=1e-6)
    assert s["r_tip_m1"] == pytest.approx(st25["r_tip_m"], abs=1e-6)
    res = records.read_revision("M2", A.INPUT_REVISION, "results.yaml")
    assert st25["r_hub_m"] == pytest.approx(float(res["station_24"]["r_hub"]), abs=5e-6)


def test_flowpath_build_reproduces_file():
    """calc.regenerate depends on flowpath.build reproducing the derived file."""
    assert FP.build() == read_yaml(FP.OUT_FILE)


def test_regenerate_reproduces_file_from_stale_state(tmp_path):
    """Two-pass regenerate (R-G2.22/26): a stale file (other x and a wrong radius) is rewritten to the same bytes."""
    path = FP.OUT_FILE
    good = path.read_bytes()
    stale = read_yaml(path)
    stale["interfaces"]["M3_station_25"]["x_m"] = 0.5
    stale["planes"][-1]["r_hub_m"] += 0.01
    try:
        from core.util import write_yaml
        write_yaml(path, stale)
        calc.regenerate(records.ROOT, records.active_revision("M2"))
        assert path.read_bytes() == good
    finally:
        path.write_bytes(good)
        calc._clear_geometry_caches()


def test_stale_file_refused_then_regenerated_passes_strict_check():
    """R-G2.26/ADR-013: outside regenerate a stale file is refused; calc.regenerate rewrites it without checking it,
    and afterwards the strict check passes again (sha256 for every record after rev001)."""
    path = FP.OUT_FILE
    good = path.read_bytes()
    rev = records.active_revision("M2")
    stale = read_yaml(path)
    stale["interfaces"]["M3_station_25"]["x_m"] = 0.5
    stale["planes"][-1]["r_hub_m"] += 0.01
    try:
        from core.util import write_yaml
        write_yaml(path, stale)
        calc._clear_geometry_caches()
        with pytest.raises(ValueError):
            L.record(rev)
        calc.regenerate(records.ROOT, rev)
        assert not L._REGENERATING
        rec = L.record(rev)
        assert rec["flowpath_check"] in ("sha256", "radii")
        assert rec["flowpath_check"] == "sha256" or rev in L.RELAXED_RECORDS
        manifest = records.read_revision("M2", rev, "manifest.yaml")
        results = records.read_revision("M2", rev, "results.yaml")
        assert L.flowpath_input_check(rev, path, manifest, results) in ("sha256", "radii")
    finally:
        path.write_bytes(good)
        calc._clear_geometry_caches()


def test_record_input_check():
    """R-G2.26: radii agree with the record at record precision; sha256 or radii check accepted."""
    rec = L.record()
    assert rec["flowpath_check"] in ("sha256", "radii")
    assert rec["flowpath_check"] == "sha256" or rec["revision"] in L.RELAXED_RECORDS
    assert L.flowpath_radii_deviation(rec["flowpath"], rec["results"]) <= 1.0


def _rev001_inputs():
    return (records.read_revision("M2", "rev001", "manifest.yaml"), records.read_revision("M2", "rev001", "results.yaml"))


def test_record_input_check_rev001_relaxed():
    """rev001 only: the current flowpath.yaml (with x_m, sha256 differs) passes on radii and area."""
    manifest, results = _rev001_inputs()
    assert L.RELAXED_RECORDS == ("rev001",)
    assert L.flowpath_input_check("rev001", L.M2_FLOWPATH, manifest, results) in ("sha256", "radii")
    assert L._sha256(L.M2_FLOWPATH) != {o["file"]: o["sha256"] for o in manifest["outputs"]}["geometry/flowpath.yaml"]


def test_record_input_check_strict_after_rev001(tmp_path):
    """rev002 and later: same radii but a wrong checksum is refused (ADR-013)."""
    manifest, results = _rev001_inputs()
    path = tmp_path / "flowpath.yaml"
    path.write_bytes(L.M2_FLOWPATH.read_bytes())
    for rev in ("rev002", "rev003"):
        with pytest.raises(ValueError):
            L.flowpath_input_check(rev, path, manifest, results)
    good = dict(manifest, outputs=[{"file": "geometry/flowpath.yaml", "sha256": L._sha256(path)}])
    assert L.flowpath_input_check("rev002", path, good, results) == "sha256"
    path.write_bytes(path.read_bytes() + b"# changed\n")
    with pytest.raises(ValueError):
        L.flowpath_input_check("rev002", path, good, results)


def test_casing_ends_at_station_24(asm):
    """R-G2.23: M2.0.2 ends at station 24, M1.4.6 starts there; no common volume, contact, no axial overlap."""
    cb = A.casing_boundary(asm)
    assert cb["x_casing"][1] == pytest.approx(cb["x24"], abs=1e-9)
    assert cb["x_wall_ring"][0] == pytest.approx(cb["x24"], abs=1e-9)
    assert cb["axial_overlap"] == 0.0 and cb["common_volume_m3"] == 0.0
    assert cb["distance_m"] == pytest.approx(0.0, abs=1e-7)


def test_blade_counts(asm):
    rc = A.record_checks(asm)
    assert rc["rotor_counts"] == rc["counts_record"][0] == [74, 78, 74]
    assert rc["stator_counts"] == rc["counts_record"][1] == [31, 39, 49]


def test_radii_areas_and_record_files(asm):
    rc = A.record_checks(asm)
    assert rc["areas_pass"] and rc["area_max_rel_dev"] <= _gp("area_tolerance")
    assert rc["radius_dev_half_digits"] <= 1.0
    assert all(rc["record_files_unchanged"].values()), rc["record_files_unchanged"]


def test_common_volume_m2_pairs(cv):
    s = cv["summary"]["M2-M2"]
    assert s["pairs"] > 0 and not s["fail"], s["fail"]
    assert s["max_fraction"] <= cv["tolerance"]


def test_common_volume_m2_vs_m1(cv):
    s = cv["summary"]["M2-M1"]
    assert s["pairs"] > 0 and not s["fail"], s["fail"]
    assert s["max_fraction"] <= cv["tolerance"]


def test_bom_written_from_geometry(asm):
    """R-G2.24: bom.yaml valid, equal to the proposed data, one entry per part, ids and names by the convention,
    qty = instance count, unit mass = mass table (4 decimals), owner M2."""
    data, rep = BU.apply(write=False)
    assert not rep.errors, rep.errors
    on_disk = core_bom.load(BU.BOM)
    assert on_disk["parts"] == data["parts"]
    assert core_bom.validate(BU.BOM) == []
    m = A.mass_table(asm)["parts"]
    ids = [p["id"] for p in on_disk["parts"]]
    assert ids == list(asm["parts"]) and len(ids) == len(set(ids))
    for p in on_disk["parts"]:
        stage, k = (int(x) for x in p["id"].split(".")[1:])
        assert re.fullmatch(r"M2\.\d\.\d", p["id"])
        assert p["name"].startswith("Booster " if stage == 0 else f"Booster Stage {stage} ")
        assert p["qty"]["value"] == asm["parts"][p["id"]]["qty"]
        assert p["mass"]["value"] == round(m[p["id"]]["unit_kg"], 4) and p["mass"]["tag"] == "H"
        assert p["parent"] is None
    assert not [p for p in on_disk["parts"] if p["id"].endswith(".3")]  # liners not modelled


def test_mass_information_only(asm):
    m = A.mass_table(asm)
    assert m["total_kg"] == pytest.approx(sum(r["set_kg"] for r in m["parts"].values()))
    assert m["check_value_kg"] == pytest.approx(A.LOLIS_ENGINE_KG * A.LOLIS_BOOSTER_SHARE)


def test_step_export(asm):
    paths = A.export(asm)
    assert paths[A.ASSEMBLY_NAME].name == "m2_assembly.step"
    assert paths[A.ASSEMBLY_NAME].parent.name == A.DESIGN_REVISION
    for pid in asm["parts"]:
        assert paths[pid].is_file() and paths[pid].stat().st_size > 0
