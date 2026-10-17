"""Change requests (CR) between modules, coordinated by M0.

Files: engine/M0_engine/requests/CR-###.yaml.
Workflow: open -> approved -> applied, or open -> rejected.
The CR file is a workflow document: it is updated in place, and every status
change is appended to `history`.

Change paths:
  <header_field>                      e.g. module_name
  parts[<id>]                         whole part (old null = add, new null = remove)
  parts[<id>].<field>[.<subfield>]    e.g. parts[M1.1.1].qty
"""

import copy
import re
from pathlib import Path

from core.bom import check_data
from core.records import ROOT, create_revision, is_dirty, module_dir, module_dirs
from core.util import dump_yaml, now_utc, read_yaml, schema_errors, write_yaml

CR_RE = re.compile(r"^CR-(\d{3})$")
PART_PATH_RE = re.compile(r"^parts\[(M\d(?:\.\d+)+)\](?:\.(.+))?$")


class CRError(Exception):
    pass


# --- storage -------------------------------------------------------------------

def _requests_dir(root: Path) -> Path:
    return module_dir("M0", root) / "requests"


def _cr_path(cr_id: str, root: Path) -> Path:
    if not CR_RE.match(cr_id):
        raise CRError(f"invalid CR id {cr_id!r}")
    return _requests_dir(root) / f"{cr_id}.yaml"


def _check(cr: dict, root: Path) -> None:
    errors = schema_errors("cr.schema.json", cr)
    if not errors:
        known = {d.name.split("_")[0] for d in module_dirs(root)}
        for mod in {cr["from_module"], *cr["to_modules"]}:
            if mod not in known:
                errors.append(f"unknown module {mod}")
        for change in cr["changes"]:
            if change["module"] not in cr["to_modules"]:
                errors.append(f"change for {change['module']} but it is not in to_modules")
    if errors:
        raise CRError(f"{cr.get('id', '<new CR>')}: " + "; ".join(errors))


def load_cr(cr_id: str, root: Path = ROOT) -> dict:
    path = _cr_path(cr_id, root)
    if not path.exists():
        raise CRError(f"{cr_id} not found")
    cr = read_yaml(path)
    _check(cr, root)
    return cr


def _save(cr: dict, root: Path) -> None:
    _check(cr, root)
    write_yaml(_cr_path(cr["id"], root), cr)


def _set_status(cr: dict, status: str) -> None:
    cr["history"].append({"date": now_utc(), "from": cr["status"], "to": status})
    cr["status"] = status


def _next_cr_id(root: Path) -> str:
    folder = _requests_dir(root)
    numbers = [int(m.group(1)) for p in folder.glob("CR-*.yaml") if (m := CR_RE.match(p.stem))]
    n = max(numbers, default=0) + 1
    if n > 999:
        raise CRError("no CR ids left")
    return f"CR-{n:03d}"


# --- BOM path access --------------------------------------------------------------

_MISSING = object()


def _locate(bom: dict, path: str):
    """Return (container, key) for a change path; container is a dict or the parts list."""
    m = PART_PATH_RE.match(path)
    if not m:
        return bom, path
    part_id, rest = m.groups()
    parts = bom["parts"]
    if rest is None:
        return parts, part_id
    part = next((p for p in parts if p.get("id") == part_id), None)
    if part is None:
        raise CRError(f"{path}: part {part_id} not found")
    *walk, last = rest.split(".")
    container = part
    for key in walk:
        container = container.get(key)
        if not isinstance(container, dict):
            raise CRError(f"{path}: {key} is not a mapping")
    return container, last


def _get(container, key):
    if isinstance(container, list):
        return next((p for p in container if p.get("id") == key), None)
    return container.get(key)


def _put(container, key, value) -> None:
    if isinstance(container, list):
        container[:] = [p for p in container if p.get("id") != key]
        if value is not None:
            if value.get("id") != key:
                raise CRError(f"parts[{key}]: new part id {value.get('id')!r} does not match path")
            container.append(value)
    elif value is None:
        container.pop(key, None)
    else:
        container[key] = value


# --- workflow ---------------------------------------------------------------------

def create_cr(
    from_module: str,
    to_modules: list[str],
    reason: str,
    changes: list[dict],
    root: Path = ROOT,
) -> str:
    """Create an open CR and return its id. Invalid CRs are rejected and not written."""
    cr_id = _next_cr_id(root)
    date = now_utc()
    cr = {
        "id": cr_id,
        "date": date,
        "from_module": from_module,
        "to_modules": list(to_modules),
        "reason": reason,
        "changes": copy.deepcopy(changes),
        "impact": None,
        "status": "open",
        "decision": None,
        "applied_revisions": None,
        "history": [{"date": date, "from": None, "to": "open"}],
    }
    _check(cr, root)
    with _cr_path(cr_id, root).open("x", encoding="utf-8", newline="\n") as f:  # never overwrite
        f.write(dump_yaml(cr))
    return cr_id


def set_impact(cr_id: str, affected_modules: list[str], notes: str, root: Path = ROOT) -> None:
    """M0 records its impact analysis. Only while the CR is open."""
    cr = load_cr(cr_id, root)
    if cr["status"] != "open":
        raise CRError(f"{cr_id}: impact can only be set while open (status: {cr['status']})")
    cr["impact"] = {"affected_modules": list(affected_modules), "notes": notes}
    _save(cr, root)


def decide(cr_id: str, approve: bool, note: str, root: Path = ROOT) -> None:
    """User decision. Approval requires an impact analysis."""
    cr = load_cr(cr_id, root)
    if cr["status"] != "open":
        raise CRError(f"{cr_id}: already decided (status: {cr['status']})")
    if approve and cr["impact"] is None:
        raise CRError(f"{cr_id}: cannot approve without an impact analysis")
    cr["decision"] = {"date": now_utc(), "note": note}
    _set_status(cr, "approved" if approve else "rejected")
    _save(cr, root)


def apply(cr_id: str, root: Path = ROOT) -> dict[str, str]:
    """Apply an approved CR: edit each target bom.yaml, then record one revision per module.

    Every change is checked (old value matches, resulting BOM valid) before any file is written.
    """
    cr = load_cr(cr_id, root)
    if cr["status"] != "approved":
        raise CRError(f"{cr_id}: only approved CRs can be applied (status: {cr['status']})")

    new_boms: dict[str, dict] = {}
    for change in cr["changes"]:
        module = change["module"]
        if module not in new_boms:
            if is_dirty(module, root):
                raise CRError(f"{cr_id}: {module} has no active revision or unrecorded changes")
            new_boms[module] = read_yaml(module_dir(module, root) / "bom" / "bom.yaml")
        container, key = _locate(new_boms[module], change["path"])
        current = _get(container, key)
        if current != change["old"]:
            raise CRError(f"{cr_id}: {module} {change['path']}: expected {change['old']!r}, found {current!r}")
        _put(container, key, copy.deepcopy(change["new"]))

    for module, bom in new_boms.items():
        errors = check_data(bom).errors
        if errors:
            raise CRError(f"{cr_id}: {module} would become invalid: " + "; ".join(errors))

    revisions = {}
    for module, bom in new_boms.items():
        write_yaml(module_dir(module, root) / "bom" / "bom.yaml", bom)
        revisions[module] = create_revision(module, f"Apply {cr_id}", cr["reason"], cr=cr_id, root=root)

    cr["applied_revisions"] = revisions
    _set_status(cr, "applied")
    _save(cr, root)
    return revisions
