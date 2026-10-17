# Proje durumu

## Amaç
CFM56-7B27 sınıfı (temel, SAC) turbofan için konsept seviyesinde çoklu agent tasarım sistemi.
M0 motor agent'ı + M1–M9 modül agent'ları (Claude Code subagent). Öğrenmek + belgelemek.

## Temel kararlar
- Mimari: docs/architecture.md, ADR-001..005.
- Tek doğru kaynak: bom.yaml + kod; Fusion sadece görünüm (STEP).
- Revizyonlar değişmez; aktif = records/ACTIVE. Değişiklik yalnızca CR + kullanıcı onayı.
- Güven etiketleri: K, KS, H, G, T. Sayılar koddan gelir, LLM metninden değil.
- Telif: kendi cümlelerimiz, kaynaklar docs/sources.md'de lisansıyla; PDF/xlsx git'e girmez.
- Tasarım noktası: deniz seviyesi, ISA, maksimum kalkış. Seyir noktası sonra.
- Çalışma döngüsü (her modül): ders -> araştırma -> rule book -> kod -> kabul testi. Testsiz sonraki modüle geçilmez.

## Son yapılanlar
- Sürekli entalpi düzeltmesi (ADR-006); rev001 geçersiz, REVIEW.md'de kayıtlı.
- M0 cycle v2 kalibre edildi (rev002, aktif).
- M0 cycle v2 ilk deneme (83b6856): h = cp·T hatası nedeniyle çözümsüz; neden bulundu.
- M0 cycle v1 (rev001): kalibrasyon hedefleri tuttu ama W2=447 kg/s ile W2/A=260.5, fan choke sınırını (241 kg/s/m²) aştı -> fizik dışı. Ders: hedefleri tutturmak sonucu doğrulamaz.
- ICAO EDB v32: -7B27 OPR 28.63, BPR 5.0, T/O yakıt 1.284 kg/s [K]. SFC = 10.57 g/kNs [H].
- core tamam: BOM şeması, revizyon, konsept manifest, CR akışı, kanonik BOM yazıcı.

## M0 v2 sonucu (rev002)
- W2 = 363.2 kg/s, W2/A = 211.7 kg/(s·m²), FPR = 1.833, HPC PR = 13.63.
- T4 = 1860 K, T41 = 1716 K, soğutma oranı = 0.2645 (çekirdek havası 60.5 kg/s, soğutma 16.0 kg/s).
- EGT (gösterilen) = 843.5 °C; TCDS sınırı 950 °C, pay 106 K.
- Kontroller: fan choke (HARD) geçti; W2/A, W2 (+%2.4), SFC ve EGT geçti. Soğutma oranı 0.12-0.22 aralığının dışında, kaldı (işaretli).
- Hassasiyet: her e_poly +0.01 -> W2 2-7 kg/s azalır, EGT 3-12 K artar. T4'ü yalnız e_hpc (-7 K) ve e_booster (-2 K) etkiler. Soğutma +0.02 -> T4 +19 K, W2 +3 kg/s, EGT -5 K.

## Açık konular
- 44.52 kg/s yanma odası havasına liner soğutması dahil mi? (Soğutma oranı 0.26 > 0.22, T4 = 1860 K yüksek.)
- FPR 1.83 beklenenden yüksek olabilir (doğrulanmadı).
- Indriyati HPC havası 39.57 vs Lopez-Pintor yanma odası havası 44.52 kg/s.
- EGT formülü CFM56-3 katsayılarıyla [T].
- ICAO test koşulunda müşteri bleed/güç çekişi doğrulanmadı.

## Sıradaki adımlar
1. v3: NASA Glenn polinomlarıyla değişken cp(T, FAR); 44.52 hedef mi kontrol mü kararı.
2. M0 kapsamını tamamla: istasyon tablosu -> modül bütçeleri, arayüz sözleşmesi, review_criteria.
3. Arayüz (Streamlit).
4. M1 Inlet & Fan: ders + araştırma.

## Çalışma kuralları
- Görev sonu raporu: Commit / Done / Decisions for user / Tests (max 15 satır).
- Kaynak bulunamazsa uydurma; "doğrulanamadı" yaz.
