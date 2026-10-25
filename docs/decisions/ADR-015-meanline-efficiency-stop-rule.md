# ADR-015: Meanline verimi için durma kuralı (M1 fan)

Durum: **kabul edildi** (kullanıcı kuralı, M1 adım 4d). **Uygulanan dal: bütçe verimi.**

## Kural
Kayıp biçimi değişiklikleri (adım 4b-4d) ve ADR-014 (a) kalibrasyonundan sonra Rotor 67 stall yakını nokta hâlâ geçmiyorsa:
- M1'in kendi verim tahmini kullanılmaz. Fan verimleri (eta_fan_outer, eta_fan_inner) M0 bütçesinden alınır (`core.budgets.read_icd`). M1'in kendi tahmini olarak etiketi [T] olur.
- Meanline yalnızca hız üçgenleri, metal açıları, DF ve geometri (veter, solidite, akım tüpü yarıçapları) için kullanılır. Radyal denge ve tam kayıp modeli açık kalır (`rotor67.FULL_MODEL` biçimleri): üçgenler ve DF bu modelden gelir.
- Meanline'ın hesapladığı verim bilgi olarak raporlanır [H, doğrulanmamış model]. Bütçe kontrolüne verilmez.
- Çıkış sıcaklıkları (T13, T21) hedef PR ve bütçe veriminden hesaplanır: Tt_çıkış = Tt2 (1 + (PR^((γ-1)/γ) - 1) / η_bütçe). Böylece çevrimle tutarlı kalır.

## Hangi dal uygulanıyor
Adım 4d sonuçları (`engine/M1_inlet_fan/analysis/rotor67_validation.yaml` `loss_review`, `loss_calibration.yaml`) [H]:
- B1 (ses altı giriş akışında şok kaybı yok): tasarım PR -%3.8, stall yakını PR -%7.2, η 0.855 (ölçülen 0.901).
- B2 (Koch-Smith profil kaybı): kaynak setinden kurulamıyor, doğrulanmadı.
- C (kalibrasyon): profil 0.66, şok 0.38, uç duvar 0.80, uç 0.05. Şok ve uç 0.5-2 dışında, uygulanmadı. Bu çarpanlarla bile stall yakını η 0.938 (+3.7 puan). Ayrıca çarpanlar adım 4c'dekinden çok farklı (şok 0.05 -> 0.38, uç 0.57 -> 0.05), yani veri dört çarpanı iyi belirleyemiyor.
- Stall yakını kalıyor. Uygulanan dal: **bütçe verimi**.

## Sonuçlar
- M1 bütçe kontrolünde verim satırları tanım gereği bütçeye eşit. Bu bir doğrulama değil, varsayımdır [T]. Rapor bunu açıkça söyler.
- Tam kayıp modeli verimi düşük tahmin ediyor (Rotor 67'de tepe veriminin yaklaşık 7 puan altında). Bu yüzden hedef PR'ye ulaşmak için meanline daha fazla iş, yani daha fazla dönüş ister. Metal açıları ve DF muhafazakâr yönde (fazla yüklü) olabilir. Sınırlama olarak raporlanır.
- Kayıp biçimleri düzeltilip Rotor 67 stall yakını geçtiğinde bu ADR yeniden ele alınır ve meanline verimine dönülür.
