import streamlit as st

from ui_public import data, widgets
from ui_public.i18n import learning_text, t

st.title(t("learning.title"))

TOPICS = ["00_turbofan"] + [m.lower() for m in data.MODULES]


def label(topic: str) -> str:
    if topic == "00_turbofan":
        return learning_text(topic).splitlines()[0].lstrip("# ")
    return f"{topic.upper()} · {widgets.module_name(topic.upper())}"


start = st.session_state.pop("topic", None) or st.query_params.get("topic", "00_turbofan")
topic = st.selectbox(t("learning.topic"), TOPICS, index=TOPICS.index(start) if start in TOPICS else 0,
                     format_func=label)
if topic != "00_turbofan":
    img = data.image(f"{topic}_cutaway")
    if img:
        left, _ = st.columns([3, 2])
        left.image(str(img), width="stretch")
st.markdown(learning_text(topic))
