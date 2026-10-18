"""Read-only data adapter for the UI. Every read goes through core/; nothing is written here.

The snapshot is cached and keyed by the modification times of the record pointers, CRs and
derived files, so a change on disk shows up on the next rerun.

The repo root is ROOT unless TURBOFAN_UI_ROOT names another copy (tests use a temporary copy, so
UI writes in tests never reach the real repo). Docs (docs/) are always read from ROOT.
"""

import os
import re
from pathlib import Path

import streamlit as st

from core import bom as bom_io
from core.budgets import load_icd
from core.diff import diff_concepts as _diff_concepts
from core.diff import diff_revisions
from core.records import (
    ROOT,
    active_concept,
    active_revision,
    concept_ids,
    module_dir,
    module_dirs,
    read_concept,
    read_revision,
    revision_ids,
)
from core.requests import list_crs
from core.util import read_yaml

MODULES = [f"M{i}" for i in range(10)]
NAMES_TR = {
    "M0": "Motor", "M1": "Giriş ve fan", "M2": "Booster", "M3": "HP kompresör", "M4": "Yanma odası",
    "M5": "HP türbin", "M6": "LP türbin", "M7": "Lüle", "M8": "Şaft ve yatak", "M9": "İkincil hava ve yağ",
}
TAGS = ("K", "KS", "H", "G", "T")
EGT_CHECK = "EGT displayed vs TCDS limit"
REFERENCE_SVG = ROOT / "docs" / "design" / "engine_reference.svg"
CONCEPT_REFERENCE = ROOT / "docs" / "design" / "concept_reference.yaml"
SOURCES = ROOT / "docs" / "sources.md"
TAG_LEGEND = [
    ("K", "Birincil kaynak (ör. EASA TCDS, ICAO veri bankası)"),
    ("KS", "İkincil kaynak (ör. tez, makale)"),
    ("H", "Koddan hesaplanan değer"),
    ("G", "Genel mühendislik bilgisi"),
    ("T", "Tahmin / varsayım; doğrulanmadı"),
]
STATUS_TR = {"open": "açık", "approved": "onaylandı", "rejected": "reddedildi", "applied": "uygulandı"}


def root() -> Path:
    return Path(os.environ.get("TURBOFAN_UI_ROOT", ROOT))


# --- formatting (display only: decimal comma, tags) ---------------------------------------

def num(x, digits: int | None = None) -> str:
    """Number with a decimal comma; digits=None gives 5 significant digits."""
    if x is None:
        return "-"
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return str(x)
    s = f"{x:.{digits}f}" if digits is not None else f"{x:.5g}"
    return s.replace(".", ",")


def unit_tr(unit: str | None) -> str:
    return {"degC": "°C", "-": "", "- of W25": "W25 oranı", None: ""}.get(unit, unit)


def quantity(q: dict, digits: int | None = None, tag: bool = True) -> str:
    """'121,4 kN [H]' from a Quantity {value, unit, tag}."""
    text = " ".join(s for s in (num(q.get("value"), digits), unit_tr(q.get("unit"))) if s)
    return f"{text} [{q['tag']}]" if tag and q.get("tag") else text


def tolerance(tol: dict) -> str:
    if "type" not in tol:
        return "bilgi"
    if tol["type"] == "relative":
        return f"± %{num(tol['value'] * 100.0)}"
    return f"± {num(tol['value'])}{' ' + tol['unit'] if tol.get('unit') else ''}"


# --- snapshot -------------------------------------------------------------------------------

def _stamp(root: Path) -> tuple:
    files = [root / "engine" / "M0_engine" / "records" / "ACTIVE_CONCEPT"]
    for mdir in module_dirs(root):
        files += [mdir / "records" / "ACTIVE", mdir / "bom" / "bom.yaml"]
    files += sorted((root / "engine" / "M0_engine" / "requests").glob("CR-*.yaml"))
    files += [root / "engine" / "M0_engine" / "rules" / "icd.yaml"]
    return tuple((str(f), f.stat().st_mtime_ns) for f in files if f.exists())


def _chain(module: str, rev: str | None, root: Path) -> list[str]:
    """Revision chain up to `rev` via parent_revision, oldest first."""
    chain = []
    while rev:
        chain.append(rev)
        rev = read_revision(module, rev, "manifest.yaml", root)["parent_revision"]
    return chain[::-1]


def _validation(root: Path) -> dict:
    """Girão validation summary from the result table in validation_girao.md."""
    text = (module_dir("M0", root) / "analysis" / "validation_girao.md").read_text(encoding="utf-8")
    rows = [r for r in re.findall(r"^\|(.+)\|\s*$", text, re.M) if not set(r) <= set("-| ")][1:]
    results = [r.split("|")[-1].strip() for r in rows]
    return {"passed": sum(r.startswith("geçti") for r in results), "total": len(results)}


def _module_rows(concept: dict | None, crs: list[dict], root: Path) -> list[dict]:
    pins = (concept or {}).get("modules", {})
    open_by_module = {}
    for cr in crs:
        if cr["status"] == "open":
            for m in {cr["from_module"], *cr["to_modules"]}:
                open_by_module.setdefault(m, []).append(cr["id"])
    rows, next_marked = [], False
    for m in MODULES:
        rev, pinned = active_revision(m, root), pins.get(m)
        name = bom_io.load(module_dir(m, root) / "bom" / "bom.yaml")["module_name"]
        if rev is None:
            status, color = "Başlamadı", "gray"
            if not next_marked and m != "M0":
                status, next_marked = "Başlamadı · sıradaki", True
        elif pinned and pinned != rev:
            status, color = f"{rev} aktif (konseptte {pinned})", "orange"
        else:
            status, color = f"{rev} aktif", "green"
        if open_by_module.get(m):
            color = "orange"
            status += f" · açık talep: {', '.join(open_by_module[m])}"
        rows.append({"id": m, "name": name, "name_tr": NAMES_TR[m], "active": rev, "pinned": pinned,
                     "status": status, "color": color, "open_crs": open_by_module.get(m, [])})
    return rows


