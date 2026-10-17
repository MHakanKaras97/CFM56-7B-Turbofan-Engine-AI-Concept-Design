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
| Yanma odası hava debisi (kalkış, -7B27/B1F) | 44.52 | kg/s | [KS] | Lopez-Pintor vd. 2026, Tablo 2 |
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
| Politropik verim: fan | 0.89 | - | [G] | Genel mühendislik varsayımı |
| Politropik verim: kompresörler | 0.90 | - | [G] | Genel mühendislik varsayımı |
| Politropik verim: türbinler | 0.90 | - | [G] | Genel mühendislik varsayımı |
| Yanma verimi | 0.99 | - | [G] | Genel mühendislik varsayımı |
| Yanma odası basınç kaybı | 4 | % | [G] | Genel mühendislik varsayımı |
| Mekanik verim | 0.99 | - | [G] | Genel mühendislik varsayımı |
| Toplam hava debisi | 782 | lb/s | [T] | Tahmin; kalibrasyonla çözülecek |
| Türbin giriş sıcaklığı T4 | 1450 | belirsiz | [T] | Tahmin; birim belirsiz (K veya °C) |

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
- **Toplam hava debisi (açık):** 782 lb/s yalnızca başlangıç tahmini; gerçek değer kalibrasyonla çözülecek.
- **İtki:** TCDS 121.43 kN, ICAO 121.44 kN; fark yuvarlamadan kaynaklanıyor.
- **BPR:** ICAO 5.0-5.1 (-7B27), Kalkan 6 (CFM56-5A3); farklı motor ailesi.

## Yöntem

- Tasarım noktası: maksimum (kalkış) itki.
- Bilinmeyen parametreler (verimler, T4, toplam ve çekirdek hava debisi) itki, yakıt debisi ve EGT değerlerine kalibre edilir.
- Yaklaşım Kurzke'nin kalibrasyon yöntemidir; Martins 2015 üzerinden aktarılmıştır.
