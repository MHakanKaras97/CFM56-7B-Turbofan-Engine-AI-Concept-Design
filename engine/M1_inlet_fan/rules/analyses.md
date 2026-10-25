# M1 Analyses

Acceptance criteria tagged [T] are provisional until a source or an M0 decision fixes them.

| Id | Analysis | Method | Tool | Acceptance criterion | Source |
|---|---|---|---|---|---|
| A-1 | Meanline aero, design point | `aero_method.md` steps 1-7 | Python (M1 `analysis/`, to be written) | Rotor 67: computed PR and efficiency vs measured near-peak point within 2 % PR and 2 points efficiency [T] | Strazisar 1989 [KS] |
| A-2 | Budget check | `core.budgets.check_budget` | core | All non-info M1 budget items within the ICD tolerances | M0 ICD [H] |
| A-3 | Blade and dovetail static stress | Centrifugal + gas load; dovetail contact with friction | FE (CalculiX via PrePoMax) | Peak stress below yield / safety factor [T]; contact pressure recorded | Fox 2023, Mirghani 2023 [KS] |
| A-4 | Campbell diagram | Blade modes vs engine orders, 0 to max N1 | FE modal | No crossing of low orders in the running range without margin [T] | [G] |
| A-5 | Flutter screening | Reduced frequency / incidence check | meanline + modal | Screening only at this stage [T] | [G] |
| A-6 | Disk and dovetail LCF | Cycles to crack initiation at the contact face | FE + S-N / strain-life | Life above the inspection interval with margin [T]; allowables per R-MAT.1 | Fox 2023 [KS] |
| A-7 | Bird strike | SPH or ALE bird on rotating blade | LS-DYNA class explicit solver (tool not chosen; decision for user) | No blade release; deformation limit [T] | `bird_strike.md` [KS] |
| A-8 | Blade-off containment | Energy of a released blade vs case | Hand calc, then explicit FE | Case contains the blade [T] | [G] |
| A-9 | Tip clearance | Centrifugal and thermal growth vs case | Hand calc / FE | Running clearance positive at max N1 [T] | Strazisar 1989 (Rotor 67 ~1 mm) [KS] |

Notes:
- Mirghani 2023 ran a fan blade at 4000 rpm (abstract, p. v) [KS]. Our take-off N1 is about 5282 rpm (Girão 2023 nominal LP speed, M0 `girao_2023.yaml`) [KS]. Centrifugal stress scales with N squared, so Mirghani's stresses are not M1 values; any reuse scales them in code.
- Mirghani's blade is an assumed geometry (Table 4, p. 50): not CFM56-7B data [KS].
