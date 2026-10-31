# M3 design rules (concept level)

Written before the code (analysis/design.py, geometry/build.py). Inputs: `read_icd("M3 design")` (stations 25, 3,
HP speed reference, interstage leak) and the M2 interface `engine/M2_booster/geometry/flowpath.yaml`
(M3_station_25, read-only). Every number of the design is in `analysis/hpc_params.yaml` with its tag.

- R-D3.1 Flow path [T]: inlet S-duct from station 25 to the rotor 1 leading edge; then constant mean radius through
  the 9 stages (rotor 1 LE mean radius); rotor 1 tip radius from the rotor 1 tip speed at the HP speed reference [G:
  HPC stage 1 tip speeds 430-500 m/s]. Annulus area of each plane from W, Tt, Pt and an axial Mach number that falls
  linearly from the rotor 1 inlet value to the exit value (tools/concept.area_for).
- R-D3.2 Work and pressure [H]: equal stage work; stage total temperature rise = (T3 - T25)/9; total pressure along
  the compressor with one polytropic exponent that reproduces Pt3/Pt25 of the ICD exactly.
- R-D3.3 Interstage leak [T]: the ICD interstage leak (0.5 of the enthalpy rise) leaves after stage 5 (stage 5 bleed
  [G]); W3 = W25 - leak.
- R-D3.4 Velocity triangles [G]: mean line, reaction 0.5, axial velocity from the plane Mach number, free vortex
  for hub/tip; metal angles = flow angles with Carter deviation (m = 0.26) [G], zero incidence. The stage 9 stator is the outlet guide vane: axial exit to the M4 diffuser [G].
- R-D3.5 Blade counts: rotors 38/53/60/68/75/82/82/80/76 [KS] (rules/known_values.md); rotor chord from the rotor
  solidity target at mean radius [T]; stator chord from the stator aspect ratio [T]; stator count from the stator
  solidity target (R-KV3.1) [T], changed by +1 if equal to an adjacent rotor count.
- R-D3.6 Hardware [T]: rotor blades sit on the disk rims (rim outer radius = hub line), stators span case to hub
  line with a seal gap to the spool drum; disks rim/web/bore by ratios of the rotor axial width; spools: stage 1-2,
  stage 3 disk, stage 4-9 [KS part split, LLP list]; forward shaft to bearing #3 (M8); CDP seal aft of stage 9;
  case split front (IGV + stages 1-4, variable vanes [KS]) / rear (5-9).
- R-D3.7 Exit interface [H]: station 3 = stage 9 stator trailing edge plane (x, hub, tip, area) in
  `geometry/flowpath.yaml` for M4.
- R-D3.8 Efficiency [T]: eta_hpc is taken from the M0 budget (ADR-015 precedent); no loss model at this level
  (known deviation, docs/open_issues.md).
