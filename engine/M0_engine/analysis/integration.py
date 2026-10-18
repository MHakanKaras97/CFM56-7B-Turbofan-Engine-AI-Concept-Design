"""M0 integration check: re-run the cycle with a module's achieved values.

Modes [T]:
- thrust_held (default, FADEC-like): W2 and thrust fixed at the ICD reference; T4 and fuel flow
  are solved. Checked: SFC and EGT; T41 is reported.
- operating_point: W2 and T4 fixed at the ICD operating point. Checked: thrust, SFC and EGT.

Out of tolerance, a change request from the module to M0 is drafted through core/requests.py
with two options for the user: (a) accept the achieved values in the M0 params and re-balance
(params changes), (b) module redesign (no change). The CR carries its impact (dSFC %, dEGT K,
dT41 K; dThrust % in operating_point mode). The CR stays open; nothing is applied here.
"""

from dataclasses import replace
from pathlib import Path

from core.budgets import check_budget, read_icd
from core.records import ROOT, module_dir
from core.requests import create_cr
from core.util import read_yaml
from engine.M0_engine.analysis.cycle import ETA, Params, egt_model_K, load_inputs, run, with_delta_eta

PARAM_FIELDS = set(Params.__dataclass_fields__) - {"T0", "P0", "opr", "bpr", "gas", "include_fuel_mass"}
PARAMS_FILE = "cycle_params.yaml"
MODES = ("thrust_held", "operating_point")


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


def design_point(root: Path = ROOT):
    """Params of the ICD source revision with its delta_eta applied, plus raw params and the ICD."""
    icd = read_icd("M0 integration_check", root)
    op = icd["integration"]["operating_point"]
    rev_params = module_dir("M0", ROOT) / "records" / icd["source"]["revision"] / "params.yaml"
    p, _, _, raw, _ = load_inputs(rev_params)
    return with_delta_eta(p, op["delta_eta"], tuple(op["delta_eta_group"])), raw, icd


def solve_thrust_held(p: Params, W2: float, thrust: float, T4: float, tol: float = 1e-10) -> dict:
    """Newton on T4 so that thrust [N] matches at fixed W2."""
    for _ in range(50):
        r = run(p, W2, T4)
        res = r["thrust"] / thrust - 1.0
        if abs(res) < tol:
            return r
        slope = (run(p, W2, T4 + 0.1)["thrust"] / thrust - 1.0 - res) / 0.1
        T4 -= res / slope
    raise ArithmeticError(f"no T4 holds thrust {thrust / 1000.0:.2f} kN at W2 = {W2:.1f} kg/s")


def evaluate(p: Params, raw: dict, icd: dict, mode: str) -> dict:
    op, ref = icd["integration"]["operating_point"], icd["integration"]["reference"]
    if mode == "thrust_held":
        return solve_thrust_held(p, op["W2"], ref["thrust_kN"] * 1000.0, op["T4"])
    if mode == "operating_point":
        return run(p, op["W2"], op["T4"])
    raise ValueError(f"unknown mode {mode!r}; one of {MODES}")


def _metrics(r: dict, base: dict, raw: dict, icd: dict, mode: str) -> list[dict]:
    tol = icd["integration"]["tolerances"]
    sfc, sfc0 = r["W_fuel"] / r["thrust"], base["W_fuel"] / base["thrust"]
    rows = []
    if mode == "operating_point":
        rows.append({"name": "thrust", "value": r["thrust"] / 1000.0, "unit": "kN",
                     "deviation": r["thrust"] / base["thrust"] - 1.0, "tolerance": tol["thrust"]["value"]})
    rows += [
        {"name": "sfc", "value": sfc * 1e6, "unit": "g/(kN s)", "deviation": sfc / sfc0 - 1.0,
         "tolerance": tol["sfc"]["value"]},
        {"name": "egt", "value": egt_model_K(r, raw), "unit": "K",
         "deviation": egt_model_K(r, raw) - egt_model_K(base, raw), "tolerance": tol["egt"]["value"]},
    ]
    for m in rows:
        m["result"] = "pass" if abs(m["deviation"]) <= m["tolerance"] else "fail"
    rows.append({"name": "T41", "value": r["T41"], "unit": "K", "deviation": r["T41"] - base["T41"],
                 "result": "info"})
    return rows


IMPACT_METRICS = {"thrust": ("dThrust", "%", 100.0), "sfc": ("dSFC", "%", 100.0),
                  "egt": ("dEGT", "K", 1.0), "T41": ("dT41", "K", 1.0)}


