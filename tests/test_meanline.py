"""tools/meanline.py: gas dynamics relations and the stream-tube solution."""

import math

import pytest

from tools.meanline import (Gas, Tube, carter_deviation, mach_from_flux, mach_from_prandtl_meyer, mass_averaged,
                            mass_flux_function, normal_shock_pt_ratio, prandtl_meyer, solve_tube)

GAS = Gas()


def test_normal_shock_and_prandtl_meyer_textbook_values():
    # gamma 1.4 tables [G]: Pt2/Pt1 = 0.7209 at M 2; nu(2) = 26.38 deg
    assert normal_shock_pt_ratio(2.0, GAS) == pytest.approx(0.7209, abs=1e-4)
    assert normal_shock_pt_ratio(0.9, GAS) == 1.0
    assert math.degrees(prandtl_meyer(2.0, GAS)) == pytest.approx(26.38, abs=0.01)
    assert mach_from_prandtl_meyer(prandtl_meyer(1.7, GAS), GAS) == pytest.approx(1.7, abs=1e-6)


def test_mass_flux_round_trip_and_choke():
    assert mass_flux_function(1.0, GAS) == pytest.approx(0.6847, abs=1e-4)
    assert mach_from_flux(mass_flux_function(0.55, GAS), GAS) == pytest.approx(0.55, abs=1e-9)
    with pytest.raises(ValueError, match="choked"):
        mach_from_flux(0.7, GAS)


def test_carter_deviation():
    # m = 0.23 + kappa2/500 deg; camber 30 deg, solidity 1 -> (0.23 + 0.02) * 30
    assert math.degrees(carter_deviation(math.radians(40), math.radians(10), 1.0)) == pytest.approx(7.5)


def tube(**kw):
    base = dict(name="t", r1=0.2, r2=0.2, A1=0.02, A2=0.017, kappa1=math.radians(55), kappa2=math.radians(40),
                solidity=1.8, covered_fraction=0.4)
    return Tube(**{**base, **kw})


def test_euler_work_and_energy_balance():
    gas = GAS
    r = solve_tube(tube(), 4.0, 1500.0, 288.15, 101325.0, gas)
    U2 = 1500.0 * 0.2
    assert gas.cp * 288.15 * (r.Tt_ratio - 1) == pytest.approx(U2 * r.Vt2, rel=1e-9)
    assert r.Vt2 == pytest.approx(U2 - r.Vm2 * math.tan(r.beta2), rel=1e-9)
    assert 0.5 < r.efficiency < 1.0
    assert r.notes == []


def test_losses_lower_efficiency_and_subsonic_has_no_shock_loss():
    slow = solve_tube(tube(), 3.0, 1000.0, 288.15, 101325.0)
    assert slow.M1rel < 0.8 and slow.loss_shock == 0.0
    fast = solve_tube(tube(), 3.0, 1700.0, 288.15, 101325.0)
    assert fast.M1rel > 1.0 and fast.loss_shock > 0.0


def test_mass_average_of_identical_tubes():
    r = solve_tube(tube(), 4.0, 1500.0, 288.15, 101325.0)
    avg = mass_averaged([r, r])
    assert avg["Pt_ratio"] == pytest.approx(r.Pt_ratio)
    assert avg["efficiency"] == pytest.approx(r.efficiency)


def test_endwall_and_tip_losses_lower_efficiency():
    from tools.meanline import Endwall
    base = solve_tube(tube(), 4.0, 1500.0, 288.15, 101325.0)
    assert base.loss_endwall == 0.0 and base.loss_tip == 0.0  # off without Endwall data
    tip = solve_tube(tube(endwall=Endwall(0.9, 0.1, 0.05, 0.001)), 4.0, 1500.0, 288.15, 101325.0)
    mid = solve_tube(tube(endwall=Endwall(0.5, 0.1, 0.05, 0.001)), 4.0, 1500.0, 288.15, 101325.0)
    assert tip.loss_endwall > 0 and tip.loss_tip > 0 and tip.efficiency < base.efficiency
    assert mid.loss_endwall == 0.0  # parabolic endwall weight vanishes at mid span
    assert mid.loss_tip < tip.loss_tip


def test_loss_weights_average_to_one_over_the_span():
    from tools.meanline import endwall_weight, tip_weight
    n = 10000
    for w in (endwall_weight, tip_weight):
        assert sum(w((i + 0.5) / n) for i in range(n)) / n == pytest.approx(1.0, abs=1e-6)
    assert tip_weight(0.0) == 0.0 and endwall_weight(0.0) == endwall_weight(1.0) == 3.0


def test_howell_endwall_loss_textbook_form():
    from tools.meanline import howell_endwall_loss
    # no turning: C_L = 0, only annulus drag 0.020 s/h; beta1 = beta2 = 0 -> sigma * C_D
    assert howell_endwall_loss(0.0, 0.0, 1.5, 0.05, 0.10) == pytest.approx(1.5 * 0.020 * 0.5)
