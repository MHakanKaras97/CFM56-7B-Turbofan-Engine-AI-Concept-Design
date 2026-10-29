# M6 LP Turbine Rules

| File | Content |
|---|---|
| `known_values.md` | Source values with tags and source numbers (rotor counts, LLP lives; NGV count rule [T]) |

Sources: `learning/sources/INDEX.md`. Agent: `.claude/agents/m6-lp-turbine.md`.

Workflow (M6 agent):
1. Read the budget with `core.budgets.read_icd("M6 ...")`.
2. Work only under `engine/M6_lp_turbine/`; record revisions with `core.records.create_revision`.
3. Check results with `core.budgets.check_budget("M6", ...)`.
4. Cross-module needs: CR to M0 via `core/requests.py`, user approval required.

Status: skeleton (agent, rule book index, known values). No design, no code, no revision; `bom/bom.yaml` has no parts.
