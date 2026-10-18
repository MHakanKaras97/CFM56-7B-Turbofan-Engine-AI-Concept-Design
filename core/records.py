"""Revision records.

Module level: engine/M*/records/revNNN/ holds manifest.yaml, bom.yaml (snapshot),
params.yaml and results.yaml; engine/M*/records/ACTIVE names the active revision.
Concept level: engine/M0_engine/records/conceptNNN/manifest.yaml pins one revision
(or null = not started) per module; engine/M0_engine/records/ACTIVE_CONCEPT names
the active concept.

Records are written once and never rewritten. Only ACTIVE / ACTIVE_CONCEPT change.
"""

import hashlib
import re
import shutil
import subprocess
from pathlib import Path

from core import bom as bom_io
from core.util import now_utc, read_yaml, schema_errors, write_yaml

ROOT = Path(__file__).resolve().parents[1]

REV_RE = re.compile(r"^rev(\d{3})$")
CONCEPT_RE = re.compile(r"^concept(\d{3})$")
MODULE_RE = re.compile(r"^(M\d)_")


class RecordError(Exception):
    pass


# --- helpers -----------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _code_commit(root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip() or None


def _check_schema(name: str, data) -> None:
    errors = schema_errors(name, data)
    if errors:
        raise RecordError(f"{name}: " + "; ".join(errors))


def _next_id(folder: Path, pattern: re.Pattern, prefix: str) -> str:
    numbers = [int(m.group(1)) for p in folder.iterdir() if p.is_dir() and (m := pattern.match(p.name))]
    n = max(numbers, default=0) + 1
    if n > 999:
        raise RecordError(f"no {prefix} ids left in {folder}")
    return f"{prefix}{n:03d}"


def _write_pointer(path: Path, value: str) -> None:
    path.write_text(value + "\n", encoding="utf-8", newline="\n")


def module_dir(module: str, root: Path = ROOT) -> Path:
    """Resolve 'M1' or 'M1_inlet_fan' to the module folder."""
    module_id = module.split("_")[0]
    matches = [p for p in (root / "engine").glob(f"{module_id}_*") if p.is_dir()]
    if len(matches) != 1:
        raise RecordError(f"module {module!r} not found (matches: {len(matches)})")
    return matches[0]


def module_dirs(root: Path = ROOT) -> list[Path]:
    return sorted(p for p in (root / "engine").iterdir() if p.is_dir() and MODULE_RE.match(p.name))


def active_revision(module: str, root: Path = ROOT) -> str | None:
    active = module_dir(module, root) / "records" / "ACTIVE"
    return active.read_text(encoding="utf-8").strip() if active.exists() else None


def is_dirty(module: str, root: Path = ROOT) -> bool:
    """True if there is no active revision or bom.yaml differs from its snapshot."""
    mdir = module_dir(module, root)
    rev = active_revision(module, root)
    if rev is None:
        return True
    snapshot = mdir / "records" / rev / "bom.yaml"
    return snapshot.read_bytes() != (mdir / "bom" / "bom.yaml").read_bytes()


def revision_ids(module: str, root: Path = ROOT) -> list[str]:
    """Recorded revisions of a module, oldest first."""
    records = module_dir(module, root) / "records"
    return sorted(p.name for p in records.iterdir() if p.is_dir() and REV_RE.match(p.name)) if records.is_dir() else []


def read_revision(module: str, rev: str, name: str, root: Path = ROOT):
    """Read one file of a record: manifest.yaml, bom.yaml, params.yaml or results.yaml."""
    if name not in ("manifest.yaml", "bom.yaml", "params.yaml", "results.yaml"):
        raise RecordError(f"{name}: not a record file")
    path = module_dir(module, root) / "records" / rev / name
    if not REV_RE.match(rev) or not path.is_file():
        raise RecordError(f"{module}: {rev}/{name} not found")
    return read_yaml(path)


# --- module revisions ----------------------------------------------------------

def create_revision(
    module: str,
    summary: str,
    reason: str,
    cr: str | None = None,
    params: dict | None = None,
    results: dict | None = None,
    outputs: list[str | Path] | None = None,
    root: Path = ROOT,
) -> str:
    """Snapshot the module's current state into a new revNNN and make it active."""
    mdir = module_dir(module, root)
    records = mdir / "records"
    bom_path = mdir / "bom" / "bom.yaml"

    errors = bom_io.validate(bom_path)
    if errors:
        raise RecordError(f"{bom_path} is invalid: " + "; ".join(errors))

    rev = _next_id(records, REV_RE, "rev")

    output_entries = []
    for out in outputs or []:
        out_path = Path(out)
        if not out_path.is_absolute():
            out_path = mdir / out_path
        try:
            rel = out_path.resolve().relative_to(mdir.resolve())
        except ValueError:
            raise RecordError(f"output {out} is outside {mdir}") from None
        if not out_path.is_file():
            raise RecordError(f"output {out} not found")
        output_entries.append({"file": rel.as_posix(), "sha256": _sha256(out_path)})

    manifest = {
        "revision": rev,
        "parent_revision": active_revision(module, root),
        "date": now_utc(),
        "summary": summary,
        "reason": reason,
        "change_request": cr,
        "code_commit": _code_commit(root),
        "outputs": output_entries,
    }
    _check_schema("manifest.schema.json", manifest)

    bom = bom_io.load(bom_path)
    bom["revision"] = rev

    rev_dir = records / rev
    rev_dir.mkdir(exist_ok=False)  # never overwrite an existing record
    bom_io.write(rev_dir / "bom.yaml", bom)
    write_yaml(rev_dir / "params.yaml", params or {})
    write_yaml(rev_dir / "results.yaml", results or {})
    write_yaml(rev_dir / "manifest.yaml", manifest)

    bom_io.write(bom_path, bom)
    _write_pointer(records / "ACTIVE", rev)
    return rev


