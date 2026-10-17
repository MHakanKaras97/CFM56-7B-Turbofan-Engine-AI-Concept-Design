# ADR-005: Referans motor

## Karar
Referans, temel CFM56-7B27'dir (SAC, ICAO satırı UID 3CM034). Tech Insertion (/3) daha sonra bir revizyon senaryosu olarak ele alınır.

## Neden
Tek ve tutarlı bir veri seti (TCDS itkisi + tek ICAO satırı) kalibrasyonu belirsizlikten korur.

## Sonuç
Çevrim girdileri 3CM034 satırından okunur; /3 değerleri yalnızca ayrı bir M0 revizyonunda kullanılır.
