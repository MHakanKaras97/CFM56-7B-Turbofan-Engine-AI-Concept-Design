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


def _read_local(root: Path) -> dict:
    cfg = local_config(root)
    if not cfg.is_file():
        raise ToolPathError(f"{cfg} not found; copy config/tools.example.yaml and set the paths")
    return read_yaml(cfg) or {}


def sources_archive(root: Path = ROOT) -> Path:
    """Folder holding the source documents outside the repo (<archive>/<module>/...); must exist."""
    value = _read_local(root).get("sources_archive")
    if not value:
        raise ToolPathError(f"sources_archive: not in {local_config(root).name}")
    path = Path(value)
    if not path.is_dir():
        raise ToolPathError(f"sources_archive: {path} does not exist")
    return path


def tool_path(name: str, root: Path = ROOT) -> Path:
    """Executable path of tool `name` from tools.local.yaml; the file must exist and point to a file."""
    cfg = local_config(root)
    tools = _read_local(root).get("tools") or {}
    if name not in tools:
        raise ToolPathError(f"{name}: not in {cfg.name}")
    path = Path(tools[name]["path"])
    if not path.is_file():
        raise ToolPathError(f"{name}: {path} does not exist")
    return path
