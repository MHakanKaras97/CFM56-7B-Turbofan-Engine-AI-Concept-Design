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
- Not yet modelled: endwall and tip clearance loss, radial equilibrium, incidence-dependent deviation and loss.

## M1 rules
- R-AM.1 The first M1 meanline code implements steps 1-7 at design point, then off-design (step 8).
- R-AM.2 Loss set for version 1: Lieblein D_eq profile loss, Schwenk-type normal shock at passage Mach; Wright-Miller-type endwall loss is the next addition. Alternatives are kept as options, not mixed silently.
- R-AM.3 Validation case: NASA Rotor 67 (`learning/rotor67_reference.yaml`). Pass criterion in `analyses.md` A-1.
- R-AM.4 Meanline results are compared with the M1 budget only through `core.budgets.check_budget` (see `budget.md`).

## Fan design (M1 step 3, `analysis/fan_design.py`)
- R-AM.5 Blade loading: DF limit 0.6 at the hub and 0.3 at the tip (Abrisha p. 38) [KS], linear in inlet span fraction [T]; each tube gets the lowest solidity that keeps DF at its local limit, within the search bounds 1.0-3.2 [T]. A tube at the upper solidity bound with DF above its limit is reported as a failed DF check.
- R-AM.6 Metal angles: kappa1 = beta1 - design incidence (3 deg [T]); kappa2 iterated until the tube pressure ratio equals its stream target (outer FPR, inner pr_fan_inner from `read_icd`).
- R-AM.7 Splitter at the inlet radius whose inner area share equals W21/W2 (uniform inlet, `solve_rotor` splits by area); tubes of equal inlet area within each stream.
- R-AM.8 Until endwall and tip clearance losses are in the tool, design efficiencies are optimistic and are reported as such, not tuned.
