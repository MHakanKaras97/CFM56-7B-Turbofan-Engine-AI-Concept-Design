"""Read-only data for the public UI: the active engine state from the repo (ICD, M0 results, module BOMs) shown as
the published baseline rev01. The internal revision history stays in the repo and the development UI (ui/)."""

from pathlib import Path

import streamlit as st

from core import bom as core_bom
from core import records
from core.budgets import read_icd

ROOT = records.ROOT
IMG = Path(__file__).resolve().parent / "assets" / "img"
PUBLISHED_REV = "rev01"
MODULES = ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9")
STATION_ORDER = ("2", "13", "21", "25", "3", "31", "4", "41", "44", "45", "5", "8", "18")


@st.cache_data(show_spinner=False)
def icd() -> dict:
    return read_icd("public UI")


@st.cache_data(show_spinner=False)
def m0_results() -> dict:
    return records.read_revision("M0", records.active_revision("M0"), "results.yaml")


@st.cache_data(show_spinner=False)
def bom(module: str) -> list[dict]:
    parts = core_bom.load(records.module_dir(module) / "bom" / "bom.yaml")["parts"]
    return sorted(parts, key=lambda p: [int(x) for x in p["id"].split(".")[1:]])


def module_mass(module: str) -> float:
    return sum((p.get("mass") or {}).get("value", 0.0) * p["qty"]["value"] for p in bom(module))


def metrics() -> list[dict]:
    r = m0_results()
    perf = r["performance"]
    egt = next(c for c in r["checks"] if c["name"].startswith("EGT displayed"))
    return [
        {"key": "thrust", "value": perf["thrust"]["value"], "unit": "kN", "digits": 1},
        {"key": "sfc", "value": perf["sfc"]["value"], "unit": "g/(kN s)", "digits": 2},
        {"key": "egt_margin", "value": egt["margin"], "unit": "K", "digits": 0},
        {"key": "w2", "value": r["calibration"]["W2"]["value"], "unit": "kg/s", "digits": 0},
        {"key": "bpr", "value": perf["bpr"]["value"], "unit": "", "digits": 2},
        {"key": "opr", "value": perf["opr"]["value"], "unit": "", "digits": 1},
    ]


def image(name: str) -> Path | None:
    path = IMG / f"{name}.png"
    return path if path.is_file() else None
