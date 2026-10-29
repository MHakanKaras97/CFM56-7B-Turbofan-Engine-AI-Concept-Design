# M8 Shaft and Bearing Rules

| File | Content |
|---|---|
| `known_values.md` | Source values with tags and source numbers (fan shaft and booster spool LLP lives) |

Sources: `learning/sources/INDEX.md`. Agent: `.claude/agents/m8-shaft-bearing.md`.

Workflow (M8 agent):
1. Read the budget with `core.budgets.read_icd("M8 ...")`.
2. Work only under `engine/M8_shaft_bearing/`; record revisions with `core.records.create_revision`.
3. Check results with `core.budgets.check_budget("M8", ...)`.
4. Cross-module needs: CR to M0 via `core/requests.py`, user approval required.

Status: skeleton (agent, rule book index, known values). No design, no code, no revision; `bom/bom.yaml` has no parts.
