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
- M0 cycle v2 (commit 83b6856, rev002 YOK): soğutma havası + yanma odası havası hedefi; kalibrasyon çözümsüz. Aktif revizyon hâlâ rev001.
- M0 cycle v1 (rev001): kalibrasyon hedefleri tuttu ama W2=447 kg/s ile W2/A=260.5, fan choke sınırını (241 kg/s/m²) aştı -> fizik dışı. Ders: hedefleri tutturmak sonucu doğrulamaz.
- ICAO EDB v32: -7B27 OPR 28.63, BPR 5.0, T/O yakıt 1.284 kg/s [K]. SFC = 10.57 g/kNs [H].
- core tamam: BOM şeması, revizyon, konsept manifest, CR akışı, kanonik BOM yazıcı.

## M0 v2 sonucu
- Durum: çözümsüz (results.yaml `status: infeasible`). rev002 oluşturulmadı; review_criteria gereği.
- Yakıt, V18/V8 ve yanma odası havası tutturulduğunda ulaşılabilen en yüksek itki 110.97 kN (c = 0.31); hedef 121.43 kN.
- c = 0.20'de: itki 109.4 kN, W2 = 334 kg/s, FPR = 1.80, T4 = 1755 K, W2/A = 194.6.
- T4 sabit 1755 K: yakıt + yanma odası havası f'yi, dolayısıyla T4'ü belirliyor.
- Soğutma ≥ 0.10 iken yanma odası hedefi olmadan da (itki + yakıt) çözüm yok.
- Kontroller ve hassasiyet çalıştırılmadı (kalibre sonuç yok).
- Olası neden: h = cp·T tanımı; yanma odasında cp 1005 -> 1150 sıçraması yakıt enerjisinin yaklaşık %10'unu kaybettiriyor, soğutma havası ~730 K gibi karışıyor.
- Tanı (commit edilmedi): T3'te sürekli entalpiyle çözüm var: c ≈ 0.26, W2 ≈ 362 kg/s, W2/A ≈ 211, T4 ≈ 1860 K.

## Açık konular
- v2 gaz modeli düzeltmesi (sürekli entalpi / değişken cp) kullanıcı kararı bekliyor; rev001 de HARD choke kuralını ihlal ediyor.
- Indriyati HPC havası 39.57 vs Lopez-Pintor yanma odası havası 44.52 kg/s.
- EGT formülü CFM56-3 katsayılarıyla [T].
- ICAO test koşulunda müşteri bleed/güç çekişi doğrulanmadı.

## Sıradaki adımlar
1. v2 sonuçlarını yorumla; gerekirse v3 (değişken cp, verim varsayımları).
2. M0 kapsamını tamamla: istasyon tablosu -> modül bütçeleri, arayüz sözleşmesi, review_criteria.
3. Arayüz (Streamlit).
4. M1 Inlet & Fan: ders + araştırma.

## Çalışma kuralları
- Görev sonu raporu: Commit / Done / Decisions for user / Tests (max 15 satır).
- Kaynak bulunamazsa uydurma; "doğrulanamadı" yaz.
