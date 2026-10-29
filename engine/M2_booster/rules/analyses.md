# M2 Analyses

| Id | Analysis | Method | Acceptance | Source |
|---|---|---|---|---|
| A-1 | Meanline validation on TP-1523 rotor 23B | `aero_method.md` A-1; `analysis/a1_validation.py` (step 2: fail, see aero_method.md) | D +-0.02, exit angle +-1.5 deg, PR +-1 % [T] | TP-1523 Tables 2, 8 [K] |
| A-2 | Budget and integration | `core.budgets.check_budget("M2", ...)`; M0 integration check | all budget rows pass (ICD tolerances) | ICD [H] |
| A-3 | Blade-row rule check | DF per section (R-AM2.2), solidity range, AR, hub/tip vs TP-1523 range | R-AM2.2 met; outside the tested range -> open issue | RM E53D01, TP-1523 [K] |
| A-4 | Structural safety | blade root pull stress and drum hoop stress, closed form [G] | stress <= yield / 1.5 (same rule as M1 R-AM.15) [T] | M1 rule; material values `tools/data/materials.yaml` |
| A-5 | Mass check (info) | sum of BOM masses | reported against the check value, never tuned to it | Lolis 2014 Table 4.3 [KS weak] |

## Check values (weak, labelled, never targets)
- Booster ("IPC" in the table) about 7.5 % of the estimated engine weight 2285.5 kg (Lolis 2014 Table 4.3 s. 126,
  Table 4.2 s. 125) -> about 171 kg [H from KS weak]. It is the author's ATLAS estimate (real engine 2405 kg); the
  author notes that the ATLAS booster disks came out larger than the real ones (s. 125); whether the share includes
  the drum, stators and case: doğrulanamadı. No tuning to it.
- Booster spool LLP life 22,900 EFC for -7B27 [KS] (Owner's Guide mtce s. 19): context for FM2-4, no life analysis
  at concept level.
