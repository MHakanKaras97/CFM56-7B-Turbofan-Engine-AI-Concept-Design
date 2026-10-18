import pandas as pd
import streamlit as st

from ui import data, widgets
from ui.widgets import badge, tag_badge

snap = data.snapshot()
m0 = snap["m0"]
results, icd = m0["results"], m0["icd"]
val = m0["validation"]

head, button = st.columns([4, 1], vertical_alignment="center")
widgets.page_title("M0 motor", head)
button.page_link(widgets.PAGES["revizyonlar"], label="Revizyonları karşılaştır", icon=":material/compare_arrows:")
rev_badge = badge(f"{m0['rev']} aktif", "green") if m0["rev"] else badge("revizyon yok", "gray")
st.markdown(f"{rev_badge} &nbsp; Doğrulama: Girão {val['passed']}/{val['total']}",
            help="kaynak engine/M0_engine/analysis/validation_girao.md")

if results is None:
    st.info("M0'ın aktif revizyonu yok.")
    st.stop()
if icd is None:
    st.error(m0["icd_error"])
    st.stop()

src = icd["source"]["revision"]
main_tab, info_tab = st.tabs(["Genel", "Bilgi"])


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


def reference_text(c) -> str:
    ref = c.get("reference")
    if isinstance(ref, list):
        text = " – ".join(data.num(x) for x in ref)
    elif isinstance(ref, dict):
        text = ", ".join(f"{k} {data.num(v)}" for k, v in ref.items())
    else:
        text = data.num(ref)
    return f"ref {text} {widgets.ref_tag(c.get('ref_tag'))}".rstrip()


with main_tab:
    left, right = st.columns([3, 2], gap="large")

with left:
    widgets.section("İstasyon tablosu")
    main = [s for s in m0["station_order"] if s in icd["stations"]]
    st.dataframe(station_rows(main), hide_index=True, width="stretch")
    with st.expander(f"Tüm istasyonlar ({len(icd['stations'])})"):
        st.dataframe(station_rows(list(icd["stations"])), hide_index=True, width="stretch")
    st.caption(f"Her değerin etiketi tabloda · kaynak {src} (rules/icd.yaml)")

with right:
    widgets.section("Kontroller")
    for c in results["checks"]:
        name = c["name"] + (" (sert)" if c.get("hard") else "")
        value = data.quantity({"value": c["value"], "unit": c.get("unit"), "tag": "H"})
        color, label = {"pass": ("green", "geçti"), "fail": ("red", "kaldı")}.get(c["result"], ("blue", "bilgi"))
        a, b = st.columns([3, 2], vertical_alignment="center")
        a.markdown(name, help=c.get("criterion"))
        b.markdown(f"{value} {badge(label, color)}", help=reference_text(c))
        a.caption(reference_text(c))
    st.caption(f"Sert kontrollerin hepsi geçti: {'evet' if results.get('hard_checks_passed') else 'hayır'}"
               f" · kaynak {m0['rev']}/results.yaml")
    widgets.section("Varsayımlar [T]")
    assumptions = results.get("assumptions")
    if assumptions is None:
        st.caption(f"{m0['rev']} sonuçlarında varsayım listesi yok.")
    for e in assumptions or []:
        value = data.quantity({**e, "tag": None}) if e.get("value") is not None else e.get("target", "")
        st.markdown(f"{tag_badge('T')} `{e['path']}` · {value}", help=e.get("note"))
    st.caption(f"Sonucun dayandığı [T] girdiler · kaynak {m0['rev']}/results.yaml (assumptions)")

widgets.section("Modül bütçeleri (ICD)", main_tab)
tols = icd["tolerances"]
cols = main_tab.columns(3)
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
main_tab.caption(f"İzin verilen sapmalar [{tols['efficiency']['tag']}] · kaynak {src} (rules/icd.yaml)")

with info_tab:
    info = data.info_sections()
    st.markdown(info["band"])
    st.caption("kaynak engine/M0_engine/rules/cycle_inputs.md")
    st.divider()
    st.markdown(info["sensitivity"])
    st.caption("kaynak engine/M0_engine/analysis/acceptance_M0.md")
    st.divider()
    st.warning("Entegrasyon kontrolünün sınırı (ADR-010): çekirdek modülleri (M3, M5) için EGT sonuçları "
               "iyimserdir; geçici EGT toleransı 5 K [T].")
    with st.expander("ADR-010 tam metin"):
        st.markdown(info["adr010"])
