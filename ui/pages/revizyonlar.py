"""Revision and concept timelines, the A -> B difference (core/diff.py), revert and verify (core/records.py).

Writes: a revert CR (core.requests: create_revert_cr -> decide -> apply) after a confirmation dialog;
the dialog decision is recorded as the CR's approval. Verify only reads.
"""

import pandas as pd
import streamlit as st

from core.diff import is_empty
from core.records import RecordError, verify
from core.requests import apply, create_revert_cr, decide, load_cr, revert_impact
from ui import data, widgets
from ui.widgets import badge

snap = data.snapshot()
active = {r["id"]: r["active"] for r in snap["modules"]}
started = [m for m in data.MODULES if snap["revisions"][m]]


def table(rows: list[dict]) -> None:
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    else:
        st.caption("Bu bölümde fark yok.")


def value(x) -> str:
    if isinstance(x, (list, dict)):
        return str(x)
    return data.num(x)


DECIDED_BY = "user (UI)"
FULL_STATE = ("Tam durum geri dönüşü: bom.yaml, params ve results kayıttan geri yüklenir, icd.yaml yeniden "
              "üretilir; ardından güncel kod kayıtlı params ile yeniden çalıştırılır (fark uyarı olarak gösterilir). "
              "Bir revert CR'si oluşturulur; onayınız bu CR'nin onayı olarak kaydedilir ve CR uygulanır.")


def impact_lines(targets: dict[str, str]) -> list[str]:
    impact = revert_impact(targets, data.root())
    return [f"Etkilenen modüller ({impact['by']}): {', '.join(impact['affected_modules'])}", impact["notes"]]


def run_revert(p: dict) -> str:
    """Revert CR: create (impact by M0), record the dialog decision as approval, apply."""
    root = data.root()
    cr_id = create_revert_cr(p["targets"], p["reason"], root=root, concept=p.get("concept"))
    decide(cr_id, True, p["reason"], root=root, decided_by=DECIDED_BY)
    applied = apply(cr_id, root=root)
    st.session_state["ui_warn"] = load_cr(cr_id, root=root).get("apply_warnings", [])
    target = p.get("concept") or ", ".join(f"{m} {r}" for m, r in applied.items())
    return f"{cr_id} uygulandı: aktif artık {target}."


def run_verify(p: dict) -> str:
    problems = verify(p["module"], p["rev"], root=data.root())
    if problems:
        raise RecordError(f"{p['module']} {p['rev']}: doğrulama başarısız: " + "; ".join(problems))
    return f"{p['module']} {p['rev']}: çıktı özetleri (sha256) kayıtla aynı."


def reset_diff() -> None:
    for k in ("rev_a", "rev_b"):
        st.session_state.pop(k, None)


def show_module_diff(module: str, rev_a: str, rev_b: str) -> None:
    st.session_state.update(rev_module=module, rev_a=rev_a, rev_b=rev_b)


TYPE_TR = {"design": "tasarım", "maintenance": "bakım"}

widgets.page_title("Revizyonlar")
widgets.flash()
if not started:
    st.info("Henüz kayıtlı revizyon yok.")
    st.stop()

module = st.selectbox("Modül", started, format_func=lambda m: f"{m} {data.NAMES_TR[m]}", key="rev_module",
                      on_change=reset_diff)
manifests = snap["revisions"][module]
revs = [m["revision"] for m in manifests]

widgets.section("Modül zaman çizelgesi")
st.markdown(" → ".join(badge(f"{r} aktif", "blue") if r == active[module] else badge(r, "gray") for r in revs))
for m in reversed(manifests):
    rev, is_active = m["revision"], m["revision"] == active[module]
    with st.container(border=True):
        info, act = st.columns([5, 2], vertical_alignment="center")
        kind = TYPE_TR.get(m.get("revision_type"), "tür kayıtlı değil (REVIEW.md)")
        info.markdown(f"{badge(rev + (' aktif' if is_active else ''), 'blue' if is_active else 'gray')} "
                      f"{m['summary']}")
        info.caption(f"{m['date']} · {kind} · CR {m['change_request'] or '-'} · commit "
                     f"{(m['code_commit'] or '-')[:10]} · {m['reason']}")
        b1, b2 = act.columns(2)
        not_reproducible = None if is_active else data.reproducible(module, rev)
        if not_reproducible:
            info.caption(f"Geçmiş kaydı: bu revizyona dönülemez (güncel kodla yeniden üretilemiyor: "
                         f"{not_reproducible})")
        if b1.button("Bu revizyona dön", key=f"revert_{rev}", disabled=is_active or bool(not_reproducible),
                     help=not_reproducible, width="stretch"):
            targets = {module: rev}
            widgets.request("revert", f"{module}: {rev} revizyonuna dönülsün mü?",
                            [f"Şu an aktif: {active[module]} → yeni aktif: {rev}", *impact_lines(targets)],
                            "Onayla ve uygula", FULL_STATE, targets=targets,
                            reason=f"Revizyonlar sayfası: {module} {active[module]} -> {rev}")
        if b2.button("Doğrula", key=f"verify_{rev}", width="stretch"):
            widgets.request("verify", f"{module} {rev} doğrulansın mı?",
                            ["Kayıttaki çıktı dosyalarının sha256 özetleri yeniden hesaplanır (yalnızca okuma)."],
                            "Doğrula", module=module, rev=rev)

