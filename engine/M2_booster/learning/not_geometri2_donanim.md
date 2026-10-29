# Not: booster rotor tamburu, iç örtüler ve kasa (geometri adım 2)

Kurallar: `rules/geometry.md` R-G2.9-17. Kod: `geometry/hardware.py`. Tüm ölçüler [T] oran (`geometry_params.yaml`
`hw_*`), yapısal aşamaya (A-4) kadar; hiçbiri bir kontrolü geçirmek için ayarlanmadı.

## Neden tambur?
Booster düşük hızlı ve düşük sıcaklıklı bir kompresördür; kademeler kısa açıklıklı ve birbirine yakındır. Bu yüzden
her kademeye ayrı disk yerine, jantları ince bir silindirik/konik duvarla birleşen tek parça bir tambur (spool)
kullanmak yaygındır [G]. Owner's Guide "booster spool"u ömür sınırlı parça (LLP) olarak sayar; yani tek parça kabulü
kaynakla uyumlu, ama iç yapısı (kaynaklı disk mi, tek dövme mi) doğrulanamadı.

## Parçalar
- **Tambur (M2.0.1)**: her rotor sırası için bir jant; jantın dış yüzü göbek akış yolu çizgisidir. Statorların altında
  jantları ince bir duvar bağlar; duvar üstünde iki labirent dişi vardır. Önde ist. 21 düzleminde bir flanş, arkada
  ist. 24 düzleminde serbest uç.
- **Kanat bağlantısı**: her kanada bir düz yuva; yuva göbek kesitinin kademe açısı (stagger) boyunca uzanır, kesiti
  dikdörtgendir (gerçek kırlangıç yerine sade yer tutucu). Kanadın kök bloğu yuvaya bir uyum boşluğuyla oturur.
- **İç örtü (önerilen M2.n.4)**: stator kanatlarının göbek tarafını taşıyan halka; dış yüzü göbek akış yolu, altında
  aşınabilir sızdırmazlık yüzeyi (seal land). Tamburdaki dişler bu yüzeye radyal açıklıkla bakar: kademeler arasında
  statorun altından geri kaçan havayı azaltır.
- **Kasa (M2.0.2)**: iç yüzü uç akış yolu; her stator sırası için çevresel bir oluk; kanat ayakları bu oluğa oturur.
  Rotor uç açıklığı R-G2.6 kuralıyla kasa iç yüzüne ölçülür (aşınabilir astar modellenmedi).

## Dönen / duran ayrımı
Her sıralar arası boşluk ortadan bölünür; ortasına eksenel çalışma boşluğu konur. Böylece dönen jantlar ile duran
örtüler arasında hem eksenel (çalışma boşluğu) hem radyal (diş açıklığı) mesafe kalır ve kontrol bunu ölçer.

## Öğrenilenler (bu adımın bulguları)
- Yuvaların arka ucu bir sonraki statorun duvarıyla kısmen kapanıyor (#75): kademe kademe göbek yükseldiği için duvar
  bir sonraki yuvanın tabanından yukarıda kalıyor. Gerçek motorda bu, bağlantı tipi seçimini (eksenel/çevresel
  kırlangıç) etkileyen bir yerleşim sorunudur.
- Fan diski ile tambur arasında 95 mm eksenel boşluk var (#76); köprünün hangi modülde olacağı bir sahiplik kararı.
- M1 fan çerçevesi booster'ın kademe 2-3'ünün üstüne düşüyor (#77): M1 çerçeveyi M2 akış yolu bilinmeden yer tutucu
  olarak yerleştirmişti (#49). Modüller arası hacim kontrolü bu yüzden önemli.
