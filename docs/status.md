# Proje durumu

## Amaç
CFM56-7B27 sınıfı (temel, SAC) turbofan için konsept seviyesinde çoklu agent tasarım sistemi.
M0 motor agent'ı + M1–M9 modül agent'ları (Claude Code subagent). Öğrenmek + belgelemek.

## Temel kararlar
- Mimari: docs/architecture.md, ADR-001..011.
- Tek doğru kaynak: bom.yaml + kod; Fusion sadece görünüm (STEP).
- Revizyonlar değişmez; aktif = records/ACTIVE. Değişiklik yalnızca CR + kullanıcı onayı.
- Güven etiketleri: K, KS, H, G, T. Sayılar koddan gelir, LLM metninden değil.
- Telif: kendi cümlelerimiz, kaynaklar docs/sources.md'de lisansıyla; PDF/xlsx git'e girmez.
- Tasarım noktası: deniz seviyesi, ISA, maksimum kalkış. Seyir noktası sonra.
- M8 devir referansları M0 kurallarında (girao_2023.yaml); M8'e aktarım M8'in işi.
- Çalışma döngüsü (her modül): ders -> araştırma -> rule book -> kod -> kabul testi. Testsiz sonraki modüle geçilmez.

## Kararlar (2026-10-18, UI öncesi)
- "Fusion'da aç": kullanıcı Windows'ta .step dosyalarını Fusion ile ilişkilendirir; UI işletim sistemi ilişkilendirmesini kullanır, sabit yol yok.
- CR şeması: yapısal "impact" alanı (metrik -> {value, unit, tag}); UI kartları buradan okur.
- core: Revizyonlar sayfası için revizyon farkı fonksiyonu.
- Araç yolları: config/tools.local.yaml (git dışı, makineye özel) + config/tools.example.yaml (commit). Kod araç yollarını yalnızca buradan okur (core/toolpaths.py).
- Talepler sayfası: tek "Kararı kaydet" düğmesi; (b) seçeneği = ret. Kabul edildi.

