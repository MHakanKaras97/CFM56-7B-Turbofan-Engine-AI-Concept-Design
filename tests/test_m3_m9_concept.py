"""M3-M9 concept design (docs/m3_m9_plan.md): rule books, interface chain, budgets, source counts, BOM, solids,
intra-module common volume, derived files. One parametrised set per module plus module-specific checks."""

import importlib
import itertools
import math
import re

import pytest

from core import bom as core_bom
from core.budgets import read_icd
from core.records import ROOT, module_dir
from core.util import read_yaml
from tools import concept as C

MODULES = {"M3": ("M3_hp_compressor", "hpc_results.yaml"), "M4": ("M4_combustor", "combustor_results.yaml"),
           "M5": ("M5_hp_turbine", "hpt_results.yaml"), "M6": ("M6_lp_turbine", "lpt_results.yaml"),
           "M7": ("M7_nozzle", "nozzle_results.yaml"), "M8": ("M8_shaft_bearing", "shaft_results.yaml"),
           "M9": ("M9_secondary_air_oil", "air_oil_results.yaml")}
TAG = r"\[(K|KS|H|G|T)"


def design(m):
    return importlib.import_module(f"engine.{MODULES[m][0]}.analysis.design")


def build(m):
    return importlib.import_module(f"engine.{MODULES[m][0]}.geometry.build")


_cache = {}


def res(m):
    if m not in _cache:
        _cache[m] = design(m).run()
    return _cache[m]


def mod(m):
    key = m + "_mod"
    if key not in _cache:
        _cache[key] = build(m).build(res(m))
    return _cache[key]


def known_counts(m, header):
    text = (module_dir(m) / "rules" / "known_values.md").read_text(encoding="utf-8")
    return [int(n) for n in re.findall(rf"^\| {header} stage \d \| (\d+) \|", text, re.M)]


@pytest.mark.parametrize("m", MODULES)
def test_rule_book_written(m):
    """Rules before code: R-D<n>.k lines, numbered from 1, each with a tag."""
    text = (module_dir(m) / "rules" / "design.md").read_text(encoding="utf-8")
    ids = re.findall(rf"^- R-D{m[1]}\.(\d+) ", text, re.M)
    assert ids and [int(i) for i in ids] == list(range(1, len(ids) + 1))
    for line in re.findall(rf"^- R-D{m[1]}\.\d+ .*$", text, re.M):
        assert re.search(TAG, line), line


@pytest.mark.parametrize("m", MODULES)
def test_params_tagged(m):
    folder = module_dir(m) / "analysis"
    params = [p for p in folder.glob("*_params.yaml")]
    assert len(params) == 1
    for key, q in read_yaml(params[0]).items():
        assert isinstance(q, dict) and q.get("tag") in ("K", "KS", "H", "G", "T"), key


@pytest.mark.parametrize("m", MODULES)
def test_derived_files_reproduce(m):
    """results.yaml and geometry/flowpath.yaml are what the code writes (never edited by hand)."""
    d, r = design(m), res(m)
    assert read_yaml(d.OUT_FILE) == read_yaml_roundtrip(d.to_yaml(r))
    assert C.read_interface(m) == read_yaml_roundtrip(d.interface(r))


def read_yaml_roundtrip(data):
    import yaml
    from core.util import dump_yaml
    return yaml.safe_load(dump_yaml(data))


@pytest.mark.parametrize("m", MODULES)
def test_bom_valid_and_from_geometry(m):
    path = module_dir(m) / "bom" / "bom.yaml"
    assert core_bom.validate(path) == []
    bom = core_bom.load(path)
    md = mod(m)
    by_id = {p["id"]: p for p in bom["parts"]}
    assert set(by_id) == {p.pid for p in md.parts}
    for p in md.parts:
        e = by_id[p.pid]
        assert e["qty"]["value"] == p.count and e["material"] == p.material
        assert e["mass"]["value"] == pytest.approx(round(p.unit_mass, 4), abs=1e-4)
        assert e["mass"]["tag"] == "H"
        stage_name = re.match(r"M\d\.(\d+)\.\d+", p.pid).group(1)
        if stage_name != "0" and m in ("M3", "M5", "M6"):
            assert f"Stage {stage_name}" in e["name"], e["name"]


@pytest.mark.parametrize("m", MODULES)
def test_solids_valid_and_no_common_volume(m):
    md = mod(m)
    parts = md.parts
    for p in parts:
        assert p.shape.isValid(), p.pid
        assert p.unit_mass > 0, p.pid
    for a, b in itertools.combinations(parts, 2):
        ba, bb = a.shape.BoundingBox(), b.shape.BoundingBox()
        if ba.xmax < bb.xmin or bb.xmax < ba.xmin:
            continue
        assert C.common_volume(a.shape, b.shape) * 1e9 < 1e-3, (a.pid, b.pid)


