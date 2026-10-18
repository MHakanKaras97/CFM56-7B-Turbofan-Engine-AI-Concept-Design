# Kaynaklar

Kural: alıntı veya şekil kopyalanmaz; yalnızca faktler kullanılır, kendi cümlelerimizle özetlenir.
İndirilen dosyalar `engine/*/learning/sources/` altında tutulur ve git'e girmez.

| # | Kaynak | Kullanım | Lisans |
|---|---|---|---|
| 1 | EASA, *Type-Certificate Data Sheet No. E.004, CFM International CFM56-7B series engines*, Issue 07, 9 Ocak 2023. https://www.easa.europa.eu/en/downloads/7795/en | Kalkış ve maksimum sürekli itki | faktler, kendi cümlelerimizle |
| 2 | ICAO Aircraft Engine Emissions Databank, EASA, v32 (03/2026), dosya `edb-emissions-databank_v32__web_.xlsx`. https://www.easa.europa.eu/en/domains/environment/icao-aircraft-engine-emissions-databank | OPR, BPR, nominal itki, LTO yakıt debileri; SFC hesabı | faktler, kendi cümlelerimizle |
| 3 | Lopez-Pintor D., MacDonald J., Ramirez-Correa E., Garcia-Oliver J.M., Payri R., Marti Gomez-Aldaravi P., Leyland P., "Fuel Effects on Aviation Engine Emissions: A Chemical Reactor Network Modeling Study", *Energy & Fuels* 40(9), 4777-4792, 2026. DOI 10.1021/acs.energyfuels.5c05727 (PMC12969266) | -7B27/B1F kalkışta yanma odası hava ve yakıt debisi | CC BY 4.0; faktler, kendi cümlelerimizle |
| 4 | Turan Ö., Karakoç T.H., *Havacılık ve Uzay Teknolojileri Dergisi* 4(2), 67-76, 2009. | Turan değerleri: OPR 32.8 (geçersiz sayıldı), SFC 10.63 (yalnızca çapraz kontrol, doğrulanamadı); 4 ve 5 arasındaki dağılım teyit edilecek | faktler, kendi cümlelerimizle |
| 5 | Turan O., "Exergo-economic analysis of a CFM56-7B turbofan engine", *Energy* 259, 124936, 2022. DOI 10.1016/j.energy.2022.124936 | Bkz. 4; bu yayının özetinde SFC değeri yok | faktler, kendi cümlelerimizle |
| 6 | Indriyati, 2024, *JNEST* 3(3). DOI 10.56741/jnest.v3i03.543 | 7B test istasyonu sıcaklık/basınçları, debiler | faktler, kendi cümlelerimizle |
| 7 | Kalkan, 2024, *Konya Journal of Engineering Sciences*. DOI 10.36306/konjes.1332160 | CFM56-5A3 FPR, OPR, BPR (karşılaştırma) | faktler, kendi cümlelerimizle |
| 8 | Kuropatwa, 2022. DOI 10.37105/sd.186 | Yalnızca makullük aralıkları: BPR 5.0-6.8, OPR 21-33, kalkış TSFC 0.32-0.39 lb/(lbf·h) | CC BY 4.0 |
| 9 | Yadav et al., ASME Turbo Expo, GT2005-68244, 2005. | Referans | faktler, kendi cümlelerimizle |
| 10 | Grönstedt T., Kyprianidis K.G., ASME Turbo Expo, GT2010-22519, 2010. | Referans | faktler, kendi cümlelerimizle |
| 11 | Müller et al., ISROMAC 2017. | Referans | faktler, kendi cümlelerimizle |
| 13 | McBride B.J., Gordon S., Reno M.A., *Coefficients for Calculating Thermodynamic and Transport Properties of Individual Species*, NASA TM-4513, 1993. https://ntrs.nasa.gov/citations/19940013151 | N2, O2, Ar, CO2, H2O için 7 katsayılı cp/h/s polinomları (`tools/data/nasa_glenn.yaml`) | ABD hükümeti eseri, kamu malı |
| 14 | Cantera, `data/nasa_gas.yaml` (commit 9573e6b), https://github.com/Cantera/cantera | Kaynak 13'teki katsayıların makinece okunur kopyası; katsayılar buradan kodla aktarıldı | BSD-3-Clause (dosya); veriler kamu malı |
| 15 | Girão B.P., *Development of a Prediction Model for the CFM56-7B Engine*, yüksek lisans tezi, Universidade da Beira Interior (UBI), 2023. | M0 v4 birincil kaynağı: Şekil 4.9-4.10 (GasTurb tasarım noktası, standart güne düzeltilmiş test hücresi verisi): FPR, basınç oranları/kayıpları, izentropik verimler, lüle katsayıları, ikincil hava, EGT formülü, doğrulama noktası ve ara istasyonlar, devir sayıları; Bölüm 3: modül bilgileri (`docs/learning/cfm56_7b_module_facts.md`) | faktler, kendi cümlelerimizle |
| 16 | Yılmaz İ., *Proc. IMechE Part G*, 2009. DOI 10.1243/09544100JAERO474 | Yalnızca FN, N1, N2, PS3/P2 (birimler tutarsız); kalkış N1/N2 ortalamaları M8 bilgi referansı | faktler, kendi cümlelerimizle |
| 17 | Guynn M.D. vd., NASA/TM-2009-215784, 2009. | Yalnızca ileri teknoloji sınırları | ABD hükümeti eseri, kamu malı |
| 18 | Yang vd., *Chinese Journal of Aeronautics* 36(1), 2023. DOI 10.1016/j.cja.2022.06.018 | AGTF30 ikincil hava sistemi: kalkışta toplam soğutma yaklaşık %17 (karşılaştırma) | CC BY-NC-ND 4.0; faktler, kendi cümlelerimizle |
| 21 | He, 2025, *Case Studies in Thermal Engineering*. DOI 10.1016/j.csite.2025.106616 | Henüz kullanılmadı | CC BY 4.0 |
| 19 | Bennett vd., NASA; büyük olasılıkla AIAA SciTech 2024 (doğrulanmadı). | HPT verim kaybı: soğutma havasının her %1'i için %0.25-1.5 (tam künye tamamlanacak) | faktler, kendi cümlelerimizle |
| 20 | Lee, 2023, MIT yüksek lisans tezi. | Yalnızca kaynakça taraması | faktler, kendi cümlelerimizle |
| 12 | Martins D., *Off-Design Performance Prediction of the CFM56-3 Aircraft Engine*, genişletilmiş özet, Instituto Superior Técnico, Lizbon, 2015. | Kalibrasyon yöntemi (Kurzke yaklaşımı); EGT formu; verim kaybı başına EGT artışı (yalnızca büyüklük karşılaştırması, `rules/martins_2015.yaml`); motor CFM56-3 | faktler, kendi cümlelerimizle |
