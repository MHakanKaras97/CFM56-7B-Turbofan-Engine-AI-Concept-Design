import streamlit as st

from ui import data
from ui.widgets import badge

snap = data.snapshot()
m0 = snap["m0"]

st.title("Genel bakış")

st.subheader("Motor şeridi (gaz yolu sırası)")
for col, row in zip(st.columns(len(snap["modules"])), snap["modules"]):
    col.markdown(badge(row["id"], row["color"]), help=f"{row['name_tr']} · {row['status']}")
st.caption("Yeşil: aktif revizyon · gri: başlamadı · turuncu: açık talep veya konseptten farklı revizyon")

if m0["metrics"]:
    for col, m in zip(st.columns(len(m0["metrics"])), m0["metrics"]):
        col.metric(m["label"], data.quantity(m["q"], m["digits"]), help=m["help"], border=True)
else:
    st.info("M0'ın aktif revizyonu yok; metrikler gösterilemiyor.")

st.subheader("Modüller")
cols = st.columns(3)
for i, row in enumerate(r for r in snap["modules"] if r["id"] != "M0"):
    with cols[i % 3].container(border=True):
        st.markdown(f"**{row['id']} {row['name_tr']}**")
        st.caption(row["status"])

st.subheader("Son revizyonlar")
if m0["chain"]:
    st.markdown(" → ".join(badge(f"{r} aktif", "blue") if r == m0["rev"] else badge(r, "gray")
                           for r in m0["chain"]))
    st.caption("M0 revizyon zinciri (parent_revision)")

with st.expander("Kavramsal düzen referansı (ölçeksiz)"):
    st.image(str(data.REFERENCE_SVG), width="stretch")
    st.caption("docs/design/engine_reference.svg · kaynak docs/design/concept_reference.yaml")
