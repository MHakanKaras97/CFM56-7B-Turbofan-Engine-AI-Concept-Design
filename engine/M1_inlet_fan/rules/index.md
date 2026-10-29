# M1 Inlet and Fan Rules

| File | Content |
|---|---|
| `budget.md` | Station ownership, budget via `read_icd`, tolerances, what to do out of tolerance |
| `bom.md` | Part numbering M1.1-M1.4, naming, material ids |
| `materials.md` | Material selection rules; values in `tools/data/materials.yaml` |
| `joints.md` | Dovetail, shim, coating stack, spacer/platform, flanges |
| `analyses.md` | Analyses A-1..A-9: method, tool, acceptance criterion, source |
| `failure_modes.md` | FM-1..FM-6, incl. CFM56-7B dovetail LCF case (Fox 2023) |
| `bird_strike.md` | Bird models, speeds, methods; certification numbers status |
| `aero_method.md` | Meanline method steps and loss models (diffusion factor, profile, shock, endwall) |
| `cs_e_800_birds.yaml` | CS-E 800 bird tables by inlet throat area (data for `analysis/bird_class.py`) |

Reference data: `learning/rotor67_reference.yaml` (NASA Rotor 67, validation case for A-1).

Workflow (M1 agent):
1. Read the budget with `core.budgets.read_icd`.
2. Work only under `engine/M1_inlet_fan/`; record revisions with `core.records.create_revision`.
3. Check results with `core.budgets.check_budget("M1", ...)`.
4. Cross-module needs: CR to M0 via `core/requests.py`, user approval required.

Status: step 4i-f (supersonic R-AM.9 floor back on the tube inlet pitch 2 pi r1 / 24, known deviation: conservative on most tubes; 1.8 % below Rotor 67 on tube 5 (expanding tube) by the paper's definition; user-accepted, revisit with M0 v2; R-AM.18 hub floor on the hub mean-radius pitch; solidity reported by the paper definition; valid design: converged, FPR 1.7650, pr_inner 1.3440, R-AM.9 9/9, hub solidity 3.110, tip 1.350, results.yaml regenerated, budget and integration pass, no revision, rev010 active). Step 4i-e (solidity = true chord x blade count / (2 pi r_mean), r_mean = mean of the blade-edge inlet and exit radii, for R-AM.18 and the supersonic R-AM.9 floor; implemented, but NO valid design: the stream PR balance stalls in pass 1 about 1.5e-4 short in both streams; results.yaml still the step 4i-c run, rev010 active; open for user decision). Step 4i-c (R-AM.16 level = smallest A_root with derived mid and tip t/c inside the Rotor 67 ranges; hub t/c known deviation, user-accepted; valid design, results.yaml regenerated, no revision yet; open item tip t/c at the lower bound -> bird strike and flutter). Step 4i-b (R-AM.18 root chord floor hub solidity >= Rotor 67 3.11; R-AM.16 area level from the stress rule; implemented, but the level is undetermined because the steady stress does not depend on the root area, and no level puts the derived t/c in range at all three span thirds; results.yaml still from step 4h, rev009 active, open for user decision). Step 4i (chord plain quadratic from the R-AM.9 needs, section area as its own linear law with the Rotor 67 taper and hub t/c level, derived t/c checked against Rotor 67 span-third ranges, R-AM.17 chord roughness, stress <= half the allowable; implemented, but no PR-balanced design exists: outer FPR maximum about 0.4 % short, derived mid/tip t/c far below range; results.yaml still from step 4h, open for user decision). Step 4h (R-AM.9 needs from the balanced state, R-AM.15 section stress along the span, R-AM.16 monotonic section area, R-AM.17 chord smoothness vs Rotor 67; R-AM.16 and R-AM.17 not met by the R-AM.14 chord law, reported, open for user decision). Step 4g: R-AM.14 chord law quadratic + C2 local bump, Rotor 67 t/c benchmark. Step 4f: part 1 R-AM.13 root sizing, kappa2 blend limits, tip check; part 2 vortex law stated, blade mass diagnosis. Meanline validated on Rotor 67 at the design point (A-1, no radial equilibrium, no added losses); CS-E 800 bird class (A-7 input); CFM56-7B27 fan rotor as one smooth blade with radial equilibrium and the full loss model, budget efficiencies per ADR-015 (`analysis/fan_design.py`, section profile `analysis/blade_profile.py`, params `analysis/fan_params.yaml`, results `analysis/results.yaml`, calc plugin `analysis/calc.py`; rules R-AM.7, R-AM.9 (step 4e), R-AM.10, R-AM.11, R-AM.12, R-AM.13, R-AM.14, `aero_method.md` smooth blade and structure sections). No 3D geometry yet.
