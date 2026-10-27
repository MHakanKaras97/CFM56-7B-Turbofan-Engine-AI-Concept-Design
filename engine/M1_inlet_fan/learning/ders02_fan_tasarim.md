# Ders 02: İlk fan tasarımı (M1 adım 3) ve yeniden tasarım (adım 4d, 4e)

> **Adım 4e güncellemesi (tek, düzgün kanat).** Güncel sayılar `analysis/results.yaml` dosyasındadır; aşağısı özet.
> - Kanat göbekten uca tek parça; ayırıcı (splitter) kanadın arkasında. Bu yüzden kord, katılık, metal açıları ve kalınlık açıklık boyunca düzgün fonksiyonlar olmalı. Tüp başına ayrı değer yok: kord açıklığın ikinci derece polinomu (3 katsayı), kappa2 üçüncü derece polinom + ayırıcı geçiş terimi (5 katsayı), kappa1 giriş akış açısından (insidans 3° [T]), t/c ve profil parametreleri Rotor 67 uydurmalarından [T].
> - Profil ailesi (R-AM.11): MCA tipi, yani iki dairesel yaydan kamber çizgisi + parabolik kalınlık. Ön yayın kamber payı 0.5 ve en kalın nokta ortada ise bu DCA profilidir (NASA SP-36, PDF s. 204) [K]. TP-2879 Rotor 67'nin profil ailesini söylemiyor (doğrulanmadı); ama kesitleri göbekte DCA'ya benzer, uca doğru ön kamberi çok azalıyor (süpersonik kesit). Emme yüzeyi açısı bu profilden hesaplanıyor ve şok genişlemesine giriyor; Rotor 67'de geometrinin verdiği değerden süpersonik akım çizgilerinde -0.6 ile +1.1° arasında farklı (düz DCA uçta +4.3° hata verirdi) [H].
> - DF kuralı (yeni R-AM.9): ses altı bölgede (bağıl Mach < 1) SP-36 sınırları: göbek D < 0.6, uç D < 0.4 (PDF s. 286) [K], arası doğrusal [T]. Süpersonik bölgede katılık Rotor 67'den az olamaz [KS]. Dokuz tüpün hepsi geçti. Yükleme katsayısı psi = dh0/U_uç²: bizim fan 0.310, Rotor 67 0.258 [H]; uçumuz daha yüklü, o yüzden Rotor 67 katılık tabanı yalnız bir alt sınır.
> - İş dağılımı (R-AM.12): her akımda serbest girdap (r·Vt2 sabit) [G], ayırıcı çevresinde C² yumuşak geçiş (±0.25 açıklık) [T]. Akım başına kappa2 kayması aynı geçişle uygulanıyor; bu yüzden ayırıcıda kırılma olamaz.
> - Öğrenilen: basit radyal dengede çekirdek ile bypass arasındaki iş farkı göbekteki eksenel hızı düşürüyor; göbek tüpü çok yavaşlayınca kayıp patlıyor ve çözüm "çöken" dala gidiyor. Çözüm: kanat biçimini önce kayıpsız bir "tasarım dengesi" üzerinde (hedef iş + akım verimi) kurmak, sonra sabit kanatla gerçek dengeyi çözmek; çıkış uç yarıçap oranı 0.98'den 0.95'e (Rotor 67: 0.951) indirildi [T].
> - Düzgünlük: kord ikinci farkı adım 4d'de 32.3 iken şimdi 1.6; kappa2 için 3940 iken 854 [H]. kappa2'de ayırıcının hemen üstünde (açıklık 0.36) bir çukur var: bypass işinin küçük yarıçapta yapılması büyük dönüş istiyor.
> - Meanline verimi eksi bütçe verimi: dış -0.052, iç +0.043, toplam -0.044 [H]. Kök gerilmesi 370 MPa, pay 0.98 (kesit alanı uca doğru büyümesin sınırı etkin) [H].

