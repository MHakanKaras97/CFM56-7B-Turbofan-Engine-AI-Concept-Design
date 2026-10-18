# CLAUDE.md

## Purpose
Concept-level design of a CFM56-7B27 class turbofan via a multi-agent system:
an M0 engine agent coordinating M1-M9 module agents.

## Numbers and provenance
- Numbers come from code, never from LLM text.
- Tag every value with its provenance:
  - `[K]` primary source
  - `[KS]` secondary source
  - `[H]` computed
  - `[G]` general engineering knowledge
  - `[T]` estimate

## Single source of truth
- `engine/M*/bom/bom.yaml` is the single source of truth for parts.
- bom.yaml is machine-managed: no comments; use notes. Write it only via `core/bom.py` (`write`/`dump`).
- Geometry is generated only by code in the module's `geometry/` folder.
- Derived files (results.yaml, icd.yaml) are never edited by hand; change the source and regenerate.

## Part identification
- Part id: `M<module>.<stage>.<part>`
- Part name: `"<Module> Stage <n> <Part type>"`
- Repeated parts: one definition + `qty`.

## Ownership and change control
- Each part has exactly one owner module.
- Agents never edit other modules' files. They raise a change request to M0.
- User approval is required for every cross-module change.
- Create, decide and apply change requests only through `core/requests.py`.

## Records
- Records are immutable.
- Revert restores the module's full state (bom, params, results) from its record, regenerates derived files,
  and is allowed only to reproducible revisions. Records are never modified. Module agents read budgets only via read_icd.
- Active revision = `records/ACTIVE` file only; manifests are never rewritten.
- Create, revert and verify records only through `core/records.py`.

## Sources and copyright
- No copyrighted text or figures. Summarize in your own words.
- List every source with its license in `docs/sources.md`.

## Language
- Code, identifiers, comments: English.
- Learning notes (`docs/learning/`, `engine/M*/learning/`): Turkish.

## Restrictions
- Do not add dependencies without asking.
- Do not add root-level `.py` files without asking.

## Session status
- Session start: read docs/status.md. Task end: update it (keep under 70 lines, newest first in 'Son yapılanlar').

## Where things are
- Architecture: `docs/architecture.md` (read before structural changes)
- Decisions: `docs/decisions/ADR-*.md`
- Change requests: `engine/M0_engine/requests/CR-###.yaml`
- Module rules: `engine/M*/rules/index.md` (read only the relevant module)

## Final report
End every task with only this report, max 15 lines, no step narration:

```
Commit: <hash> <message>
Done: <bullets>
Decisions for user: <bullets or "none">
Tests: <passed/total>
```
