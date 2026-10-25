# M1 Failure Modes

Ids are referenced from `bom.yaml` (`failure_modes`) and `analyses.md`.

## FM-1 Blade dovetail low-cycle fatigue (CFM56-7B field case)
Source: Fox, Rossey, Raguet 2023, J Fail. Anal. and Preven. 23:1438-1451 [KS]. NTSB investigation of the 2016 (SWA 3472) and 2018 (SWA 1380) CFM56-7B24 fan blade fractures.

Hardware facts [KS], p. 1439:
- 24 Ti-6Al-4V blades in a Ti-6Al-4V disk. Alloy 718 shims sit between blade and disk contact faces; an elastomer-coated Ti-6Al-4V spacer in each slot gives radial restraint; aluminium platforms with elastomer seals between blades.
- Blade airfoil and root are shot peened. The dovetail contact faces are then grit blasted, plasma sprayed with Cu-Ni-In, and given a MoS2 dry-film lubricant; shims also get MoS2.
- Shims were not in the original design; added for disks made after 2004 (p. 1440).

Mechanism [KS]:
- LCF cracks start at several origins on the grit-blasted convex contact face of the dovetail, near its leading edge, in a zone of high contact stress (pp. 1442, 1449). No cracks in the adjacent shot-peened-only areas (p. 1447).
- One striation is about one flight cycle. Growth from 12.7 um depth to fracture took about 15,000 cycles (2016 blade, p. 1444) and about 20,000 cycles (2018 blade, p. 1448). Final fracture: ductile overload.
- Crack arrest lines matched dovetail relubrication events (a change in contact stress after reseating), p. 1445.
- Many cracked blades had a relaxed (less compressive) shot-peen residual stress at the contact face (about 80 % of test points on the tested blades, p. 1447). Post-accident tests: plasma spray coating without proper cooling can relax it (p. 1450).
- Contributing factors named: higher friction when run without lubrication or shims, coating spalling, coating thickness variation (some above the new-make limit), relaxed residual stress. NTSB finding: higher-than-expected dovetail stresses under normal operating load (p. 1450).
- Not lot-specific and not operator-specific (p. 1449). Fleet cracks mostly at more than 30,000 cycles since new; lowest 19,497 (p. 1448).

Mitigations and inspections [KS], pp. 1440, 1450-1451:
- Relubrication of dovetails and shims: at the time, not to exceed 5000 h or 3000 cycles; intervals reduced afterwards for inspected blades.
- Improved visual inspection of the dovetail coating.
- Eddy current inspection (ECI) at blade overhaul; ECI was the most sensitive method in the lab (p. 1446).
- Ultrasonic testing (UT) at each relubrication; one-time UT for high-time blades. UT works through the coating, but the coating adds signal noise.
- FPI and ECI need the coating stripped.

Design rules for M1 [G]:
- R-FM1.1 The dovetail contact face is a fatigue-critical location: the analysis must include contact pressure and friction, not only the centrifugal pull (see `analyses.md` A-3).
- R-FM1.2 Residual stress from peening is not a guaranteed credit after coating; assume it may relax.
- R-FM1.3 The design must allow inspection of the dovetail (UT through coating, ECI at overhaul).

## FM-2 Blade high-cycle fatigue (resonance, flutter) [G]
Excitation from inlet distortion and blade-row interaction; checked with a Campbell diagram and flutter screening (A-4, A-5).

## FM-3 Foreign object and bird impact [KS]
Leading-edge damage, root overload, blade-off. Methods and values: `bird_strike.md`.
Mirghani 2023 reports that a notch near the root raises root stresses more than a notch elsewhere (abstract, p. vi) [KS].

## FM-4 Blade-off and containment [G]
A released blade must be contained by the fan case (M1.2.2); the trailing blade and the rotor imbalance load the bearings (M8 interface, via CR).

## FM-5 Disk LCF [G]
Disk slots and bore under centrifugal and thermal cycles (A-6).

## FM-6 Tip rub [G]
Tip clearance closure (centrifugal growth, case ovalization, imbalance). Vadcard 2022 models blade-tip/casing contact on Rotor 67 [KS]; no M1 values taken.
