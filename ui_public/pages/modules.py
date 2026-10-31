import pandas as pd
import streamlit as st

from ui_public import data, widgets
from ui_public.i18n import num, t

selected = st.query_params.get("m") or st.session_state.get("module")

if selected not in data.MODULES:
    st.title(t("modules.title"))
    for mid in data.MODULES:
        with st.container(border=True):
            a, b, c = st.columns([1, 4, 1], vertical_alignment="center")
            img = data.image(f"{mid.lower()}_iso")
            if img:
                a.image(str(img), width="stretch")
            b.markdown(f"**{mid} · {widgets.module_name(mid)}** &nbsp; :green-badge[{data.PUBLISHED_REV}]")
            b.caption(f"{len(data.bom(mid))} {t('common.parts')} · {num(data.module_mass(mid), 0)} kg")
            if c.button(t("common.open"), key=f"open_{mid}", icon=":material/open_in_new:"):
                widgets.open_module(mid)
    st.stop()

if st.button(t("common.back"), icon=":material/arrow_back:", key="back"):
    st.query_params.clear()
    st.session_state.pop("module", None)
    st.rerun()

st.title(f"{selected} · {widgets.module_name(selected)}")
st.markdown(f":green-badge[{data.PUBLISHED_REV}] &nbsp; {t('modules.total_mass')}: "
            f"**{num(data.module_mass(selected), 1)} kg** ({t('common.mass_info')})")

widgets.views(selected.lower())

st.subheader(t("modules.bom"))
parts = data.bom(selected)
st.dataframe(pd.DataFrame([{
    "ID": p["id"], t("cols.part"): p["name"], t("cols.qty"): p["qty"]["value"],
    t("cols.material"): t(f"materials.{p['material']}", p["material"] or ""),
    t("cols.mass"): num((p.get("mass") or {}).get("value", 0.0), 3),
    t("cols.function"): p["function"]} for p in parts]), hide_index=True, width="stretch")

st.subheader(t("modules.budget"))
budget = data.icd()["modules"].get(selected, {}).get("budget", {})
if budget:
    st.dataframe(pd.DataFrame([{t("cols.item"): k, t("cols.value"): num(v["value"], 4),
                                t("cols.unit"): "" if v["unit"] == "-" else v["unit"],
                                t("cols.meaning"): t(f"budget.{k}", "")} for k, v in budget.items()]),
                 hide_index=True, width="stretch")
else:
    st.caption(t("modules.no_budget"))

if st.button(t("modules.learn_more"), icon=":material/menu_book:", key="learn"):
    st.session_state["topic"] = selected.lower()
    st.switch_page("pages/learning.py")
