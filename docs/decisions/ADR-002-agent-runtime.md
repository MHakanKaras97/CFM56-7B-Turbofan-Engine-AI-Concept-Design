# ADR-002: Agent çalışma ortamı

## Karar
Agent'lar Claude Code oturumları olarak çalışır: M0 ana oturum, M1-M9 subagent. Uygulama içinde API çağrısı yapılmaz.

## Neden
Ek bağımlılık ve API anahtarı yönetimi olmadan, dosya tabanlı ve izlenebilir bir çalışma düzeni.

## Sonuç
Uygulama kodu LLM'e bağımlı olmaz; tüm durum dosyalarda tutulur.

## Subagent tanımı (2026-10-25)
- Biçim: `.claude/agents/<ad>.md`; YAML ön bilgi (`name`, `description` zorunlu; `tools`, `model` vb. isteğe bağlı), gövde sistem istemidir. Kaynak: Claude Code belgeleri, https://code.claude.com/docs/en/sub-agents (2026-10-25'te okundu).
- İlk modül agent'ı: `.claude/agents/m1-inlet-fan.md`.
- Yeni `.claude/agents/` klasörü oturum başında yoksa izlenmez; ilk dosyadan sonra Claude Code yeniden başlatılmalı (aynı belge).

## Subagent'lar başka subagent başlatabilir mi?
- Belgeye göre evet: varsayılan olarak bir subagent kendi subagent'larını başlatabilir, ana konuşmanın en fazla üç katman altına kadar. Sınır `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` ile ayarlanır; `1` iç içe başlatmayı kapatır.
- Tek bir subagent'ı engellemek için `Agent` aracı `tools` listesinden çıkarılır veya `disallowedTools` içine yazılır.
- Karar: modül agent'larının `tools` listesinde `Agent` yok. Koordinasyon yalnızca M0'dan geçer; bir modül agent'ı başka modül agent'ı başlatmaz.
- Yazma yolu kısıtı için ön bilgi alanı yok; belge bunun için `PreToolUse` kancası öneriyor. Şimdilik kural sistem isteminde (yalnızca `engine/M1_inlet_fan/` altına yazar); kanca ile zorlamak kullanıcı kararıdır.
