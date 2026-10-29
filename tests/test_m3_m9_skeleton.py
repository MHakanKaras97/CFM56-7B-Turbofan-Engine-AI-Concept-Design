"""M3-M9 skeleton: agent definitions, write scope, rule book index, known values, source index."""

import re
from pathlib import Path

import pytest
import yaml

from core.scope import write_allowed

ROOT = Path(__file__).resolve().parents[1]
MODULES = {"M3": ("M3_hp_compressor", "m3-hp-compressor"), "M4": ("M4_combustor", "m4-combustor"),
           "M5": ("M5_hp_turbine", "m5-hp-turbine"), "M6": ("M6_lp_turbine", "m6-lp-turbine"),
           "M7": ("M7_nozzle", "m7-nozzle"), "M8": ("M8_shaft_bearing", "m8-shaft-bearing"),
           "M9": ("M9_secondary_air_oil", "m9-secondary-air-oil")}
KNOWN = {"M3": ["| 38 |", "| 53 |", "| 60 |", "| 68 |", "| 75 |", "| 82 |", "| 80 |", "| 76 |", "stages 1-3"],
         "M4": ["| 20 |"], "M5": ["| 80 |", "| 17,300 |", "| 19,200 |", "ISSUE39"],
         "M6": ["| 162 |", "| 150 |", "| 134 |", "| 23,900 |", "| 16,300 |", "ISSUE39"],
         "M7": ["bypass duct 13-18", "turbine frames", "fan nozzle"], "M8": ["| 30,000 |", "| 22,900 |"],
         "M9": ["gearbox", "oil"]}


@pytest.mark.parametrize("module", MODULES)
def test_agent_definition(module):
    folder, agent = MODULES[module]
    text = (ROOT / ".claude" / "agents" / f"{agent}.md").read_text(encoding="utf-8")
    front = yaml.safe_load(text.split("---")[1])
    assert front["name"] == agent and front["description"]
    assert "Agent" not in [t.strip() for t in front["tools"].split(",")]
    assert f"Write only under `engine/{folder}/`" in text
    assert f'read_icd("{module} agent")' in text


@pytest.mark.parametrize("module", MODULES)
def test_scope_hook_covers_module(module):
    folder, agent = MODULES[module]
    assert write_allowed(agent, str(ROOT / "engine" / folder / "rules" / "x.md"))[0]
    assert not write_allowed(agent, str(ROOT / "engine" / "M1_inlet_fan" / "rules" / "x.md"))[0]


@pytest.mark.parametrize("module", MODULES)
def test_rule_book_and_sources(module):
    mdir = ROOT / "engine" / MODULES[module][0]
    assert "`known_values.md`" in (mdir / "rules" / "index.md").read_text(encoding="utf-8")
    assert (mdir / "learning" / "sources" / "INDEX.md").is_file()
    known = (mdir / "rules" / "known_values.md").read_text(encoding="utf-8")
    for item in KNOWN[module]:
        assert item in known, (module, item)
    for row in re.findall(r"^\| .+ \| [\d,]+ \| \[(\w+)\] \| (.+) \|$", known, re.M):
        assert row[0] == "KS" and "#" in row[1], (module, row)  # every source value is [KS] with a source number


def test_stator_and_ngv_counts_are_rules_only():
    for module in ("M3", "M5", "M6"):
        known = (ROOT / "engine" / MODULES[module][0] / "rules" / "known_values.md").read_text(encoding="utf-8")
        section = known.split("vane counts" if module == "M3" else "NGV counts")[1].split("##")[0]
        assert "[T]" in section and not re.search(r"\|\s*\d+\s*\|", section), module


def test_rejected_source_not_used():
    for folder, _ in MODULES.values():
        for path in (ROOT / "engine" / folder).rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            assert "CFM56_Answers" not in text or "rejected" in text, path
