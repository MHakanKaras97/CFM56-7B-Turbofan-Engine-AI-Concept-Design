# M4 design rules (concept level)

Written before the code (analysis/design.py, geometry/build.py). Inputs: `read_icd("M4 design")` (stations 3, 31, 4,
burner_pr) and the M3 interfaces `engine/M3_hp_compressor/geometry/flowpath.yaml` (M4_station_3, M4_case_flange,
read-only). Design choices with tags in `analysis/combustor_params.yaml`.

- R-D4.1 Prediffuser [T]: straight-walled annular diffuser from station 3, area ratio and length from params; its exit
  mean radius = the liner mean radius (the diffuser turns the flow outward to the dome).
- R-D4.2 Casing [G method, T value]: reference area A_ref = W31 / (rho3 U_ref) with rho3 = Pt3 / (R Tt3) and the
  reference velocity U_ref of params (pressure-loss sizing after Lefebvre [G]); casing annulus = A_ref centred on the
  liner mean radius.
- R-D4.3 Liner [T]: liner annulus = liner/reference area ratio x A_ref (optimum band 0.6-0.7 [G]); liner length =
  length/height ratio x liner height; the liner converges over its aft part to the station 4 annulus.
- R-D4.4 Station 4 [T]: mean radius and axial Mach from params; area from W4, Tt4, Pt4, FAR4 of the ICD
  (tools/concept.area_for). Station 4 is the M5 NGV inlet.
- R-D4.5 Fuel injectors: 20 twin-tip injectors on the SAC [KS] (rules/known_values.md), one per dome swirler, equally
  spaced; stem radial through the outer case (hole cut in the case), tip in the dome swirler opening.
- R-D4.6 Burner efficiency and pressure loss [KS/H]: from the M0 budget (burner_eta, burner_pr); no combustion model
  at this level (known deviation, docs/open_issues.md).
