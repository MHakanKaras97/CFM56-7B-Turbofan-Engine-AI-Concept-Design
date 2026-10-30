# M8 Known Values

Values from sources for the CFM56-7B27 shaft and bearing. Each value carries its tag and source number (`docs/sources.md`). Values from `CFM56_Answers.txt` are rejected and never used.

## LLP lives

| Part | Life (EFC) | Tag | Source |
|---|---|---|---|
| Fan shaft | 30,000 | [KS] | #49 (ISSUE58), p. 20, -7B27 column |

- Configuration: the ISSUE58 table header reads "non-Tech Insertion engines"; the label "before Tech Insertion" is unverified.
- Booster spool LLP life: moved to `engine/M2_booster/rules/known_values.md` (drum M2.0.1 is M2's part).
