"""Public UI (published prototype) entry point. Run from the repo root: streamlit run ui_public/app.py

Separate from the development UI (ui/): read-only, bilingual (TR/EN), every module shown as the published baseline
rev01, images from ui_public/assets/img (python -m ui_public.assets.build_assets).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from ui_public.i18n import LANGS, t  # noqa: E402

st.set_page_config(page_title="CFM56-7B27 Concept Design", page_icon=":material/flight:", layout="wide")

with st.sidebar:
    st.radio(t("app.language"), list(LANGS), format_func=LANGS.get, key="lang", horizontal=True)

HERE = Path(__file__).resolve().parent / "pages"
nav = st.navigation([
    st.Page(HERE / "overview.py", title=t("nav.overview"), icon=":material/home:", default=True),
    st.Page(HERE / "engine.py", title=t("nav.engine"), icon=":material/settings:"),
    st.Page(HERE / "modules.py", title=t("nav.modules"), icon=":material/category:"),
    st.Page(HERE / "learning.py", title=t("nav.learning"), icon=":material/menu_book:"),
    st.Page(HERE / "requests.py", title=t("nav.requests"), icon=":material/inbox:"),
    st.Page(HERE / "revisions.py", title=t("nav.revisions"), icon=":material/history:"),
])
st.markdown(f"#### {t('app.title')} &nbsp; :blue-badge[rev01 · {t('app.baseline')}]")
st.caption(t("app.subtitle"))
nav.run()
