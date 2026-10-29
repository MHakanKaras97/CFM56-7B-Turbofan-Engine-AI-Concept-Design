# M2 Budget

- M2 owns stations 21 -> 24 (booster) -> 25 (transition duct exit, HPC inlet) (`engine/M0_engine/rules/station_ownership.md`).
  Station 21 is owned by M1 (inlet to M2); station 24 is M2-internal; station 25 goes to M3.
- The budget is read only through `core.budgets.read_icd("M2 ...")`. Never read `icd.yaml` directly: `read_icd` refuses
  an ICD that is not from the active M0 revision.
- Budget items (names as in the ICD): `pr_booster` [KS], `eta_booster` [H], `duct_25_24` [KS], `W25`, `T25`; `power` is info.
- Values are not copied into M2 files; code reads them at run time.
- Efficiency: `eta_booster` is taken from the budget (ADR-015); the meanline does not predict it.

## Tolerances
- Owned by M0 (`tolerances` in the ICD): pressure_ratio relative, efficiency absolute, flow relative, temperature
  absolute. All are [T].
- `core.budgets.check_budget("M2", achieved)` returns pass/fail per item. Items of kind info are reported only.

## VBV boundary (user decision, M2 step 1)
- The variable bleed valve flow function belongs to M2; the hardware (openings, doors, structure) stays in the M1 fan
  frame (open issue #48, M1 placeholder openings).
- At concept level M2 models only the station 25 outlet; no VBV open/closed state (design point = take-off, VBV
  closed at high power, Girão 2023 PDF p. 47 [KS]). No M1 BOM change, so no CR.

## Out of tolerance
- M2 does not change its budget. It reports the `check_budget` rows to M0; M0 runs the integration check and drafts a
  CR (options: M0 params change or M2 redesign).
- Any change that affects another module (M1 station 21 annulus or fan disk flange, M3 station 25, M8 LP shaft) goes to
  M0 as a CR through `core/requests.py`; user approval is required.
