"""Concept-level design toolkit shared by M3-M9 (docs/m3_m9_plan.md).

Sizing: annulus area from W, Tt, Pt and an axial Mach number through the mass flux function (perfect gas with
gamma and R of the NASA polynomials at the station temperature and FAR, tools/thermo.NasaGas) [G].
Geometry (CadQuery, metres, M1 frame R-G1/R-G2.1: X engine axis positive aft, origin in the fan rotor stacking
plane, radial plane Y/Z, reference blade at +Z): revolved solids from closed (x, r) polygons, circular-arc
cambered blades lofted hub -> tip, disks (bore / web / rim), and a Module that writes the BOM through
core.bom.write, one STEP per part and the module assembly STEP (instances placed by rotation about X).
Masses = solid volume x density [H]; densities are [G] handbook values (information only).
"""

import math
from dataclasses import dataclass, field
from pathlib import Path

import cadquery as cq

from core import bom as core_bom
from core.records import ROOT, module_dir
from core.util import read_yaml, write_yaml
from tools.thermo import NasaGas

AXIS_O = cq.Vector(0, 0, 0)
AXIS_X = cq.Vector(1, 0, 0)

# kg/m3 [G] (handbook room-temperature values)
DENSITY = {
    "ti6al4v": 4430.0, "ti6242": 4540.0, "inconel718": 8190.0, "inconel625": 8440.0, "waspaloy": 8190.0,
    "rene88dt": 8300.0, "cmsx4": 8700.0, "rene_n5": 8630.0, "rene77": 7910.0, "hastelloy_x": 8220.0,
    "haynes188": 8980.0, "mar_m247": 8540.0, "steel_m50": 7830.0, "maraging_c250": 8000.0, "aisi9310": 7850.0,
    "ss321": 7920.0, "al_2219": 2840.0, "al_c355": 2710.0, "mg_ze41": 1840.0, "composite_cfrp": 1600.0,
}

COLOR = {
    "ti6al4v": (0.70, 0.72, 0.75), "ti6242": (0.66, 0.68, 0.72), "inconel718": (0.62, 0.58, 0.52),
    "inconel625": (0.60, 0.56, 0.50), "waspaloy": (0.58, 0.55, 0.50), "rene88dt": (0.55, 0.52, 0.48),
    "cmsx4": (0.80, 0.62, 0.30), "rene_n5": (0.82, 0.60, 0.28), "rene77": (0.75, 0.58, 0.35),
    "hastelloy_x": (0.55, 0.45, 0.40), "haynes188": (0.52, 0.42, 0.38), "mar_m247": (0.78, 0.55, 0.30),
    "steel_m50": (0.40, 0.42, 0.45), "maraging_c250": (0.45, 0.45, 0.50), "aisi9310": (0.42, 0.44, 0.46),
    "ss321": (0.65, 0.65, 0.62), "al_2219": (0.80, 0.82, 0.85), "al_c355": (0.78, 0.80, 0.82),
    "mg_ze41": (0.72, 0.74, 0.70), "composite_cfrp": (0.20, 0.20, 0.22),
}

_GAS = NasaGas()


def v(q):
    return q["value"] if isinstance(q, dict) else q


# --- sizing -----------------------------------------------------------------------------------------------

def gas_props(T: float, f: float = 0.0) -> tuple[float, float]:
    """(gamma, R) at static-ish temperature T and FAR f [G, NASA polynomials]."""
    return _GAS.gamma(T, f), _GAS.R(f)


def mass_flux_function(M: float, gamma: float) -> float:
    g = gamma
    return math.sqrt(g) * M * (1 + (g - 1) / 2 * M * M) ** (-(g + 1) / (2 * (g - 1)))


def static_T(Tt: float, M: float, gamma: float) -> float:
    return Tt / (1 + (gamma - 1) / 2 * M * M)


def area_for(W: float, Tt: float, Pt_kpa: float, M: float, f: float = 0.0) -> float:
    """Annulus area [m2] carrying W [kg/s] at total state (Tt [K], Pt [kPa]) and axial Mach M [G]."""
    g, R = gas_props(Tt, f)
    g, R = gas_props(static_T(Tt, M, g), f)
    return W * math.sqrt(R * Tt) / (Pt_kpa * 1e3 * mass_flux_function(M, g))


def area_swirl(W: float, Tt: float, Pt_kpa: float, Vx: float, Vt: float, f: float = 0.0) -> float:
    """Annulus area [m2] for W at total state (Tt, Pt) with axial and tangential velocities Vx, Vt [m/s]: static
    state from the absolute velocity, isentropic with gamma at the static temperature [G]."""
    cp = _GAS.cp(Tt, f)
    T = Tt - (Vx * Vx + Vt * Vt) / (2 * cp)
    g, R = gas_props(T, f)
    P = Pt_kpa * 1e3 * (T / Tt) ** (g / (g - 1))
    return W / (P / (R * T) * Vx)


