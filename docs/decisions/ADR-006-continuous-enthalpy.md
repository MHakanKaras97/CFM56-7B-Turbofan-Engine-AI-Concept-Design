# ADR-006: Gaz bölgeleri arasında sürekli entalpi

## Karar
Entalpi, soğuk ve sıcak gaz bölgeleri arasında sürekli olmalıdır. Ara çözüm: h_hot(T) = h_cold(T3) + cp_hot·(T − T3). Planlanan v3: NASA Glenn polinomlarıyla (kamu malı) değişken cp(T, FAR).

## Neden
h = cp·T tanımında cp sıçraması, yakıt enerjisinin yaklaşık %10'unu kaybettiriyor ve soğutma havasını gerçekte olduğundan soğuk gibi karıştırıyordu (rev001 ve ilk v2 denemesi).

## Sonuç
Yanma odası ve karışım hesapları T3 referanslı entalpiyle yapılır; rev001 geçersiz sayılır (records/REVIEW.md).
