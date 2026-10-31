# How does a turbofan work?

A turbofan is a jet engine in which a small gas turbine (the core) drives a large fan. Almost every airliner today
uses turbofans, because they are efficient at high speed and comparatively quiet.

## The principle in four steps (Brayton cycle)
1. **Intake:** the fan draws air in.
2. **Compression:** the compressors raise the air pressure by tens of times.
3. **Combustion:** fuel is sprayed into the compressed air and burned; the gas gets very hot.
4. **Expansion:** the hot gas drives the turbines, then leaves the nozzle at high speed.

The turbines produce the power that drives the compressors and the fan. The remaining energy becomes thrust.

## Bypass: the secret of the turbofan
- Most of the air pushed by the fan does not enter the core; it flows around it (the **bypass**).
- The ratio of bypass air to core air is the **bypass ratio**. On the CFM56-7B it is about 5.
- Accelerating a lot of air a little is more efficient than accelerating a little air a lot.
  That is why most of the thrust comes from the fan and the fuel burn is low.

## Two-spool layout
- **Low-pressure (LP) spool:** fan + booster, driven by the low-pressure turbine. Turns slowly.
- **High-pressure (HP) spool:** high-pressure compressor, driven by the high-pressure turbine. Turns fast.
- The two shafts are concentric and turn at independent speeds, so each component runs near its best speed.

## About the CFM56-7B
- Built by CFM International (a GE and Safran joint company); the only engine of the Boeing 737 Next Generation family.
- Layout: 1-stage fan, 3-stage booster, 9-stage high-pressure compressor, single annular combustor,
  1-stage high-pressure turbine, 4-stage low-pressure turbine.
- One of the most produced airliner engine families in the world.

## The modules of this project
| Module | Section | Short task |
|---|---|---|
| M1 | Inlet and fan | Takes in the air, makes most of the bypass thrust |
| M2 | Booster | First compression of the core air |
| M3 | High-pressure compressor | The biggest pressure rise |
| M4 | Combustor | Burns the fuel, heats the gas |
| M5 | High-pressure turbine | Drives the HP compressor |
| M6 | Low-pressure turbine | Drives the fan and the booster |
| M7 | Nozzles | Accelerate the gas and make thrust |
| M8 | Shafts and bearings | Carry the rotating parts, transmit power |
| M9 | Secondary air, oil, gearbox | Cooling, lubrication and accessory drive |

## Station numbers
Engineers name points along the gas path with numbers (SAE AS755): **2** fan face, **13** fan exit (bypass),
**25** HP compressor inlet, **3** HP compressor exit, **4** turbine inlet (hottest point), **45** LP turbine inlet,
**5** LP turbine exit, **8** core nozzle exit, **18** fan nozzle exit.

## Three kinds of numbers to remember
- **Pressure ratio:** how many times the air is compressed. Higher means more efficient.
- **Turbine inlet temperature:** the hottest point of the engine. Higher gives more power but makes materials and cooling harder.
- **Specific fuel consumption (SFC):** fuel burned per unit thrust. The lower, the better.
