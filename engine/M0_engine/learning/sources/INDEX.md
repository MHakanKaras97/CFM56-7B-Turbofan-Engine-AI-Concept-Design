# M0 kaynak dizini

Kaynak PDF'leri açmadan önce buraya bak; sonra `../sources_text/<ad>.txt` içinde grep yap (`python -m tools.pdf_text` ile üretilir).
Sayfalar PDF sayfasıdır (`=== p.N ===`). Tam künye ve lisans: `docs/sources.md` (# numarası parantez içinde).
Değer zaten bir yaml'da varsa kaynağı yeniden okuma.

### EASA_TCDS_E004.pdf (#1)
- EASA TCDS E.004, CFM56-7B serisi, Issue 07, 2023. Lisans: kamu yayını; yalnızca faktler.
- Kullanım: -7B27 kalkış ve maksimum sürekli itki [K].
- Çıkarılan: `engine/M0_engine/rules/tcds_e004.yaml` (`ratings.CFM56-7B27.takeoff_thrust` 121.43 kN, max continuous).
- Sayfalar: Ratings bölümü s. 3, 14, 20.

### edb-emissions-databank_v32__web_.xlsx (#2)
- ICAO Aircraft Engine Emissions Databank v32 (EASA, 2026). Lisans: kamu verisi; yalnızca faktler. PDF değil, metin önbelleği yok.
- Kullanım: OPR, BPR, nominal itki, LTO yakıt debileri; kalkış SFC hesabı.
- Çıkarılan: `engine/M0_engine/rules/icao_edb_cfm56_7b27.yaml` (`tools/extract_edb.py`), `engine/M0_engine/analysis/sfc_takeoff.yaml` (`tools/derive_sfc.py`).

### girao_2023_cfm56-7b_thesis.pdf (#15)
- Girão B.P., CFM56-7B tahmin modeli, YL tezi, UBI, 2023. Lisans: yazar telifi; faktler, kendi cümlelerimizle.
- Kullanım: M0 çevriminin birincil [KS] kaynağı (GasTurb tasarım noktası), doğrulama noktası, modül bilgileri.
- Çıkarılan: `engine/M0_engine/analysis/cycle_params.yaml` (FPR 1.765, verimler, basınç kayıpları, lüle katsayıları, ikincil hava oranları), `engine/M0_engine/rules/girao_2023.yaml` (doğrulama durumu, ara istasyonlar, devirler), `docs/learning/cfm56_7b_module_facts.md` (Bölüm 3).
- Sayfalar: Şekil 4.9-4.10 s. 48-49; Bölüm 3 (motor tanıtımı) yaklaşık s. 13-33.

### indriyati_2024_cfm56-7b_exergy.pdf (#6)
- Indriyati, JNEST 3(3), 2024. Lisans: faktler, kendi cümlelerimizle.
- Kullanım: test istasyonu sıcaklık/basınç ve debileri (ISA değil, yalnızca bilgi).
- Çıkarılan: `engine/M0_engine/analysis/cycle_params.yaml` (`indriyati_turbine_in` 1553 K).
- Sayfalar: s. 2-4.

### yilmaz_2009_cfm56-7b_egt.pdf (#16)
- Yılmaz İ., Proc. IMechE Part G, 2009. Lisans: faktler, kendi cümlelerimizle.
- Kullanım: FN, N1, N2, PS3/P2 (birimler tutarsız); kalkış N1/N2 ortalaması.
- Çıkarılan: `engine/M0_engine/rules/girao_2023.yaml` (`yilmaz_takeoff_mean_n1` 5086 rpm, `_n2` 14403 rpm), `engine/M0_engine/rules/icd.yaml` (M8 bilgi referansı).
- Sayfalar: s. 2-8 (N1/N2 tabloları).

### martins_2015_cfm56-3.pdf (#12)
- Martins D., CFM56-3 off-design, genişletilmiş özet, IST, 2015. Lisans: faktler, kendi cümlelerimizle.
- Kullanım: kalibrasyon yöntemi, EGT formu; verim kaybı başına EGT artışı (yalnızca büyüklük).
- Çıkarılan: `engine/M0_engine/rules/martins_2015.yaml` (fan 4 K, booster 3 K, HPC 8 K, HPT 12 K, LPT 6 K / puan).
- Sayfalar: s. 2-10 (EGT geçen sayfalar).

### kuropatwa_2022_review.pdf (#8)
- Kuropatwa, 2022, DOI 10.37105/sd.186. Lisans: CC BY 4.0.
- Kullanım: yalnızca makullük aralıkları (BPR 5.0-6.8, OPR 21-33, kalkış TSFC 0.32-0.39 lb/(lbf·h)).
- Çıkarılan: `tools/derive_sfc.py` (`SANITY_LB_PER_LBF_H`), `engine/M0_engine/analysis/sfc_takeoff.yaml`, `engine/M0_engine/rules/cycle_inputs.md`.
- Sayfalar: s. 1-7.

### kalkan_2024_cfm56-5a3.pdf (#7)
- Kalkan, Konya J. Eng. Sci., 2024. Lisans: faktler, kendi cümlelerimizle.
- Kullanım: CFM56-5A3 FPR, OPR, BPR (yalnızca karşılaştırma). Yaml değeri yok; `engine/M0_engine/rules/cycle_inputs.md`.
- Sayfalar: s. 4.

### turan_karakoc_2009.pdf (#4)
- Turan Ö., Karakoç T.H., Havacılık ve Uzay Teknolojileri Dergisi 4(2), 2009. Lisans: faktler, kendi cümlelerimizle.
- Kullanım: OPR 32.8 geçersiz sayıldı; SFC 10.63 yalnızca çapraz kontrol (doğrulanamadı). Yaml değeri yok; `engine/M0_engine/rules/cycle_inputs.md`.
- Sayfalar: s. 2, 6-8.

### guynn_2009_nasa_tm.pdf (#17)
- Guynn M.D. vd., NASA/TM-2009-215784. Lisans: ABD hükümeti eseri, kamu malı.
- Kullanım: yalnızca ileri teknoloji sınırları. Çıkarılan değer yok.
- Sayfalar: 97 sayfa; BPR tartışması dağınık (grep "bypass ratio").

### gronstedt_2010_gt.pdf (#10), yadav_2005_gt.pdf (#9), muller_2017_isromac.pdf (#11)
- ASME Turbo Expo GT2010-22519 / GT2005-68244, ISROMAC 2017. Lisans: faktler, kendi cümlelerimizle.
- Kullanım: genel referans. Çıkarılan değer yok.
