# M2 Joints

- **J2-1 Spool-to-fan-disk joint (M2.0.3, interface with M1)**: the booster drum is bolted to the aft face of the fan
  disk (M1.1.2); the fan/booster module separates from the core as one unit (Owner's Guide mtce s. 19: the fan disk
  can be replaced after removing the fan blades without disassembling the module) [KS]. Bolt count, circle radius and
  flange thickness: no source -> [T] rule at design time. The M1 flange geometry is read from the M1 record, never
  changed by M2; a needed change is a CR.
- **J2-2 Rotor blade attachment**: dovetail type (axial or circumferential) for the CFM56-7B booster: doğrulanamadı.
  Concept: one attachment per stage, sized by the blade pull with the R-AM.15-type margin rule (see `analyses.md`).
- **J2-3 Stator vanes to case**: vanes carried by the case (M2.0.2); inner shroud type: doğrulanamadı.
- **J2-4 Abradable liner**: liner over each rotor tip in the case; tip clearance [T] (TP-1523 static clearances
  0.023-0.069 cm on a 25.4 cm tip radius, Table 18 p. 48 [K], used only as a scale reference).
- **VBV boundary**: no M2 hardware joint; the VBV openings are in the M1 fan frame (#48). M2 owns only the flow function
  (not modelled at the design point).
