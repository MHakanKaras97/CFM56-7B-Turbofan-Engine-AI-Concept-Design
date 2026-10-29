# M5 Known Values

Values from sources for the CFM56-7B27 HP turbine. Each value carries its tag and source number (`docs/sources.md`). Values from `CFM56_Answers.txt` are rejected and never used.

## Rotor blade counts

| Stage | Rotor blades | Tag | Source |
|---|---|---|---|
| HPT stage 1 | 80 | [KS] | #52, p. 159 |

Read from the page image, not from OCR text.

## NGV counts

No source value (#52 gives rotor blades only; open item #62 in `docs/open_issues.md`).

- **R-KV5.1 NGV count** [T]: from a stated proportional rule (required solidity and chord) in this module's rule book, to be written at design time; the count differs from the adjacent rotor counts (avoid coincident rotor-stator interaction [G]). The value comes from code, never from this file.

## LLP lives

| Part | Life (EFC) | Tag | Source |
|---|---|---|---|
| HPT front shaft | 17,300 | [KS] | #49 (ISSUE58), p. 20, -7B27 column |
| HPT front air seal | 17,300 | [KS] | #49 (ISSUE58), p. 20, -7B27 column |
| HPT disk | 19,200 | [KS] | #49 (ISSUE58), p. 20, -7B27 column |
| HPT rear shaft | 20,000 | [KS] | #49 (ISSUE58), p. 20, -7B27 column |

- Configuration: the ISSUE58 table header reads "non-Tech Insertion engines"; the label "before Tech Insertion" is unverified.
- ISSUE39 (Aircraft Commerce Owner's Guide) differs: HPT disk 20,000 EFC. ISSUE39 is not yet in `docs/sources.md` and has no text in the archive: doğrulanamadı.
