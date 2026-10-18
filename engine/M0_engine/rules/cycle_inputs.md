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

| Büyüklük | Değer | Not |
|---|---|---|
| FPR | 1.765 | Girdi (ADR-008) |
| P25/P2 (toplam) | 2.64 | P25/P24 = 0.98 dahil |
| Politropik verim: fan / çekirdek tarafı / HPC / HPT / LPT | 0.887 / 0.89 / 0.879 / 0.862 / 0.903 | |
| Yanma verimi / P4/P3 | 0.9995 / 0.95 | |
| P2/P1, P45/P44, P16/P13, P6/P5 | 0.99, 0.98, 0.975, 0.99 | |
| Mekanik verim | 0.99 | |
| İkincil hava (W25 oranı) | NGV 0.05, HPT rotor 0.06, kaçak 0.02; toplam 0.13 | NGV rotordan önce, diğerleri 45'te karışır |
| EGT formülü | EGT = 0.976·(T45 − 0.217·(T45 − T5)) | Şekil 4.10'da 0.976, metinde 0.9664 |

Girão'dan alınmayan varsayımlar: lüle cv 0.98 [G], LHV 43.0 MJ/kg [G], HP güç çekişi 100 kW [T].

## Doğrulama noktası (yalnızca test, revizyon değil) [KS]

Girdiler: itki 125.73 kN, yakıt 1.4023 kg/s, BPR 4.80, OPR (P3/P2) 29.88. Referanslar: W2 358.28 kg/s, T3 838.0 K, P3 2997 kPa, T4 1690.5 K, T41 1649.0 K, T45 1220.9 K, T5 902.1 K, P5 171.1 kPa, EGT 1124.0 K. Geçme ölçütü: sıcaklıklar ±%2, W2 ve basınçlar ±%3. Veriler `girao_2023.yaml` dosyasında.

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

- **ICAO nominal noktası ile Girão verimleri (açık):** Girão noktasındaki SFC 11.15 g/(kN·s), ICAO/TCDS SFC'si ise 10.57 (−%5.2). Girão girdileriyle ve 1.284 kg/s yakıtla ulaşılabilecek en yüksek itki 118.0 kN; 121.43 kN'ye ulaşılamıyor (rev004 oluşturulmadı).

## Yöntem

- Tasarım noktası: maksimum (kalkış) itki.
- Bilinmeyen parametreler (verimler, T4, toplam ve çekirdek hava debisi) itki, yakıt debisi ve EGT değerlerine kalibre edilir.
- Yaklaşım Kurzke'nin kalibrasyon yöntemidir; Martins 2015 üzerinden aktarılmıştır.
