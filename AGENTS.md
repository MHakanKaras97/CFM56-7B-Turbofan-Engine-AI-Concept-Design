# AGENTS.md

Instructions for AI coding agents other than Claude Code (for example OpenAI Codex).

The project rules are in [CLAUDE.md](CLAUDE.md). Read it first and follow it exactly; it applies to every agent,
not only Claude.

## Agent roles
- The main session acts as **M0, the engine agent**.
- Module agents M1-M9 are defined in `.claude/agents/<module>.md`. When you work on one module, use that file as
  your role description and read `engine/<module>/rules/index.md`.
- A module agent writes only inside its own `engine/<module>/` folder. For any change to another module, raise a
  change request through `core/requests.py`; the user approves it in the UI.

## Differences from Claude Code
- Claude Code runs a hook (`.claude/settings.json` -> `python -m core.scope hook`) that blocks writes outside a
  module's scope and blocks reading PDFs. Other agents do not run it: follow these rules yourself.
- The core rules are enforced in Python regardless of the agent: `core/bom.py`, `core/records.py`,
  `core/requests.py` and the test suite.

## Before you commit
- Run `pytest -q --tb=short <path>` for the files you changed during work, and the full suite before a commit.
- Numbers come from code, never from your own text, and every value carries a provenance tag (`[K]`, `[KS]`,
  `[H]`, `[G]`, `[T]`).
