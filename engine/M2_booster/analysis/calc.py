"""M2 calculation plugin for params change requests (core/requests.py apply()) and full-state revert
(core/records.py revert()).

The M2 record holds analysis/booster_params.yaml (params) and analysis/meanline_results.yaml (results) of
analysis/booster_meanline.py. The meanline reads its budget and station 21 state from the ICD at run time,
so a re-run against another active M0 revision can differ from the record; revert reports that as a warning
(core.records._restore) and keeps the recorded results. Derived file besides the results:
geometry/flowpath.yaml (M3 station 25 interface), regenerated from the restored params.
"""

from pathlib import Path

from core.budgets import read_icd
from core.records import module_dir
from core.util import read_yaml, write_yaml
from engine.M2_booster.analysis import a1_validation, booster_meanline as bm
from engine.M2_booster.geometry import flowpath

PARAMS_FILE = bm.PARAMS_FILE.name
RESULTS_FILE = bm.OUT_FILE.name


def _analysis(root: Path) -> Path:
    return module_dir("M2", root) / "analysis"


def _results(root: Path, params: dict, consumer: str) -> dict:
    ref = read_yaml(bm.REF_FILE)
    a1 = a1_validation.run(ref)
    res = bm.run(icd=read_icd(consumer, root), params=params)
    return bm.to_yaml(res, a1, bm.rule_checks(res, ref, a1))


def recalculate(root: Path, params_files: dict[str, dict]) -> dict:
    """Meanline with the new params. Returns {"params", "results"} for the revision record.
    An infeasible design raises (refused); a budget miss is a result, not a refusal."""
    params = params_files[PARAMS_FILE]
    return {"params": params, "results": _results(root, params, "M2 recalculate")}


def write_outputs(root: Path, out: dict) -> None:
    write_yaml(_analysis(root) / RESULTS_FILE, out["results"])


def regenerate(root: Path, revision: str) -> None:
    """geometry/flowpath.yaml from the current params file."""
    write_yaml(module_dir("M2", root) / "geometry" / flowpath.OUT_FILE.name, flowpath.build())


def rerun(root: Path, params: dict) -> dict:
    return _results(root, params, "M2 rerun")


def restore(root: Path, revision: str, params: dict, results: dict) -> list[str]:
    write_yaml(_analysis(root) / PARAMS_FILE, params)
    write_yaml(_analysis(root) / RESULTS_FILE, results)
    regenerate(root, revision)
    return []


def reproducible(root: Path, revision: str) -> str | None:
    """Params and results are in the record; restore needs nothing else."""
    return None
