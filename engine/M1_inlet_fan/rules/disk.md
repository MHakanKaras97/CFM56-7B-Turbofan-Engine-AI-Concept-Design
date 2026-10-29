# M1 Disk Sizing (M1.1.2)

## R-DISK.1 Concept disk sizing rule [T rule, G method]
Purpose: size the fan disk web and bore so that the steady centrifugal stress meets the same rule as the blade
(R-AM.13/15): in every section of the disk the von Mises stress from the stepped rotating-disk solution is at most
half the allowable, allowable = yield / safety factor (Ti-6Al-4V yield from `tools/data/materials.yaml`, safety factor
and margin rule from the record params `mechanical`), i.e. margin = allowable / sigma_vm,max - 1 >= 1.0.

Method [G]: `analysis/disk_stress.py` (plane stress, constant thickness per segment, continuity of radial force and
displacement at the steps, free bore). Segments: bore, web, live rim (slot bottom inward). Rim load: dead load of
blades (airfoil + root), shims, spacers, platforms and the slotted rim above the slot bottom, at N1 (ICD LP speed).

Fixed (not changed by the rule):
- slots, dovetail, slot bottom radius, live-rim depth and rim axial width (the blade root slab x_a..x_b);
- bore inner radius (0.3 r_rim [T]): treated as the boundary to the LP shaft interface (M8, CR via M0);
- disk axial centre (rim mid plane).

Growth variables, all from their initial ratios in `geometry/rotor_params.yaml` `disk`:
- bore axial width, bore radial height, web axial thickness.

Steps: at step k every growth variable = initial value x (1 + s k), s = `disk_sizing.step_fraction` (0.1 [T]), all
three together (one proportional scale, monotonic), each capped by its envelope:
- bore width <= rim axial width (keeps the disk inside x_a..x_b: no contact with the spinner flange ahead of x_a,
  the platforms above the rim top, the frame hub ring and bearing flange behind station 13);
- web thickness <= bore width;
- bore outer radius <= live-rim inner radius - `web_height_min_over_neck` x neck width (0.5 [T]).

Stop: at the first step k = 0, 1, 2, ... whose margin >= 1.0 (pass). If every growth variable is at its cap and the
margin is still below 1.0, stop there, report the binding envelope and keep the open issue (STOP RULE); never relax
the margin rule. Code: `geometry/rotor_hardware.py` `disk_profile(L, step)`, `size_disk`, used by `build`.

Not covered: lug and dovetail stresses (dovetail proportions, `rules/joints.md`, open issue #33), stress
concentrations at the steps and slots, thermal stress, shaft fit, burst margin, LCF (A-6).
