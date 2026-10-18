# M0 kabul listesi (M0 v1)

Liste `docs/architecture.md` bölüm 10'dan alındı. Testler: `python -m pytest tests/acceptance` (`tests/acceptance/test_M0.py`). Tarih: 2026-10-18; sonuç: 5/5 geçti.

| Madde | Durum | Kanıt |
|---|---|---|
| Kural kontrolleri | [x] | `test_rule_checks_run_and_pass`: rev005 parametreleriyle bütün kontroller çalışır, HARD ve sağlık kontrolleri geçer, `results.yaml` kaynağından yeniden üretilebilir. |
| Hesap doğrulama | [x] | `test_girao_validation_accepted`: Girão noktasında 19 kalemden yalnızca P5 kalır (kabul edilen beklenen hata, `validation_girao.md`). |
| Parametre değişikliği testi | [x] | `test_parameter_change_propagates_without_writing`: P16/P13 0.975 → 0.970 yapılınca hedefler yeniden tutar, W2 değişir, HARD geçer, hiçbir dosya yazılmaz. |
| Geri dönüş testi | [x] | `test_revert_and_rerun_reproduces_record`: geçici kopyada ACTIVE rev004 → rev005; rev005 yeniden hesaplanınca `results.yaml` sha256 kayıttakiyle aynı. |
| Çakışma testi | [x] | `test_conflict_reject_then_approve`: bütçe CR'si açılır. (b) seçilip reddedilince hiçbir dosya değişmez. (a) seçilip onaylanınca rev006 oluşur; params, `results.yaml` ve `icd.yaml` yeniden üretilir. |
| M0 kontrolü | [x] | M0 kendi entegrasyon kontrolünü (`analysis/integration.py`) çalıştırır; M1-M9 henüz başlamadı (concept001'de null). |

## Makullük: verim kaybının EGT'ye etkisi (itki sabit)
Model: rev005, itki 121.43 kN ve W2 sabit, verim 0.01 düşürülür [H]. Martins 2015 değerleri CFM56-3 içindir; yalnızca büyüklük karşılaştırması yapılır [KS].

| Bileşen | ΔEGT model [K] | ΔEGT Martins [K] | ΔSFC model | ΔT41 model [K] |
|---|---|---|---|---|
| Fan (dış) | +3.1 | +4 | +%0.52 | +3.7 |
| Booster | +1.9 | +3 | +%0.19 | +2.8 |
| HPC | +4.3 | +8 | +%0.61 | +8.4 |
| HPT | +5.3 | +12 | +%0.73 | +5.3 |
| LPT | +5.5 | +6 | +%0.76 | +5.5 |

İşaretler ve büyüklük mertebesi tutuyor. HPC ve HPT etkisi ise Martins'in yaklaşık yarısı. Olası nedenler: bizde W2 sabit tutuluyor (Martins'te N1 sabit), EGT formülü T45 ile T5'in ağırlıklı ortalaması [T] ve motorlar farklı (-3 / -7B). Açık konu olarak kaydedildi.
