import streamlit as st

from ui_public.i18n import t

st.title(t("revisions.title"))
st.info(t("revisions.empty"), icon=":material/history:")