def impact(module: str, metrics: list[dict], mode: str) -> dict:
    """CR impact from the integration metrics: deltas against the ICD design point, tag H."""
    out = {}
    for m in metrics:
        name, unit, scale = IMPACT_METRICS[m["name"]]
        out[name] = {"value": round(m["deviation"] * scale, 6), "unit": unit, "tag": "H"}
    return {"affected_modules": sorted({"M0", module}),
            "notes": f"M0 integration check ({mode}); deltas against the ICD design point",
            "by": "M0 integration_check", "metrics": out}


def params_changes(module: str, achieved: dict[str, float], root: Path = ROOT) -> list[dict]:
    """Option (a): achieved values written into the M0 params. Efficiencies set this way are fixed,
    i.e. excluded from the delta_eta shift. Items that are not M0 inputs get no change."""
    raw = read_yaml(module_dir("M0", root) / "analysis" / PARAMS_FILE)
    changes, fixed = [], []
    for item, value in achieved.items():
        section = next((s for s in ("components", "secondary_air") if item in raw[s]), None)
        if section is None:
            continue
        node = raw[section][item]
        changes.append({"type": "params", "module": "M0", "file": PARAMS_FILE, "path": f"{section}.{item}",
                        "old": {k: node[k] for k in ("value", "unit", "tag")},
                        "new": {"value": value, "unit": node["unit"], "tag": "H"}})
        if item in ETA:
            fixed.append(item)
    if fixed:
        old = raw["rated_case"].get("delta_eta_exclude")
        new = sorted(set(old or []) | set(fixed))
        changes.append({"type": "params", "module": "M0", "file": PARAMS_FILE,
                        "path": "rated_case.delta_eta_exclude", "old": old, "new": new})
    return changes


def integration_check(module: str, achieved: dict[str, float], mode: str = "thrust_held",
                      draft_cr: bool = True, cr_root: Path = ROOT) -> dict:
    """Budget check plus cycle re-run. Returns rows, metrics, pass/fail and the drafted CR id (or None).

    cr_root holds the CR and the params read for option (a); design data always come from ROOT.
    """
    module_id = module.split("_")[0]
    p0, raw, icd = design_point()
    budget_rows = check_budget(module_id, achieved, ROOT)
    p, unused = apply_achieved(p0, achieved)
    base = evaluate(p0, raw, icd, mode)
    r = evaluate(p, raw, icd, mode)
    metrics = _metrics(r, base, raw, icd, mode)
    passed = all(m["result"] != "fail" for m in metrics)

    cr_id = None
    if not passed and draft_cr:
        failed = ", ".join(f"{m['name']} {m['deviation']:+.4g}" for m in metrics if m["result"] == "fail")
        changes = params_changes(module_id, achieved, cr_root)
        options = [
            {"id": "a", "applies_changes": True,
             "description": "M0 params change: accept the achieved values and re-balance the cycle"
                            if changes else "not available: the achieved items are not M0 inputs"},
            {"id": "b", "applies_changes": False,
             "description": f"{module_id} redesign to meet its budget; M0 unchanged"},
        ]
        cr_id = create_cr(module_id, ["M0"], f"Integration check ({mode}) out of tolerance: {failed}",
                          changes, root=cr_root, options=options, impact=impact(module_id, metrics, mode))
    return {"module": module_id, "mode": mode, "budget": budget_rows, "not_used_in_cycle": unused,
            "metrics": metrics, "passed": passed, "cr": cr_id}


def efficiency_debits(step: float = 0.01) -> list[dict]:
    """EGT and SFC change per efficiency loss of `step` (thrust held), next to Martins 2015 (CFM56-3)."""
    p0, raw, icd = design_point()
    refs = read_yaml(module_dir("M0", ROOT) / "rules" / "martins_2015.yaml")["egt_rise_per_point_efficiency_loss"]
    base = evaluate(p0, raw, icd, "thrust_held")
    rows = []
    for component, ref in refs.items():
        if not isinstance(ref, dict):
            continue
        item = ref["model_item"]
        r = evaluate(replace(p0, **{item: getattr(p0, item) - step}), raw, icd, "thrust_held")
        rows.append({"component": component, "item": item,
                     "dEGT_K": egt_model_K(r, raw) - egt_model_K(base, raw), "martins_dEGT_K": ref["value"],
                     "dSFC": (r["W_fuel"] / r["thrust"]) / (base["W_fuel"] / base["thrust"]) - 1.0,
                     "dT41_K": r["T41"] - base["T41"]})
    return rows
