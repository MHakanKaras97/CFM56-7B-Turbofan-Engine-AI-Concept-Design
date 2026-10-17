from pathlib import Path

import pytest
import yaml

from core.bom import check, validate

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "bom_valid.yaml"
MODULE_BOMS = sorted(ROOT.glob("engine/M*/bom/bom.yaml"))


def load_fixture() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "bom.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def blade(data: dict) -> dict:
    return next(p for p in data["parts"] if p["id"] == "M1.1.1")


def test_valid_fixture_passes():
    assert validate(FIXTURE) == []


def test_bad_id_fails(tmp_path):
    data = load_fixture()
    blade(data)["id"] = "M1-1-1"
    assert any("M1-1-1" in e for e in validate(write(tmp_path, data)))


def test_id_prefix_mismatch_fails(tmp_path):
    data = load_fixture()
    blade(data)["id"] = "M2.1.1"
    assert any("prefix" in e for e in validate(write(tmp_path, data)))


def test_missing_tag_fails(tmp_path):
    data = load_fixture()
    del blade(data)["qty"]["tag"]
    assert any("'tag' is a required property" in e for e in validate(write(tmp_path, data)))


def test_duplicate_id_fails(tmp_path):
    data = load_fixture()
    data["parts"].append(dict(blade(data)))
    assert "duplicate id: M1.1.1" in validate(write(tmp_path, data))


def test_missing_parent_fails(tmp_path):
    data = load_fixture()
    blade(data)["parent"] = "M1.9"
    assert "M1.1.1: parent M1.9 not found" in validate(write(tmp_path, data))


def test_null_material_on_assembly_passes():
    data = load_fixture()
    assert next(p for p in data["parts"] if p["id"] == "M1.1")["material"] is None
    assert validate(FIXTURE) == []


def test_null_material_on_leaf_part_fails(tmp_path):
    data = load_fixture()
    blade(data)["material"] = None
    assert "M1.1.1: material is null but part has no children" in validate(write(tmp_path, data))


def test_missing_joint_target_in_same_module_fails(tmp_path):
    data = load_fixture()
    blade(data)["joints"][0]["to"] = "M1.1.9"
    assert "M1.1.1: joint target M1.1.9 not found" in validate(write(tmp_path, data))


def test_joint_target_in_other_module_is_warning(tmp_path):
    data = load_fixture()
    blade(data)["joints"][0]["to"] = "M8.1.1"
    report = check(write(tmp_path, data))
    assert report.errors == []
    assert any("M8.1.1" in w for w in report.warnings)


def test_all_ten_module_boms_present():
    assert len(MODULE_BOMS) == 10


@pytest.mark.parametrize("path", MODULE_BOMS, ids=lambda p: p.parts[-3])
def test_module_bom_valid(path):
    assert validate(path) == []
