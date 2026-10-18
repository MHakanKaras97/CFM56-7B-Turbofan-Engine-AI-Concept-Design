"""Concept layout reference: schematic engine SVG and layout check.

Reads docs/design/concept_reference.yaml and writes docs/design/engine_reference.svg, an upper
half-section along the engine axis (schematic, not to scale). The SVG depends only on the YAML,
so regenerating it gives identical bytes.

check_layout() compares a module layout (order, stage counts) with the reference; module agents
use it from M1 on.

Usage:
    python -m tools.reference
"""

import sys
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_FILE = ROOT / "docs" / "design" / "concept_reference.yaml"
SVG_FILE = ROOT / "docs" / "design" / "engine_reference.svg"

# schematic drawing data (px): axial width per module, annulus outer radius at inlet and exit
X0, AXIS_Y = 60, 330
SHAPE = {
    "M1": (110, 250, 250),
    "M2": (96, 118, 112),
    "M3": (216, 104, 62),
    "M4": (100, 76, 76),
    "M5": (44, 78, 84),
    "M6": (152, 90, 132),
    "M7": (96, 116, 70),
}
STAGE_PITCH = {"M2": 32, "M3": 24, "M5": 44, "M6": 38}
HUB = {"M1": 70, "M2": 72, "M3": 44, "M4": 40, "M5": 46, "M6": 52, "M7": 26}
COLORS = {"M1": "#3b82f6", "M2": "#06b6d4", "M3": "#10b981", "M4": "#f59e0b",
          "M5": "#ef4444", "M6": "#a855f7", "M7": "#64748b"}
BYPASS_IN, BYPASS_OUT = 196, 250  # bypass duct radii: inner (core cowl) and outer (fan case)


def load_reference(path: Path = REFERENCE_FILE) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _stages(ref: dict, module: str) -> int:
    s = ref["modules"]["items"][module]["stages"]
    return 0 if s is None else int(s["value"])


def module_x(ref: dict) -> dict[str, tuple[int, int]]:
    """Axial start and end (px) of each module in gas-path order."""
    out, x = {}, X0
    for m in ref["modules"]["order"]:
        out[m] = (x, x + SHAPE[m][0])
        x += SHAPE[m][0]
    return out


def station_x(ref: dict) -> dict[str, tuple[int, int]]:
    """Station marker position (x, radius) in px."""
    mx = module_x(ref)
    r_in = {m: SHAPE[m][1] for m in SHAPE}
    r_out = {m: SHAPE[m][2] for m in SHAPE}
    return {
        "2": (mx["M1"][0], 236), "13": (mx["M1"][1], 236), "21": (mx["M1"][1], 100),
        "25": (mx["M2"][1], r_out["M2"] - 10), "3": (mx["M3"][1], r_out["M3"] - 6),
        "31": (mx["M4"][0] + 16, r_in["M4"] - 6), "4": (mx["M4"][1], r_out["M4"] - 6),
        "41": (mx["M5"][0] + 14, r_in["M5"] - 6), "44": (mx["M5"][1], r_out["M5"] - 6),
        "45": (mx["M6"][0] + 14, r_in["M6"] - 4), "5": (mx["M6"][1], r_out["M6"] - 8),
        "8": (mx["M7"][1], r_out["M7"] - 6), "18": (mx["M4"][1], 236),
    }


