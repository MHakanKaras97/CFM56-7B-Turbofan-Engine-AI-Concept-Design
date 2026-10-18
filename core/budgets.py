"""Module budget checks against the M0 interface control document (engine/M0_engine/rules/icd.yaml).

A module reports achieved values for items of its budget. Each item has a `kind`; the ICD
tolerance of that kind decides pass/fail. Items of kind `info` are reported, not checked.
"""

from pathlib import Path

from core.records import ROOT, module_dir
from core.util import read_yaml


class BudgetError(Exception):
    pass


def load_icd(root: Path = ROOT) -> dict:
    return read_yaml(module_dir("M0", root) / "rules" / "icd.yaml")


def check_budget(module: str, achieved: dict[str, float], root: Path = ROOT) -> list[dict]:
    """Compare achieved values with the module budget. Returns one row per achieved item."""
    icd = load_icd(root)
    module_id = module.split("_")[0]
    if module_id not in icd["modules"]:
        raise BudgetError(f"{module}: no budget in the ICD")
    budget = icd["modules"][module_id]["budget"]
    unknown = sorted(set(achieved) - set(budget))
    if unknown:
        raise BudgetError(f"{module_id}: not in budget: {', '.join(unknown)}")
    rows = []
    for item, value in achieved.items():
        b = budget[item]
        row = {"item": item, "budget": b["value"], "achieved": value, "unit": b["unit"], "kind": b["kind"]}
        if b["kind"] == "info":
            rows.append(dict(row, result="info"))
            continue
        tol = icd["tolerances"][b["kind"]]
        deviation = value / b["value"] - 1.0 if tol["type"] == "relative" else value - b["value"]
        rows.append(dict(row, deviation=deviation, tolerance=tol["value"], tolerance_type=tol["type"],
                         result="pass" if abs(deviation) <= tol["value"] else "fail"))
    return rows
