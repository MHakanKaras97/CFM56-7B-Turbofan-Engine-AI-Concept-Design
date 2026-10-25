# M1 Bird Strike

Summary of `learning/sources/bird_strike/`. Values are what each study used, not requirements.

## Certification requirement: CS-E 800 [K]
Source: EASA Easy Access Rules for Engines (CS-E), Amendment 5, CS-E 800 (ED Decision 2018/014/R), pp. 180-187 (`learning/sources/regulation/easa_cs-e_easy_access_amdt5.pdf`). Summary in our words; the regulation text governs.

Which basis applies: EASA TCDS E.004 lists, for the CFM56-7B27 "SAC" build, JAR-E Change 8 plus Special Condition No. 1 "Bird strikes" [K]; later builds (/3, E) list CS-E 800 (CS-E dated 24 Oct 2003) [K]. The special condition text was not read (doğrulanmadı). M1 designs to current CS-E 800 (Amdt 5) (user decision, M1 step 2b).

The bird mass and number depend on the engine inlet throat area A, which the applicant declares as an installation limitation (CS-E 800(g)(8)). A for the CFM56-7B: doğrulanmadı. The nacelle is out of scope, so the fan face area from the ICD is the proxy [T].

M1 bird class (`analysis/bird_class.py` -> `analysis/bird_class.yaml`; tables in `rules/cs_e_800_birds.yaml` [K]): with A = 1.716 m2 [T], large single bird 2.75 kg; large flocking bird not required (A < 2.50 m2); medium birds 1 x 1.15 + 4 x 0.70 kg (integrity 1 x 1.15 kg); small birds 16 x 85 g; core flocking bird 1.15 kg. The proxy is 0.9 % above the 1.70 m2 medium band edge: a throat area that much smaller drops the medium set to 1 x 1.15 + 3 x 0.70 kg. The large-bird class holds for A from 1.35 to 3.90 m2.

| Test | Engine condition | Bird | Speed | Pass criterion |
|---|---|---|---|---|
| (b) Single large bird | >= 100 % take-off thrust; account for hot-day sea level take-off | min. 1.85 kg (A < 1.35 m2), 2.75 kg (1.35 <= A < 3.90), 3.65 kg (A >= 3.90); aimed at the most critical exposed location of the first-stage rotor blades | 200 kn (aeroplane) | No Hazardous Engine Effect; no power lever movement for 15 s |
| (c) Large flocking bird (only A >= 2.50 m2) | rotor speed giving 90 % of SLS rated take-off thrust, ISA | 1.85 kg (2.50 <= A < 3.50), 2.10 kg (3.50 <= A < 3.90), 2.50 kg (A >= 3.90); at >= 50 % blade height, leading edge | 200 kn | Complete the 20-min run-on schedule (steps 1-6); no shutdown; thrust not sustained below 50 % in step 1; no Hazardous Engine Effect |
| (d) Medium (flocking) birds | >= 100 % take-off thrust | Table A, by A; e.g. 1.35 <= A < 1.70: 1 x 1.15 + 3 x 0.70 kg; 1.70 <= A < 2.10: 1 x 1.15 + 4 x 0.70 kg; 2.10 <= A < 2.50: 1 x 1.15 + 5 x 0.70 kg. Largest at the core, one at the most critical rotor location | critical speed in normal operation up to 1500 ft AGL, not below V1 | Not more than a sustained 25 % thrust loss; no shutdown during the 20-min schedule |
| (d)(3) Medium birds, rotor integrity | - | Table A third column, e.g. 1 x 1.15 kg for 1.35 <= A < 2.90 | as (d) | Rotor still meets (d)(2) |
| (d)(1)(v)(B) Small birds | as (d) | one 85 g bird per 0.032 m2 of A, max 16 | as (d) | as (d) |
| (e) Core flocking bird (turbofan) | rotor speed for lowest climb thrust through 3000 ft AGL | heaviest Table A bird, aimed to put most material into the core | 250 kn | No sustained thrust below 50 % that the power lever cannot restore; no shutdown in the run-on; no Hazardous Engine Effect |
| (f) Impact on engine front | as ingestion tests | largest medium bird and the large bird | critical speed up to 1500 ft, not below V1 | Assessed for CS-E 540, incl. damage to rotating blades |

