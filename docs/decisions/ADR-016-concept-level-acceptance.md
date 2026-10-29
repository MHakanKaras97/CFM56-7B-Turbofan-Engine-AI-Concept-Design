# ADR-016: Konsept seviyesinde kabul

Durum: **kabul edildi** (kullanıcı kuralı, M1 adım 4j).

## Bağlam
Konsept tasarımı bilinen sapmalar ve doğrulanamamış değerlerle ilerliyor (zayıf kaynak, [T] tahminler, model
sınırlamaları). Her açık konu kapanana kadar beklemek sonraki modülleri durdurur; kuralları gevşetmek ise sapmaları
gizler. Bir modül parçasının ne zaman "konsept için yeterli" sayılacağı tanımlı olmalı.

## Karar
Bir modül (veya modül parçası) şu dört koşulun hepsi sağlandığında **konsept seviyesinde kabul** edilir:
1. Yeniden üretilebilir aktif kayıt: `records/ACTIVE` revizyonu `core.records.reproduce` ile temiz doğrulanıyor.
2. M0 bütçe kontrolleri geçiyor (`core.budgets.check_budget`, bütçeler yalnızca `read_icd` ile).
3. Yapısal güvenlik kuralları geçiyor (modül kural kitabındaki gerilme/pay kuralları; M1 için R-AM.13/R-AM.15).
4. Bilinen her sapma ve açık konu `docs/open_issues.md`'de bir satır: modül, konu, etiket, neden kabul edildi,
   yeniden bakma tetikleyicisi.

Kurallar olduğu gibi kalır; hiçbir tolerans gevşetilmez. Kabul bir revizyon türü değildir: kayıt, bom.yaml ve
türetilmiş dosyalar değişmez. Kabul durumu status.md, modül `rules/index.md` ve modül REVIEW.md'de yazılır.

## Sonuçlar
- Kabul edilmiş bir parçada tetikleyici gerçekleşince satır yeniden açılır; değişiklik yeni revizyon (ve gerekirse
  CR + kullanıcı onayı) ile yapılır. Yeni revizyon dört koşulu yeniden sağlamalıdır.
- Kabul kapsamı açıkça yazılır (ör. M1'de yalnız fan kanadı); başlamamış parçalar kabul edilmiş sayılmaz.
- İlk uygulama: M1 fan kanadı, rev011. Disk, kasa, OGV ve çerçeve başlamadı.