> **Adım 4d güncellemesi (yeniden tasarım).** Bölüm 1-7 adım 3'ü anlatır; güncel sayılar `analysis/results.yaml` dosyasındadır.
> - Model: radyal denge açık (`solve_rotor_re`), tam kayıp modeli (uç duvar + uç boşluğu açık, ses altı akışta şok kaybı yok, çarpanlar 1). Uç boşluğu 3.0 mm [T]: Rotor 67'nin 1.0 mm'si uç yarıçapına göre ölçeklendi; CFM değeri doğrulanmadı. Şok genişleme açısı aracın varsayılanı (doğrusal kamber) [T]; Rotor 67'de M_ss'i fazla tahmin ediyordu (uçta +0.23'e kadar).
> - Verim (ADR-015): bütçeye giden verimler M0 bütçesinin kendisi (dış 0.895, iç 0.887) [T]. Meanline'ın kendi verimi yalnızca bilgi: dış 0.831, iç 0.925 [H, doğrulanmamış model]. T13 ≈ 344.9 K ve T21 ≈ 316.8 K hedef PR ve bütçe veriminden [H].
> - Neden "her tüp aynı PR" kuralı (R-AM.6) bırakıldı? Uç tüpte kayıp çok yüksek (tüp verimi ≈ 0.66), yani entropi yüksek. Basit radyal dengede sabit iş için dVm² = -2 T ds; uçtaki eksenel hız sıfıra gidiyor. Her tüpe aynı PR'yi zorlamak daha da kötü: kayıp arttıkça iş artıyor ve çözüm kaçıyor (deneme: uç tüp çıkış alanının %63'ünü aldı, verim 0.24). Kanat açıları sabit tutulunca ise hız düşünce iş artar ve çözüm kararlı kalır.
> - Uygulanan yol [T, kullanıcı kararı bekliyor]: (1) ilk halkada her akım için sabit iş ile kanat biçimi; (2) kanatlar sabitken radyal denge ve her akıma tek bir kappa2 kayması (Newton), böylece akımın kütle ortalamalı PR'si hedefe eşit (dış 1.765, iç 1.344); dış akımda kayma yalnızca %80 açıklığın altında; (3) R-AM.9 ile katılık geçişi. 5 geçişte yakınsadı; tüpler arasında PR değişiyor (≈ 1.71-1.87 dış, ≈ 1.34-1.35 iç).
> - R-AM.9 (Rotor 67'ye göre yükleme) 9 tüpün 6'sında sağlanamadı: göbekteki iki tüp (3.2 katılıkta bile DF fazla) ve dış akımın üst dört tüpü (%64-95 açıklık). Bu tüplerde katılık Rotor 67 tabanında bırakıldı ve rapor edildi. Neden: kayıp modeli verimi düşük tahmin ettiği için hedef PR'ye ulaşmak daha fazla iş, yani daha fazla yük istiyor (ADR-015'te öngörülen sınırlama).
> - Uç bağıl Mach ≈ 1.44; uç katılığı 1.37 (kord ≈ 0.27 m), Rotor 67 ucu 1.29. Kök gerilmesi ≈ 266 MPa, Ti-6Al-4V payı ≈ 1.76 (akma/1.5).

Bu not, CFM56-7B27 sınıfı fanın ilk akım tüpü (meanline) tasarımının nasıl yapıldığını anlatır. Sayılar `analysis/results.yaml` dosyasından gelir (kod: `analysis/fan_design.py`, girdiler: `analysis/fan_params.yaml`). Buradaki sayılar o dosyanın özetidir; değişirse doğru olan dosyadır.

## 1. Girdiler nereden geliyor?
- Bütçe M0'ın ICD'sinden, yalnızca `read_icd` ile okunur: toplam debi W2 ≈ 345.4 kg/s, çekirdek debisi W21 ≈ 57.6 kg/s, dış fan basınç oranı 1.765, iç fan basınç oranı 1.344 [H/KS]. Bu değerler M1 dosyalarına kopyalanmaz; kod her çalıştığında okur.
- Devir: 5282 rpm (Girão 2023 nominal LP devri, ICD üzerinden) [KS].
- Kanat sayısı 24 [KS]. Fan çapı 61 inç [T]: ikincil bir belgede "yaklaşık 61 inç" geçiyor ama birincil kaynak doğrulanmadı; M0 da aynı değeri [T] etiketiyle kullanıyor.
- Göbek/uç oranı 0.30 [T]. Bu iki değerle hesaplanan halka alanı ICD'deki fan yüzü alanıyla (1.716 m²) aynı çıkıyor; yani M0'ın W2/A kontrolü ile tutarlıyız.

## 2. Ayırıcı (splitter) yarıçapı
`solve_rotor` debiyi giriş alanına göre böler (giriş düzgün kabul edilir). O halde çekirdeğe giden alan payı W21/W2 = 1/6 olmalı. Göbekten başlayarak alanın 1/6'sını kapsayan yarıçap ≈ 0.381 m [H]. Uç yarıçapı 0.775 m, göbek 0.232 m.

