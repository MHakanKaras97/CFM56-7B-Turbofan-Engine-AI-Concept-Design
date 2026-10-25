"""Extract NASA Rotor 67 tables from the scanned TP-2879 (Strazisar et al. 1989) [KS].

The PDF is a scan with an OCR text layer. `pdftotext -table` (xpdf) keeps table rows roughly aligned, but
the OCR splits decimals ("0 71202"), breaks rows over two lines, misplaces the K labels, reads letters for
digits (l, I, O, Z, B) and misreads digits (most often 3 as 5). This module:
- parses Table I (blade sections), Table II (flowpath) and Table III(b) station 2 (survey profile),
- repairs only layout damage (split decimals, letters for digits) and lists every repair,
- runs plausibility checks and flags suspected misread values; flagged values are kept exactly as read.
  For a flagged value it lists single-digit OCR substitutions that would pass the check, as review hints.

Run: python -m engine.M1_inlet_fan.analysis.rotor67_tables  (writes learning/rotor67_geometry.yaml
and learning/rotor67_survey.yaml; needs the PDF and pdftotext in config/tools.local.yaml).
"""

import math
import re
import subprocess
from itertools import combinations
from pathlib import Path

from core.toolpaths import tool_path
from core.util import read_yaml, write_yaml

M1 = Path(__file__).resolve().parents[1]
PDF = M1 / "learning" / "sources" / "aero" / "strazisar_1989_nasa_tp2879_rotor67.pdf"
GEOMETRY_OUT = M1 / "learning" / "rotor67_geometry.yaml"
SURVEY_OUT = M1 / "learning" / "rotor67_survey.yaml"
REFERENCE = M1 / "learning" / "rotor67_reference.yaml"

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


def page_text(page: int, pdf: Path = PDF) -> str:
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


def check_flowpath(points: list[dict]) -> list[dict]:
    flags = []
    if [p["K"] for p in points] != list(range(1, N_FLOWPATH + 1)):
        flags.append({"check": "point_numbers", "found": [p["K"] for p in points]})
    for field in ("Z", "R_hub", "R_shroud"):
        flags += check_column([p[field] for p in points], 0.02, 5, lambda i: {"field": field, "K": points[i]["K"]})
    return flags


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


def extract(pdf: Path = PDF) -> tuple[dict, dict]:
    sections, flags_out, repairs_out = [], [], []
    for n, page in enumerate(SECTION_PAGES, 1):
        sec = parse_section(page_text(page, pdf))
        flags = check_section(sec)
        summary = {"section": n, "page": page - PRINTED_OFFSET, **section_summary(sec, flags)}
        sections.append(summary)
        flags_out += [dict(f, section=n) for f in flags]
        repairs_out += [f"section {n}: {r}" for r in sec["repairs"]]
    flags_out += check_across_sections(sections)
    flow, rep = parse_flowpath(page_text(FLOWPATH_PAGE, pdf))
    repairs_out += [f"flowpath {r}" for r in rep]
    geometry = {
        "description": "NASA Rotor 67 blade sections (Table I) and flowpath (Table II); generated by "
                       "engine/M1_inlet_fan/analysis/rotor67_tables.py, do not edit",
        "source": {"primary": "Strazisar et al., NASA TP-2879, 1989, Table I (pp. 18-32), Table II (p. 33)",
                   "tag": "KS", "license": "US Government work; facts only"},
        "units": "cm, deg; Z = 0 at blade leading edge / hub; angles from the meridional direction",
        "review": "flagged: true = failed a plausibility check, kept as read; ocr_candidates are hints, not used",
        "sections": sections,
        "flowpath": {"page": FLOWPATH_PAGE - PRINTED_OFFSET, "tag": "KS", "points": flow},
        "flags": flags_out + [dict(f, table="II") for f in check_flowpath(flow)],
        "ocr_repairs": repairs_out,
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


if __name__ == "__main__":
    main()
