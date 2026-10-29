# M4 Combustor Rules

| File | Content |
|---|---|
| `known_values.md` | Source values with tags and source numbers (fuel injectors) |

Sources: `learning/sources/INDEX.md`. Agent: `.claude/agents/m4-combustor.md`.

Workflow (M4 agent):
1. Read the budget with `core.budgets.read_icd("M4 ...")`.
2. Work only under `engine/M4_combustor/`; record revisions with `core.records.create_revision`.
3. Check results with `core.budgets.check_budget("M4", ...)`.
4. Cross-module needs: CR to M0 via `core/requests.py`, user approval required.

Status: skeleton (agent, rule book index, known values). No design, no code, no revision; `bom/bom.yaml` has no parts.
