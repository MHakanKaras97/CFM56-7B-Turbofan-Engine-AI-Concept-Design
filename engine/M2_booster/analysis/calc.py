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


def _clear_geometry_caches() -> None:
    """Drop the cached record inputs and the M1 frame layout that read geometry/flowpath.yaml (R-G2.26)."""
    from engine.M1_inlet_fan.geometry import fan_frame, m2_boundary
    from engine.M2_booster.geometry import layout
    layout._record_cached.cache_clear()
    m2_boundary.m2_boundary.cache_clear()
    fan_frame.build.cache_clear()


def regenerate(root: Path, revision: str) -> None:
    """geometry/flowpath.yaml from the current params file, in two passes (R-G2.22, R-G2.26): the radii first (the
    station 25 fields of a stale file are kept, they are not read by the M1 frame layout), then the station 25 x
    from the M1 frame code, which reads the M2 station 24 x and radii through layout.record. The file being rewritten
    is not checked against the record (layout.regenerating); the radii it holds come from the params of this pass."""
    from engine.M2_booster.geometry import layout
    path = module_dir("M2", root) / "geometry" / flowpath.OUT_FILE.name
    res = bm.run()
    old = read_yaml(path) if path.exists() else {}
    x_old = (old.get("interfaces") or {}).get("M3_station_25", {}).get("x_m")
    first = flowpath.build(res, st25={"x25": x_old if x_old is not None else float("nan"), "m1_revision": "-"})
    try:
        with layout.regenerating():
            write_yaml(path, first)
            _clear_geometry_caches()
            write_yaml(path, flowpath.build(res))
    finally:
        _clear_geometry_caches()


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
