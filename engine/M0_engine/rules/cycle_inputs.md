# M0 Çevrim Girdileri (CFM56-7B27)

Tasarım noktası hesabına girecek değerler. Kaynak ayrıntıları: `docs/sources.md`.
ICAO satırlarının tamamı `icao_edb_cfm56_7b27.yaml` dosyasındadır (`tools/extract_edb.py` ile üretildi).

## Değerler

| Büyüklük | Değer | Birim | Etiket | Kaynak |
|---|---|---|---|---|
| Kalkış itkisi (CFM56-7B27, SAC/DAC/TI) | 121.43 | kN | [K] | EASA TCDS E.004 Issue 07 (12143 daN) |
| Maksimum sürekli itki | 115.21 | kN | [K] | EASA TCDS E.004 Issue 07 (11521 daN) |
| ICAO nominal itki | 121.44 | kN | [K] | ICAO EEDB v32, UID 3CM034 |
| Toplam basınç oranı (OPR), -7B27 | 28.63 | - | [K] | ICAO EEDB v32, UID 3CM034 |
| OPR, -7B27/2 | 28.84 | - | [K] | ICAO EEDB v32, UID 4CM043 |
| OPR, -7B27/3 (Tech Insertion) | 29.0 | - | [K] | ICAO EEDB v32, UID 8CM066 |
| Bypass oranı (BPR), -7B27 ve /2 | 5.0 | - | [K] | ICAO EEDB v32 |
| BPR, -7B27/3 (Tech Insertion) | 5.1 | - | [K] | ICAO EEDB v32 |
| Yakıt debisi T/O / C/O / App / Idle, -7B27 | 1.284 / 1.043 / 0.349 / 0.116 | kg/s | [K] | ICAO EEDB v32, UID 3CM034 |
| Yakıt debisi T/O / C/O / App / Idle, -7B27/2 | 1.265 / 1.033 / 0.351 / 0.115 | kg/s | [K] | ICAO EEDB v32, UID 4CM043 |
| Yakıt debisi T/O / C/O / App / Idle, -7B27/3 | 1.293 / 1.031 / 0.343 / 0.110 | kg/s | [K] | ICAO EEDB v32, UID 8CM066 |
| Yakıt debisi (kalkış, -7B27/B1F) | 1.28 | kg/s | [KS] | Lopez-Pintor vd. 2026 (PMC12969266), Tablo 2 |
| Yanma odası hava debisi (kalkış, -7B27/B1F) | 44.52 | kg/s | [KS] | Lopez-Pintor vd. 2026 (PMC12969266), Tablo 2 |
| Özgül yakıt tüketimi (SFC) | 10.63 | g/(kN·s) | [KS] | Turan 2022, özet (doğrulanamadı, aşağıya bakın) |
| HPC girişi T / p | 385.9 / 216.54 | K / kPa | [KS] | Indriyati 2024, 7B test istasyonları |
| HPC çıkışı T / p | 832.4 / 2683.49 | K / kPa | [KS] | Indriyati 2024 |
| Türbin girişi T / p | 1553 / 2545.35 | K / kPa | [KS] | Indriyati 2024 |
| Türbin çıkışı T / p | 1121.9 / 529.43 | K / kPa | [KS] | Indriyati 2024 |
| Hava debisi | 39.57 | kg/s | [KS] | Indriyati 2024 |
| Yakıt debisi | 1.29 | kg/s | [KS] | Indriyati 2024 |
| Ortam sıcaklığı T0 (ISA değil) | 298 | K | [KS] | Indriyati 2024 |
| Fan basınç oranı (FPR) | 1.55 | - | [KS-5A] | Kalkan 2024 (CFM56-5A3) |
| OPR | 27.8 | - | [KS-5A] | Kalkan 2024 (CFM56-5A3) |
| BPR | 6 | - | [KS-5A] | Kalkan 2024 (CFM56-5A3) |
| Politropik verim: fan | 0.89 | - | [G] | Genel mühendislik varsayımı |
| Politropik verim: kompresörler | 0.90 | - | [G] | Genel mühendislik varsayımı |
| Politropik verim: türbinler | 0.90 | - | [G] | Genel mühendislik varsayımı |
| Yanma verimi | 0.99 | - | [G] | Genel mühendislik varsayımı |
| Yanma odası basınç kaybı | 4 | % | [G] | Genel mühendislik varsayımı |
| Mekanik verim | 0.99 | - | [G] | Genel mühendislik varsayımı |
| Toplam hava debisi | 782 | lb/s | [T] | Tahmin (kaynak belirtilmedi) |
| Türbin giriş sıcaklığı T4 | 1450 | belirsiz | [T] | Tahmin; birim belirsiz (K veya °C) |

Etiket notu: `[KS-5A]` = ikincil kaynak, fakat farklı motor (CFM56-5A3); yalnızca karşılaştırma ve başlangıç tahmini için kullanılır.

## Çelişkiler

- **OPR:** 32.8, ICAO'nun 28.6-29.0 aralığı ve test istasyonlarından çıkan yaklaşık 26.5 birbirini tutmuyor. Olası nedenler: farklı alt model (SAC/TI), ICAO'nun sertifikasyon tanımı, test hücresi koşulları (T0 = 298 K) ve istasyon tanımı farkı.
- **Hava debisi:** HPC havası 39.57 kg/s, yanma odası havası 44.52 kg/s'den küçük. Yanma odasına HPC'den fazla hava giremeyeceği için bu fiziksel olarak imkânsızdır; iki kaynak debiyi farklı tanımlıyor (çekirdek, soğutma havası, ölçüm noktası).
- **İtki:** TCDS 121.43 kN, ICAO 121.44 kN; fark yuvarlamadan kaynaklanıyor.
- **BPR:** ICAO 5.0-5.1 (-7B27), Kalkan 6 (-5A3); farklı motor ailesi.

## Yöntem

- Tasarım noktası: maksimum (kalkış) itki.
- Bilinmeyen parametreler (verimler, T4, debi dağılımı) itki, yakıt debisi ve EGT değerlerine kalibre edilir.
- Yaklaşım Kurzke'nin kalibrasyon yöntemidir; Martins 2015 üzerinden aktarılmıştır.
