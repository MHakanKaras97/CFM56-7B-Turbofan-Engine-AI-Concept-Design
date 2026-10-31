# M2 BOM Rules

- `bom/bom.yaml` is the single source of truth; written only through `core.bom.write` / `core.bom.dump`, no comments
  (use `notes`). Step 1: the list below is the planned part set; `bom.yaml` stays empty until geometry exists.
  Step 4 (geometry, R-G2.24): `bom.yaml` is written from the geometry part list by `geometry/bom_update.py`; see the
  amendment at the end of this file.
- Part id `M2.<stage>.<part>`; stage 1-3 = booster stages, stage 0 = parts common to the booster. Name
  `"Booster Stage <n> <Part type>"`; common parts `"Booster <Part type>"`. Repeated parts: one entry + `qty`.
- Owner of every part below: M2. No geometry, no values at step 1; blade counts, radii and chords come from code by
  the R-AM2.3 proportional rule [T].

| Id | Name | Note |
|---|---|---|
| M2.1.1 | Booster Stage 1 Rotor Blade | qty = blade count from R-AM2.2/R-AM2.3 |
| M2.1.2 | Booster Stage 1 Stator Vane | qty as above |
| M2.1.3 | Booster Stage 1 Abradable Liner | case liner over the rotor tips |
| M2.2.1 | Booster Stage 2 Rotor Blade | |
| M2.2.2 | Booster Stage 2 Stator Vane | |
| M2.2.3 | Booster Stage 2 Abradable Liner | |
| M2.3.1 | Booster Stage 3 Rotor Blade | |
| M2.3.2 | Booster Stage 3 Stator Vane | stage 3 stator; whether a separate booster exit guide vane row exists: doğrulanamadı |
| M2.3.3 | Booster Stage 3 Abradable Liner | |
| M2.0.1 | Booster Drum | the "booster spool" LLP: 23,600 EFC, 22,900 EFC for -7B27 (Owner's Guide mtce s. 19-20) [KS] |
| M2.0.2 | Booster Case | carries the stator vanes and abradable liners |
| M2.0.3 | Booster Spool-to-Fan-Disk Joint | bolted flange set; the fan disk flange itself is M1.1.2 (M1) |

- Not M2 parts: VBV hardware (openings, doors, actuation) stays in the M1 fan frame (#48); LP shaft and bearings (M8).
- Materials: `material` id from `tools/data/materials.yaml` or `tbd` (see `materials.md`).

## Step 4 amendment (geometry step 4, R-G2.24)

Change and reason: the BOM now follows the geometry part list; parts without geometry are not BOM entries.
- Added: M2.1.4, M2.2.4, M2.3.4 `Booster Stage <n> Inner Shroud` (qty 1, full ring, R-G2.11; proposed in step 2).
- Not BOM entries until they have geometry: M2.1.3-M2.3.3 abradable liners (not modelled, R-G2.12) and M2.0.3
  spool-to-fan-disk joint (the drum flange and forward cone are inside M2.0.1, bolts not modelled, J2-1, #76).
- Root blocks stay inside M2.n.1, vane feet inside M2.n.2 (one part each: airfoil + root, vane + foot; their masses
  are summed into the unit mass, the split is in `notes`).
- No assemblies (all parents null); rotor blade qty tag [KS] (known_values.md), stator vane qty tag [T] (R-KV2.1),
  rings and drum qty 1 [G]; status `draft` (materials tbd, structural stage not done).
