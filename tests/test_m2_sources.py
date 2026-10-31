"""M2 step 1: source index, TP-1523 table checks, definitions, applicability, rule book skeleton, agent."""

import math
import warnings
from pathlib import Path

import pytest
import yaml

from core.bom import load as load_bom
from core.budgets import read_icd
from core.records import active_revision, design_drift, read_revision, reproduce, verify
from tools.meanline import diffusion_factor

ROOT = Path(__file__).resolve().parents[1]
M2 = ROOT / "engine" / "M2_booster"
TAGS = {"K", "KS", "H", "G", "T"}
GAMMA, R_AIR = 1.4, 287.05  # [G] cold air
RIG_TIP_CM, RIG_HUB_CM = 25.4, 20.32
SOURCE_FILES = ["britsch_1979_tp1523.md", "lieblein_1953_rme53d01.md", "lolis_thesis_cranfield.md",
                "oog_issue58_cfm56_7b_guide.txt", "oog_issue58_cfm56_7b_mtce.md", "ge_e3_cr168211.md",
                "davis_stearns_1985_cr168219.md"]
RULE_FILES = ["index.md", "bom.md", "budget.md", "aero_method.md", "materials.md", "joints.md", "analyses.md",
              "failure_modes.md", "open_items.md"]


def read(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


REF = read(M2 / "learning" / "tp1523_reference.yaml")


def quantities(node, path=""):
    if isinstance(node, dict):
        if "value" in node:
            yield path, node
        for key, child in node.items():
            yield from quantities(child, f"{path}.{key}")
    elif isinstance(node, list):
        for i, child in enumerate(node):
            yield from quantities(child, f"{path}[{i}]")


def table(name: str) -> list[dict]:
    t = REF[name]
    return [dict(zip(t["columns"], row)) for row in t["rows"]]


def solidity(chord: float, blades: int, r_le: float, r_te: float) -> float:
    return chord * blades / (2 * math.pi * (r_le + r_te) / 2)


def mass_flow_parameter(mach: float) -> float:
    return math.sqrt(GAMMA / R_AIR) * mach * (1 + (GAMMA - 1) / 2 * mach ** 2) ** (-(GAMMA + 1) / (2 * (GAMMA - 1)))


def subsonic_mach(flow_function: float) -> float:
    lo, hi = 1e-4, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if mass_flow_parameter(mid) < flow_function else (lo, mid)
    return (lo + hi) / 2


def test_source_index_complete():
    index = (M2 / "learning" / "sources" / "INDEX.md").read_text(encoding="utf-8")
    for name in SOURCE_FILES:
        assert name in index, name
    assert "girao_2023_cfm56-7b_thesis" in index  # referenced in the M0 archive, not copied
    assert not [p.name for p in (M2 / "learning" / "sources").iterdir() if p.name != "INDEX.md"]
    sources = (ROOT / "docs" / "sources.md").read_text(encoding="utf-8")
    for name in SOURCE_FILES:
        assert name in sources, name


def test_reference_tags_valid():
    found = list(quantities(REF))
    assert len(found) > 15
    for path, q in found:
        if "repairs" in path:
            continue
        assert q.get("tag") in TAGS, path
        assert "unit" in q, path
    for name in ("table1", "blade_tables", "df_check"):
        assert REF[name]["tag"] in TAGS
    for name in ("table1", "blade_tables", "df_check"):
        for rep in REF[name].get("repairs", []) + REF[name].get("other_repairs", []):
            assert rep["tag"] in TAGS, rep["cell"]


def test_rig_geometry_consistent():
    rig = REF["rig"]
    assert RIG_HUB_CM / RIG_TIP_CM == pytest.approx(rig["hub_tip_ratio"]["value"], abs=1e-9)
    assert 2 * RIG_TIP_CM == rig["tip_diameter"]["value"]
    u_tip = rig["design_rpm_23B"]["value"] * 2 * math.pi / 60 * RIG_TIP_CM / 100
    assert u_tip == pytest.approx(rig["design_tip_speed"]["value"], rel=0.002)


def test_table1_aspect_ratio_and_tip_solidity():
    span = RIG_TIP_CM - RIG_HUB_CM
    for row in table("table1"):
        for side in ("rotor", "stator"):
            chord, blades = row[f"{side}_chord_cm"], row[f"{side}_blades"]
            assert span / chord == pytest.approx(row[f"{side}_ar"], abs=0.011), (row["stage"], side)
            sigma_tip = solidity(chord, blades, RIG_TIP_CM, RIG_TIP_CM)
            assert sigma_tip == pytest.approx(row[f"{side}_solidity"], rel=0.03), (row["stage"], side)


def test_blade_tables_solidity_on_mean_edge_radius():
    rows = table("blade_tables")
    checked = [r for r in rows if r["status"] != "unresolved"]
    for r in checked:
        sigma = solidity(r["chord_cm"], r["blades"], r["r_le_cm"], r["r_te_cm"])
        assert sigma == pytest.approx(r["solidity"], rel=0.002), (r["row"], r["station"])
    # stator 22 mid span discriminates the radius: the LE radius alone misses by more than 0.3 %
    s22 = next(r for r in rows if r["row"] == "stator 22" and r["station"] == "mid")
    le_only = solidity(s22["chord_cm"], s22["blades"], s22["r_le_cm"], s22["r_le_cm"])
    assert abs(le_only / s22["solidity"] - 1) > 0.003
    counts = {s: sum(r["status"] == s for r in rows) for s in ("trusted", "repaired", "unresolved")}
    assert counts == {"trusted": 21, "repaired": 7, "unresolved": 2}


def test_diffusion_factor_reproduces_table2():
    for r in table("df_check"):
        wt1, wt2 = r["U1"] - r["Vt1"], r["U2"] - r["Vt2"]
        df = diffusion_factor(r["W1"], r["W2"], r["r1_cm"], r["r2_cm"], wt1, wt2, r["solidity"])
        assert df == pytest.approx(r["df_table"], abs=0.002), r["station"]


def test_head_rise_and_flow_coefficients_reproduce_table2():
    c = {k: v["value"] for k, v in REF["coefficient_check"].items() if isinstance(v, dict)}
    cp, u2 = 1004.0, c["tip_speed"] ** 2  # cp as in the TP-1523 symbol list
    for pr, psi in ((c["rotor_pressure_ratio"], c["rotor_head_rise_coefficient"]),
                    (c["stage_pressure_ratio"], c["stage_head_rise_coefficient"])):
        head = cp * c["inlet_total_temperature"] * (pr ** ((GAMMA - 1) / GAMMA) - 1)
        assert head / u2 == pytest.approx(psi, abs=0.001)
    assert c["inlet_axial_velocity_tip"] / c["tip_speed"] == pytest.approx(c["flow_coefficient"], abs=0.001)


def test_applicability_numbers():
    app = REF["applicability"]
    icd = read_icd("M2 step 1 test")
    s21 = read(ROOT / "engine" / "M1_inlet_fan" / "geometry" / "flowpath.yaml")["interfaces"]["M2_station_21"]
    st21, st24 = icd["stations"]["21"], icd["stations"]["24"]
    pr = icd["modules"]["M2"]["budget"]["pr_booster"]["value"]
    n1 = icd["shafts"]["LP"]["speed_refs"]["girao_nominal"]["value"]
    omega = n1 * 2 * math.pi / 60
    r_hub, r_tip = s21["r_hub_m"], s21["r_tip_m"]
    w, tt, pt = st21["W"]["value"], st21["Tt"]["value"], st21["Pt"]["value"] * 1e3
    assert r_hub / r_tip == pytest.approx(app["station21_hub_tip"]["value"], abs=5e-5)
    assert omega * r_tip == pytest.approx(app["station21_tip_speed"]["value"], abs=0.01)
    assert omega * r_tip / REF["rig"]["design_tip_speed"]["value"] - 1 == pytest.approx(
        app["station21_tip_speed_vs_rig"]["value"], abs=5e-5)
    mach = subsonic_mach(w * math.sqrt(tt) / (pt * s21["area_m2"]))
    assert mach == pytest.approx(app["station21_mach"]["value"], abs=5e-5)
    t_static = tt / (1 + (GAMMA - 1) / 2 * mach ** 2)
    a = math.sqrt(GAMMA * R_AIR * t_static)
    m_rel = math.hypot(mach * a, omega * r_tip) / a
    assert m_rel == pytest.approx(app["station21_tip_relative_mach"]["value"], abs=5e-4)
    assert m_rel < 1.0  # subsonic like the rig

    def exit_hub_tip(mach_axial):
        out = []
        for k in (1, 2, 3):
            pt_k, tt_k = pt * pr ** (k / 3), tt + (st24["Tt"]["value"] - tt) * k / 3
            area = w * math.sqrt(tt_k) / (pt_k * mass_flow_parameter(mach_axial))
            out.append(math.sqrt(r_hub ** 2 + area / math.pi))
        return out

    r_exit = exit_hub_tip(mach)
    assert [round(r_hub / r, 4) for r in r_exit] == app["stage_exit_hub_tip"]["value"]
    assert [round(omega * r, 1) for r in r_exit] == app["stage_exit_tip_speed"]["value"]
    assert round(r_hub / exit_hub_tip(0.5)[-1], 4) == app["lolis_mach_0p5_exit_hub_tip"]["value"]
    assert pt * pr == pytest.approx(st24["Pt"]["value"] * 1e3, rel=1e-4)


def test_definitions_present():
    text = (M2 / "rules" / "aero_method.md").read_text(encoding="utf-8")
    for heading in ("### Solidity", "### Diffusion factor", "### Flow coefficient", "### Loading coefficient",
                    "### Aspect ratio", "### Hub/tip ratio"):
        assert heading in text, heading
    assert "doğrulanamadı" in text  # TP-1523 eq. B4 not readable from the text


def test_rule_book_skeleton():
    index = (M2 / "rules" / "index.md").read_text(encoding="utf-8")
    for name in RULE_FILES:
        assert (M2 / "rules" / name).is_file(), name
        if name != "index.md":
            assert f"`{name}`" in index, name
    lesson = (M2 / "learning" / "ders02_booster.md").read_text(encoding="utf-8")
    for name in ("TP-1523", "RM E53D01", "Girão", "Owner", "Lolis", "CS-E"):
        assert name in lesson, name


def test_m2_bom_parts_from_geometry():
    """Geometry step 4 (R-G2.24): drum, case, per stage rotor blade / stator vane / inner shroud; no liners (#84)."""
    from core.bom import validate
    path = M2 / "bom" / "bom.yaml"
    assert validate(path) == []
    bom = load_bom(path)
    res = read_revision("M2", "rev001", "results.yaml")
    n = len(res["stages"])
    parts = {p["id"]: p for p in bom["parts"]}
    assert list(parts) == ["M2.0.1", "M2.0.2"] + [f"M2.{s}.{k}" for s in range(1, n + 1) for k in (1, 2, 4)]
    val = lambda x: x["value"] if isinstance(x, dict) else x
    for s, st in enumerate(res["stages"], 1):
        assert parts[f"M2.{s}.1"]["qty"]["value"] == int(val(st["rotor_blades"]))
        assert parts[f"M2.{s}.2"]["qty"]["value"] == int(val(st["stator_vanes"]))
    assert bom["module_id"] == "M2" and all(p["mass"]["tag"] == "H" for p in bom["parts"])


def test_m2_active_record_verifies():
    rev = active_revision("M2")
    assert rev is not None
    assert verify("M2", rev) == []
    assert read_revision("M2", rev, "params.yaml") and read_revision("M2", rev, "results.yaml")  # else reproduce is empty
    assert reproduce("M2", rev) == []  # with the record's own code_commit (ADR-013)


def test_m2_design_drift_info():
    """Info only: current code differs from the active record -> new revision needed (ADR-013)."""
    rev = active_revision("M2")
    if rev and (keys := design_drift("M2", rev)):
        warnings.warn(f"M2 {rev}: design drift, new revision needed ({len(keys)} keys: {', '.join(keys[:5])})")


def test_m2_agent_definition():
    text = (ROOT / ".claude" / "agents" / "m2-booster.md").read_text(encoding="utf-8")
    front = yaml.safe_load(text.split("---")[1])
    assert front["name"] == "m2-booster" and front["description"]
    tools = [t.strip() for t in front["tools"].split(",")]
    assert "Agent" not in tools
    assert "engine/M2_booster/" in text
