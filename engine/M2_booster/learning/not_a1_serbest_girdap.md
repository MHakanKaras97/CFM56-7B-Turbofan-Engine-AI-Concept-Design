# Not: A-1 neden kaldı (serbest girdap ve uç bölgeler)

Kısa not, M2 adım 2. Sayılar `analysis/a1_validation.yaml` dosyasından gelir; burada tekrar yazılmaz.

- A-1, booster ile aynı kod yolunu (`analysis/stage_aero.py`) TP-1523 rotor 23B üzerinde çalıştırır: tasarım modu,
  PR ve PR/TR çiftinden verim, serbest girdap (r Vt sabit), açıklık boyunca tek eksenel hız.
- Orta kesitte D ve çıkış açısı tutuyor; uç ve göbekte D tabloya göre düşük çıkıyor.
- Sebep yöntemde: rig tasarımı serbest girdap değil. Tablo 2(b)'de toplam sıcaklık oranı uçta ve göbekte ortadan
  yüksek (uç bölgelere ek iş verilmiş) ve çıkış meridyen hızı uçlarda düşük (uç duvar blokajı). Meanline bu iki
  etkiyi görmez, bu yüzden uç bölge D'sini olduğundan düşük tahmin eder.
- D formülü doğru: aynı kod Tablo 2(b) üçgenleriyle D-FACT değerini 0.002 içinde verir.
- Sonuç: booster D değerleri uçta ve göbekte iyimser (güvensiz tarafta). Kural sınırına yakın geçen bir kesit
  gerçekte sınırı aşabilir. Düzeltme ayar değil, yöntem değişikliği olur (ör. uç bölge iş dağılımı ve blokaj
  modeli); bu kullanıcı kararıdır.
- PR kriteri tasarım modunda kendiliğinden sağlanır (iş PR ve verimden gelir); fiziği değil kod zincirini sınar.
