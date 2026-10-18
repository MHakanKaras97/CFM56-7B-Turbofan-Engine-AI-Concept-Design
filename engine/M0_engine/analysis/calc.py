"""M0 calculation plugin for params change requests (core/requests.py apply()) and full-state
revert (core/records.py revert()).

recalculate() evaluates new params without writing anything and refuses a result that is
infeasible or fails a HARD check; write_outputs() and regenerate() write the derived files
(analysis/results.yaml, rules/icd.yaml). Derived files are never edited by hand.

Revert: restore() writes the record's params and results back to analysis/ and regenerates
icd.yaml (re-solve, else the recorded operating point); rerun() runs the current code on the
record's params for the verification; affected_modules() lists modules whose ICD budget changes;
reproducible() tells whether a record can be restored at all (its ICD can be regenerated).
"""

from pathlib import Path

from core.budgets import read_icd
from core.records import module_dir
from core.util import write_yaml
from engine.M0_engine.analysis.cycle import load_inputs, solve_rated
from engine.M0_engine.analysis.icd import MODULES, icd_file, icd_for_revision, write_icd

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


def rerun(root: Path, params: dict) -> dict:
    """Results of the current code for `params`, without the checks of recalculate()."""
    p, t, initial, raw, refs = load_inputs(root=root, raw=params)
    results, *_ = solve_rated(p, t, initial, raw, refs, float(raw["calibration"]["tolerance"]["value"]))
    return results


def restore(root: Path, revision: str, params: dict, results: dict) -> list[str]:
    """Write the record's params and results to analysis/ and regenerate icd.yaml. Returns warnings.

    Only for reproducible records (core.records.revert checks first); nothing is written otherwise."""
    icd, warnings = icd_for_revision(revision, root)
    if icd is None:
        raise ArithmeticError(f"{revision} is not reproducible: " + "; ".join(warnings))
    mdir = module_dir("M0", root)
    write_yaml(mdir / "analysis" / PARAMS_FILE, params)
    write_yaml(mdir / "analysis" / "results.yaml", results)
    write_yaml(icd_file(root), icd)
    if icd["source"].get("method"):  # re-solve failed, the recorded operating point was used
        return [f"icd.yaml {revision} kaydının çalışma noktasından üretildi; güncel kod yeniden çözemedi "
                f"({warnings[0]})"]
    return []


def affected_modules(root: Path, revision: str) -> tuple[list[str], str]:
    """Modules whose ICD budget differs between the current icd.yaml and `revision`, plus a note."""
    current = read_icd("M0 revert impact", root)["modules"]
    target, _ = icd_for_revision(revision, root)
    if target is None:
        return list(MODULES), f"{revision} için ICD üretilemedi; bütün modüller etkilenmiş sayıldı"
    changed = [m for m in MODULES if current.get(m, {}).get("budget") != target["modules"][m]["budget"]]
    return changed, f"ICD bütçesi değişen modüller: {', '.join(changed) or 'yok'}"


def reproducible(root: Path, revision: str) -> str | None:
    """None if the record can be restored (its ICD re-solves or evaluates at the recorded operating
    point), else the reason."""
    icd, warnings = icd_for_revision(revision, root)
    return None if icd is not None else "; ".join(warnings)
