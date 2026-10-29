# #64 duyarlılık çalışması (normalize taban, adım 4), kol sırası ve kapanış kontrolü (#68)

**Not (adım 4):** Bu dosyanın önceki tablosu adım 3'ün normalize edilmemiş açıklık kuralıyla (kapanış oranları
kütle 0.973 / iş 1.030) hesaplanmıştı. O sayıların hepsi aşağıdaki normalize taban sayılarıyla değiştirildi; eski
kural yalnız "normalize edilmemiş (bilgi)" satırında kaldı.

Kaynak kod: `engine/M2_booster/analysis/sensitivity_64.py` (yalnızca yazdırır; params/results/bom/geometri
yazmaz; her varyant `booster_meanline.run` + yazılı parametre değişikliği). D değerleri koddan [T] (booster açıklık
dağılımı [T] seçim); ihlal sayıları, ICD satırları koddan [H]. Sınırlar R-AM2.2 [K]: rotor uç D <= 0.45, diğer
kesitler D <= 0.58; uç katılığı 0.9-2.0 [K]. Rotor sayıları 74/78/74 [KS], 3 kademe sabit. Hiçbir varyant bir D
hedefine doğru yinelenmedi.

## Normalizasyon kuralı (#68)
`rules/aero_method.md` "Spanwise normalisation": her profilli düzlemde Vx şekli Simpson kütle oranına, iş şekli
kütle ortalamalı iş oranına bölünür; kesit profili 1-B süreklilik debisini ve kademe işini tam taşır. Blokaj yok.
Sonuç [H]: tüm düzlemlerde oranlar 1 (1e-6 içinde). Kesit profili akış kabul edilse de W25, pr_booster, T25 ICD
toleransında (check_budget: pass). Eski kural: W25 -%2.21, pr_booster +%1.87 (geçmiyor), T25 +2.26 K.
A-1 normalize edilmez (rigin kendi tablo değerleri); sonuç değişmedi: geçiyor.

## Tek kol tablosu (normalize taban: sabit göbek, eşit PR, veter x 1, k = 1)

İhlal kodu: kademe + R/S + g/o/u (ör. 3Ru = kademe 3 rotor uç). nD = D ihlali (18 kontrolden), nσ = uç katılığı
0.9-2.0 dışı. Tüm satırlarda ist. 21 ve 25 Pt, Tt, W ICD ile tutuyor.

| Kol / varyant | Rotor D 1 | Rotor D 2 | Rotor D 3 | Stator D 1 | Stator D 2 | Stator D 3 | z_stator | nD | nσ | İhlaller |
|---|---|---|---|---|---|---|---|---|---|---|
| Taban (normalize) | 0.5145/0.4440/0.4856 | 0.5200/0.4792/0.5306 | 0.5632/0.5299/0.6000 | 0.5743/0.4554/0.4855 | 0.5764/0.4620/0.4951 | 0.5800/0.4700/0.5063 | 31/39/49 | 3 | 0 | 1Ru 2Ru 3Ru |
| Anülüs: sabit ortalama | 0.4990/0.4231/0.4673 | 0.5171/0.4605/0.5110 | 0.5764/0.5175/0.5832 | 0.5739/0.4574/0.4900 | 0.5749/0.4647/0.5024 | 0.5776/0.4725/0.5148 | 31/39/49 | 3 | 0 | 1Ru 2Ru 3Ru |
| Anülüs: sabit uç | 0.4724/0.3919/0.4403 | 0.4969/0.4311/0.4820 | 0.5621/0.4914/0.5550 | 0.5740/0.4605/0.4963 | 0.5755/0.4697/0.5127 | 0.5796/0.4788/0.5274 | 31/39/49 | 2 | 0 | 2Ru 3Ru |
| İş: 40/33/27 | 0.5509/0.5361/0.5958 | 0.5221/0.4801/0.5344 | 0.4898/0.4316/0.4850 | 0.5795/0.4559/0.4757 | 0.5785/0.4658/0.5010 | 0.5793/0.4736/0.5195 | 55/39/30 | 3 | 1 (3S) | 1Ru 2Ru 3Ru |
| İş: 30/33/37 | 0.5069/0.4327/0.4728 | 0.5179/0.4758/0.5262 | 0.5689/0.5416/0.6143 | 0.5754/0.4572/0.4889 | 0.5778/0.4633/0.4968 | 0.5784/0.4680/0.5026 | 29/38/53 | 3 | 0 | 1Ru 2Ru 3Ru |
| Rotor veter x 0.9 | 0.5303/0.4579/0.5003 | 0.5393/0.4957/0.5483 | 0.5886/0.5517/0.6235 | taban | taban | taban | 31/39/49 | 4 | 0 | 1Ru 2Ru 3Rg 3Ru |
| Rotor veter x 1.1 | 0.5016/0.4326/0.4735 | 0.5043/0.4658/0.5161 | 0.5424/0.5121/0.5807 | taban | taban | taban | 31/39/49 | 3 | 0 | 1Ru 2Ru 3Ru |
| Rotor veter x 1.2 | 0.4909/0.4231/0.4634 | 0.4912/0.4546/0.5040 | 0.5251/0.4973/0.5646 | taban | taban | taban | 31/39/49 | 3 | 1 (1R 2.0542) | 1Ru 2Ru 3Ru |
| Uç iş k = 0.5 | 0.5168/0.4475/0.4696 | 0.5221/0.4827/0.5134 | 0.5652/0.5334/0.5814 | 0.5790/0.4599/0.4648 | 0.5753/0.4607/0.4676 | 0.5758/0.4658/0.4755 | 31/40/51 | 3 | 0 | 1Ru 2Ru 3Ru |
| Uç iş k = 0 | 0.5191/0.4511/0.4531 | 0.5241/0.4861/0.4955 | 0.5671/0.5369/0.5618 | 0.5763/0.4569/0.4346 | 0.5799/0.4652/0.4459 | 0.5763/0.4661/0.4493 | 32/40/52 | 3 | 0 | 1Ru 2Ru 3Ru |
| Eksenel Mach x 0.9 | 0.5693/0.4754/0.4858 | 0.5543/0.5041/0.5406 | 0.5953/0.5571/0.6144 | 0.5784/0.4545/0.4785 | 0.5777/0.4592/0.4859 | 0.5779/0.4648/0.4946 | 35/45/58 | 4 | 0 | 1Ru 2Ru 3Rg 3Ru |
| Eksenel Mach x 1.1 | 0.4595/0.4079/0.4768 | 0.4889/0.4546/0.5171 | 0.5339/0.5037/0.5827 | 0.5727/0.4579/0.4932 | 0.5753/0.4642/0.5022 | 0.5776/0.4701/0.5108 | 28/35/44 | 3 | 0 | 1Ru 2Ru 3Ru |
| Normalize edilmemiş (adım 3 kuralı, bilgi) | 0.5379/0.4684/0.5067 | 0.5397/0.5008/0.5516 | 0.5830/0.5531/0.6235 | 0.5762/0.4554/0.4839 | 0.5780/0.4623/0.4938 | 0.5787/0.4679/0.5023 | 34/43/55 | 4 | 0 | 1Ru 2Ru 3Rg 3Ru |

