"""Change requests. The only write is core.requests.decide, after a confirmation dialog."""

import pandas as pd
import streamlit as st

from core.requests import CRError, decide
from ui import data
from ui.widgets import badge

DECIDED_BY = "user (UI)"
PENDING = "talep_pending"  # {"cr", "approve", "option", "note"} while the dialog is open
STATUS_COLOR = {"open": "orange", "approved": "blue", "rejected": "gray", "applied": "green"}

snap = data.snapshot()
crs = snap["crs"]


def cancel() -> None:
    st.session_state.pop(PENDING, None)


@st.dialog("Kararı onayla", on_dismiss=cancel)
def confirm(p: dict) -> None:
    verdict = "ONAY" if p["approve"] else "RET"
    st.markdown(f"**{p['cr']}** için karar: **{verdict}**" + (f" · seçenek ({p['option']})" if p["option"] else ""))
    st.markdown(f"Not: {p['note']}")
    st.caption(f"Kaydeden: {DECIDED_BY}. Karar CR dosyasına yazılır; geri alınamaz.")
    ok, back = st.columns(2)
    if ok.button("Kaydet", key="confirm_ok", type="primary", width="stretch"):
        try:
            decide(p["cr"], p["approve"], p["note"], root=data.root(), option=p["option"], decided_by=DECIDED_BY)
        except CRError as exc:
            st.session_state["talep_error"] = str(exc)
        else:
            st.session_state["talep_done"] = f"{p['cr']}: karar kaydedildi ({verdict.lower()})."
        cancel()
        st.rerun()
    if back.button("Vazgeç", key="confirm_cancel", width="stretch"):
        cancel()
        st.rerun()


def impact_block(cr: dict) -> bool:
    """Show the impact; return True if it allows approval."""
    impact = cr["impact"]
    if impact is None:
        st.markdown(badge("etki analizi yok", "gray") + " · onay için M0 etki analizi gerekir")
        return False
    ready = bool(impact["affected_modules"])
    st.markdown(badge("etki analizi hazır" if ready else "etkilenen modül yok", "green" if ready else "orange")
                + f" · {impact.get('by', 'üretici kayıtlı değil')} · etkilenen: "
                + (", ".join(impact["affected_modules"]) or "-"))
    if impact.get("notes"):
        st.caption(impact["notes"])
    metrics = impact.get("metrics") or {}
    if metrics:
        for col, (name, q) in zip(st.columns(len(metrics)), metrics.items()):
            col.metric(name.replace("d", "Δ", 1) if name.startswith("d") else name,
                       data.quantity(q, 2), help=f"impact.metrics.{name} · {impact.get('by', '')}", border=True)
    return ready


def changes_table(cr: dict) -> None:
    if not cr["changes"]:
        return
    rows = [{"Modül": c["module"], "Tür": c.get("type", "bom"), "Yol": c["path"],
             "Eski": data.quantity(c["old"]) if isinstance(c["old"], dict) else str(c["old"]),
             "Yeni": data.quantity(c["new"]) if isinstance(c["new"], dict) else str(c["new"])}
            for c in cr["changes"]]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def history(cr: dict) -> None:
    rows = [{"Tarih": h["date"], "Önce": data.STATUS_TR.get(h["from"], "-"), "Sonra": data.STATUS_TR[h["to"]]}
            for h in cr["history"]]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def decision_form(cr: dict, approvable: bool) -> None:
    key = cr["id"]
    options = cr.get("options")
    if options:
        labels = {o["id"]: f"({o['id']}) {o['description']}" for o in options}
        option = st.radio("Seçenek", list(labels), format_func=labels.get, key=f"opt_{key}")
        approve = next(o for o in options if o["id"] == option)["applies_changes"]
    else:
        option = None
        approve = st.radio("Karar", [True, False], format_func=lambda a: "Onayla" if a else "Reddet",
                           key=f"dec_{key}", horizontal=True)
    note = st.text_area("Karar notu (zorunlu)", key=f"note_{key}")
    blocked = approve and not approvable
    if blocked:
        st.caption("Onay devre dışı: etki analizi yok veya etkilenen modül listesi boş.")
    if st.button("Kararı kaydet", key=f"save_{key}", type="primary", disabled=blocked or not note.strip()):
        st.session_state[PENDING] = {"cr": key, "approve": approve, "option": option, "note": note.strip()}


st.title("Talepler")
n_open = sum(cr["status"] == "open" for cr in crs)
st.markdown(f"{badge(f'{n_open} açık', 'orange' if n_open else 'gray')} {badge(f'{len(crs) - n_open} kapalı', 'gray')}")

for k, kind in (("talep_done", st.success), ("talep_error", st.error)):
    if k in st.session_state:
        kind(st.session_state.pop(k))

if not crs:
    st.info("Kayıtlı değişiklik talebi yok.")

for cr in crs:
    is_open = cr["status"] == "open"
    with st.container(border=True):
        kind = "bütçe ihlali" if cr.get("options") else "değişiklik talebi"
        st.markdown(f"**{cr['id']}** · {cr['from_module']} → {', '.join(cr['to_modules'])} · {kind} "
                    f"{badge(data.STATUS_TR[cr['status']], STATUS_COLOR[cr['status']])}")
        st.markdown(cr["reason"])
        approvable = impact_block(cr)
        changes_table(cr)
        if is_open:
            decision_form(cr, approvable)
        else:
            d = cr["decision"] or {}
            option = f" · seçenek ({d['option']})" if d.get("option") else ""
            st.markdown(f"Karar: {d.get('date', '-')}{option} · {d.get('decided_by', 'kaydeden belirtilmemiş')}")
            st.caption(d.get("note", ""))
            if cr.get("applied_revisions"):
                st.caption("Uygulanan revizyonlar: " + ", ".join(f"{m} {r}" for m, r in cr["applied_revisions"].items()))
        with st.expander("Geçmiş"):
            history(cr)

if PENDING in st.session_state:
    confirm(st.session_state[PENDING])
