import math
from dataclasses import replace

import pytest

from engine.M0_engine.analysis.cycle import calibrate, load_inputs, run
from tools.thermo import COLD, HOT, Gas, burner, compressor, nozzle, turbine_for_work


@pytest.fixture(scope="module")
def inputs():
    return load_inputs()


@pytest.fixture(scope="module")
def calibrated(inputs):
    p, t, initial, raw, _ = inputs
    r, _ = calibrate(p, t, initial)
    return p, t, r


# --- thermo ----------------------------------------------------------------------

def test_compressor_eff1_is_isentropic():
    Tt, Pt, w = compressor(288.15, 101325.0, 4.0, 1.0, COLD)
    assert Tt == pytest.approx(288.15 * 4.0 ** COLD.k)
    assert Pt == pytest.approx(4 * 101325.0)
    assert w == pytest.approx(COLD.cp * (Tt - 288.15))


def test_turbine_inverts_compressor_at_eff1():
    gas = Gas(1005.0, 1.4)
    Tt_c, Pt_c, w = compressor(300.0, 1e5, 3.0, 1.0, gas)
    Tt_t, Pt_t, pi = turbine_for_work(Tt_c, Pt_c, w, 1.0, gas)
    assert (Tt_t, Pt_t, pi) == pytest.approx((300.0, 1e5, 3.0))


def test_burner_energy_balance():
    f = burner(800.0, 1500.0, 0.995, 43e6)
    assert COLD.cp * 800.0 + 0.995 * f * 43e6 == pytest.approx((1 + f) * HOT.cp * 1500.0)


def test_nozzle_choking():
    gas = COLD
    critical = (2 / (gas.gamma + 1)) ** (-1 / gas.k)
    assert not nozzle(300.0, 0.99 * critical * 1e5, 1e5, 1.0, gas).choked
    n = nozzle(300.0, 1.2 * critical * 1e5, 1e5, 1.0, gas)
    assert n.choked
    T_exit = 300.0 * 2 / (gas.gamma + 1)
    assert n.V == pytest.approx(math.sqrt(2 * gas.cp * (300.0 - T_exit)))
    assert n.F_per_W > n.V  # pressure thrust added


# --- cycle -----------------------------------------------------------------------

def ideal_params(p):
    gas = Gas(1005.0, 1.4)
    return replace(
        p, cold=gas, hot=gas, inlet_recovery=1.0, e_fan=1.0, e_booster=1.0, e_hpc=1.0, e_hpt=1.0, e_lpt=1.0,
        burner_eta=1.0, burner_dp=0.0, bypass_duct_dp=0.0, mech_eff=1.0, nozzle_cv=1.0,
        include_fuel_mass=False, opr=10.0, bpr=5.0, core_pr_25_2=2.0,
    )


def test_ideal_limit_matches_closed_form(inputs):
    p = ideal_params(inputs[0])
    T4, FPR, W2 = 1000.0, 1.5, 300.0
    r = run(p, W2, T4, FPR)
    assert not r["n18"].choked and not r["n8"].choked  # closed form assumes full expansion

    g, cp, T0 = 1.4, 1005.0, p.T0
    k = (g - 1) / g
    tau_lam, tau_c, tau_f, alpha = T4 / T0, p.opr ** k, FPR ** k, p.bpr
    tau_t = 1 - (tau_c - 1 + alpha * (tau_f - 1)) / tau_lam
    a0 = math.sqrt((g - 1) * cp * T0)
    v9 = a0 * math.sqrt(2 / (g - 1) * (tau_lam * tau_t - tau_lam / tau_c))
    v19 = a0 * math.sqrt(2 / (g - 1) * (tau_f - 1))
    specific_thrust = (v9 + alpha * v19) / (1 + alpha)

    assert r["thrust"] / W2 == pytest.approx(specific_thrust, rel=1e-9)


def test_energy_balance_closes(calibrated):
    p, _, r = calibrated
    st = r["stations"]
    comp_work = r["P_fan"] + r["P_boost"] + r["P_hpc"]
    mech_loss = comp_work * (1 / p.mech_eff - 1)
    heat = p.burner_eta * r["W_fuel"] * p.LHV
    inflow = r["W2"] * p.cold.cp * st["2"][0] + heat
    outflow = r["W_byp"] * p.cold.cp * st["18"][0] + r["W_hot"] * p.hot.cp * st["8"][0]
    assert outflow + mech_loss == pytest.approx(inflow, rel=1e-12)


def test_shaft_balance(calibrated):
    p, _, r = calibrated
    assert r["P_hpt"] * p.mech_eff == pytest.approx(r["P_hpc"])
    assert r["P_lpt"] * p.mech_eff == pytest.approx(r["P_fan"] + r["P_boost"])


def test_calibration_hits_targets(calibrated):
    _, t, r = calibrated
    assert r["thrust"] == pytest.approx(t.thrust, rel=1e-3)
    assert r["W_fuel"] == pytest.approx(t.fuel, rel=1e-3)
    assert r["velocity_ratio"] == pytest.approx(r["eta_fan_is"] * r["eta_lpt_is"], rel=1e-3)
