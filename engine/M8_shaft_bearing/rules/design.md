# M8 design rules (concept level)

Written before the code (analysis/design.py, geometry/build.py). Inputs: `read_icd("M8 design")` (LP/HP shaft powers,
speed references, mech_eff), the M1 fan disk and fan frame (engine/M1_inlet_fan/geometry rotor_hardware.build and
fan_frame interfaces, read-only), and the interfaces of M3 (bearing #3 journal), M5 (bearing #4 journal),
M6 (LP coupling, bearing #5 journal) and M7 (bearing #5 support). Design choices with tags in
`analysis/shaft_params.yaml`.

- R-D8.1 Bearing arrangement [G]: five main bearings (CFM56 two-spool layout): #1 ball (fan thrust) and #2 roller on the
  fan shaft in the forward sump, #3 ball (HP thrust) on the HPC forward shaft journal, #4 intershaft roller between
  the HPT rear shaft journal and the LP shaft, #5 roller on the LPT shaft journal under the turbine rear frame.
- R-D8.2 Fan shaft [T]: flange on the M1 fan disk bore aft face, tube aft to the spline with the LP shaft.
- R-D8.3 LP shaft [T/H]: tube from inside the fan shaft spline to the M6 LPT shaft coupling (same radii). Torsion
  check [H]: torque = LP power / omega_LP at the LP speed reference; shear stress T r / J; margin with the M1 margin
  definition (allowable shear 0.577 x yield / 1.5) / tau - 1 >= 1.0; yield of params [G].
- R-D8.4 Bearings [T]: envelope rings (inner race on the journal, outer radius = bore + section height of params);
  rolling elements and cages not modelled.
- R-D8.5 Supports [T]: forward support (#1/#2) and #3 support hang from the M1 fan frame hub ring flange (r 0.151065,
  M8 boundary of M1); #5 support hangs from the M7 TRF hub. Sump walls, seals, oil jets not modelled.
- R-D8.6 Rotor dynamics [T]: not analysed at concept level (ROSS planned; known deviation, docs/open_issues.md).
