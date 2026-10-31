"""M9 secondary air and oil parts, BOM and STEP files (rules/design.md R-D9.1-3) from analysis/design.run.

Parts: M9.0.1 inlet gearbox, M9.0.2 radial drive shaft, M9.0.3 transfer gearbox, M9.0.4 horizontal drive shaft,
M9.0.5 accessory gearbox, M9.0.6 oil tank, M9.0.7 forward sump oil supply line, M9.0.8 aft sump oil supply line,
M9.0.9 stage 5 bleed duct. STEP: .cache/geometry/M9_secondary_air_oil/<revision>/.

Run: python -m engine.M9_secondary_air_oil.geometry.build
"""

import cadquery as cq

from engine.M9_secondary_air_oil.analysis import design as D
from tools import concept as C

REVISION = "rev001"
SCRIPT = "engine/M9_secondary_air_oil/geometry/build.py"
NAME = "Secondary Air and Oil"


def _box(b: dict) -> cq.Shape:
    """Envelope box on the +Z side between radii r0 and r1, turned to its clock angle."""
    s = C.box(b["x0"], b["x1"], -b["half_width"], b["half_width"], b["r0"], b["r1"])
    return C.rotate_x(s, b["angle"])


def _tube(path, r_out, t) -> cq.Shape:
    return C.tube([D.polar(*q) for q in path], r_out, t)


def build(res: dict | None = None) -> C.Module:
    res = res or D.run()
    mat = C.v(res["params"]["materials"])
    mod = C.Module("M9", NAME, REVISION)
    ds, ol, bl = res["drive_shaft"], res["oil_line"], res["bleed"]
    igb, tgb, agb, tank = (_box(res[k]) for k in ("igb", "tgb", "agb", "tank"))

    def trimmed(path, r_out, t, *boxes):  # shaft and line ends stop at the housing faces
        s = _tube(path, r_out, t)
        for b in boxes:
            s = s.cut(b)
        return s.clean()
    mod.add(C.Part("M9.0.1", "Inlet Gearbox", igb, mat["gearbox"],
                   "Bevel gear set driven by the HP rotor at the forward sump; turns the drive into the radial shaft "
                   "(R-D9.1)", process="casting", notes="Envelope box; gears and the HP bevel gear not modelled."))
    mod.add(C.Part("M9.0.2", "Radial Drive Shaft", trimmed(res["rds"], ds["r_out"], ds["thickness"], igb, tgb), mat["drive_shaft"],
                   "Drive from the inlet gearbox to the transfer gearbox through the 6 o'clock fan frame struts",
                   process="forging", joints=[("M9.0.1", "spline"), ("M9.0.3", "spline")],
                   notes="Passage through the M1 frame struts and rings not cut (R-D9.4)."))
    mod.add(C.Part("M9.0.3", "Transfer Gearbox", tgb, mat["gearbox"],
                   "Turns the radial drive into the horizontal drive shaft (R-D9.1)", process="casting",
                   notes="Envelope box."))
    mod.add(C.Part("M9.0.4", "Horizontal Drive Shaft", trimmed(res["hds"], ds["r_out"], ds["thickness"], tgb, agb),
                   mat["drive_shaft"], "Drive from the transfer gearbox to the accessory gearbox along the frame ring",
                   process="forging", joints=[("M9.0.3", "spline"), ("M9.0.5", "spline")]))
    mod.add(C.Part("M9.0.5", "Accessory Gearbox", agb, mat["gearbox"],
                   "Drives the accessories (fuel and oil pumps, generator, starter pad) on the fan frame ring (R-D9.1)",
                   process="casting", joints=[("M1.4.2", "bolted_flange")],
                   notes="Envelope box; accessories out of scope (architecture.md)."))
    mod.add(C.Part("M9.0.6", "Oil Tank", tank, mat["tank"], "Engine oil reservoir on the fan frame ring "
                   "(R-D9.2)", process="welded sheet", joints=[("M1.4.2", "bolted_flange")], notes="Envelope box."))
    mod.add(C.Part("M9.0.7", "Forward Sump Oil Supply Line", trimmed(res["oil_fwd"], ol["r_out"], ol["thickness"], tank, tgb),
                   mat["tube"], "Oil feed from the tank to the forward sump (bearings #1-#3) through the 6 o'clock "
                   "struts (R-D9.2)", process="drawn tube", notes="Passage through M1 struts not cut (R-D9.4)."))
    mod.add(C.Part("M9.0.8", "Aft Sump Oil Supply Line", _tube(res["oil_aft"], ol["r_out"], ol["thickness"]),
                   mat["tube"], "Oil feed in the core compartment to the aft sump (bearing #5) through a turbine rear "
                   "frame strut (R-D9.2)", process="drawn tube",
                   notes="Passage through the M7 TRF strut and rings not cut (R-D9.4); link to the tank through the "
                         "fan frame not modelled."))
    mod.add(C.Part("M9.0.9", "Stage 5 Bleed Duct", _tube(bl["path"], bl["r_out"], bl["thickness"]), mat["tube"],
                   "Interstage leak from the HPC stage 5 port (M3) to the LPT case at stage 1 (return 45, R-D9.3)",
                   process="drawn tube", notes=f"Bore radius {bl['r_bore']:.4f} m [H] from W, Tt, Pt at the port."))
    return mod


def main() -> None:
    from core.util import write_yaml
    res = D.run()
    write_yaml(D.OUT_FILE, D.to_yaml(res))
    C.write_interface("M9", D.interface(res))
    mod = build(res)
    warn = mod.write_bom(SCRIPT)
    paths = mod.export()
    print("M9 mass", round(mod.mass(), 2), "kg; parts", len(mod.parts), "; warnings", len(warn), ";", paths["assembly"])


if __name__ == "__main__":
    main()
