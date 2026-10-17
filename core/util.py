"""Shared file, time and schema helpers."""

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

SCHEMAS = Path(__file__).parent / "schemas"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_yaml(path: Path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def dump_yaml(data) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def write_yaml(path: Path, data) -> None:
    Path(path).write_text(dump_yaml(data), encoding="utf-8", newline="\n")


def schema_errors(name: str, data) -> list[str]:
    schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.absolute_path))
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors]
