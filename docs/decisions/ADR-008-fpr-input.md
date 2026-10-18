# ADR-008: FPR girdi; V18/V8 kuralı kaldırıldı

## Karar
- Fan basınç oranı (FPR) bir girdidir: 1.765 [KS] (Girão 2023, GasTurb tasarım noktası).
- V18/V8 = η_fan · η_LPT kuralı kalibrasyondan çıkarıldı. V18/V8 yalnızca bilgi olarak raporlanır.
- Kalibrasyonda bilinmeyenler W2 ve T4, hedefler ise itki ve yakıt debisidir.
- Bileşen verimleri, basınç kayıpları ve ikincil hava oranları Girão 2023'ten [KS] alınır.

## Neden
- V18/V8 = η_fan · η_LPT, seyir koşulunda özgül yakıt tüketimini en aza indiren hız oranıdır. Kalkış noktası için geçerli değildir.
- Girão'nun kalkıştaki ideal oranı 0.627'dir; kural ise yaklaşık 0.80 verir.
- Doğrudan CFM56-7B'ye ait bir FPR, genel bir optimizasyon kuralından daha güvenilir bir dayanaktır.

## Sonuç
- FPR değiştiğinde W2 ve T4 yeniden çözülür. FPR'nin kendisi artık çıktı değildir.
- `results.yaml` içinde V18/V8, Girão 0.627 ve η_fan · η_LPT ile birlikte bilgi kontrolü olarak gösterilir.