def axial_velocity(Tt: float, M: float, f: float = 0.0) -> float:
    g, R = gas_props(Tt, f)
    return M * math.sqrt(g * R * static_T(Tt, M, g))


def radii_mean(A: float, r_mean: float) -> tuple[float, float]:
    h = A / (2 * math.pi * r_mean)
    return r_mean - h / 2, r_mean + h / 2


def radii_tip(A: float, r_tip: float) -> tuple[float, float]:
    return math.sqrt(r_tip ** 2 - A / math.pi), r_tip


def radii_hub(A: float, r_hub: float) -> tuple[float, float]:
    return r_hub, math.sqrt(r_hub ** 2 + A / math.pi)


def annulus_area(r_hub: float, r_tip: float) -> float:
    return math.pi * (r_tip ** 2 - r_hub ** 2)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def r6(x: float) -> float:
    return round(float(x), 6)


def stage_triangles(psi: float, phi: float, reaction: float) -> dict:
    """Mean-line repeating-stage velocity components over U (positive in the direction of rotation) from the
    loading psi = dh0/U^2, flow coefficient phi = Vx/U and reaction R [G]: Vt1/U = 1 - R - psi/2,
    Vt2/U = 1 - R + psi/2 (compressor, psi > 0; a turbine passes psi < 0 with Vt in = 1 - R - psi/2)."""
    return {"vt1": 1 - reaction - psi / 2, "vt2": 1 - reaction + psi / 2, "phi": phi}


def free_vortex_sections(radii: dict[str, float], r_mean: float, U_mean: float, Vx: float, vt_in_m: float,
                         vt_out_m: float, rotor: bool, chord: float, tc: dict[str, float], solidity_mean: float,
                         carter_m: float) -> list[dict]:
    """Hub/mean/tip sections with metal angles [deg, positive towards +Y; the rotor moves towards -Y at +Z,
    R-G1/R-G2.1] from free-vortex flow angles (Vt ~ 1/r, U ~ r, Vx constant) [G] and a Carter-type deviation
    m / sqrt(solidity) on the flow turning, zero incidence [G]. vt_*_m: absolute tangential velocity at the mean
    radius, positive in the direction of rotation [m/s]."""
    out = []
    names = ("hub", "mean", "tip")
    for i, name in enumerate(names):
        r = radii[name]
        U = U_mean * r / r_mean if rotor else 0.0
        a_in = math.degrees(math.atan((U - vt_in_m * r_mean / r) / Vx))
        a_out = math.degrees(math.atan((U - vt_out_m * r_mean / r) / Vx))
        sigma = solidity_mean * r_mean / r
        d = carter_m / math.sqrt(sigma)
        theta = (a_in - a_out) / (1 - d)
        out.append({"f": i / 2, "name": name, "r": r, "c": chord, "k1": a_in, "k2": a_in - theta,
                    "flow_in": a_in, "flow_out": a_out, "tc": tc[name], "solidity": sigma})
    return out


def axial_width(sections: list[dict]) -> float:
    """Largest axial extent of the section airfoils (blade() aligns every section's leading point to x_le)."""
    out = 0.0
    for s in sections:
        xs = [q[0] for q in section(s["c"], s["k1"], s["k2"], s["tc"])]
        out = max(out, max(xs) - min(xs))
    return out


# --- solids -----------------------------------------------------------------------------------------------

def revolve(points: list[tuple[float, float]]) -> cq.Solid:
    """Solid of revolution about X of a closed (x, r) polygon (r >= 0)."""
    wp = cq.Workplane("XZ").polyline([(float(x), float(r)) for x, r in points]).close()
    return wp.revolve(360.0, (0, 0, 0), (1, 0, 0)).val()


def ring(x0: float, x1: float, r_in: float, r_out: float) -> cq.Solid:
    return revolve([(x0, r_in), (x1, r_in), (x1, r_out), (x0, r_out)])


def shell(curve: list[tuple[float, float]], t: float, outward: bool = True) -> cq.Solid:
    """Revolved wall of radial thickness t on one side of a meridional (x, r) curve."""
    off = [(x, r + (t if outward else -t)) for x, r in curve]
    return revolve(list(curve) + off[::-1])


def between(inner: list[tuple[float, float]], outer: list[tuple[float, float]]) -> cq.Solid:
    """Revolved solid between two meridional curves with the same end x values."""
    return revolve(list(outer) + list(inner)[::-1])


