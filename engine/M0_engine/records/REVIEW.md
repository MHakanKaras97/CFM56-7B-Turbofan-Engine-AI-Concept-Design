# M0 Revision Review Log

Append-only. Never edit or delete entries; add a new entry instead.

## 2026-10-18 rev001
rev001 invalid: enthalpy reference bug + choke violation.
- Enthalpy h = cp*T with a cp jump at the burner (fixed by ADR-006).
- W2/A = 260.5 kg/(s m2) exceeds the SLS fan choke limit 241.3 (HARD rule, review_criteria.md).
