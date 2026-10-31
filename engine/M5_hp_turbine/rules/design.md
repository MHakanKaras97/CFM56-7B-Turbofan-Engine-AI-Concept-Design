# M5 design rules (concept level)

Written before the code (analysis/design.py, geometry/build.py). Inputs: `read_icd("M5 design")` (stations 4, 41,
43, 44, HP power and speed reference) and the interfaces of M4 (M5_station_4, case flanges) and M3 (M5_cdp_flange),
read-only. Design choices with tags in `analysis/hpt_params.yaml`.

- R-D5.1 Mean line [G method, T values]: constant mean radius = station 4 mean radius (M4); U = omega r_m at the HP
  speed reference; loading psi = (HPT power / W41) / U^2 [H]; reaction and flow coefficient from params; repeating-
  stage velocity components (tools/concept.stage_triangles with negative psi); NGV inlet axial.
- R-D5.2 Annulus [G]: NGV inlet = station 4 (M4); rotor inlet (41) and rotor exit (44) areas from W, Tt, Pt, FAR of
  the ICD with the static state of the absolute velocity (tools/concept.area_swirl).
- R-D5.3 Counts and chords: rotor blades 80 [KS] (rules/known_values.md), chord from the rotor solidity target [T];
  NGV chord from the NGV aspect ratio [T], NGV count from the NGV solidity target (R-KV5.1) [T], changed if it
  equals 80 or a divisor relation of 80/2.
- R-D5.4 Metal angles [G]: free vortex, deviation m / sqrt(solidity) with the small turbine m of params [T], zero
  incidence.
- R-D5.5 Hardware [T]: NGV bands (inner, outer) with radial webs to the M4 cases; shroud over the rotor tips hung
  from the HPT case; disk (fir-tree rim region, web, bore) under the rotor; front shaft from the M3 CDP flange to the
  disk; front air seal plate ahead of the rim; rear shaft to the bearing #4 journal (M8). Parts named after the LLP
  list [KS].
- R-D5.6 Efficiency and cooling [T]: eta_hpt from the M0 budget (ADR-015 precedent); cooling flows of the ICD
  enter as given (stations 41, 44), cooling passages not modelled (known deviation, docs/open_issues.md).
