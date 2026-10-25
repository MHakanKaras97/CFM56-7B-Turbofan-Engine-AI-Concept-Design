# M1 Aerodynamic Method (meanline)

Summary of the meanline theses in `learning/sources/aero/`. Page numbers are PDF pages. No code yet; this file fixes the method the M1 meanline code will follow.

## Sources
| Source | Tool | Use here |
|---|---|---|
| Visentin 2021, Padova MSc [KS] | SATURN (1D meanline, C++) | Method steps, loss model set (Table 2.1, p. 32) |
| Zanoni 2020, Padova MSc [KS] | SATURN, validated on NASA Rotor 37 | Same loss set (pp. 19-20); meanline + genetic optimizer + CFD check |
| Abrisha 2026, TU Wien MSc [KS] | MATLAB fan-stage loss model | Loss correlations in detail, stall and choke limits (pp. 35-42) |
| Sjögren 2023, Chalmers Lic. [KS] | SC90C streamline curvature | Profile, endwall, shock loss and deviation (pp. 22-25) |
| Khelghatibana 2014, Montréal MSc [KS] | 3D CFD optimization of Rotor 67 | Not meanline; Rotor 67 data cross-check (p. 37); notes that transonic blade detail needs 3D CFD (p. 28) |

## Method steps (meanline, per blade row)
1. Inputs: mass flow, inlet Tt and Pt, rotor speed, annulus radii at inlet and exit, blade angles, solidity, thickness/chord, blockage. Perfect gas (Visentin p. 27) [KS]; M1 uses the M0 gas model instead [G].
2. Axial velocity from continuity with a blockage factor; relative Mach found by Newton iteration on the static state (Visentin pp. 29-30) [KS].
3. Inlet velocity triangle; incidence = inlet relative flow angle minus blade inlet angle (Abrisha p. 36) [KS].
4. Deviation: reference value at minimum-loss incidence from a Carter-type rule (camber, solidity, thickness, stagger), then corrected for off-reference incidence (Sjögren pp. 22-23; Abrisha p. 36) [KS].
5. Exit triangle and work from the Euler equation, delta h = U2 Vt2 - U1 Vt1; rothalpy conserved across the rotor (Visentin p. 30; Abrisha p. 36) [KS].
6. Losses as total pressure loss coefficients, summed: profile + shock + endwall (+ tip clearance, secondary) (Sjögren p. 22; Visentin p. 31) [KS].
7. Exit total pressure from the loss; efficiency and pressure ratio from the total temperature and pressure ratios (Abrisha pp. 36-37) [KS].
8. Off-design: incidence-dependent loss bucket; stall and choke limits from critical incidence (Abrisha pp. 41-42); SATURN flags choke when the Mach loop diverges and surge from a stall criterion (Visentin p. 32) [KS].
9. Spanwise: SATURN solves several spans per row (Visentin p. 27); SC90C adds spanwise mixing and an endwall loss distribution along the span (Sjögren p. 23) [KS].

## Loss models
### Diffusion factor (blade loading)
- Lieblein diffusion factor DF = 1 - W2/W1 + |delta Vt| / (2 sigma W1) (Sjögren eq. 2.13; Abrisha eq. 4.10) [KS].
- Equivalent diffusion ratio D_eq (Lieblein) gives the wake momentum thickness and hence profile loss (Sjögren eq. 2.10-2.11) [KS].
- Abrisha caps DF at 0.7 in the Koch-Smith model (p. 38) and gives 0.3-0.6 as a practical design criterion, 0.3 at the tip and 0.6 at the hub (p. 38, printed p. 26) [KS].

### Profile loss
- Lieblein: loss from wake momentum thickness vs D_eq and inlet Mach (Sjögren p. 23) [KS].
- Koch and Smith: includes compressibility, area contraction, thickness; chosen by Abrisha as the conservative option (pp. 37-38) [KS].
- Hearsey (exponential in DF) and Miller (Mach-interpolated polynomials) as alternatives (Abrisha p. 39) [KS].
- Reynolds correction below Re = 1e6 (Sjögren eq. 2.16, p. 25) [KS].

### Shock loss
- Normal-shock total pressure loss at a passage Mach number = mean of inlet relative Mach and peak suction-surface Mach (Schwenk method in SC90C, Sjögren p. 24) [KS].
- Taper between M1rel = 0.8 (zero) and 1.0 (full) (Sjögren p. 24) [KS].
- Miller-Lewis-Hartmann / Koch-Smith in SATURN (Visentin p. 32; Zanoni p. 20) [KS].
- Boyer's modified Miller-Bloch: oblique shock with sonic downstream flow, then a second normal shock if still supersonic (Abrisha p. 40) [KS].

