import pandas as pd
import streamlit as st

from ui_public import data, widgets
from ui_public.i18n import num, t

st.title(t("engine.title"))
st.markdown(t("engine.intro"))

icd = data.icd()
results = data.m0_results()

widgets.metrics_grid(data.metrics())

left, right = st.columns([3, 2], gap="large")
with left:
    st.subheader(t("engine.stations"))
    rows = []
    for sid in data.STATION_ORDER:
        s = icd["stations"][sid]
        rows.append({t("cols.station"): sid, t("cols.meaning"): t(f"stations.{sid}"),
                     "Tt [K]": num(s["Tt"]["value"], 1), "Pt [kPa]": num(s["Pt"]["value"], 1),
                     "W [kg/s]": num(s["W"]["value"], 2), "FAR": num(s["FAR"]["value"], 4)})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={
        "Tt [K]": st.column_config.TextColumn(help=t("station_cols.Tt")),
        "Pt [kPa]": st.column_config.TextColumn(help=t("station_cols.Pt")),
        "W [kg/s]": st.column_config.TextColumn(help=t("station_cols.W")),
        "FAR": st.column_config.TextColumn(help=t("station_cols.FAR"))})
    st.caption(t("engine.stations_hint"))

with right:
    st.subheader(t("engine.checks"))
    for c in results["checks"]:
        color, label = {"pass": ("green", t("engine.pass")), "fail": ("red", t("engine.fail"))}.get(
            c["result"], ("blue", t("engine.info")))
        unit = c.get("unit") or ""
        unit = "" if unit.startswith("-") else unit.replace("degC", "°C")
        a, b = st.columns([3, 2], vertical_alignment="center")
        a.markdown(t(f"check_labels.{c['name']}", c["name"]), help=t(f"checks.{c['name']}", ""))
        b.markdown(f"{num(c['value'], 2)} {unit} :{color}-badge[{label}]")

st.subheader(t("engine.budgets"))
st.caption(t("engine.budgets_hint"))

cols = st.columns(3)
for i, (mid, mod) in enumerate(icd["modules"].items()):
    with cols[i % 3].container(border=True):
        st.markdown(f"**{mid} · {widgets.module_name(mid)}**")
        df = pd.DataFrame([{t("cols.item"): k, t("cols.value"): num(v["value"], 4).rstrip("0").rstrip(",.") or "0",
                            t("cols.unit"): "" if v["unit"] == "-" else v["unit"],
                            t("cols.meaning"): t(f"budget.{k}", "")} for k, v in mod["budget"].items()])
        st.dataframe(df, hide_index=True, width="stretch")
