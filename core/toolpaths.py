"""External tool paths, read only from config/tools.local.yaml (machine-specific, git-ignored).

The committed template is config/tools.example.yaml. No tool path is hardcoded in code.
"""

from pathlib import Path

from core.records import ROOT
from core.util import read_yaml


class ToolPathError(Exception):
    pass


def local_config(root: Path = ROOT) -> Path:
    return root / "config" / "tools.local.yaml"


def tool_path(name: str, root: Path = ROOT) -> Path:
    """Executable path of tool `name` from tools.local.yaml; the file must exist and point to a file."""
    cfg = local_config(root)
    if not cfg.is_file():
        raise ToolPathError(f"{cfg} not found; copy config/tools.example.yaml and set the paths")
    tools = read_yaml(cfg).get("tools") or {}
    if name not in tools:
        raise ToolPathError(f"{name}: not in {cfg.name}")
    path = Path(tools[name]["path"])
    if not path.is_file():
        raise ToolPathError(f"{name}: {path} does not exist")
    return path
