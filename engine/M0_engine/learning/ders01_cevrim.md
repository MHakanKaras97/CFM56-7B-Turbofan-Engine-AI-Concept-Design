# Ders 01: Turbofan Çevrimi (M0 cycle v1)

## 1. İstasyonlar (SAE AS755)
| No | Yer |
|---|---|
| 0 | Serbest akış (ortam) |
| 2 | Fan girişi |
| 13 | Fan bypass çıkışı |
| 18 | Bypass lülesi |
| 25 | HPC girişi (booster çıkışı) |
| 3 | HPC çıkışı |
| 4 | HPT girişi (yanma odası çıkışı) |
| 45 | LPT girişi (HPT çıkışı) |
| 5 | LPT çıkışı |
| 8 | Çekirdek lülesi |

Hava fan girişinde ikiye ayrılır: BPR = bypass debisi / çekirdek debisi. Bizde BPR = 5.0 (ICAO).

## 2. Basınç oranı (π) ve verim (η)
- π: çıkış toplam basıncı / giriş toplam basıncı. OPR = P3 / P2.
- Kompresörde sıcaklık artışı: T_çıkış / T_giriş = π^((γ-1)/(γ·e)).
- e politropik verimdir: küçük kademelerin verimi. Basınç oranından bağımsız kabul edilir; bu yüzden farklı π'deki makineleri karşılaştırmak için uygundur.
- İzantropik verim (η_is) basınç oranına bağlıdır. Kompresörde π büyüdükçe η_is düşer; türbinde ise yükselir.
- Türbinde ilişki tersine döner: T_çıkış / T_giriş = (P_çıkış / P_giriş)^((γ-1)·e/γ).
- Soğuk bölge (hava): cp = 1005, γ = 1.40. Sıcak bölge (yanma ürünleri): cp = 1150, γ = 1.33.

## 3. Yanma odası
- Enerji dengesi: hava entalpisi + yakıt ısısı = ürünlerin entalpisi.
- Buradan yakıt-hava oranı f bulunur. T4 yükseldikçe f artar.
- Basınç kaybı %4: P4 = 0.96 · P3.

## 4. Şaft dengesi
İki şaft vardır ve her biri kendi içinde dengededir:
- Yüksek basınç şaftı: HPT işi = HPC işi / η_mek
- Alçak basınç şaftı: LPT işi = (fan işi + booster işi) / η_mek

Türbin önce gereken işi verir, sonra kalan enerji lüleye gider. Yani lüle hızı şaft dengesinin sonucudur.

## 5. Lüle ve itki
- Yakınsak lüle: basınç oranı kritik değeri (havada yaklaşık 1.89) aşarsa lüle boğulur. Çıkışta ses hızı olur ve fazla basınç, basınç itkisi verir.
- İtki = Σ (debi · hız) + Σ alan · (p_çıkış − p0). Yer seviyesinde, durağan halde ram sürüklemesi yoktur.
- SFC = yakıt debisi / itki.

## 6. Kalibrasyon mantığı
Üç bilinmeyen: W2 (toplam hava), T4, FPR (fan basınç oranı).
Üç hedef:
1. İtki = 121.43 kN (TCDS)
2. Yakıt debisi = 1.284 kg/s (ICAO)
3. V18 / V8 = η_fan,is · η_LPT,is

Üçüncü hedefin anlamı: bu oran sağlandığında, verilen enerjiyle elde edilen itki en büyüktür. Bu, ayrık akışlı turbofanlar için klasik optimum lüle hızı oranıdır.

Çözüm Newton yöntemiyle yapılır. Her adımda bilinmeyenler biraz oynatılarak türevler (Jacobian) sayısal olarak hesaplanır ve 3x3 lineer sistem çözülür. Birkaç iterasyonda yakınsar.

## 7. Sağlık kontrolleri neden önemli
Kalibrasyon hedefleri tutturur; fakat model eksikse bunu hatalı parametrelerle telafi eder.
v1'de soğutma havası, müşteri hava alımı ve güç çekişi yok. Bu nedenle motor "fazla iyi" çıkıyor:
- T4 düşük çıkıyor,
- aynı yakıtı yakmak için çekirdek debisi ve dolayısıyla W2 büyüyor.

W2/A ve W2 kontrolleri bu sapmayı gösterir. Bir sonraki adım (v2): soğutma havası ve kayıpları eklemek.
