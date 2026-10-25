# M1 Materials

Property values live only in `tools/data/materials.yaml` (each with tag and source). This file holds the selection rules.

| Part | Material id | Basis |
|---|---|---|
| Blade, disk | `ti6al4v` | CFM56-7B hardware [KS] Fox 2023 p. 1439 |
| Blade spacer | `ti6al4v` (elastomer coated) | [KS] Fox 2023 p. 1439 |
| Dovetail shim | `alloy718` | [KS] Fox 2023 p. 1439 |
| Blade platform | `aluminium_alloy` | [KS] Fox 2023 p. 1439 |
| Fan frame | `aluminium_alloy` | [KS] Girão 2023 |
| Spinner, case, containment, OGV | `tbd` | aluminium or composite [T]; no source yet |

Rules:
- R-MAT.1 Design allowables need a source that states the test condition (cycles, stress ratio, notch, temperature). The Ti-6Al-4V fatigue value in `materials.yaml` has none and is not an allowable.
- R-MAT.2 When sources disagree, keep the main value and list the others under `cross_check` (e.g. Ti-6Al-4V density 4405-4440 kg/m3 across sources).
- R-MAT.3 Strain-rate models for impact (Johnson-Cook) are kept with the analysis that uses them (`bird_strike.md`), not in `materials.yaml`.
