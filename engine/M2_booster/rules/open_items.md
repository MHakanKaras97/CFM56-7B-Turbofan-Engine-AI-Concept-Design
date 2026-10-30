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
- Drum ownership (R-G2.15): the drum is assumed M2's part M2.0.1 [T] (bom.md plan; architecture.md section 4 gives M8
  shafts, bearing supports and sumps). M8 `known_values.md` carries the booster spool LLP life (22,900 vs 23,600 EFC,
  open) as a source value only. Not decided here.
- BOM proposal for the BOM step (not written): inner shrouds as `M2.<n>.4 Booster Stage <n> Inner Shroud` (qty 1, full
  ring at concept level); root blocks and vane feet stay inside M2.n.1 / M2.n.2; abradable liners M2.n.3 not modelled.
- The M1 hub ring (r 0.2935-0.3021 m) and bearing flange lie inside the M2 drum without common volume; a stationary
  M1 part inside the rotating drum is part of #77.
- `tests/test_m2_geometry1.py::test_rules_linked_and_tagged` counts lines starting with `| R-G2.` and expects 8; the
  step 2 ids are written in bold (`| **R-G2.9** |`) so that the step 1 count holds. Suggest counting R-G2.1-8 explicitly.
