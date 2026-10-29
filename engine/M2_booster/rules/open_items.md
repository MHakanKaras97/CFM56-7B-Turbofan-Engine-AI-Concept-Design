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