### Endwall, tip clearance, secondary
- Endwall: Koch-Smith, Koch, Benner (SATURN); Wright-Miller with aspect ratio, loading and clearance (SC90C); polynomial in DF with a cap (Abrisha p. 40) [KS].
- Tip clearance: Yaras-Sjolander; secondary: Howell (Visentin p. 32) [KS].

## Implementation (M1 step 2)
- `tools/meanline.py` (shared with M2/M3): stream tubes with given inlet/exit radii and areas, no radial equilibrium; perfect gas with gamma 1.4 [G].
- Deviation: Carter's rule (m = 0.23 (2a/c)^2 + kappa2/500, a/c = 0.5) [G], at the reference incidence only.
- Profile loss: Lieblein D_eq [KS] with the wake momentum fit theta/c = 0.004 (1 + 3.1 (D_eq - 1)^2 + 0.4 (D_eq - 1)^8) [G, Aungier 2003, not in the source set].
- Shock loss: normal shock at the mean of inlet relative Mach and the suction-surface Mach after a Prandtl-Meyer expansion to the covered-passage entrance [KS method, geometry assumption T].
- Endwall and tip clearance loss (M1 step 3b, `Endwall` data per tube; off when absent). No source in the set gives a closed form with coefficients (Abrisha p. 40 gives the structure but not the polynomial coefficients; Sjögren eq. 2.12 leaves the Wright-Miller function f(D, tau/c) to its reference), so general correlations are used:
  - endwall: Howell annulus drag C_Da = 0.020 s/h + secondary drag C_Ds = 0.018 C_L^2, loss = sigma C_D cos^2(beta1) / cos^3(beta_m) [G; Howell is SATURN's secondary model, Visentin p. 32];
  - tip clearance: Lakshminarayana efficiency debit 0.7 (tau/h) psi / cos(beta_m) (1 + 10 sqrt((tau/c) AR / (psi cos(beta_m)))) [G], applied as the matching total pressure loss;
  - spanwise weights: endwall 3 (2f - 1)^2 [T] (both walls, after the parabolic distribution of SC90C, Sjögren p. 23); tip clearance only above 80 % span, uniform weight 5 (M1 step 4b; extent [KS] Zanoni p. 16, shape [T]); both average 1 over the span.
- Rotor 67 with these losses on (analysis/rotor67_validation.yaml `losses_on_diagnostic`) [H]: design PR 1.516, -7.0 % (A-1 limit 2 %); the two tip tubes choke at the exit; hub PR near peak 1.744 -> 1.721 against 1.609 measured. The hub excess is a work/deviation issue, not a loss issue. The losses therefore stay OFF in the acceptance run and in the fan design until radial equilibrium is in (user decision, M1 step 3b).
- Rotor 67 DF per design streamline at the design point (rotor67_reference.yaml `computed_diffusion_factor`) [H from KS geometry]: 0.39 (hub, span 0.11) rising to 0.46 at mid span, falling to 0.39-0.40 at span 0.73-0.82; tip streamline 0.30 is at exit choke. Lieblein DF is less meaningful in the supersonic tip flow (M1rel > 1 above span about 0.45).
- Loss correlation sources (M1 step 4): Howell annulus/secondary drag in the form of Saravanamuttoo et al., Gas Turbine Theory, and Dixon & Hall (cascade lift, drag and loss relations); Lakshminarayana 1970 (J. Basic Eng. 92) for tip clearance. All [G]: not in the M1 source set (full citations in the `tools/meanline.py` docstring).
- Radial equilibrium (M1 step 4, `solve_rotor_re`): simple radial equilibrium dh0/dr = T ds/dr + Vm dVm/dr + (Vt/r) d(r Vt)/dr [G] at rotor inlet (uniform inlet: uniform Vm, split by area) and exit (tube exit areas and area-centre radii moved, mass per tube fixed, under-relaxation 0.1, re-solving work, deviation and losses each pass). Limitation: streamline curvature and slope neglected.
- A-1 with radial equilibrium (`radial_equilibrium_diagnostic` in rotor67_validation.yaml) [H]: RE without the new losses passes (PR +1.3 %); RE with the losses on removes the tip exit choke but fails (PR -4.5 %, eta 0.850; limit 2 %). Near peak, hub PR 1.744 -> 1.666 (measured 1.609); mid-span and tip PR now 0.13-0.22 below measured. Not tuned (user rule). Acceptance run stays without RE and without the new losses until this passes.
- Loss model review (M1 step 4b, PDF pages):
  - (i) Profile loss data basis: 2D cascade data. SC90C takes it from Lieblein's DCA cascade correlation with endwall loss added separately by Wright-Miller (Sjögren pp. 22-23); Abrisha combines cascade profile loss (Koch-Smith) with separate shock and endwall terms (p. 37). Our Lieblein/Aungier fit is cascade-based, so endwall and tip losses are not double counted; nothing removed.
  - (ii) Transonic shock loss: Schwenk normal shock at the passage Mach = mean of M1rel and the peak suction-surface Mach (SC90C, Sjögren p. 24); Miller-Lewis-Hartmann and Koch-Smith (SATURN, Visentin p. 32; Zanoni p. 20); Boyer's modified Miller-Bloch, oblique shock then a normal shock if still supersonic (Abrisha p. 40). `tools/meanline.py` already uses the passage-shock form (mean of M1rel and the Prandtl-Meyer suction-surface Mach), not a normal shock at M1rel; unchanged.
  - (iii) Tip clearance spanwise extent: measured Rotor 37 efficiency falls sharply above 80 % span, from tip clearance flow, shock and casing boundary layer (Zanoni p. 16); SC90C spreads the whole endwall loss (which includes clearance) parabolically (Sjögren p. 23); Abrisha notes Lakshminarayana's radial-distribution model without giving it (p. 21) and shows a parabolic total-loss profile with minimum about 0.027 near mid-span (p. 54). Applied: tip loss only above 80 % span.
  - Result (`rotor67_validation.yaml` `loss_review`) [H]: radial equilibrium + all losses, design PR -5.9 % and near-stall PR -9.1 %, eta 0.834 vs 0.901: A-1 fails. Mass-averaged deficit shares at the design point: profile 0.028, shock 0.068, endwall 0.030, tip 0.024 (1 - eta = 0.163; measured near-peak deficit 0.072). Calibration proposal: ADR-014 (draft, not applied).
- Not yet modelled: streamline curvature, incidence-dependent deviation and loss.

## M1 rules
- R-AM.1 The first M1 meanline code implements steps 1-7 at design point, then off-design (step 8).
- R-AM.2 Loss set for version 1: Lieblein D_eq profile loss, Schwenk-type normal shock at passage Mach. Endwall (Howell) and tip clearance (Lakshminarayana) terms and radial equilibrium are implemented [G] but used in design only after A-1 passes with all of them on (it does not yet, M1 step 4). Alternatives are kept as options, not mixed silently.
- R-AM.3 Validation case: NASA Rotor 67 (`learning/rotor67_reference.yaml`). Pass criterion in `analyses.md` A-1.
- R-AM.4 Meanline results are compared with the M1 budget only through `core.budgets.check_budget` (see `budget.md`).

## Fan design (M1 step 3, `analysis/fan_design.py`)
- R-AM.5 Blade loading: DF limit 0.6 at the hub and 0.3 at the tip (Abrisha p. 38) [KS], linear in inlet span fraction [T]; each tube gets the lowest solidity that keeps DF at its local limit, within the search bounds 1.0-3.2 [T]. A tube at the upper solidity bound with DF above its limit is reported as a failed DF check.
- R-AM.6 Metal angles: kappa1 = beta1 - design incidence (3 deg [T]); kappa2 iterated until the tube pressure ratio equals its stream target (outer FPR, inner pr_fan_inner from `read_icd`).
- R-AM.7 Splitter at the inlet radius whose inner area share equals W21/W2 (uniform inlet, `solve_rotor` splits by area); tubes of equal inlet area within each stream.
- R-AM.8 Until endwall and tip clearance losses are in the tool, design efficiencies are optimistic and are reported as such, not tuned.
- R-AM.9 (approved by the user, M1 step 4) Blade loading per stream tube against Rotor 67 at the same relative span (linear interpolation in `rotor67_reference.yaml` `computed_diffusion_factor`, tubes at exit choke excluded) [H from KS]:
  - below about 45 % span (subsonic Rotor 67 inlet, M1rel < 1): DF not above the Rotor 67 DF;
  - above about 45 % span (supersonic, where Lieblein DF means less): DF not above the Rotor 67 DF and solidity not below the Rotor 67 solidity (hub 3.11 to tip 1.29, linear in span, Strazisar p. 2 [KS]).
  It replaces the Abrisha 0.6/0.3 band of R-AM.5 for the redesign. The 45 % boundary is the Rotor 67 sonic span at the design point (M1rel = 1 between span 0.44 and 0.54 in `computed_diffusion_factor`) [H].
