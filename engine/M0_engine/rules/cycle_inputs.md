# M0 Çevrim Girdileri (CFM56-7B27)

Tasarım noktası hesabına girecek değerler. Kaynak ayrıntıları: `docs/sources.md`.

Veri dosyaları (sayılar koddan gelir):
- `icao_edb_cfm56_7b27.yaml`: ICAO satırlarının tamamı (`tools/extract_edb.py`).
- `tcds_e004.yaml`: TCDS itki değerleri.
- `../analysis/sfc_takeoff.yaml`: hesaplanan SFC (`tools/derive_sfc.py`).

## Değerler

| Büyüklük | Değer | Birim | Etiket | Kaynak |
|---|---|---|---|---|
| Kalkış itkisi (CFM56-7B27, SAC/DAC/TI) | 121.43 | kN | [K] | EASA TCDS E.004 Issue 07 (12143 daN) |
| Maksimum sürekli itki | 115.21 | kN | [K] | EASA TCDS E.004 Issue 07 (11521 daN) |
| ICAO nominal itki | 121.44 | kN | [K] | ICAO EEDB v32, UID 3CM034 |
| **OPR, -7B27 (tasarım değeri)** | 28.63 | - | [K] | ICAO EEDB v32, UID 3CM034 |
| OPR, -7B27/2 | 28.84 | - | [K] | ICAO EEDB v32, UID 4CM043 |
| OPR, -7B27/3 (Tech Insertion) | 29.0 | - | [K] | ICAO EEDB v32, UID 8CM066 |
| ~~OPR~~ | ~~32.8~~ | - | geçersiz | Turan; ICAO değeri ile değiştirildi |
| **BPR, -7B27 (tasarım değeri)** | 5.0 | - | [K] | ICAO EEDB v32, UID 3CM034 (/2 aynı) |
| BPR, -7B27/3 (Tech Insertion) | 5.1 | - | [K] | ICAO EEDB v32, UID 8CM066 |
| Yakıt debisi T/O / C/O / App / Idle, -7B27 | 1.284 / 1.043 / 0.349 / 0.116 | kg/s | [K] | ICAO EEDB v32, UID 3CM034 |
| Yakıt debisi T/O / C/O / App / Idle, -7B27/2 | 1.265 / 1.033 / 0.351 / 0.115 | kg/s | [K] | ICAO EEDB v32, UID 4CM043 |
| Yakıt debisi T/O / C/O / App / Idle, -7B27/3 | 1.293 / 1.031 / 0.343 / 0.110 | kg/s | [K] | ICAO EEDB v32, UID 8CM066 |
| **Kalkış SFC, -7B27 (tasarım değeri)** | 10.574 | g/(kN·s) | [H] | ICAO T/O yakıt / TCDS itki, `sfc_takeoff.yaml` |
| Kalkış SFC, -7B27/2 | 10.418 | g/(kN·s) | [H] | aynı yöntem |
| Kalkış SFC, -7B27/3 | 10.648 | g/(kN·s) | [H] | aynı yöntem |
| SFC (çapraz kontrol) | 10.63 | g/(kN·s) | [KS] | Turan; doğrulanamadı, yalnızca çapraz kontrol |
| Yakıt debisi (kalkış, -7B27/B1F) | 1.28 | kg/s | [KS] | Lopez-Pintor vd. 2026, Tablo 2 |
| Yanma odası hava debisi (kalkış, -7B27/B1F) | 44.52 | kg/s | [KS] | Lopez-Pintor vd. 2026, Tablo 2; v3'ten itibaren yalnızca kontrol (ADR-007) |
| HPC girişi T / p | 385.9 / 216.54 | K / kPa | [KS] | Indriyati 2024, 7B test istasyonları |
| HPC çıkışı T / p | 832.4 / 2683.49 | K / kPa | [KS] | Indriyati 2024 |
| Türbin girişi T / p | 1553 / 2545.35 | K / kPa | [KS] | Indriyati 2024 |
| Türbin çıkışı T / p | 1121.9 / 529.43 | K / kPa | [KS] | Indriyati 2024 |
| Hava debisi | 39.57 | kg/s | [KS] | Indriyati 2024 |
| Yakıt debisi | 1.29 | kg/s | [KS] | Indriyati 2024 |
| Ortam sıcaklığı T0 (ISA değil) | 298 | K | [KS] | Indriyati 2024 |
| Fan basınç oranı (FPR) | 1.55 | - | [KS] | Kalkan 2024; not: CFM56-5A3 |
| OPR | 27.8 | - | [KS] | Kalkan 2024; not: CFM56-5A3 |
| BPR | 6 | - | [KS] | Kalkan 2024; not: CFM56-5A3 |
| ~~Politropik verimler, yanma verimi, soğutma 0.18~~ | - | - | [G] | v4'te Girão değerleriyle değiştirildi (aşağıda) |
| Gaz özellikleri cp(T, FAR) | NASA 7 katsayılı polinomlar | - | [K] | McBride vd. 1993, NASA TM-4513; `tools/data/nasa_glenn.yaml` |
| Yakıt | C12H23, 298.15 K'de girer | - | [G] | Jet-A vekil bileşimi |
| Kuru hava bileşimi | N2 / O2 / Ar / CO2 | mol oranı | [G] | ABD Standart Atmosferi 1976 |
| Toplam hava debisi | 782 | lb/s | [T] | Tahmin; kalibrasyonla çözülecek |
| Türbin giriş sıcaklığı T4 | 1450 | belirsiz | [T] | Tahmin; birim belirsiz (K veya °C) |

