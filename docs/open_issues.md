# Açık konular

Konsept kabulünde (ADR-016) bilinen her sapma ve açık konu burada bir satırdır. Sayılar kayıttan/yaml'dan gelir;
kaynak sütunu nerede olduğunu söyler. Kural değişmez, tolerans gevşetilmez; satır yalnızca kabul gerekçesini ve
ne zaman yeniden bakılacağını kaydeder. Kapanan satır silinmez, durumuna "kapandı (<adım>)" yazılır.

## M1 Giriş ve fan (kanat rev011, konsept kabulü)

| # | Modül | Konu | Etiket | Neden kabul edildi | Yeniden bakma tetikleyicisi | Kaynak |
|---|---|---|---|---|---|---|
| 1 | M1 | Göbek t/c 0.134, Rotor 67 göbek aralığı 0.07147-0.08513 dışında (R-AM.16) | [H] | Kullanıcı kabulü (adım 4i-c): göbek bağıl akışta ses altı, yapısal olarak muhafazakâr (kalın); oran taper ve r_göbek/r_uç'tan geliyor | Disk/kırlangıç kuyruğu tasarımı veya göbek veteri/alan yasasını değiştiren M1 revizyonu | REVIEW.md 2026-10-28 (4i-c); aero_method.md R-AM.16 |
| 2 | M1 | Uç t/c 0.02979, Rotor 67 uç aralığının alt sınırında (en küçük A_kök) | [H] | Kural sağlanıyor (sınırda); dayanım riski kuş çarpması ve flutter analizine bağlı | A-7 kuş çarpması (R-BS) ve flutter analizi kurulunca | results.yaml open_items tip_tc_lower_bound |
| 3 | M1 | Ses üstü R-AM.9 solidite tabanı giriş adımında (2 pi r1 / 24): çoğu tüpte muhafazakâr (uç +2.6 %), tüp 5'te (genişleyen) makale tanımıyla Rotor 67'nin 1.8 % altında | [H] | Kullanıcı kabulü (adım 4i-f): ortalama yarıçap adımıyla PR dengesi yok (#4); tanım eşleşmesi değil, bilinen sapma | M0 v2 (off-design, FPR bütçesi yeniden) | REVIEW.md 2026-10-29 (4i-f); aero_method.md |
| 4 | M1 | PR haritası kıvrımı: ses üstü taban ortalama yarıçap adımında iken iç akım dengeli fiziksel dalda dış FPR en çok ~1.7648 (1.765'in ~2.2e-4 altı) | [H] | Gerçek erişilemezlik (çözücü gürültüsü değil); 1.765 bütçe şartı korunuyor, bu yüzden #3 seçildi | M0 v2 veya FPR bütçesi değişikliği | REVIEW.md 2026-10-29 (4i-f stall diagnosis) |
| 5 | M1 | Kanat kütlesi 6.769 kg/kanat, kontrol değeri 4.917 kg (118 kg / 24) oranı x1.38 | [H] / kontrol [KS zayıf] | Kontrol değeri zayıf (tüm kanat, Mirghani); ayar yok; fark Rotor 67 t/c analoğu ve veter seviyesi | CFM56-7B veter/kalınlık kaynağı bulunursa | results.yaml blade mass; aero_method.md 4i-f |
| 6 | M1 | Kanat sayısı 24 (üretim motorları, Fox 2023/NTSB) ile CFM 1997 makalesi 22 çelişkisi | 24 [KS], 22 [K] | 1997 makalesi daha erken bir tasarımı anlatıyor olabilir; üretim değeri seçildi | Üretim kanat sayısını doğrudan veren kaynak | status.md adım 3b; docs/sources.md #42 |
| 7 | M1 | Rotor çıkış göbek yarıçap oranı 1.30 (Rotor 67 1.314 [H]) | [T] | Radyal denge + tam kayıpla 1.45 iç akımda fazla iş veriyordu; Rotor 67'ye yakın değer | M2 booster giriş arayüzü veya M0 v2 akış yolu | fan_params.yaml exit_hub_radius_ratio |
| 8 | M1 | Fan verimleri M0 bütçesinden (eta_fan_outer/inner); M1 bütçe kontrolünde verim satırları tanım gereği eşit | [T] | ADR-015 durma kuralı: kayıp modeli Rotor 67 stall yakınını geçmiyor | Kayıp biçimleri Rotor 67 stall yakınını geçince | ADR-015 |
| 9 | M1 | Kayıp modeli Rotor 67 tepe verimini vermiyor: model 0.857 / ölçülen 0.928 (-7.1 puan); stall yakını 0.855 / 0.901 | [H] / ölçüm [KS] | Bilinen model sapması; meanline yalnız üçgen/açı/DF/geometri için (#8) | Kayıp modeli biçim değişikliği (B2 Koch-Smith kaynağı, akım çizgisi eğriliği) | ADR-015 sapma tablosu; rotor67_validation.yaml |
| 10 | M1 | Kasa, spinner, OGV malzemesi doğrulanmadı; Ti-6Al-4V yorulma değeri test koşulsuz (izin değeri değil, R-MAT.1) | [T] / [KS koşulsuz] | Kanat kabulü statik merkezkaç gerilmesine dayanıyor (yorulma değeri kullanılmıyor); diğer parçalar başlamadı | Disk, kasa, OGV tasarımı veya yorulma analizi başlarken | rules/materials.md R-MAT.1; tools/data/materials.yaml |
| 11 | M1 | results.yaml yazıcısı 9 çok sözcüklü etiket üretiyor (ör. "H from KS", "T (model choice)") | — | Sayılar ve kayıt doğrulaması etkilenmiyor; yalnız etiket biçimi | Sonraki M1 revizyonu (yazıcı tek sözcüklü etiket + not) | engine/M1_inlet_fan/analysis/results.yaml |
| 12 | M1 | Motor giriş boğaz alanı yerine fan yüzü vekili 1.716 m² (orta kuş bandı kenarına 0.9 %) | [T] | Nasel kapsam dışı; CS-E 800 kuş sınıfı vekille aynı | Nasel/boğaz alanı kaynağı veya A-7 analizi | rules/bird_strike.md |
| 13 | M1 | 7B27 SAC Özel Koşul No. 1 "Bird strikes" metni okunmadı | doğrulanmadı | Tasarım güncel CS-E 800 (Amdt 5) ile (kullanıcı kararı) | Metin bulunursa | rules/bird_strike.md |
| 14 | M1 | OGV kanat sayısı doğrulanmadı; OGV kaybı modelde yok | doğrulanmadı | OGV tasarımı başlamadı | OGV tasarımı | rules/bom.md M1.3 |
| 15 | M1 | Rotor 67 OCR açı sütunlarında ~6 % son basamak hatası (en çok 0.22°) | [KS] | Duyarlılık ölçütü 1.5 % içinde (REVIEW.md 2026-10-26) | Temiz açı verisi bulunursa | REVIEW.md; tests/test_m1_rotor67.py |
| 16 | M1 | Çalışma uç boşluğu 3.0 mm (Rotor 67'den ölçekli); CFM değeri yok | [T] | Uç kaybı ve uç tüp verimi bilgi amaçlı (#8) | Kaynak bulunursa veya kayıp modeli değişirse | aero_method.md |
| 17 | M1 | Uçtan %70'te şok azaltma kuralı şok kaybı uyguluyor, lazer verisinde geçit şoku yok (kaynak-ölçüm çatışması) | [KS] çatışma | Model biçimi açık noktası; verim bütçeden (#8) | Kayıp modeli biçim değişikliği | aero_method.md |
| 18 | M1 | Akım çizgisi eğriliği, eğim ve geliş açısına bağlı sapma/kayıp modellenmedi | [G] sınırlama | Konsept seviyesinde basit radyal denge | Off-design (M0 v2) veya kayıp modeli revizyonu | aero_method.md |

## M1 kanat katı modeli (adım 5a, `engine/M1_inlet_fan/geometry/blade_solid.py`)

Kaynaklı değeri olmayan geometri ayrıntıları; ayar yapılmadı. Kayıttaki kütle integraliyle aynı idealleştirme.

| # | Modül | Konu | Etiket | Neden kabul edildi | Yeniden bakma tetikleyicisi | Kaynak |
|---|---|---|---|---|---|---|
| 23 | M1 | Hücum ve firar kenarı yarıçapı 0 (keskin kenar); R-AM.11 profili kenar dairelerini yok sayıyor | [T] | Kayıttaki alan/kütle aynı varsayımla; CFM kenar yarıçapı kaynağı yok | Kuş çarpması/erozyon analizi veya kenar yarıçapı kaynağı | blade_solid.py |
| 24 | M1 | Uç boşluğu kanattan kesilmedi: kanat r_tip1'e kadar (aero modelde çalışma boşluğu 3.0 mm [T], #16) | [T] | Kasa başlamadı; boşluk kasa tarafında tanımlanacak | Kısmen kapandı (5b): boşluk kasa tarafında, #28 | blade_solid.py |
| 25 | M1 | Kök köşe yuvarlatması, kanat-kök geçişi, platform ve kırlangıç kuyruğu yok; kanat r_hub1 düzleminde bitiyor, yükselen çıkış göbek hattı (#7) kesilmedi | [T] | Disk ve kök tasarımı başlamadı; kütle yalnız kanat profili (kayıtla aynı) | Kısmen kapandı (5b): göbek hattı kırpıldı, #29-30; kök/disk 5c | blade_solid.py |
| 26 | M1 | Düzlemsel kesitler sabit yarıçapta, kesit ağırlık merkezlerinden radyal yığma (eğim, ok açısı, silindire sarma yok); dönüş yönü (Y işareti) seçilmedi | [T] | Konsept seviyesi; kayıttaki kütle integraliyle tutarlı | Yapısal (FEM) veya 3B aero analizi; dönüş yönü seçildi (5b), #31 | blade_solid.py |

## M1 konsept montajı (adım 5b-5g, `engine/M1_inlet_fan/geometry/`)

| # | Modül | Konu | Etiket | Neden kabul edildi | Yeniden bakma tetikleyicisi | Kaynak |
|---|---|---|---|---|---|---|
| 27 | M1 | Akış yolu eksenel konumları (splitter dudağı, OGV, istasyon 13) oran kuralıyla; göbek/uç hatları kenarlar arasında doğrusal, sonra sabit yarıçap | [T] | Kaynak yok; konsept seviyesi | OGV (5e), M7 kanalı veya kaynak bulunursa | geometry_params.yaml |
| 28 | M1 | Kasa duvarı = kanat uç hattı + 3.0 mm; boşluk halkası kayıttaki akış alanının dışında (ist. 2: 1.7304 / 1.71577 m², +%0.85) | [T] | Uç boşluğu meanline'da yalnız kayıp; kanat uç yarıçapı kayda eşit kalır (#16, #24) | Kasa (5d) veya kayıp modeli değişirse | flowpath.py |
| 29 | M1 | Kanat kayıt halkasına kırpıldı (uç köşeleri, daralan kasa, yükselen göbek): kütle 6.095 kg, kayıt 6.769 kg (-%10); kayıttaki kütle/gerilme integrali dikdörtgen meridyen varsayıyor (muhafazakâr) | [H] | Tasarım değerleri değişmedi; fark geometrik | Sonraki M1 tasarım revizyonu veya FEM (A-3) | fan_ring.py |
| 30 | M1 | Kök saplaması: kök kesiti göbek hattına kadar prizmatik uzatıldı; platform/kırlangıç kuyruğu yok | [T] | Yapım yardımı; 5c'de kök ile değişecek | Adım 5c | fan_ring.py |
| 31 | M1 | Dönüş yönü seçildi: +X etrafında pozitif (önden bakışta saat yönü) | [T] | 5a kanat yönüyle tutarlı; CFM yönü doğrulanamadı | Kaynak bulunursa | geometry_params.yaml |

## M0 Motor

| # | Modül | Konu | Etiket | Neden kabul edildi | Yeniden bakma tetikleyicisi | Kaynak |
|---|---|---|---|---|---|---|
| 19 | M0 | HPC ve HPT verim kaybının EGT etkisi Martins'in yaklaşık yarısı (sabit geometri yok) | [H] | Tasarım noktası modeli sınırlaması (ADR-010) | M0 v2 off-design modeli | ADR-010 |
| 20 | M0 | Δη = +0.017 sınanmamış varsayım; tolerans ve entegrasyon sınırları | [T] | Konsept seviyesi bütçe | M0 v2 | status.md M0 v1 özeti |
| 21 | M0 | .step dosya ilişkilendirmesi kullanıcıda bekliyor | — | UI işlevi, tasarımı etkilemez | Kullanıcı Fusion ilişkilendirmesini yapınca | docs/design/ui_spec.md |
| 22 | M0 | Bennett künyesi doğrulanmadı; Indriyati HPC havası tanım farkı | doğrulanmadı | Kontrol/karşılaştırma kaynakları, bütçe girdisi değil | Kaynak doğrulaması | docs/sources.md |
