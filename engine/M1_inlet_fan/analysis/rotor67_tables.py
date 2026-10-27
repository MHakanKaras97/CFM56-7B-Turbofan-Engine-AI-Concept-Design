"""Extract NASA Rotor 67 tables from the scanned TP-2879 (Strazisar et al. 1989) [KS].

The PDF is a scan with an OCR text layer. `pdftotext -table` (xpdf) keeps table rows roughly aligned, but
the OCR splits decimals ("0 71202"), breaks rows over two lines, misplaces the K labels, reads letters for
digits (l, I, O, Z, B) and misreads digits (most often 3 as 5). This module:
- parses Table I (blade sections), Table II (flowpath) and Table III(b) station 2 (survey profile),
- repairs layout damage (split decimals, letters for digits) and lists every repair,
- runs plausibility checks and flags suspected misread values.

Table I geometry (rotor67_geometry.yaml) is then built as follows:
- Z, R, THSP1, THSP2 and the edge circle data come from a clean digital transcription of the same
  TP-2879 PDF (BladeAtlas, pinned commit, sha256-checked), after it is compared with every OCR value
  that passed the plausibility checks (agreement statistics in the output) [KS].
- TNPC, BETA, BETA1, BETA2 are not in the digital copy. They are read from the OCR layer and checked
  against values computed from the clean coordinates (normal thickness, camber and surface angles) [H].
  A value off that reference gets OCR digit substitutions (3<->5, 4<->6, 8<->3, up to two); the one
  with the fewest substitutions that lands within the tolerance is used, marked "repaired". Otherwise the
  value stays as read and flagged. A second pass replaces a last-digit misread when a one-digit
  substitution is much closer to the reference ("repaired_last_digit").
- Manual overrides (learning/rotor67_overrides.yaml: value, page-image evidence, verified_by) are applied
  last and logged with status "override".
- Table II (flowpath) has no digital copy: flagged values get the same substitutions against the robust
  smooth-column fit; repaired values are marked.

Run: python -m engine.M1_inlet_fan.analysis.rotor67_tables  (writes learning/rotor67_geometry.yaml
and learning/rotor67_survey.yaml; needs the PDF and the digital copy in the source archive, and
sources_archive and pdftotext in config/tools.local.yaml).
"""

import csv
import hashlib
import json
import math
import re
import subprocess
from itertools import combinations, product
from pathlib import Path

from core.toolpaths import sources_archive, tool_path
from core.util import read_yaml, write_yaml

M1 = Path(__file__).resolve().parents[1]
# Source files live in the source archive outside the repo (config/tools.local.yaml: sources_archive)
PDF_REL = Path("M1_inlet_fan") / "aero" / "strazisar_1989_nasa_tp2879_rotor67.pdf"
GEOMETRY_OUT = M1 / "learning" / "rotor67_geometry.yaml"
SURVEY_OUT = M1 / "learning" / "rotor67_survey.yaml"
REFERENCE = M1 / "learning" / "rotor67_reference.yaml"
OVERRIDES = M1 / "learning" / "rotor67_overrides.yaml"

SECTION_PAGES = range(23, 37)  # PDF pages of Table I, one blade section per page, hub (1) to casing (14)
FLOWPATH_PAGE = 37  # Table II
SURVEY_PAGE = 39  # Table III(b)
PRINTED_OFFSET = 4  # printed page = PDF page - 4
N_POINTS = 35
N_FLOWPATH = 80

ROW_FIELDS = ("Z", "R", "THSP1", "THSP2", "TNPC", "BETA", "BETA1", "BETA2")
ROW_DECIMALS = (5, 5, 5, 5, 5, 2, 2, 2)  # as printed in Table I
LETTERS = str.maketrans({"l": "1", "I": "1", "i": "1", "O": "0", "o": "0", "Z": "2", "B": "8"})
NUMBER = re.compile(r"^-?\d+\.\d+$")
OCR_SWAPS = {"5": "3", "3": "5", "6": "4", "4": "6", "8": "3", "1": "7", "7": "1"}

# Plausibility limits [T]: residual of a value against a local quadratic through its neighbours
SMOOTH_LIMIT = {"Z": 0.02, "R": 0.02, "THSP1": 0.004, "THSP2": 0.004, "TNPC": 0.008,
                "BETA": 0.8, "BETA1": 1.0, "BETA2": 1.0}
SECTION_LIMIT = {"le_radius": 0.15, "te_radius": 0.15, "le_metal_angle": 1.5, "te_metal_angle": 3.0,
                 "meridional_chord": 0.3, "chord": 0.3, "max_thickness": 0.05}
THICKNESS_MAX_FRACTION = 0.15  # max thickness / meridional chord upper bound [T]
EDGE_MATCH = 0.003  # cm: LE circle centre meridional coordinate equals the LE circle radius [T]

