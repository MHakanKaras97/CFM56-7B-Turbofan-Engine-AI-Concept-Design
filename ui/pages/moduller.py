"""Module list and the module page template (M1-M9). Read-only; geometry comes in later phases."""

import pandas as pd
import streamlit as st

from ui import data, widgets
from ui.widgets import badge

snap = data.snapshot()
rows = {r["id"]: r for r in snap["modules"]}
icd = snap["m0"]["icd"]
selected = st.query_params.get("m")

if selected not in rows or selected == "M0":
    widgets.page_title("Modüller")
    for row in (r for r in snap["modules"] if r["id"] != "M0"):
        with st.container(border=True):
            a, b = st.columns([5, 1], vertical_alignment="center")
            a.markdown(f"**{row['id']} {row['name_tr']}** · {row['name']} {badge(row['status'], row['color'])}")
            if b.button("Aç", key=f"open_{row['id']}", icon=":material/open_in_new:"):
                widgets.open_module(row["id"])
    st.stop()

row = rows[selected]
revs = [m["revision"] for m in snap["revisions"][selected]]
if st.button("Modüller", icon=":material/arrow_back:", key="back"):
    st.query_params.clear()
    st.rerun()

widgets.page_title(f"{selected} {row['name_tr']}")
st.markdown(f"{row['name']} · {badge(row['status'], row['color'])}")

a, b, c = st.columns([2, 2, 3], vertical_alignment="bottom")
if revs:
    rev_b = b.selectbox("B", revs, index=len(revs) - 1, key="mod_rev_b")
    a.selectbox("Karşılaştır: A", revs, index=max(revs.index(rev_b) - 1, 0), key="mod_rev_a")
else:
    a.selectbox("Karşılaştır: A", ["revizyon yok"], disabled=True, key="mod_rev_a")
    b.selectbox("B", ["revizyon yok"], disabled=True, key="mod_rev_b")
with c:
    k, d3, f = st.columns(3)
    k.button("Kesit", disabled=True, width="stretch", key="btn_section")
    d3.button("3B", disabled=True, width="stretch", key="btn_3d")
    f.button("Fusion'da aç", disabled=True, width="stretch", key="btn_fusion")

tree, section = st.columns([1, 2], gap="large")
with tree:
    widgets.section("BOM ağacı")
    parts = data.read_bom(selected)["parts"]
    if parts:
        for p in sorted(parts, key=lambda p: [int(x) for x in p["id"].split(".")[1:]]):
            depth = p["id"].count(".") - 1
            qty = p["qty"]["value"]
            st.markdown(f"{'&nbsp;' * 4 * depth}`{p['id']}` {p['name']}{f' ×{qty}' if qty != 1 else ''}")
    else:
        st.caption("BOM boş (parça yok).")
with section:
    widgets.section("Kesit görünümü")
    st.info("Kesit görünümü sonraki aşamada (records/revNNN/section.svg, ADR-011).")

widgets.section("ICD bütçesi")
budget = icd["modules"].get(selected, {}).get("budget", {})
tols = icd["tolerances"]
if budget:
    st.dataframe(pd.DataFrame([
        {"Kalem": k, "Değer": data.quantity(v), "Tür": v["kind"], "İzin": data.tolerance(tols[v["kind"]])}
        for k, v in budget.items()
    ]), hide_index=True, width="stretch")
    st.caption(f"kaynak {icd['source']['revision']} (rules/icd.yaml)")
else:
    st.caption("Bu modül için ICD bütçesi yok.")
