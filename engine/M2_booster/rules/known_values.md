# M2 Known Values

Values from sources for the CFM56-7B booster. Each value carries its tag and source number (`docs/sources.md`).
Extract and limits: `docs/learning/cfm56_7b_blade_counts.md`.

## Rotor blade counts

| Stage | Rotor blades | Tag | Source |
|---|---|---|---|
| Booster stage 1 | 74 | [KS] | #52, p. 159 |
| Booster stage 2 | 78 | [KS] | #52, p. 159 |
| Booster stage 3 | 74 | [KS] | #52, p. 159 |

- Read from the page image (booster stages 1-3 = ST2-ST4 of the "fan & booster" columns), not from OCR text.
- Use: check value for the rotor count from R-AM2.3 (`aero_method.md`). Whether these counts replace the
  R-AM2.3 rotor count is a user decision; until then R-AM2.3 sets the design value.

## Stator vane counts

No source value (#52 gives rotor blades only; open item #62 in `docs/open_issues.md`).

- **R-KV2.1 Stator count** [T]: stator vane count per stage from R-AM2.3 (stator AR 1.2, sigma_req from R-AM2.2);
  the count differs from the adjacent rotor counts (avoid coincident rotor-stator interaction [G]).
  The value comes from code, never from this file.
