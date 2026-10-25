"""M1 calculation plugin for params change requests (core/requests.py apply()) and full-state revert
(core/records.py revert()).

The M1 record holds analysis/fan_params.yaml (params) and analysis/results.yaml (results) of
analysis/fan_design.py. The design reads its budget and inlet state from the ICD at run time, so a
re-run against another active M0 revision can differ from the record; revert reports that as a warning
(core.records._restore) and keeps the recorded results. M1 has no derived files besides results.yaml.
"""

from pathlib import Path

from core.budgets import read_icd
from core.records import module_dir
from core.util import write_yaml
from engine.M1_inlet_fan.analysis import fan_design

PARAMS_FILE = "fan_params.yaml"


def _analysis(root: Path) -> Path:
    return module_dir("M1", root) / "analysis"


def recalculate(root: Path, params_files: dict[str, dict]) -> dict:
    """Fan design with the new params. Returns {"params", "results"} for the revision record.
    An infeasible design raises ValueError (refused); a budget miss is a result, not a refusal."""
    params = params_files[PARAMS_FILE]
    return {"params": params, "results": fan_design.run(params, read_icd("M1 recalculate", root))}


def write_outputs(root: Path, out: dict) -> None:
    write_yaml(_analysis(root) / "results.yaml", out["results"])


def regenerate(root: Path, revision: str) -> None:
    """No derived files besides results.yaml."""


def rerun(root: Path, params: dict) -> dict:
    return fan_design.run(params, read_icd("M1 rerun", root))


def restore(root: Path, revision: str, params: dict, results: dict) -> list[str]:
    write_yaml(_analysis(root) / PARAMS_FILE, params)
    write_yaml(_analysis(root) / "results.yaml", results)
    return []


def reproducible(root: Path, revision: str) -> str | None:
    """Params and results are in the record; restore needs nothing else."""
    return None
