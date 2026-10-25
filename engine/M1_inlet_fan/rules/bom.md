# M1 BOM Rules

- Single source of truth: `engine/M1_inlet_fan/bom/bom.yaml`, written only via `core.bom.write`; no comments, use `notes`.
- Part id `M1.<group>.<part>`; name `"Fan Stage 1 <Part type>"`. Repeated parts: one entry with `qty`.
- `material` is an id from `tools/data/materials.yaml`, `tbd` while not selected, or null for an assembly.
- Every part starts as `draft`; geometry is added only by a script in `geometry/`.

## Numbering
| Id | Part | Notes |
|---|---|---|
| M1.1 | Fan Stage 1 Rotor | assembly |
| M1.1.1 | Fan Stage 1 Rotor Blade | x24 [KS] Fox 2023 (all 24 blades of two production -7B24 engines examined, PDF p. 3) and Girão 2023; CFM 1997 article (sources #42) says 22, see below |
| M1.1.2 | Fan Stage 1 Disk | Ti-6Al-4V [KS] Fox 2023 |
| M1.1.3 | Fan Stage 1 Spinner | material tbd |
| M1.1.4 | Fan Stage 1 Dovetail Shim | Alloy 718 [KS] Fox 2023 |
| M1.1.5 | Fan Stage 1 Blade Spacer | elastomer-coated Ti-6Al-4V, radial restraint [KS] Fox 2023 |
| M1.1.6 | Fan Stage 1 Blade Platform | aluminium alloy with elastomer seals [KS] Fox 2023 |
| M1.2 | Fan Stage 1 Case | assembly |
| M1.2.1 | Fan Stage 1 Case Shell | material tbd |
| M1.2.2 | Fan Stage 1 Containment Ring | material tbd |
| M1.3 | Fan Stage 1 Outlet Guide Vane | vane count doğrulanmadı |
| M1.4 | Fan Stage 1 Frame | aluminium [KS] Girão 2023 |

## Reference values
- Blade count conflict: CFM's 1997 CFM56-7 article (docs/sources.md #42) [K] gives 22 wide-chord blades; the production engines examined by the NTSB have 24 (Fox 2023) [KS]. The 1997 article may describe an earlier design. M1 uses 24.
- Mass sanity check: 24 fan blades together 118 kg [KS, weak: student thesis; Mirghani 2023 Table 3, printed p. 49 (PDF p. 67), citing other sources]. M1 blade mass estimates are compared with it; it is not a design input.

Not owned by M1: inlet cowl (airframe/nacelle), LP shaft and bearings 1-2 (M8), VBV (inside the fan frame; owner to be set by M0).
