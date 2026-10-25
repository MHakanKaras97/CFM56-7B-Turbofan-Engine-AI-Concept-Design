"""M1 CS-E 800 bird class from the inlet throat area (proxy: ICD fan face area [T])."""

import yaml

from core.util import read_yaml
from engine.M1_inlet_fan.analysis import bird_class


def tables():
    return read_yaml(bird_class.TABLES)


def test_bird_class_file_is_current():
    assert read_yaml(bird_class.OUT) == yaml.safe_load(yaml.safe_dump(bird_class.run(), sort_keys=False))


def test_bands_are_contiguous():
    for name in ("large_single", "large_flocking", "medium_flocking"):
        bands = tables()[name]["bands"]
        assert bands[0]["lower"] == 0.0 and bands[-1]["upper"] is None, name
        assert all(a["upper"] == b["lower"] for a, b in zip(bands, bands[1:])), name


def test_band_edges_follow_cs_e_800():
    t = tables()
    assert bird_class.classify(1.34, t)["large_single"]["birds"] == [{"number": 1, "mass_kg": 1.85}]
    assert bird_class.classify(1.35, t)["large_single"]["birds"] == [{"number": 1, "mass_kg": 2.75}]
    assert bird_class.classify(3.90, t)["large_single"]["birds"] == [{"number": 1, "mass_kg": 3.65}]
    assert not bird_class.classify(2.49, t)["large_flocking"]["applies"]
    assert bird_class.classify(2.50, t)["large_flocking"]["birds"] == [{"number": 1, "mass_kg": 1.85}]
    assert bird_class.classify(1.69, t)["medium_flocking"]["engine_test"][1] == {"number": 3, "mass_kg": 0.70}
    assert bird_class.classify(0.10, t)["small"]["number"] == 4  # 0.10 / 0.032 = 3.1, a fraction counts
    assert bird_class.classify(4.0, t)["core_flocking_bird_kg"] == 1.15


def test_m1_fan_class():
    result = bird_class.run()
    assert result["inlet_throat_area"]["tag"] == "T"
    c = result["class"]
    assert c["large_single"]["birds"] == [{"number": 1, "mass_kg": 2.75}]
    assert not c["large_flocking"]["applies"]
    assert c["medium_flocking"]["engine_test"] == [{"number": 1, "mass_kg": 1.15}, {"number": 4, "mass_kg": 0.70}]
    assert c["small"]["number"] == 16
