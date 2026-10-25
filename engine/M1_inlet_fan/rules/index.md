# M1 Inlet and Fan Rules

| File | Content |
|---|---|
| `budget.md` | Station ownership, budget via `read_icd`, tolerances, what to do out of tolerance |
| `bom.md` | Part numbering M1.1-M1.4, naming, material ids |
| `materials.md` | Material selection rules; values in `tools/data/materials.yaml` |
| `joints.md` | Dovetail, shim, coating stack, spacer/platform, flanges |
| `analyses.md` | Analyses A-1..A-9: method, tool, acceptance criterion, source |
| `failure_modes.md` | FM-1..FM-6, incl. CFM56-7B dovetail LCF case (Fox 2023) |
| `bird_strike.md` | Bird models, speeds, methods; certification numbers status |
| `aero_method.md` | Meanline method steps and loss models (diffusion factor, profile, shock, endwall) |

Reference data: `learning/rotor67_reference.yaml` (NASA Rotor 67, validation case for A-1).

Workflow (M1 agent):
1. Read the budget with `core.budgets.read_icd`.
2. Work only under `engine/M1_inlet_fan/`; record revisions with `core.records.create_revision`.
3. Check results with `core.budgets.check_budget("M1", ...)`.
4. Cross-module needs: CR to M0 via `core/requests.py`, user approval required.

Status: step 1 (rule book, sources). No meanline code or geometry yet.
