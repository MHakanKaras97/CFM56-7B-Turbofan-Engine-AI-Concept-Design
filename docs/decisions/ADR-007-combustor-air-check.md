# ADR-007: Yanma odası havası (44.52 kg/s) hedef değil, kontrol

## Karar
Lopez-Pintor vd. (2026) kaynağındaki 44.52 kg/s yanma odası havası kalibrasyon hedefi olmaktan çıkarılır ve yalnızca bilgi amaçlı bir kontrol olarak raporlanır. Bunun yerine toplam soğutma oranı bir girdi olur: nominal değer 0.18 [G], duyarlılık için 0.14-0.22 aralığı taranır. Kalibrasyonda W2, T4 ve FPR bilinmeyendir; itki, yakıt debisi ve V18/V8 kuralı hedeftir.

## Neden
- 44.52 kg/s ölçülmüş bir değer değil, kaynaktaki reaktör ağı modelinin bir girdisi. Hangi akışları kapsadığı belli değil; liner soğutma havasını büyük olasılıkla içeriyor.
- Hedef olarak kullanıldığında çözüm fizik dışı uçlara itiliyor. Sabit cp ile (rev002) sonuç T4 ≈ 1860 K, FPR 1.83 ve soğutma oranı 0.26 idi. Değişken cp ile (v3 karşılaştırması) soğutma 0.35'e çıkıyor ve W2/A fan boğulma sınırına yaklaşıyor.
- Soğutma oranı için genel mühendislik aralığı (0.12-0.22 [G]), tanımı belirsiz tek bir debiden daha güvenilir bir dayanak.

## Sonuç
- M0 v3 (rev003) soğutma oranını 0.18 alır. 44.52 kg/s ile model arasındaki fark `results.yaml` içinde "Combustor air vs Lopez-Pintor" kontrolünde görülür.
- Eski kurgu (44.52 hedef, soğutma çözülür) karşılaştırma için `comparison_combustor_air_target` bölümünde tutulur.
- Soğutma oranı kontrolü artık yalnızca girdinin aralıkta olduğunu doğrular.
