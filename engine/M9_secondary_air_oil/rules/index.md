# M9 Secondary Air and Oil Rules

| File | Content |
|---|---|
| `known_values.md` | Source values with tags and source numbers (scope only) |

Sources: `learning/sources/INDEX.md`. Agent: `.claude/agents/m9-secondary-air-oil.md`.

Workflow (M9 agent):
1. Read the budget with `core.budgets.read_icd("M9 ...")`.
2. Work only under `engine/M9_secondary_air_oil/`; record revisions with `core.records.create_revision`.
3. Check results with `core.budgets.check_budget("M9", ...)`.
4. Cross-module needs: CR to M0 via `core/requests.py`, user approval required.

Status: skeleton (agent, rule book index, known values). No design, no code, no revision; `bom/bom.yaml` has no parts.
