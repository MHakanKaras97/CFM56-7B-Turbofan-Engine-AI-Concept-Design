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

## 2026-10-27 Criteria: chord roughness, derived t/c range, margin wording (M1 step 4i, R-AM.16/17, R-AM.13/15)
- R-AM.17 redefined: roughness, not total curvature. Metric = largest |c/c_mean - q(f)| over the span stations, q = least-squares
  quadratic of c/c_mean (plain quadratic -> 0, local bump -> high). Replaces the step 4h second-difference metric (limit 1.2685 retired).
- Limit: 0.003880 [H from KS] = same metric on the 14 Rotor 67 Table I sections (chord rotor67_geometry.yaml, span = LE radius
  fraction, c_mean 9.3138 cm); largest at section 6 (span 0.385); RMS 0.001975 (information).
- R-AM.16: area is its own non-increasing law (taper 0.3-0.5), chord quadratic from aero rules, t/c = A / (k c^2) derived.
  Check ranges [H from KS] = min-max of Rotor 67 section t/c (blade_profile.rotor67_tc_benchmark) per span third:
  hub [0, 1/3] sections 1-5: 0.07147-0.08513; mid [1/3, 2/3] sections 6-9: 0.04567-0.06531; tip [2/3, 1] sections 10-14: 0.02979-0.03999.
- R-AM.13/15 wording: steady centrifugal stress <= half the allowable (yield / 1.5), headroom for vibratory and bending stress [T],
  every section. Same number as margin >= 1.0; wording only.
- Source: Strazisar et al., NASA TP-2879 (1989), Table I via the BladeAtlas digital copy (docs/sources.md #41).

## 2026-10-28 Criteria: root chord floor and structural area level (M1 step 4i-b, R-AM.18, R-AM.16)
- R-AM.18 (new): hub solidity >= 3.11 [KS] = Rotor 67 hub solidity (rotor67_reference.yaml solidity_hub, Strazisar et al., NASA TP-2879 (1989) p. 2, docs/sources.md).
  Reason: step 4i chord from the R-AM.9 needs alone gave a 0.024 m root (extrapolated quadratic) and no reachable PR balance.
- R-AM.16 area level: from structure, not from hub t/c. A_root = smallest root area with steady stress <= half the allowable (yield / 1.5)
  at every section; linear area law, taper 0.335 (Rotor 67 [H from KS]). Replaces the step 4i anchor "derived hub t/c = 0.0851".
  Derived t/c checked per span third against the step 4i Rotor 67 ranges above (hub 0.07147-0.08513, mid 0.04567-0.06531, tip 0.02979-0.03999).
- Outer FPR 1.765 stays a requirement (budget); if unreachable the binding rule is reported, nothing relaxed.

## 2026-10-28 Tests retired and merged (M1 step 4i-b)
- Merged: engine/M1_inlet_fan/agent/proposed_test_m1_step4i.py -> tests/test_m1_step4i.py (15 code-only tests; R-AM.16/17/18, derived t/c).
- Retired from tests/test_m1_fan_design.py:
  - test_blade_mechanics_uniform_blade_matches_closed_form: blade_mechanics now takes an area-law dict, not chord coefficients x Rotor 67 t/c (replaced by the same-named test in test_m1_step4i.py).
  - test_chord_lp_meets_needs_and_taper_band: chord_constraints has no taper row and no root_chord_min (R-AM.16 area is its own law; floor = R-AM.18 `floors`).
  - test_chord_smoothness_limit_r_am17: second-difference metric and limit 1.2685 retired in step 4i (roughness 0.003880).
- Kept until results.yaml is regenerated (they read the step 4h results, still the active state): bump, area-profile, mass-diagnosis,
  chord-law-variant, monotonic-area, need-basis and stress-key tests.

## 2026-10-28 M1 step 4i-b result: no revision
- No valid design: R-AM.16 structural level is undetermined. Steady stress sigma(f) = rho omega^2 int(A r dr) / A(f) does not depend on A_root
  (it cancels; checked at 1e-4 and 1e-2 m^2). Linear law, taper 0.3352: 225.0 MPa at the root <= 366.7 MPa for every A_root > 0 [H].
- Derived t/c ratios fixed by the shape (mid/hub 0.2842, tip/hub 0.1754); hub third needs A_root 17.06-20.32 cm^2, mid 38.36-54.86, tip
  40.55-54.44: no level passes all three thirds [H]. rev010 not recorded; rev009 stays active.

## 2026-10-28 Criterion: area level on mid and tip thirds; hub t/c deviation accepted (M1 step 4i-c, R-AM.16)
- User decision: A_root = smallest value that puts derived mid and tip t/c inside the step 4i Rotor 67 ranges (mid 0.04567-0.06531,
  tip 0.02979-0.03999). Replaces the step 4i-b structural level (undetermined: stress independent of A_root).
- Known deviation (user-accepted, revisit later): hub-third t/c is reported against 0.07147-0.08513 and does not fail.
- Rationale [G]: hub subsonic-relative, structurally conservative. Arithmetic verified [H]: tip/hub t/c = taper (c_hub/c_tip)^2 with
  c ~ solidity x radius: 0.175 at M1 hub/tip 0.300 vs 0.350-0.560 needed; 0.274 at Rotor 67 hub/tip 0.375 (still outside); needs >= 0.424.
  So the radius ratio contributes but is not the whole cause; Rotor 67 Table I chords (tip/hub 0.971) do not match its published
  solidity pair 3.11/1.29 (implied 1.106).
- Open item: tip t/c at the lower bound -> bird strike and flutter.

## 2026-10-28 Tests retired and merged (M1 step 4i-c)
- Merged: proposed_test_m1_step4i_c.py -> tests/test_m1_step4i_c.py (14 tests: level rule, hub deviation status, results checks).
- Retired from tests/test_m1_step4i.py: test_structural_level_undetermined_when_shape_passes and
  test_structural_level_shape_failing_goes_to_next_order (structural level and structural_root_area removed; the stress rule is now a check,
  covered by test_stress_rule_is_a_check_that_fails_the_design).
- Retired from tests/test_m1_fan_design.py: test_blade_mass_diagnosis (step 4f/4h diagnosis structure gone), test_chord_bump_is_local_r_am14
  (bump dropped in step 4i), test_chord_law_variants_ordered (chord_law_variants removed), test_root_stress_and_mass_by_independent_quadrature
  with helper _area_profile (area = k t/c_R67 c^2 no longer the law; replaced by test_results_stress_and_mass_by_independent_quadrature),
  test_area_monotonic_r_am16_reported (step 4h feasibility branch; replaced by test_results_area_monotonic_and_taper_in_band).
- Changed: chord_at helper evaluates the plain quadratic (coefficients_m) instead of quadratic + bump.
