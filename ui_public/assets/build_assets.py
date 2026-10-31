"""Render the published UI images (derived, never edited by hand): for the engine and every module M1-M9 an isometric
view, a quarter-cut isometric view and a half-section side view (PNG, VTK off-screen).

Geometry comes from the module code through engine/M0_engine/geometry/final_assembly.collect (read-only). Revolved
and single parts are cut exactly (OCC boolean); patterned instances are kept or dropped by their centroid.

Run from the repo root: python -m ui_public.assets.build_assets [M3 M4 ... engine]
"""

import sys
from pathlib import Path

import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray

from engine.M0_engine.geometry import final_assembly as F
from tools import concept as C

OUT = Path(__file__).resolve().parent / "img"
SIZE = (1600, 900)
TOL, ANG = 0.0008, 0.4  # tessellation tolerance [m] and angular tolerance [rad]
VIEW_DIR = np.array([-0.45, -0.75, 0.5])  # camera direction from the centre (intake towards the viewer, left)
CUT_HALF = C.box(-10, 10, -10, 0, -10, 10)  # removes y < 0 (section viewed from -Y: flow left to right)
CUT_QUARTER = C.box(-10, 10, -10, 0, 0, 10)  # removes y < 0, z > 0


def _mesh(shape):
    v, f = shape.tessellate(TOL, ANG)
    return np.array([[p.x, p.y, p.z] for p in v]), np.array(f, dtype=np.int64)


def _rot(V, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return V @ np.array([[1, 0, 0], [0, c, -s], [0, s, c]]).T


def _actor(V, F_, color):
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(V.astype(np.float64), deep=True))
    cells = np.hstack([np.full((len(F_), 1), 3), F_]).astype(np.int64).ravel()
    ca = vtk.vtkCellArray()
    ca.ImportLegacyFormat(numpy_to_vtkIdTypeArray(cells, deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(ca)
    n = vtk.vtkPolyDataNormals()
    n.SetInputData(pd)
    n.SetFeatureAngle(35)
    n.Update()
    mp = vtk.vtkPolyDataMapper()
    mp.SetInputConnection(n.GetOutputPort())
    a = vtk.vtkActor()
    a.SetMapper(mp)
    a.GetProperty().SetColor(*color)
    a.GetProperty().SetSpecular(0.3)
    a.GetProperty().SetSpecularPower(20)
    return a


def _merge(chunks):
    """One mesh from [(V, F)] chunks."""
    Vs, Fs, off = [], [], 0
    for V, F_ in chunks:
        Vs.append(V)
        Fs.append(F_ + off)
        off += len(V)
    return np.vstack(Vs), np.vstack(Fs)


def scene(parts: list[dict]) -> dict[str, list]:
    """Actors for the full, quarter-cut and half-cut views."""
    out = {"iso": [], "cutaway": [], "section": []}
    for p in parts:
        color = C.COLOR.get(p["material"], (0.62, 0.62, 0.64))
        angs = p["angles"]
        V, F_ = _mesh(p["shape"])
        if len(angs) == 1:
            out["iso"].append(_actor(V, F_, color))
            for key, box in (("cutaway", CUT_QUARTER), ("section", CUT_HALF)):
                s = p["shape"].cut(box)
                if s.Volume() > 1e-12:
                    out[key].append(_actor(*_mesh(s), color))
            continue
        full, quarter, half = [], [], []
        for a in angs:
            Vr = _rot(V, a)
            c = Vr.mean(axis=0)
            full.append((Vr, F_))
            if not (c[1] < 0 and c[2] > 0):
                quarter.append((Vr, F_))
            if c[1] >= 0:
                half.append((Vr, F_))
        for key, chunks in (("iso", full), ("cutaway", quarter), ("section", half)):
            if chunks:
                out[key].append(_actor(*_merge(chunks), color))
    return out


def render(actors: list, path: Path, side: bool) -> None:
    r = vtk.vtkRenderer()
    r.SetBackground(1.0, 1.0, 1.0)
    r.SetBackground2(0.86, 0.90, 0.95)
    r.GradientBackgroundOn()
    for a in actors:
        r.AddActor(a)
    w = vtk.vtkRenderWindow()
    w.SetOffScreenRendering(1)
    w.SetMultiSamples(8)
    w.AddRenderer(r)
    w.SetSize(*SIZE)
    cam = r.GetActiveCamera()
    b = r.ComputeVisiblePropBounds()
    centre = np.array([(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2])
    d = np.array([0.0, -1.0, 0.0]) if side else VIEW_DIR / np.linalg.norm(VIEW_DIR)
    cam.SetFocalPoint(*centre)
    cam.SetPosition(*(centre + 10 * d))
    cam.SetViewUp(0, 0, 1)
    if side:
        cam.ParallelProjectionOn()
    r.ResetCamera()
    cam.Zoom(1.15 if side else 1.3)
    w.Render()
    f = vtk.vtkWindowToImageFilter()
    f.SetInput(w)
    f.Update()
    wr = vtk.vtkPNGWriter()
    wr.SetFileName(str(path))
    wr.SetInputConnection(f.GetOutputPort())
    wr.Write()
    crop(path)


def crop(path: Path, pad: int = 30) -> None:
    """Trim the empty gradient margin (background varies with the row only)."""
    from PIL import Image
    img = np.asarray(Image.open(path).convert("RGB")).astype(int)
    bg = img[:, :1, :]
    mask = np.abs(img - bg).sum(axis=2) > 24
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return
    h, w = mask.shape
    box = (max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, w), min(ys.max() + pad, h))
    Image.open(path).crop(box).save(path, optimize=True)


def main(argv: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    targets = argv or ["engine", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]
    data = F.collect()
    for t in targets:
        parts = data["parts"] if t == "engine" else [p for p in data["parts"] if p["module"] == t]
        sc = scene(parts)
        for view in ("iso", "cutaway", "section"):
            render(sc[view], OUT / f"{t.lower()}_{view}.png", side=(view == "section"))
        print(t, "done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
