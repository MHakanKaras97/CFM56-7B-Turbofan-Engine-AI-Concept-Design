# ADR-010: Entegrasyon kontrolünün sınırı

## Karar
- M0 entegrasyon kontrolü bir tasarım noktası yeniden dengelemesidir: lüle alanları ve türbin kapasiteleri serbesttir. Sabit geometrili bir tasarım dışı (off-design) hesap değildir.
- Ara çözüm: entegrasyon EGT toleransı 10 K'den 5 K'e indirildi [T]. Değer `analysis/icd.py` içinde tanımlı; `rules/icd.yaml` yeniden üretildi.
- Kalıcı çözüm M0 v2 olacak: sabit A8, A18 ve HPT NGV kapasitesiyle, bileşen haritaları kullanan bir off-design modeli. Bu model seyir noktası için de gerekli.

## Neden
- Gerçek motorda bir bileşenin verimi düşerse geometri değişmez. Çalışma noktası kayar; HPT NGV ve lüle boğazları debiyi sınırlar, bu da T4 ve EGT'yi daha çok yükseltir.
- Bizim kontrolde itki ve W2 sabit tutuluyor, alanlar serbest; çevrim kendini yeniden dengeliyor. Bu yüzden EGT duyarlılığı düşük çıkıyor.
- Karşılaştırma (verim 1 puan düşük, ΔEGT, model / Martins 2015, CFM56-3): HPC 4.3/8 K, HPT 5.3/12 K, yani çekirdek bileşenlerinde yaklaşık yarısı. Fan 3.1/4 K ve LPT 5.5/6 K'de yakın; booster 1.9/3 K (`analysis/acceptance_M0.md`).
- Toleransı yarıya indirmek, çekirdek bileşen etkisinin yaklaşık yarısının görülmemesini kabaca dengeler. Bu bir kalibrasyon değil, geçici bir güvenlik payıdır.

## Sonuç
- Çekirdek modülleri (M3, M5) için EGT sonuçları iyimser kabul edilir. Sınıra yakın sonuçlar kullanıcıya işaretlenir.
- SFC toleransı (±%0.5) ve modül bütçe toleransları değişmedi.
- M0 v2 (off-design) yol haritasına eklendi. Geldiğinde entegrasyon kontrolü sabit geometriyle yapılacak ve bu ADR'nin yerini alacak.
