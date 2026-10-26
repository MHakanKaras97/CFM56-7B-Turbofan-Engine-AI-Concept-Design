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


def test_radial_equilibrium_uniform_flow_keeps_uniform_velocity():
    """Uniform h0 and s and no swirl (omega = 0, no turning): equilibrium needs a uniform Vm, so each tube's
    exit area is mass / (rho Vm) with the same Vm, whatever the initial split."""
    from dataclasses import replace
    from tools.meanline import area_centre_radii, solve_rotor_re
    base = tube(kappa1=0.0, kappa2=0.0, A1=0.02, A2=0.02)
    tubes = [replace(base, name=f"t{i}", r1=r, r2=r, A2=a) for i, (r, a) in enumerate(((0.15, 0.025), (0.25, 0.015)))]
    sol = solve_rotor_re(tubes, 8.0, 0.0, 288.15, 101325.0, exit_hub=0.1, exit_tip=0.3)
    assert sol.converged
    assert sol.results[0].Vm2 == pytest.approx(sol.results[1].Vm2, rel=1e-3)  # within the area tolerance
    assert sol.tubes[0].A2 == pytest.approx(sol.tubes[1].A2, rel=1e-3)
    assert sum(t.A2 for t in sol.tubes) == pytest.approx(0.04)
    assert area_centre_radii([1.0, 1.0], 0.0, 1.0) == pytest.approx([0.5, math.sqrt(0.75)])


def test_radial_equilibrium_balances_swirl_gradient():
    """Rotor tubes at two radii: the converged exit state satisfies the discrete equilibrium relation."""
    from dataclasses import replace
    from tools.meanline import exit_state, solve_rotor_re
    tubes = [replace(tube(), name="hub", r1=0.15, r2=0.16, A1=0.02, A2=0.017),
             replace(tube(), name="tip", r1=0.25, r2=0.25, A1=0.02, A2=0.017)]
    sol = solve_rotor_re(tubes, 7.0, 1500.0, 288.15, 101325.0, exit_hub=0.12, exit_tip=0.29)
    assert sol.converged
    (h, t), (a, b) = sol.results, [exit_state(r, 288.15, 101325.0) for r in sol.results]
    r_h, r_t = sol.tubes[0].r2, sol.tubes[1].r2
    lhs = (t.Vm2 ** 2 - h.Vm2 ** 2) / 2
    rhs = (b["h0"] - a["h0"]) - (a["T"] + b["T"]) / 2 * (b["s"] - a["s"]) - (h.Vt2 + t.Vt2) / (r_h + r_t) * (r_t * t.Vt2 - r_h * h.Vt2)
    assert lhs == pytest.approx(rhs, rel=1e-3, abs=1.0)


def test_tip_loss_only_in_tip_region_and_breakdown_adds_up():
    from tools.meanline import TIP_REGION_START, Endwall, loss_breakdown, tip_weight
    assert TIP_REGION_START == 0.8 and tip_weight(0.79) == 0.0 and tip_weight(0.9) == pytest.approx(5.0)
    r = solve_tube(tube(endwall=Endwall(0.9, 0.1, 0.05, 0.001)), 3.0, 1700.0, 288.15, 101325.0)
    b = loss_breakdown(r)
    assert all(b[k]["loss"] > 0 for k in ("profile", "shock", "endwall", "tip"))
    assert sum(v["delta_eta"] for v in b.values()) == pytest.approx(1 - r.efficiency)


@pytest.mark.parametrize("mach, recovery", [(1.2, 0.9928), (1.3, 0.9794), (1.4, 0.9582), (1.5, 0.9298)])
def test_normal_shock_recovery_textbook(mach, recovery):
    # gamma 1.4 normal-shock tables (NACA Report 1135) [G]
    assert normal_shock_pt_ratio(mach, GAS) == pytest.approx(recovery, abs=1e-4)


def test_shock_loss_only_when_passage_is_supersonic_and_follows_the_expansion_angle():
    slow = solve_tube(tube(), 3.0, 1000.0, 288.15, 101325.0)
    assert slow.M1rel < 0.8 and slow.loss_shock == 0.0 and slow.M_passage == slow.M1rel
    linear = solve_tube(tube(), 3.0, 1700.0, 288.15, 101325.0)
    flat = solve_tube(tube(ss_turn=0.0), 3.0, 1700.0, 288.15, 101325.0)  # straight suction surface to the shock
    assert linear.M1rel > 1.0 and flat.loss_shock < linear.loss_shock
    assert flat.M_passage >= flat.M1rel  # at most the incidence expansion is left


def test_physical_solution_has_no_issues():
    from dataclasses import replace
    from tools.meanline import solve_rotor_re
    tubes = [replace(tube(), name="hub", r1=0.15, r2=0.16, A1=0.02, A2=0.017),
             replace(tube(), name="tip", r1=0.25, r2=0.25, A1=0.02, A2=0.017)]
    sol = solve_rotor_re(tubes, 7.0, 1500.0, 288.15, 101325.0, exit_hub=0.12, exit_tip=0.29)
    assert sol.physical and sol.issues == []


def test_non_physical_solutions_are_flagged():
    """Unconverged run, collapsed area split and exit choke are each reported."""
    from dataclasses import replace
    from tools.meanline import AREA_SHARE_LIMIT, physical_issues, solve_rotor_re, solve_tube
    tubes = [replace(tube(), name="hub", r1=0.15, r2=0.16, A1=0.02, A2=0.017),
             replace(tube(), name="tip", r1=0.25, r2=0.25, A1=0.02, A2=0.017)]
    sol = solve_rotor_re(tubes, 7.0, 1500.0, 288.15, 101325.0, exit_hub=0.12, exit_tip=0.29, max_iter=2)
    assert not sol.physical and sol.issues[0] == "not converged"
    results = [solve_tube(t, m, 1500.0, 288.15, 101325.0) for t, m in zip(tubes, (4.0, 0.5))]
    share = AREA_SHARE_LIMIT / 9 + 0.05  # tip area share above the limit x its mass share 1/9
    collapsed = [replace(tubes[0], A2=0.034 * (1 - share)), replace(tubes[1], A2=0.034 * share)]
    area = [i for i in physical_issues(collapsed, results, True) if "exit-area share" in i]
    assert len(area) == 1 and area[0].startswith("tube 1:")
    matched = [replace(tubes[0], A2=0.034 * 8 / 9), replace(tubes[1], A2=0.034 / 9)]
    assert not [i for i in physical_issues(matched, results, True) if "exit-area share" in i]
    choked = solve_tube(replace(tubes[0], A2=0.002), 3.5, 1500.0, 288.15, 101325.0)
    assert any(i == "tube 0: exit choked" for i in physical_issues(tubes, [choked, results[1]], True))