# Clean digital copy of Table I (Z, R, THSP1, THSP2 and edge circles), see docs/sources.md
DIGITAL_REL = Path("M1_inlet_fan") / "aero" / "bladeatlas_rotor67"
DIGITAL_FILES = {
    "table": ("rotor67_tp2879_table1.csv", "81d84a82d9fcecfcebd20478ace1a705e1f745141fa9d776977a4958a70ed936"),
    "edges": ("rotor67_tp2879_edge_circles.csv", "eb513c30121ada06afc52a550b696c24d4b8a4027e518fda4ffdb5ae0af99a22"),
}
DIGITAL_SOURCE = {
    "name": "BladeAtlas (naoyamd/BladeAtlas), src/turbinebladegen/data/rotor67_tp2879_*.csv",
    "url": "https://github.com/naoyamd/BladeAtlas",
    "commit": "ec4097351164333b6f544e710cc0964257841dd8",
    "transcribed_from": "NASA TP-2879 PDF, NTRS 19900001929, sha256 f570c421...0d2e1 (same file as ours)",
    "license": "data: US Government work, public use permitted (NTRS); repository code: MIT",
    "columns": "Z, R, THSP1, THSP2 per point; edge circle radius and centre coordinates",
}
DIGITAL_FIELDS = ("Z", "R", "THSP1", "THSP2")
EDGE_FIELDS = {"radius": "radius_cm", "radial": "center_radial_cm", "axial": "center_axial_cm",
               "meridional": "center_meridional_cm", "angular": "center_angular_rad"}

# OCR repair: digit substitutions tried on a value off its reference (user rule, M1 step 2b)
REPAIR_SWAPS = {"3": "58", "5": "3", "4": "6", "6": "4", "8": "3"}
MAX_SWAPS = 2
# Tolerance of an OCR value against the value computed from the clean coordinates [T]; the reference is
# a three-point derivative (angles) or r x dtheta x cos(beta) (thickness), good to about the p95 spread
# of the agreeing values (0.2 deg, 0.001 cm), with margin at the blade edges.
DERIVED_TOL = {"TNPC": 0.004, "BETA": 0.6, "BETA1": 0.6, "BETA2": 0.6}
DERIVED_FIELDS = ("TNPC", "BETA", "BETA1", "BETA2")
# Last-digit pass [T]: a value FINE_FLOOR to FINE_CEILING off the reference is replaced by a one-digit
# substitution that is FINE_RATIO times closer to it (the reference is good to about 0.0001 cm and 0.01 deg
# inside the blade; a 3/5 misread in the last digits moves a value by 0.0002 cm or 0.02 deg). Larger
# angle differences are left alone: at the blade edges the one-sided reference is off by up to 0.2 deg.
FINE_FLOOR = {"TNPC": 0.00015, "BETA": 0.015, "BETA1": 0.015, "BETA2": 0.015}
FINE_CEILING = {"TNPC": 0.004, "BETA": 0.05, "BETA1": 0.05, "BETA2": 0.05}
FINE_RATIO = 3.0
# Table II repair limits [T]: Z is printed at an even spacing, so a straight line fits it to the last digit
FLOWPATH_LIMIT = {"Z": 0.001, "R_hub": 0.02, "R_shroud": 0.02}


def pdf_path() -> Path:
    return sources_archive() / PDF_REL


def digital_dir() -> Path:
    return sources_archive() / DIGITAL_REL


def page_text(page: int, pdf: Path) -> str:
    exe = tool_path("pdftotext")
    out = subprocess.run([str(exe), "-table", "-f", str(page), "-l", str(page), str(pdf), "-"],
                         capture_output=True, check=True)
    return out.stdout.decode("latin-1")


def _clean(token: str) -> str:
    return token.translate(LETTERS)


def read_stream(tokens: list[str], decimals: tuple[int, ...], n_rows: int,
                inferred: list | None = None) -> tuple[list[list], list[str]]:
    """Fill rows of len(decimals) numbers from a token stream. Bare integers of one or two digits that
    are not the head of a split decimal are row labels (K) and are skipped; longer bare integers are
    values whose decimal point was lost (position recorded in `inferred` as (row, field index)).
    Returns rows (None = unreadable) and repairs."""
    rows, row, repairs = [], [], []
    inferred = [] if inferred is None else inferred
    i = 0
    while i < len(tokens) and len(rows) < n_rows:
        raw = tokens[i]
        tok = _clean(raw)
        d = decimals[len(row)]
        nxt = _clean(tokens[i + 1]) if i + 1 < len(tokens) else ""
        if re.fullmatch(r"-?\d+\.?", tok) and re.fullmatch(r"\d+", nxt) and len(nxt) == d:
            value_txt, used = f"{tok.rstrip('.')}.{nxt}", 2
        elif re.fullmatch(r"-?\d+", tok) and re.fullmatch(r"\.\d+", nxt):
            value_txt, used = tok + nxt, 2
        elif re.fullmatch(r"-?\d+\.", tok) and nxt:
            value_txt, used = tok + nxt, 2  # fraction split off with an unreadable character
        elif re.fullmatch(r"-?\d{3,}", tok) and len(tok.lstrip("-")) > d:
            value_txt, used = f"{tok[:-d]}.{tok[-d:]}", 1  # decimal point lost; K labels have <= 2 digits
            inferred.append((len(rows) + 1, len(row)))
        elif re.fullmatch(r"-?\d+", tok):
            i += 1  # row label or stray integer
            continue
        else:
            value_txt, used = tok, 1
        source = " ".join(tokens[i:i + used])
        if used == 2 or tok != raw or (inferred and inferred[-1] == (len(rows) + 1, len(row))):
            repairs.append(f"row {len(rows) + 1} {ROW_FIELDS[len(row)] if len(decimals) == 8 else len(row)}: "
                           f"'{source}' -> {value_txt}")
        row.append(float(value_txt) if NUMBER.match(value_txt) else None)
        if row[-1] is None:
            repairs.append(f"row {len(rows) + 1}: unreadable '{source}'")
        i += used
        if len(row) == len(decimals):
            rows.append(row)
            row = []
    return rows, repairs


