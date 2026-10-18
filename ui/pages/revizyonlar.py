"""Revision and concept timelines, the A -> B difference (core/diff.py), revert and verify (core/records.py).

Writes: core.records.revert only, after a confirmation dialog. Verify only reads.
"""

import pandas as pd
import streamlit as st

from core.diff import is_empty
from core.records import RecordError, revert, verify
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


def run_revert(p: dict) -> str:
    revert(p["module"], p["rev"], root=data.root())
    return f"{p['module']}: aktif revizyon artık {p['rev']}."


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
        if b1.button("Bu revizyona dön", key=f"revert_{rev}", disabled=is_active, width="stretch"):
            widgets.request("revert", f"{module}: {rev} aktif yapılsın mı?",
                            [f"Şu an aktif: {active[module]} → yeni aktif: {rev}"], "Aktif yap",
                            "core.records.revert: yalnızca records/ACTIVE ve bom.yaml değişir; kayıtlar silinmez. "
                            "Analiz dosyaları (params, results.yaml, icd.yaml) ve aktif konsept değişmez.",
                            module=module, rev=rev)
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
st.dataframe(pd.DataFrame([
    {"Konsept": c["concept"] + (" (aktif)" if c["concept"] == snap["concept"] else ""), "Tarih": c["date"],
     "Özet": c["summary"], **{m: c["modules"].get(m) or "-" for m in data.MODULES}}
    for c in reversed(concepts)
]), hide_index=True, width="stretch")
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
