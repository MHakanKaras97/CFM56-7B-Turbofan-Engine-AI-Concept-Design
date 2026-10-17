"""BOM loading and validation.

validate(path) returns error strings; check(path) also returns warnings.
Run as `python -m core.bom <bom.yaml> ...` to validate files from the shell.
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).parent / "schemas" / "bom.schema.json"


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _schema_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _location(error) -> str:
    return "/".join(str(p) for p in error.absolute_path) or "<root>"


def check(path: str | Path) -> Report:
    report = Report()
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        report.errors.append(f"cannot load {path}: {exc}")
        return report

    for err in sorted(_schema_validator().iter_errors(data), key=lambda e: list(e.absolute_path)):
        report.errors.append(f"schema: {_location(err)}: {err.message}")

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
