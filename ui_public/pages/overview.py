import streamlit as st

from ui_public import data, widgets
from ui_public.i18n import num, t

st.title(t("nav.overview"))

widgets.metrics_grid(data.metrics())

st.subheader(t("overview.engine_views"))
widgets.views("engine")
st.caption(t("overview.engine_caption"))

st.subheader(t("overview.strip"))
for col, mid in zip(st.columns(len(data.MODULES), gap="small"), data.MODULES):
    if col.button(mid, key=f"strip_{mid}", help=widgets.module_name(mid), width="stretch"):
        widgets.open_module(mid)
st.caption(t("overview.strip_hint"))

st.subheader(t("overview.modules"))
cols = st.columns(3)
for i, mid in enumerate(data.MODULES):
    with cols[i % 3].container(border=True):
        img = data.image(f"{mid.lower()}_iso")
        if img:
            st.image(str(img), width="stretch")
        st.markdown(f"**{mid} · {widgets.module_name(mid)}** &nbsp; :green-badge[{data.PUBLISHED_REV}]")
        st.caption(f"{len(data.bom(mid))} {t('common.parts')} · {num(data.module_mass(mid), 0)} kg")
        if st.button(t("common.open"), key=f"card_{mid}", icon=":material/open_in_new:"):
            widgets.open_module(mid)
