"""Read-only differences between records (revisions of one module, or two concepts).

Pure data, no formatting. Nested params/results are flattened to dotted paths; a list of
mappings that share a unique identity key (id, station, name) is keyed by it, e.g.
stations[3].Tt_K, other lists are compared as one value.
"""

from pathlib import Path

from core.records import REV_RE, ROOT, RecordError, module_dir, read_concept
from core.util import read_yaml

ID_KEYS = ("id", "station", "name")
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


def diff_revisions(module: str, rev_a: str, rev_b: str, root: Path = ROOT) -> dict:
    """Changes from rev_a to rev_b of one module.

    params:  [{path, old, new}]            (None = absent)
    results: [{key, old, new, delta, pct}] (delta/pct only when both numeric; pct None for old 0)
    bom:     {header: [...], added: [ids], removed: [ids], changed: {id: [{path, old, new}]}}
    outputs: [{file, old, new}]            sha256 per output file
    """
    da, db = _rev_dir(module, rev_a, root), _rev_dir(module, rev_b, root)
    return {
        "module": module.split("_")[0],
        "from": rev_a,
        "to": rev_b,
        "params": _changes(_load(da, "params.yaml"), _load(db, "params.yaml")),
        "results": [_with_delta(c) for c in _changes(_load(da, "results.yaml"), _load(db, "results.yaml"))],
        "bom": _bom_diff(_load(da, "bom.yaml"), _load(db, "bom.yaml")),
        "outputs": _outputs_diff(_load(da, "manifest.yaml").get("outputs"), _load(db, "manifest.yaml").get("outputs")),
    }


def is_empty(diff: dict) -> bool:
    bom = diff["bom"]
    return not (diff["params"] or diff["results"] or diff["outputs"]
                or bom["header"] or bom["added"] or bom["removed"] or bom["changed"])


def diff_concepts(concept_a: str, concept_b: str, root: Path = ROOT) -> list[dict]:
    """Modules whose pinned revision differs: [{module, old, new}] (None = not started)."""
    a, b = (read_concept(c, root)["modules"] for c in (concept_a, concept_b))
    return [{"module": m, "old": a.get(m), "new": b.get(m)}
            for m in sorted(set(a) | set(b)) if a.get(m) != b.get(m)]
