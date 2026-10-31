import streamlit as st

from ui_public.i18n import t

st.title(t("requests.title"))
st.info(t("requests.empty"), icon=":material/inbox:")
