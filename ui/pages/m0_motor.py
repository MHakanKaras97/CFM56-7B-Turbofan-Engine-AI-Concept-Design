import pandas as pd
import streamlit as st

from ui import data, widgets
from ui.widgets import badge, tag_badge

snap = data.snapshot()
m0 = snap["m0"]
results, icd = m0["results"], m0["icd"]
val = m0["validation"]

head, button = st.columns([4, 1], vertical_alignment="center")
head.title("M0 motor")
button.page_link(widgets.PAGES["revizyonlar"], label="Revizyonları karşılaştır", icon=":material/compare_arrows:")
rev_badge = badge(f"{m0['rev']} aktif", "green") if m0["rev"] else badge("revizyon yok", "gray")
st.markdown(f"{rev_badge} &nbsp; Doğrulama: Girão {val['passed']}/{val['total']}",
            help="kaynak engine/M0_engine/analysis/validation_girao.md")

if results is None:
    st.info("M0'ın aktif revizyonu yok.")
    st.stop()

src = icd["source"]["revision"]
left, right = st.columns([3, 2], gap="large")


def station_rows(ids):
    stations = icd["stations"]
    rows = []
    for sid in ids:
        s = stations[sid]
        q = {k: s[k] for k in ("Tt", "Pt", "W", "FAR")}
        rows.append({"İst.": sid, "Sahip": s["owner"] or "-",
                     "Tt [K]": data.num(q["Tt"]["value"], 1), "Pt [kPa]": data.num(q["Pt"]["value"], 2),
                     "W [kg/s]": data.num(q["W"]["value"], 2), "FAR [-]": data.num(q["FAR"]["value"], 5),
                     "Etiket": ", ".join(sorted({v["tag"] for v in q.values()}))})
    return pd.DataFrame(rows)


with left:
    st.subheader("İstasyon tablosu")
    main = [s for s in m0["station_order"] if s in icd["stations"]]
    st.dataframe(station_rows(main), hide_index=True, width="stretch")
    with st.expander(f"Tüm istasyonlar ({len(icd['stations'])})"):
        st.dataframe(station_rows(list(icd["stations"])), hide_index=True, width="stretch")
    st.caption(f"Her değerin etiketi tabloda · kaynak {src} (rules/icd.yaml)")

with right:
    st.subheader("Kontroller")
    for c in results["checks"]:
        name = c["name"] + (" (sert)" if c.get("hard") else "")
        value = data.quantity({"value": c["value"], "unit": c.get("unit"), "tag": "H"})
        color, label = {"pass": ("green", "geçti"), "fail": ("red", "kaldı")}.get(c["result"], ("blue", "bilgi"))
        a, b = st.columns([3, 2], vertical_alignment="center")
        a.markdown(name, help=c.get("criterion"))
        b.markdown(f"{value} {badge(label, color)}")
    st.caption(f"Sert kontrollerin hepsi geçti: {'evet' if results.get('hard_checks_passed') else 'hayır'}"
               f" · kaynak {m0['rev']}/results.yaml")
    estimates = data.tagged(results)
    with st.expander(f"[T] etiketli değerler ({len(estimates)})"):
        for e in estimates:
            st.markdown(f"{tag_badge('T')} `{e['path']}` · {data.quantity({**e, 'tag': None})}")

st.subheader("Modül bütçeleri (ICD)")
tols = icd["tolerances"]
cols = st.columns(3)
for i, (mid, mod) in enumerate(icd["modules"].items()):
    items = mod["budget"]
    checked = [(k, v) for k, v in items.items() if v["kind"] != "info"]
    with cols[i % 3].container(border=True):
        st.markdown(f"**{mid} {data.NAMES_TR.get(mid, mod['name'])}**")
        st.caption(" · ".join(f"{k} {data.quantity(v)} {data.tolerance(tols[v['kind']])}" for k, v in checked[:3]))
        with st.expander(f"Tüm kalemler ({len(items)})"):
            st.dataframe(pd.DataFrame([
                {"Kalem": k, "Değer": data.num(v["value"]), "Birim": data.unit_tr(v["unit"]), "Etiket": v["tag"],
                 "Tür": v["kind"], "İzin": data.tolerance(tols[v["kind"]])} for k, v in items.items()
            ]), hide_index=True, width="stretch")
st.caption(f"İzin verilen sapmalar [{tols['efficiency']['tag']}] · kaynak {src} (rules/icd.yaml)")
