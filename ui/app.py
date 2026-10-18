"""Streamlit entry point. Run from the repo root: streamlit run ui/app.py

Read-only skeleton (UI phase 2). Writes will go only through core/ (docs/design/ui_spec.md).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from ui import data, widgets  # noqa: E402

st.set_page_config(page_title="CFM56-7B27 konsept", page_icon=":material/flight:", layout="wide")

nav = st.navigation([
    st.Page(widgets.PAGES["genel_bakis"], title="Genel bakış", icon=":material/home:", default=True),
    st.Page(widgets.PAGES["m0"], title="M0 motor", icon=":material/settings:"),
    st.Page(widgets.PAGES["moduller"], title="Modüller", icon=":material/category:"),
    st.Page(widgets.PAGES["talepler"], title="Talepler", icon=":material/inbox:"),
    st.Page(widgets.PAGES["revizyonlar"], title="Revizyonlar", icon=":material/history:"),
    st.Page(widgets.PAGES["ogrenme"], title="Öğrenme", icon=":material/menu_book:"),
])
widgets.top_bar(data.snapshot())
nav.run()
