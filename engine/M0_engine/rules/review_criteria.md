# M0 Sonuç İnceleme Kriterleri

## Temel ilke
Kalibrasyon hedeflerinin tutması tek başına sonucu doğrulamaz. Eksik bir model, hedefleri yanlış parametrelerle de tutturabilir. v1 bunu gösterdi: itki ve yakıt tuttu, fakat W2 %26 büyük çıktı. Bir sonuç ancak aşağıdaki iki koşul birlikte sağlanırsa kabul edilir:
1. Tüm sert kurallar geçer.
2. Sağlık kontrollerindeki sapmalar açıklanmış ve kayda geçirilmiştir.

## Sert kurallar (HARD): biri bile kalırsa sonuç reddedilir, revizyon oluşturulmaz
- **Fan boğulma sınırı:** W2/A, SLS ISA toplam koşullarında (P0, T0, soğuk gaz) hesaplanan M = 1 kütle akı yoğunluğundan küçük olmalı. Sınır kodda hesaplanır (`choke_mass_flux`, yaklaşık 241 kg/(s·m²)). A, göbek/uç oranı düşülmüş fan halka alanıdır.
- **Yakınsama:** Kalibrasyon tüm hedefleri toleransta tutturmalıdır. Yakınsamayan çözüm "infeasible" olarak raporlanır ve zorlanmaz.

## Sağlık kontrolleri: kalırsa raporlanır, karar kullanıcıya bırakılır
- W2/A 190-215 kg/(s·m²) [G]
- W2, tahmin edilen 354.7 kg/s'nin ±%10 içinde [T]
- Toplam ikincil hava, W25'in 0.12-0.22'si [G] (v4: Girão girdisi 0.13; kontrol girdinin aralıkta olduğunu doğrular)
- SFC, ICAO/TCDS değerinin ±%0.5 içinde
- EGT (gösterilen), TCDS sınırı 950 °C'nin altında [K]

## Yalnızca bilgi
- Model EGT'sinin Girão'nun yaklaşık 851 °C değeriyle karşılaştırılması (125.7 kN'de) [KS]
- V18/V8; Girão kalkış ideali 0.627 ve η_fan · η_LPT ile birlikte (ADR-008)
- T4'ün 1450 K ve 1553 K referanslarına göre konumu
- T3'ün test hücresi değeriyle karşılaştırılması (ISA olmayan koşul)
- Yanma odası havasının (W31) Lopez-Pintor 44.52 ve Girão 53.71 kg/s değerlerine göre sapması

## Doğrulama (v4)
- Model, Girão tasarım noktasında (125.73 kN, 1.4023 kg/s, BPR 4.80, OPR 29.88) çözülür ve referanslarla karşılaştırılır: sıcaklıklar ±%2, W2 ve basınçlar ±%3.
- Bu bir testtir (`tests/test_cycle.py`), revizyon oluşturmaz. `python -m engine.M0_engine.analysis.cycle --validate` sapmaları yazdırır.

## Uygulama
- Kontroller `engine/M0_engine/analysis/cycle.py` içinde hesaplanır ve `results.yaml` dosyasına yazılır.
- `hard_checks_passed: false` ise ya da `status: infeasible` ise revizyon oluşturulmaz.
