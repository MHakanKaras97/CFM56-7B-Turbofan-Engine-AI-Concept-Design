# ADR-014: Kayıp mekanizması çarpanlarıyla kalibrasyon (TASLAK, önerilen)

Durum: **seçenek (a) denendi (M1 adım 4c), koşul sağlanmadı, uygulanmadı.** Kullanıcı (a)'yı 0.5-2 sınırı koşuluyla onayladı.

## Bağlam
- M1 adım 4b kayıp modeli incelemesi (`engine/M1_inlet_fan/analysis/rotor67_validation.yaml`, `loss_review`) [H]: radyal denge + profil, şok, uç duvar ve uç boşluğu kayıplarıyla Rotor 67 A-1'i geçmiyor.
  - Tasarım noktası: PR 1.534, ölçülen 1.63'e göre -%5.9 (sınır %2); uç Mrel +%1.8 (geçer).
  - Stall yakını, bağımsız kontrol: PR 1.571, ölçülen 1.728'e göre -%9.1; η 0.834, ölçülen 0.901'e göre -6.7 puan.
- Kaynakların gerekçelendirdiği biçim değişiklikleri uygulandı:
  - uç boşluğu kaybı yalnızca açıklığın %80'inin üstünde (Zanoni PDF s. 16);
  - şok modeli zaten geçit şoku (Schwenk / Miller-Lewis-Hartmann türü; Sjögren PDF s. 24, Visentin PDF s. 32);
  - profil kaybı 2B kaskat verisinden geliyor, uç duvar ve uç kayıplarıyla çift sayım yok (Sjögren PDF s. 22-23; Abrisha PDF s. 37).
- Tasarım noktası verim açığı, kütle ortalamalı mekanizma payları (1 - η = 0.163) [H]: profil 0.028, şok 0.068, uç duvar 0.030, uç 0.024. Ölçülen tepe verimin açığı yalnızca 0.072 (η 0.928). En büyük pay şokun.
- Radyal dengede yüksek kayıplı uç tüpleri çıkışta daha çok alan alıyor; orta açıklık tüpleri hızlanıyor ve iş düşüyor. Uç kayıpları bu yolla orta açıklık PR'sini de düşürüyor.

## Öneri
Her kayıp mekanizmasına bir çarpan: k_profile, k_shock, k_endwall, k_tip.
- Toplam kayıp katsayısı: ω = k_profile ω_p + k_shock ω_sh + k_endwall ω_ew + k_tip ω_tip.
- Çarpanlar tek bir sayı olarak bütün tüplere aynı uygulanır. Tüpe ya da açıklığa göre ayrı çarpan yok.
- Kalibrasyon tasarım noktasında yapılır (33.25 kg/s, 16043 rpm, radyal denge açık).
- Doğrulama ve kabul stall yakını noktada (Tablo III(a), 32.31 kg/s): PR ±%2, η ±2 puan. Bu nokta kalibrasyonda kullanılmaz.
- Çarpanlar [H, kalibre] etiketiyle `rules/aero_method.md` içinde ve `tools/meanline.py` girdisi olarak tutulur. Değerleri yalnız kalibrasyon betiği yazar (elle girilmez).
- Sınırlar [T]: 0.3 <= k <= 1.5. Bir çarpan sınıra dayanırsa sonuç "sınırda" diye raporlanır, kabul edilmez.

## Açık sorun: tasarım noktasında belirlenemezlik
TP-2879, tasarım noktası için yalnızca PR'yi (1.63) ve uç Mrel'i veriyor. Tasarım verimi verilmiyor (doğrulanmadı). Uç Mrel kayıplardan bağımsız. Dört çarpanı tek bir denklem (PR) belirleyemez. Seçenekler (kullanıcı kararı):
- (a) Tasarım noktası PR'sine ek olarak tepe verim yakını noktayı da kullanmak: Tablo III(b) radyal PR profili (işaretli satırlar hariç), PR 1.642 ve η 0.928. Toplam 9'a kadar denklem, en küçük kareler. Stall yakını nokta bağımsız kalır.
- (b) Yalnız tasarım noktası, ama mekanizmalar arası oranları kaynaktan sabitlemek: örneğin Abrisha PDF s. 54'deki orta açıklık kayıp katsayısı (yaklaşık 0.027) profil kaybı için bir hedef olur. Bu durumda gerçekte daha az serbest çarpan kalır.
- (c) Ortak bir tek çarpan. "Mekanizma başına bir çarpan" kuralına uymuyor; yalnızca karşılaştırma için.
- Öneri: (a). Kalibrasyonu ölçülmüş verime dayandıran tek seçenek bu ve stall noktası bağımsız kalıyor.

## Riskler
- Çarpanlar, eksik fizik olan eğrilik, olay açısına bağlı kayıp ve kanat-şok etkileşimini örtebilir. Rotor 67 dışında, örneğin CFM56-7B fanında, geçerlilikleri sınanmamış olur.
- Şok çarpanı büyük olasılıkla 1'in çok altına iner. Bu, geçit şoku Mach tahmininin, yani Prandtl-Meyer genişlemesi ve örtülü geçit girişi varsayımının [T], fazla yüksek olduğunu gösterebilir. Bu ayrı incelenmeli.

## Karar
- M1 adım 4c: kullanıcı (a)'yı seçti, koşul: her çarpan 0.5 ile 2 arasında [T], dışındaysa uygulanmaz ve model biçimi sorunu olarak raporlanır.
- Önce şok modeli ölçülen geçit Mach'ına göre düzeltildi: emme yüzeyi genişlemesi artık geometriden. Sonra kalibrasyon yapıldı (`engine/M1_inlet_fan/analysis/loss_calibration.py`, sonuç `loss_calibration.yaml`) [H].
  - Çarpanlar: profil 0.48, şok 0.05, uç duvar 1.01, uç 0.57.
  - Profil ve şok sınır dışında, bu yüzden **uygulanmadı**.
  - Bu çarpanlarla bile stall yakını η 0.936 (ölçülen 0.901, +3.5 puan) kalıyor; PR +%1.1.
- Yorum: veri neredeyse sıfır şok kaybı ve yarı profil kaybı istiyor. Sorun ölçekte değil, biçimde: şok hâlâ fazla güçlü, alt-sesüstü kademeli şok kuralı ölçümde olmayan şok kaybı ekliyor, profil korelasyonu bu kanada uymuyor. Çarpanlar tasarımda kullanılmaz (`rotor67.build_tubes` varsayılanı 1).
