"""Read-only differences between records (revisions of one module, or two concepts).

Pure data, no formatting. Nested params/results are flattened to dotted paths; a list of
mappings that share a unique identity key (id, station, name, path) is keyed by it, e.g.
stations[3].Tt_K, other lists are compared as one value.
"""

from pathlib import Path

from core.records import REV_RE, ROOT, RecordError, module_dir, read_concept
from core.util import read_yaml

ID_KEYS = ("id", "station", "name", "path")
BOM_IGNORED = ("revision",)  # differs between any two snapshots by construction


def _rev_dir(module: str, rev: str, root: Path) -> Path:
    path = module_dir(module, root) / "records" / rev
    if not REV_RE.match(rev) or not (path / "manifest.yaml").exists():
        raise RecordError(f"{module}: revision {rev} not found")
    return path


def _id_key(items: list) -> str | None:
    if not items or not all(isinstance(x, dict) for x in items):
        return None
    for key in ID_KEYS:
        ids = [x.get(key) for x in items]
        if None not in ids and len(set(map(str, ids))) == len(ids):
            return key
    return None


def flatten(data, prefix: str = "") -> dict:
    """Dotted path -> leaf value."""
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
        return out if out or not prefix else {prefix: {}}
    if isinstance(data, list) and (key := _id_key(data)):
        out = {}
        for item in data:
            rest = {k: v for k, v in item.items() if k != key}
            out.update(flatten(rest, f"{prefix}[{item[key]}]"))
        return out
    return {prefix: data}


def _changes(a, b) -> list[dict]:
    fa, fb = flatten(a or {}), flatten(b or {})
    return [{"path": p, "old": fa.get(p), "new": fb.get(p)}
            for p in list(fa) + [p for p in fb if p not in fa] if fa.get(p) != fb.get(p)]


def _number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _with_delta(change: dict) -> dict:
    old, new = change["old"], change["new"]
    numeric = _number(old) and _number(new)
    delta = new - old if numeric else None
    pct = 100.0 * delta / old if numeric and old != 0 else None
    return {"key": change["path"], "old": old, "new": new, "delta": delta, "pct": pct}


def _bom_header(bom: dict) -> dict:
    return {k: v for k, v in bom.items() if k != "parts" and k not in BOM_IGNORED}


def _bom_diff(a: dict, b: dict) -> dict:
    pa = {p["id"]: p for p in a.get("parts") or []}
    pb = {p["id"]: p for p in b.get("parts") or []}
    return {
        "header": _changes(_bom_header(a), _bom_header(b)),
        "added": [i for i in pb if i not in pa],
        "removed": [i for i in pa if i not in pb],
        "changed": {i: c for i in pa if i in pb and (c := _changes(pa[i], pb[i]))},
    }


def _outputs_diff(a: list, b: list) -> list[dict]:
    sa = {o["file"]: o["sha256"] for o in a or []}
    sb = {o["file"]: o["sha256"] for o in b or []}
    return [{"file": f, "old": sa.get(f), "new": sb.get(f)}
            for f in list(sa) + [f for f in sb if f not in sa] if sa.get(f) != sb.get(f)]


def _load(rev_dir: Path, name: str):
    return read_yaml(rev_dir / name) or {}


def diff_data(a: dict, b: dict) -> dict:
    """Changes between two record contents {params, results, bom, outputs} (any may be missing)."""
    return {
        "params": _changes(a.get("params") or {}, b.get("params") or {}),
        "results": [_with_delta(c) for c in _changes(a.get("results") or {}, b.get("results") or {})],
        "bom": _bom_diff(a.get("bom") or {}, b.get("bom") or {}),
        "outputs": _outputs_diff(a.get("outputs"), b.get("outputs")),
    }


def read_record(module: str, rev: str, root: Path = ROOT) -> dict:
    d = _rev_dir(module, rev, root)
    return {"params": _load(d, "params.yaml"), "results": _load(d, "results.yaml"), "bom": _load(d, "bom.yaml"),
            "outputs": _load(d, "manifest.yaml").get("outputs")}