def disk(x_mid: float, r_bore_in: float, r_bore_out: float, w_bore: float, t_web: float, r_rim_in: float,
         r_rim_out: float, w_rim: float) -> cq.Solid:
    """Revolved rim / web / bore disk, symmetric about x_mid."""
    hb, hw, hr = w_bore / 2, t_web / 2, w_rim / 2
    pts = [(x_mid - hb, r_bore_in), (x_mid + hb, r_bore_in), (x_mid + hb, r_bore_out), (x_mid + hw, r_bore_out),
           (x_mid + hw, r_rim_in), (x_mid + hr, r_rim_in), (x_mid + hr, r_rim_out), (x_mid - hr, r_rim_out),
           (x_mid - hr, r_rim_in), (x_mid - hw, r_rim_in), (x_mid - hw, r_bore_out), (x_mid - hb, r_bore_out)]
    return revolve(pts)


def cone(x0: float, r0: float, x1: float, r1: float, t: float) -> cq.Solid:
    """Conical (or cylindrical) wall of radial thickness t from (x0, r0) to (x1, r1), r = inner radius."""
    return revolve([(x0, r0), (x1, r1), (x1, r1 + t), (x0, r0 + t)])


def section(c: float, k1: float, k2: float, tc: float, n: int = 16, te_c: float = 0.01) -> list[tuple[float, float]]:
    """Closed airfoil (axial, tangential) points: camber line angle linear from k1 to k2 [deg from axial,
    positive towards +Y] (circular-arc camber for constant curvature) [G], thickness tc*c, parabolic
    distribution with a small trailing-edge thickness. Leading edge at axial 0, centred tangentially."""
    s = [0.5 * (1 - math.cos(math.pi * i / (n - 1))) for i in range(n)]
    xs, ys = [0.0], [0.0]
    for a, b in zip(s, s[1:]):
        ang = math.radians(k1 + (k2 - k1) * 0.5 * (a + b))
        xs.append(xs[-1] + (b - a) * c * math.cos(ang))
        ys.append(ys[-1] + (b - a) * c * math.sin(ang))
    up, lo = [], []
    for i, si in enumerate(s):
        ang = math.radians(k1 + (k2 - k1) * si)
        t = max(4 * si * (1 - si) * tc * c, te_c * c) / 2
        nx, ny = -math.sin(ang), math.cos(ang)
        up.append((xs[i] + nx * t, ys[i] + ny * t))
        lo.append((xs[i] - nx * t, ys[i] - ny * t))
    ym = 0.5 * (min(ys) + max(ys))
    pts = up + lo[::-1][1:-1]
    return [(px, py - ym) for px, py in pts]


def blade(x_le: float, r_hub: float, r_tip: float, sections: list[dict]) -> cq.Solid:
    """Blade lofted through sections [{"f": span fraction, "c", "k1", "k2", "tc"}] from r_hub to r_tip; each
    section is a planar airfoil at radius r (Z), axial along X from x_le (axial width centred on the hub
    section's width), tangential along Y; the tip section is lowered so that no point lies outside r_tip."""
    wires = []
    for sec in sections:
        r = lerp(r_hub, r_tip, sec["f"])
        pts = section(sec["c"], sec["k1"], sec["k2"], sec["tc"])
        if sec["f"] >= 1.0:  # planar tip section: keep its tangential corners inside the radius r_tip
            r = math.sqrt(r * r - max(py * py for _, py in pts))
        xmin, xmax = min(p[0] for p in pts), max(p[0] for p in pts)
        x0 = x_le + sec.get("dx", 0.0) - xmin
        wires.append(cq.Wire.makePolygon([cq.Vector(x0 + px, py, r) for px, py in pts], close=True))
    return cq.Solid.makeLoft(wires, True)


def box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> cq.Solid:
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def cylinder_x(x0: float, x1: float, r: float, y: float = 0.0, z: float = 0.0) -> cq.Solid:
    return cq.Solid.makeCylinder(r, x1 - x0, cq.Vector(x0, y, z), AXIS_X)


def tube(points: list[tuple[float, float, float]], r_out: float, t: float) -> cq.Shape:
    """Pipe of outer radius r_out and wall t along a polyline of 3D points (straight segments joined)."""
    solids = []
    for a, b in zip(points, points[1:]):
        va, vb = cq.Vector(*a), cq.Vector(*b)
        d = vb - va
        L = d.Length
        outer = cq.Solid.makeCylinder(r_out, L, va, d.normalized())
        inner = cq.Solid.makeCylinder(r_out - t, L, va, d.normalized())
        solids.append(outer.cut(inner))
        solids.append(cq.Solid.makeSphere(r_out, vb).cut(cq.Solid.makeSphere(r_out - t, vb)))
    out = solids[0]
    for s in solids[1:-1]:
        out = out.fuse(s)
    return out.clean()


