# Proje durumu

## Amaç
CFM56-7B27 sınıfı (temel, SAC) turbofan için konsept seviyesinde çoklu agent tasarım sistemi.
M0 motor agent'ı + M1–M9 modül agent'ları (Claude Code subagent). Öğrenmek + belgelemek.

## Temel kararlar
- Mimari: docs/architecture.md, ADR-001..008.
- Tek doğru kaynak: bom.yaml + kod; Fusion sadece görünüm (STEP).
- Revizyonlar değişmez; aktif = records/ACTIVE. Değişiklik yalnızca CR + kullanıcı onayı.
- Güven etiketleri: K, KS, H, G, T. Sayılar koddan gelir, LLM metninden değil.
- Telif: kendi cümlelerimiz, kaynaklar docs/sources.md'de lisansıyla; PDF/xlsx git'e girmez.
- Tasarım noktası: deniz seviyesi, ISA, maksimum kalkış. Seyir noktası sonra.
- M8 devir referansları M0 kurallarında (girao_2023.yaml); M8'e aktarım M8'in işi.
- Çalışma döngüsü (her modül): ders -> araştırma -> rule book -> kod -> kabul testi. Testsiz sonraki modüle geçilmez.

## Son yapılanlar
- M0 ICD ve modül bütçeleri: rules/icd.yaml (analysis/icd.py ile rev005'ten üretilir), station_ownership.md, core/budgets.py (check_budget), analysis/integration.py (entegrasyon kontrolü, sınır dışında taslak CR).
- Belirsizlik bandı (bilgi): Δη kompresörlere / türbinlere / eşit -> T4 1659-1682 K, W2 ±0.6 kg/s, EGT 2.7 K yayılım.
- Ders 02 (kalibrasyon, v1 -> rev005).
- M0 rev005 (aktif): ICAO -7B27, benzerlik koşulu (ADR-009), Δη = 0.0171. Tüm kontroller geçti.
- Parça bilgi dokümanı v0.2; Girão doğrulaması kabul edildi (18/19, P5 beklenen hata).
- M0 v4.1 girdileri (Girão Şekil 4.9); v3 değişken cp (rev003); ADR-006/007/008.

## M0 rev005 sonucu [H]
- Δη = 0.0171: η fan dış/iç 0.895/0.887, booster 0.907, HPC 0.853, HPT 0.897, LPT 0.934. FPR 1.765 [KS].
- W2 = 345.4 kg/s, W2/A = 201.3, HPC PR = 10.85, T3 = 817.5 K.
- T4 = 1670.7 K, T41 = 1629.2 K, W31 = 50.08 kg/s, SFC 10.574.
- EGT model 844.9 °C (Girão 125.7 kN'de ~851), gösterilen 874.9 °C (TCDS 950, pay 75 K).
- İdeal V18/V8 = 0.6036 (Girão 0.627). İtki tavanı 130.91 kN (W2 430), pay %7.8.
- Kontroller: fan choke (HARD), W2/A, W2, ikincil hava, SFC, EGT sınırı geçti.
- Δη taraması (bilgi): V18/V8, Δη = 0'da 0.849, 0.03'te 0.537; W2 372.0 -> 335.2.
- Yedek yol (bilgi, kullanılmadı): Δη = 0 ve FPR serbest -> FPR 1.612, W2 381.7, T4 1608 K.

## Açık konular
- Δη = +0.017 sınanmamış bir varsayım; Girão ile ICAO arasındaki yaklaşık %5'lik SFC farkını kapatıyor.
- Benzerlik hedefi modelin değeri (0.6036); Girão'nun 0.627'si ile fark −%3.7.
- Bennett künyesi doğrulanmadı (büyük olasılıkla AIAA SciTech 2024).
- Indriyati HPC havası 39.57 vs model çekirdek havası (tanım farkı).
- Bütçe toleransları ve entegrasyon sınırları [T]; ICD bütçe CR'leri taslak olarak kalır.

## Sıradaki adımlar
1. Kabul listesinin kalan maddeleri (parametre değişikliği, geri dönüş, çakışma testleri).
2. ICD için CR uygulama yolu: bütçe CR'leri BOM yolu değil; apply() bunları uygulayamaz.
3. Arayüz (Streamlit).
4. M1 Inlet & Fan: ders + araştırma.

## Çalışma kuralları
- Görev sonu raporu: Commit / Done / Decisions for user / Tests (max 15 satır).
- Kaynak bulunamazsa uydurma; "doğrulanamadı" yaz.
