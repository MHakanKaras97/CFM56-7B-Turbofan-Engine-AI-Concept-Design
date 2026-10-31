# Not: geometri adımı 4 (montaj, istasyon 25, BOM)

Kurallar: `rules/geometry.md` R-G2.22-27. Kod: `geometry/flowpath.py` (`station_25`), `geometry/assembly.py`,
`geometry/bom_update.py`.

## İstasyon 25 neden M1 kodundan okunuyor
- Geçiş kanalı 24 -> 25'in akış işlevi M2'nin, donanımı ise M1 çerçevesinin çekirdek bölgesi (göbek halkası M1.4.1,
  çekirdek dikmeleri M1.4.5, duvar halkası M1.4.6; CR-002/CR-003). Kanadın bittiği düzlem (x24) M2 yerleşiminden,
  bölgenin uzunluğu M1 kuralından gelir. Bu yüzden x25 elle yazılmaz, M1 `fan_frame.build` düzeninden (`xc1`) okunur.
- Kanal duvarları ist. 24 yarıçaplarında olduğundan ist. 25 anülüsü ist. 24 anülüsüne eşit; kanal kaybı yalnızca ICD
  kalemi duct_25_24 ile temsil ediliyor.

## Döngüsel bağımlılık ve kayıt kontrolü
- M1 çerçevesi M2'nin x24 ve yarıçaplarını `layout.record` üzerinden okur; `layout.record` ise `flowpath.yaml`'ı
  kontrol eder. x25 dosyaya eklenince dosyanın sha256'sı rev001 manifestosuyla tutmaz. Çözüm (R-G2.26): sha256 tutmazsa
  yarıçaplar kayıt yarıçaplarıyla kayıt hassasiyetinde (son hanenin yarısı) karşılaştırılır; x yarıçapları değiştirmez.
- `calc.regenerate` dosyayı iki geçişte yazar: önce yarıçaplar (eski x korunur), sonra M1 kodundan x. Böylece eski
  (bayat) bir dosyadan da aynı baytlar üretilir; geri alma (revert) buna dayanır.

## Ortak hacim: örnek almadan tüm örnekler
- Tekrarlanan parçalar tek şekil + açı listesi. Kesin sonuç için simetri kullanılır: x aralıkları ayrıksa 0; bir taraf
  eksenel simetrikse tek boole işlemi yeter; yuvalı tambur için önce yuvasız (dönel) üst küme, olmazsa bir jant
  üzerinde 360/N simetrisi; iki dönel olmayan sıra için bir sıranın dönel zarfı, olmazsa sınır kutuları kesişen tüm
  örnek çiftleri. Üst küme ile ortak hacim 0 ise alt küme ile de 0'dır.

## Kütle
- Toplam yalnızca bilgi; Lolis kontrol değeri (yaklaşık 171 kg, zayıf ikincil kaynak) bir hedef değil. Stator, kasa ve
  örtüler için Ti-6Al-4V yoğunluğu yer tutucu (#71).
