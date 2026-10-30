# M2 Booster Rules

| File | Content |
|---|---|
| `budget.md` | Station ownership 21 -> 24 -> 25, budget via `read_icd`, tolerances, VBV boundary |
| `bom.md` | Part list and numbering (parts only, no geometry yet) |
| `aero_method.md` | Definitions (solidity, DF, phi, psi, AR, hub/tip), meanline plan, R-AM2.1-4, TP-1523 applicability, A-1 |
| `materials.md` | Material selection rule; values in `tools/data/materials.yaml` |
| `joints.md` | Spool-to-fan-disk joint with M1, blade attachments, abradable, VBV boundary |
| `analyses.md` | Analyses A-1..A-5: method, acceptance criterion, source |
| `failure_modes.md` | FM2-1..FM2-5: FOD/ice/hail, stall/surge, tip rub, drum LCF, blade HCF |
| `geometry.md` | Geometry step 1: frame (M1 convention), axial layout, section profile, trim, flow path, clearance, material for mass, checks (R-G2.1-8); step 2: drum, root slots, inner shrouds and seals, casing and vane grooves, M1 interface, drum ownership, checks (R-G2.9-17); step 3a: hardware boundary = M1 disk aft face, drum forward cone, sloped slot bottom (R-G2.18-19); step 3b: hub flow-path wall (R-G2.20, #79) |
| `known_values.md` | Source values: booster rotor counts 74/78/74 [KS] (#52); stator count rule R-KV2.1 [T] |
| `open_items.md` | Pointer to the M2 rows in `docs/open_issues.md` |

Reference data: `learning/tp1523_reference.yaml` (NASA TP-1523 stages; reference stage and A-1 validation case).
Sources: `learning/sources/INDEX.md`. Lesson: `learning/ders02_booster.md`.

Workflow (M2 agent):
1. Read the budget with `core.budgets.read_icd("M2 ...")`; read the M1 station 21 annulus from
   `engine/M1_inlet_fan/geometry/flowpath.yaml` (read-only; M1 is accepted at rev014, any M1 change needs an approved CR).
2. Work only under `engine/M2_booster/`; record revisions with `core.records.create_revision`.
3. Check results with `core.budgets.check_budget("M2", ...)`.
4. Cross-module needs: CR to M0 via `core/requests.py`, user approval required.

Acceptance (ADR-016) applies from the start: reproducible record, M0 budget pass, structural safety rules pass,
deviations in `docs/open_issues.md`.

Status: step 4 (#68 spanwise normalisation, closure ratios 1; #64 levers in a written order: L2 constant tip radius
applied, L1/L3 not; remaining rotor tip violations stage 2 and 3, drafted as #69/#70 in `open_items.md`). A-1 pass.
Booster section values [T]. M3 interface: `geometry/flowpath.py` -> `geometry/flowpath.yaml` (station 25 annulus).
No revision; `bom/bom.yaml` has no parts. Geometry step 2 (`geometry/hardware.py`, R-G2.9-17): drum, inner
shrouds, casing; drafts #75-#77 in `open_items.md`. Step 3a: forward cone (#76) and sloped slots (#75)
applied (R-G2.18-19), casing and #77 wait for CR-002/CR-003. Step 3b: hub flow-path wall
(R-G2.20, #79) in the drum; M1 platform top below the hub line drafted as #80. Lesson: `learning/not_geometri2_donanim.md`.