## 3. Akım tüpleri
- 9 tüp: çekirdek tarafında 3, bypass tarafında 6. Her akımın içinde tüpler eşit giriş alanlı, düzgün giriş olduğu için bu aynı zamanda eşit debi demek.
- Çıkış halkası bir tahmin [T]: uç yarıçapı girişin 0.98'i, göbek yarıçapı girişin 1.45 katı, çıkış alanının %20'si çekirdeğe. Rotor 67'de bu oranlar 0.951 ve 1.314 [H, Strazisar s. 34].
- Neden göbek yükseliyor? Euler denklemi işi U2·Vt2 olarak verir. Göbekte çevresel hız düşük (≈145 m/s); yarıçap büyümeden 1.344 basınç oranı için Vt2'nin U2'yi geçmesi gerekirdi. Yükselen göbek bu işin bir kısmını merkezkaç etkisiyle sağlar.

## 4. Kanat açıları ve katılık
- Giriş metal açısı: akış açısı eksi 3° tasarım insidansı [T].
- Çıkış metal açısı: her tüpün basınç oranı kendi akım hedefine (dış 1.765, iç 1.344) eşit olana kadar ikiye bölme ile aranır.
- Katılık (solidity = kord / adım): difüzyon faktörü (DF) yerel sınıra eşit olacak en küçük katılık. Sınır Abrisha'dan: göbekte 0.6, uçta 0.3 (PDF s. 38) [KS]; arada doğrusal [T]. Arama aralığı 1.0-3.2 [T].

## 5. Sonuçlar (özet, [H])
- Uç bağıl Mach ≈ 1.44: uç süpersonik, şok kaybı uç tüplerde baskın.
- Dış akım: basınç oranı 1.765, verim ≈ 0.891 (bütçe 0.895, tolerans içinde). İç akım: 1.344, verim ≈ 0.978 (bütçe 0.887; tolerans dışında).
- İç verimin bu kadar yüksek olması gerçekçi değil: araçta uç duvar (endwall), uç boşluğu ve ikincil akış kayıpları yok; göbek bölgesinde bunlar baskındır. Ayrıca yükselen göbek işin çoğunu yaptığından iç tüplerde kanat neredeyse hiç dönüş yapmıyor (kamber 2-14°).
- DF kontrolü uçtaki dört tüpte kaldı: 3.2 katılıkta bile DF ≈ 0.39-0.43, sınır 0.31-0.41. Uçta 0.3 sınırı bu basınç oranında yalnızca katılıkla sağlanamıyor. Bu yüzden uç kordu ≈ 0.63 m çıktı; gerçek bir geniş kordlu fan için çok büyük. Bu, karar bekleyen bir nokta.
- Kord, çekirdek tarafında ≈ 7-9 cm, bypass tarafında 22-63 cm: ayırıcıda sıçrama var. Sebep, her akımın içinde düzgün basınç oranı istenmesi; gerçek fanda basınç oranı yarıçap boyunca sürekli değişir.

## 6. Mekanik hızlı kontrol
- Kök merkezkaç gerilmesi: σ = ρ ω² ∫ (A(r)/A_kök) r dr. Kesit alanı kökten uca doğrusal azalır, uç/kök alan oranı 0.4 [T].
- Ti-6Al-4V yoğunluk 4430 kg/m³, akma 1100 MPa [KS, materials.yaml]. Akma kullanıldı (kök kalıcı şekil değiştirmemeli), güvenlik katsayısı 1.5 [T] → izin 733 MPa.
- Kök gerilmesi ≈ 239 MPa, pay ≈ 2.07; düzgün (incelmeyen) kanat için ≈ 370 MPa, pay ≈ 0.98. Gaz bükmesi, kırlangıç kuyruğu (dovetail) ve yorulma bu hesapta yok.

## 7. Öğrenilenler
- Bütçe kontrolü geçse bile tasarımın kendisi (uç kordu, ayırıcıdaki sıçrama) fiziksel olarak tutarsız olabilir; sayıları tek tek okumak gerekir.
- Çıkış halkası tahmini verimi ≈ 0.01 oynatıyor: tahminler [T] olarak işaretli kalmalı.
- Sıradaki adım: araca uç duvar ve uç boşluğu kaybı, yarıçap boyunca sürekli basınç oranı dağılımı.

