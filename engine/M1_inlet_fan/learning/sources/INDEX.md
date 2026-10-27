# M1 kaynak dizini

Kaynak PDF'leri açmadan önce buraya bak; sonra `../sources_text/<alt klasör>/<ad>.txt` içinde grep yap (`python -m tools.pdf_text` ile üretilir).
Sayfalar PDF sayfasıdır (`=== p.N ===`), aksi yazılmadıkça. Tam künye ve lisans: `docs/sources.md` (# numarası parantez içinde).
Değer zaten bir yaml'da varsa kaynağı yeniden okuma.

## aero/

### strazisar_1989_nasa_tp2879_rotor67.pdf (#22)
- Strazisar, Wood, Hathaway, Suder, NASA TP-2879, 1989. Lisans: ABD hükümeti eseri.
- Kullanım: Rotor 67 tasarım ve ölçüm değerleri, A-1 doğrulaması, uç duvar blokajı.
- Çıkarılan: `learning/rotor67_reference.yaml`, `learning/rotor67_geometry.yaml`, `learning/rotor67_survey.yaml`, `learning/rotor67_overrides.yaml` (`analysis/rotor67_tables.py`).
- Sayfalar: Tablo I s. 23-36 (kesit başına bir sayfa), Tablo II s. 37, Tablo III(b) s. 39. Basılı sayfa = PDF - 4. Taranmış, OCR katmanı var; sayısal değerler için `aero/bladeatlas_rotor67/` (#41) tercih edilir.

### nasa_sp36_1965_axial_compressor_design.pdf (#43)
- Johnsen, Bullock (eds.), NASA SP-36, 1965. Lisans: ABD hükümeti eseri, kamu malı.
- Kullanım: Lieblein difüzyon faktörü sınırları (R-AM.9).
- Çıkarılan: `analysis/fan_params.yaml` (rotor ucu D < 0.4, göbek D < 0.6) [K].
- Sayfalar: s. 286 (basılı 268) sınırlar, s. 257 (basılı 239) kayıp eğilimi. 526 sayfa; geri kalanı için grep.

### abrisha_2026_fan_loss_model.pdf (#32)
- Abrisha B.E.S., Generalized Fan Stage Loss Model, YL tezi, TU Wien, 2026. Lisans: yazar telifi.
- Kullanım: DF, profil/uç duvar/şok kaybı, stall ve choke; Koch-Smith seçimi.
- Çıkarılan: `rules/aero_method.md`, `analysis/rotor67_validation.yaml`, ADR-014.
- Sayfalar: s. 35-42 (korelasyonlar, limitler), DF kriteri s. 38.

### visentin_transonic_fan_meanline.pdf (#30)
- Visentin A., YL tezi, Padova, 2021. Lisans: beyan yok.
- Kullanım: meanline adımları, kayıp modeli seti. Çıkarılan: `rules/aero_method.md`.
- Sayfalar: s. 27-32 (Tablo 2.1 s. 32).

### zanoni_meanline_cfd_rotor.pdf (#31)
- Zanoni N., YL tezi, Padova, 2020. Lisans: beyan yok.
- Kullanım: SATURN kayıp modelleri (Rotor 37). Çıkarılan: `rules/aero_method.md`, `analysis/fan_params.yaml`, ADR-014.
- Sayfalar: s. 19-20.

### sjogren_2023_fan_mdo_thesis.pdf (#33)
- Sjögren O., lisansiyat tezi, Chalmers, 2023. Lisans: yazar telifi.
- Kullanım: SC90C kayıp ve sapma modelleri, Lieblein. Çıkarılan: `rules/aero_method.md`.
- Sayfalar: s. 22-26.

### khelghatibana_2014_fan_optimization.pdf (#34)
- Khelghatibana M., YL tezi, Polytechnique Montréal, 2014. Lisans: yazar telifi.
- Kullanım: Rotor 67 değerlerinin çapraz kontrolü. Çıkarılan: `learning/rotor67_reference.yaml` (`cross_check`).
- Sayfalar: Tablo 3.1 s. 37.

### vadcard_2022_rotor67_tip_casing.pdf (#38)
- Vadcard vd., ASME GT2022-81694, HAL. Lisans: beyan yok.
- Kullanım: uç sürtmesi arıza modu (FM-6), değer alınmadı. `rules/failure_modes.md`.
- Sayfalar: s. 2, 11-14.

### reis_rotor67_openfoam_thesis.pdf (#35)
- Reis A.J.F., YL tezi, FCT/UNL, 2013. Lisans: yazar telifi; eğitim amaçlı kopya serbest.
- Henüz kullanılmadı.

### tiow_zangeneh_rotor67_inverse.pdf (#37)
- Tiow, Zangeneh, Proc. IMechE Part A, 2002. Lisans: © IMechE.
- Henüz kullanılmadı.

### defoe_2022_rotor67_body_force.pdf (#36)
- Pazireh, Defoe, J. Turbomach. 144(6), 2022. Lisans: ASME kabul edilmiş makale kopyası.
- Henüz kullanılmadı. Metin katmanı yok (`SCANNED`); gerekirse sayfa görüntüsü yalnızca kullanıcı isterse.

### bladeatlas_rotor67/ (#41)
- BladeAtlas (GitHub), commit ec40973. Lisans: veri kamu malı (NASA), kod MIT. PDF değil.
- Kullanım: Tablo I'in temiz sayısal kopyası; sha256 `analysis/rotor67_tables.py` `DIGITAL_FILES`. Çıkarılan: `learning/rotor67_geometry.yaml` [KS].

## structure/

### fox_2023_cfm56-7b_blade_fatigue.pdf (#23)
- Fox, Rossey, Raguet, J Fail. Anal. and Preven. 23, 2023. Lisans: © ASM International.
- Kullanım: dovetail LCF arıza modu, malzemeler, kaplama, muayene.
- Çıkarılan: `analysis/fan_params.yaml`, `bom/bom.yaml` notları, `tools/data/materials.yaml` (alloy718, alüminyum), `rules/failure_modes.md`, `rules/joints.md`.
- Sayfalar: dergi s. 1439 = PDF s. 2; dovetail tartışması s. 1-13.

### mirghani_2023_cfm56-7b_blade_thesis.pdf (#24)
- Mirghani A.A.M., YL tezi, CSU Sacramento, 2023. Lisans: yazar telifi.
- Kullanım: Ti-6Al-4V özellikleri, yorulma testleri, 4000 rpm varsayımı.
- Çıkarılan: `tools/data/materials.yaml` (`ti6al4v`, Tablo 2), `analysis/fan_params.yaml`.
- Sayfalar: Tablo 2 basılı s. 17 (grep "Table 2"); 139 sayfa.

## bird_strike/

### mao_2008_bird_strike_fe.pdf (#25)
- Mao, Meguid, Ng, Int J Mech Mater Des 4, 2008. Lisans: Open Access, CC BY-NC.
- Kullanım: kuş modeli (934 kg/m3, 4 lb), Lagrange yöntemi. `rules/bird_strike.md`, `tools/data/materials.yaml`.
- Sayfalar: dergi s. 83-84, 95 (PDF s. 5-6, 17).

### wang_2024_multiple_bird_strike.pdf (#26)
- Wang vd., Aerospace 11, 434, 2024. Lisans: CC BY 4.0.
- Kullanım: çoklu kuş, SPH, dilimleme; FAA değişiklik geçmişi. `rules/bird_strike.md`.
- Sayfalar: s. 2-7.

### wu_2021_bird_strike_rotor_speed.pdf (#27)
- Wu vd., Appl. Sci. 11, 8883, 2021. Lisans: CC BY 4.0.
- Kullanım: SPH ördek modeli (820 g, 938 kg/m3), rotor dinamiği. `rules/bird_strike.md`.
- Sayfalar: s. 3-5.

### wu_2022_bird_strike_parameters.pdf (#28)
- Wu vd., Appl. Sci. 12, 7, 2022. Lisans: CC BY 4.0.
- Kullanım: çarpma yeri, hız, Johnson-Cook Ti-6Al-4V. `rules/bird_strike.md`, `tools/data/materials.yaml`.
- Sayfalar: s. 2-9.

### zeng_2015_hollow_blade_bird_strike.pdf (#29)
- Zeng vd., Procedia Engineering 99, 2015. Lisans: CC BY-NC-ND 4.0.
- Kullanım: ALE kuş modeli, içi boş kanat. `rules/bird_strike.md`.
- Sayfalar: dergi s. 1387-1389 (PDF s. 3-5).

## regulation/

### easa_cs-e_easy_access_amdt5.pdf (#39)
- EASA Easy Access Rules for Engines (CS-E), Amdt 5. Lisans: EASA kamu yayını.
- Kullanım: CS-E 800 kuş yutma koşulları, kütleler, hızlar, kabul ölçütleri.
- Çıkarılan: `rules/cs_e_800_birds.yaml` [K] (`analysis/bird_class.py` -> `analysis/bird_class.yaml`), `rules/bird_strike.md`.
- Sayfalar: CS-E 800 ve AMC E 800 s. 180-193 (Tablo A s. 180-184).
