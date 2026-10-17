"""Extract engine rows from the ICAO Engine Emissions Databank (EASA .xlsx).

Usage:
    python -m tools.extract_edb <databank.xlsx> <engine substring> <out.yaml>

Standard library only (zipfile + xml); the databank file itself is never committed.
"""

import hashlib
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from core.util import write_yaml

SHEET = "Gaseous Emissions and Smoke"
NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
COLUMNS = {
    "uid": "UID No",
    "engine": "Engine Identification",
    "combustor": "Combustor Description",
    "rated_thrust_kN": "Rated Thrust (kN)",
    "pressure_ratio": "Pressure Ratio",
    "bpr": "B/P Ratio",
    "fuel_flow_to_kg_s": "Fuel Flow T/O (kg/sec)",
    "fuel_flow_co_kg_s": "Fuel Flow C/O (kg/sec)",
    "fuel_flow_app_kg_s": "Fuel Flow App (kg/sec)",
    "fuel_flow_idle_kg_s": "Fuel Flow Idle (kg/sec)",
    "superseded": "Data Superseded",
    "superseded_by": "Superseded by UID No",
    "remark": "Remark 1",
}
NUMERIC = {"rated_thrust_kN", "pressure_ratio", "bpr",
           "fuel_flow_to_kg_s", "fuel_flow_co_kg_s", "fuel_flow_app_kg_s", "fuel_flow_idle_kg_s"}


def _col_index(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group():
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_sheet(path: Path, name: str) -> list[list[str]]:
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))
    workbook = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    sheet = next(s for s in workbook.find("m:sheets", NS) if s.get("name") == name)
    target = rels[sheet.get(f"{{{NS['r']}}}id")].lstrip("/")
    target = target if target.startswith("xl/") else f"xl/{target}"

    rows = []
    for row in ET.fromstring(z.read(target)).iter(f"{{{NS['m']}}}row"):
        cells = {}
        for c in row.findall("m:c", NS):
            v, kind = c.find("m:v", NS), c.get("t")
            if kind == "inlineStr":
                value = "".join(t.text or "" for t in c.iter(f"{{{NS['m']}}}t"))
            elif v is None:
                continue
            else:
                value = shared[int(v.text)] if kind == "s" else v.text
            cells[_col_index(c.get("r"))] = value
        if cells:
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
    return rows


def _number(text: str):
    # Excel stores binary floats (1.2929999999999999); 6 significant digits recovers the published value.
    return float(f"{float(text):.6g}") if text != "" else None


def extract(path: Path, engine: str) -> dict:
    rows = read_sheet(path, SHEET)
    header = rows[0]
    index = {key: header.index(col) for key, col in COLUMNS.items()}
    out = []
    for row in rows[1:]:
        get = lambda key: row[index[key]] if index[key] < len(row) else ""
        if engine not in get("engine"):
            continue
        out.append({key: (_number(get(key)) if key in NUMERIC else get(key) or None) for key in COLUMNS})
    return {
        "source": {
            "file": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "sheet": SHEET,
            "filter": engine,
        },
        "rows": out,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    data = extract(Path(argv[0]), argv[1])
    write_yaml(Path(argv[2]), data)
    print(f"{len(data['rows'])} rows -> {argv[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