@pytest.mark.parametrize("m", MODULES)
def test_step_files_exist(m):
    md = mod(m)
    d = ROOT / ".cache" / "geometry" / MODULES[m][0] / md.revision
    assert (d / f"{m.lower()}_assembly.step").is_file()
    for p in md.parts:
        assert (d / f"{p.pid.replace('.', '_')}_{p.name.split()[-1].lower()}.step").is_file(), p.pid


@pytest.mark.parametrize("m", MODULES)
def test_active_record_verifies(m):
    """rev001 design record (core.records): outputs unchanged, BOM revision = active, params/results = files."""
    from core import records
    rev = records.active_revision(m)
    assert rev == "rev001" and records.verify(m, rev) == []
    assert core_bom.load(module_dir(m) / "bom" / "bom.yaml")["revision"] == rev
    folder = module_dir(m) / "analysis"
    assert records.read_revision(m, rev, "results.yaml") == read_yaml(folder / MODULES[m][1])
    assert records.read_revision(m, rev, "params.yaml") == read_yaml(next(folder.glob("*_params.yaml")))


# --- module-specific ------------------------------------------------------------------------------------

def test_m3_interface_and_budget():
    r = res("M3")
    icd = read_icd("M3 test")
    s25 = C.read_interface("M2")["interfaces"]["M3_station_25"]
    assert r["station_25"]["x"] == float(s25["x_m"]) and r["station_25"]["r_hub"] == float(s25["r_hub_m"])
    st = icd["stations"]
    assert r["budget"]["hpc_pr"] == pytest.approx(st["3"]["Pt"]["value"] / st["25"]["Pt"]["value"], rel=1e-12)
    assert r["station_3"]["Tt"] == pytest.approx(st["3"]["Tt"]["value"], abs=1e-9)
    assert r["station_3"]["W"] == pytest.approx(st["3"]["W"]["value"], abs=1e-9)
    rotors = [x for x in r["rows"] if x["kind"] == "rotor"]
    assert [x["count"] for x in rotors] == known_counts("M3", "HPC") == list(C.v(r["params"]["rotor_blades"]))
    ogv = r["rows"][-1]
    assert ogv["kind"] == "stator" and abs(ogv["sections"][1]["flow_out"]) < 1e-9  # R-D3.4 axial exit
    U1 = r["omega"] * r["r_tip1"]
    assert U1 == pytest.approx(C.v(r["params"]["tip_speed_rotor1"]), rel=1e-12)
    stators = [x for x in r["rows"] if x["kind"] == "stator"]
    for i, s in enumerate(stators):
        assert s["count"] != rotors[i]["count"] and (i + 1 == len(rotors) or s["count"] != rotors[i + 1]["count"])


def test_m4_interface_and_counts():
    r = res("M4")
    s3 = C.read_interface("M3")["interfaces"]["M4_station_3"]
    assert r["station_3"]["x"] == float(s3["x_m"]) and r["station_3"]["r_tip"] == float(s3["r_tip_m"])
    text = (module_dir("M4") / "rules" / "known_values.md").read_text(encoding="utf-8")
    assert int(C.v(r["params"]["injectors"])) == int(re.search(r"twin-tip\) \| (\d+) \|", text).group(1)) == 20
    cs, L = r["casing"], r["liner"]
    assert cs["r_in"] < L["r_in"] < L["r_out"] < cs["r_out"]
    assert L["area"] == pytest.approx(C.v(r["params"]["liner_area_ratio"]) * cs["A_ref"], rel=1e-12)
    st = read_icd("M4 test")["stations"]
    assert r["budget"]["burner_pr"] == pytest.approx(st["4"]["Pt"]["value"] / st["3"]["Pt"]["value"], rel=1e-12)


def test_m5_interface_and_counts():
    r = res("M5")
    s4 = C.read_interface("M4")["interfaces"]["M5_station_4"]
    assert r["station_4"]["x"] == float(s4["x_m"]) and r["r_mean"] == pytest.approx(
        0.5 * (float(s4["r_hub_m"]) + float(s4["r_tip_m"])), abs=1e-12)
    text = (module_dir("M5") / "rules" / "known_values.md").read_text(encoding="utf-8")
    assert r["rotor"]["count"] == int(re.search(r"^\| HPT stage 1 \| (\d+) \|", text, re.M).group(1)) == 80
    assert r["ngv"]["count"] != 80 and 80 % r["ngv"]["count"] != 0
    icd = read_icd("M5 test")
    W41 = icd["stations"]["41"]["W"]["value"]
    assert r["psi"] * r["U"] ** 2 * W41 == pytest.approx(icd["modules"]["M5"]["budget"]["power"]["value"] * 1e6,
                                                          rel=1e-12)