widgets.section("Fark görünümü")
default_b = revs.index(active[module]) if active[module] in revs else len(revs) - 1
a_col, b_col = st.columns(2)
rev_b = b_col.selectbox("B (yeni)", revs, index=default_b, key="rev_b")
rev_a = a_col.selectbox("A (eski)", revs, index=max(revs.index(rev_b) - 1, 0), key="rev_a")
d = data.diff(module, rev_a, rev_b)
st.caption(f"core.diff.diff_revisions({module}, {rev_a}, {rev_b})")

if is_empty(d):
    st.success("Fark yok.")
else:
    p_tab, r_tab, b_tab, o_tab = st.tabs([f"Parametreler ({len(d['params'])})", f"Sonuçlar ({len(d['results'])})",
                                          "BOM", f"Çıktılar ({len(d['outputs'])})"])
    with p_tab:
        table([{"Yol": c["path"], "Eski": value(c["old"]), "Yeni": value(c["new"])} for c in d["params"]])
    with r_tab:
        st.dataframe(pd.DataFrame([{"Anahtar": c["key"], "Eski": value(c["old"]), "Yeni": value(c["new"]),
                                    "Fark": data.num(c["delta"]) if c["delta"] is not None else "",
                                    "%": data.num(c["pct"], 2) if c["pct"] is not None else ""}
                                   for c in d["results"]]), hide_index=True, width="stretch")
    with b_tab:
        bom = d["bom"]
        st.markdown(f"Eklenen: {', '.join(bom['added']) or '-'} · Silinen: {', '.join(bom['removed']) or '-'}")
        rows = [{"Parça": "(başlık)", "Yol": c["path"], "Eski": value(c["old"]), "Yeni": value(c["new"])}
                for c in bom["header"]]
        rows += [{"Parça": pid, "Yol": c["path"], "Eski": value(c["old"]), "Yeni": value(c["new"])}
                 for pid, changes in bom["changed"].items() for c in changes]
        table(rows)
    with o_tab:
        table([{"Dosya": o["file"], "Eski sha256": (o["old"] or "-")[:16], "Yeni sha256": (o["new"] or "-")[:16]}
               for o in d["outputs"]])

widgets.section("Konsept zaman çizelgesi")
concepts = snap["concepts"]
for c in reversed(concepts):
    cid, is_active = c["concept"], c["concept"] == snap["concept"]
    pins = {m: r for m, r in c["modules"].items() if r is not None}
    with st.container(border=True):
        info, act = st.columns([5, 2], vertical_alignment="center")
        info.markdown(f"{badge(cid + (' aktif' if is_active else ''), 'blue' if is_active else 'gray')} {c['summary']}")
        info.caption(f"{c['date']} · " + ", ".join(f"{m} {r}" for m, r in pins.items())
                     + f" · başlamamış: {', '.join(m for m, r in c['modules'].items() if r is None) or '-'}")
        blocked = None if is_active else next(
            (f"{m} {r}: {why}" for m, r in pins.items() if (why := data.reproducible(m, r))), None)
        if blocked:
            info.caption(f"Geçmiş kaydı: bu konsepte dönülemez ({blocked})")
        if act.button("Bu konsepte dön", key=f"revert_concept_{cid}", disabled=is_active or not pins or bool(blocked),
                      help=blocked, width="stretch"):
            widgets.request("revert", f"{cid} konseptine dönülsün mü?",
                            ["Modüller: " + ", ".join(f"{m} {active.get(m)} → {r}" for m, r in pins.items()),
                             *impact_lines(pins)],
                            "Onayla ve uygula", FULL_STATE + " Tek bir revert CR'si bütün modülleri listeler.",
                            targets=pins, concept=cid, reason=f"Revizyonlar sayfası: konsept {snap['concept']} -> {cid}")
if len(concepts) >= 2:
    ids = [c["concept"] for c in concepts]
    ca, cb = st.columns(2)
    c_b = cb.selectbox("Konsept B", ids, index=len(ids) - 1, key="concept_b")
    c_a = ca.selectbox("Konsept A", ids, index=max(ids.index(c_b) - 1, 0), key="concept_a")
    rows = data.diff_concepts(c_a, c_b)
    for r in rows:
        a, b, link = st.columns([1, 3, 2], vertical_alignment="center")
        a.markdown(f"**{r['module']}**")
        b.markdown(f"{r['old'] or '-'} → {r['new'] or '-'}")
        link.button("Modül farkını göster", key=f"cdiff_{r['module']}", disabled=not (r["old"] and r["new"]),
                    on_click=show_module_diff, args=(r["module"], r["old"], r["new"]), width="stretch")
    if not rows:
        st.success("Sabitlenen revizyonlar aynı.")

widgets.confirm_pending({"revert": run_revert, "verify": run_verify})
