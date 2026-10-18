"""Revision records.

Module level: engine/M*/records/revNNN/ holds manifest.yaml, bom.yaml (snapshot),
params.yaml and results.yaml; engine/M*/records/ACTIVE names the active revision.
Concept level: engine/M0_engine/records/conceptNNN/manifest.yaml pins one revision
(or null = not started) per module; engine/M0_engine/records/ACTIVE_CONCEPT names
the active concept.

Records are written once and never rewritten. Only ACTIVE / ACTIVE_CONCEPT change.

Revision types (ADR-012):
  design       numbers, params values or geometry change. Once the module is accepted
               (records/ACCEPTED names the accepted revision) it needs an approved CR.
  maintenance  schema, metadata or text only; no CR. Refused if the diff to the parent
               revision shows a numeric change (core.diff.numeric_changes).
"""

import hashlib
import importlib
import re
import shutil
import subprocess
from pathlib import Path

from core import bom as bom_io
from core.util import now_utc, read_yaml, schema_errors, write_yaml

ROOT = Path(__file__).resolve().parents[1]

REV_RE = re.compile(r"^rev(\d{3})$")
REVISION_TYPES = ("design", "maintenance")
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


def accepted_revision(module: str, root: Path = ROOT) -> str | None:
    """Revision at which the module passed its acceptance (records/ACCEPTED), or None."""
    path = module_dir(module, root) / "records" / "ACCEPTED"
    return path.read_text(encoding="utf-8").strip() if path.exists() else None


def mark_accepted(module: str, rev: str, root: Path = ROOT) -> None:
    """Record the module's acceptance at `rev`. From then on design revisions need an approved CR."""
    mdir = module_dir(module, root)
    if not REV_RE.match(rev) or not (mdir / "records" / rev / "manifest.yaml").exists():
        raise RecordError(f"{mdir.name}: revision {rev} not found")
    _write_pointer(mdir / "records" / "ACCEPTED", rev)


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
    kind: str = "design",
) -> str:
    """Snapshot the module's current state into a new revNNN and make it active.

    kind: "design" or "maintenance" (ADR-012). A design revision of an accepted module needs `cr`;
    a maintenance revision takes no CR and is refused if it changes a number against the parent.
    """
    mdir = module_dir(module, root)
    records = mdir / "records"
    bom_path = mdir / "bom" / "bom.yaml"

    if kind not in REVISION_TYPES:
        raise RecordError(f"revision type {kind!r}; one of {REVISION_TYPES}")
    errors = bom_io.validate(bom_path)
    if errors:
        raise RecordError(f"{bom_path} is invalid: " + "; ".join(errors))
    parent = active_revision(module, root)
    if kind == "design" and cr is None and accepted_revision(module, root):
        raise RecordError(f"{mdir.name}: accepted module; a design revision needs an approved CR (ADR-012)")

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

    bom = bom_io.load(bom_path)
    if kind == "maintenance":
        _check_maintenance(module, parent, cr, {"params": params or {}, "results": results or {},
                                                 "bom": dict(bom, revision=parent), "outputs": output_entries}, root)

    manifest = {
        "revision": rev,
        "parent_revision": parent,
        "revision_type": kind,
        "date": now_utc(),
        "summary": summary,
        "reason": reason,
        "change_request": cr,
        "code_commit": _code_commit(root),
        "outputs": output_entries,
    }
    _check_schema("manifest.schema.json", manifest)

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


def _check_maintenance(module: str, parent: str | None, cr: str | None, new: dict, root: Path) -> None:
    from core.diff import blocking, diff_data, numeric_changes, read_record  # core.diff imports this module

    if parent is None:
        raise RecordError(f"{module}: a maintenance revision needs a parent revision")
    if cr is not None:
        raise RecordError(f"{module}: a maintenance revision takes no CR (ADR-012)")
    changes = numeric_changes(diff_data(read_record(module, parent, root), new))
    blocked = blocking(changes)
    if blocked:
        listed = ", ".join(f"{c['section']} {c['path']}" for c in blocked[:5])
        raise RecordError(f"{module}: not a maintenance revision, {len(blocked)} numeric change(s): {listed}")
    review = module_dir(module, root) / "records" / "REVIEW.md"
    text = review.read_text(encoding="utf-8") if review.exists() else ""
    missing = [f"{c['path']} -> {c['to']}" for c in changes if c["kind"] == "moved"
               and f"{c['path']} -> {c['to']}" not in text]
    if missing:
        raise RecordError(f"{module}: moved value(s) need an old -> new path line in records/REVIEW.md first: "
                          + "; ".join(missing))


def calc_plugin(module: str, root: Path = ROOT):
    """The module's calculation plugin engine/<M>/analysis/calc.py, or None if it has none."""
    name = f"engine.{module_dir(module, root).name}.analysis.calc"
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name in (name, name.rsplit(".", 1)[0]):
            return None
        raise


