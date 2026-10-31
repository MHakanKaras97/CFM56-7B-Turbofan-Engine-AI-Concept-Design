# M7 design rules (concept level)

Written before the code (analysis/design.py, geometry/build.py). Scope (checkpoint 2026-10-29): bypass duct 13-18,
fan nozzle, turbine rear frame, core exhaust nozzle; nacelle and thrust reverser out of scope. Inputs:
`read_icd("M7 design")` (stations 5, 8, 13, 18; A8, A18), the M6 interfaces (M7_station_5, M7_case_flange) and the M1
fan frame layout (engine/M1_inlet_fan/geometry/fan_frame.py build, read-only: outer ring aft end, wall ring aft end).
Design choices with tags in `analysis/nozzle_params.yaml`.

- R-D7.1 Bypass duct [T]: outer wall from the M1 fan frame outer ring aft end, inner wall from the M1 wall ring M1.4.6
  aft end, both straight to the fan nozzle exit plane; wall thicknesses from params (the inner wall leaves room for the M3
  inlet duct outer wall under its forward end).
- R-D7.2 Fan nozzle [H]: exit plane x and inner radius from params [T]; outer exit radius from A18 of the ICD
  (annulus area = A18); the fan nozzle is the aft part of the outer wall (length from params).
- R-D7.3 Turbine rear frame [T]: hub and case continue the station 5 radii for the frame length, starting a gap of params
  behind the aft face of the LPT stage 4 rotor hardware (M6 interface); struts (count [T])
  span hub to case and turn the LPT exit swirl to axial (cambered strut, inlet angle = LPT exit swirl) [G].
- R-D7.4 Core nozzle [H]: convergent annular nozzle between the sleeve and the plug; exit plug radius = ratio of params x
  station 5 hub radius [T]; sleeve exit radius from A8 of the ICD; plug closes to the axis behind the exit.
- R-D7.5 Performance [KS/H]: cfg, cd and duct pressure ratios from the M0 budget; no nozzle flow model at this level.
