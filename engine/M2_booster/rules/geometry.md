# M2 Geometry Rules (geometry step 1: flow path and blade solids)

Inputs come only from the active record (`records/ACTIVE`, rev001): `results.yaml` (sections, chords, counts, plane
radii and areas) read with `core.records.read_revision`, and `geometry/flowpath.yaml` (6-digit plane radii) used only
after its sha256 matches the record manifest. Station 21 (x, tip radius) is read from
`engine/M1_inlet_fan/geometry/flowpath.yaml`, interface `M2_station_21` (read-only file, not imported).
Rule constants (fractions, ratios, tolerances) are in `geometry/geometry_params.yaml`, each with its tag and note;
this file states the rule, the yaml holds the value. One tag per rule.

| Id | Rule | Tag |
|---|---|---|
| R-G2.1 | **Frame** = M1 convention (`engine/M1_inlet_fan/geometry/frame.py`, read, not imported): X engine axis positive aft, origin on the axis in the fan rotor stacking plane, Y/Z radial plane, metres; reference blade at +Z (radial), tangential +Y; rotation positive about +X, so at +Z the blade moves towards -Y. Blade k at k x 360/N about +X. | [T] |
| R-G2.2 | **Axial layout**: rows R1 S1 R2 S2 R3 S3 in this order. Row axial width b = largest c cos(gamma) of its hub/mean/tip sections (c record chord, gamma stagger of R-G2.3). Inlet gap from station 21 to R1 LE and every gap after a row = `axial_gap_fraction` x b of the upstream row (station 21 for the inlet gap: R1 width). Station 24 = S3 TE plane; transition duct 24 -> 25 not modelled (station 25 = station 24 plane, placeholder). | [T] |
| R-G2.3 | **Section**: planar section at the section radius r = (r_le + r_te)/2 of the record row (hub, mean, tip). Metal angles = record flow angles (zero incidence, zero deviation). Circular-arc camber line, camber theta = k1 - k2, stagger gamma = (k1 + k2)/2. Thickness laid off normal to the camber line: t(u) = t_e + (t_max - t_e)(1 - (2u/c - 1)^2) (parabolic stand-in for the double-circular-arc family of TP-1523), blunt LE/TE of thickness t_e. t/c and t_e/c from `geometry_params.yaml`. Stacking: chord midpoints on a radial line at the row's mid-axial plane, tangential 0. | [T] |
| R-G2.4 | **Span and trim**: the loft runs through hub, mean and tip sections plus one copy of the hub and tip sections moved outward by an extension, then is cut by the revolved flow path. Rotor: from the hub line to (casing - tip clearance). Stator: hub line to casing (no clearance, attachment not chosen). | [T] |
| R-G2.5 | **Flow path**: casing radius constant at the station 21 tip radius; hub line through the record plane radii (row LE and TE planes, piecewise linear across a row, constant in the gaps, where the TE of one row and the LE of the next share the record plane). | [T] |
| R-G2.6 | **Tip clearance** (rotors) = `tip_clearance_ratio` x mean rotor blade height (mean of LE and TE annulus heights); ratio = TP-1523 rotor 23B average static clearance / rig blade height, proportional transfer (no CFM56 value). | [T] |
| R-G2.7 | **Material for mass**: rotor blades `ti6al4v` (materials.md); stator vanes `tbd` (materials.md), mass uses the `ti6al4v` density as a placeholder; density read from `tools/data/materials.yaml`. Mass is informational, not an acceptance value. Open issue #71 (draft). | [T] |
| R-G2.8 | **Checks**: annulus area of a planar cut of the revolved flow path at every record plane vs the record area, relative tolerance `area_tolerance`; mean-section chord and solidity (aero_method.md definition, r_mean = mean of LE/TE radii) measured on the solid vs the record, relative tolerance `chord_solidity_tolerance`; root and tip vertex radii on the hub line and on (casing - clearance) within `radius_tolerance_m`; neighbouring blades of one row do not intersect (common volume 0, distance > 0). No constant is tuned to pass a check. | [T] |

Stop rule: a section that cannot be built within these rules gets a [T] placeholder and an open issue draft in
`open_items.md`; the geometry continues.

Note for M0 (shared frame): M1 `frame.py` mixes the frame definition with M1 helpers (record access, STEP cache).
Recommendation: a small `core/frame.py` with the frame constants and axis-only helpers (rotation about the axis,
revolve of a meridional curve, radius of a point, STEP export to `.cache/geometry/<module>/<rev>/`), imported by M1
and M2+; module-specific record access stays in each module. Until then M2 re-implements the convention locally
(R-G2.1) and a test checks the M1 and M2 constants agree. Creation needs a CR (core/ and M1 are not M2's).
