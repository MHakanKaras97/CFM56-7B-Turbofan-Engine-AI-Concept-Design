# Not: A-1 neden kaldı (serbest girdap ve uç bölgeler) ve adım 3'te ne değişti

Kısa not, M2 adım 2-3. Sayılar `analysis/a1_validation.yaml` ve `analysis/meanline_results.yaml` dosyalarından gelir;
burada tekrar yazılmaz.

## Adım 2 (serbest girdap)
- A-1, booster ile aynı kod yolunu (`analysis/stage_aero.py`) TP-1523 rotor 23B üzerinde çalıştırdı: tasarım modu,
  PR ve PR/TR çiftinden verim, serbest girdap (r Vt sabit), açıklık boyunca tek eksenel hız.
- Orta kesitte D ve çıkış açısı tuttu; uç ve göbekte D tabloya göre düşük çıktı.
- Sebep yöntemde: rig tasarımı serbest girdap değil. Tablo 2(b)'de toplam sıcaklık oranı uçta ve göbekte ortadan
  yüksek (uç bölgelere ek iş verilmiş) ve çıkış meridyen hızı uçlarda düşük. Rapor da rotorların çıkışta düzgün
  basınç dağılımı verecek şekilde tasarlandığını söyler (s. 3).

## Adım 3 (açıklık dağılımı tanımı)
- Tanım `rules/aero_method.md` "Spanwise distribution": ortalama kesit 1-B değerleri taşır (kademe işi, süreklilikten
  eksenel hız); göbek ve uç, sabit oranlarla (iş oranı g, eksenel hız oranı f) türetilir. Serbest girdap g = f = 1
  özel hâlidir.
- Blokaj: TP-1523 tasarımda sınır tabaka blokaj katsayısı kullanıldığını söyler (s. 2) ama değer vermez
  (doğrulanamadı). M2 blokaj kullanmaz.
- A-1 artık rigin kendi tablo değerleriyle (yarıçap, devir, giriş/çıkış meridyen hızı, kesit TR, veter, kanat sayısı)
  çalışır ve geçer. Bu, kesit üçgeni + katılık + D kodunun doğru olduğunu gösterir; booster'ın kendi dağılımını
  doğrulamaz.
- Booster için seçim [T]: rigin uç/göbek oranları (rotor 23B iş ve çıkış hızı, stator 20 çıkış hızı) booster'a
  aktarılır. Kaynak CFM56 değil; orantı kuralıdır. Sonuç: rotor uç ve göbek D'leri serbest girdaba göre belirgin
  yükseldi, stator sayıları arttı. Süreklilik yalnız ortalama kesitte kapanır; üç noktalı (Simpson) kütle ve iş
  sapması kodda raporlanır.
- Ders: uç bölge iş dağılımı, rotor uç D sınırını (0.45) serbest girdaptan çok daha erken zorlar. Kural sınırları,
  anülüs kuralı, iş bölüşümü ve AR bu adımda değişmedi (#64 kolları sonraki adım).
