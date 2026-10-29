# M2 kaynak dizini

Kaynak dosyalar arşivde (`core.toolpaths.sources_archive()` / `M2_booster/<alt klasör>/`, git dışı, sha256 arşivdeki
`MANIFEST.sha256`'da). Bu kaynaklar zaten metin olarak geldi; `../sources_text/<alt klasör>/<ad>` arşivden birebir kopya
(git dışı). Önce buraya bak, sonra sources_text içinde grep yap. Sayfalar basılı sayfadır, aksi yazılmadıkça.
Tam künye ve lisans: `docs/sources.md` (# numarası parantez içinde). Değer zaten bir yaml'da varsa kaynağı yeniden okuma.

## aero/

### britsch_1979_tp1523.md (#45)
- Britsch, Osborn, Laessig, NASA TP-1523, Eylül 1979. 14 ses altı orta kademe: göbek/uç 0.8, uç çapı 50.8 cm, tasarım uç hızı 243.8 m/s. Lisans: ABD hükümeti eseri.
- Kullanım: M2 referans kademesi (meanline doğrulaması A-1), DF/en-boy oranı/katılık etkileri.
- Çıkarılan: `learning/tp1523_reference.yaml` (Tablo 1, kanat tabloları 8-17 uç/orta/göbek, Tablo 2(b) DF kontrolü, uygulanabilirlik).
- Sayfalar: özet s. 1; tasarım ve katılık tanımı (uç yarıçapında) s. 3; sembol listesi s. 11-12; denklemler Ek B s. 13-15 (B4 metinde görüntü, okunamıyor); Tablo 1 s. 19; Tablo 2-7 s. 20-37; Tablo 8-17 s. 38-47; Tablo 18 uç boşlukları s. 48; Tablo 19-32 performans.
- Metin OCR kalitesinde: Tablo 1 ve kanat tablolarında onarımlar yaml'da ham dizgiyle listelendi.

### lieblein_1953_rme53d01.md (#46)
- Lieblein, Schwenk, Broderick, NACA RM E53D01, 1953. Lisans: ABD hükümeti eseri.
- Kullanım: difüzyon faktörü tanımı ve sınırları (`rules/aero_method.md`).
- Sayfalar: özet s. 1 (kaskatta kayıp D ~0.6'ya kadar hafif artış; rotor ucunda D > ~0.45 için eleman verimi < 0.90); denklem (4) s. 7 (emme yüzeyi ayrılma ölçütü, yerel hız gradyanı); denklem (13) s. 8 (tasarım DF, hız üçgeninden); denklem (14) s. 9 (eşit eksenel hızlı 2B açı biçimi).

## engine_data/

### lolis_thesis_cranfield.md (#47)
- Lolis P., *Development of a Preliminary Weight Estimation Method for Advanced Turbofan Engines*, doktora tezi, Cranfield University, Temmuz 2014 (yıl metinde yazıyor). Lisans: © Cranfield University 2014, tüm hakları saklı.
- Kullanım: CFM56-7B27 ATLAS doğrulaması; booster yöntem varsayımları [KS] (CFM56 ölçümü DEĞİL).
- Sayfalar: Tablo 4.1 performans s. 123; Şekil 4.1 kesit s. 123; Şekil 4.2-4.3 s. 124; Tablo 4.2 ağırlık (gerçek 2405 / tahmin 2285.5 kg) s. 125; Tablo 4.3 ağırlık dağılımı (IPC = booster %7.5) s. 126; Tablo 4.10 booster tasarım girdileri (sabit göbek, giriş Mach 0.5, rotor AR 2.0, stator AR 1.2) s. 133; 3 kademeli booster metni s. 122.

### oog_issue58_cfm56_7b_guide.txt (#48)
- Aircraft Commerce, *Owner's & Operator's Guide: CFM56-7B*, Issue 58, Haziran/Temmuz 2008 (metin s. 10-34). Lisans: yayıncı telifi, beyan yok.
- Kullanım: üç kademeli LPC [KS] (s. 10).

### oog_issue58_cfm56_7b_mtce.md (#49)
- Aynı sayının bakım bölümü (s. 18-26). Lisans: yayıncı telifi, beyan yok.
- Kullanım: LLP ömürleri: booster spool 23,600 EFC, -7B27 için 22,900 EFC [KS] (s. 19-20, tablo s. 20); fan/LPC modülü LLP'leri fan diski, booster spool, fan şaftı.

## e3/ (yalnız bağlam, referans DEĞİL)

### ge_e3_cr168211.md (#50)
- GE, *Energy Efficient Engine: Integrated Core/Low Spool Design and Performance Report*, NASA CR-168211 (tarih doğrulanamadı; ICLS testi 1983). Lisans: ABD hükümeti sözleşme raporu.
- Kullanım: bağlam. E3 booster'ı çeyrek kademe (ada altında, FOD ayırıcı), CFM56-7B'nin 3 kademeli booster'ı ile karşılaştırılamaz. Sayfalar: fan göbeği ve çeyrek kademe bölüm 6.1.6 s. 260.

### davis_stearns_1985_cr168219.md (#51)
- Davis, Stearns, *Energy Efficient Engine: Flight Propulsion System Final Design and Analysis*, NASA CR-168219, Ağustos 1985. Lisans: ABD hükümeti sözleşme raporu.
- Kullanım: bağlam (FOD ayırıcı booster, düşük AR kanatlar). Referans değil.

## M0 arşivinde (kopyalanmadı)

### girao_2023_cfm56-7b_thesis (#15)
- M0 dizini: `engine/M0_engine/learning/sources/INDEX.md`; metin `engine/M0_engine/learning/sources_text/girao_2023_cfm56-7b_thesis.txt`.
- M2 için: booster 3 kademe (5B'de 4) [KS] PDF s. 36; fan çerçevesi VBV sistemini taşır, birincil akıştan ikincil akışa hava atar; çerçeve alüminyum, PDF s. 36-37; yüksek devirde VBV kapalı, PDF s. 47.
