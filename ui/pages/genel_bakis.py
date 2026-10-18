import streamlit as st

from ui import data, widgets
from ui.widgets import badge

snap = data.snapshot()
m0 = snap["m0"]

widgets.page_title("Genel bakış")

widgets.section("Motor şeridi (gaz yolu sırası)")
widgets.strip_style(snap["modules"])
with st.container(key="engine_strip"):
    for col, row in zip(st.columns(len(snap["modules"]), gap=None, wrap=False), snap["modules"]):
        if col.button(row["id"], key=f"strip_{row['id']}", help=f"{row['name_tr']} · {row['status']}",
                      width="stretch"):
            widgets.open_module(row["id"])
st.markdown(f"{badge('aktif revizyon', 'green')} {badge('başlamadı', 'gray')} "
            f"{badge('açık talep / konseptten farklı', 'orange')} · kutuya tıklayınca modül sayfası açılır")

if m0["metrics"]:
    for col, m in zip(st.columns(len(m0["metrics"])), m0["metrics"]):
        widgets.metric(col, m["label"], m["q"], m["digits"], m["help"])
else:
    st.info("M0'ın aktif revizyonu yok; metrikler gösterilemiyor.")

widgets.section("Modüller")
cols = st.columns(3)
for i, row in enumerate(r for r in snap["modules"] if r["id"] != "M0"):
    with cols[i % 3].container(border=True):
        st.markdown(f"**{row['id']} {row['name_tr']}**")
        st.caption(row["status"])
        if st.button("Aç", key=f"card_{row['id']}", icon=":material/open_in_new:"):
            widgets.open_module(row["id"])

widgets.section("Son revizyonlar")
if m0["chain"]:
    st.markdown(" → ".join(badge(f"{r} aktif", "blue") if r == m0["rev"] else badge(r, "gray")
                           for r in m0["chain"]))
    st.caption("M0 revizyon zinciri (parent_revision)")

with st.expander("Kavramsal düzen referansı (ölçeksiz)"):
    svg = data.read_text(data.REFERENCE_SVG).replace("<svg ", '<svg style="max-width:100%;height:auto" ', 1)
    st.markdown(f'<div style="overflow-x:auto">{svg}</div>', unsafe_allow_html=True)
    st.caption("docs/design/engine_reference.svg · kaynak docs/design/concept_reference.yaml")