def _edge_data(lines: list[str]) -> tuple[dict, list[str]]:
    """Leading/trailing edge circle radius and centre coordinates, then the meridional and angular
    coordinates of the edge tangency points on blade surfaces 1 and 2 (used as cross-checks)."""
    labels = {"radius": r"CIRCLE\s+RADIUS", "radial": r"RADIAL", "axial": r"AXIA\w*", "meridional": r"MERIDION\w*",
              "angular": r"ANGULA\w*"}
    out, repairs, block = {}, [], "centre"
    for line in lines:
        surface = re.search(r"TANGENCY.*SURFACE\s+(\S+)", line, re.I)
        if surface:
            block = "tangency_" + _clean(surface.group(1))
            continue
        for name, pattern in labels.items():
            m = re.match(rf"\s*{pattern}\s+(.*)$", line, re.I)
            key = name if block == "centre" else f"{block}_{name}"
            if key not in out and m and (block == "centre" or name in ("meridional", "angular")):
                rows, rep = read_stream(m.group(1).split(), (5, 5), 1)
                if not rows:  # trailing edge value missing on this line
                    single, rep = read_stream(m.group(1).split(), (5,), 1)
                    rows = [[single[0][0], None]] if single else [[None, None]]
                out[key] = {"le": rows[0][0], "te": rows[0][1]}
                repairs += [f"edge {key}: {r}" for r in rep]
    return out, repairs


def odd_one_out(values: dict[str, float | None], tol: float) -> list[str]:
    """Names of values that disagree with the others when they should be (nearly) equal: if some pair
    agrees within tol, every value off that pair by more than tol is odd; if no pair agrees, all are."""
    known = {k: v for k, v in values.items() if v is not None}
    pairs = [(abs(known[a] - known[b]), a, b) for i, a in enumerate(known) for b in list(known)[i + 1:]]
    good = [(d, a, b) for d, a, b in pairs if d <= tol]
    if not good:
        return list(known) if len(known) > 1 else []
    _, a, b = min(good)
    ref = (known[a] + known[b]) / 2
    return [k for k, v in known.items() if abs(v - ref) > tol]


def parse_section(text: str) -> dict:
    lines = text.splitlines()
    head = next(i for i, l in enumerate(lines) if re.search(r"\bZ\s+R\s+THSP", l))
    edge, repairs = _edge_data(lines[:head])
    tokens = " ".join(lines[head + 1:]).split()
    inferred: list[tuple[int, int]] = []
    rows, rep = read_stream(tokens, ROW_DECIMALS, N_POINTS, inferred)
    return {"edge": edge, "rows": [dict(zip(ROW_FIELDS, r)) for r in rows], "repairs": repairs + rep,
            "inferred": [(k, ROW_FIELDS[f]) for k, f in inferred]}


def _weighted_quadratic(xs: list[float], ys: list[float], ws: list[float]) -> list[float] | None:
    """Coefficients c0, c1, c2 of the weighted least-squares quadratic y = c0 + c1 x + c2 x^2."""
    s = [sum(w * x ** k for x, w in zip(xs, ws)) for k in range(5)]
    b = [sum(w * y * x ** k for x, y, w in zip(xs, ys, ws)) for k in range(3)]
    m = [[s[0], s[1], s[2]], [s[1], s[2], s[3]], [s[2], s[3], s[4]]]

    def det(a):
        return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
                + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))

    d = det(m)
    if abs(d) < 1e-12:
        return None
    coef = []
    for c in range(3):
        mc = [row[:] for row in m]
        for r in range(3):
            mc[r][c] = b[r]
        coef.append(det(mc) / d)
    return coef


