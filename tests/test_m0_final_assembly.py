"""M0 final assembly (engine/M0_engine/geometry/final_assembly.py): every module in one STEP, no unknown cross-module
common volume, axial chain of the interfaces M1 -> M7. Slow (builds M1, M2 and M3-M9 models)."""

import pytest

from core.util import read_yaml
from engine.M0_engine.geometry import final_assembly as F
from tools import concept as C


@pytest.fixture(scope="module")
def data():
    return F.collect()


def test_interface_chain_is_continuous():
    """Each module starts where the upstream interface ends (x and radii from the interface files)."""
    s25 = C.read_interface("M2")["interfaces"]["M3_station_25"]
    m3 = C.read_interface("M3")
    assert m3["planes"][0]["x_m"] > float(s25["x_m"])
    s3 = m3["interfaces"]["M4_station_3"]
    s4 = C.read_interface("M4")["interfaces"]["M5_station_4"]
    s44 = C.read_interface("M5")["interfaces"]
    s5 = C.read_interface("M6")["interfaces"]["M7_station_5"]
    s8 = C.read_interface("M7")["interfaces"]["station_8"]
    xs = [float(s25["x_m"]), float(s3["x_m"]), float(s4["x_m"]), float(s44["M6_station_44"]["x_m"]),
          float(s5["x_m"]), float(s8["x_m"])]
    assert xs == sorted(xs)


def test_all_modules_present(data):
    mods = {p["module"] for p in data["parts"]}
    assert mods == {"M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"}
    ids = [p["pid"] for p in data["parts"]]
    assert len(ids) == len(set(ids))


def test_no_unknown_cross_module_common_volume(data):
    rows = F.interference(data)
    unknown = [r for r in rows if not r["known"]]
    assert unknown == [], unknown


def test_step_written():
    rep = read_yaml(F.OUT_DIR / "final_report.yaml")
    path = F.OUT_DIR / F.STEP_NAME
    assert path.is_file() and path.stat().st_size > 1e6
    assert rep["parts"] > 100 and rep["x_extent_m"][0] < 0 < rep["x_extent_m"][1]
    assert [r for r in rep["cross_module_common_volume"] if not r["known"]] == []
