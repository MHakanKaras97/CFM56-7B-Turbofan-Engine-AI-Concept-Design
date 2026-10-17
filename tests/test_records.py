import shutil
from pathlib import Path

import pytest
import yaml

from core import records
from core.bom import write as write_bom
from core.records import (
    RecordError,
    active_concept,
    active_revision,
    create_concept,
    create_revision,
    revert,
    revert_concept,
    verify,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "bom_valid.yaml"
NO_RECORDS = shutil.ignore_patterns("rev[0-9][0-9][0-9]", "concept[0-9][0-9][0-9]", "ACTIVE", "ACTIVE_CONCEPT", "CR-*.yaml")


@pytest.fixture
def repo(tmp_path) -> Path:
    """Temp copy of engine/ without records or CRs; tests never touch the real module folders."""
    shutil.copytree(ROOT / "engine", tmp_path / "engine", ignore=NO_RECORDS)
    shutil.copyfile(FIXTURE, tmp_path / "engine" / "M1_inlet_fan" / "bom" / "bom.yaml")
    return tmp_path


def bom_path(repo: Path) -> Path:
    return repo / "engine" / "M1_inlet_fan" / "bom" / "bom.yaml"


def rev_dir(repo: Path, rev: str) -> Path:
    return repo / "engine" / "M1_inlet_fan" / "records" / rev


def edit_bom(repo: Path, blade_count: int) -> None:
    data = yaml.safe_load(bom_path(repo).read_text(encoding="utf-8"))
    data["parts"][1]["qty"]["value"] = blade_count
    write_bom(bom_path(repo), data)


def test_create_revision(repo):
    rev = create_revision("M1", "Initial fan BOM", "Baseline", root=repo)

    assert rev == "rev001"
    assert active_revision("M1", root=repo) == "rev001"
    for name in ("manifest.yaml", "bom.yaml", "params.yaml", "results.yaml"):
        assert (rev_dir(repo, rev) / name).is_file()
    manifest = yaml.safe_load((rev_dir(repo, rev) / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["parent_revision"] is None
    assert "status" not in manifest
    assert manifest["change_request"] is None
    assert yaml.safe_load(bom_path(repo).read_text(encoding="utf-8"))["revision"] == "rev001"
    assert (rev_dir(repo, rev) / "bom.yaml").read_bytes() == bom_path(repo).read_bytes()


def test_second_revision_links_parent(repo):
    create_revision("M1", "Initial", "Baseline", root=repo)
    edit_bom(repo, 26)
    rev = create_revision("M1", "More blades", "Test", cr="CR-001", root=repo)

    assert rev == "rev002"
    assert active_revision("M1", root=repo) == "rev002"
    m2 = yaml.safe_load((rev_dir(repo, "rev002") / "manifest.yaml").read_text(encoding="utf-8"))
    assert m2["parent_revision"] == "rev001"
    assert m2["change_request"] == "CR-001"


def test_no_overwrite(repo, monkeypatch):
    create_revision("M1", "Initial", "Baseline", root=repo)
    before = (rev_dir(repo, "rev001") / "bom.yaml").read_bytes()

    edit_bom(repo, 26)
    monkeypatch.setattr(records, "_next_id", lambda *args: "rev001")
    with pytest.raises(FileExistsError):
        create_revision("M1", "Clash", "Test", root=repo)

    assert (rev_dir(repo, "rev001") / "bom.yaml").read_bytes() == before
    assert active_revision("M1", root=repo) == "rev001"


def test_invalid_bom_is_not_recorded(repo):
    bom_path(repo).write_text("module_id: M1\n", encoding="utf-8", newline="\n")
    with pytest.raises(RecordError):
        create_revision("M1", "Broken", "Test", root=repo)
    assert not rev_dir(repo, "rev001").exists()


def test_revert_restores_bom(repo):
    create_revision("M1", "Initial", "Baseline", root=repo)
    original = bom_path(repo).read_bytes()
    edit_bom(repo, 26)
    create_revision("M1", "More blades", "Test", root=repo)
    assert bom_path(repo).read_bytes() != original

    revert("M1", "rev001", root=repo)

    assert bom_path(repo).read_bytes() == original
    assert active_revision("M1", root=repo) == "rev001"


def test_records_never_rewritten(repo):
    create_revision("M1", "Initial", "Baseline", root=repo)
    snapshot = {p.name: p.read_bytes() for p in rev_dir(repo, "rev001").iterdir()}

    edit_bom(repo, 26)
    create_revision("M1", "More blades", "Test", root=repo)
    revert("M1", "rev001", root=repo)
    revert("M1", "rev002", root=repo)

    assert {p.name: p.read_bytes() for p in rev_dir(repo, "rev001").iterdir()} == snapshot


def test_revert_refuses_unrecorded_changes(repo):
    create_revision("M1", "Initial", "Baseline", root=repo)
    edit_bom(repo, 30)
    with pytest.raises(RecordError, match="unrecorded"):
        revert("M1", "rev001", root=repo)
    revert("M1", "rev001", force=True, root=repo)
    assert yaml.safe_load(bom_path(repo).read_text(encoding="utf-8"))["parts"][1]["qty"]["value"] == 24


def test_verify_detects_changed_output(repo):
    out = repo / "engine" / "M1_inlet_fan" / "geometry" / "blade.stl"
    out.write_bytes(b"solid blade\nendsolid blade\n")
    rev = create_revision("M1", "With geometry", "Test", outputs=["geometry/blade.stl"], root=repo)
    assert verify("M1", rev, root=repo) == []

    out.write_bytes(b"solid blade\nfacet\nendsolid blade\n")
    problems = verify("M1", rev, root=repo)
    assert len(problems) == 1 and "sha256 mismatch" in problems[0]

    out.unlink()
    assert verify("M1", rev, root=repo) == ["geometry/blade.stl: missing"]


def test_concept_revert(repo):
    for mdir in sorted((repo / "engine").glob("M[0-9]_*")):
        create_revision(mdir.name, "Initial", "Baseline", root=repo)
    c1 = create_concept("Baseline concept", root=repo)
    original = bom_path(repo).read_bytes()

    edit_bom(repo, 26)
    create_revision("M1", "More blades", "Test", root=repo)
    c2 = create_concept("More fan blades", root=repo)

    assert (c1, c2) == ("concept001", "concept002")
    c2_manifest = yaml.safe_load(
        (repo / "engine" / "M0_engine" / "records" / c2 / "manifest.yaml").read_text(encoding="utf-8")
    )
    assert c2_manifest["parent_concept"] == "concept001"
    assert c2_manifest["modules"]["M1"] == "rev002"
    assert len(c2_manifest["modules"]) == 10

    revert_concept(c1, root=repo)

    assert active_concept(root=repo) == "concept001"
    assert active_revision("M1", root=repo) == "rev001"
    assert bom_path(repo).read_bytes() == original


def test_concept_with_unstarted_modules(repo):
    create_revision("M1", "Initial", "Baseline", root=repo)
    c1 = create_concept("Fan only", root=repo)
    manifest = yaml.safe_load(
        (repo / "engine" / "M0_engine" / "records" / c1 / "manifest.yaml").read_text(encoding="utf-8")
    )
    assert manifest["modules"]["M1"] == "rev001"
    assert manifest["modules"]["M3"] is None
    assert sum(v is None for v in manifest["modules"].values()) == 9

    edit_bom(repo, 26)
    create_revision("M1", "More blades", "Test", root=repo)
    revert_concept(c1, root=repo)

    assert active_revision("M1", root=repo) == "rev001"
    assert active_revision("M3", root=repo) is None


def test_concept_refuses_unrecorded_module_with_parts(repo):
    with pytest.raises(RecordError, match="no revision"):
        create_concept("Fan not recorded", root=repo)
