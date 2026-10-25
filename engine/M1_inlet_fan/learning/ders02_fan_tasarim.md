# Ders 02: İlk fan tasarımı (M1 adım 3)

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
