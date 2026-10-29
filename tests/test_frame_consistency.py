"""Read-only guard: the M2 geometry frame copy (layout.py, R-G2.1) must equal the M1 frame (frame.py).

M1 and M2 each hold their own copy of the frame constants (shared frame module deferred, open_issues #74).
Constants are read with ast from the source files; neither module is imported or changed.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
M1_FRAME = ROOT / "engine" / "M1_inlet_fan" / "geometry" / "frame.py"
M2_FRAME = ROOT / "engine" / "M2_booster" / "geometry" / "layout.py"
NAMES = ("AXIS_ORIGIN", "AXIS_DIR", "ROTATION_SIGN")


def frame_constants(path: Path) -> dict:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in NAMES:
                out[node.targets[0].id] = ast.literal_eval(node.value)
    return out


@pytest.mark.parametrize("name", NAMES)
def test_m2_frame_matches_m1(name):
    m1, m2 = frame_constants(M1_FRAME), frame_constants(M2_FRAME)
    assert name in m1 and name in m2, f"{name} missing from a frame file"
    assert m2[name] == m1[name], f"{name}: M2 {m2[name]} != M1 {m1[name]}"