Notes [K]:
- Table A read in `pdftotext -raw` mode; the `-layout` mode shifts the rows by one line.
- Alternative evidence (rig tests, analysis, similar engines) may replace tests by agreement (CS-E 800(g)(1)).

Earlier summary (kept for context): Wang 2024 (p. 2) [KS] recounts the FAA FAR 33.76/33.77 amendment history; superseded here by the CS-E text.

## Bird models used
| Source | Bird | Mass | Density | Speed | Fan state |
|---|---|---|---|---|---|
| Mao 2008, pp. 83-84 [KS] | Hemispherical-ended cylinder, L/D 2 (also straight cylinder, ellipsoid) | 4 lb (1.82 kg); also 6 lb | 934 kg/m3 | 225 m/s (also 83, 318) | Stationary blade, hit at 85 % radius, 60 deg local angle |
| Wu 2021, pp. 3-5 [KS] | Mallard from CT scan, SPH, 41,685 particles | 820 g | 938 kg/m3 | 116 m/s axial | 836-3772 r/min |
| Wu 2022, pp. 2-9 [KS] | Same mallard, SPH | 820 g | 938 kg/m3 | 253, 225, 116 m/s | 600 rad/s baseline |
| Wang 2024, pp. 6-7 [KS] | SPH bird | 0.680 kg | 970 kg/m3 | 100 m/s axial | 500 rad/s |
| Zeng 2015, pp. 1387-1389 [KS] | Cylinder, ALE | 1 kg (validation) | not read | 197 m/s (validation); 100 m/s axial on blade | 9000 r/min, hit at 67 % span |

## Modelling approach
- Bird as a fluid-like body above about 100 m/s: hydrodynamic pressure-volume law with negligible strength (Mao 2008, p. 83) [KS].
- Formulations: Lagrangian solid elements (Mao 2008; good for one blade, needs a fine mesh, bird diameter / element size 32), ALE (Zeng 2015), SPH (Wu 2021, Wu 2022, Wang 2024). Mao 2008 reviews that Lagrangian meshes distort, ALE needs a fine Eulerian mesh, SPH avoids mesh tangling (pp. 81-82) [KS].
- Equation of state: polynomial (Brockman) in Mao 2008; Gruneisen with sound speed 1480 m/s in Wu 2021/2022 and Wang 2024 [KS].
- Blade material: Perzyna viscoplastic (Mao 2008); Johnson-Cook with Gruneisen EOS for Ti-6Al-4V (Wu 2022, Wang 2024) [KS].
- Validation against Wilbeck rigid-plate tests (Wu 2022, Zeng 2015) [KS].
- Slicing: the rotating fan cuts the bird into slices; the slice length follows from axial speed, rotor speed and blade count (Wang 2024, pp. 3-4) [KS].
- Rotor dynamics: the strike force applied to a shaft-bearing model (Newmark integration) excites the first rotor mode (Wu 2021) [KS]. Interface with M8.

## Findings that drive M1 design [KS]
- Peak force depends on the early contact area: straight cylinder > hemispherical > ellipsoid; L/D has little effect (Mao 2008, p. 95).
- Normal incidence gives the highest force and plastic strain; at 60 deg or more the blade stays elastic (Mao 2008, abstract).
- Impact at the blade root is the worst location (390 kN in Wu 2022, abstract); multiple strikes near the root are the most damaging (Wang 2024, abstract).
- Higher rotor speed raises the impact force (Wu 2021, abstract).
- A hollow blade deforms less and fails more material than a solid one (Zeng 2015, abstract).

## M1 rules
- R-BS.1 Bird strike is analysed on the rotating blade at take-off speed, with impact positions at least at root, mid span and tip [G].
- R-BS.2 Use SPH or ALE with a Gruneisen EOS and a Johnson-Cook Ti-6Al-4V model; validate the bird on a rigid-plate case first [KS methods].
- R-BS.3 Bird masses, speeds and pass criteria are those of CS-E 800 above [K]; the size class comes from `analysis/bird_class.py` with the fan face area as throat area proxy [T] until the nacelle defines it.