## v4 girdileri (Girão 2023, Şekil 4.9-4.10) [KS]

Verimler izentropiktir (GasTurb girdileri, Şekil 4.9); politropiğe çevrilmez (v4.1).

### Bileşen verimi tanımı [H]

Kaynak: kod (`engine/M0_engine/analysis/cycle.py:11`, `run()` satır 189-226; `tools/thermo.py`
`compressor_is` satır 181, `turbine_is_for_work` satır 189). Altı verim de toplamdan toplama
(total-to-total) izentropik verimdir; gaz özellikleri değişken cp(T, FAR) ile (NASA polinomları),
phi(T) = ∫cp/T dT entropi fonksiyonu, R_s gaz sabiti, FAR o istasyonun yakıt-hava oranı.

- Kompresör (eta_fan_outer, eta_fan_inner, eta_booster, eta_hpc), PR = Pt_çıkış/Pt_giriş:
  phi(T_is) = phi(Tt_giriş) + R_s ln(PR);
  eta = [h(T_is) - h(Tt_giriş)] / [h(Tt_çıkış) - h(Tt_giriş)].
- Türbin (eta_hpt, eta_lpt), PR = Pt_giriş/Pt_çıkış > 1, iş w kompresör gücünden verilir:
  h(T_is) = h(Tt_giriş) - w/eta; PR = exp{[phi(Tt_giriş) - phi(T_is)] / R_s};
  yani eta = [h(Tt_giriş) - h(Tt_çıkış)] / [h(Tt_giriş) - h(T_is)].

| Verim | İstasyonlar | Not |
|---|---|---|
| eta_fan_outer | 2 -> 13 | Baypas akışı, PR = FPR |
| eta_fan_inner | 2 -> 21 | Çekirdek akışı, iç fan |
| eta_booster | 21 -> 24 | P25/P24 kanal kaybı verime dahil değil |
| eta_hpc | 25 -> 3 | Kaçak havası HPC işinin leak_bleed_point oranını alır, verim tanımı değişmez |
| eta_hpt | 41 -> 43 | Giriş = NGV soğutması karıştıktan sonra (T41), rotor soğutması 44'te karışır |
| eta_lpt | 45 -> 5 | Giriş = kaçak havası döndükten ve P45/P44 kanalından sonra |

Nominal durumda (ADR-009) ortak Δη bu izentropik verimlere eklenir. Modüller politropik verime
ihtiyaç duyarsa dönüşümü `tools.thermo.compressor_isentropic_eff` / `turbine_isentropic_eff`
ile aynı gaz modeliyle kendileri yapar (ör. M2 kademe politropik verimi); M0 girdisi izentropik kalır.

