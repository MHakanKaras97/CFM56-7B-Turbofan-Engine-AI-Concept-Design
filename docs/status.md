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

## Son yapılanlar
- UI spesifikasyonu (docs/design/ui_spec.md, 4 maketten); ADR-011 (revizyonda section.svg, GLB/STEP önbellekte).
- Kavramsal düzen referansı: docs/design/concept_reference.yaml -> tools/reference.py -> engine_reference.svg; check_layout() taslağı.
- Araçlar .venv'e kuruldu (Python 3.13): streamlit 1.65.0, cadquery 2.8.0 (OCP 7.9.3.1.1), gmsh 4.15.2; smoke testleri geçti.
- Harici araçlar: PrePoMax 2.6.0 (C:\Tools, ccx 2.22), ParaView 6.2.0 (pvpython çalışıyor), Autodesk Fusion kurulu. Fusion MCP bağlı değil; .step dosya ilişkilendirmesi yok.
- ADR-010: entegrasyon kontrolü tasarım noktası yeniden dengelemesi (alanlar serbest); çekirdek EGT etkisini yaklaşık yarı küçük gösteriyor. Geçici EGT toleransı 5 K [T] (önceden 10).
- **M0 v1 tamam.** concept001: M0 rev005, M1-M9 null. Kabul listesi 6/6 (analysis/acceptance_M0.md), kabul testleri 5/5.
- Params CR'leri: core/requests.py `params` türü; apply() params'ı yazar, hesabı yeniden çalıştırır (analysis/calc.py), revizyon oluşturur, results.yaml ve icd.yaml'ı yeniden üretir. Bütçe CR'leri iki seçenek sunar: (a) M0 params, (b) modül yeniden tasarımı.
- Entegrasyon kontrolü: varsayılan `thrust_held` (itki + W2 sabit), eski mod `operating_point`.
- CLAUDE.md: türetilmiş dosyalar elle düzenlenmez.
- M0 ICD ve bütçeler (icd.yaml, station_ownership.md, core/budgets.py); belirsizlik bandı; ders 02.
- M0 rev005: ICAO -7B27, benzerlik koşulu (ADR-009), Δη = 0.0171; Girão doğrulaması 18/19 (P5 beklenen hata).

## M0 v1 özeti (rev005) [H]
- W2 345.4 kg/s, W2/A 201.3, FPR 1.765 [KS], HPC PR 10.85, T3 817.5 K, T4 1670.7 K, T41 1629.2 K.
- W31 50.08 kg/s, SFC 10.574, EGT gösterilen 874.9 °C (pay 75 K), ideal V18/V8 0.6036, itki tavanına pay %7.8.
- Belirsizlik bandı: T4 1659-1682 K (Δη'nın hangi gruba uygulandığına göre).
- Verim -0.01 (itki sabit) ΔEGT, model / Martins: fan 3.1/4, booster 1.9/3, HPC 4.3/8, HPT 5.3/12, LPT 5.5/6 K.

## Açık konular
- HPC ve HPT verim kaybının EGT etkisi Martins'in yaklaşık yarısı: sabit geometri yok (ADR-010). M0 v2 ile çözülecek.
- Δη = +0.017 sınanmamış bir varsayım; tolerans ve entegrasyon sınırları [T].
- Bennett künyesi doğrulanmadı. Indriyati HPC havası tanım farkı.

## Sıradaki adımlar
1. Arayüz (Streamlit), ui_spec.md'ye göre; açık noktalar: CR'de yapısal etki metrikleri, revizyon farkı (core), .step ilişkilendirmesi.
2. M1 Inlet & Fan: ders + araştırma; icd.yaml'daki M1 bütçesinden başla.
3. M0 v2: off-design modeli (sabit A8, A18, HPT NGV kapasitesi, bileşen haritaları); entegrasyon kontrolü ve seyir noktası bunun üzerine kurulur.

## Çalışma kuralları
- Görev sonu raporu: Commit / Done / Decisions for user / Tests (max 15 satır).
- Kaynak bulunamazsa uydurma; "doğrulanamadı" yaz.