## 8. Adım 4g: veter yasası, t/c kaynağı ve kanat kütlesi (2026-10-27)
Sayılar `analysis/results.yaml` dosyasından (koddan) alındı; yaml esastır.
- **t/c ölçütü (Rotor 67, [H, KS'den]):** her Tablo I kesitinde t/c = en büyük TNPC (kamburluk çizgisine dik kalınlık, TP-2879 sembol listesi, PDF s. 22, basılı s. 18 [KS]) / kesit veteri (kenar dairelerinin uç noktaları arası doğru, (m, r θ) düzleminde). Açıklık oranı = hücum kenarı yarıçap oranı (kesit 1 -> 14); bizim açıklık değişkenimizle aynı tanım. Göbek 0.0851, orta (0.5) 0.0552, uç 0.0298. Kübik uydurma kesitlerden en çok 0.0003 sapıyor. Önceki adımlarda da aynı Rotor 67 verisi kullanılıyordu (kesit sırası ile açıklık neredeyse aynı, kesitler hücum kenarında eşit aralıklı), bu yüzden t/c değişikliği kütleyi neredeyse hiç değiştirmedi: t/c bir kaldıraç değil, bir analog [T].
- **Veter yasası (R-AM.14):** ikinci derece taban + C2 kompakt tümsek a (1 - x²)³. Tümsek, R-AM.9 ihtiyacı iki komşusundan en çok yüksek olan tüpte (tüp 4, ayırıcı üstü ilk bypass tüpü) ortalanır; yarı genişlik komşu tüpe en kısa mesafe, yani komşu tüplerin veterine dokunmaz. Aynı ihtiyaçlarla karşılaştırma (`mass_diagnosis.chord_law_variants`): ikinci derece 9.81 kg, kübik 9.44 kg, ikinci derece + tümsek 7.275 kg. Kübik yerel değil: tüp 4'ü karşılamak için orta açıklığı yine şişiriyor.
- **Sonuç:** kanat kütlesi 7.275 kg/kanat (rev006: 9.78), kontrol 4.917 kg [KS zayıf, Mirghani], oran 1.48. Kök gerilmesi 366.3 MPa, izin 733.3, pay 1.002; taper 0.50 (bandın üst ucu, aktif); kappa2 monoton, eğrilik 87.1 <= 339.8 °/açıklık². 9/9 tüp R-AM.9 geçti, bütçe satırları geçti.
- **Kalan fark neden kapanmıyor (açık konu, ayar yapılmadı):**
  1. Tüp 4 ihtiyacı (katılık 3.2 = arama üst sınırı) girdap tasarım hedefindeki işle (54.0 kJ/kg) hesaplanıyor; dengelenmiş kanat bu tüpte 41.6 kJ/kg iş yapıyor ve DF 0.377 (sınır 0.528). Aynı tüp dengelenmiş işte değerlendirilince ihtiyaç tabandaki 1.0'a iniyor (`local_need_at_balanced_work`, tanı). Yani tümsek, kanadın gerçekte yapmadığı bir iş için duruyor. Bu ihtiyaç düşerse 6.71 kg. Kuralın (ihtiyacın hangi durumda hesaplandığı) değişmesi kullanıcı kararıdır.
  2. Son geçişte tüp 4'ün tasarım durumu ihtiyacı arama sınırında karşılanmadı (`need_met` false); rev006'da 3.19 ile sınırın hemen altındaydı. Son R-AM.9 kontrolü (dengelenmiş çözümde) geçiyor.
  3. Kalan 6.71 / 4.92 farkı: t/c Rotor 67 analoğu (veter²-ağırlıklı 0.0551, eşdeğer ortalama kalınlık 10.6 mm) ve veter seviyesi (ortalama 0.286 m, kök katılığı 3.66). CFM56-7B veter ve kalınlığı doğrulanmadı. Kontrol değeri kırlangıç kuyruğu dahil bütün kanat; profil kısmıyla karşılaştırınca fark daha da büyük.
  4. Tümsekteki kesit alanı kökün 2.04 katı (f 0.355). Kurallar sağlanıyor (en büyük gerilme kökte), ama orta açıklıkta ağır bir kesit yapısal olarak alışılmış değil. Monoton alan kısıtı adım 4f'de reddedilmişti.
