"""Revision and concept timelines, and the A -> B difference from core/diff.py. Read-only."""

import pandas as pd
import streamlit as st

from core.diff import is_empty
from ui import data
from ui.widgets import badge

snap = data.snapshot()
active = {r["id"]: r["active"] for r in snap["modules"]}
started = [m for m in data.MODULES if snap["revisions"][m]]


def value(x) -> str:
    if isinstance(x, (list, dict)):
        return str(x)
    return data.num(x)


st.title("Revizyonlar")
if not started:
    st.info("Henüz kayıtlı revizyon yok.")
    st.stop()

module = st.selectbox("Modül", started, format_func=lambda m: f"{m} {data.NAMES_TR[m]}", key="rev_module")
manifests = snap["revisions"][module]
revs = [m["revision"] for m in manifests]

st.subheader("Modül zaman çizelgesi")
st.markdown(" → ".join(badge(f"{r} aktif", "blue") if r == active[module] else badge(r, "gray") for r in revs))
st.dataframe(pd.DataFrame([
    {"Revizyon": m["revision"] + (" (aktif)" if m["revision"] == active[module] else ""), "Tarih": m["date"],
     "Özet": m["summary"], "Gerekçe": m["reason"], "CR": m["change_request"] or "-",
     "Kod commit": (m["code_commit"] or "-")[:10]}
    for m in reversed(manifests)
]), hide_index=True, width="stretch")

st.subheader("Fark görünümü")
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
        st.dataframe(pd.DataFrame([{"Yol": c["path"], "Eski": value(c["old"]), "Yeni": value(c["new"])}
                                   for c in d["params"]]), hide_index=True, width="stretch")
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
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    with o_tab:
        st.dataframe(pd.DataFrame([{"Dosya": o["file"], "Eski sha256": (o["old"] or "-")[:16],
                                    "Yeni sha256": (o["new"] or "-")[:16]} for o in d["outputs"]]),
                     hide_index=True, width="stretch")

st.subheader("Konsept zaman çizelgesi")
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
    if rows:
        st.dataframe(pd.DataFrame([{"Modül": r["module"], "A": r["old"] or "-", "B": r["new"] or "-"} for r in rows]),
                     hide_index=True, width="stretch")
    else:
        st.success("Sabitlenen revizyonlar aynı.")
st.caption("Geri dönüş (Aktif yap) ve çıktı doğrulama bu aşamada yok; salt okunur.")