def revert(module: str, rev: str, force: bool = False, root: Path = ROOT) -> None:
    """Make `rev` active and restore bom.yaml from its snapshot.

    Refuses if the working bom.yaml has unrecorded changes, unless force=True.
    """
    mdir = module_dir(module, root)
    snapshot = mdir / "records" / rev / "bom.yaml"
    if not REV_RE.match(rev) or not snapshot.exists():
        raise RecordError(f"{mdir.name}: revision {rev} not found")
    if not force and is_dirty(module, root):
        raise RecordError(f"{mdir.name}: bom.yaml has unrecorded changes; create a revision or use force")
    shutil.copyfile(snapshot, mdir / "bom" / "bom.yaml")
    _write_pointer(mdir / "records" / "ACTIVE", rev)


def verify(module: str, rev: str, root: Path = ROOT) -> list[str]:
    """Recompute output hashes of `rev`; return mismatches (empty list = OK)."""
    mdir = module_dir(module, root)
    manifest_path = mdir / "records" / rev / "manifest.yaml"
    if not manifest_path.exists():
        raise RecordError(f"{mdir.name}: revision {rev} not found")
    problems = []
    for entry in read_yaml(manifest_path).get("outputs", []):
        path = mdir / entry["file"]
        if not path.is_file():
            problems.append(f"{entry['file']}: missing")
        elif (actual := _sha256(path)) != entry["sha256"]:
            problems.append(f"{entry['file']}: sha256 mismatch (expected {entry['sha256']}, got {actual})")
    return problems


# --- engine concepts (M0) -----------------------------------------------------

def _concept_records(root: Path) -> Path:
    return module_dir("M0", root) / "records"


def active_concept(root: Path = ROOT) -> str | None:
    path = _concept_records(root) / "ACTIVE_CONCEPT"
    return path.read_text(encoding="utf-8").strip() if path.exists() else None


def read_concept(concept: str, root: Path = ROOT) -> dict:
    path = _concept_records(root) / concept / "manifest.yaml"
    if not CONCEPT_RE.match(concept) or not path.is_file():
        raise RecordError(f"concept {concept} not found")
    return read_yaml(path)


def create_concept(summary: str, root: Path = ROOT) -> str:
    """Pin the active revision of every module into a new conceptNNN.

    A module with no revision and an empty parts list is pinned as null (not started).
    """
    modules = {}
    for mdir in module_dirs(root):
        module_id = MODULE_RE.match(mdir.name).group(1)
        rev = active_revision(module_id, root)
        if rev is None:
            if read_yaml(mdir / "bom" / "bom.yaml").get("parts"):
                raise RecordError(f"{mdir.name}: has parts but no revision; create a revision first")
            modules[module_id] = None
        elif is_dirty(module_id, root):
            raise RecordError(f"{mdir.name}: bom.yaml has unrecorded changes")
        else:
            modules[module_id] = rev

    records = _concept_records(root)
    concept = _next_id(records, CONCEPT_RE, "concept")
    manifest = {
        "concept": concept,
        "parent_concept": active_concept(root),
        "date": now_utc(),
        "summary": summary,
        "modules": modules,
    }
    _check_schema("concept.schema.json", manifest)

    cdir = records / concept
    cdir.mkdir(exist_ok=False)  # never overwrite an existing record
    write_yaml(cdir / "manifest.yaml", manifest)
    _write_pointer(records / "ACTIVE_CONCEPT", concept)
    return concept


def revert_concept(concept: str, force: bool = False, root: Path = ROOT) -> None:
    """Restore every pinned module's ACTIVE pointer (and bom.yaml); null modules are skipped.

    All modules are checked before any is changed.
    """
    records = _concept_records(root)
    manifest_path = records / concept / "manifest.yaml"
    if not CONCEPT_RE.match(concept) or not manifest_path.exists():
        raise RecordError(f"concept {concept} not found")
    pinned = {m: rev for m, rev in read_yaml(manifest_path)["modules"].items() if rev is not None}

    for module_id, rev in pinned.items():
        mdir = module_dir(module_id, root)
        if not (mdir / "records" / rev / "bom.yaml").exists():
            raise RecordError(f"{mdir.name}: revision {rev} not found")
        if not force and is_dirty(module_id, root):
            raise RecordError(f"{mdir.name}: bom.yaml has unrecorded changes; create a revision or use force")

    for module_id, rev in pinned.items():
        revert(module_id, rev, force=True, root=root)
    _write_pointer(records / "ACTIVE_CONCEPT", concept)