def test_m6_interface_and_counts():
    r = res("M6")
    ds = C.read_interface("M5")["interfaces"]["M6_duct_start"]
    assert r["duct_start"]["x"] == float(ds["x_m"]) and r["duct_start"]["r_tip"] == float(ds["r_tip_m"])
    rotors = [x for x in r["rows"] if x["kind"] == "rotor"]
    assert [x["count"] for x in rotors] == known_counts("M6", "LPT") == [162, 150, 150, 134]
    st = read_icd("M6 test")["stations"]
    assert r["planes"][-1]["Pt"] == pytest.approx(st["5"]["Pt"]["value"], rel=1e-12)
    assert r["planes"][-1]["Tt"] == pytest.approx(st["5"]["Tt"]["value"], abs=1e-9)


def test_m7_nozzle_areas_and_m1_frame():
    r = res("M7")
    budget = read_icd("M7 test")["modules"]["M7"]["budget"]
    b, nz = r["bypass"], r["nozzle"]
    assert C.annulus_area(b["r_in18"], b["r_out18"]) == pytest.approx(budget["A18"]["value"], rel=1e-12)
    assert C.annulus_area(nz["r_plug8"], nz["r_sleeve8"]) == pytest.approx(budget["A8"]["value"], rel=1e-12)
    m1 = r["m1"]
    assert b["inner"][0] == (m1["x_wall_aft"], m1["r_wall_out"]) and b["outer"][0] == (m1["x_outer_aft"],
                                                                                       m1["r_outer_in"])
    s5 = C.read_interface("M6")["interfaces"]["M7_station_5"]
    assert r["trf"]["x0"] == pytest.approx(float(s5["x_rotor_aft_m"]) + C.v(r["params"]["trf_gap"]), abs=1e-12)
    assert r["trf"]["x0"] > float(s5["x_m"]) and r["trf"]["r_tip"] == float(s5["r_tip_m"])


def test_m8_bearings_on_journals_and_torsion():
    r = res("M8")
    assert r["margin_ok"] and all(c["margin"] >= C.v(r["params"]["margin_target"]) for c in r["torsion"].values())
    j3 = C.read_interface("M3")["interfaces"]["M8_bearing_3_journal"]
    j4 = C.read_interface("M5")["interfaces"]["M8_bearing_4_journal"]
    m6 = C.read_interface("M6")["interfaces"]
    b = r["bearings"]
    assert b[3]["r_in"] == float(j3["r_outer_m"]) and b[3]["x0"] == float(j3["x_fwd_m"])
    assert b[4]["r_out"] == float(j4["r_inner_m"]) and b[4]["r_in"] == r["lp_shaft"]["r_out"]
    assert r["lp_shaft"]["x0"] < b[4]["x0"] and b[4]["x1"] < r["lp_shaft"]["x1"]
    assert b[5]["r_in"] == float(m6["M8_bearing_5_journal"]["r_outer_m"])
    assert r["lp_shaft"]["r_out"] == float(m6["M8_lp_coupling"]["r_out_m"]) < r["fan_shaft"]["r_in"]
    icd = read_icd("M8 test")
    T = icd["shafts"]["LP"]["power_lpt"]["value"] * 1e6 / (icd["shafts"]["LP"]["speed_refs"]["girao_nominal"]["value"]
                                                          * 2 * math.pi / 60)
    assert r["torsion"]["lp_shaft"]["torque_Nm"] == pytest.approx(T, rel=1e-12)


def test_m9_bleed_duct_and_externals():
    r = res("M9")
    icd = read_icd("M9 test")
    leak = next(f for f in icd["secondary_air"]["flows"] if f["name"] == "interstage_leak")
    port = C.read_interface("M3")["interfaces"]["M9_bleed_port"]
    A = C.area_for(leak["W"]["value"], leak["T_extraction"]["value"], float(port["Pt_kpa"]),
                   C.v(r["params"]["bleed_duct"])["mach"])
    assert r["bleed"]["area"] == pytest.approx(A, rel=1e-12)
    for key in ("tgb", "agb", "tank"):
        assert r[key]["r0"] > r["ring"]["r_out"]
