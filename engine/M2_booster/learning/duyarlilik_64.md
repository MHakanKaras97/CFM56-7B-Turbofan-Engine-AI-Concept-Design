# #64 duyarlılık çalışması (rotor D ihlalleri) ve kapanış kontrolü (#68)

Kaynak kod: `engine/M2_booster/analysis/sensitivity_64.py` (yalnızca yazdırır; params/results/bom/geometri
yazmaz). Tüm D değerleri koddan [T] (booster açıklık dağılımı [T] tasarım seçimi olduğu için, `booster_meanline.py`
etiket kuralı); ihlal sayıları ve bütçe satırları koddan [H]. Sınırlar R-AM2.2 [K]: rotor uç D <= 0.45, diğer
kesitler D <= 0.58; uç katılığı 0.9-2.0 [K]. Rotor sayıları 74/78/74 [KS] sabit. Hiçbir değişken bir hedefe doğru
yinelenmedi; her biri yazılı bir kuraldan tek seferde türetildi.

## Değişkenler (her seferinde yalnız biri)

| Kol | Kural | Adım |
|---|---|---|
| Anülüs | ist. 21 -> 24 arası sabit göbek (taban), sabit ortalama yarıçap, sabit uç yarıçapı; sabit yarıçap ist. 21 değerinde; eksenel Mach tüm varyantlarda ist. 21 değeri [T] | 3 kural |
| İş bölüşümü | toplam entalpi artışının kademe payları; aynı politropik verim, bu yüzden toplam PR ve eta_booster değişmez [H] | eşit PR (taban), 40/33/27, 30/33/37 |
| Rotor katılığı | rotor veteri x k, sayılar sabit (eşdeğer rotor AR = 2.0 / k); stator veteri değişmez, stator sayısı R-KV2.1 ile | k = 0.9, 1.1, 1.2 |
| Uç iş oranı | g_uç = 1 + k (g_uç,rig - 1); göbek oranı ve Vx şekilleri aynı | k = 0.5, 0 (taban 1) |
| Kapanış normalizasyonu (#68, bilgi) | her düzlemde Vx şekli Simpson kütle oranına, iş şekli kütle ortalamalı iş oranına bölünür | açık/kapalı |

## Tablo: rotor ve stator D (göbek/orta/uç), kademe 1 | 2 | 3

İhlal kodu: kademe + R/S + g/o/u (ör. 3Ru = kademe 3 rotor uç). nD = R-AM2.2 D ihlali sayısı (18 kontrolden),
nσ = uç katılığı 0.9-2.0 dışı satır sayısı.

| Kol / varyant | Rotor D 1 | Rotor D 2 | Rotor D 3 | Stator D 1 | Stator D 2 | Stator D 3 | z_stator | nD | nσ | İhlaller |
|---|---|---|---|---|---|---|---|---|---|---|
| Taban (sabit göbek, eşit PR, k=1) | 0.5379/0.4684/0.5067 | 0.5397/0.5008/0.5516 | 0.5830/0.5531/0.6235 | 0.5762/0.4554/0.4839 | 0.5780/0.4623/0.4938 | 0.5787/0.4679/0.5023 | 34/43/55 | 4 | 0 | 1Ru 2Ru 3Rg 3Ru |
| Anülüs: sabit ortalama | 0.5235/0.4474/0.4883 | 0.5391/0.4820/0.5316 | 0.6002/0.5411/0.6065 | 0.5751/0.4568/0.4878 | 0.5750/0.4635/0.4997 | 0.5779/0.4721/0.5131 | 34/43/54 | 4 | 0 | 1Ru 2Ru 3Rg 3Ru |
| Anülüs: sabit uç | 0.4981/0.4161/0.4612 | 0.5204/0.4521/0.5019 | 0.5877/0.5144/0.5776 | 0.5741/0.4590/0.4931 | 0.5797/0.4726/0.5151 | 0.5772/0.4759/0.5231 | 34/42/54 | 4 | 0 | 1Ru 2Ru 3Rg 3Ru |
| İş: 40/33/27 | 0.5675/0.5614/0.6197 | 0.5422/0.5019/0.5556 | 0.5124/0.4525/0.5052 | 0.5792/0.4543/0.4716 | 0.5795/0.4655/0.4991 | 0.5748/0.4680/0.5119 | 64/43/33 | 3 | 1 (1S) | 1Ru 2Ru 3Ru |
| İş: 30/33/37 | 0.5307/0.4568/0.4935 | 0.5376/0.4974/0.5470 | 0.5878/0.5649/0.6381 | 0.5750/0.4549/0.4845 | 0.5786/0.4628/0.4945 | 0.5769/0.4656/0.4983 | 32/42/60 | 4 | 0 | 1Ru 2Ru 3Rg 3Ru |
| Rotor veter x 0.9 | 0.5541/0.4827/0.5219 | 0.5597/0.5179/0.5699 | 0.6094/0.5757/0.6479 | taban | taban | taban | 34/43/55 | 4 | 0 | 1Ru 2Ru 3Rg 3Ru |
| Rotor veter x 1.1 | 0.5246/0.4567/0.4943 | 0.5234/0.4869/0.5366 | 0.5615/0.5346/0.6036 | taban | taban | taban | 34/43/55 | 3 | 0 | 1Ru 2Ru 3Ru |
| Rotor veter x 1.2 | 0.5135/0.4469/0.4839 | 0.5098/0.4753/0.5241 | 0.5435/0.5192/0.5869 | taban | taban | taban | 34/43/55 | 3 | 1 (1R 2.054) | 1Ru 2Ru 3Ru |
| Uç iş k = 0.5 | 0.5379/0.4684/0.4864 | 0.5397/0.5008/0.5297 | 0.5830/0.5531/0.6001 | 0.5762/0.4554/0.4583 | 0.5780/0.4623/0.4682 | 0.5787/0.4679/0.4769 | 34/43/55 | 4 | 0 | 1Ru 2Ru 3Rg 3Ru |
| Uç iş k = 0 | 0.5379/0.4684/0.4658 | 0.5397/0.5008/0.5073 | 0.5830/0.5531/0.5757 | 0.5762/0.4554/0.4319 | 0.5780/0.4623/0.4418 | 0.5787/0.4679/0.4505 | 34/43/55 | 4 | 0 | 1Ru 2Ru 3Rg 3Ru |
| Kapanış normalizasyonu (#68) | 0.5145/0.4440/0.4856 | 0.5200/0.4792/0.5306 | 0.5632/0.5299/0.6000 | 0.5743/0.4554/0.4855 | 0.5764/0.4620/0.4951 | 0.5800/0.4700/0.5063 | 31/39/49 | 3 | 0 | 1Ru 2Ru 3Ru |
| En iyi kombinasyon + normalizasyon (sabit uç, eşit PR, veter x 1.1, k = 0) | 0.4676/0.3893/0.3974 | 0.4899/0.4261/0.4328 | 0.5507/0.4822/0.4954 | 0.5753/0.4614/0.4439 | 0.5780/0.4719/0.4610 | 0.5777/0.4769/0.4707 | 32/40/51 | 1 | 0 | 3Ru |

Hücum kenarı göbek/uç oranı [T]: sabit göbek 0.697/0.731/0.763, sabit ortalama 0.697/0.744/0.784, sabit uç
0.697/0.760/0.808 (kademe 3 rig değeri 0.8'in üstüne çıkıyor; #57 için de olumlu).

## Tek kolun etkisi (özet)
- Hiçbir tek kol dört ihlali kapatmıyor; en iyi tek kollar 3 ihlale iniyor (veter x 1.1, 40/33/27, normalizasyon).
- Uç D'yi en çok düşürenler: sabit uç anülüsü (-0.03 ile -0.05) ve uç iş k = 0 (-0.04 ile -0.05). Kademe 3
  rotor uç her tek kolda >= 0.5052 kalıyor (sınır 0.45).
- 40/33/27 yükü kademe 1'e taşıyor (1Ru 0.6197) ve stator 1 sayısı 64'e çıkıp uç katılığı aralık dışına çıkıyor;
  30/33/37 kademe 3'ü kötüleştiriyor. İş bölüşümü ihlali yer değiştiriyor, kapatmıyor.
- Veter x 1.2 kademe 1 rotor uç katılığını 2.054'e çıkarıyor (TP-1523 test aralığı dışı).

## Kombinasyonlar
Kontrol edilen ızgara: anülüs {göbek, ortalama, uç} x iş {eşit PR, 40/33/27, 30/33/37} x rotor veter
{1.0, 0.9, 1.1, 1.2} x uç iş k {1, 0.5, 0} = 108 çalıştırma [H]. Hiçbirinde D ihlali sıfır değil; en az 1 ihlal.
En iyiler: (sabit uç, eşit PR, veter x 1.1 veya 1.2, k = 0) yalnız 3Ru 0.5073/0.4924; (sabit uç, 40/33/27,
veter x 1.1/1.2, k = 0) yalnız 1Ru 0.5118/0.5009 ama stator 3 uç katılığı aralık dışı. Bunlara #68 normalizasyonu
eklenince de 3Ru 0.4954 kalıyor.

**Hüküm [H]:** Yazılı kurallarla türetilen hiçbir tek kol ve kontrol edilen 108 + 1 kombinasyonun hiçbiri,
3 kademe, 74/78/74 rotor ve R-AM2.2 sınırlarıyla bütün ihlalleri kapatmıyor; kalan ihlal her zaman bir rotor ucu
(çoğunlukla kademe 3, D ~0.50). Ara iş bölüşümleri (ör. iki ucu dengeleyen bir pay) denenmedi: bu, bir D hedefine
doğru ayar olurdu (kural dışı). Eksenel Mach (anülüs kuralının ikinci yarısı) ve kademe sayısı kol olarak
denenmedi.

## Kapanış kontrolü (#68)
Oranların tanımı ve nedeni `rules/aero_method.md` "Closure ratios" bölümünde. Kesit profili akış kabul edilirse
[H, check_budget]: W25 56.293 kg/s (-%2.21, tolerans ±%1: geçmiyor), pr_booster 2.0415 (+%1.87, ±%1: geçmiyor),
T25 395.38 K (+2.26 K, ±10 K: geçiyor). Meanline'ın kendi bütçe satırları 1-B değerlerle yapı gereği geçiyor.

## Önerilen değişiklik sırası (uygulanmadı; kullanıcı kararı)
1. #68: kapanış kuralı (profili 1-B akış ve işi taşıyacak şekilde normalize etmek veya blokaj tanımı). Doğruluk
   sorunu, ICD toleransını aşıyor; tüm D'leri değiştirir (3Rg'yi kapatıyor, uçları ~0.02 düşürüyor).
2. Uç iş oranı (uçta serbest girdaba doğru, k = 0): geometri değişmeden en büyük uç D düşüşü; rig oranının
   aktarımı zaten [T].
3. Anülüs: sabit uç yarıçapı (uç D -0.03 ile -0.05; göbek/uç rig'e yaklaşır). İst. 24/25 göbek yarıçapı
   yükselir: M3 ist. 25 arayüzü etkilenir (CR gerekebilir).
4. Rotor veteri x 1.1 (AR 1.82): kesit katılığı aralıkta kalır; x 1.2 kademe 1 uçta aralık dışı.
5. İş bölüşümü: kaynak gelmedikçe eşit PR kalsın (verilen payların ikisi de ihlali kapatmıyor).
Bunlardan sonra kademe 3 rotor ucu (~0.50) kalıyor: kapatmak için kural düzeyinde kullanıcı kararı gerekir
(R-AM2.2 rotor uç 0.45 kriteri bir verim ölçütü, verim ise M0 bütçesinden geliyor; ya da eksenel Mach / kademe
sayısı kuralları), bu çalışmada önerilmiyor, yalnız seçenek olarak listeleniyor.
