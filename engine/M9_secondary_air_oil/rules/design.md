# M9 design rules (concept level)

Written before the code (analysis/design.py, geometry/build.py). Scope (checkpoint 2026-10-29): accessory gearbox and
oil system; secondary air budgets (ICD secondary_air); own pipes and seals only (architecture.md). Inputs:
`read_icd("M9 design")`, the M1 fan frame outer ring (read-only import), the M3 bleed port, the M6 LPT case radius
at stage 1, the M7 bypass inner wall and the M8 sump positions. Design choices with tags in
`analysis/air_oil_params.yaml`. Angles: clock positions about +X from +Z (tools/concept.rotate_x).

- R-D9.1 Drive train [G arrangement, T sizes]: inlet gearbox (IGB) inside the fan frame hub zone, radial drive shaft
  through the 6 o'clock fan frame struts to the transfer gearbox (TGB) on the frame outer ring, horizontal drive shaft
  along the ring to the accessory gearbox (AGB). Housings as envelope boxes; gears and accessories not modelled.
- R-D9.2 Oil system [T]: oil tank on the frame outer ring; forward sump supply line along the ring and down the
  6 o'clock struts; aft sump supply line in the core compartment (under the M7 bypass inner wall, between injector
  bosses) and down a turbine rear frame strut. Scavenge lines, pumps, coolers not modelled.
- R-D9.3 Secondary air [KS/H]: flows, extraction and return stations from the ICD; internal cooling paths (3 -> 41,
  3 -> 44) inside M4/M5 hardware are not modelled; the interstage leak (stage 5 bleed, M3 port) is routed in an
  external duct to the LPT case at stage 1 (return 45). Duct bore from W, Tt, Pt at the port and the duct Mach of params
  (tools/concept.area_for) [H].
- R-D9.4 Passages [T] through other modules' structure (struts, rings) are not cut (other modules' parts are not edited);
  the common volumes are listed as a known deviation (docs/open_issues.md).
