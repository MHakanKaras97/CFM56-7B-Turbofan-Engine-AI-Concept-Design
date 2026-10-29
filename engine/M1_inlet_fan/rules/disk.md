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

Not covered by R-DISK.1: lug and dovetail stresses (R-DISK.2), stress concentrations at the steps and slots,
thermal stress, shaft fit, burst margin, LCF (A-6).

## R-DISK.2 Dovetail and lug sizing rule [T rule, G method]
Checks (closed form, average stresses [G]; same criterion as R-AM.13/15 and R-DISK.1: margin = (yield / 1.5) /
sigma_eq - 1 >= 1.0 for every mode). Per slot: F = pull of the blade (airfoil + root) + shim + platform; each lug
carries one blade pull (half of each neighbour). L = slot length along the slot axis = slab length / cos(slot angle).
1. Lug tension at the narrowest lug section (lobe level z2): (F + pull of the lug material above z2) / (w_lobe L),
   w_lobe = 2 pi z2 cos(slot angle) / N - (lobe width + 2 (shim + clearance)).
2. Lug tension at the neck level z1: same with the neck slot width and the lug material above z1.
3. Flank bearing (frictionless): N = F / (2 cos alpha) on each flank of length ((lobe - neck) / 2) / cos alpha.
4. Ear shear: the disk ear over the lobe sheared on the radial plane at the lobe-max line, height r_rim - z2:
   sigma_eq = sqrt(3) (F / 2) / (h_ear L).
5. Ear bending: the ear as a cantilever from that plane, load F / 2 at the flank mid-line, arm (lobe - neck) / 4,
   section L h_ear^2 / 6.
6. Blade neck tension: blade pull / (neck width L).

Growth variable: the rotor slab axial length (disk rim axial width = blade-root dovetail and shank length; it is a
blade-root dimension as well as a disk dimension, so the blade root, shim, spacer, platform and disk rim all grow
together), symmetric about the initial slab mid-plane. Reason: every failing mode (lug tension, flank bearing) scales
with 1 / L; the lug width cannot grow at fixed slot count, rim radius and lobe without shrinking the lobe, which
reduces the flank bearing area that also fails.
Steps: slab = initial x (1 + s k), s = `dovetail.slab_step_fraction` (0.1 [T]), k = 0..5 (`slab_max_steps`); loads
recomputed from the CAD parts at every step (heavier root and platform). Stop at the first k where every mode passes;
then R-DISK.1 is re-run with the loads and rim width of that slab.
Fixed: slot count 24, rim top radius, dovetail cross-section (neck, lobe, flanks, levels), blade airfoil, flowpath.
Envelope: spinner aft edge follows the disk front face (one clearance ahead); platforms span the slab; no
interference with the frame hub ring / bearing flange, OGV, case or splitter.
If no k <= 5 passes: stop, report the binding mode, keep the previous design (STOP RULE), open issue.
Code: `geometry/rotor_hardware.py` `root_modes`, `build` (slab loop), `geometry/dovetail.py` `layout(slab_step)`.
