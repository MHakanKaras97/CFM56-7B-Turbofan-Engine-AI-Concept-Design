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
- M0 cycle v4 (ADR-008): Girão 2023 girdileri [KS]; FPR 1.765 girdi; bilinmeyenler W2, T4; hedefler itki, yakıt. V18/V8 kuralı kaldırıldı.
- v4 nominal nokta (ICAO 121.43 kN, 1.284 kg/s) ÇÖZÜMSÜZ: bu yakıtla en fazla 118.0 kN (W2 395). rev004 yok; aktif rev003.
- v4 doğrulama (Girão 125.73 kN): 9 kalemin 7'si kaldı (testlerde xfail strict).
- M0 cycle v3 (rev003): değişken cp(T, FAR), NASA 7 katsayılı polinomlar; ADR-007 (44.52 kontrol).
- Sürekli entalpi (ADR-006); rev001 geçersiz. Ders: hedefleri tutturmak sonucu doğrulamaz.
- core tamam: BOM şeması, revizyon, konsept manifest, CR akışı, kanonik BOM yazıcı.

## v4 doğrulama sapmaları (model / Girão) [H]
- W2 387.6 / 358.28 (+%8.2), T4 1643 / 1690.5 (−%2.8), T41 −%2.7, T45 −%4.1, T5 −%6.2, P5 146.3 / 171.1 (−%14.5), EGT −%4.4.
- Geçen: T3 841.0 / 838.0 (+%0.4), P3 2997 (+%0.01).
- Tanı: Girão'nun W2 ve T4'ü modele verilince T45 −%0.3, T5 −%0.7, P5 −%3.6, yakıt −%1.4; itki 120.8 kN (−%3.9).
  Termodinamik yakın; özgül itki düşük. Şüpheliler, Girão'dan gelmeyen varsayımlar: cv 0.98 [G], LHV 43.0 [G], 100 kW çekiş [T].
- cv 1.0 ile doğrulama: W2 +%2.7, sıcaklıklar ±%2 içinde, P5 −%5.9 (kalır).
- Nominal nokta: Girão SFC 11.15, ICAO 10.57 g/(kN·s) (−%5.2). cv 1.0 + LHV 43.124 + çekiş 0 ile bile en fazla 121.2 kN.

## Açık konular
- Nominal nokta için hangi veri seti: ICAO yakıtı mı, Girão verimleri mi? (İkisi birlikte tutmuyor.)
- Lüle cv, LHV ve güç çekişi için Girão değerleri tezden okunmalı.
- W2/A: doğrulama noktasında 225.9 > 215 (fan çapı/göbek oranı [T]).
- Indriyati HPC havası 39.57 vs model çekirdek havası (tanım farkı).

## Sıradaki adımlar
1. Kullanıcı kararı: nominal nokta veri seti ve cv/LHV kaynağı; ardından rev004.
2. M0 kapsamını tamamla: istasyon tablosu -> modül bütçeleri, arayüz sözleşmesi.
3. Arayüz (Streamlit).
4. M1 Inlet & Fan: ders + araştırma.

## Çalışma kuralları
- Görev sonu raporu: Commit / Done / Decisions for user / Tests (max 15 satır).
- Kaynak bulunamazsa uydurma; "doğrulanamadı" yaz.
