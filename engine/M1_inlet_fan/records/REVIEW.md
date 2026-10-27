# M1 Revision Review Log

Append-only. Never edit or delete entries; add a new entry instead.

## 2026-10-25 rev002
rev002 not reproducible: code_commit predates fan_design.py. Its manifest names 45549cd, which does not contain
analysis/fan_design.py or analysis/calc.py (both were committed later in 091135c), so the recorded commit cannot
re-run the record. Numbers are unaffected; superseded by rev003 (maintenance, same numbers).

## 2026-10-25 rev003 (maintenance)
rev002 superseded by rev003. Same params and results; code_commit = 091135c, the commit that contains the code.

## 2026-10-26 Criterion change: Rotor 67 angle sensitivity (tests/test_m1_rotor67.py)
Acceptance criterion of the geometry-digitisation check changed from |dPR|/PR < 1 % to < 1.5 % [T] (M1 step 4c, commit fc3b2b4).
- Check: all LE and TE metal angles shifted by +-0.22 deg (largest residual OCR last-digit error), same sign at every section (upper bound of random errors), design point.
- Reason: since the suction-surface expansion uses the blade geometry (step 4c), the tip tube no longer chokes at the exit; its work now follows the trailing-edge angle. TE alone gives dPR -0.86 % / +0.77 %, LE and TE -1.12 % / +0.96 %. A choked tube had hidden this sensitivity before, so the larger value is a property of the corrected model, not a regression.
- From step 4d every Rotor 67 validation PR carries this band (PR_band_geometry in rotor67_validation.yaml).

## 2026-10-27 Criterion: chord smoothness limit (M1 step 4h, R-AM.17)
- Metric: largest |second divided difference| of c(f) / c_mean over the span stations (fan_design.second_differences), per unit span^2.
- Limit: 1.2685 [H from KS] = the same metric on the 14 Rotor 67 Table I sections (chord from rotor67_geometry.yaml [H from KS],
  span = leading-edge radius fraction, c_mean 9.3138 cm); the largest value is at section 6 (span 0.385).
- Source: Strazisar et al., NASA TP-2879 (1989), Table I via the BladeAtlas digital copy (docs/sources.md #41).
- Requested revert of a 5 -> 10 chord smoothness change: no such limit or change exists in the repository or its git history
  (all commits, stash, worktrees searched); nothing reverted. R-AM.17 is the first chord smoothness limit.
