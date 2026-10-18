"""Change requests (CR) between modules, coordinated by M0.

Files: engine/M0_engine/requests/CR-###.yaml.
Workflow: open -> approved -> applied, or open -> rejected.
The CR file is a workflow document: it is updated in place, and every status
change is appended to `history`.

Change types:
  bom (default)   path into engine/<M>/bom/bom.yaml
    <header_field>                      e.g. module_name
    parts[<id>]                         whole part (old null = add, new null = remove)
    parts[<id>].<field>[.<subfield>]    e.g. parts[M1.1.1].qty
  params          `file` in engine/<M>/analysis/ (*_params.yaml), dotted `path`, e.g. components.eta_hpc.
                  A Quantity old/new compares and sets value, unit and tag of the entry.
                  Applying re-runs the module calculation (engine/<M>/analysis/calc.py), records a
                  revision and regenerates the module's derived files.

Options: a CR may offer resolution options (e.g. budget CRs: (a) accept the value in M0 params,
(b) module redesign). decide() records the user's pick; only an option that applies changes
can be approved.
"""

import copy
import importlib
import re
from pathlib import Path

from core import bom as bom_io
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
    options: list[dict] | None = None,
    impact: dict | None = None,
) -> str:
    """Create an open CR and return its id. Invalid CRs are rejected and not written.

    `impact` may be given when M0 itself drafts the CR from its own analysis (budget CRs).
    """
    cr_id = _next_cr_id(root)
    date = now_utc()
    cr = {
        "id": cr_id,
        "date": date,
        "from_module": from_module,
        "to_modules": list(to_modules),
        "reason": reason,
        "changes": copy.deepcopy(changes),
        "impact": copy.deepcopy(impact),
        "status": "open",
        "decision": None,
        "applied_revisions": None,
        "history": [{"date": date, "from": None, "to": "open"}],
    }
    if options:
        cr["options"] = copy.deepcopy(options)
    _check(cr, root)
    with _cr_path(cr_id, root).open("x", encoding="utf-8", newline="\n") as f:  # never overwrite
        f.write(dump_yaml(cr))
    return cr_id


def set_impact(cr_id: str, affected_modules: list[str], notes: str, root: Path = ROOT,
               metrics: dict[str, dict] | None = None) -> None:
    """M0 records its impact analysis. Only while the CR is open.

    metrics: metric name -> Quantity. None keeps the metrics already recorded (if any).
    """
    cr = load_cr(cr_id, root)
    if cr["status"] != "open":
        raise CRError(f"{cr_id}: impact can only be set while open (status: {cr['status']})")
    if metrics is None:
        metrics = (cr["impact"] or {}).get("metrics")
    cr["impact"] = {"affected_modules": list(affected_modules), "notes": notes}
    if metrics is not None:
        cr["impact"]["metrics"] = copy.deepcopy(metrics)
    _save(cr, root)


def decide(cr_id: str, approve: bool, note: str, root: Path = ROOT, option: str | None = None) -> None:
    """User decision. Approval requires an impact analysis.

    For a CR with options, `option` names the pick; it must apply changes when approving and
    must not when rejecting.
    """
    cr = load_cr(cr_id, root)
    if cr["status"] != "open":
        raise CRError(f"{cr_id}: already decided (status: {cr['status']})")
    if approve and cr["impact"] is None:
        raise CRError(f"{cr_id}: cannot approve without an impact analysis")
    if approve and not cr["changes"]:
        raise CRError(f"{cr_id}: nothing to approve, the CR has no changes")
    options = {o["id"]: o for o in cr.get("options", [])}
    if options:
        if option not in options:
            raise CRError(f"{cr_id}: pick one of the options {sorted(options)}")
        if options[option]["applies_changes"] != approve:
            raise CRError(f"{cr_id}: option {option!r} does not match approve={approve}")
    elif option is not None:
        raise CRError(f"{cr_id}: has no options")
    cr["decision"] = {"date": now_utc(), "note": note, **({"option": option} if option else {})}
    _set_status(cr, "approved" if approve else "rejected")
    _save(cr, root)


# --- params access ------------------------------------------------------------------

QUANTITY_KEYS = ("value", "unit", "tag")


def _is_quantity(x) -> bool:
    return isinstance(x, dict) and "value" in x