| Büyüklük | Değer | Not |
|---|---|---|
| Dış fan PR (FPR) / izentropik verim | 1.765 / 0.878 | Girdi (ADR-008) |
| İç fan PR / izentropik verim | 1.344 / 0.870 | P21/P2 |
| Booster PR / izentropik verim | 2.004 / 0.890 | P24/P21 |
| P25/P24 | 0.98 | P25/P2 = 1.344 · 2.004 · 0.98 = 2.64 |
| HPC / HPT / LPT izentropik verim | 0.8363 / 0.880 / 0.9173 | |
| Yanma verimi / P4/P3 | 0.9995 / 0.95 | |
| P2/P1, P45/P44, P16/P13, P6/P5 | 0.99, 0.98, 0.975, 0.99 | |
| Mekanik verim | 0.99 | |
| Lüle itki katsayısı: by-pass / çekirdek | 1.00998 / 1.0 | Çekirdek değeri tezde yok, GasTurb varsayılanı [T] |
| Lüle debi katsayısı CD18 / CD8 | 0.99756 / 0.99492 | Yalnızca alanı etkiler |
| HP güç çekişi | 0 kW | |
| İkincil hava (W25 oranı) | NGV 0.05, HPT rotor 0.06, kaçak 0.02; toplam 0.13 | NGV rotordan önce, rotor soğutması 44'te, kaçak 45'te karışır |
| EGT formülü | EGT = 0.976·(T45 − 0.217·(T45 − T5)) | Şekil 4.10'da 0.976, metinde 0.9664 |

Kaçak havası HPC çıkışından önce ayrılır (Girão W3 60.499 < W25 61.733). Model bunu HPC entalpi artışının %50'sinde ayrılan bir ara kademe çekişi olarak ele alır [T].

Girão'dan alınmayan varsayımlar: LHV 43.124 MJ/kg [T] (GasTurb genel yakıtı varsayıldı, tezde yok); kaçak çekiş noktası 0.5 [T].

## Doğrulama noktası (yalnızca test, revizyon değil) [KS]

Girdiler: itki 125.73 kN, yakıt 1.4023 kg/s, BPR 4.80, OPR (P3/P2) 29.88. Referanslar (gaz yolu sırasıyla): W2 358.28 kg/s; T13 345.73 K, P13 177.088 kPa; T21 317.23 K; T25 395.08 K, P25 264.816 kPa; T3 838.0 K, P3 2997 kPa; W3 60.499, W31 53.708 kg/s; T4 1690.5 K; T41 1649.0 K; T43 1254.55 K; P44 705.1 kPa, T44 1231.30 K; T45 1220.9 K; T5 902.1 K, P5 171.1 kPa; EGT 1124.0 K. Doğrulama, sapması %1'i aşan ilk kalemi de raporlar. Geçme ölçütü: sıcaklıklar ±%2, W2 ve basınçlar ±%3. Veriler `girao_2023.yaml` dosyasında.

## Nominal nokta (ICAO -7B27, rev005, ADR-009)

- Hedefler: itki 121.43 kN, yakıt 1.284 kg/s; BPR 5.0, OPR 28.63 [K]. Girão FPR'si 1.765 ve çekirdek bölüşümü (1.344, 2.004, P25/P24 0.98) korunur; HPC PR = OPR / 2.64.
- Benzerlik koşulu: üçüncü hedef ideal V18/V8 = 0.6036 [T]. Bu, modelin Girão noktasında hesapladığı değer (Girão 0.627).
- Üçüncü bilinmeyen: bütün izentropik turbomakine verimlerine eklenen ortak Δη. Çözüm yoksa ya da Δη > 0.03 ise yedek yol: Δη = 0 ve FPR serbest.
- Sonuç: Δη = 0.0171 [H], FPR 1.765. İtki tavanı 130.91 kN (+%7.8 pay).
- Δη taraması (0-0.03, yalnızca itki ve yakıt) bilgi tablosu olarak `results.yaml` içinde; V18/V8 sütunu dahil.
- rev004 (Δη = 0, iki hedef) yerini bu sonuca bıraktı: itki tavanına %1.2 yakın, ideal V18/V8'i yüksek (0.849) bir çözümdü.

## Belirsizlik bandı (yalnızca bilgi, revizyon yok) [H]

Δη farklı verim gruplarına uygulandı; her durumda aynı üç hedef çözüldü (itki, yakıt, ideal V18/V8 = 0.6036). Komut: `python -m engine.M0_engine.analysis.cycle --band`.

| Δη uygulanan | Δη | W2 [kg/s] | T4 [K] | T41 [K] | EGT model [°C] |
|---|---|---|---|---|---|
| (a) yalnız kompresörler (fan dış/iç, booster, HPC) | 0.0344 | 345.94 | 1659.4 | 1618.0 | 843.6 |
| (b) yalnız türbinler (HPT, LPT) | 0.0348 | 344.84 | 1682.3 | 1640.9 | 846.3 |
| (c) hepsi eşit (rev005) | 0.0171 | 345.40 | 1670.7 | 1629.2 | 844.9 |
| Yayılım | | 1.1 | 22.9 | 22.9 | 2.7 |

