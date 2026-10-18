"""M0 calculation plugin for params change requests (core/requests.py apply()).

recalculate() evaluates new params without writing anything and refuses a result that is
infeasible or fails a HARD check; write_outputs() and regenerate() write the derived files
(analysis/results.yaml, rules/icd.yaml). Derived files are never edited by hand.
"""

from pathlib import Path

from core.records import module_dir
from core.util import write_yaml
from engine.M0_engine.analysis.cycle import load_inputs, solve_rated
from engine.M0_engine.analysis.icd import write_icd

PARAMS_FILE = "cycle_params.yaml"


def recalculate(root: Path, params_files: dict[str, dict]) -> dict:
    """Rated case with the new params. Returns {"params", "results"} for the revision record."""
    raw = params_files[PARAMS_FILE]
    p, t, initial, raw, refs = load_inputs(root=root, raw=raw)
    tol = float(raw["calibration"]["tolerance"]["value"])
    results, r, *_ = solve_rated(p, t, initial, raw, refs, tol)
    if r is None:
        raise ArithmeticError("rated case infeasible with the new params")
    if not results["hard_checks_passed"]:
        raise ValueError("a HARD check fails with the new params")
    return {"params": raw, "results": results}


def write_outputs(root: Path, out: dict) -> None:
    write_yaml(module_dir("M0", root) / "analysis" / "results.yaml", out["results"])


def regenerate(root: Path, revision: str) -> None:
    write_icd(revision, root)