def _params_locate(data: dict, path: str):
    *walk, last = path.split(".")
    container = data
    for key in walk:
        container = container.get(key) if isinstance(container, dict) else None
        if not isinstance(container, dict):
            raise CRError(f"{path}: {key} is not a mapping")
    return container, last


def _params_get(container: dict, key: str):
    node = container.get(key)
    if _is_quantity(node):
        return {k: node[k] for k in QUANTITY_KEYS if k in node}
    return node


def _params_put(container: dict, key: str, new, cr_id: str) -> None:
    node = container.get(key)
    if new is None:
        container.pop(key, None)
    elif _is_quantity(new) and _is_quantity(node):
        node = dict(node)
        if node.get("tag") != new["tag"]:
            node.pop("source", None)  # the source no longer backs the value
        node.update(new)
        node["note"] = f"set by {cr_id}"
        container[key] = node
    else:
        container[key] = copy.deepcopy(new)


def _calc(module: str, root: Path):
    """The module's calculation plugin: engine/<M>/analysis/calc.py."""
    name = f"engine.{module_dir(module, root).name}.analysis.calc"
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError:
        raise CRError(f"{module}: params change needs {name.replace('.', '/')}.py") from None


def apply(cr_id: str, root: Path = ROOT) -> dict[str, str]:
    """Apply an approved CR and record one revision per changed module.

    BOM changes edit bom.yaml. Params changes edit engine/<M>/analysis/*_params.yaml, re-run the
    module calculation and regenerate its derived files (calc.py). Every change is checked (old
    value matches, BOM valid, calculation accepted) before any file is written.
    """
    cr = load_cr(cr_id, root)
    if cr["status"] != "approved":
        raise CRError(f"{cr_id}: only approved CRs can be applied (status: {cr['status']})")

    modules: list[str] = []
    new_boms: dict[str, dict] = {}
    new_params: dict[str, dict[str, dict]] = {}
    for change in cr["changes"]:
        module = change["module"]
        if module not in modules:
            if is_dirty(module, root):
                raise CRError(f"{cr_id}: {module} has no active revision or unrecorded changes")
            modules.append(module)
        if change.get("type", "bom") == "params":
            files = new_params.setdefault(module, {})
            if change["file"] not in files:
                path = module_dir(module, root) / "analysis" / change["file"]
                if not path.is_file():
                    raise CRError(f"{cr_id}: {module} {change['file']} not found")
                files[change["file"]] = read_yaml(path)
            container, key = _params_locate(files[change["file"]], change["path"])
            current = _params_get(container, key)
            if current != change["old"]:
                raise CRError(f"{cr_id}: {module} {change['file']} {change['path']}: "
                              f"expected {change['old']!r}, found {current!r}")
            _params_put(container, key, change["new"], cr_id)
            continue
        if module not in new_boms:
            new_boms[module] = bom_io.load(module_dir(module, root) / "bom" / "bom.yaml")
        container, key = _locate(new_boms[module], change["path"])
        current = _get(container, key)
        if current != change["old"]:
            raise CRError(f"{cr_id}: {module} {change['path']}: expected {change['old']!r}, found {current!r}")
        _put(container, key, copy.deepcopy(change["new"]))

    for module, bom in new_boms.items():
        errors = bom_io.check_data(bom).errors
        if errors:
            raise CRError(f"{cr_id}: {module} would become invalid: " + "; ".join(errors))

    calcs, computed = {}, {}
    for module, files in new_params.items():
        calcs[module] = _calc(module, root)
        try:
            computed[module] = calcs[module].recalculate(root, files)
        except (ArithmeticError, ValueError) as exc:
            raise CRError(f"{cr_id}: {module} calculation not accepted: {exc}") from None

    revisions = {}
    for module in modules:
        mdir = module_dir(module, root)
        if module in new_boms:
            bom_io.write(mdir / "bom" / "bom.yaml", new_boms[module])
        out = computed.get(module)
        if out is not None:
            for name, data in new_params[module].items():
                write_yaml(mdir / "analysis" / name, data)
            calcs[module].write_outputs(root, out)
        revisions[module] = create_revision(
            module, f"Apply {cr_id}", cr["reason"], cr=cr_id,
            params=out["params"] if out else None, results=out["results"] if out else None, root=root)
        if out is not None:
            calcs[module].regenerate(root, revisions[module])

    cr["applied_revisions"] = revisions
    _set_status(cr, "applied")
    _save(cr, root)
    return revisions
