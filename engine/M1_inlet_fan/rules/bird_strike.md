# M1 Bird Strike

Summary of `learning/sources/bird_strike/`. Values are what each study used, not requirements.

## Certification numbers
- Wang 2024 (p. 2) [KS] summarizes the FAA history: FAR 33.77 Amdt 6 refined bird weight and number for ingestion tests; Amdt 20 (2000) set medium-bird ingestion with 1.5-2.5 lb birds and up to six birds, scaled with engine inlet area; Amdt 23/24 (2007) raised post-ingestion criteria and added large flocking birds.
- These are a secondary summary; the regulation text (14 CFR 33.76, CS-E 800) was not read. Exact bird masses, speeds and pass criteria for the CFM56-7B fan size: doğrulanmadı.
- Large single bird mass (e.g. 4 lb or 8 lb class) as a requirement: doğrulanmadı. Mao 2008 calls a 4 lb bird "canonical" but cites no rule.
- Zeng 2015 (p. 1386) names CCAR-33R2 (China) and FAR as the criteria; no numbers.

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
- R-BS.3 Bird masses and speeds come from the regulation text once read; until then the case is marked [T].
