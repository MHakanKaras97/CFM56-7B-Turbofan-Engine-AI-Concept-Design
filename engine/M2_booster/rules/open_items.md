# M2 Open Items

The list is kept in one place: `docs/open_issues.md`, section "M2 Booster" (#57 onwards). This file only points there.
Step 1 items: #57 TP-1523 hub/tip extrapolation at stage 1, #58 station 21 Mach vs Lolis inlet Mach 0.5 (closed: M1 area kept, no CR),
#59 TP-1523 OCR rows unresolved, #60 booster materials not sourced, #61 mass check value weak.
Step 3 follow-up (#64 analysis): `analysis/sensitivity_64.py`, `learning/duyarlilik_64.md`. #68 spanwise closure.

## Step 4 drafts for `docs/open_issues.md` (M2 cannot write there; M0 copies verbatim)

New rows (remaining R-AM2.2 violations after step 4; no limit loosened):

| # | Modül | Konu | Etiket | Neden kabul edildi | Yeniden bakma tetikleyicisi | Kaynak |
|---|---|---|---|---|---|---|
| 69 | M2 | R-AM2.2 ihlali (bilinen sapma), adım 4 son taban (normalize profil, sabit uç yarıçapı L2): kademe 2 rotor uç D 0.4820 > 0.45 (pay -0.032); kademe 2 diğer kesitler geçiyor (rotor göbek/orta 0.4969/0.4311, stator 0.5755/0.4697/0.5127) | [T] | Koşudan önce yazılı kol kuralı (aero_method.md "Design levers", tek geçiş) uygulandı; L1 ve L3 ihlal sayısını azaltmadı; sınır, rotor sayısı 74/78/74 ve 3 kademe değişmedi; D değerleri [T] açıklık aktarımına bağlı | Kol kuralının ikinci geçişi (kullanıcı kararı), göbek iş oranı kuralı, eksenel Mach kuralı, booster açıklık dağılımı kaynağı veya rotor uç kriteri (verim ölçütü; verim M0 bütçesinden) değişirse | analysis/sensitivity_64.py; learning/duyarlilik_64.md; RM E53D01 s. 1 |
| 70 | M2 | R-AM2.2 ihlali (bilinen sapma), adım 4 son taban: kademe 3 rotor uç D 0.5550 > 0.45 (pay -0.105); kademe 3 diğer kesitler geçiyor (rotor göbek/orta 0.5621/0.4914, stator 0.5796/0.4788/0.5274; stator göbek sınıra 0.0004). 108 kombinasyonun hiçbiri bu ihlali kapatmıyor (en iyi 0.4954) | [T] | #69 ile aynı kural; kademe 3 ucu tüm yazılı kollarla açık kalıyor, kapatmak kural düzeyinde kullanıcı kararı ister | #69 ile aynı; ayrıca kademe sayısı veya iş bölüşümü kaynağı | analysis/sensitivity_64.py; learning/duyarlilik_64.md; RM E53D01 s. 1 |

Suggested updates of existing rows (wording for M0):
- #64: adım 4 ile yerine geçti: normalize taban 3 ihlal (1Ru 2Ru 3Ru, 3Rg normalizasyonla kapandı); L2 sabit uç
  uygulandı (3 -> 2); kalanlar #69, #70. Tetik/kaynak aynı.
- #65: stator sayıları R-KV2.1 ile 31/39/49 [T] (adım 4 son taban); stator göbek D 0.5740/0.5755/0.5796 <= 0.58;
  uç katılığı aralıkta.
- #67: annulus artık sabit uç + sabit eksenel Mach [T] (L2, aero_method.md "Design levers"); yeni parametreler
  tip_work_ratio_k 1.0, rotor_chord_scale 1.0, spanwise_normalisation mass_and_work, axial_mach_scale 1.0 [T].
- #68: kapandı (adım 4): "Spanwise normalisation" kuralı; oranlar 1 (1e-6 içinde), W25/pr_booster/T25 ICD
  toleransında. Eski kural yalnız bilgi satırı olarak `sensitivity_64.py`'de.
- #57: sabit uç ile rotor hücum kenarı göbek/uç 0.697/0.760/0.808 (kademe 3 rig 0.8 üstünde); kademe 1-2 hâlâ altında.
- New info for M3 (no CR, M3 not started): ist. 25 göbek yarıçapı 0.36624 m, uç 0.433488 m [T] (ist. 24 anülüsü,
  geçiş kanalı modellenmedi), `engine/M2_booster/geometry/flowpath.yaml` interfaces.M3_station_25.

## Geometry step 1 drafts for `docs/open_issues.md` (M0 copies verbatim)

| # | Modül | Konu | Etiket | Neden kabul edildi | Yeniden bakma tetikleyicisi | Kaynak |
|---|---|---|---|---|---|---|
| 71 | M2 | Booster kanat malzemesi ve yoğunluğu kaynaksız: rotor `ti6al4v` (M1 fan kanadı benzetmesi), stator `tbd`; geometri adım 1 kütlesi statorlar için de `ti6al4v` yoğunluğunu yer tutucu olarak kullanıyor (geometry_params.yaml stator_mass_material); kütle yalnız bilgi | [T] | Konsept seviyesi; kütle kabul değeri değil (#60, #61 ile ilişkili) | CFM56-7B booster malzeme kaynağı, stator bağlantı/örtü seçimi veya kütle bütçesi | rules/materials.md; rules/geometry.md R-G2.7; tools/data/materials.yaml |
| 72 | M2 | Booster kesit kuralı kaynaksız (R-G2.3-6): dairesel yay kamber, parabolik kalınlık (TP-1523 çift dairesel yay ailesinin yerine), t/c rotor göbek 0.06 / uç 0.03, stator 0.05, kenar 0.01; metal açıları = akış açıları (hücum ve sapma açısı sıfır, Carter/Lieblein sapma kuralı uygulanmadı); eksenel boşluk 0.25 x eksenel genişlik; uç açıklığı TP-1523 rotor 23B oranı (Tablo 18 s. 47) ile orantılı aktarım; stator uç/göbek açıklığı yok | [T] | Konsept geometri; değerler kayda değil geometry_params.yaml'a bağlı, kontrollerin hiçbiri bu sabitlerle ayarlanmadı | Booster kesit/kalınlık kaynağı, sapma kuralı (metal açısı adımı), yapısal analiz (kök gerilmesi, HCF FM2-5) veya uç açıklığı kaynağı | rules/geometry.md; geometry/geometry_params.yaml; TP-1523 Tablo 8 s. 37, Tablo 18 s. 47 |
| 73 | M2 | İstasyon 24/25 eksenel konumu artık geometriden çıkıyor (x24 = S3 firar kenarı, R-G2.2 [T] kurallarıyla); geometry/flowpath.yaml M3_station_25 arayüzünde x yok ve geçiş kanalı 24 -> 25 modellenmedi (ist. 25 = ist. 24 düzlemi yer tutucu) | [T] | flowpath.yaml rev001 kaydının çıktısı; değiştirmek yeni revizyon ister, bu adımda revizyon yok | Bir sonraki M2 revizyonu veya M3 başlangıcı (x25 ihtiyacı) | geometry/layout.py; geometry/flowpath.yaml |

Note for M0 (no open issue): shared frame module recommendation in `rules/geometry.md` (end of file); it needs a CR
(core/ and M1 are outside M2).

## Geometry step 2 drafts for `docs/open_issues.md` (M0 copies verbatim)

Values from `geometry/hardware.py` (`checks`, `m1_overlap`), rev001, step 2 rules R-G2.9-17.

| # | Modül | Konu | Etiket | Neden kabul edildi | Yeniden bakma tetikleyicisi | Kaynak |
|---|---|---|---|---|---|---|
| 75 | M2 | R-G2.10 "yuva iki jant yüzünde açık" şartı sağlanmıyor: her rotor yuvası ön yüzde açık, arka yüzde bir sonraki statorun tambur duvarı (sızdırmazlık dişi tabanı) yuva tabanının üstünde kalıyor; kapalı yükseklik kademe 1/2/3 17.70/13.22/10.05 mm [H]. Parça kurulabiliyor, kök bloğu yuvaya önden giriyor. Analiz: kapanma = rotor boyunca göbek yükselişi (21.32/16.17/12.46 mm) + yuva derinliği 0.25 c_R (15.09/12.02/9.65 mm) - conta yığını 0.20 c_S (17.85/14.29/11.52 mm) - conta açıklığı (0.86/0.68/0.55 mm); yuva derinliği 0 olsa bile diş tabanı rotor hücum göbeğinin 2.62/1.20/0.39 mm üstünde (sığ yuva imkânsız). Kural seçenekleri (meanline değişmez) [T]: eğik tabanlı eksenel yuva (arka yüz payı 3.62/2.96/2.41 mm), çevresel kırlangıç oluğu, duvar bağlantısını 17.70/13.22/10.05 mm indirmek (conta kolu), önden açık kör yuva + tutucu (broşlanamaz), tümleşik kanatlı halka [H] | [H] | Kural oranlarıyla çıkan sonuç; oran ayarlanmadı (dur kuralı: geometri olduğu gibi, yer tutucu) | Bağlantı tipi kaynağı (J2-2, eksenel/çevresel kırlangıç doğrulanamadı), tutucu tasarımı veya yapısal aşama (A-4) | rules/geometry.md R-G2.10/11; geometry/hardware.py; analysis/conflicts_75_77.py slot_closure; learning/geometri_celiskileri.md |
| 76 | M2 | Tambur - fan diski arayüzü kapanmıyor: tambur ön flanşı ist. 21 düzleminde (x 0.235369 m, iç yarıçap 0.172952 m, cıvata dairesi 0.186545 m [T]); M1 disk jantı arka yüzü x 0.140291 m (rev014, salt okunur) -> eksenel boşluk 0.095078 m [H]. M1 diskinde arka kol/flanş yok; ya M1 diske arka kol ekler (M1 değişikliği, CR) ya da M2 tamburu ist. 21 düzlemini geçen bir ön koni alır (sınır kuralı değişikliği). Analiz: x 0.140291-0.235369, r 0-0.30213 bölgesi M1 parçalarından boş; aynı aralıkta iç akış yolu duvarı da yok. Geçici koni (flanş r 0.172952-0.200138 disk arka yüzünde, 4.85 mm kabuk ist. 21 flanşına) hiçbir M1 parçasıyla çakışmıyor, diske temas, M8 sınırına (r 0.151065, M1 fan_frame_params bearing_flange_inner_over_hub_radius 0.5 [T]) pay 0.021887 m, kütle 3.456 kg (M2.0.1'de bir kez). Değişecek kurallar R-G2.9, R-G2.13, R-G2.17; cıvata delikleri M1 diskinde (arayüz CR) [H] | [T] | M2 parçası ist. 21'i geçmez kuralı (R-G2.13); M1 kabul edilmiş, CR açılmadı | M0/kullanıcı kararı (hangi taraf köprüler), son montaj veya J2-1 tasarımı | rules/geometry.md R-G2.13; rules/joints.md J2-1; M1 geometry/rotor_hardware.py; analysis/conflicts_75_77.py forward_space, cone_check; learning/geometri_celiskileri.md |
| 77 | M2 | M1 rev014 parçaları booster hacmiyle çakışıyor (ortak hacim / küçük parça hacmi, yalnız rapor): fan çerçevesi x 0.478-0.635 m booster kademe 2-3 üstünde; çekirdek dikmesi R3 kanadı 0.653, S3 kanadı 0.550, R3 kök bloğu 0.468, S2 kanadı 0.137, tambur 0.092; splitter halkası (r 0.4248-0.4335) tüm kanat uçlarında 0.041-0.119; M2 kasası (r >= 0.433488) baypas dikmesi 0.021 ve OGV 0.019 ile, ayaklar 0.093-0.178 [H]. M1 #49 tetikleyicisi (M2 akış yolu tasarımı) gerçekleşti. Analiz: (a) splitter ile M2 kasası ortak hacimsiz, ortak yüzey r 0.433488 x 0.270-0.635: aynı çekirdek/baypas duvarı, M1 kalınlığı içe, M2 dışa almış; kütle M1.4.3 23.3591 kg (Al) ve M2 kasası 31.8164 kg (Ti yer tutucu; Al ile 20.11 kg), M2 BOM boş olduğundan henüz çift sayım yok; splitter iç yüzü uç akış yolunun 8.67 mm içinde, M2 tarafında kaldırılamaz (CR). (b) kasa x OGV takım 4.339e-4 m3, x baypas dikmeleri 1.478e-4 m3 (r 0.43349-0.44216): radyal yer sıfır (r_split2 = ist. 21 uç), M2 kalınlık/boy/boşluk/ayak seçenekleri kaldırmıyor (CR: baypas iç duvarı en az 8.67 mm dışa veya ortak duvar). (c) çekirdek dikmeleri tambur/örtü/S2-R3-S3 bantlarıyla (tambur takım 2.573e-4 m3); sıra genişlikleri 0.325786 m > ist. 21-dikme 0.258375 m (eksik 0.067411 m), M2 tarafında imkânsız; CR: dikmeler >= 0.147812 m, çerçeve >= 0.163497 m aft ve çerçeve çekirdek kanalı M2 anülüsüne; göbek halkası/yatak flanşı dönen tamburun içinde [H] | [H] | M1 parçaları M2 komşusu değil (R-G2.17); M2 kuralları değiştirilmedi, M1'e dokunulmadı, CR yok | M0/kullanıcı kararı: M1 çerçeve/splitter yerleşimi (CR) veya booster kasa yarıçapı/uzunluğu (yeni M2 revizyonu) | geometry/hardware.py m1_overlap; M1 geometry/fan_frame.py, ogv.py; analysis/conflicts_75_77.py overlap_table, frame_numbers, splitter_casing; learning/geometri_celiskileri.md |

Notes for M0 (no open issue, no CR):
- Drum ownership (R-G2.15): the drum is M2's part M2.0.1, confirmed by the user [T] (bom.md plan; architecture.md
  section 4 gives M8 shafts, bearing supports and sumps). The booster spool LLP life (22,900 vs 23,600 EFC conflict
  still open, #49) is in M2 `known_values.md`; M8 keeps a one-line pointer.
- BOM proposal for the BOM step (not written): inner shrouds as `M2.<n>.4 Booster Stage <n> Inner Shroud` (qty 1, full
  ring at concept level); root blocks and vane feet stay inside M2.n.1 / M2.n.2; abradable liners M2.n.3 not modelled.
- The M1 hub ring (r 0.2935-0.3021 m) and bearing flange lie inside the M2 drum without common volume; a stationary
  M1 part inside the rotating drum is part of #77.
- `tests/test_m2_geometry1.py::test_rules_linked_and_tagged` counts lines starting with `| R-G2.` and expects 8; the
  step 2 ids are written in bold (`| **R-G2.9** |`) so that the step 1 count holds. Suggest counting R-G2.1-8 explicitly.

## Geometry step 3a updates for #75 and #76 (M0 copies verbatim; #77 unchanged, test stays strict xfail)

Values from `geometry/hardware.py` (`checks`, `slot_checks`, `cone_checks`), rev001, rules R-G2.9/13/17 (step 3a
text) and R-G2.18-19. No constant tuned; no new open issue (stop rule not triggered, next free number stays #78).
Replacement rows (same columns):

| # | Modül | Konu | Etiket | Neden kabul edildi | Yeniden bakma tetikleyicisi | Kaynak |
|---|---|---|---|---|---|---|
| 75 | M2 | Adım 3a: R-G2.19 (seçenek 1) uygulandı: rotor yuva tabanı yerel göbek çizgisine paralel, derinlik 0.25 x rotor kirişi değişmedi; yuvalar iki jant yüzünde açık. Arka yüz payı (arka yüzde yuva tabanı - sonraki statorun tambur duvarı dış yarıçapı) kademe 1/2/3 3.622/2.956/2.415 mm, ön yüz payı kademe 2/3 12.526/9.906 mm [H]. Kök bloğu: tamburla ortak hacim 0, tambura mesafe 0.197/0.195/0.216 mm (uyum açıklığı 0.214/0.212/0.234 mm; konik tabanda normal mesafe radyal açıklıktan küçük) [H]; kütle 4.081/2.632/1.771 kg (adım 2: 6.68/4.27/2.83) [H]. Paylar yapısal aşama için kontrol, geçiş değil | [T] | Kural [G] gerekçeyle seçildi (konik jantta eksenel kırlangıç jant konisini izler, kök taşıma derinliği kök boyunca aynı), "R-G2.10 geçsin" diye değil; oran ayarlanmadı | Yapısal aşama (A-4 kök/jant boyutlandırması, paylar 2.4-3.6 mm küçük), J2-2 kırlangıç tipi kaynağı (eksenel/çevresel doğrulanamadı) | rules/geometry.md R-G2.10, R-G2.19; geometry/hardware.py slot_checks; learning/geometri_celiskileri.md |
| 76 | M2 | Adım 3a: R-G2.9/13/17 değişti, R-G2.18 ön koni uygulandı. Donanım sınırı M1 disk arka yüzü x 0.140291 m, M1 rev014 geometri kodundan çalışma anında okunuyor (yazılmış kopya yok; `m1_disk_*` kaldırıldı); ist. 21 yalnız akış düzlemi. Koni (M2.0.1 tamburunun parçası, tek katı): disk arka yüzünde flanş halkası r 0.172952-0.200138, eksenel 9.704 mm; cıvata dairesi 0.186545'ten ist. 21 tambur flanşının iç kenarına (r 0.172952) 4.852 mm konik kabuk [H]. M1 rotor parçalarıyla (disk, kanat+kök, şim, aralayıcı, platform, spinner) ortak hacim 0 (koni ve tüm tambur), diske temas (mesafe 0), en yakın diğer parça aralayıcı 6.350 mm; M8 yatak flanşı sınırına (r 0.151065, M1 fan_frame arayüzü) radyal pay 0.021887 m; koni 3.456 kg, tambur toplam 63.106 kg (Ti-6Al-4V yoğunluğu, bilgi; kütle bir kez M2.0.1'de) [H]. Kalan: cıvata delikleri M1 diskinde modellenmedi (M1 spinner emsali; M1 parçasına delik eklemek arayüz CR ister); x 0.140291-0.235369 aralığında göbek akış yolu duvarı (M1 platformu ile ist. 21 arası) yok, bu adımda ele alınmadı | [T] | Kullanıcı görevi (adım 3a) M2 kural değişikliğini istedi; M1 dosyası değişmedi, CR yok | Son montaj, J2-1 cıvata/flanş tasarımı (M1 disk deliği CR), M8 mil/yatak tasarımı (r 0.151065 sınırı [T]), göbek duvarı boşluğunun sahibi (M0) | rules/geometry.md R-G2.9, R-G2.13, R-G2.17, R-G2.18; rules/joints.md J2-1; geometry/hardware.py m1_interface, cone_checks; M1 geometry/rotor_hardware.py, fan_frame.py |

Notes for M0:
- Superseded tests in `tests/test_m2_geometry2.py` (old rules): `test_hw_params_tagged` (24 -> 20 keys),
  `test_m1_disk_copy_matches_m1_code`, `test_nothing_ahead_of_station_21`, `test_slot_aft_face_known_deviation`;
  replacements and the step 3a acceptance tests in `agent/proposed_test_geometry3a.py`.
- Step 3a ids R-G2.18-19 are in bold so that the R-G2.1-17 row count of the M0 tests holds (step 2 precedent).
- `analysis/conflicts_75_77.py` stays the step 2 analysis record; after step 3a its temporary cone coincides with the
  drum cone (common volume = cone volume), as expected.

## Geometry step 3b: hub flow-path wall (#79) and new draft #80 (M0 copies verbatim)

Values from `geometry/hardware.py` (`hub_wall_checks`, `hub_line_gaps`), rev001, M1 rev014 (read-only), rule R-G2.20.
No constant tuned; stop rule triggered twice: literal hub-line check (M1 platform shape) -> #80; R1 slot front face
covered by the wall -> #81 (wall kept as the rule gives it, placeholder). Replacement row #79, new rows #80, #81:

| # | Modül | Konu | Etiket | Neden kabul edildi | Yeniden bakma tetikleyicisi | Kaynak |
|---|---|---|---|---|---|---|
| 79 | M2 | Adım 3b: R-G2.20 göbek akış yolu duvarı uygulandı (M2.0.1 tamburunun parçası, koni ve tamburla tek katı, kütle bir kez). Duvar x 0.140777-0.235369 m, r 0.297278-0.30213 m; kalınlık 4.852 mm (kademe 1 tambur duvarı kuralı); M1 platform arka ucuna eksenel birleşim boşluğu 0.1 x duvar kalınlığı = 0.000485 m (katılarda ölçülen aynı) [H]. Dış yarıçap katıda 0.30213 (1e-5 içinde, M1 ist. 21 göbeği); M1 rotor parçaları, ön koni, M2 kanatları ve kök bloklarıyla ortak hacim 0; tambur duvar başlangıcından ist. 21'e boşluksuz. Duvar 3.829 kg, tambur toplam 66.935 kg (adım 3a 63.106; Ti-6Al-4V yoğunluğu, bilgi) [H]. Kalan: göbek çizgisi kanat firar kenarı - platform arka ucu arasında #80; duvar R1 yuva ön ağzını kapatıyor #81 | [T] | Kullanıcı kararı (sahibi M2, tambur kabuğunun öne uzantısı); oran [T] kaynaksız, ayarlanmadı; BOM, revizyon, M1 dosyası değişmedi | Sonraki M2 revizyonu (tambur kütlesi kayda girer), J2-1 / yapısal aşama (A-4), #80 kararı | rules/geometry.md R-G2.20; geometry/geometry_params.yaml hw_wall_joint_gap_over_wall; geometry/hardware.py hub_wall, hub_wall_checks |
| 80 | M1-M2 | M1 rev014 platformunun (M1.1.6) üst yüzü göbek akış yolu çizgisini izlemiyor: uçları arasında düz koni (disk ön yüzünde r 0.23241, arka yüzde 0.30213); kanat göbek firar kenarı x 0.109785 ile platform arka ucu x 0.140291 arasında M1 göbek çizgisinin (sabit 0.30213) altında, firar kenarında 8.045 mm, arka uçta 0 [H]. Göbek çizgisinin 10 µm altından yapılan sonda bu aralığı kaplanmamış görüyor: en büyük boşluk 0.030992 m > birleşim boşluğu 0.000485 m (R-G2.20 kontrolü, katı xfail). Eksenel birleşim (platform arka ucu - M2 duvarı) kural değerinde; radyal basamak yok (ikisi de x 0.140291'de r 0.30213) [H] | [H] | M1 kabul edilmiş ve salt okunur (ADR-016); M2 tarafında düzeltilemez (duvar platform bölgesine uzatılamaz, M1 parçasıyla çakışır); ayar yapılmadı | M0/kullanıcı kararı: M1 platform üst yüzünü göbek çizgisine oturtan CR (M1 platform() üst kenarı) veya sapmanın bilinen sapma olarak kabulü; M1 platform/kırlangıç ayrıntılı tasarımı (#25, #35) | geometry/hardware.py hub_line_gaps; agent/proposed_test_geometry3b.py; M1 geometry/rotor_hardware.py platform(), geometry/flowpath.yaml curves_x_r_m.hub |
| 81 | M2 | R-G2.20 duvarı ist. 21'de rim 1 ön yüzüne bağlanıyor ve R1 yuvalarının ön ağzının üst 4.852 mm'sini (duvar kalınlığının tamamı, r 0.297278-0.30213) kapatıyor; altında 10.236 mm pencere kalıyor (yuva tabanı ön yüzde r 0.287043). Kök bloğu (yükseklik ~ yuva derinliği) pencereden geçmez -> R1 kökleri önden takılamaz; R1 kök bloğu - tambur mesafesi 0 (temas duvarın arka yüzünde; R-G2.19 > 0 ve <= uyum açıklığı 0.214 mm ister), ortak hacim 0. Yuva arka yüzde açık (pay 3.622 mm) [H]. Seçenekler (kullanıcı/M0, kural düzeyinde) [T]: (a) yuvaları duvar boyunca kesmek (duvar ön ucu yarıklı dudak olur, akış yolunda 74 yarık); (b) duvar ile rim 1 arasında eksenel birleşim boşluğu (ayrı tutucu halka gibi; duvar koniye/flanşa ayrı bağlanmalı); (c) R1 köklerini arkadan takmak (montaj sırası S1 örtüsünden önce); (d) duvar R1 için kanat tutucusu sayılır (gerçek boosterlarda ön tutucu halka yaygın [G], kaynak doğrulanamadı) | [H] | Dur kuralı: duvar kuralın verdiği gibi bırakıldı (yer tutucu), oran ayarlanmadı; sistem sorunları listesinde tek kayıt | Kullanıcı kararı (a-d), J2-2 kırlangıç/tutucu tasarımı, yapısal aşama (A-4) | rules/geometry.md R-G2.10, R-G2.19, R-G2.20; geometry/hardware.py hw_layout (hub_wall slot_front_covered), slot_checks; agent/proposed_test_geometry3b.py |

Notes for M0:
- New constant `hw_wall_joint_gap_over_wall` (0.1 [T]) -> `tests/test_m2_geometry3a.py::test_hw_params_tagged_step3a`
  counts 20 `hw_*` keys and now sees 21 (expected failure, superseded; suggest 21 or an explicit key list).
- #81 makes `issues` non-empty: `test_built_without_stop_rule` in `tests/test_m2_geometry2.py` and
  `tests/test_m2_geometry3a.py` fail, `test_m2_geometry3a.py::test_slot_aft_face_margins` fails (asserts R1
  `slot_open_front`) and `test_m2_geometry3a.py::test_root_block_fits_slot` fails for R1 (distance 0);
  suggest strict xfail on #81 until the user decides (a)-(d).
- Proposed tests: `agent/proposed_test_geometry3b.py` (literal hub-line test is a strict xfail on #80).
- Possible CR draft (not created, M0/user decide on #80): M1 `rotor_hardware.platform()` top edge following the M1
  hub line (`h(x)` at intermediate x, not the straight end-to-end line); impact: platform volume/mass, rim dead load
  (R-DISK.2), M1 tests; no M2 change needed (the wall already starts at the platform aft end + joint gap).

## Geometry step 3c: R1 root insertion (#81), #80 known deviation, new draft #82 (M0 copies verbatim)

Second pass (user decision option (2)): values from `geometry/hardware.py` (`place_slot_bottom`) and
`geometry/insertion.py` (`sweep`, `r1_seated_fit`), rev001, M1 rev014 (read-only), rules R-G2.19 (amended) and R-G2.21
(gate as exact swept solid). No constant added or tuned; slot geometry changed by the amended rule; gate clear, #81
removed from `hw["issues"]`. Replacement rows #80 (unchanged), #81, new row #82:

| # | Modül | Konu | Etiket | Neden kabul edildi | Yeniden bakma tetikleyicisi | Kaynak |
|---|---|---|---|---|---|---|
| 80 | M1-M2 | Bilinen sapma (kullanıcı kararı, adım 3c): M1 rev014 platformunun (M1.1.6) üst yüzü kanat göbek firar kenarı x 0.109785 ile platform arka ucu x 0.140291 arasında M1 göbek çizgisinin (0.30213) altında, en çok 8.045 mm (firar kenarında), arka uçta 0; kaplanmamış aralık 0.030992 m > birleşim boşluğu 0.000485 m (R-G2.20 kontrolü, katı xfail kalıyor) [H]. CR açılmadı | [H] | Kullanıcı kararı: bilinen sapma olarak kabul; M1 kabul edilmiş ve salt okunur (ADR-016), M2 tarafında düzeltilemez; ayar yapılmadı | Bir sonraki M1 tasarım revizyonu veya son montaj | geometry/hardware.py hub_line_gaps; tests/test_m2_geometry3b.py; M1 geometry/rotor_hardware.py platform() |
| 81 | M2 | Adım 3c (ikinci geçiş), kullanıcı kararı seçenek (2): R-G2.19 değiştirildi, yuva yuva ekseni boyunca düz prizma (broşlanan/frezelenen eksenel kırlangıç yuvaları gibi, G); eksen rotor sırası üzerindeki göbek eğimiyle yükseliyor (eksenel metre başına 0.42395 / 0.42155 / 0.41015), düz taban rotor sırasının her noktasında belirtilen derinliğin (0.25 x veter) en az o kadar altında, en derin noktada temas. Rotor sırası üzerinde ek derinlik R1/R2/R3 1.067 / 0.804 / 0.620 mm; jant boyunca derinlik 12.669-21.026 / 10.189-16.148 / 8.260-12.947 mm (belirtilenden sığ yalnız arka çalışma boşluğu yarısında); arka yüz payı 5.124 / 4.028 / 3.152 mm (adım 3a 3.622 / 2.956 / 2.415), ön yüz payı R2/R3 8.394 / 6.611 mm; canlı jant 9.149 / 13.246 / 11.793 mm [H]. R-G2.21 yol tanımı değişmedi (R1 eğimi aynı, yol artık düz yuva tabanını tam izliyor); 405 adımlı tarama yerine kademe başına tam süpürülmüş katı (blok 13091 / 7909 / 5606 mm3, süpürülen 30035 / 17842 / 12618 mm3): tambur (duvar ve dişler dahil), ön koni ve oturmuş komşu köklerle ortak hacim üç kademede de 0 (tolerans 1e-6 x blok hacmi): TEMİZ [H]. R-G2.21 uygulandı: #81 sistem sorunları listesinden çıkarıldı; R1 ön ağzı duvarla kapalı (4.852 mm, bilgi), duvar arka yüzü amaçlanan ileri dayanak (oturmuş: dayanak yüzünde mesafe 0, diğer yüzlerde 0.2138 mm = uyum açıklığı, ortak hacim 0) [H]. Bilgi: statorlar önce takılsaydı R1 süpürülmüş katısı S1 iç örtü halkasını (1590.5 mm3, eksenel 28.76 mm, radyal 8.78 mm) ve 3 S1 kanadını (983.0 mm3, eksenel 18.93 mm, radyal 23.87 mm) keserdi; conta yüzeyi, dişler, kanat ayakları kesilmiyor [H]. Seçenek (a) sayıları ilk geçiş değerleridir (yeniden hesaplanmadı) | [H] | Kural değişikliği gerekçesi geçitten bağımsız (talaşlı imalat, G); hiçbir ölçü ayarlanmadı, yeni sabit yok; BOM, revizyon, M1 dosyası değişmedi | Sonraki M2 revizyonu (tambur ve kök kütleleri kayda girer), J2-2 kırlangıç/tutucu kaynağı, yapısal aşama (A-4 kök/jant; arka boşluktaki sığ taban) | rules/geometry.md R-G2.19, R-G2.21; geometry/hardware.py place_slot_bottom; geometry/insertion.py; agent/proposed_test_geometry3c.py |
| 82 | M2 | Kanat tutma modellenmedi: R1 arka tutucusu (tutucu halka; ileri dayanak R-G2.20 duvarı) ve R2/R3'ün ön/arka tutucuları (yuvalar iki yüzde açık, takma yönü kuralla sabitlenmedi) konsept geometride yok [T]; montaj sırası varsayımı: rotor kanatları, sonra statorlar, sonra kasa [G] (kaynak doğrulanamadı) | [T] | R-G2.21 kapsamı: geometri adımı tutma donanımını modellemiyor; kütle ve yük yolu yapısal aşamada | Yapısal aşama (A-4 kök/jant, tutucu boyutlandırması), J2-2 kırlangıç/tutucu kaynağı | rules/geometry.md R-G2.21; rules/joints.md J2-2 |

Notes for M0:
- Second pass, one process per file: `tests/test_m2_geometry1.py` 29 passed; `test_m2_geometry2.py` 12 passed, 1 xfail
  (#77); `test_m2_geometry3a.py` 12 passed, 1 failed; `test_m2_geometry3b.py` 11 passed, 2 failed, 2 xfail;
  `test_m2_geometry3c.py` (first pass) 3 passed, 7 failed, 1 error.
- Replacements: 3a `test_slot_bottom_parallel_to_hub` (curved bottom superseded) -> proposed
  `test_slot_axis_slope_and_path` + `test_slot_bottom_depth_every_row_point` (optionally assert
  `r_slot_bottom == hub_min - d`); 3b `test_built_without_stop_rule` (strict XPASS) -> drop the xfail marker; 3b
  `test_only_stop_rule_is_81` -> proposed `test_stop_rule_state`; 3b `test_r1_root_block_clear_of_drum` (still xfails,
  reason text stale) -> proposed `test_seated_contact_on_forward_stop`; whole `tests/test_m2_geometry3c.py` -> proposed file.
- Proposed tests: `agent/proposed_test_geometry3c.py` supersedes `tests/test_m2_geometry3c.py` (15 passed, ~1 min,
  three swept solids; no xfail).

## Geometry step 4: assembly, station 25, BOM (#73 closed; new draft #84; M0 copies verbatim)

Values from `geometry/flowpath.py` (`station_25`) and `geometry/assembly.py` (`station_25_checks`, `casing_boundary`,
`mass_table`, `common_volume_checks`, `record_checks`), rev001 inputs, M1 rev015 (read-only), rules R-G2.22-27. No
constant added or tuned. Replacement row #73, new row #84, suggested updates of #61 and #82:

| # | Modül | Konu | Etiket | Neden kabul edildi | Yeniden bakma tetikleyicisi | Kaynak |
|---|---|---|---|---|---|---|
| 73 | M2 | Kapandı (geometri adımı 4, R-G2.22): ist. 25 x = M1 rev015 çerçeve çekirdek bölgesinin arka ucu, çalışma anında M1 kodundan okunuyor (`fan_frame.py` `layout` xc1, `build` ile), 0.798406 m [H]; göbek halkası M1.4.1 ve duvar halkası M1.4.6 aynı x'te bitiyor, çekirdek dikmesi firar kenarı 0.782721 m (önde). Geçiş kanalı 24 -> 25 = M1 çerçeve çekirdek geçidi (x 0.641557-0.798406 m, boy 0.156849 m), duvarları ist. 24 yarıçaplarında: ist. 25 anülüsü = ist. 24 anülüsü (göbek 0.36624, uç 0.433488 m, alan 0.168954 m2); M2 kanal parçası eklemiyor; x `geometry/flowpath.yaml` interfaces.M3_station_25.x_m'de (M3 için). Kanal kaybı yalnız ICD kalemi duct_25_24 | [H] | Kullanıcı görevi (adım 4); x elle yazılmadı, M1 dosyası değişmedi; `calc.regenerate` dosyayı iki geçişte yeniden üretiyor (bayat dosyadan da aynı bayt) | M1 çerçeve uzunluğu veya yerleşimi değişirse (M1 revizyonu), M3 kanal şekli/kaybı isterse, M2 x24 değişirse | rules/geometry.md R-G2.22, R-G2.26; geometry/flowpath.py station_25; M1 geometry/fan_frame.py layout |
| 84 | M2 | Planlanan BOM'dan iki kalem geometri olmadığı için çıkarıldı (rules/bom.md adım 4 ek kuralı): aşınabilir astarlar M2.1.3-M2.3.3 (R-G2.12, modellenmedi; FM2-3 bunlara dayanıyor) ve M2.0.3 fan diski bağlantı seti (flanş ve koni M2.0.1 içinde, cıvatalar modellenmedi, J2-1). Kök blokları M2.n.1, kanat ayakları M2.n.2 içinde (kütle birim kütleye eklendi, ayrım notlarda); M2.n.4 iç örtüler eklendi | [T] | BOM tek doğruluk kaynağı ve geometriden üretiliyor; geometrisi olmayan parçaya kütle yazılamaz | Astar malzemesi/kalınlığı (J2-4) veya J2-1 cıvata/flanş tasarımı modellenince; yapısal aşama (A-4) | rules/bom.md; rules/geometry.md R-G2.24; geometry/bom_update.py |

Suggested updates of existing rows (wording for M0):
- #61: geometri adımı 4 kütle tablosu (bilgi, ayar yok): M2 toplamı 160.745 kg [H] (Ti-6Al-4V yoğunluğu kasa, stator ve
  örtülerde yer tutucu, #71), Lolis kontrol değeri 171.41 kg [KS zayıf] (2285.5 x 0.075), oran 0.938.
- #82: S3 kanat ayağının arka tutulması da modellenmedi: S3 oluğu kasanın arka yüzünde açık, ayak bir uyum açıklığı
  önde bitiyor; arka yüzü M1.4.6 halkasının ön yüzü kapatıyor (R-G2.23).
