# M1 BOM Rules

- Single source of truth: `engine/M1_inlet_fan/bom/bom.yaml`, written only via `core.bom.write`; no comments, use `notes`.
- Part id `M1.<group>.<part>`; name `"Fan Stage 1 <Part type>"`. Repeated parts: one entry with `qty`.
- `material` is an id from `tools/data/materials.yaml`, `tbd` while not selected, or null for an assembly.
- Every part starts as `draft`; geometry is added only by a script in `geometry/`.

## Numbering
| Id | Part | Notes |
|---|---|---|
| M1.1 | Fan Stage 1 Rotor | assembly |
| M1.1.1 | Fan Stage 1 Rotor Blade | x24 [KS] Girão 2023, also Fox 2023 |
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

Not owned by M1: inlet cowl (airframe/nacelle), LP shaft and bearings 1-2 (M8), VBV (inside the fan frame; owner to be set by M0).
