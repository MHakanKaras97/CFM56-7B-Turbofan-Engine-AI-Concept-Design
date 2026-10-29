# Araçlar

Araç yolları makineye özel: `config/tools.local.yaml` (git dışı) + `config/tools.example.yaml` (commit); kod yalnızca
`core/toolpaths.py` üzerinden okur.

- core/toolpaths.py: ccx 2.22 çalıştı; pdftotext eklendi.
- UI spesifikasyonu: docs/design/ui_spec.md; ADR-011.
- Kavramsal düzen: concept_reference.yaml -> tools/reference.py -> engine_reference.svg.
- Python araçları (.venv, Python 3.13): streamlit 1.65.0, cadquery 2.8.0 (OCP 7.9.3.1.1), gmsh 4.15.2; smoke testleri geçti.
- Harici: PrePoMax 2.6.0 (C:\Tools, ccx 2.22), ParaView 6.2.0, Autodesk Fusion (MCP).
