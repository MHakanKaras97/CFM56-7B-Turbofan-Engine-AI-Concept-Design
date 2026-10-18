# M0 çevrim doğrulaması: Girão 2023

Nokta: Girão'nun GasTurb tasarım noktası (125.73 kN, 1.4023 kg/s, BPR 4.80, OPR 29.88) [KS]. Model aynı bileşen girdileriyle W2 ve T4'ü çözer. Ölçüt: sıcaklıklar ±%2, debiler ve basınçlar ±%3. Değerler `python -m engine.M0_engine.analysis.cycle --validate` çıktısından alındı [H].

| İstasyon | Model | Girão | Sapma % | Sonuç |
|---|---|---|---|---|
| W2 [kg/s] | 355.76 | 358.28 | −0.70 | geçti |
| T13 [K] | 345.91 | 345.73 | +0.05 | geçti |
| P13 [kPa] | 177.05 | 177.088 | −0.02 | geçti |
| T21 [K] | 317.33 | 317.23 | +0.03 | geçti |
| T25 [K] | 395.28 | 395.08 | +0.05 | geçti |
| P25 [kPa] | 264.77 | 264.816 | −0.02 | geçti |
| T3 [K] | 840.13 | 838.0 | +0.26 | geçti |
| P3 [kPa] | 2997.3 | 2997.0 | +0.01 | geçti |
| W3 [kg/s] | 60.111 | 60.499 | −0.64 | geçti |
| W31 [kg/s] | 53.364 | 53.708 | −0.64 | geçti |
| T4 [K] | 1708.4 | 1690.5 | +1.06 | geçti |
| T41 [K] | 1666.3 | 1649.0 | +1.05 | geçti |
| T43 [K] | 1270.9 | 1254.55 | +1.30 | geçti |
| P44 [kPa] | 716.74 | 705.1 | +1.65 | geçti |
| T44 [K] | 1246.8 | 1231.3 | +1.26 | geçti |
| T45 [K] | 1235.6 | 1220.9 | +1.20 | geçti |
| T5 [K] | 916.19 | 902.1 | +1.56 | geçti |
| P5 [kPa] | 177.02 | 171.1 | +3.46 | kaldı (beklenen) |
| EGT [K] | 1138.3 | 1124.0 | +1.27 | geçti |

## İlk sapma
Sapması %1'i aşan ilk istasyon T4'tür (yanma odası çıkışı). Ondan önceki tüm istasyonlar %0.7 içindedir. Fark yanma odasında başlıyor ve türbin boyunca taşınıyor.

## Karar (2026-10-18)
- Doğrulama kabul edildi: 19 kalemin 18'i geçti.
- P5 (+%3.46) beklenen hata olarak kalıyor. Gerekçe: sıcak gaz özellik modeli ve yakıt tanımı GasTurb'den farklı. LHV, doğrulamayı geçirmek için ayarlanmadı (43.124 MJ/kg [T]).
- Bilgi: LHV %0.3 düşürülürse (yaklaşık 43.0) P5 +%2.23'e iner. Bu ayar yapılmadı.

## Kabul listesi
Kabul listesinin tamamı ve sonuçları `acceptance_M0.md` dosyasında. Hesap doğrulama maddesinin kanıtı bu belgedir.
