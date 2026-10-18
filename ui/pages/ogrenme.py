"""Learning notes (Turkish), sources and the tag legend. Read-only."""

import pandas as pd
import streamlit as st

from ui import data
from ui.widgets import tag_badge

st.title("Öğrenme")
notes, sources, legend = st.tabs(["Notlar", "Kaynaklar", "Etiketler"])

with notes:
    groups = {g: files for g, files in data.learning_files().items() if files}
    nav, body = st.columns([1, 3], gap="large")
    with nav:
        group = st.radio("Grup", list(groups), key="learn_group")
        path = st.radio("Dosya", groups[group], format_func=lambda p: p.name, key=f"learn_file_{group}")
    with body:
        text = data.read_text(path)
        if path.suffix == ".md":
            st.markdown(text)
        else:
            st.code(text, language=None, wrap_lines=True)
        base = data.ROOT if path.is_relative_to(data.ROOT) else data.root()
        st.caption(path.relative_to(base).as_posix())
    st.caption("learning/sources/ (indirilen kaynaklar, git dışı) listelenmez.")

with sources:
    st.dataframe(pd.DataFrame(data.sources()), hide_index=True, width="stretch")
    st.caption("kaynak docs/sources.md")

with legend:
    for tag, text in data.TAG_LEGEND:
        st.markdown(f"{tag_badge(tag)} **[{tag}]** {text}")
    st.caption("Her sayının yanında etiketi gösterilir; [T] değerleri turuncu rozetle vurgulanır.")