## Son yapılanlar
- UI faz 3: Talepler (etki kartları, seçenekler, zorunlu not, onay penceresi -> yalnızca decide, decided_by "user (UI)", geçmiş), Revizyonlar (modül/konsept zaman çizelgesi, A->B farkı), Öğrenme (notlar, kaynaklar, etiket açıklaması), Modüller (liste + modül şablonu), şerit/kart tıklama ile gezinme, M0 Bilgi sekmesi. Uygula, geri dönüş ve doğrulama düğmeleri henüz yok.
- M0 rev006 + concept002: results.yaml'a `assumptions` ([T] girdiler) ve kontrollerde `ref_tag`; sayılar rev005 ile aynı (core/diff ile doğrulandı). icd.yaml rev006'dan yeniden üretildi.
- UI faz 2 (salt okunur): ui/app.py (st.navigation), ui/pages/ (6 sayfa), ui/data.py (core üzerinden okuma, mtime anahtarlı önbellek), ui/widgets.py (üst çubuk). Genel bakış ve M0 motor dolu; diğerleri "3. aşamada". core: revision_ids, read_revision, read_concept, list_crs. Çalıştırma: depo kökünden `streamlit run ui/app.py`. Tarayıcıda görsel kontrol yapılmadı (yalnızca AppTest + headless sağlık kontrolü).
- Fusion MCP kullanılabilir: http://127.0.0.1:27182/mcp (HTTP, Fusion eklentisi; yerel kapsamda kayıtlı, commit edilmez). Araçlar: fusion_mcp_read (belge/proje/lisans/API dokümanı/ekran görüntüsü, salt okunur), fusion_mcp_execute (modelde işlem), fusion_mcp_update (model güncelleme), fusion_mcp_electronics_read. Salt okunur test: açık belge listesi -> 0 belge. Fusion MCP için Fusion açık olmalı; ona ihtiyaç duyan testler aksi halde atlanır. Araçlar Claude Code yeniden başlatılınca oturuma yüklenir.
- CR kuralı: impact.by (üretici) kaydedilir; onay için impact.affected_modules boş olmamalı. Önceden doldurulmuş etki yalnızca bütçe CR'lerinde (M0 integration_check); modül CR'leri M0 set_impact bekler.
- UI faz 1: CR `impact.metrics` (isteğe bağlı; bütçe CR'leri dSFC %, dEGT K, dT41 K ile doldurur, onay için etki hazır). core/diff.py: diff_revisions, diff_concepts (saf veri). .cache/geometry/test_box.step üretildi (Fusion ilişkilendirme testi).
- Araç yolları yapılandırması: core/toolpaths.py; ccx yapılandırılan yoldan çalıştı ("This is Version 2.22"; girdisiz: kullanım satırı).
- UI spesifikasyonu (docs/design/ui_spec.md); ADR-011 (revizyonda section.svg, GLB/STEP önbellekte).
- Kavramsal düzen referansı: concept_reference.yaml -> tools/reference.py -> engine_reference.svg; check_layout() taslağı.
- Araçlar (.venv, Python 3.13): streamlit 1.65.0, cadquery 2.8.0 (OCP 7.9.3.1.1), gmsh 4.15.2; smoke testleri geçti.
- Harici: PrePoMax 2.6.0 (C:\Tools, ccx 2.22), ParaView 6.2.0, Autodesk Fusion (MCP: aşağıya bakın).
- ADR-010: entegrasyon kontrolü tasarım noktası yeniden dengelemesi; geçici EGT toleransı 5 K [T].
- **M0 v1 tamam.** concept001: M0 rev005, M1-M9 null. Kabul listesi 6/6, kabul testleri 5/5.
- Params CR'leri (apply: params -> yeniden hesap -> revizyon -> results.yaml + icd.yaml); bütçe CR'si seçenekleri (a)/(b).
- M0 ICD ve bütçeler, belirsizlik bandı, ders 02; rev005 benzerlik koşulu (ADR-009), Girão 18/19.

## M0 v1 özeti (rev005 = rev006 sayıları) [H]
- W2 345.4 kg/s, W2/A 201.3, FPR 1.765 [KS], HPC PR 10.85, T3 817.5 K, T4 1670.7 K, T41 1629.2 K.
- W31 50.08 kg/s, SFC 10.574, EGT gösterilen 874.9 °C (pay 75 K), ideal V18/V8 0.6036, itki tavanına pay %7.8.
- Belirsizlik bandı: T4 1659-1682 K (Δη'nın hangi gruba uygulandığına göre).
- Verim -0.01 (itki sabit) ΔEGT, model / Martins: fan 3.1/4, booster 1.9/3, HPC 4.3/8, HPT 5.3/12, LPT 5.5/6 K.

## Açık konular
- HPC ve HPT verim kaybının EGT etkisi Martins'in yaklaşık yarısı: sabit geometri yok (ADR-010). M0 v2 ile çözülecek.
- Δη = +0.017 sınanmamış bir varsayım; tolerans ve entegrasyon sınırları [T].
- .step ilişkilendirmesi kullanıcıda bekliyor. Bennett künyesi doğrulanmadı. Indriyati HPC havası tanım farkı.

## Sıradaki adımlar
1. UI kalanlar: CR Uygula düğmesi, revizyon geri dönüş + verify, konsept farkından modül farkına geçiş, tarayıcıda açık/koyu tema kontrolü.
2. M1 Inlet & Fan: ders + araştırma; icd.yaml'daki M1 bütçesinden başla.

Yol haritası: M0 v2 off-design modeli (sabit A8, A18, HPT NGV kapasitesi, bileşen haritaları); entegrasyon kontrolü ve seyir noktası bunun üzerine kurulur.

## Çalışma kuralları
- Görev sonu raporu: Commit / Done / Decisions for user / Tests (max 15 satır).
- Kaynak bulunamazsa uydurma; "doğrulanamadı" yaz.
