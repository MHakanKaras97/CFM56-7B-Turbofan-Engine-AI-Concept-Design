"""BOM loading and validation.

validate(path) returns error strings; check(path) also returns warnings.
check_data(data) does the same for an already loaded BOM.
dump(data) / write(path, data) are the only way BOM files are written:
fixed key order, block style, no comments (use the part `notes` field).
Run as `python -m core.bom <bom.yaml> ...` to validate files from the shell.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from core.util import schema_errors

HEADER_KEYS = ("module_id", "module_name", "revision", "parts")
PART_KEYS = (
    "id", "name", "parent", "qty", "function", "material", "process", "status",
    "mass", "joints", "loads", "failure_modes", "analyses", "geometry", "notes",
)
QUANTITY_KEYS = ("value", "unit", "tag")
JOINT_KEYS = ("to", "type")
GEOMETRY_KEYS = ("script", "params")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def check_data(data) -> Report:
    report = Report()
    report.errors.extend(f"schema: {msg}" for msg in schema_errors("bom.schema.json", data))

    if not isinstance(data, dict) or not isinstance(data.get("parts"), list):
        return report

    module_id = data.get("module_id")
    parts = [p for p in data["parts"] if isinstance(p, dict)]

    ids: set[str] = set()
    for part in parts:
        pid = part.get("id")
        if not isinstance(pid, str):
            continue
        if pid in ids:
            report.errors.append(f"duplicate id: {pid}")
        ids.add(pid)
        if isinstance(module_id, str) and pid.split(".")[0] != module_id:
            report.errors.append(f"{pid}: id prefix does not match module_id {module_id}")

    parent_ids = {p.get("parent") for p in parts}

    for part in parts:
        pid = part.get("id", "<no id>")
        if "material" in part and part["material"] is None and pid not in parent_ids:
            report.errors.append(f"{pid}: material is null but part has no children")

        parent = part.get("parent")
        if parent is not None:
            if parent == pid:
                report.errors.append(f"{pid}: part is its own parent")
            elif parent not in ids:
                report.errors.append(f"{pid}: parent {parent} not found")

        for joint in part.get("joints") or []:
            target = joint.get("to") if isinstance(joint, dict) else None
            if not isinstance(target, str) or target in ids:
                continue
            if target.split(".")[0] == module_id:
                report.errors.append(f"{pid}: joint target {target} not found")
            else:
                report.warnings.append(f"{pid}: joint target {target} is in another module (not checked)")

    return report


def _ordered(data, keys: tuple[str, ...]):
    """Known keys in fixed order, then any unknown keys sorted (kept so invalid data still round-trips)."""
    if not isinstance(data, dict):
        return data
    out = {k: data[k] for k in keys if k in data}
    out.update({k: data[k] for k in sorted(data, key=str) if k not in out})
    return out


def _sorted_deep(value):
    if isinstance(value, dict):
        return {k: _sorted_deep(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, list):
        return [_sorted_deep(v) for v in value]
    return value


def _canonical_part(part):
    if not isinstance(part, dict):
        return part
    part = _ordered(part, PART_KEYS)
    for key in ("qty", "mass"):
        if key in part:
            part[key] = _ordered(part[key], QUANTITY_KEYS)
    if isinstance(part.get("joints"), list):
        part["joints"] = [_ordered(j, JOINT_KEYS) for j in part["joints"]]
    for key in ("loads", "failure_modes", "analyses"):
        if key in part:
            part[key] = _sorted_deep(part[key])
    if "geometry" in part:
        geometry = _ordered(part["geometry"], GEOMETRY_KEYS)
        if isinstance(geometry, dict) and "params" in geometry:
            geometry["params"] = _sorted_deep(geometry["params"])
        part["geometry"] = geometry
    return part


def canonical(data):
    data = _ordered(data, HEADER_KEYS)
    if isinstance(data, dict) and isinstance(data.get("parts"), list):
        data["parts"] = [_canonical_part(p) for p in data["parts"]]
    return data


def dump(data) -> str:
    return yaml.safe_dump(
        canonical(data), sort_keys=False, default_flow_style=False, allow_unicode=True, width=10_000,
    )


def load(path: str | Path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def write(path: str | Path, data) -> None:
    Path(path).write_text(dump(data), encoding="utf-8", newline="\n")


def check(path: str | Path) -> Report:
    try:
        data = load(path)
    except (OSError, yaml.YAMLError) as exc:
        return Report(errors=[f"cannot load {path}: {exc}"])
    return check_data(data)


def validate(path: str | Path) -> list[str]:
    return check(path).errors


def main(argv: list[str]) -> int:
    failed = False
    for path in argv:
        report = check(path)
        status = "FAIL" if report.errors else "OK"
        print(f"{status} {path}")
        for msg in report.errors:
            print(f"  error: {msg}")
        for msg in report.warnings:
            print(f"  warning: {msg}")
        failed |= bool(report.errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