def _active_module(rows: list[dict], m0_results: dict | None) -> dict | None:
    started = [r for r in rows if r["active"]]
    if not started:
        return None
    last = started[-1]
    if last["id"] == "M0" and m0_results and m0_results.get("hard_checks_passed"):
        return {"id": "M0", "label": "M0 · tamam", "color": "green"}
    return {"id": last["id"], "label": f"{last['id']} · {last['active']}", "color": "blue"}


def _metrics(results: dict, rev: str) -> list[dict]:
    perf, cal, egt = results["performance"], results["calibration"], results["egt"]
    egt_check = next(c for c in results["checks"] if c["name"] == EGT_CHECK)
    margin = {"value": egt_check["margin"], "unit": "K", "tag": egt["displayed_C"]["tag"]}
    return [
        {"label": "İtki", "q": perf["thrust"], "digits": 1, "help": f"kaynak {rev} · performance.thrust"},
        {"label": "SFC", "q": perf["sfc"], "digits": 2, "help": f"kaynak {rev} · performance.sfc"},
        {"label": "EGT payı", "q": margin, "digits": 0,
         "help": f"kaynak {rev} · checks['{EGT_CHECK}'].margin; etiket gösterilen EGT'den"},
        {"label": "W2", "q": cal["W2"], "digits": 0, "help": f"kaynak {rev} · calibration.W2"},
    ]


def load(root: Path = ROOT) -> dict:
    """Everything the pages show, read through core/."""
    concept_id = active_concept(root)
    revisions = {m: [read_revision(m, r, "manifest.yaml", root) for r in revision_ids(m, root)] for m in MODULES}
    concepts = [read_concept(c, root) for c in concept_ids(root)]
    concept = read_concept(concept_id, root) if concept_id else None
    crs = list_crs(root)
    rows = _module_rows(concept, crs, root)
    m0_rev = active_revision("M0", root)
    results = read_revision("M0", m0_rev, "results.yaml", root) if m0_rev else None
    return {
        "root": str(root),
        "concept": concept_id,
        "concepts": concepts,
        "revisions": revisions,
        "crs": sorted(crs, key=lambda cr: (cr["status"] != "open", cr["id"])),
        "modules": rows,
        "open_crs": sum(cr["status"] == "open" for cr in crs),
        "closed_crs": sum(cr["status"] != "open" for cr in crs),
        "active_module": _active_module(rows, results),
        "m0": {
            "rev": m0_rev,
            "chain": _chain("M0", m0_rev, root),
            "results": results,
            "metrics": _metrics(results, m0_rev) if results else [],
            "icd": load_icd(root),
            "validation": _validation(root),
            "station_order": read_yaml(CONCEPT_REFERENCE)["stations"]["order"],
        },
    }


@st.cache_data(show_spinner=False)
def _cached(stamp: tuple, root_dir: str) -> dict:
    return load(Path(root_dir))


def snapshot() -> dict:
    r = root()
    return _cached(_stamp(r), str(r))


def diff(module: str, rev_a: str, rev_b: str) -> dict:
    return diff_revisions(module, rev_a, rev_b, root())


def read_bom(module: str) -> dict:
    return bom_io.load(module_dir(module, root()) / "bom" / "bom.yaml")


def diff_concepts(concept_a: str, concept_b: str) -> list[dict]:
    return _diff_concepts(concept_a, concept_b, root())


# --- documents (learning, sources, info sections) -------------------------------------------

def learning_files() -> dict[str, list[Path]]:
    """Group -> .md/.txt files: 'Genel' (docs/learning) and one group per module; sources/ excluded."""
    groups = {"Genel": sorted((ROOT / "docs" / "learning").glob("*.*"))}
    for mdir in module_dirs(root()):
        files = sorted((mdir / "learning").glob("*.*")) if (mdir / "learning").is_dir() else []
        groups[mdir.name] = files
    return {g: [f for f in files if f.suffix in (".md", ".txt")] for g, files in groups.items()}


def read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def markdown_table(text: str, after_heading: str | None = None) -> list[dict]:
    """First markdown table (optionally after a heading) as rows keyed by the header cells."""
    if after_heading:
        text = text[text.index(after_heading):]
    lines = [ln.strip() for ln in text.splitlines()]
    start = next(i for i, ln in enumerate(lines) if ln.startswith("|"))
    block = []
    for ln in lines[start:]:
        if not ln.startswith("|"):
            break
        block.append([c.strip() for c in ln.strip("|").split("|")])
    header, rows = block[0], [r for r in block[2:]]
    return [dict(zip(header, r)) for r in rows]


def md_section(path: Path, heading: str) -> str:
    """A markdown section from its heading line up to the next heading of the same or higher level."""
    text = read_text(path)
    start = text.index(heading)
    level = len(heading) - len(heading.lstrip("#"))
    rest = text[start + len(heading):]
    m = re.search(rf"^#{{1,{level}}} ", rest, re.M)
    return heading + (rest[:m.start()] if m else rest)


def sources() -> list[dict]:
    return markdown_table(read_text(SOURCES))


def info_sections() -> dict[str, str]:
    m0 = module_dir("M0", ROOT)
    return {
        "band": md_section(m0 / "rules" / "cycle_inputs.md", "## Belirsizlik bandı"),
        "sensitivity": md_section(m0 / "analysis" / "acceptance_M0.md", "## Makullük"),
        "adr010": read_text(ROOT / "docs" / "decisions" / "ADR-010-integration-limitation.md"),
    }
