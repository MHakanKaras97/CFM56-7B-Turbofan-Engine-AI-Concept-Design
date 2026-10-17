"""Take-off SFC = ICAO T/O fuel flow / TCDS take-off thrust, per ICAO row.

Usage:
    python -m tools.derive_sfc [out.yaml]

Inputs:  engine/M0_engine/rules/icao_edb_cfm56_7b27.yaml, engine/M0_engine/rules/tcds_e004.yaml
Output:  engine/M0_engine/analysis/sfc_takeoff.yaml (default)
Sanity range (Kuropatwa 2022): T/O TSFC 0.32-0.39 lb/(lbf*h).
"""

import sys
from pathlib import Path

from core.util import read_yaml, write_yaml

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "engine" / "M0_engine" / "rules"
DEFAULT_OUT = ROOT / "engine" / "M0_engine" / "analysis" / "sfc_takeoff.yaml"

LB_KG = 0.45359237
LBF_N = 4.4482216152605
# 1 lb/(lbf*h) expressed in g/(kN*s)
LB_PER_LBF_H_IN_G_PER_KN_S = (LB_KG * 1000) / (LBF_N / 1000 * 3600)

SANITY_LB_PER_LBF_H = (0.32, 0.39)


def sfc_g_per_kn_s(fuel_kg_s: float, thrust_kn: float) -> float:
    return fuel_kg_s * 1000 / thrust_kn


def g_per_kn_s_to_lb_per_lbf_h(sfc: float) -> float:
    return sfc / LB_PER_LBF_H_IN_G_PER_KN_S


def derive(icao: dict, tcds: dict) -> dict:
    thrust = tcds["ratings"]["CFM56-7B27"]["takeoff_thrust"]["value"]
    lo, hi = SANITY_LB_PER_LBF_H
    rows = []
    for row in icao["rows"]:
        if row["superseded"]:
            continue
        sfc = sfc_g_per_kn_s(row["fuel_flow_to_kg_s"], thrust)
        sfc_imp = g_per_kn_s_to_lb_per_lbf_h(sfc)
        rows.append({
            "uid": row["uid"],
            "engine": row["engine"],
            "fuel_flow_to": {"value": row["fuel_flow_to_kg_s"], "unit": "kg/s", "tag": "K"},
            "thrust_to": {"value": thrust, "unit": "kN", "tag": "K"},
            "sfc": {"value": round(sfc, 3), "unit": "g/(kN*s)", "tag": "H"},
            "sfc_imperial": {"value": round(sfc_imp, 4), "unit": "lb/(lbf*h)", "tag": "H"},
            "in_sanity_range": lo <= sfc_imp <= hi,
        })
    return {
        "method": "SFC = ICAO T/O fuel flow / TCDS take-off thrust (sea-level static, ICAO test conditions)",
        "inputs": ["icao_edb_cfm56_7b27.yaml", "tcds_e004.yaml"],
        "sanity_range": {"min": lo, "max": hi, "unit": "lb/(lbf*h)", "source": "Kuropatwa 2022"},
        "rows": rows,
    }


def main(argv: list[str]) -> int:
    out = Path(argv[0]) if argv else DEFAULT_OUT
    data = derive(read_yaml(RULES / "icao_edb_cfm56_7b27.yaml"), read_yaml(RULES / "tcds_e004.yaml"))
    write_yaml(out, data)
    for r in data["rows"]:
        print(f"{r['uid']:<11} {r['engine']:<16} {r['sfc']['value']:>7} g/kNs  "
              f"{r['sfc_imperial']['value']:>7} lb/lbf/h  sane={r['in_sanity_range']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
