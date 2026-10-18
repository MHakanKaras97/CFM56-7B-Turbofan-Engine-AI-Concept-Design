# M0 Revision Review Log

Append-only. Never edit or delete entries; add a new entry instead.

## 2026-10-18 rev001
rev001 invalid: enthalpy reference bug + choke violation.
- Enthalpy h = cp*T with a cp jump at the burner (fixed by ADR-006).
- W2/A = 260.5 kg/(s m2) exceeds the SLS fan choke limit 241.3 (HARD rule, review_criteria.md).

## 2026-10-18 rev002
rev002 superseded by rev003 (not invalid).
- Combustor air 44.52 kg/s is a check, not a target (ADR-007); rev002 used it as a target.
- Constant cp (cold 1005, hot 1150 J/(kg K)) replaced by variable cp(T, FAR) from NASA polynomials.
- With variable cp the rev002 setup gives cooling 0.352 and W2/A 240.2, near the choke limit 241.3.

## 2026-10-18 rev003
rev003 superseded by the v4 inputs (ADR-008, Girão 2023); it stays ACTIVE because no rev004 exists.
- v4 rated case (121.43 kN, 1.284 kg/s) is infeasible with the Girão component inputs: max thrust 118.0 kN at that fuel flow.
- v4 validation against Girão fails 7 of 9 items (W2 +8.2 %, P5 -14.5 %); see docs/status.md.

## 2026-10-18 rev003 (update)
rev003 superseded by rev004 (cycle v4.1, Girão 2023 inputs, ICAO -7B27 rating).
- Combustor-air and cooling assumptions of rev003 replaced by Girão secondary air (0.13 of W25).
- Validation against Girão: 18 of 19 items pass; P5 +3.46 % accepted (engine/M0_engine/analysis/validation_girao.md).
- rev004 soft-check deviation: W2/A 216.8 > 215 (fan geometry is [T]); explained, user decision open.
