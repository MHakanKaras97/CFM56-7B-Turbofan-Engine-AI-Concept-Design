"""Shared page elements of the public UI."""

import streamlit as st

from ui_public import data
from ui_public.i18n import num, t

MODULES_PAGE = "pages/modules.py"


def open_module(module: str) -> None:
    st.session_state["module"] = module  # switch_page drops query parameters
    st.switch_page(MODULES_PAGE)


def views(name: str) -> None:
    """3D, cutaway and half-section images of the engine ('engine') or a module ('m3')."""
    tabs = st.tabs([t("common.view_3d"), t("common.view_cutaway"), t("common.view_section")])
    for tab, view in zip(tabs, ("iso", "cutaway", "section")):
        path = data.image(f"{name}_{view}")
        with tab:
            if path:
                st.image(str(path), width="stretch")
            else:
                st.info(t("common.no_image"))


def metric(col, m: dict) -> None:
    unit = f" {m['unit']}" if m["unit"] else ""
    col.metric(t(f"metrics.label_{m['key']}"), num(m["value"], m["digits"]) + unit, help=t(f"metrics.{m['key']}"))


def metrics_grid(items: list[dict], per_row: int = 3) -> None:
    for i in range(0, len(items), per_row):
        for col, m in zip(st.columns(per_row, border=True), items[i:i + per_row]):
            metric(col, m)


def module_name(module: str) -> str:
    return t(f"module_names.{module}")