def neighbour_fit(values: list[float | None], i: int, scale: float, window: int = 4) -> float | None:
    """Robust estimate of values[i] from the points within +-window (i left out). Least median of
    squares: of the quadratics through every 3 neighbours, take the one with the smallest median
    residual over all neighbours (tolerates up to half of them misread), then refit by least squares
    on its inliers (residual within 3 x max(median, scale))."""
    pts = [(float(j - i), values[j]) for j in range(max(0, i - window), min(len(values), i + window + 1))
           if j != i and values[j] is not None]
    if len(pts) < 4:
        return None
    best, best_med = None, None
    for trio in combinations(pts, 3):
        coef = _weighted_quadratic([x for x, _ in trio], [y for _, y in trio], [1.0, 1.0, 1.0])
        if coef is None:
            continue
        res = sorted(abs(y - (coef[0] + coef[1] * x + coef[2] * x * x)) for x, y in pts)
        med = res[len(res) // 2]
        if best_med is None or med < best_med:
            best, best_med = coef, med
    if best is None:
        return None
    cut = 3 * max(best_med, scale)
    inl = [(x, y) for x, y in pts if abs(y - (best[0] + best[1] * x + best[2] * x * x)) <= cut]
    if len(inl) >= 4:
        refit = _weighted_quadratic([x for x, _ in inl], [y for _, y in inl], [1.0] * len(inl))
        best = refit or best
    return best[0]


def robust_outliers(values: list[float | None], limit: float, end_factor: float = 2.0) -> dict[int, float]:
    """{index: robust neighbour fit} for values further than `limit` from it. The two points at each end
    are extrapolated from one side, so their limit is multiplied by `end_factor` [T]."""
    out = {}
    n = len(values)
    for i, v in enumerate(values):
        fit = neighbour_fit(values, i, limit / 4)
        if v is None or fit is None:
            continue
        if abs(v - fit) > limit * (end_factor if i < 2 or i > n - 3 else 1.0):
            out[i] = fit
    return out


def ocr_candidates(value: float, fit: float, limit: float, decimals: int) -> list[float]:
    """Single-digit OCR substitutions of `value` that land within `limit` of the neighbour fit."""
    text = f"{value:.{decimals}f}"
    out = []
    for pos, ch in enumerate(text):
        if ch in OCR_SWAPS:
            cand = float(text[:pos] + OCR_SWAPS[ch] + text[pos + 1:])
            if abs(cand - fit) <= limit:
                out.append(cand)
    return out


def check_column(values, limit, decimals, labels) -> list[dict]:
    flags = []
    for i, v in enumerate(values):
        if v is None:
            flags.append({"check": "unreadable", **labels(i)})
    for i, fit in sorted(robust_outliers(values, limit).items()):
        flags.append({"check": "not_smooth", **labels(i), "read": values[i], "neighbour_fit": round(fit, decimals),
                      "ocr_candidates": ocr_candidates(values[i], fit, limit, decimals)})
    return flags


def check_section(sec: dict) -> list[dict]:
    flags = []
    rows = sec["rows"]
    if len(rows) != N_POINTS:
        flags.append({"check": "row_count", "found": len(rows), "expected": N_POINTS})
    for field, d in zip(ROW_FIELDS, ROW_DECIMALS):
        flags += check_column([r[field] for r in rows], SMOOTH_LIMIT[field], d,
                              lambda i, f=field: {"field": f, "K": i + 1})
    for k, field in sec["inferred"]:
        flags.append({"check": "decimal_point_inferred", "field": field, "K": k, "read": rows[k - 1][field]})
    z = [r["Z"] for r in rows]
    for i in range(1, len(z)):
        if None not in (z[i], z[i - 1]) and z[i] <= z[i - 1]:
            flags.append({"check": "z_not_increasing", "field": "Z", "K": i + 1, "read": z[i], "previous": z[i - 1]})
    for i, r in enumerate(rows):
        if r["TNPC"] is not None and r["TNPC"] < 0:
            flags.append({"check": "thickness_negative", "field": "TNPC", "K": i + 1, "read": r["TNPC"]})
    edge = sec["edge"]
    m_le, r_le = edge.get("meridional", {}).get("le"), edge.get("radius", {}).get("le")
    if None in (m_le, r_le) or abs(m_le - r_le) > EDGE_MATCH:
        flags.append({"check": "edge_le_meridional_vs_radius", "field": "edge", "meridional": m_le, "radius": r_le})
    for coord, tol in (("angular", 0.02), ("meridional", 0.1)):
        te = {"centre": edge.get(coord, {}).get("te"),
              "surface_1": edge.get(f"tangency_1_{coord}", {}).get("te"),
              "surface_2": edge.get(f"tangency_2_{coord}", {}).get("te")}
        odd = odd_one_out(te, tol)
        if odd:
            flags.append({"check": f"edge_te_{coord}_vs_tangency", "field": "edge" if "centre" in odd else "tangency",
                          "values": te, "odd": odd})
    r_k1, rad_le = (rows[0]["R"] if rows else None), edge.get("radial", {}).get("le")
    if None in (r_k1, rad_le) or abs(r_k1 - rad_le) > 0.05:
        flags.append({"check": "edge_le_radial_vs_R_K1", "field": "edge", "edge": rad_le, "R_K1": r_k1})
    return flags


def section_summary(sec: dict, flags: list[dict]) -> dict:
    rows, edge = sec["rows"], sec["edge"]
    flagged = {(f.get("field"), f.get("K")) for f in flags}
    edge_flagged = any(f.get("field") == "edge" for f in flags)

    def point(field, k):
        v = rows[k - 1][field] if len(rows) >= k else None
        return {"value": v, "flagged": (field, k) in flagged or v is None}

    good = [(r["TNPC"], k) for k, r in enumerate(rows, 1) if r["TNPC"] is not None and ("TNPC", k) not in flagged]
    t_max, k_max = max(good) if good else (None, None)
    m, rad = edge.get("meridional", {}), edge.get("radius", {})
    ang, radial = edge.get("angular", {}), edge.get("radial", {})
    chord = true_chord = None
    if None not in (m.get("le"), m.get("te"), rad.get("le"), rad.get("te")):
        chord = round((m["te"] + rad["te"]) - (m["le"] - rad["le"]), 5)
        if None not in (ang.get("le"), ang.get("te"), radial.get("le"), radial.get("te")):
            r_mean = (radial["le"] + radial["te"]) / 2
            true_chord = round(math.hypot(chord, r_mean * (ang["te"] - ang["le"])), 5)
    out = {
        "le_radius": {"value": edge.get("radial", {}).get("le"), "unit": "cm", "tag": "KS", "flagged": edge_flagged,
                      "note": "radial coordinate of the leading edge circle centre"},
        "te_radius": {"value": edge.get("radial", {}).get("te"), "unit": "cm", "tag": "KS", "flagged": edge_flagged,
                      "note": "radial coordinate of the trailing edge circle centre"},
        "le_metal_angle": dict(point("BETA", 1), unit="deg", tag="KS", note="BETA at K=1"),
        "te_metal_angle": dict(point("BETA", N_POINTS), unit="deg", tag="KS", note="BETA at K=35"),
        "meridional_chord": {"value": chord, "unit": "cm", "tag": "H", "flagged": edge_flagged or chord is None,
                             "note": "(TE centre + TE circle radius) - (LE centre - LE circle radius), meridional"},
        "chord": {"value": true_chord, "unit": "cm", "tag": "H", "flagged": edge_flagged or true_chord is None,
                  "note": "hypot(meridional chord, mean edge radius x change of edge-centre angular coordinate)"},
        "edge_angular": {"le": ang.get("le"), "te": ang.get("te"), "unit": "rad", "tag": "KS"},
        "max_thickness": {"value": t_max, "unit": "cm", "tag": "KS", "at_K": k_max, "flagged": t_max is None,
                          "note": "largest unflagged TNPC"},
        "edge_circle_radius": {"le": rad.get("le"), "te": rad.get("te"), "unit": "cm", "tag": "KS"},
    }
    if chord and t_max is not None and not 0 < t_max / chord < THICKNESS_MAX_FRACTION:
        flags.append({"check": "thickness_bounds", "field": "TNPC", "ratio": round(t_max / chord, 4)})
        out["max_thickness"]["flagged"] = True
    return out


def check_across_sections(sections: list[dict]) -> list[dict]:
    """Section summary values against neighbouring sections (spanwise smoothness)."""
    flags = []
    n = len(sections)
    for key, limit in SECTION_LIMIT.items():
        values = [s[key]["value"] for s in sections]
        outliers = robust_outliers(values, limit)
        for i, fit in sorted(outliers.items()):
            flags.append({"check": "not_smooth_spanwise", "field": key, "section": i + 1, "read": values[i],
                          "neighbour_fit": round(fit, 5), "ocr_candidates": ocr_candidates(values[i], fit, limit, 5 if "angle" not in key else 2)})
            sections[i][key]["flagged"] = True
        # At the hub and casing ends the fit is an extrapolation and cannot tell which of the two end
        # sections is misread, so a flag on either marks both as ambiguous.
        for pair in ((0, 1), (n - 2, n - 1)):
            if any(i in outliers for i in pair):
                for i in pair:
                    if i not in outliers:
                        flags.append({"check": "ambiguous_end_pair", "field": key, "section": i + 1, "read": values[i]})
                        sections[i][key]["flagged"] = True
    return flags


def read_digital(folder: Path) -> tuple[dict, dict]:
    """Digital copy: ({section: [row dict of DIGITAL_FIELDS] x 35}, {section: edge dict as _edge_data}).
    Refused if a file differs from the pinned sha256."""
    paths = {}
    for key, (name, sha) in DIGITAL_FILES.items():
        paths[key] = folder / name
        if hashlib.sha256(paths[key].read_bytes()).hexdigest() != sha:
            raise ValueError(f"{name}: sha256 differs from the pinned copy")
    rows: dict[int, list[dict]] = {}
    with paths["table"].open(newline="") as f:
        for r in csv.DictReader(f):
            rows.setdefault(int(r["surface"]), []).append(
                dict(zip(DIGITAL_FIELDS, (float(r[c]) for c in ("z_cm", "r_cm", "thsp1_rad", "thsp2_rad")))))
    edges: dict[int, dict] = {}
    with paths["edges"].open(newline="") as f:
        for r in csv.DictReader(f):
            edge = edges.setdefault(int(r["surface"]), {k: {} for k in EDGE_FIELDS})
            for key, column in EDGE_FIELDS.items():
                edge[key][r["edge"].lower()] = float(r[column])
    return rows, edges


def ocr_variants(value: float, decimals: int, max_swaps: int = MAX_SWAPS) -> list[tuple[float, int]]:
    """(value, number of substituted digits) for every way of applying up to max_swaps REPAIR_SWAPS."""
    text = f"{value:.{decimals}f}"
    spots = [i for i, ch in enumerate(text) if ch in REPAIR_SWAPS]
    out = []
    for n in range(1, max_swaps + 1):
        for pos in combinations(spots, n):
            for repl in product(*(REPAIR_SWAPS[text[i]] for i in pos)):
                chars = list(text)
                for i, ch in zip(pos, repl):
                    chars[i] = ch
                out.append((float("".join(chars)), n))
    return out


def ocr_explained(read: float, true: float, decimals: int) -> bool:
    """True if `read` is `true` with some digits misread as in REPAIR_SWAPS (read from true)."""
    a, b = f"{read:.{decimals}f}", f"{true:.{decimals}f}"
    return len(a) == len(b) and all(x == y or x in REPAIR_SWAPS.get(y, "") or y in REPAIR_SWAPS.get(x, "")
                                    for x, y in zip(a, b))


def compare_with_digital(ocr: list[dict], ocr_flags: list[list[dict]], rows: dict, edges: dict) -> dict:
    """Agreement of the digital copy with the OCR values, split by whether the OCR value passed the
    plausibility checks. A mismatch is 'ocr_digit' when the digits differ only by REPAIR_SWAPS pairs."""
    stats = {s: {"compared": 0, "equal": 0, "ocr_digit": 0, "other": 0} for s in ("unflagged", "flagged")}
    other = []
    for n, (sec, flags) in enumerate(zip(ocr, ocr_flags), 1):
        flagged = {(f.get("field"), f.get("K")) for f in flags}
        edge_flagged = any(f.get("field") == "edge" for f in flags)
        pairs = [(f, k, row[f], rows[n][k - 1][f], (f, k) in flagged, 5)
                 for k, row in enumerate(sec["rows"], 1) for f in DIGITAL_FIELDS]
        pairs += [(f"edge {key} {side}", 0, sec["edge"].get(key, {}).get(side), edges[n][key][side], edge_flagged, 5)
                  for key in EDGE_FIELDS for side in ("le", "te")]
        for field, k, read, true, is_flagged, d in pairs:
            s = stats["flagged" if is_flagged or read is None else "unflagged"]
            s["compared"] += 1
            if read is not None and round(read, d) == round(true, d):
                s["equal"] += 1
            elif read is not None and ocr_explained(read, true, d):
                s["ocr_digit"] += 1
            else:
                s["other"] += 1
                if not is_flagged and read is not None:
                    other.append({"section": n, "field": field, "K": k, "ocr": read, "digital": true})
    for s in stats.values():
        s["equal_fraction"] = round(s["equal"] / s["compared"], 4)
    return {"by_ocr_status": stats, "unflagged_other_mismatches": other,
            "note": "flagged = failed an OCR plausibility check or unreadable; ocr_digit = digits differ only "
                    "by 3/5, 4/6, 8/3 confusions; other = any remaining difference"}


def _derivative(xs: list[float], ys: list[float], i: int) -> float:
    """dy/dx at xs[i] from the quadratic through three neighbouring points (one-sided at the ends)."""
    j = min(max(i - 1, 0), len(xs) - 3)
    (x0, x1, x2), (y0, y1, y2), x = xs[j:j + 3], ys[j:j + 3], xs[i]
    return (y0 * (2 * x - x1 - x2) / ((x0 - x1) * (x0 - x2)) + y1 * (2 * x - x0 - x2) / ((x1 - x0) * (x1 - x2))
            + y2 * (2 * x - x0 - x1) / ((x2 - x0) * (x2 - x1)))


def derived_columns(rows: list[dict]) -> dict[str, list[float]]:
    """TNPC, BETA, BETA1, BETA2 computed from the clean coordinates [H]: angles = atan(r dtheta/dm) along
    the meridional distance m of the section, for the mean camber line (theta1 + theta2) / 2 and both
    surfaces; normal thickness = r (theta1 - theta2) cos(BETA)."""
    m = [0.0]
    for a, b in zip(rows, rows[1:]):
        m.append(m[-1] + math.hypot(b["Z"] - a["Z"], b["R"] - a["R"]))
    r = [p["R"] for p in rows]
    curves = {"BETA": [(p["THSP1"] + p["THSP2"]) / 2 for p in rows], "BETA1": [p["THSP1"] for p in rows],
              "BETA2": [p["THSP2"] for p in rows]}
    out = {f: [math.degrees(math.atan(r[i] * _derivative(m, th, i))) for i in range(len(rows))]
           for f, th in curves.items()}
    out["TNPC"] = [r[i] * (p["THSP1"] - p["THSP2"]) * math.cos(math.radians(out["BETA"][i]))
                   for i, p in enumerate(rows)]
    return out


def repair_value(read: float | None, reference: float, tol: float, decimals: int) -> tuple[float | None, str]:
    """(value, status): 'as_read' within tol of the reference; 'repaired' when an OCR substitution lands
    within tol (fewest substituted digits first, then closest to the reference); else 'unresolved'
    (kept as read). Within tol the reference cannot tell close candidates apart, so the smallest edit wins."""
    if read is None:
        return None, "unresolved"
    if abs(read - reference) <= tol:
        return read, "as_read"
    fits = [(n, abs(v - reference), v) for v, n in ocr_variants(read, decimals) if abs(v - reference) <= tol]
    if not fits:
        return read, "unresolved"
    return min(fits)[2], "repaired"


def fine_repair(read: float, reference: float, floor: float, ceiling: float, decimals: int) -> tuple[float, str]:
    """Last-digit pass on an 'as_read' or 'repaired' value: (value, 'as_read' or 'repaired_last_digit')."""
    off = abs(read - reference)
    if not floor <= off <= ceiling:
        return read, "as_read"
    best = min(((abs(v - reference), v) for v, _ in ocr_variants(read, decimals, 1)), default=None)
    if best is None or best[0] * FINE_RATIO >= off:
        return read, "as_read"
    return best[1], "repaired_last_digit"


def merge_section(n: int, ocr: dict, digital_rows: list[dict], digital_edge: dict) -> tuple[dict, list, list]:
    """Section with digital coordinates and checked / repaired OCR columns. Returns the section in the
    parse_section layout, the repair log and flags for unresolved values."""
    ref = derived_columns(digital_rows)
    rows, log, flags = [], [], []
    for k, (clean, read) in enumerate(zip(digital_rows, ocr["rows"]), 1):
        row = dict(clean)
        for f in DERIVED_FIELDS:
            d = ROW_DECIMALS[ROW_FIELDS.index(f)]
            value, status = repair_value(read[f], ref[f][k - 1], DERIVED_TOL[f], d)
            if status != "unresolved":
                value, fine = fine_repair(value, ref[f][k - 1], FINE_FLOOR[f], FINE_CEILING[f], d)
                status = fine if status == "as_read" else status
            row[f] = value
            if status != "as_read":
                entry = {"section": n, "K": k, "field": f, "read": read[f], "value": value,
                         "reference": round(ref[f][k - 1], d + 1), "status": status}
                log.append(entry)
                if status == "unresolved":
                    flags.append({"check": "off_derived_reference", **entry})
        rows.append(row)
    return {"edge": digital_edge, "rows": rows}, log, flags


def apply_overrides(n: int, merged: dict, ocr: dict, log: list[dict], overrides: list[dict]) -> list[dict]:
    """Set the overridden values of section n in `merged` (after the OCR passes). Returns the section log
    with each overridden point's earlier entry replaced by an 'override' entry (earlier status kept)."""
    log = list(log)
    ref = derived_columns(merged["rows"])
    for o in (o for o in overrides if o["section"] == n):
        k, f = o["K"], o["field"]
        d = ROW_DECIMALS[ROW_FIELDS.index(f)]
        earlier = next((e for e in log if e["K"] == k and e["field"] == f), None)
        log = [e for e in log if e is not earlier]
        log.append({"section": n, "K": k, "field": f, "read": ocr["rows"][k - 1][f], "value": o["value"],
                    "reference": round(ref[f][k - 1], d + 1), "status": "override",
                    "replaces": earlier["status"] if earlier else "as_read",
                    "evidence": o["evidence"], "verified_by": o["verified_by"]})
        merged["rows"][k - 1][f] = o["value"]
    return log


def flowpath_repairs(points: list[dict]) -> tuple[list[dict], list[dict]]:
    """Table II values that are not smooth get OCR substitutions against the robust column fit. One
    value at a time, the one furthest off its fit first, then the column is re-checked, so a misread
    value does not drag the fit of its correct neighbours. Outliers left without a fitting
    substitution, and unreadable values, are 'unresolved'."""
    out = [dict(p) for p in points]
    log = []
    for field, lim in FLOWPATH_LIMIT.items():
        values = [p[field] for p in points]
        done: set[int] = set()
        while True:
            outliers = {i: fit for i, fit in robust_outliers(values, lim).items() if i not in done}
            fixes = [(abs(values[i] - fit), i, fit) for i, fit in outliers.items()
                     if repair_value(values[i], fit, lim, 5)[1] == "repaired"]
            if not fixes:
                break
            _, i, fit = max(fixes)
            value = repair_value(values[i], fit, lim, 5)[0]
            log.append({"table": "II", "K": points[i]["K"], "field": field, "read": values[i], "value": value,
                        "reference": round(fit, 5), "status": "repaired"})
            values[i] = out[i][field] = value
            done.add(i)
        for i, fit in sorted(robust_outliers(values, lim).items()):
            if i not in done:
                log.append({"table": "II", "K": points[i]["K"], "field": field, "read": values[i], "value": values[i],
                            "reference": round(fit, 5), "status": "unresolved"})
        log += [{"table": "II", "K": points[i]["K"], "field": field, "read": None, "value": None, "reference": None,
                 "status": "unresolved"} for i, v in enumerate(values) if v is None]
    return out, log


def parse_flowpath(text: str) -> tuple[list[dict], list[str]]:
    """Table II: K, Z, R hub, R shroud in two column groups (K 1-40 left, 41-80 right)."""
    lines = text.splitlines()
    head = next(i for i, l in enumerate(lines) if re.search(r"R\s+HUB", l))
    left, right, repairs = [], [], []
    for line in lines[head + 1:]:
        tokens = line.split()
        if not tokens:
            continue
        if len(tokens) == 1 and right:
            right[-1].append(tokens[0])  # wrapped shroud value of the right group
            continue
        split = next((j for j in range(2, len(tokens)) if re.fullmatch(r"(4[1-9]|[5-7]\d|80)", _clean(tokens[j]))), None)
        if split is None:
            left.append(tokens)
        else:
            left.append(tokens[:split])
            right.append(tokens[split:])
    points = []
    for group in (left, right):
        for tokens in group:
            k = int(_clean(tokens[0]))
            rows, rep = read_stream(tokens[1:], (5, 5, 5), 1)
            vals = rows[0] if rows else [None, None, None]
            points.append({"K": k, "Z": vals[0], "R_hub": vals[1], "R_shroud": vals[2]})
            repairs += [f"K={k}: {r}" for r in rep]
    return points, repairs


def parse_survey_station2(text: str) -> tuple[list[dict], list[str]]:
    """Table III(b) station 2 radial survey: radius, Pt/Pref, Tt/Tref, Ps/Pref, flow angle."""
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if re.search(r"STATION\s+2", l))
    rows, repairs = [], []
    for line in lines[start:]:
        tokens = line.split()
        if len(tokens) >= 5 and re.fullmatch(r"\d{2}\.\d{4}", _clean(tokens[0])):
            vals, rep = read_stream(tokens, (4, 4, 4, 4, 1), 1)
            rows.append(dict(zip(("radius", "Pt_ratio", "Tt_ratio", "Ps_ratio", "flow_angle"), vals[0])))
            repairs += rep
    return rows, repairs


