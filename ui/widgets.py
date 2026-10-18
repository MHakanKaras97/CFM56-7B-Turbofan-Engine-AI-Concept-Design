"""Shared page parts: top bar and small display helpers. Native Streamlit elements only,
so the light and dark themes both work."""

import streamlit as st

from core.records import RecordError
from core.requests import CRError
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


def top_bar(snap: dict, page: str = "") -> None:
    left, right = st.columns([3, 2], vertical_alignment="center")
    with left:
        where = f" &nbsp;·&nbsp; {page}" if page else ""
        st.markdown(f"#### CFM56-7B27 konsept &nbsp; {badge(snap['concept'] or 'konsept yok', 'gray')}{where}")
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


def page_title(text: str, container=st) -> None:
    """Page heading; small, because the top bar already names the page."""
    container.subheader(text, anchor=False)


def section(text: str, container=st) -> None:
    """Section heading below the page title."""
    container.markdown(f"##### {text}")


LONG_UNIT = 5  # longer units go to the label so the value is not truncated in a card


def metric(col, label: str, q: dict, digits: int | None = None, help: str | None = None) -> None:
    """Metric card: the tag is a small badge next to the label, the value stays clean."""
    tag, unit = q.get("tag"), data.unit_tr(q.get("unit"))
    if len(unit) > LONG_UNIT:
        label, q = f"{label} ({unit})", {**q, "unit": None}
    col.metric(f"{label} {tag_badge(tag)}" if tag else label, data.quantity(q, digits, tag=False),
               help=help, border=True)


# status colours of the engine strip (legend on the overview page); mid-tones read on light and dark
STRIP_COLORS = {"green": "#15803d", "gray": "#6b7280", "orange": "#c2410c", "blue": "#1d4ed8"}


def strip_style(rows: list[dict]) -> None:
    """Colour the engine strip buttons (keys strip_<Mx>) as equal, full-width segments."""
    rules = [".st-key-engine_strip [data-testid='stHorizontalBlock'] { gap: 2px; flex-wrap: nowrap; }",
             ".st-key-engine_strip [data-testid='stColumn'] { min-width: 0 !important; flex: 1 1 0 !important; }",
             ".st-key-engine_strip button { min-width: 0; width: 100%; padding-left: 0; padding-right: 0; }"]
    for r in rows:
        c = STRIP_COLORS[r["color"]]
        rules.append(f".st-key-strip_{r['id']} button {{ background: {c}; border: 1px solid {c}; color: #fff; "
                     f"border-radius: 4px; min-height: 2.6rem; font-weight: 600; }}")
        rules.append(f".st-key-strip_{r['id']} button:hover {{ filter: brightness(1.15); color: #fff; "
                     f"border-color: {c}; }}")
    st.html("<style>" + " ".join(rules) + "</style>")


# --- confirmed actions -----------------------------------------------------------------------
# A button stores the action in session state; the dialog stays open on reruns until "Vazgeç",
# dismissal or the confirmed call. Only the runner given by the page writes, and it calls core/.

PENDING_ACTION = "ui_pending_action"


def request(kind: str, title: str, lines: list[str], ok: str, warning: str | None = None, **args) -> None:
    st.session_state[PENDING_ACTION] = {"kind": kind, "title": title, "lines": lines, "ok": ok,
                                        "warning": warning, **args}


def _clear() -> None:
    st.session_state.pop(PENDING_ACTION, None)


@st.dialog("Onay", on_dismiss=_clear)
def _confirm(p: dict, run) -> None:
    st.markdown(f"**{p['title']}**")
    for line in p["lines"]:
        st.markdown(line)
    if p.get("warning"):
        st.caption(p["warning"])
    ok, back = st.columns(2)
    if ok.button(p["ok"], key="confirm_ok", type="primary", width="stretch"):
        try:
            message = run(p)
        except (CRError, RecordError) as exc:
            st.session_state["ui_error"] = str(exc)
        else:
            st.session_state["ui_done"] = message
        _clear()
        st.rerun()
    if back.button("Vazgeç", key="confirm_cancel", width="stretch"):
        _clear()
        st.rerun()


def confirm_pending(runners: dict) -> None:
    """Open the dialog for the pending action, if it belongs to this page (call at the end of the page)."""
    p = st.session_state.get(PENDING_ACTION)
    if p and p["kind"] in runners:
        _confirm(p, runners[p["kind"]])


def flash() -> None:
    """Result of the last confirmed action."""
    if "ui_done" in st.session_state:
        st.success(st.session_state.pop("ui_done"))
    for warning in st.session_state.pop("ui_warn", []):
        st.warning(warning)
    if "ui_error" in st.session_state:
        st.error(st.session_state.pop("ui_error"))
