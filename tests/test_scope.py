"""core/scope.py: module write scope (hook and git check)."""

import json
import subprocess
import sys
from pathlib import Path

from core.scope import PDF_READ_MESSAGE, agent_module, changed_outside, hook

ROOT = Path(__file__).resolve().parents[1]


def event(agent, path, tool="Write"):
    data = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"file_path": str(path)}}
    if agent:
        data["agent_type"] = agent
    return json.dumps(data)


def test_agent_module():
    assert agent_module("m1-inlet-fan") == "M1"
    assert agent_module(None) is None and agent_module("Explore") is None


def test_hook_allows_module_folder_and_main_session():
    assert hook(event("m1-inlet-fan", ROOT / "engine" / "M1_inlet_fan" / "rules" / "x.md"))[0] == 0
    assert hook(event(None, ROOT / "core" / "bom.py"))[0] == 0
    assert hook(event("Explore", ROOT / "core" / "bom.py"))[0] == 0


def test_hook_blocks_writes_outside_module():
    code, msg = hook(event("m1-inlet-fan", ROOT / "core" / "bom.py", tool="Edit"))
    assert code == 2 and "engine/M1_inlet_fan/" in msg
    assert hook(event("m1-inlet-fan", ROOT / "engine" / "M1_inlet_fan" / ".." / "M2_booster" / "x.md"))[0] == 2
    assert hook(event("m1-inlet-fan", ROOT / "engine" / "M0_engine" / "rules" / "icd.yaml"))[0] == 2


def test_hook_ignores_other_tools_and_bad_input():
    assert hook(json.dumps({"tool_name": "Bash", "agent_type": "m1-inlet-fan", "tool_input": {"command": "ls"}}))[0] == 0
    assert hook("not json")[0] == 0


def test_hook_blocks_pdf_reads_for_everyone():
    for agent in (None, "m1-inlet-fan", "Explore"):
        code, msg = hook(event(agent, "C:/Tools/TurbofanSources/M1_inlet_fan/aero/r67.PDF", tool="Read"))
        assert code == 2 and msg == PDF_READ_MESSAGE
    assert hook(event(None, ROOT / "engine" / "M1_inlet_fan" / "learning" / "sources" / "INDEX.md", tool="Read"))[0] == 0
    assert hook(event("m1-inlet-fan", ROOT / "core" / "bom.py", tool="Read"))[0] == 0


def test_hook_command_line_exit_code():
    out = subprocess.run([sys.executable, "-m", "core.scope", "hook"], cwd=ROOT, capture_output=True,
                         input=event("m1-inlet-fan", ROOT / "README.md").encode("utf-8"))
    assert out.returncode == 2 and b"blocked" in out.stderr


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_changed_outside_lists_files_outside_module(tmp_path):
    for d in ("engine/M1_inlet_fan/bom", "engine/M0_engine", "core"):
        (tmp_path / d).mkdir(parents=True)
    git(tmp_path, "init", "-q")
    git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init")
    assert changed_outside("M1", tmp_path) == []
    (tmp_path / "engine/M1_inlet_fan/bom/bom.yaml").write_text("x")
    assert changed_outside("M1", tmp_path) == []
    (tmp_path / "core/new.py").write_text("x")
    (tmp_path / "engine/M0_engine/a.yaml").write_text("x")
    assert sorted(changed_outside("M1", tmp_path)) == ["core/new.py", "engine/M0_engine/a.yaml"]
