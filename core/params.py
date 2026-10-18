"""Params file validation (engine/<M>/analysis/*_params.yaml).

A quantity entry (any mapping with a 'value' key) may only have value, unit, tag, note and source;
unknown keys are errors. Unquoted text with a comma inside a YAML flow mapping is the usual cause.
"""

from pathlib import Path

from core.records import ROOT, module_dirs
from core.util import read_yaml, schema_errors


def params_errors(data: dict) -> list[str]:
    return schema_errors("params.schema.json", data)


def params_files(root: Path = ROOT) -> list[Path]:
    return sorted(f for mdir in module_dirs(root) for f in (mdir / "analysis").glob("*_params.yaml"))


def check_all(root: Path = ROOT) -> dict[str, list[str]]:
    """Errors per params file (relative path); files without errors are left out."""
    out = {}
    for f in params_files(root):
        errors = params_errors(read_yaml(f))
        if errors:
            out[f.relative_to(root).as_posix()] = errors
    return out
