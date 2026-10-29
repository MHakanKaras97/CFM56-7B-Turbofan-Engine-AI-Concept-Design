# M3 HP Compressor Rules

| File | Content |
|---|---|
| `known_values.md` | Source values with tags and source numbers (rotor counts, IGV/VSV, LLP lives; stator count rule [T]) |

Sources: `learning/sources/INDEX.md`. Agent: `.claude/agents/m3-hp-compressor.md`.

Workflow (M3 agent):
1. Read the budget with `core.budgets.read_icd("M3 ...")`.
2. Work only under `engine/M3_hp_compressor/`; record revisions with `core.records.create_revision`.
3. Check results with `core.budgets.check_budget("M3", ...)`.
4. Cross-module needs: CR to M0 via `core/requests.py`, user approval required.

Status: skeleton (agent, rule book index, known values). No design, no code, no revision; `bom/bom.yaml` has no parts.
