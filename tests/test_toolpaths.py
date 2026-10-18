import subprocess

import pytest

from core.records import ROOT
from core.toolpaths import ToolPathError, local_config, tool_path
from core.util import read_yaml

needs_local = pytest.mark.skipif(not local_config().is_file(), reason="config/tools.local.yaml not on this machine")


def test_example_lists_the_known_tools():
    example = read_yaml(ROOT / "config" / "tools.example.yaml")["tools"]
    assert set(example) == {"ccx", "pvpython"}


def test_missing_config_or_tool_is_reported(tmp_path):
    with pytest.raises(ToolPathError):
        tool_path("ccx", root=tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "tools.local.yaml").write_text("tools: {}\n", encoding="utf-8")
    with pytest.raises(ToolPathError):
        tool_path("ccx", root=tmp_path)


@needs_local
def test_ccx_runs_from_configured_path():
    ccx = tool_path("ccx")
    no_input = subprocess.run([str(ccx)], capture_output=True, text=True, timeout=60)
    assert "Usage" in no_input.stdout + no_input.stderr  # no input: usage line only
    version = subprocess.run([str(ccx), "-v"], capture_output=True, text=True, timeout=60)
    assert "Version" in version.stdout


@needs_local
def test_pvpython_path_configured():
    assert tool_path("pvpython").name.lower() == "pvpython.exe"