def _check_clean(module: str, force: bool, root: Path) -> None:
    """Refuse to overwrite unrecorded work: bom.yaml or the analysis params differ from the active record."""
    if force:
        return
    mdir = module_dir(module, root)
    if is_dirty(module, root):
        raise RecordError(f"{mdir.name}: bom.yaml has unrecorded changes; create a revision or use force")
    plugin, active = calc_plugin(module, root), active_revision(module, root)
    if plugin is not None and active is not None:
        recorded = read_revision(module, active, "params.yaml", root)
        current = mdir / "analysis" / plugin.PARAMS_FILE
        if recorded and current.exists() and read_yaml(current) != recorded:
            raise RecordError(f"{mdir.name}: analysis/{plugin.PARAMS_FILE} differs from {active}; "
                              f"record it or use force")


def _restore(module: str, rev: str, root: Path) -> dict:
    """Full-state restore of one module (no checks): bom.yaml, ACTIVE, and through the calc plugin
    params, results and derived files; then re-run the current code on the restored params."""
    from core.diff import diff_data  # core.diff imports this module

    mdir = module_dir(module, root)
    shutil.copyfile(mdir / "records" / rev / "bom.yaml", mdir / "bom" / "bom.yaml")
    _write_pointer(mdir / "records" / "ACTIVE", rev)
    out = {"module": module.split("_")[0], "revision": rev, "warnings": [], "results_diff": None}
    plugin = calc_plugin(module, root)
    params = read_revision(module, rev, "params.yaml", root)
    if plugin is None or not params:
        return out
    results = read_revision(module, rev, "results.yaml", root)
    out["warnings"] += plugin.restore(root, rev, params, results)
    try:
        rerun = plugin.rerun(root, params)
    except Exception as exc:  # any failure of the current code on an old record is reported, not raised
        out["warnings"].append(f"{rev}: güncel kod kayıtlı params ile çalışmadı ({type(exc).__name__}: {exc}); "
                               f"kayıtlı sonuçlar geri yüklendi")
        return out
    diff = diff_data({"results": results}, {"results": rerun})["results"]
    if diff:
        out["results_diff"] = diff
        out["warnings"].append(f"{rev}: kayıtlı sonuç ile güncel kod sonucu farklı ({len(diff)} anahtar); "
                               f"kayıtlı sonuçlar geri yüklendi")
    return out


def reproducible(module: str, rev: str, root: Path = ROOT) -> str | None:
    """None if `rev` can be restored by revert, else the reason (ADR-013). A module without a calc
    plugin restores bom.yaml only and is always reproducible; otherwise the plugin decides."""
    mdir = module_dir(module, root)
    if not REV_RE.match(rev) or not (mdir / "records" / rev / "bom.yaml").exists():
        return f"{mdir.name}: revision {rev} not found"
    plugin = calc_plugin(module, root)
    if plugin is None or not read_revision(module, rev, "params.yaml", root):
        return None
    return plugin.reproducible(root, rev)


def revert(module: str, rev: str, force: bool = False, root: Path = ROOT) -> dict:
    """Make `rev` active with its full state: bom.yaml from its snapshot and, for a module with a calc
    plugin, params and results from the record (the record is the truth) and regenerated derived
    files. The current code is then re-run on the restored params; a difference is a warning and
    does not overwrite the restored results.

    Allowed only to reproducible revisions (reproducible()); older ones stay as history.
    Refuses if bom.yaml or the analysis params have unrecorded changes, unless force=True.
    Returns {module, revision, warnings, results_diff}.
    """
    reason = reproducible(module, rev, root)
    if reason:
        raise RecordError(f"{module}: {rev} is not reproducible, revert refused: {reason}")
    _check_clean(module, force, root)
    return _restore(module, rev, root)


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


def concept_ids(root: Path = ROOT) -> list[str]:
    records = _concept_records(root)
    return sorted(p.name for p in records.iterdir() if p.is_dir() and CONCEPT_RE.match(p.name))


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


def revert_concept(concept: str, force: bool = False, root: Path = ROOT) -> dict[str, dict]:
    """Full-state revert of every pinned module (see revert); null modules are skipped.

    All modules are checked before any is changed. Returns the revert result per module.
    """
    records = _concept_records(root)
    pinned = {m: rev for m, rev in read_concept(concept, root)["modules"].items() if rev is not None}
    for module_id, rev in pinned.items():
        reason = reproducible(module_id, rev, root)
        if reason:
            raise RecordError(f"{module_id}: {rev} is not reproducible, revert refused: {reason}")
        _check_clean(module_id, force, root)

    out = {module_id: _restore(module_id, rev, root) for module_id, rev in pinned.items()}
    _write_pointer(records / "ACTIVE_CONCEPT", concept)
    return out
