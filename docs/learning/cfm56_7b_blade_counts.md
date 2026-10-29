# CFM56-7B rotor blade counts (extract)

Source: CFMI "CFM56-ALL Training Manual", Borescope Inspection, appendix "Blade quantities", page 159, revision Sep 2003.
The manual carries a CFMI proprietary / training-purposes-only notice. The original PDF stays in the source archive, outside git.
Tag: [KS]. The table was read from the page image, not from OCR text (OCR garbled the HPT column).

| Rotor | Count per stage |
|---|---|
| Fan (ST1) | 24 |
| Booster (ST2-ST4 of the "fan & booster" columns, i.e. booster stages 1-3) | 74 / 78 / 74 |
| HPC (stages 1-9) | 38 / 53 / 60 / 68 / 75 / 82 / 82 / 80 / 76 |
| HPT (stage 1) | 80 |
| LPT (stages 1-4) | 162 / 150 / 150 / 134 |

## Limits
- Rotor blades only. Stator and NGV counts are not given: use a stated [T] rule and list as open items.
- Fan 24 agrees with M1 (Girao 2023, Fox 2023). The 22 in the 1997 CFM article remains an earlier-design question, not a design input.
- Also seen in the manual text (OCR, "-7B" effectivity not confirmed sentence by sentence): 20 double-tip fuel nozzles in the SAC; IGV plus variable stator stages 1-3 in the HPC.
- Not covered by pages 0-125 and 140-185 (the pages OCR'd so far): bearing and sump layout. The 3-sump (unsourced answer) vs 2-sump (secondary summary) conflict stays open.

## Use
Input to the rule books of M2, M3, M5, M6 as [KS] values. Do not copy manual text into the repo; cite page 159 only.
