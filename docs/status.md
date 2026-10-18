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
- M0 v4.1: Girão Şekil 4.9 girdileri [KS]; izentropik verimler, iki adımlı çekirdek sıkıştırma (iç fan + booster), lüle itki/debi katsayıları, güç çekişi 0, LHV 43.124 [T], HPC ara kademe kaçağı (%50 entalpi artışı [T], 45'te döner), 43/44 istasyonları.
- v4.1 doğrulama (Girão 125.73 kN): 19 kalemin 18'i geçti; P5 kaldı (xfail strict). Nominal noktaya dokunulmadı.
- Öğrenme notu: docs/learning/cfm56_7b_module_facts.md (Girão §3); fan kanadı (24) ve yakıt memesi (20) sayıları çözüldü.
- M0 cycle v4 (ADR-008): FPR girdi; bilinmeyenler W2, T4; hedefler itki, yakıt. Nominal nokta (v4 girdileriyle) çözümsüzdü: en fazla 118.0 kN. rev004 yok; aktif rev003.
- M0 cycle v3 (rev003): değişken cp(T, FAR), NASA 7 katsayılı polinomlar; ADR-007 (44.52 kontrol).
- Sürekli entalpi (ADR-006); rev001 geçersiz. Ders: hedefleri tutturmak sonucu doğrulamaz.

## v4.1 doğrulama sapmaları (model / Girão, %) [H]
- W2 355.8 (−0.70), T13 +0.05, P13 −0.02, T21 +0.03, T25 +0.05, P25 −0.02, T3 840.1 (+0.26), P3 +0.01.
- W3 60.11 (−0.64), W31 53.36 (−0.64), T4 1708.4 (+1.06), T41 +1.05, T43 +1.30, P44 716.7 (+1.65), T44 +1.26.
- T45 +1.20, T5 916.2 (+1.56), P5 177.0 (+3.46, kalır; sınır 3), EGT 1138.3 (+1.27).
- %1'i aşan ilk istasyon: T4 (yanma odası çıkışı). Ondan önceki her şey %0.7 içinde.
- LHV ±%0.3: T4 ∓5.2 K, W2 ∓1.2 kg/s, EGT ∓4.8 K. LHV −%0.3 ile (≈43.0) P5 +%2.23, her kalem geçer.
- V18/V8 = 0.610 (Girão ideal 0.627). W2/A = 207.3 (bant içinde).

## Açık konular
- T4 +%1.06 ve P5 +%3.46: yanma ve LPT tarafında kalan fark (LHV [T], yakıt özellikleri, kaçak çekiş noktası [T]).
- Nominal nokta için veri seti: ICAO yakıtı mı, Girão verimleri mi? (v4'te tutmadı; v4.1 girdileriyle denenmedi.)
- analysis/results.yaml hâlâ v4 nominal denemesinin (çözümsüz, eski girdiler) çıktısı.
- He 2025 ve Bennett vd. künyeleri eksik.

## Sıradaki adımlar
1. Nominal noktayı v4.1 girdileriyle dene (kullanıcı onayıyla); ardından rev004.
2. M0 kapsamını tamamla: istasyon tablosu -> modül bütçeleri, arayüz sözleşmesi.
3. Arayüz (Streamlit).
4. M1 Inlet & Fan: ders + araştırma.

## Çalışma kuralları
- Görev sonu raporu: Commit / Done / Decisions for user / Tests (max 15 satır).
- Kaynak bulunamazsa uydurma; "doğrulanamadı" yaz.