def rotate_x(s: cq.Shape, deg: float) -> cq.Shape:
    return s.rotate(AXIS_O, AXIS_X, deg)


def common_volume(a: cq.Shape, b: cq.Shape) -> float:
    try:
        return a.intersect(b).Volume()
    except Exception:  # noqa: BLE001 - OCC boolean failure is reported as unknown
        return float("nan")


# --- module output ----------------------------------------------------------------------------------------

@dataclass
class Part:
    pid: str
    name: str
    shape: cq.Shape
    material: str
    function: str
    count: int = 1
    count_tag: str = "G"
    process: str = ""
    notes: str = ""
    joints: list = field(default_factory=list)
    phase_deg: float = 0.0
    patterned: bool = True  # False: the shape already holds every instance (count is the BOM qty only)

    @property
    def unit_mass(self) -> float:
        return self.shape.Volume() * DENSITY[self.material]


@dataclass
class Module:
    module_id: str
    module_name: str
    revision: str
    parts: list[Part] = field(default_factory=list)

    @property
    def folder(self) -> Path:
        return module_dir(self.module_id)

    def add(self, part: Part) -> Part:
        self.parts.append(part)
        return part

    def part(self, pid: str) -> Part:
        return next(p for p in self.parts if p.pid == pid)

    def mass(self) -> float:
        return sum(p.unit_mass * p.count for p in self.parts)

    def bom(self, script: str) -> dict:
        out = []
        for p in sorted(self.parts, key=lambda q: [int(n) for n in q.pid.split(".")[1:]]):
            m = p.unit_mass
            entry = {
                "id": p.pid, "name": p.name, "parent": None,
                "qty": {"value": int(p.count), "unit": "ea", "tag": p.count_tag},
                "function": p.function, "material": p.material, "status": "draft",
                "mass": {"value": round(m, 4), "unit": "kg", "tag": "H"},
                "geometry": {"script": script, "params": {"revision": self.revision}},
                "notes": (f"Unit mass {m:.4f} kg [H] = solid volume x density ({p.material} "
                          f"{DENSITY[p.material]:.0f} kg/m3 [G]); information only. " + p.notes).strip(),
            }
            if p.process:
                entry["process"] = p.process
            if p.joints:
                entry["joints"] = [{"to": t, "type": k} for t, k in p.joints]
            out.append(entry)
        return {"module_id": self.module_id, "module_name": self.module_name, "revision": self.revision,
                "parts": out}

    def write_bom(self, script: str) -> list[str]:
        """Writes bom/bom.yaml through core.bom.write; keeps the recorded revision id of the file."""
        path = self.folder / "bom" / "bom.yaml"
        data = self.bom(script)
        if path.exists():
            data["revision"] = core_bom.load(path).get("revision", data["revision"])
        report = core_bom.check_data(data)
        if report.errors:
            raise ValueError("; ".join(report.errors))
        core_bom.write(path, data)
        return report.warnings

    def step_dir(self) -> Path:
        d = ROOT / ".cache" / "geometry" / self.folder.name / self.revision
        d.mkdir(parents=True, exist_ok=True)
        return d

    def assembly(self) -> cq.Assembly:
        assy = cq.Assembly(name=f"{self.module_id.lower()}_assembly")
        for p in self.parts:
            col = cq.Color(*COLOR.get(p.material, (0.6, 0.6, 0.6)))
            for i in range(p.count if p.patterned else 1):
                ang = p.phase_deg + 360.0 * i / p.count
                assy.add(p.shape, name=f"{p.pid.replace('.', '_')}_{i}",
                         loc=cq.Location(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), ang), color=col)
        return assy

    def export(self) -> dict[str, Path]:
        d = self.step_dir()
        paths = {}
        for p in self.parts:
            path = d / f"{p.pid.replace('.', '_')}_{p.name.split()[-1].lower()}.step"
            cq.exporters.export(cq.Workplane().add(p.shape), str(path), exportType="STEP")
            paths[p.pid] = path
        path = d / f"{self.module_id.lower()}_assembly.step"
        self.assembly().export(str(path), exportType="STEP")
        paths["assembly"] = path
        return paths


def write_interface(module: str, data: dict) -> Path:
    path = module_dir(module) / "geometry" / "flowpath.yaml"
    write_yaml(path, data)
    return path


def read_interface(module: str) -> dict:
    return read_yaml(module_dir(module) / "geometry" / "flowpath.yaml")
