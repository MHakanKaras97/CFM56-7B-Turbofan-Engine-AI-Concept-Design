# M2 Materials

- Material values (density, yield, ...) come only from `tools/data/materials.yaml`, each tagged and sourced there.
  M2 files store the material id, never copied values.
- CFM56-7B booster materials: not found in the M2 source set (doğrulanamadı). Until a source is found:
  - rotating parts (rotor blades M2.n.1, drum M2.0.1): `ti6al4v` [T, analogy with the M1 fan blade; Ti alloy is the
    usual low-temperature compressor material [G]];
  - stator vanes, case: `tbd` (choice reported, not invented); abradable liner: `tbd` (no material entry exists).
- Temperatures: booster exit T24 393 K from the ICD [H]; material properties at that temperature only if the source
  gives them, else room temperature with the deviation in `docs/open_issues.md`.
- A new material needs a source with licence in `docs/sources.md`; M2 reports it to M0 (tools/ is not M2's).
