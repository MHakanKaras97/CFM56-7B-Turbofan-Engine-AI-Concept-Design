# ADR-012: Revizyon türleri

## Karar
- **Tasarım revizyonu (design):** sayılar, params değerleri veya geometri değişir. Kabul edilmiş bir modülde onaylanmış bir CR ve kullanıcı onayı gerekir.
- **Bakım revizyonu (maintenance):** yalnızca şema, üst veri veya metin değişir. CR gerekmez. Ana revizyona göre farkta (`core.diff.numeric_changes`) sayısal değişiklik olmamalı ve `records/REVIEW.md` dosyasına bir kayıt eklenir.
- **Kabulden önce** bir modülün kendi revizyonları CR gerektirmez.
- Kabul, `engine/<M>/records/ACCEPTED` dosyasıyla işaretlenir; dosya kabul edilen revizyonu adlandırır (`core.records.mark_accepted`). M0, v1 kabul listesiyle rev005'te kabul edildi.

## Uygulama (core)
- `core.records.create_revision(..., kind="design" | "maintenance")`. Manifestte `revision_type` alanı tutulur (ADR-012 öncesi revizyonlarda yoktur; sınıflandırmaları REVIEW.md'dedir).
- Kabul edilmiş modülde CR'siz tasarım revizyonu reddedilir. `core.requests.apply` tasarım revizyonunu CR ile oluşturur.
- Bakım revizyonu CR almaz ve kayıt yazılmadan önce ana revizyonla karşılaştırılır. Şunlardan biri varsa reddedilir:
  - params, results veya BOM'da değişen ya da silinen bir sayı,
  - eklenen veya silinen parça,
  - değişen çıktı SHA-256 değeri (geometri).
- Sayılmayanlar: metin, yeni eklenen anahtarlar (şema veya üst veri eklemesi) ve params içinde aynı değerle başka bir yola taşınan sayı. Taşınan sayı farkta `moved` olarak raporlanır.
- Her `moved` girdisi için modülün `records/REVIEW.md` dosyasında revizyondan **önce** `eski.yol -> yeni.yol` satırı bulunmalı (ör. `checks.w2_ref.tolerance -> checks.w2_tolerance.value`); yoksa bakım revizyonu reddedilir.
- Kod, eski kayıtların params biçimini okumaya devam eder (ör. rev007 öncesi `w2_ref.tolerance`), böylece eski kayıtlar yeniden çalıştırılabilir kalır.
- Kimlik anahtarı olan listeler (`id`, `station`, `name`, `path`) öğe bazında karşılaştırılır; böylece bir notun değişmesi sayısal değişiklik sayılmaz.

## Neden
- rev006 yalnızca alan ekledi (varsayımlar, `ref_tag`); sayılar aynıydı. Böyle değişiklikler için CR süreci gereksiz ağırlık, ama "sayı değişmedi" iddiası kodla doğrulanmalı.
- Kabul edilmiş bir modülde sayı değişikliği diğer modülleri etkileyebilir (ICD); bu yüzden CR ve kullanıcı onayı şart.

## Sonuç
- rev001-rev006 geriye dönük olarak REVIEW.md'de sınıflandırıldı. rev007 ilk bakım revizyonudur (params notları tırnaklandı, W2 toleransı ayrı bir büyüklük oldu).
- Params dosyaları `core/schemas/params.schema.json` ile doğrulanır: bir büyüklük girdisi yalnızca value, unit, tag, note, source anahtarlarını taşıyabilir.
