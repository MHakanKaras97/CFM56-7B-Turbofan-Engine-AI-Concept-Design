# ADR-001: Geometri dosyalarının saklanması

- Durum: Kabul edildi
- Tarih: 2026-10-17

## Karar
STEP, STL ve GLB dosyaları git'e eklenmez (`.gitignore` ile dışlanır).

## Revizyon kaydı
Her geometri revizyonu için `records/` altında şunlar saklanır:
- Girdi parametreleri
- Geometriyi üreten kodun commit hash'i
- Üretilen dosyanın SHA-256 özeti

## Geri dönüş
Geometri, kayıttaki commit ve parametrelerle koddan yeniden üretilir.
Üretilen dosyanın SHA-256 özeti kayıttaki özetle karşılaştırılarak doğrulanır.

## Neden
- Repo boyutu: büyük ikili CAD dosyaları geçmişi şişirir.
- Yeniden üretilebilirlik: tek doğruluk kaynağı kod ve parametrelerdir, dosya değil.
