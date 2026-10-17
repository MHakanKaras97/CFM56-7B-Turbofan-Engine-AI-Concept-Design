"""Revision records.

Module level: engine/M*/records/revNNN/ holds manifest.yaml, bom.yaml (snapshot),
params.yaml and results.yaml; engine/M*/records/ACTIVE names the active revision.
Concept level: engine/M0_engine/records/conceptNNN/manifest.yaml pins one revision
per module; engine/M0_engine/records/ACTIVE_CONCEPT names the active concept.

Records are never overwritten. The only field rewritten after creation is the
manifest `status`, which is kept in sync with ACTIVE.
"""

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from core.bom import validate as validate_bom

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = Path(__file__).parent / "schemas"

REV_RE = re.compile(r"^rev(\d{3})$")
CONCEPT_RE = re.compile(r"^concept(\d{3})$")
MODULE_RE = re.compile(r"^(M\d)_")


class RecordError(Exception):
    pass


# --- helpers -----------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _read_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, data) -> None:
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8", newline="\n",
    )


def _check_schema(name: str, data) -> None:
    schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    errors = [e.message for e in Draft202012Validator(schema).iter_errors(data)]
    if errors:
        raise RecordError(f"{name}: " + "; ".join(errors))


def _next_id(folder: Path, pattern: re.Pattern, prefix: str) -> str:
    numbers = [int(m.group(1)) for p in folder.iterdir() if p.is_dir() and (m := pattern.match(p.name))]
    n = max(numbers, default=0) + 1
    if n > 999:
        raise RecordError(f"no {prefix} ids left in {folder}")
    return f"{prefix}{n:03d}"


def module_dir(module: str, root: Path = ROOT) -> Path:
    """Resolve 'M1' or 'M1_inlet_fan' to the module folder."""
    module_id = module.split("_")[0]
    matches = [p for p in (root / "engine").glob(f"{module_id}_*") if p.is_dir()]
    if len(matches) != 1:
        raise RecordError(f"module {module!r} not found (matches: {len(matches)})")
    return matches[0]


def _module_dirs(root: Path) -> list[Path]:
    return sorted(p for p in (root / "engine").iterdir() if p.is_dir() and MODULE_RE.match(p.name))


def active_revision(module: str, root: Path = ROOT) -> str | None:
    active = module_dir(module, root) / "records" / "ACTIVE"
    return active.read_text(encoding="utf-8").strip() if active.exists() else None


def _set_active(mdir: Path, rev: str) -> None:
    records = mdir / "records"
    for rdir in records.iterdir():
        if not (rdir.is_dir() and REV_RE.match(rdir.name)):
            continue
        manifest_path = rdir / "manifest.yaml"
        manifest = _read_yaml(manifest_path)
        status = "active" if rdir.name == rev else "superseded"
        if manifest.get("status") != status:
            manifest["status"] = status
            _write_yaml(manifest_path, manifest)
    (records / "ACTIVE").write_text(rev + "\n", encoding="utf-8", newline="\n")


def _is_dirty(mdir: Path) -> bool:
    """True if the working bom.yaml differs from the active snapshot."""
    active = mdir / "records" / "ACTIVE"
    if not active.exists():
        return True
    rev = active.read_text(encoding="utf-8").strip()
    snapshot = mdir / "records" / rev / "bom.yaml"
    return snapshot.read_bytes() != (mdir / "bom" / "bom.yaml").read_bytes()


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

    errors = validate_bom(bom_path)
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
        "date": _now(),
        "summary": summary,
        "reason": reason,
        "change_request": cr,
        "code_commit": _code_commit(root),
        "outputs": output_entries,
        "status": "active",
    }
    _check_schema("manifest.schema.json", manifest)

    bom_text = bom_path.read_bytes().decode("utf-8")
    bom_text = re.sub(r"(?m)^revision:.*$", f"revision: {rev}", bom_text, count=1)

    rev_dir = records / rev
    rev_dir.mkdir(exist_ok=False)  # never overwrite an existing record
    (rev_dir / "bom.yaml").write_bytes(bom_text.encode("utf-8"))
    _write_yaml(rev_dir / "params.yaml", params or {})
    _write_yaml(rev_dir / "results.yaml", results or {})
    _write_yaml(rev_dir / "manifest.yaml", manifest)

    bom_path.write_bytes(bom_text.encode("utf-8"))
    _set_active(mdir, rev)
    return rev


def revert(module: str, rev: str, force: bool = False, root: Path = ROOT) -> None:
    """Make `rev` active and restore bom.yaml from its snapshot.

    Refuses if the working bom.yaml has unrecorded changes, unless force=True.
    """
    mdir = module_dir(module, root)
    snapshot = mdir / "records" / rev / "bom.yaml"
    if not REV_RE.match(rev) or not snapshot.exists():
        raise RecordError(f"{mdir.name}: revision {rev} not found")
    if not force and _is_dirty(mdir):
        raise RecordError(f"{mdir.name}: bom.yaml has unrecorded changes; create a revision or use force")
    shutil.copyfile(snapshot, mdir / "bom" / "bom.yaml")
    _set_active(mdir, rev)


def verify(module: str, rev: str, root: Path = ROOT) -> list[str]:
    """Recompute output hashes of `rev`; return mismatches (empty list = OK)."""
    mdir = module_dir(module, root)
    manifest_path = mdir / "records" / rev / "manifest.yaml"
    if not manifest_path.exists():
        raise RecordError(f"{mdir.name}: revision {rev} not found")
    problems = []
    for entry in _read_yaml(manifest_path).get("outputs", []):
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


def create_concept(summary: str, root: Path = ROOT) -> str:
    """Pin the active revision of every module into a new conceptNNN."""
    modules = {}
    for mdir in _module_dirs(root):
        module_id = MODULE_RE.match(mdir.name).group(1)
        if _is_dirty(mdir):
            raise RecordError(f"{mdir.name}: no active revision or unrecorded bom.yaml changes")
        modules[module_id] = active_revision(module_id, root)

    records = _concept_records(root)
    concept = _next_id(records, CONCEPT_RE, "concept")
    manifest = {
        "concept": concept,
        "parent_concept": active_concept(root),
        "date": _now(),
        "summary": summary,
        "modules": modules,
    }
    _check_schema("concept.schema.json", manifest)

    cdir = records / concept
    cdir.mkdir(exist_ok=False)  # never overwrite an existing record
    _write_yaml(cdir / "manifest.yaml", manifest)
    (records / "ACTIVE_CONCEPT").write_text(concept + "\n", encoding="utf-8", newline="\n")
    return concept


def revert_concept(concept: str, force: bool = False, root: Path = ROOT) -> None:
    """Restore every module's ACTIVE pointer (and bom.yaml) to the concept's revisions.

    All modules are checked before any is changed.
    """
    records = _concept_records(root)
    manifest_path = records / concept / "manifest.yaml"
    if not CONCEPT_RE.match(concept) or not manifest_path.exists():
        raise RecordError(f"concept {concept} not found")
    modules = _read_yaml(manifest_path)["modules"]

    for module_id, rev in modules.items():
        mdir = module_dir(module_id, root)
        if not (mdir / "records" / rev / "bom.yaml").exists():
            raise RecordError(f"{mdir.name}: revision {rev} not found")
        if not force and _is_dirty(mdir):
            raise RecordError(f"{mdir.name}: bom.yaml has unrecorded changes; create a revision or use force")

    for module_id, rev in modules.items():
        revert(module_id, rev, force=True, root=root)
    (records / "ACTIVE_CONCEPT").write_text(concept + "\n", encoding="utf-8", newline="\n")