def diff_revisions(module: str, rev_a: str, rev_b: str, root: Path = ROOT) -> dict:
    """Changes from rev_a to rev_b of one module.

    params:  [{path, old, new}]            (None = absent)
    results: [{key, old, new, delta, pct}] (delta/pct only when both numeric; pct None for old 0)
    bom:     {header: [...], added: [ids], removed: [ids], changed: {id: [{path, old, new}]}}
    outputs: [{file, old, new}]            sha256 per output file
    """
    return {"module": module.split("_")[0], "from": rev_a, "to": rev_b,
            **diff_data(read_record(module, rev_a, root), read_record(module, rev_b, root))}


# --- numeric change (ADR-012) ------------------------------------------------------------

def _numeric(x, path: str) -> bool:
    """A number, or a numeric string stored as a quantity value (YAML reads 43.124e6 as text)."""
    if _number(x):
        return True
    if isinstance(x, str) and path.rsplit(".", 1)[-1] == "value":
        try:
            float(x)
        except ValueError:
            return False
        return True
    return False


def numeric_changes(diff: dict) -> list[dict]:
    """Changes that alter a number, a part or a geometry output (ADR-012).

    Counted: a numeric value changed or removed (params, results, BOM), a part added or removed,
    an output sha256 changed. Not counted: text, added keys (schema/metadata additions), and a
    params number that only moved to another path with the same value (reported as "moved").
    """
    out = []
    removed, added = [], []
    for section, key in (("params", "path"), ("results", "key")):
        for c in diff[section]:
            path, old, new = c[key], c["old"], c["new"]
            old_num, new_num = _numeric(old, path), _numeric(new, path)
            if old_num and new_num:
                if float(old) != float(new):
                    out.append({"kind": "changed", "section": section, "path": path, "old": old, "new": new})
            elif old_num:
                removed.append((section, path, old))
            elif new_num:
                added.append((section, path, new))
            elif isinstance(old, (list, dict)) and old != new and any(_number(v) for v in _leaves(old)):
                out.append({"kind": "changed", "section": section, "path": path, "old": old, "new": new})
    for section, path, value in removed:
        match = next((a for a in added if a[0] == section and float(a[2]) == float(value)), None)
        if section == "params" and match:
            added.remove(match)
            out.append({"kind": "moved", "section": section, "path": path, "to": match[1], "value": value})
        else:
            out.append({"kind": "removed", "section": section, "path": path, "old": value})
    bom = diff["bom"]
    out += [{"kind": "part_added", "section": "bom", "path": i} for i in bom["added"]]
    out += [{"kind": "part_removed", "section": "bom", "path": i} for i in bom["removed"]]
    for pid, changes in bom["changed"].items():
        for c in changes:
            if _numeric(c["old"], c["path"]) or _numeric(c["new"], c["path"]):
                out.append({"kind": "changed", "section": "bom", "path": f"{pid}.{c['path']}",
                            "old": c["old"], "new": c["new"]})
    out += [{"kind": "output", "section": "outputs", "path": o["file"], "old": o["old"], "new": o["new"]}
            for o in diff["outputs"]]
    return [c for c in out if c["kind"] != "moved"] + [c for c in out if c["kind"] == "moved"]


def blocking(changes: list[dict]) -> list[dict]:
    """Numeric changes that a maintenance revision may not contain (moves are allowed)."""
    return [c for c in changes if c["kind"] != "moved"]


def _leaves(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from _leaves(v)
    elif isinstance(x, list):
        for v in x:
            yield from _leaves(v)
    else:
        yield x


def is_empty(diff: dict) -> bool:
    bom = diff["bom"]
    return not (diff["params"] or diff["results"] or diff["outputs"]
                or bom["header"] or bom["added"] or bom["removed"] or bom["changed"])


def diff_concepts(concept_a: str, concept_b: str, root: Path = ROOT) -> list[dict]:
    """Modules whose pinned revision differs: [{module, old, new}] (None = not started)."""
    a, b = (read_concept(c, root)["modules"] for c in (concept_a, concept_b))
    return [{"module": m, "old": a.get(m), "new": b.get(m)}
            for m in sorted(set(a) | set(b)) if a.get(m) != b.get(m)]