def build_svg(ref: dict) -> str:
    mx = module_x(ref)
    end = mx[ref["modules"]["order"][-1]][1]
    width, height = end + 60, AXIS_Y + 150
    y = lambda r: AXIS_Y - r  # noqa: E731  radius (px) to SVG y
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" font-family="sans-serif" font-size="12">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{X0}" y="28" font-size="16" font-weight="bold">CFM56-7B27 class: concept layout reference</text>',
        f'<text x="{X0}" y="46" fill="#475569">Schematic, not to scale. Upper half-section; flow left to right. '
        f'Envelope length {ref["envelope"]["length"]["value"]:g} mm [K], fan diameter about '
        f'{ref["envelope"]["fan_diameter"]["value"]:g} in [KS].</text>',
    ]
    # bypass duct from fan exit to the bypass nozzle (end of M4 region)
    x13, x18 = mx["M1"][1], station_x(ref)["18"][0]
    out.append(f'<path d="M{x13} {y(BYPASS_OUT)} L{x18} {y(BYPASS_OUT - 14)} L{x18} {y(BYPASS_IN + 6)} '
               f'L{x13} {y(BYPASS_IN)} Z" fill="#e2e8f0" stroke="#64748b"/>')
    out.append(f'<text x="{(x13 + x18) // 2}" y="{y(BYPASS_IN) - 14}" text-anchor="middle" fill="#334155">'
               f'bypass duct + fan nozzle (M7)</text>')
    # modules: annulus between hub and outer radius
    for m in ref["modules"]["order"]:
        x1, x2 = mx[m]
        _, r1, r2 = SHAPE[m]
        h = HUB[m]
        item = ref["modules"]["items"][m]
        out.append(f'<path d="M{x1} {y(r1)} L{x2} {y(r2)} L{x2} {y(h)} L{x1} {y(h)} Z" '
                   f'fill="{COLORS[m]}" fill-opacity="0.25" stroke="{COLORS[m]}" stroke-width="1.5"/>')
        n = _stages(ref, m)
        if m == "M1":
            out.append(f'<line x1="{x1 + 50}" y1="{y(250)}" x2="{x1 + 50}" y2="{y(h)}" '
                       f'stroke="{COLORS[m]}" stroke-width="6"/>')
        elif n:
            pitch = STAGE_PITCH[m]
            for k in range(n):
                xs = x1 + pitch // 2 + k * pitch
                rs = r1 + (r2 - r1) * (xs - x1) / (x2 - x1)
                out.append(f'<line x1="{xs}" y1="{y(round(rs) - 4)}" x2="{xs}" y2="{y(h + 4)}" '
                           f'stroke="{COLORS[m]}" stroke-width="3"/>')
        label = f'{m} {item["component"]}' + (f' ({n})' if n else "")
        out.append(f'<text x="{(x1 + x2) // 2}" y="{AXIS_Y + 22}" text-anchor="middle" '
                   f'fill="{COLORS[m]}" font-weight="bold">{escape(m)}</text>')
        out.append(f'<text x="{(x1 + x2) // 2}" y="{AXIS_Y + 38}" text-anchor="middle" fill="#334155" '
                   f'font-size="10">{escape(label[len(m) + 1:])}</text>')
    # engine axis and shafts (LP inside HP)
    out.append(f'<line x1="{X0 - 20}" y1="{AXIS_Y}" x2="{end + 30}" y2="{AXIS_Y}" '
               f'stroke="#0f172a" stroke-dasharray="10 4 2 4"/>')
    out.append(f'<text x="{end + 30}" y="{AXIS_Y - 6}" text-anchor="end" fill="#0f172a" font-size="10">'
               f'engine axis</text>')
    shafts = ref["shafts"]
    for name, r, color in (("LP", 14, "#2563eb"), ("HP", 30, "#dc2626")):
        s = shafts[name]
        xa = mx[s["drives"][0]][0] + (30 if name == "LP" else 10)
        xb = mx[s["driven_by"]][1] - 10
        out.append(f'<rect x="{xa}" y="{y(r + 4)}" width="{xb - xa}" height="8" fill="{color}" fill-opacity="0.8"/>')
        out.append(f'<text x="{xa + 4}" y="{y(r + 4) - 3}" fill="{color}" font-size="10">'
                   f'{name} shaft: {", ".join(s["drives"])} &lt;- {s["driven_by"]}</text>')
    # stations in reference order
    for k, (s, (xs, rs)) in enumerate((s, station_x(ref)[s]) for s in ref["stations"]["order"]):
        out.append(f'<circle cx="{xs}" cy="{y(rs)}" r="3" fill="#0f172a"/>')
        dy = -8 if k % 2 == 0 else 14
        out.append(f'<text x="{xs + 3}" y="{y(rs) + dy}" fill="#0f172a" font-size="10">{escape(s)}</text>')
    # radius rules
    for k, rule in enumerate(ref["radius_rules"]["rules"]):
        out.append(f'<text x="{X0}" y="{AXIS_Y + 66 + 16 * k}" fill="#475569" font-size="11">'
                   f'[{ref["radius_rules"]["tag"]}] {escape(rule)}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def write_svg(ref: dict | None = None, path: Path = SVG_FILE) -> Path:
    ref = load_reference() if ref is None else ref
    Path(path).write_text(build_svg(ref), encoding="utf-8", newline="\n")
    return Path(path)


def check_layout(layout: dict, ref: dict | None = None) -> list[str]:
    """Compare a module layout with the reference; returns problems (empty list = consistent).

    layout: {"module_order": [...], "stage_counts": {module: n}}; missing keys are not checked.
    Stub: only order and stage counts for now; radius trends follow when modules have geometry.
    """
    ref = load_reference() if ref is None else ref
    problems = []
    order = layout.get("module_order")
    if order is not None:
        expected = [m for m in ref["modules"]["order"] if m in order]
        if list(order) != expected:
            problems.append(f"module order {list(order)} differs from reference {expected}")
    for m, n in layout.get("stage_counts", {}).items():
        if m not in ref["modules"]["items"]:
            problems.append(f"{m}: not in the reference")
        elif _stages(ref, m) != n:
            problems.append(f"{m}: {n} stages, reference {_stages(ref, m)}")
    return problems


def main(argv: list[str]) -> int:
    path = write_svg()
    print(f"wrote {path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
