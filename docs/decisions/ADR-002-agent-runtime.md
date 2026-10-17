# ADR-002: Agent çalışma ortamı

## Karar
Agent'lar Claude Code oturumları olarak çalışır: M0 ana oturum, M1-M9 subagent. Uygulama içinde API çağrısı yapılmaz.

## Neden
Ek bağımlılık ve API anahtarı yönetimi olmadan, dosya tabanlı ve izlenebilir bir çalışma düzeni.

## Sonuç
Uygulama kodu LLM'e bağımlı olmaz; tüm durum dosyalarda tutulur.
