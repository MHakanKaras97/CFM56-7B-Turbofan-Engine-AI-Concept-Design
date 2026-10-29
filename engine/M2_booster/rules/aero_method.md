# M2 Aero Method

Definitions come first and are written once here; every M2 file uses them. Numbers for TP-1523 are in
`learning/tp1523_reference.yaml` and are checked by `tests/test_m2_sources.py`.

## Definitions

### Solidity
- sigma = c / s, c = true chord (straight line leading edge to trailing edge along the design streamline), pitch
  s = 2 pi r_m / z, r_m = section mean radius (r_LE + r_TE) / 2 [H, settled numerically from TP-1523].
- Same as the M1 rule (M1 `aero_method.md` R-AM.18: chord x blades / (2 pi r_mean), r_mean = mean of LE and TE radii).
- TP-1523: Table 1 and all report text quote solidity **at the tip radius** (p. 3; symbol list p. 12, "at maximum
  radius") [K]. The blade tables 8-17 give solidity per radius; 28 of 30 checked rows reproduce chord x z /
  (2 pi (r_LE + r_TE)/2) within 0.2 %; stator 22 mid-span (r_TE - r_LE = 0.176 cm) reproduces only with the mean
  radius (LE alone is 0.4 % off) [H].
- M2 reports solidity per section by this definition and, for comparisons with TP-1523 Table 1 or its figures,
  the tip value.

### Diffusion factor
- M2 uses the Lieblein design diffusion factor in the relative frame for rotors and the absolute frame for stators,
  with radius change: D = 1 - W2/W1 + (r1 Wt1 - r2 Wt2) / ((r1 + r2) sigma W1), sigma per section as above
  (`tools.meanline.diffusion_factor`, same as M1) [K form, RM E53D01 eq. 13 p. 8].
- Note on "eq. 4": in RM E53D01, equation (4) (p. 7) is the boundary-layer separation criterion built on the
  local suction-surface velocity gradient; it needs the surface velocity distribution and cannot be evaluated from
  a velocity triangle. The design form derived from it is equation (13) (p. 8); equation (14) (p. 9) is its
  two-dimensional, equal-axial-velocity angle form. M2 applies eq. (13).
- TP-1523 eq. B4 (p. 13): doğrulanamadı from the text (image). Settled numerically: Table 2(b) rotor 23B tip, mid
  and hub D-FACT 0.452 / 0.450 / 0.571 are reproduced within 0.002 by the form above with the local blade-table
  solidity [H]. The radius-change term cannot be discriminated here (r2/r1 - 1 < 2e-4).
- TP-1523 Table 1 DF values are measured, mass-averaged hub to tip and interpolated to peak efficiency at design
  speed (p. 3) [K]; they are not design-point section values.

### Flow coefficient
- phi = V_x1 / U_tip, inlet axial velocity over rotor inlet tip speed [H, settled numerically: TP-1523 Table 2(a)
  stage 23B-20 0.470 = 114.6 / 243.9]. The appendix B formula (p. 15) is an image: doğrulanamadı from the text.

### Loading coefficient
- M2 reports two values per stage:
  - psi = dh0 / U_tip^2 (actual work, rotor inlet tip speed), the M1 definition [H].
  - head-rise coefficient psi_is = cp T1 (PR^((gamma-1)/gamma) - 1) / U_tip^2, the TP-1523 form, for comparison
    with the rig [H, settled numerically: Table 2(a) rotor 0.329, stage 0.322 reproduced within 0.001 with cp 1004,
    gamma 1.40 from the symbol list p. 11]. Appendix B formula (p. 14) is an image: doğrulanamadı from the text.

### Aspect ratio
- AR = blade height / mean chord (TP-1523 symbol list p. 11) [K]. Height = mean of the LE and TE annulus heights,
  mean chord = mean of the section chords [T for a flared annulus; TP-1523 annulus is parallel, height 5.08 cm].
- TP-1523 Table 1 AR uses the nominal chord (5.08 / 5.08 = 1.00 for rotor 23B) and matches within 0.01 for all
  24 rows [H].
- Lolis 2014 Table 4.10 rotor AR 2.0, stator AR 1.2 [KS, method assumption, not a CFM56 measurement]; Lolis'
  AR definition: doğrulanamadı.

### Hub/tip ratio
- nu = r_hub / r_tip at the blade-row leading edge plane [G]. TP-1523: 0.8, constant through the stage [K].

### Spanwise distribution (hub/mean/tip) [step 3, written before the step 3 runs]
- The meanline carries one-dimensional values at the mean radius r_m = (r_hub + r_tip) / 2 of each plane: stage work
  w (from the stage PR and the polytropic efficiency, R-AM2.4) and the plane axial velocity Vx_1D from continuity on
  the geometric annulus (uniform over the span, no blockage, see below). The annulus rule (plan step 5) uses Vx_1D only.
- Hub and tip sections are local values from fixed shape ratios, mean section = 1:
  - work: w_sec = g_sec x w (g_mean = 1); rotor exit swirl from Euler on the section radii,
    Vt2_sec = (g_sec w + U1_sec Vt1_sec) / U2_sec, U = omega r (r1 on the LE plane, r2 on the TE plane);
  - axial velocity: Vx_sec = f_sec x Vx_1D (f_mean = 1), one shape per plane (rotor LE, rotor TE, stator TE);
  - inlet swirl Vt1_sec comes from the upstream plane (zero here: stator exit swirl 0 [T], station 21 no swirl);
  - triangles, DF and solidity per section by the definitions above (`stage_aero.rotor_section`, `stator_section`).
- Free vortex is the special case g = f = 1 (uniform work, uniform axial velocity, r Vt constant).
- No radial equilibrium or streamline curvature is solved; the shape ratios replace it [T]. Continuity and the
  mass-averaged work are closed on the mean section only; hub/tip ratios are not re-normalised. The code reports the
  three-point (Simpson, weights 1/4/1 on r Vx, uniform density) mass-flow and work deviation of each profile [H].
- A-1 uses the rig's own tabulated section values (TP-1523 Table 2(b) p. 21, rotor 23B hub/mid/tip): radii, rpm,
  inlet and exit meridional velocity, zero inlet swirl, total temperature ratio (work w_sec = cp Tt1 (TR_sec - 1),
  cp 1004 p. 11), chord and blade count (Table 8). In A-1 the mean section also uses the tabulated values, not
  continuity.
- Booster design choice (step 3) [T]: shape ratios transferred from the rig (proportional rule, no CFM56 source),
  read by code from `learning/tp1523_reference.yaml`:
  - g from rotor 23B Table 2(b): g_sec = (TR_sec - 1) / (TR_mid - 1);
  - f at the rotor TE from rotor 23B Table 2(b) exit meridional velocity / mid value;
  - f at the stator TE from stator 20 Table 2(c) p. 22 exit absolute velocity / mid value (exit swirl 0); the next
    rotor LE is the same plane; stage 1 rotor LE (station 21) is uniform (M1 gives no profile).
  - The rig's mid-span TR 1.071 against the overall 1.072 (Table 2(a)) [K] supports mean-section work = stage work.

### Blockage
- TP-1523 p. 2: the streamline design program included boundary-layer blockage factors [K]; the report gives no
  values (doğrulanamadı). M2 uses **no blockage**: continuity on the geometric annulus. The rig mass flow 9.457 kg/s
  (Table 2(a)) against rho Vx A on the geometric inlet annulus (`a1_validation.yaml`) is reported for information
  only and is not used as a factor.

## Meanline plan (run in step 2: `analysis/booster_meanline.py`, inputs `analysis/booster_params.yaml`)
1. Inlet: station 21 (`read_icd`: Tt, Pt, W) and the M1 station 21 annulus (`engine/M1_inlet_fan/geometry/flowpath.yaml`,
   read-only, rev014). N1 = ICD `shafts.LP.speed_refs.girao_nominal` [KS].
2. Stage count 3 [KS] (Girão 2023 PDF p. 36; Owner's Guide s. 10; Lolis 2014 s. 122 agree).
3. Work split: equal stage pressure ratio of `pr_booster` [T] until a source gives another split.
4. Efficiency: the M0 budget `eta_booster` (ADR-015). The meanline gives velocity triangles, angles, DF, loading and
   geometry only; it does not predict efficiency.
5. Annulus: constant hub radius (Lolis 2014 Table 4.10, method assumption [KS]); tip radius from continuity with
   axial Mach number equal to the station 21 value [T]. Lolis' inlet Mach 0.5 differs from station 21 (0.393 [H]); user decision (#58 closed): keep the M1 station 21 area, no CR; Lolis 0.5 is a method assumption only.
6. Per row: mean-line triangles plus hub and tip by the spanwise distribution above (step 2: free vortex [G];
   step 3: TP-1523 shape transfer [T]); DF by the definition above; solidity from R-AM2.2.
7. Exit: station 24 (booster exit), then the transition duct `duct_25_24` to station 25. VBV: M2 models only the
   station 25 outlet; no VBV open/closed state (user decision; VBV closed at high power, Girão PDF p. 47 [KS]).

## Rules (few, each with a source)

- **R-AM2.1 Stage count**: 3 stages [KS] (three sources above).
- **R-AM2.2 Diffusion factor limits** (each section, design point):
  - rotor tip D <= 0.45: above about 0.45 rotor-tip element efficiency falls below 0.90 (RM E53D01 summary p. 1) [K];
  - rotor hub/mean and all stator sections D <= 0.58: the highest loading tested in TP-1523 (stage 28B-22, rotor and
    stator 0.58 measured, stall margin 13 %, p. 3 and Table 1) [K]; no extrapolation above the tested range.
  - Stator solidity comes from these limits (smallest vane count that meets them, R-KV2.1); rotor solidity is an
    output (rotor counts are fixed inputs, R-AM2.3). All rows are checked against the TP-1523 tested tip range
    0.9-2.0 [K]; outside -> open issue, not a silent extrapolation.
- **R-AM2.3 Proportional geometry** [T] (no CFM56 source for radii, chords or stator counts):
  - rotor blade counts 74/78/74 are fixed inputs [KS] (#52, `known_values.md`), read by code, not derived;
  - chord from AR: rotor AR 2.0, stator AR 1.2 (Lolis 2014 Table 4.10 method assumptions [KS]);
  - rotor solidity and rotor DF are outputs; counts and chords are never tuned to meet a DF limit; a violation
    is reported (open issue);
  - stator vane count by R-KV2.1 [T]: z = ceil(sigma_req x 2 pi r_m / c), sigma_req from R-AM2.2, and z differs
    from both adjacent rotor counts;
  - radii from step 5 of the meanline plan. These are rules, not values; values come from code.
- **R-AM2.4 Efficiency** from the M0 budget only (ADR-015).

## Applicability of TP-1523 (step 1, `tp1523_reference.yaml` applicability) [H]
- Booster inlet (station 21): hub/tip 0.697 (rig 0.8: 13 % below, outside the tested range); tip speed 239.8 m/s at
  5282 rpm (rig 243.8: -1.7 %); tip relative Mach 0.787 without inlet swirl (rig rotor 23B tip 0.801): subsonic.
- Stage exits with constant hub and constant axial Mach [T]: hub/tip 0.731 / 0.763 / 0.793, tip speed 228.7 / 219.0 /
  210.6 m/s (down to -14 % against the rig). Stage 1 is an extrapolation in hub/tip -> open issue #57.

## Validation case A-1 (run in step 2: `analysis/a1_validation.py` -> `analysis/a1_validation.yaml`)
- Case: TP-1523 rotor 23B at design point (Table 2(b) p. 21: inlet velocities, rpm 9170, blade angles Table 8 p. 38).
- Run the M2 meanline with the rig geometry and Table 2 inlet conditions. Rotor adiabatic efficiency in Table 2(a) is
  OCR "0.9L3" (0.943 likely; PR/TR 1.257 / 1.072 give 0.938, TR rounded to 3 decimals): doğrulanamadı; A-1 uses the
  PR/TR pair.
- Pass criteria [T]: D at tip/mid/hub within +-0.02 of 0.452 / 0.450 / 0.571; exit relative flow angle within
  +-1.5 deg of Table 2(b); rotor PR within 1 % of 1.257 with the efficiency from PR/TR.
- Step 2 result: fail (D tip and hub outside +-0.02; exit angles and PR pass, PR by construction in design mode).
  Stopping rule: no tuning; the booster meanline values are tagged [T] (unvalidated placeholder) until A-1 passes.
- Step 3 (#63): A-1 re-run with the rig's tabulated section inputs (Spanwise distribution above; criteria,
  tolerances and stopping rule unchanged): pass on all seven criteria (`a1_validation.yaml`). This checks the section
  triangles, solidity and DF given a spanwise distribution; it does not validate the booster's own [T] shape
  transfer, so booster section values stay [T] (`booster_meanline.py` tag rule).
