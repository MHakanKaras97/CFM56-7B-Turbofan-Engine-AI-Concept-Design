# M1 Budget

- M1 owns stations 2 -> 13 (outer fan + OGV, bypass side) and 2 -> 21 (fan hub, core side), and the inlet recovery P2/P1 (`engine/M0_engine/rules/station_ownership.md`).
- The budget is read only through `core.budgets.read_icd("M1 ...")`. Never read `icd.yaml` directly: `read_icd` refuses an ICD that is not from the active M0 revision.
- Budget items (names as in the ICD): FPR, eta_fan_outer, pr_fan_inner, eta_fan_inner, inlet_recovery, W2, W13, W21, T13, T21; power_outer_fan and power_inner_fan are info.
- Values are not copied into M1 files; code reads them at run time.

## Tolerances
- Tolerances are owned by M0 (`tolerances` in the ICD): pressure_ratio relative, efficiency absolute, flow relative, temperature absolute. All are [T].
- `core.budgets.check_budget("M1", achieved)` returns pass/fail per item. Items of kind info are reported only.

## Out of tolerance
- M1 does not change its budget. It reports the rows of `check_budget` to M0; M0 runs the integration check and drafts a CR (options: M0 params change or M1 redesign).
- Any change that affects another module (M2 inlet conditions from station 21, M7 bypass duct from station 13, M8 shaft power and speed) goes to M0 as a CR through `core/requests.py`; user approval is required.
