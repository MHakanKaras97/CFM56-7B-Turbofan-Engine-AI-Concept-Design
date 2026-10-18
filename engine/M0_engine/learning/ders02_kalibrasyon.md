# Ders 02: Kalibrasyon (M0 v1 → rev005)

Bu ders, M0 çevriminin altı adımda nasıl düzeldiğini ve her adımın ne öğrettiğini anlatır. Sayılar kayıtlardan alındı (`records/REVIEW.md`, `status.md`).

## 1. Fan boğulma sınırı (v1, rev001)
- Ne oldu: İtki ve yakıt hedefleri tuttu, ama W2 = 447 kg/s çıktı. Fan alanına bölünce W2/A = 260.5 kg/(s·m²) oldu. SLS koşulunda fiziksel üst sınır, yani M = 1'deki kütle akısı, yaklaşık 241'dir.
- Ders: Hedeflerin tutması sonucu doğrulamaz. Eksik bir model hedefleri yanlış parametrelerle de tutturabilir.
- Sonuç: Fan boğulma sınırı sert (HARD) kural oldu. Bu kontrolden geçmeyen sonuç için revizyon oluşturulmaz.

## 2. Entalpi hatası (v2, ADR-006)
- Ne oldu: Soğuk bölgede cp = 1005, sıcak bölgede cp = 1150 alınmıştı ve h = cp·T kullanılıyordu. Yanma odasında cp sıçrayınca entalpi de sıçradı. Yakıt enerjisinin yaklaşık %10'u kayboldu ve soğutma havası olduğundan soğuk karıştı.
- Ders: Entalpi tek ve sürekli bir fonksiyon olmalı. Referans noktası (T_ref) her yerde aynı olmalı.
- Sonuç: Önce ara çözüm, sonra v3'te NASA polinomlarıyla değişken cp(T, FAR). Entalpi 298.15 K'e (LHV referansı) göre tanımlandı.

## 3. Hedef mi, kontrol mü? (v3, ADR-007)
- Ne oldu: Lopez-Pintor'un 44.52 kg/s yanma odası havası hedef yapılmıştı. Model buna uymak için soğutma oranını 0.26-0.35'e, T4'ü 1860 K'e itti.
- Ders: Bir kaynaktaki sayı ölçüm değil de başka bir modelin girdisiyse ve tanımı belirsizse, hedef değil kontrol olmalı. Hedefler en güvenilir verilerden seçilir: TCDS itkisi, ICAO yakıt debisi.
- Benzer bir durum: V18/V8 = η_fan·η_LPT kuralı seyir için geçerli bir optimum; kalkışta kullanılmaz (ADR-008).

## 4. GasTurb'e karşı doğrulama (v4, Girão)
- Ne oldu: Girão'nun girdileriyle ilk denemede 9 kalemin 7'si kaldı. Neden, Girão'dan gelmeyen varsayımlardı: lüle cv 0.98, LHV 43.0, 100 kW güç çekişi. Şekil 4.9'daki gerçek değerler (lüle itki ve debi katsayıları, çekiş 0), iç fan + booster ayrımı ve HPC ara kademe kaçağı eklenince 19 kalemin 18'i geçti.
- Kalan fark: %1'i aşan ilk istasyon T4. Fark yanma odasında başlıyor; sıcak gaz modeli ve yakıt tanımı GasTurb'den farklı. P5 +%3.46 beklenen hata olarak kabul edildi.
- Ders: Doğrulamayı geçirmek için girdiler ayarlanmaz. Sapma, gaz yolu sırasıyla izlenir ve %1'i aşan ilk istasyon nedeni gösterir. Bilinmeyen bir girdi [T] olarak açıkça işaretlenir.

## 5. Benzerlik koşulu (rev004 → rev005, ADR-009)
- Ne oldu: ICAO noktasında iki hedefle (itki, yakıt) Δη = 0 çözüldü (rev004). Ama çözüm itki tavanına yalnızca %1.2 uzaktaydı ve ideal V18/V8 0.849'du. Bu oran ailenin kalkış değerinin (yaklaşık 0.60) çok üstünde, yani çekirdek jeti fazla yavaştı.
- Çözüm: Üçüncü hedef olarak Girão noktasındaki ideal V18/V8 (0.6036) kullanıldı. Aynı aile ve aynı kalkış koşulu olduğu için benzerlik varsayımı yapıldı [T]. Sonuç Δη = 0.0171; itki tavanına pay %7.8, tüm kontroller geçiyor.
- Ders: İki hedef yalnızca bir eğri tanımlar; eğrinin hangi dalında olunduğunu söylemez. Fiziksel anlamı olan bir oran (jet hız oranı) dalı seçer.

## 6. Belirsizlik bandı
- Δη'yı yalnız kompresörlere, yalnız türbinlere ya da hepsine eşit uygulamak, aynı üç hedefle T4'ü yaklaşık 23 K değiştiriyor (1659-1682 K). W2 ve EGT ise neredeyse sabit kalıyor (sırasıyla yaklaşık 1 kg/s ve 3 K).
- Ders: Kalibre edilmiş bir T4 tek bir sayı değil, bir banttır. Modül bütçeleri bu bandı akılda tutarak okunmalı.

## Özet: her adımın kazandırdığı
| Adım | Kazanılan kural |
|---|---|
| v1 | Fiziksel sınır kontrolü (HARD) |
| v2 | Sürekli entalpi, tek referans |
| v3 | Hedef ile kontrol ayrımı |
| v4 | Bağımsız modele karşı doğrulama, ilk sapma noktası |
| rev005 | Benzerlik koşulu ile dal seçimi |
