# M5 HP Turbine Rules

| File | Content |
|---|---|
| `known_values.md` | Source values with tags and source numbers (rotor count, LLP lives; NGV count rule [T]) |

Sources: `learning/sources/INDEX.md`. Agent: `.claude/agents/m5-hp-turbine.md`.

Workflow (M5 agent):
1. Read the budget with `core.budgets.read_icd("M5 ...")`.
2. Work only under `engine/M5_hp_turbine/`; record revisions with `core.records.create_revision`.
3. Check results with `core.budgets.check_budget("M5", ...)`.
4. Cross-module needs: CR to M0 via `core/requests.py`, user approval required.

Status: skeleton (agent, rule book index, known values). No design, no code, no revision; `bom/bom.yaml` has no parts.
