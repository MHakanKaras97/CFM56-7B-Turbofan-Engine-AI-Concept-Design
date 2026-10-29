# M3 Known Values

Values from sources for the CFM56-7B27 HP compressor. Each value carries its tag and source number (`docs/sources.md`). Values from `CFM56_Answers.txt` are rejected and never used.

## Rotor blade counts

| Stage | Rotor blades | Tag | Source |
|---|---|---|---|
| HPC stage 1 | 38 | [KS] | #52, p. 159 |
| HPC stage 2 | 53 | [KS] | #52, p. 159 |
| HPC stage 3 | 60 | [KS] | #52, p. 159 |
| HPC stage 4 | 68 | [KS] | #52, p. 159 |
| HPC stage 5 | 75 | [KS] | #52, p. 159 |
| HPC stage 6 | 82 | [KS] | #52, p. 159 |
| HPC stage 7 | 82 | [KS] | #52, p. 159 |
| HPC stage 8 | 80 | [KS] | #52, p. 159 |
| HPC stage 9 | 76 | [KS] | #52, p. 159 |

Read from the page image, not from OCR text.

## Stator vane counts

No source value (#52 gives rotor blades only; open item #62 in `docs/open_issues.md`).

- **R-KV3.1 Stator vane count** [T]: from a stated proportional rule (required solidity and chord) in this module's rule book, to be written at design time; the count differs from the adjacent rotor counts (avoid coincident rotor-stator interaction [G]). The value comes from code, never from this file.

## Variable geometry

- IGV plus variable stator vanes on HPC stages 1-3 [KS] (#52, manual text (OCR; -7B effectivity not confirmed sentence by sentence)).

## LLP lives

| Part | Life (EFC) | Tag | Source |
|---|---|---|---|
| HPC forward shaft | 20,000 | [KS] | #49 (ISSUE58), p. 20, -7B27 column |
| HPC stage 1-2 spool | 20,000 | [KS] | #49 (ISSUE58), p. 20, -7B27 column |
| HPC stage 3 disk | 20,000 | [KS] | #49 (ISSUE58), p. 20, -7B27 column |
| HPC stage 4-9 spool | 20,000 | [KS] | #49 (ISSUE58), p. 20, -7B27 column |
| HPC CDP seal | 20,000 | [KS] | #49 (ISSUE58), p. 20, -7B27 column |

- Configuration: the ISSUE58 table header reads "non-Tech Insertion engines"; the label "before Tech Insertion" is unverified.
