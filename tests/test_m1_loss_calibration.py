"""M1 step 4c: ADR-014 option (a) loss calibration on Rotor 67 (analysis/loss_calibration.py, about 10 min to
re-run, so the test reads the generated file). User rule: every multiplier within 0.5-2, else not applied."""

from core.util import read_yaml
from engine.M1_inlet_fan.analysis import loss_calibration, rotor67


def result():
    return read_yaml(loss_calibration.OUT)


def test_outcome_follows_the_bounds_rule():
    r = result()
    lo, hi = r["bounds"]
    outside = [n for n, v in r["multipliers"].items() if not lo <= v <= hi]
    assert (lo, hi) == loss_calibration.BOUNDS == (0.5, 2.0)
    assert r["outside_bounds"] == outside and r["applied"] == (not outside)


def test_calibration_is_not_applied_and_reported_as_model_form_problem():
    r = result()
    assert set(r["outside_bounds"]) == {"shock", "tip"} and r["applied"] is False  # step 4d, B1 model
    assert "model-form" in r["decision"]
    assert r["fit"]["cost"] < r["fit"]["cost_initial"]
    # the near stall point was not used in the fit and fails on efficiency even with the fitted multipliers
    assert r["near_stall_with_multipliers"]["eta"]["result"] == "fail"


def test_unapplied_multipliers_are_not_used():
    assert rotor67.build_tubes()[0].multipliers == rotor67.LossMultipliers()


def test_calibration_uses_the_full_model():
    assert result()["model"] == rotor67.FULL_MODEL == {"losses": True, "equilibrium": True, "shock_taper": False}
