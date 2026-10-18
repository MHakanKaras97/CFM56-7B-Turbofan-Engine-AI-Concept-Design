"""Shared page parts: top bar and small display helpers. Native Streamlit elements only,
so the light and dark themes both work."""

import streamlit as st

from ui import data

PAGES = {
    "genel_bakis": "pages/genel_bakis.py",
    "m0": "pages/m0_motor.py",
    "moduller": "pages/moduller.py",
    "talepler": "pages/talepler.py",
    "revizyonlar": "pages/revizyonlar.py",
    "ogrenme": "pages/ogrenme.py",
}


def badge(text: str, color: str) -> str:
    """Markdown badge; brackets in the text are escaped."""
    return f":{color}-badge[{text.replace('[', '(').replace(']', ')')}]"


def tag_badge(tag: str) -> str:
    return badge(tag, "orange" if tag == "T" else "gray")


def top_bar(snap: dict) -> None:
    left, right = st.columns([3, 2], vertical_alignment="center")
    with left:
        st.markdown(f"#### CFM56-7B27 konsept &nbsp; {badge(snap['concept'] or 'konsept yok', 'gray')}")
    with right:
        a, b = st.columns(2, vertical_alignment="center")
        active = snap["active_module"]
        a.markdown(badge(active["label"], active["color"]) if active else badge("başlamadı", "gray"),
                   help="Aktif modül: aktif revizyonu olan en son modül")
        n = snap["open_crs"]
        b.page_link(PAGES["talepler"], label=f"{n} onay bekliyor" if n else "Onay bekleyen yok",
                    icon=":material/notifications:")
    st.divider()


def open_module(module_id: str) -> None:
    """Go to a module's page: M0 has its own page, M1-M9 use the module page template."""
    if module_id == "M0":
        st.switch_page(PAGES["m0"])
    st.switch_page(PAGES["moduller"], query_params={"m": module_id})


def ref_tag(tag) -> str:
    """'[K]' or '[KS/T]' for a check reference tag (str or mapping per reference)."""
    tags = list(dict.fromkeys(tag.values())) if isinstance(tag, dict) else [tag]
    return "[" + "/".join(t for t in tags if t) + "]" if any(tags) else ""


def quantity_card(col, label: str, q: dict, help: str | None = None) -> None:
    col.metric(label, data.quantity(q), help=help, border=True)
