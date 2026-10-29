# Ders 02: Booster (alçak basınç kompresörü)

Kendi cümlelerimizle. Etiketler: [K] birincil, [KS] ikincil, [H] hesap, [G] genel bilgi, [T] tahmin. Kaynaklar
`learning/sources/INDEX.md` ve `docs/sources.md` (# numaraları).

## 1. İki milli turbofanda booster ne yapar?
- Fan göbeğinden geçen çekirdek havası (istasyon 21) HPC'ye girmeden önce biraz daha sıkıştırılır; bu işi booster
  yapar. Booster fanla aynı alçak basınç (LP) milinde döner, LPT tarafından çevrilir [G]. CFM56-7B'de fan ve booster
  aynı devirde döner (Girão 2023, #15, PDF s. 46-47) [KS].
- Neden gerekli: HPC tek başına motorun toplam basınç oranının büyük kısmını verir; çekirdeğe giren havanın basıncı
  biraz yükselirse HPC daha küçük ve daha kısa olur, toplam basınç oranı artar [G].
- Bizim modelde booster basınç oranı 2.004 [KS] ve verimi M0 bütçesinden gelir (ADR-015); booster gücü yaklaşık
  4.44 MW [H], LP milinin fan+booster gücünün küçük bir kısmı (ICD).

## 2. Neden üç kademe?
- CFM56-7B'nin booster'ı 3 kademelidir; kardeş motor -5B'de 4 kademe vardır (Girão 2023 PDF s. 36) [KS]. Owner's
  Guide (#48, s. 10) üç kademeli LPC der [KS]; Lolis 2014 (#47, s. 122) küçük üç kademeli booster der [KS].
- Neden az kademe: booster LP milinde, yani fanın yavaş devrinde döner. Göbek yarıçapı küçük olduğu için kanat hızı
  düşüktür ve kademe başına iş sınırlıdır [G]. 2.0 civarı basınç oranı bu hızda birkaç kademe ister; daha fazla
  kademe ağırlık ve boy getirir [G]. Kesin seçim gerekçesi kaynakta yok (doğrulanamadı).
- E3 (#50, #51) farklı bir yol seçmiş: tek "çeyrek kademe" booster, ada altında FOD ayırıcı. Bu yüzden E3 bizim için
  referans değil, yalnızca bağlam.

## 3. Kademe yüklemesi
- Yükleme katsayısı psi = dh0 / U_uç²: kanadın yaptığı işin uç hızının karesine oranı [G]. Booster'da U düşük olduğu
  için aynı iş daha yüksek psi demektir.
- TP-1523'teki referans kademe 23B-20'de rotor kafa artışı katsayısı 0.329, akış katsayısı 0.470 [K] (Tablo 2(a));
  bu sayıları kendi formülümüzle yeniden ürettik [H] (`rules/aero_method.md`).
- Bizim booster girişinde uç hızı 239.8 m/s [H], TP-1523 tasarım uç hızı 243.8 m/s [K]: girişte çok yakın. Sabit
  göbekli bir booster'da uç yarıçapı arkaya doğru küçülür, 3. kademe çıkışında uç hızı yaklaşık 211 m/s'ye iner [T].

## 4. Difüzyon faktörü (DF) sınırları
- DF kanat emme yüzeyindeki yavaşlamanın ölçüsüdür: çok yavaşlama sınır tabakayı ayırır, kayıp hızla artar.
  Lieblein (#46) bunu hız üçgeninden hesaplanan basit bir sayıya indirdi (denklem 13) [K].
- Kaskat verisinde kayıp D ≈ 0.6'ya kadar yavaş artar, sonra keskin yükselir; rotor ucunda ise D ≈ 0.45'in üstünde
  eleman verimi 0.90'ın altına düşer (RM E53D01 özet) [K].
- TP-1523 (#45) 14 orta kademede DF'yi 0.40-0.58, katılığı 0.9-2.0 aralığında denedi. Az kanat (düşük katılık)
  genellikle daha yüksek verim ve daha geniş stall payı verdi; en yüksek rotor verimi 0.944 (DF 0.51, AR 1.2,
  katılık 0.9) [K].
- M2 kuralı R-AM2.2: rotor ucu D <= 0.45, diğer kesitler ve statorlar D <= 0.58 (denenen en yüksek yükleme) [K].

## 5. VBV ve istasyon 25
- VBV (değişken boşaltma vanaları) fan çerçevesindedir ve birincil akıştan ikincil akışa hava atar (Girão 2023 PDF
  s. 36-37) [KS]. Düşük güçte HPC, booster'ın verdiği havayı yutamaz; fazlası boşaltılmazsa booster stall'a girer [G].
- Yüksek devirde VBV kapalıdır (Girão 2023 PDF s. 47) [KS]. Tasarım noktamız kalkış olduğu için M2 VBV açık/kapalı
  durumu modellemez; yalnızca istasyon 25 çıkışını verir (kullanıcı kararı). Akış işlevi M2'nin, donanım (açıklıklar,
  yapı) M1 çerçevesinin (#48).

## 6. FOD, buz ve dolu (CS-E)
- Booster fan göbeğinin hemen arkasındadır; fanın merkezkaç etkisiyle dışarı atamadığı yabancı cisim, buz ve dolu
  çekirdeğe, yani booster'a girer [G].
- EASA CS-E: 540 yabancı madde çarpması ve yutma (PDF s. 104-105), 780(f) buz yutma (s. 147-148), 790 dolu yutma
  (s. 162-163) test koşullarını verir [K] (M1 arşivindeki CS-E Amdt 5, kaynak #39). Konsept seviyesinde yalnızca kural
  olarak kaydediyoruz; analiz yok.

## 7. Tambur (drum) yapısı
- Booster rotoru tek tek disk yerine, kanatları taşıyan bir tambur (spool) olarak yapılır [G]; fan diskine cıvatalı
  bağlanır. Owner's Guide (#49, s. 19-20) fan/LPC modülündeki ömür sınırlı parçaları sayar: fan diski, booster spool,
  fan şaftı; booster spool ömrü 23,600 EFC, -7B27 için 22,900 EFC [KS].
- Fan diski 17,900 EFC ile modülün en kısa ömürlü parçası, ama kanatlar sökülünce modül dağıtılmadan değiştirilebilir
  (#49, s. 19) [KS]: fan diski ile booster tamburu arasındaki ayrılabilir bağlantı bu yüzden önemlidir (M2.0.3).
- Malzeme: kaynak setimizde yok (doğrulanamadı); dönen parçalar için Ti-6Al-4V [T].

## 8. Kontrol değerleri (zayıf)
- Lolis 2014 Tablo 4.3: booster ("IPC") tahmini motor ağırlığının %7.5'i, 2285.5 kg x 0.075 ≈ 171 kg [H, KS zayıf].
  Bu yazarın kendi tahminidir; tambur/stator/kasa içerip içermediği belli değil. Ayar hedefi değildir.
- Lolis'in booster tasarım girdileri (sabit göbek, giriş Mach 0.5, rotor AR 2.0, stator AR 1.2) onun yönteminin
  varsayımlarıdır, CFM56 ölçümü değildir [KS].
