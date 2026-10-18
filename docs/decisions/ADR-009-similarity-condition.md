# ADR-009: Nominal noktada benzerlik koşulu (V18/V8)

## Karar
- ICAO -7B27 nominal noktasında (121.43 kN, 1.284 kg/s, BPR 5.0, OPR 28.63 [K]) üçüncü kalibrasyon hedefi ideal V18/V8'dir. İdeal V18/V8, ortam basıncına kadar tam genleşmiş izentropik jet hızlarının oranıdır.
- Hedef değer, kendi modelimizin Girão doğrulama noktasında hesapladığı ideal V18/V8'dir: 0.6036 [T]. Gerekçe benzerlik varsayımı: aynı motor ailesi, aynı kalkış koşulu. Girão'nun bildirdiği değer 0.627'dir; model ile arasındaki fark −%3.7.
- Üçüncü bilinmeyen, bütün izentropik turbomakine verimlerine eklenen ortak Δη'dır. Çözüm yoksa ya da Δη > 0.03 çıkarsa yedek yol kullanılır: Δη = 0 tutulur ve FPR serbest bırakılır.
- Sonuç (rev005): Δη = 0.0171 [H], FPR 1.765 korundu. Yedek yola gerek kalmadı.

## Neden Δη = 0 (rev004) kabul edilmedi
- İki hedefle (itki, yakıt) Δη = 0 çözülüyordu, ama çözüm itki tavanına çok yakındı. Bu yakıtla ulaşılabilecek en yüksek itki 122.88 kN; hedef bu tavanın yalnızca %1.2 altındaydı. Küçük bir girdi değişikliği çözümü yok edebilir.
- İdeal V18/V8 0.849'du. Bu, aynı ailenin kalkış noktasındaki değerin (0.60-0.63) çok üstünde, yani çekirdek jeti fazla yavaş. İki hedefli kalibrasyon bu dalı ayırt edemiyor.
- W2/A 216.8 ile yumuşak bandın (190-215) dışındaydı.
- Benzerlik koşuluyla itki tavanına pay %7.8'e çıkıyor (130.91 kN), W2/A 201.3 oluyor ve tüm kontroller geçiyor.

## Sonuç
- `cycle.py` önce Girão noktasındaki ideal V18/V8'i hesaplar, ardından nominal noktayı üç hedefle çözer. Δη taraması (0-0.03) yalnızca bilgi tablosu olarak kalır ve V18/V8 sütununu içerir.
- Bilgi: yedek yol (Δη = 0, FPR serbest) FPR 1.612, W2 381.7 kg/s, T4 1608.3 K verir [H]. Bu sonuç kullanılmadı.
- Gerçek verimlerin Girão değerlerinden bu kadar yüksek olması (+0.017) sınanmamış bir varsayımdır. Girão noktasındaki SFC ile ICAO SFC'si arasındaki farkı (yaklaşık %5) bu Δη kapatıyor.
