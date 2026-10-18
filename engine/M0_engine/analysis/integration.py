"""M0 integration check: re-run the cycle with a module's achieved values.

The cycle is evaluated at the ICD operating point (W2, T4 and delta_eta of the source revision)
with the achieved values applied to the cycle inputs; thrust, SFC and EGT are compared with the
ICD reference [T tolerances]. Out of tolerance, a change request from the module to M0 is
drafted through core/requests.py; it stays open (never applied here).
"""

from dataclasses import replace
from pathlib import Path

from core.budgets import check_budget, load_icd
from core.records import ROOT, module_dir
from core.requests import create_cr
from engine.M0_engine.analysis.cycle import Params, egt_model_K, load_inputs, run, with_delta_eta

PARAM_FIELDS = set(Params.__dataclass_fields__) - {"T0", "P0", "opr", "bpr", "gas", "include_fuel_mass"}


def apply_achieved(p: Params, achieved: dict[str, float]) -> tuple[Params, list[str]]:
    """Apply achieved values that are cycle inputs. Returns (Params, items not used)."""
    changes, unused = {}, []
    for item, value in achieved.items():
        if item in PARAM_FIELDS:
            changes[item] = value
        elif item == "hpc_pr":
            changes["opr"] = value * p.core_pr_25_2
        else:
            unused.append(item)  # cycle outputs (temperatures, flows, powers): budget check only
    return replace(p, **changes), unused


def integration_check(module: str, achieved: dict[str, float], draft_cr: bool = True,
                      cr_root: Path = ROOT) -> dict:
    """Budget check plus cycle re-run. Returns rows, metrics, pass/fail and the drafted CR id (or None)."""
    module_id = module.split("_")[0]
    icd = load_icd(ROOT)
    budget_rows = check_budget(module_id, achieved, ROOT)
    integ = icd["integration"]
    op = integ["operating_point"]

    p, _, _, raw, _ = load_inputs(module_dir("M0", ROOT) / "records" / icd["source"]["revision"] / "params.yaml")
    p = with_delta_eta(p, op["delta_eta"])
    p, unused = apply_achieved(p, achieved)
    r = run(p, op["W2"], op["T4"])

    ref, tol = integ["reference"], integ["tolerances"]
    thrust, sfc, egt = r["thrust"] / 1000.0, r["W_fuel"] / r["thrust"] * 1e6, egt_model_K(r, raw)
    metrics = [
        {"name": "thrust", "value": thrust, "reference": ref["thrust_kN"], "unit": "kN",
         "deviation": thrust / ref["thrust_kN"] - 1.0, "tolerance": tol["thrust"]["value"]},
        {"name": "sfc", "value": sfc, "reference": ref["sfc_g_kNs"], "unit": "g/(kN s)",
         "deviation": sfc / ref["sfc_g_kNs"] - 1.0, "tolerance": tol["sfc"]["value"]},
        {"name": "egt", "value": egt, "reference": ref["egt_model_K"], "unit": "K",
         "deviation": egt - ref["egt_model_K"], "tolerance": tol["egt"]["value"]},
    ]
    for m in metrics:
        m["result"] = "pass" if abs(m["deviation"]) <= m["tolerance"] else "fail"
    passed = all(m["result"] == "pass" for m in metrics)

    cr_id = None
    if not passed and draft_cr:
        budget = icd["modules"][module_id]["budget"]
        failed = ", ".join(f"{m['name']} {m['deviation']:+.4g}" for m in metrics if m["result"] == "fail")
        changes = [
            {"module": "M0", "path": f"icd_{module_id}_{item}",
             "old": {"value": budget[item]["value"], "unit": budget[item]["unit"], "tag": budget[item]["tag"]},
             "new": {"value": value, "unit": budget[item]["unit"], "tag": "T"}}
            for item, value in achieved.items()
        ]
        cr_id = create_cr(module_id, ["M0"],
                          f"Integration check out of tolerance ({failed}); M0 re-balance needed", changes,
                          root=cr_root)
    return {"module": module_id, "budget": budget_rows, "not_used_in_cycle": unused,
            "metrics": metrics, "passed": passed, "cr": cr_id}
