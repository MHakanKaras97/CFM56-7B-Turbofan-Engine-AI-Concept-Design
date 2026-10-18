"""Change requests. Writes: core.requests.decide and core.requests.apply, each after a confirmation dialog."""

import pandas as pd
import streamlit as st

from core.requests import apply, decide
from ui import data, widgets
from ui.widgets import badge

DECIDED_BY = "user (UI)"
STATUS_COLOR = {"open": "orange", "approved": "blue", "rejected": "gray", "applied": "green"}

snap = data.snapshot()
crs = snap["crs"]


def run_decide(p: dict) -> str:
    decide(p["cr"], p["approve"], p["note"], root=data.root(), option=p["option"], decided_by=DECIDED_BY)
    return f"{p['cr']}: karar kaydedildi ({'onay' if p['approve'] else 'ret'})."


def run_apply(p: dict) -> str:
    revisions = apply(p["cr"], root=data.root())
    return f"{p['cr']} uygulandı: " + ", ".join(f"{m} {r}" for m, r in revisions.items())


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
            widgets.metric(col, name.replace("d", "Δ", 1) if name.startswith("d") else name, q, 2,
                           help=f"impact.metrics.{name} · {impact.get('by', '')}")
    return ready


def changes_table(cr: dict) -> None:
    if not cr["changes"]:
        return
    def cell(x):
        return data.quantity(x) if isinstance(x, dict) else str(x)

    rows = [{"Modül": c["module"], "Tür": "revert", "Yol": "ACTIVE (tam durum)", "Eski": str(c["from"]),
             "Yeni": c["to"]} if c.get("type") == "revert" else
            {"Modül": c["module"], "Tür": c.get("type", "bom"), "Yol": c["path"], "Eski": cell(c["old"]),
             "Yeni": cell(c["new"])}
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
        verdict = "ONAY" if approve else "RET"
        widgets.request("decide", f"{key} için karar: {verdict}" + (f" · seçenek ({option})" if option else ""),
                        [f"Not: {note.strip()}"], "Kaydet",
                        f"Kaydeden: {DECIDED_BY}. Karar CR dosyasına yazılır; geri alınamaz.",
                        cr=key, approve=approve, option=option, note=note.strip())


widgets.page_title("Talepler")
n_open = sum(cr["status"] == "open" for cr in crs)
st.markdown(f"{badge(f'{n_open} açık', 'orange' if n_open else 'gray')} {badge(f'{len(crs) - n_open} kapalı', 'gray')}")

widgets.flash()

if not crs:
    st.info("Kayıtlı değişiklik talebi yok.")

for cr in crs:
    is_open = cr["status"] == "open"
    with st.container(border=True):
        if cr["changes"] and cr["changes"][0].get("type") == "revert":
            kind = f"geri dönüş ({cr['concept']})" if cr.get("concept") else "geri dönüş"
        else:
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
            if cr["status"] == "approved" and st.button("Uygula", key=f"apply_{cr['id']}", type="primary",
                                                        icon=":material/play_arrow:"):
                widgets.request("apply", f"{cr['id']} uygulansın mı?",
                                [f"{len(cr['changes'])} değişiklik: "
                                 + ", ".join(f"{c['module']} {c['path']}" for c in cr["changes"])],
                                "Uygula", "core.requests.apply: değişiklikler yazılır, modül hesabı yeniden çalışır, "
                                          "her modül için yeni bir tasarım revizyonu oluşur.", cr=cr["id"])
            if cr.get("applied_revisions"):
                st.caption("Uygulanan revizyonlar: " + ", ".join(f"{m} {r}" for m, r in cr["applied_revisions"].items()))
            for warning in cr.get("apply_warnings", []):
                st.warning(warning)
        with st.expander("Geçmiş"):
            history(cr)

widgets.confirm_pending({"decide": run_decide, "apply": run_apply})
