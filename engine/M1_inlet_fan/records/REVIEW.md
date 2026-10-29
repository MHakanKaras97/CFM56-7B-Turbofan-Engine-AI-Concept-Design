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

## 2026-10-29 Criterion: solidity definition (M1 step 4i-e, R-AM.18, R-AM.9 supersonic floor)
- Definition: solidity = true chord / pitch at the section mean radius (LE + TE)/2. Rotor 67 3.11 / 1.29 [KS] (TP-2879 p. 2, 22 blades);
  the definition is not stated in the paper, inferred from Table I (3.116 / 1.285) [H from KS]. M1 applies it with 24 blades.
- Before (rev010): pitch at the inlet hub radius (floor) and at the tube inlet radius (supersonic needs); by the paper's definition the
  rev010 hub solidity is 2.70, not 3.11.
- Retracted: step 4i-c entry "Rotor 67 Table I chords (tip/hub 0.971) do not match its published solidity pair (implied 1.106)".
  The 1.106 used the inlet hub/tip ratio; with mean section radii the pair gives 0.977, consistent with Table I.
- Kept: hub-third t/c known deviation (user-accepted), step 4i-c area level (smallest A_root with mid and tip t/c in range).
- Step 4i-d what-if (scratch, floor only): hub chord 0.1892 -> 0.2176 m, A_root 40.55 -> 42.21 cm^2, hub t/c 0.170 -> 0.134, 6.77 kg/blade.

## 2026-10-29 M1 step 4i-e result: no revision
- No valid design with the solidity definition applied to both R-AM.18 and the supersonic R-AM.9 floor: the stream PR balance stalls in
  pass 1 (PR error inner -1.46e-4, outer -1.04e-4, tolerance 2e-5); offset scan finds no better point; nothing relaxed. rev010 stays active.
- Diagnostic (scratch, same code, supersonic needs back on the tube inlet pitch, floor on the hub mean radius): converges, FPR 1.765004,
  chord 0.2176 / 0.2669 m, A_root 42.21 cm^2, t/c hub 0.134 / tip 0.0298. So the binding change is the supersonic need on the tube mean
  pitch (tip chord 0.267 -> 0.254 m in pass 1), not the hub floor [H].

## 2026-10-29 Criterion: supersonic R-AM.9 floor on inlet pitch (M1 step 4i-f)
- User decision: the supersonic floor (Rotor 67 solidity 3.11 -> 1.29 [KS] at the same span) stays on the tube inlet pitch; R-AM.18 hub
  floor stays on the section mean-radius pitch (step 4i-e).
- Known deviation: conservative on most tubes; 1.8 % below Rotor 67 on tube 5 (expanding tube) by the paper's definition; user-accepted, revisit with M0 v2
  (tip tube about 2.6 % above). Not a definition match; supersedes the step 4i-e R-AM.9 bullet.
- Evidence: mean-radius pitch for the supersonic floor -> PR balance stalls in pass 1 (outer -1.46e-4, inner -1.04e-4 vs 2e-5; step 4i-e).
- Unchanged: balance tolerance, exit hub ratio 1.30 [T]; no PR-reachability chord rule.

## 2026-10-29 M1 step 4i-f result: valid design, no revision
- Supersonic R-AM.9 floor on the tube inlet pitch (known deviation, see label above), R-AM.18 on the hub mean-radius pitch:
  converged, FPR 1.7650, pr_inner 1.3440, R-AM.9 9/9, hub / tip solidity (paper definition) 3.110 / 1.350, chord 0.2176 / 0.2669 m,
  A_root 42.21 cm^2, t/c hub 0.134 (known deviation) / mid 0.0495 / tip 0.0298, 225.0 MPa at the root, 6.769 kg per blade [H].
- By the paper definition the floor is above Rotor 67 on contracting tubes (tip +2.6 %) and below it on tube 5 (r2 > r1, -1.8 %): label as
  above, user-accepted, revisit with M0 v2.
- Stall diagnosis (scratch): with the mean-radius pitch for the supersonic floor the outer PR maximum on the inner-balanced physical
  branch is about 2.2e-4 short of 1.765 (true infeasibility, not solver noise or a max() kink). The step 4i-e stall errors are
  outer -1.46e-4 / inner -1.04e-4 (logged order [outer, inner]); the inner/outer labels in the entries above are swapped.

## 2026-10-29 Tests merged and retired; label correction (M1 step 4i-f, M0)
- Merged: proposed_test_m1_step4i_e.py -> tests/test_m1_step4i_e.py (definition, floor on hub r_mean, supersonic floor on inlet pitch,
  paper-definition solidity, results checks).
- Retired: tests/test_m1_step4i.py::test_rotor67_solidity_need_quadratic_meets_floor (held only while floor and needs both used the inlet
  hub radius); replaced by test_rotor67_inlet_pitch_needs_below_mean_radius_floor.
- Changed: test_m1_step4i.py _ctx (blade-edge radii) and R-AM.18 floor test (mean-radius pitch); test_m1_step4i_c.py hub solidity on the
  mean-radius pitch; test_m1_fan_design.py supersonic check on solidity_inlet_pitch_info, basis "inlet pitch", per-tube paper solidity.
- Label correction (verified in fan_design.design: err ordered as stream_targets {outer, inner}): the step 4i-e stall is outer -1.46e-4,
  inner -1.04e-4. The 2026-10-29 entries above that say "inner -1.46e-4, outer -1.04e-4" have the labels swapped; the rule text is corrected.
- Open (user): the inlet-pitch floor is below Rotor 67 by the paper definition on tube 5 (expanding tube, -1.8 %), so "one-sided" does not hold
  on every tube.

## 2026-10-29 Concept acceptance (M1 step 4j, ADR-016)
- Fan rotor blade (M1.1.1) concept-accepted at rev011. Criteria checked: active record reproduces (tests/test_m1_sources.py::test_m1_active_record_verifies),
  budget 9/9 pass + 2 info, R-AM.15 stress check pass (225.0 MPa at the root, margin 2.26 >= 1.0), known deviations listed in docs/open_issues.md.
- No design, rule, tolerance or code change; no new revision. Disk, case, OGV and frame: not started (not accepted).

## 2026-10-29 Criteria: blade solid acceptance (M1 step 5a)
- New check, geometry only (no design or rule change): airfoil solid from the active record (geometry/blade_solid.py) against the record,
  relative tolerances [T] (tests/test_m1_blade_solid.py): mass 1e-2, chord root/tip 1e-4, A_root 1e-3, area ratio 5e-3, t/c hub/mid/tip 1e-3.
- Achieved at rev011 [H]: mass +3.46e-3 (cause: thickness normal to the curved camber line, section polygons 0.03-0.56 % above the record's
  A = (2/3) t c; loft vs section integral 1.4e-5), chord +4.6e-6 / +3.8e-6, A_root +3.4e-4, area ratio +2.0e-3, t/c -3.7e-5 / +4.4e-5 / +4.4e-5.

## 2026-10-29 Concept acceptance: M1 module at rev014 (ADR-016)
- User decision: whole M1 module concept-accepted at rev014; records/ACCEPTED = rev014 (core.records.mark_accepted).
- Known gaps accepted as listed in docs/open_issues.md, incl. #53 disk may be oversized, #54 friction/contact pressure
  not analysed, #36 aluminium density [T]. No design, rule, tolerance or code change; no new revision.
- From now on a design revision of M1 needs an approved CR (ADR-012).