(a) ve (b) durumlarında Δη, 0.03 sınırının üstünde kalıyor.

## Bilgi referansları

- EGT: Girão, 125.7 kN'de yaklaşık 851 °C (formül değeri, şönt hariç). 800-920 °C bandı v4'te kaldırıldı.
- Yanma odası havası: Lopez-Pintor 44.52 kg/s (modellenmiş, ADR-007); Girão W31 53.71 kg/s (125.7 kN'de).
- V18/V8: Girão'nun kalkış için ideal oranı 0.627 (ADR-008).

### M8 (mil ve yatak) için devir referansları [KS]

M0 bu değerleri kullanmaz. M8 kurallarına aktarılması M8'in işi (`girao_2023.yaml`, `spool_speeds`).
- Girão nominal: HP 14465 rpm, LP 5282 rpm.
- Yılmaz, kalkış ortalamaları: N1 5086 rpm, N2 14403 rpm.

## Makullük aralıkları (Kuropatwa 2022)

Yalnızca kontrol içindir; tasarım değeri olarak kullanılmaz.

| Büyüklük | Aralık | Birim |
|---|---|---|
| BPR | 5.0 - 6.8 | - |
| OPR | 21 - 33 | - |
| Kalkış TSFC | 0.32 - 0.39 | lb/(lbf·h) |

Hesaplanan kalkış SFC değerleri bu aralıktadır (`sfc_takeoff.yaml`, `in_sanity_range`).

## Çelişkiler

- **OPR (çözüldü):** Tasarımda ICAO değeri 28.63 kullanılır. Turan'ın 32.8 değeri geçersiz sayıldı. Test istasyonlarından çıkan yaklaşık 26.5 farklı koşullara (T0 = 298 K, test hücresi) ait.
- **SFC (çözüldü):** Tasarım değeri ICAO ve TCDS verisinden kodla hesaplanır. Turan'ın 10.63 değeri doğrulanamadı; hesaplanan -7B27, /2 ve /3 değerleriyle aynı mertebede olduğu için yalnızca çapraz kontrol olarak tutulur.
- **Hava debisi (açık):** HPC havası 39.57 kg/s, yanma odası havası 44.52 kg/s'den küçük. Yanma odasına HPC'den fazla hava giremeyeceği için bu fiziksel olarak imkânsız; iki kaynak debiyi farklı tanımlıyor (çekirdek, soğutma havası, ölçüm noktası). Hangisinin kullanılacağı henüz kararlaştırılmadı.
- **Yanma odası havası tanımı (çözüldü, ADR-007):** 44.52 kg/s modellenmiş bir değer ve büyük olasılıkla liner soğutmasını içeriyor. v3'te hedef değil, bilgi amaçlı kontrol. Soğutma oranı 0.18 girdisiyle model 50.96 kg/s veriyor (+%14.5). Hedef olarak kullanıldığında soğutma 0.35'e çıkıyor (rev003, `comparison_combustor_air_target`).
- **Toplam hava debisi (açık):** 782 lb/s yalnızca başlangıç tahmini; gerçek değer kalibrasyonla çözülecek.
- **İtki:** TCDS 121.43 kN, ICAO 121.44 kN; fark yuvarlamadan kaynaklanıyor.
- **BPR:** ICAO 5.0-5.1 (-7B27), Kalkan 6 (CFM56-5A3); farklı motor ailesi.

## Çelişkiler (v4)

- **ICAO nominal noktası ile Girão verimleri (çözüldü, v4.1):** v4 girdileriyle (cv 0.98, LHV 43.0, 100 kW çekiş) en fazla 118.0 kN çıkıyordu. Şekil 4.9 girdileriyle (lüle katsayıları, çekiş 0, LHV 43.124 [T]) Δη = 0'da çözülüyor (rev004).

## Yöntem

- Tasarım noktası: maksimum (kalkış) itki.
- Bilinmeyen parametreler (verimler, T4, toplam ve çekirdek hava debisi) itki, yakıt debisi ve EGT değerlerine kalibre edilir.
- Yaklaşım Kurzke'nin kalibrasyon yöntemidir; Martins 2015 üzerinden aktarılmıştır.
