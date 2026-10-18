# ADR-011: Revizyonda kesit görünümü (section.svg)

- Durum: Kabul edildi
- Tarih: 2026-10-18
- İlişki: ADR-001'i değiştirir (geometri saklama)

## Karar
- Geometri üreten her modül revizyonu, `records/revNNN/` altında küçük bir kesit görünümü (`section.svg`) saklar. Dosya metin olduğu için git'e girer ve manifestteki `outputs` listesinde SHA-256 özetiyle yer alır.
- GLB ve STEP git dışında kalır (ADR-001). Yerel önbellekte tutulur ve gerektiğinde, revizyonun `code_commit` ve parametrelerinden yeniden üretilir.

## Neden
- Arayüz, revizyonlar arası karşılaştırmayı ("A → B": eskisi kesikli gri, yenisi renkli) anında göstermeli. Bunun için her revizyonun kesitini yeniden üretmek gerekmesin.
- SVG küçük ve metin tabanlı; git farkı okunabilir ve depoyu şişirmez.
- 3B görünüm (GLB) ve Fusion için STEP ise büyük ikili dosyalar; bunlar için ADR-001 geçerli kalır.

## Sonuç
- `section.svg` modülün `geometry/` kodu tarafından üretilir, elle düzenlenmez (türetilmiş dosya).
- Önbellek konumu: `.cache/geometry/<modül>/<rev>/` (git dışı). Önbellekte yoksa arayüz dosyayı `code_commit` ile yeniden üretir ve SHA-256 değerini kayıtla karşılaştırır.
- Kavramsal düzen referansı (`docs/design/engine_reference.svg`) da aynı ilkeyle koddan üretilir (`tools/reference.py`).
