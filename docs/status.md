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
- M0 rev004 (aktif): ICAO -7B27 nominal noktası, Girão v4.1 girdileri, Δη = 0 [H]. HARD geçti.
- Girão doğrulaması kabul edildi: 19 kalemden 18'i geçti, P5 +%3.46 beklenen hata (analysis/validation_girao.md). Kabul listesi: "hesap doğrulama" tamam.
- M0 v4.1: izentropik verimler, iç fan + booster, lüle itki/debi katsayıları, HPC ara kademe kaçağı, 43/44 istasyonları.
- Öğrenme notu: docs/learning/cfm56_7b_module_facts.md (fan 24 kanat, 20 yakıt memesi).
- M0 cycle v3 (rev003): değişken cp(T, FAR), NASA 7 katsayılı polinomlar; ADR-007 (44.52 kontrol).
- Sürekli entalpi (ADR-006); rev001 geçersiz. Ders: hedefleri tutturmak sonucu doğrulamaz.

## M0 rev004 sonucu (Δη = 0) [H]
- W2 = 372.0 kg/s, W2/A = 216.8, FPR = 1.765 (Girão), HPC PR = 10.85, T3 = 830.0 K.
- T4 = 1626.6 K, T41 = 1587.6 K, FAR 0.0238, W31 = 53.94 kg/s; SFC 10.574.
- EGT model 793.2 °C, gösterilen 823.2 °C (TCDS sınırı 950). V18/V8 = 0.858 (Girão ideali 0.627).
- Kontroller: fan choke (HARD), W2, ikincil hava, SFC, EGT sınırı geçti. W2/A 216.8 > 215 kaldı (yumuşak).
- Bu yakıtla itki tavanı 122.88 kN (W2 400); hedef tavanın %1.2 altında, düşük W2 dalında.
- Δη taraması 0 -> 0.03: W2 372.0 -> 335.2, W2/A 216.8 -> 195.4, T4 1627 -> 1686 K, T41 1588 -> 1644 K,
  EGT (gösterilen) 823 -> 897 °C, W31 53.9 -> 48.6 kg/s. Hepsi çözülüyor; HARD hepsinde geçiyor.
- W2/A bandı Δη ≥ 0.005'te sağlanıyor (210.2).

## Açık konular
- W2/A 216.8 > 215 ve itki tavanına yakınlık: fan çapı/göbek oranı [T] ya da küçük bir Δη.
- V18/V8 0.86, Girão idealinden (0.627) yüksek; çekirdek jeti yavaş.
- He 2025 ve Bennett vd. künyeleri eksik (Bennett aramada bulunamadı).
- Indriyati HPC havası 39.57 vs model çekirdek havası (tanım farkı).

## Sıradaki adımlar
1. W2/A kararı (fan geometrisi veya Δη), gerekirse rev005.
2. M0 kapsamını tamamla: istasyon tablosu -> modül bütçeleri, arayüz sözleşmesi.
3. Arayüz (Streamlit).
4. M1 Inlet & Fan: ders + araştırma.

## Çalışma kuralları
- Görev sonu raporu: Commit / Done / Decisions for user / Tests (max 15 satır).
- Kaynak bulunamazsa uydurma; "doğrulanamadı" yaz.
