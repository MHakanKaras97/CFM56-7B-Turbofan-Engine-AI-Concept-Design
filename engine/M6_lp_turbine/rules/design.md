# M6 design rules (concept level)

Written before the code (analysis/design.py, geometry/build.py). Inputs: `read_icd("M6 design")` (stations 44, 45, 5,
LPT power, LP speed reference) and the M5 interfaces (M6_duct_start, M6_station_44), read-only. Design choices with
tags in `analysis/lpt_params.yaml`.

- R-D6.1 Mean radius [G method, T value]: equal stage work; mean blade speed from the stage loading target
  psi = dh0_stage / U^2 of params at the LP speed reference; constant mean radius through the 4 stages.
- R-D6.2 Thermodynamics [H]: stage total temperature drop = (T45 - T5)/4; total pressure with one polytropic exponent
  that reproduces Pt5/Pt45 of the ICD exactly; W = W45 (= W5).
- R-D6.3 Annulus [G]: plane areas from W, Tt, Pt, FAR and the absolute velocity (tools/concept.area_swirl) with the
  repeating-stage velocity components (flow coefficient, reaction of params).
- R-D6.4 Transition duct [T]: from the M5 duct start (HPT shroud / rim aft end) to the NGV 1 leading edge over the
  duct length of params; the outer wall is the forward part of the LPT case.
- R-D6.5 Counts and chords: rotor blades 162/150/150/134 [KS] (rules/known_values.md), chord from the rotor solidity
  target [T]; NGV chord from the NGV aspect ratio [T], NGV count from the NGV solidity target (R-KV6.1) [T], changed if
  equal to an adjacent rotor count. Metal angles: free vortex, small deviation [T].
- R-D6.6 Hardware [T]: case on the tip line; NGV inner shrouds with a seal gap to the rotor drums; disks
  (rim, web, bore) joined by drums into one rotor spool; conical support from the stage 4 disk to the LPT shaft; LPT
  shaft from the coupling with the M8 LP shaft (forward, at the LPT inlet plane) to the bearing #5 journal (M8)
  under the M7 turbine rear frame. Parts named after the LLP list [KS].
- R-D6.7 Efficiency [T]: eta_lpt from the M0 budget (ADR-015 precedent); interstage leak return (45) enters as given.