Normalizasyon kendi başına 3Rg'yi kapatıyor ve rotor D'leri 0.02-0.03 düşürüyor (orta kesit akışı 1/0.973 kat
artıyor, uçtaki fazla iş azalıyor).

## Kol sırası (aero_method.md "Design levers", tek geçiş)
Kural (koşudan önce yazıldı): sırayla, her kol tek sabit adım; gerekçesi geçerli VE mevcut tabanın D ihlal sayısını
kesin azaltıyorsa uygulanır.

| Kol | Önce nD | Sonra nD | Uygulandı | Neden |
|---|---|---|---|---|
| L1 uç iş k = 0 | 3 | 3 | hayır | uçlar düşüyor (1Ru 0.4531) ama sayı azalmıyor |
| L2 sabit uç yarıçapı | 3 | 2 | evet | 1Ru 0.4403'e iniyor; ist. 24 göbek 0.30213 -> 0.36624 m |
| L3 rotor veter x 1.1 | 2 | 2 | hayır | 2Ru 0.4682, 3Ru 0.5357; sayı azalmıyor |
| L4 eşit PR | 2 | 2 | değişiklik yok | kaynak yok, eşit PR kalıyor |

Son taban: sabit uç, eşit PR, veter x 1, k = 1, normalize. Kalan ihlaller 2Ru 0.4820, 3Ru 0.5550.
Bilgi (uygulanmadı): L2 üstüne L1 (k = 0) 3Ru tek ihlale iniyor (0.5130; ızgara satırı); tek geçiş kuralı koşudan
önce sabitlendiği için ikinci geçiş kullanıcı kararı.

## Eksenel Mach duyarlılığı (son tabanda, bilgi)
Eksenel Mach ist. 21 sonrası düzlemlerde ist. 21 değerinin x 0.9 / x 1.1 katı; ist. 21 ve 25 Pt, Tt, W ICD ile
tutuyor (fark <= 0.0004).
- x 0.9: rotor D artıyor (1Rg 0.4724 -> 0.5533, 3Rg 0.5858 sınır üstü), nD 4 (1Ru 2Ru 3Rg 3Ru); stator D az
  değişiyor (göbek -0.002 ile +0.004, uç -0.010 ile -0.013), stator sayısı 35/44/55. İst. 24 göbek 0.35940 m.
- x 1.1: rotor D düşüyor (1Rg 0.3955, 3Ru 0.5467), nD 2 (2Ru 3Ru); stator uç D artıyor (0.5119/0.5198/0.5279; +0.016/+0.007/+0.001),
  stator sayısı 28/36/46 ve üç statorun uç katılığı 0.9 altına iniyor (0.8393/0.8664/0.8944; TP-1523 aralığı dışı).
  İst. 24 göbek 0.37161 m.
- Hüküm: Mach seviyesi rotor D'yi güçlü etkiliyor, stator D'yi zayıf; x 1.1 bir rotor ihlalini kapatmıyor ve stator
  katılığını aralık dışına itiyor. Kol olarak uygulanmadı.

## Kombinasyonlar (normalize, bilgi)
Izgara: anülüs {göbek, ortalama, uç} x iş {eşit PR, 40/33/27, 30/33/37} x veter {1.0, 0.9, 1.1, 1.2} x k {1, 0.5,
0} = 108 çalıştırma [H]. Sıfır D ihlali yok; en az 1 (her zaman 3Ru, ör. sabit uç, eşit PR, veter x 1.1, k = 0:
0.4954). Kademe 3 rotor ucu bu kollarla kapanmıyor.
