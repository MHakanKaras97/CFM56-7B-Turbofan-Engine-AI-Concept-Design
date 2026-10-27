"""Module write scope (ADR-002).

A module agent (Claude Code subagent named `m<digit>-...`, e.g. `m1-inlet-fan`) may write only inside its
module folder `engine/M<digit>_*/`. Two checks enforce this:
- hook(): PreToolUse hook for Write/Edit/NotebookEdit. Claude Code passes `agent_type` (the subagent name)
  in the hook input; a write outside the module folder is blocked with exit code 2.
- The same hook blocks the Read tool on *.pdf for every agent and the main session (token efficiency):
  source PDFs are read only through sources_text/ and INDEX.md.
- changed_outside(): after a module task M0 lists files changed outside the module folder (git status),
  which also catches writes made through Bash or PowerShell, where the hook cannot see the target path.

Run `python -m core.scope check M1` to list changes outside M1 (exit 1 if any).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from core.records import ROOT, module_dir

AGENT_RE = re.compile(r"^m(\d)-")
WRITE_TOOLS = {"Write": "file_path", "Edit": "file_path", "NotebookEdit": "notebook_path"}
PDF_READ_MESSAGE = "use sources_text/ and INDEX.md; ask the user for a PDF page"


def agent_module(agent_type: str | None) -> str | None:
    """'M1' for agent 'm1-inlet-fan'; None for the main session (M0) and other agents."""
    m = AGENT_RE.match(agent_type or "")
    return f"M{m.group(1)}" if m else None


def _inside(path: Path, folder: Path) -> bool:
    try:
        path.resolve().relative_to(folder.resolve())
        return True
    except ValueError:
        return False


def write_allowed(agent_type: str | None, file_path: str, root: Path = ROOT) -> tuple[bool, str]:
    module = agent_module(agent_type)
    if module is None:
        return True, ""
    folder = module_dir(module, root)
    if _inside(Path(file_path), folder):
        return True, ""
    return False, (f"{agent_type} may write only under {folder.relative_to(root).as_posix()}/; "
                   f"blocked: {file_path}. Raise a change request to M0 instead (CLAUDE.md, ADR-002).")


def hook(stdin_text: str, root: Path = ROOT) -> tuple[int, str]:
    """(exit code, stderr message) for one PreToolUse event."""
    try:
        event = json.loads(stdin_text)
    except json.JSONDecodeError:
        return 0, ""
    if event.get("tool_name") == "Read":
        target = str((event.get("tool_input") or {}).get("file_path") or "")
        return (2, PDF_READ_MESSAGE) if target.lower().endswith(".pdf") else (0, "")
    key = WRITE_TOOLS.get(event.get("tool_name", ""))
    target = (event.get("tool_input") or {}).get(key) if key else None
    if not target:
        return 0, ""
    allowed, reason = write_allowed(event.get("agent_type"), target, root)
    return (0, "") if allowed else (2, reason)


def changed_outside(module: str, root: Path = ROOT) -> list[str]:
    """Paths (repo-relative) that git reports as modified, added, deleted or untracked outside the module."""
    out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=root,
                         capture_output=True, text=True, check=True).stdout
    folder = module_dir(module, root).relative_to(root).as_posix() + "/"
    paths = []
    for line in out.splitlines():
        path = line[3:].split(" -> ")[-1].strip('"')
        if not path.startswith(folder):
            paths.append(path)
    return paths


def main(argv: list[str]) -> int:
    if argv[:1] == ["hook"]:
        code, msg = hook(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
        if msg:
            sys.stderr.buffer.write((msg + "\n").encode("utf-8"))
        return code
    if len(argv) == 2 and argv[0] == "check":
        outside = changed_outside(argv[1])
        for path in outside:
            print(f"outside {argv[1]}: {path}")
        return 1 if outside else 0
    print("usage: python -m core.scope hook | check <module>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
