# Proje durumu

## Amaç
CFM56-7B27 sınıfı (temel, SAC) turbofan için konsept seviyesinde çoklu agent tasarım sistemi.
M0 motor agent'ı + M1–M9 modül agent'ları (Claude Code subagent). Öğrenmek + belgelemek.

## Temel kararlar
- Mimari: docs/architecture.md, ADR-001..007.
- Tek doğru kaynak: bom.yaml + kod; Fusion sadece görünüm (STEP).
- Revizyonlar değişmez; aktif = records/ACTIVE. Değişiklik yalnızca CR + kullanıcı onayı.
- Güven etiketleri: K, KS, H, G, T. Sayılar koddan gelir, LLM metninden değil.
- Telif: kendi cümlelerimiz, kaynaklar docs/sources.md'de lisansıyla; PDF/xlsx git'e girmez.
- Tasarım noktası: deniz seviyesi, ISA, maksimum kalkış. Seyir noktası sonra.
- Çalışma döngüsü (her modül): ders -> araştırma -> rule book -> kod -> kabul testi. Testsiz sonraki modüle geçilmez.

## Son yapılanlar
- M0 cycle v3 (rev003, aktif): değişken cp(T, FAR), NASA 7 katsayılı polinomlar (TM-4513); soğutma 0.18 girdi [G].
- ADR-007: 44.52 kg/s yanma odası havası hedef değil, bilgi kontrolü. rev002 REVIEW.md'de "yerini aldı" olarak kayıtlı.
- Sürekli entalpi düzeltmesi (ADR-006); rev001 geçersiz.
- M0 cycle v1 (rev001): hedefler tuttu ama W2/A choke sınırını aştı. Ders: hedefleri tutturmak sonucu doğrulamaz.
- ICAO EDB v32: -7B27 OPR 28.63, BPR 5.0, T/O yakıt 1.284 kg/s [K]. SFC = 10.57 g/kNs [H].
- core tamam: BOM şeması, revizyon, konsept manifest, CR akışı, kanonik BOM yazıcı.

## M0 v3 sonucu (rev003, soğutma 0.18)
- W2 = 372.9 kg/s, W2/A = 217.3, FPR = 1.785, HPC PR = 13.63, T3 = 811.5 K [H].
- T4 = 1646.5 K, T41 = 1576.3 K, FAR = 0.0252; yanma odası havası 50.96 kg/s (44.52'ye göre +%14.5) [H].
- EGT (gösterilen) = 795.2 °C; TCDS sınırı 950 °C [T].
- HARD (fan choke 217.3 < 241.3) geçti. SFC, W2, soğutma, EGT sınırı geçti. W2/A 190-215 bandını aştı (kaldı).
- Soğutma taraması 0.14 -> 0.22: W2 367.0 -> 379.5, W2/A 213.9 -> 221.2, T4 1623 -> 1671 K, FPR 1.814 -> 1.754, EGT 804 -> 785 °C.
- Karşılaştırma (44.52 hedef, değişken cp): soğutma 0.352, W2/A 240.2 (choke'a çok yakın), T4 1752 K, FPR 1.629.
- Hassasiyet: e_poly +0.01 -> W2 2-6 kg/s azalır, T4 2-9 K, EGT 2-9 K artar.

## Açık konular
- W2/A 217.3 > 215: W2/A bandı, fan çapı/göbek oranı [T] veya FPR'ye bakılmalı.
- EGT 795 °C, 800-920 bilgi bandının altında; EGT formülü CFM56-3 katsayılarıyla [T].
- Indriyati HPC havası 39.57 vs model çekirdek havası 62.1 kg/s (tanım farkı).
- ICAO test koşulunda müşteri bleed/güç çekişi doğrulanmadı.

## Sıradaki adımlar
1. W2/A sapmasını açıkla (fan geometrisi [T] / bant) ve kayda geçir.
2. M0 kapsamını tamamla: istasyon tablosu -> modül bütçeleri, arayüz sözleşmesi, review_criteria.
3. Arayüz (Streamlit).
4. M1 Inlet & Fan: ders + araştırma.

## Çalışma kuralları
- Görev sonu raporu: Commit / Done / Decisions for user / Tests (max 15 satır).
- Kaynak bulunamazsa uydurma; "doğrulanamadı" yaz.