def check_survey(rows: list[dict], streamline_radii: list[float]) -> list[dict]:
    """Radii must match the Table IV design streamline radii; local efficiency must be plausible."""
    flags = []
    for i, (row, r_ref) in enumerate(zip(rows, streamline_radii), 1):
        if row["radius"] is None or abs(row["radius"] - r_ref) > 0.005:
            flags.append({"check": "radius_vs_table_IV", "row": i, "read": row["radius"], "table_IV": r_ref,
                          "ocr_candidates": ocr_candidates(row["radius"], r_ref, 0.005, 4) if row["radius"] else []})
        pr, tr = row["Pt_ratio"], row["Tt_ratio"]
        if None in (pr, tr) or tr <= 1:
            flags.append({"check": "unreadable", "row": i})
            continue
        eta = (pr ** (0.4 / 1.4) - 1) / (tr - 1)  # cold-air check, gamma 1.4 [G]
        if not 0.70 <= eta <= 0.97:  # [T]
            flags.append({"check": "local_efficiency_implausible", "row": i, "Pt_ratio": pr, "Tt_ratio": tr,
                          "eta": round(eta, 3)})
    return flags


def extract(pdf: Path | None = None, digital: Path | None = None) -> tuple[dict, dict]:
    pdf, digital = pdf or pdf_path(), digital or digital_dir()
    digital_rows, digital_edges = read_digital(digital)
    overrides = read_yaml(OVERRIDES)["overrides"]
    ocr, ocr_flags, layout_repairs = [], [], []
    for n, page in enumerate(SECTION_PAGES, 1):
        sec = parse_section(page_text(page, pdf))
        ocr.append(sec)
        ocr_flags.append(check_section(sec))
        layout_repairs += [f"section {n}: {r}" for r in sec["repairs"]]
    sections, points, value_log, flags_out = [], [], [], []
    for n, (page, sec) in enumerate(zip(SECTION_PAGES, ocr), 1):
        merged, log, flags = merge_section(n, sec, digital_rows[n], digital_edges[n])
        log = apply_overrides(n, merged, sec, log, overrides)
        flags = [f for f in flags if not any(o["section"] == n and o["K"] == f["K"] and o["field"] == f["field"]
                                             for o in overrides)]
        sections.append({"section": n, "page": page - PRINTED_OFFSET, **section_summary(merged, flags)})
        points.append({"section": n, "rows": [[k] + [row[f] for f in ROW_FIELDS] for k, row in enumerate(merged["rows"], 1)]})
        value_log += log
        flags_out += flags
    flags_out += check_across_sections(sections)
    flow_read, rep = parse_flowpath(page_text(FLOWPATH_PAGE, pdf))
    layout_repairs += [f"flowpath {r}" for r in rep]
    flow, flow_log = flowpath_repairs(flow_read)
    value_log += flow_log
    flags_out += [dict(f, check="flowpath_unresolved") for f in flow_log if f["status"] == "unresolved"]
    status = {}
    for e in value_log:
        key = f"{'flowpath' if e.get('table') == 'II' else 'table_I'} {e['status']}"
        status[key] = status.get(key, 0) + 1
    geometry = {
        "description": "NASA Rotor 67 blade sections (Table I) and flowpath (Table II); generated by "
                       "engine/M1_inlet_fan/analysis/rotor67_tables.py, do not edit",
        "source": {"primary": "Strazisar et al., NASA TP-2879, 1989, Table I (pp. 18-32), Table II (p. 33)",
                   "digital_copy": DIGITAL_SOURCE,
                   "tag": "KS", "license": "US Government work; facts only"},
        "provenance": {
            "Z R THSP1 THSP2 edge_circles": "digital copy, verified against the unflagged TP-2879 OCR values [KS]",
            "TNPC BETA BETA1 BETA2": "TP-2879 OCR, checked against values computed from the digital coordinates; "
                                     "off values repaired by OCR digit substitution (status 'repaired', "
                                     "'repaired_last_digit') [KS]; manual overrides from "
                                     "rotor67_overrides.yaml (status 'override', page-image evidence) [KS]",
            "flowpath": "TP-2879 OCR; not-smooth values repaired by OCR digit substitution against the column fit [KS]",
            "derived_tolerance": DERIVED_TOL,
            "last_digit_pass": {"floor": FINE_FLOOR, "ceiling": FINE_CEILING, "ratio": FINE_RATIO},
        },
        "units": "cm, deg; Z = 0 at blade leading edge / hub; angles from the meridional direction",
        "review": "flagged: true = unresolved (no substitution fits), kept as read",
        "digital_vs_ocr": compare_with_digital(ocr, ocr_flags, digital_rows, digital_edges),
        "value_status_counts": status,
        "sections": sections,
        "points": {"columns": ["K", *ROW_FIELDS], "sections": points},
        "flowpath": {"page": FLOWPATH_PAGE - PRINTED_OFFSET, "tag": "KS", "points": flow},
        "value_log": value_log,
        "flags": flags_out,
        "ocr_layout_repairs": layout_repairs,
    }
    radii = read_yaml(REFERENCE)["design_streamline_radii"]["station_2"]
    rows, srep = parse_survey_station2(page_text(SURVEY_PAGE, pdf))
    survey = {
        "description": "Rotor 67 near peak efficiency, Table III(b) station 2 radial survey; generated by "
                       "rotor67_tables.py, do not edit",
        "source": {"primary": "Strazisar et al., NASA TP-2879, 1989, Table III(b), p. 35", "tag": "KS"},
        "units": "radius cm; Pt, Tt, Ps as ratios to Pref = 101325 Pa, Tref = 288.15 K; flow angle deg",
        "review": "flags list rows whose radius disagrees with Table IV or whose Pt/Tt pair is implausible",
        "station_2": rows,
        "flags": check_survey(rows, radii),
        "ocr_repairs": srep,
    }
    return geometry, survey


def main() -> None:
    geometry, survey = extract()
    write_yaml(GEOMETRY_OUT, geometry)
    write_yaml(SURVEY_OUT, survey)
    print(f"{len(geometry['sections'])} sections, {len(geometry['flowpath']['points'])} flowpath points, "
          f"{len(geometry['flags'])} geometry flags, {len(survey['station_2'])} survey rows, "
          f"{len(survey['flags'])} survey flags")
    for e in (e for e in geometry["value_log"] if e["status"] == "override"):
        print(f"override section {e['section']} K={e['K']} {e['field']}: {e['read']} -> {e['value']} "
              f"(was {e['replaces']}; {e['verified_by']})")


if __name__ == "__main__":
    main()
