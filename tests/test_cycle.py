import math
from dataclasses import replace

import pytest

from engine.M0_engine.analysis.cycle import (
    UNKNOWNS,
    calibrate,
    choke_mass_flux,
    load_inputs,
    run,
    thrust_envelope,
)
from tools.thermo import COLD, HOT, Gas, burner, compressor, h_cold, h_hot, mix, nozzle, turbine_for_work


@pytest.fixture(scope="module")
def inputs():
    return load_inputs()


@pytest.fixture(scope="module")
def calibrated(inputs):
    """Full v2 calibration: W2, T4, FPR, cooling fraction against all four targets."""
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
    assert h_cold(800.0) + 0.995 * f * 43e6 == pytest.approx((1 + f) * h_hot(1500.0, 800.0))


def test_enthalpy_continuous_at_region_boundary():
    T_ref = 838.0
    assert h_hot(T_ref, T_ref) == pytest.approx(h_cold(T_ref))
    # slope changes to hot cp above the boundary, no jump
    assert h_hot(T_ref + 1.0, T_ref) - h_cold(T_ref) == pytest.approx(HOT.cp)


def test_mixing_streams_at_same_temperature_keeps_temperature():
    from engine.M0_engine.analysis.cycle import _mix
    T_ref = 838.0
    W, T = _mix(40.0, T_ref, 10.0, T_ref, T_ref, COLD, HOT)  # cooling air at the boundary temperature
    assert (W, T) == pytest.approx((50.0, T_ref))
    W, T = _mix(40.0, 1500.0, 10.0, 1500.0, 1500.0, COLD, HOT)  # boundary at 1500 K
    assert T == pytest.approx(1500.0)
    W, h = mix(3.0, 1.2e6, 7.0, 1.2e6)
    assert (W, h) == pytest.approx((10.0, 1.2e6))


def test_burner_with_zero_fuel_keeps_temperature():
    assert burner(838.0, 838.0, 0.995, 43e6) == pytest.approx(0.0, abs=1e-15)


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
        include_fuel_mass=False, opr=10.0, bpr=5.0, core_pr_25_2=2.0, hp_power_offtake=0.0, customer_bleed=0.0,
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
    shaft_load = r["P_fan"] + r["P_boost"] + r["P_hpc"] + p.hp_power_offtake
    mech_loss = shaft_load * (1 / p.mech_eff - 1)
    heat = p.burner_eta * r["W_fuel"] * p.LHV
    bleed_out = p.customer_bleed * p.cold.cp * st["3"][0]
    inflow = r["W2"] * p.cold.cp * st["2"][0] + heat
    outflow = r["W_byp"] * h_cold(st["18"][0], p.cold) + r["W8"] * h_hot(st["8"][0], st["3"][0], p.cold, p.hot)
    assert r["W_cool"] > 0
    assert outflow + mech_loss + p.hp_power_offtake + bleed_out == pytest.approx(inflow, rel=1e-12)


def test_shaft_balance(calibrated):
    p, _, r = calibrated
    assert r["P_hpt"] * p.mech_eff == pytest.approx(r["P_hpc"] + p.hp_power_offtake)
    assert r["P_lpt"] * p.mech_eff == pytest.approx(r["P_fan"] + r["P_boost"])


def test_calibration_hits_targets(calibrated):
    _, t, r = calibrated
    assert r["thrust"] == pytest.approx(t.thrust, rel=1e-3)
    assert r["W_fuel"] == pytest.approx(t.fuel, rel=1e-3)
    assert r["velocity_ratio"] == pytest.approx(r["eta_fan_is"] * r["eta_lpt_is"], rel=1e-3)
    assert r["W_comb"] == pytest.approx(t.combustor_air, rel=1e-3)


def test_cooling_flows_and_t41(calibrated):
    p, _, r = calibrated
    assert r["W_comb"] + r["W_cool"] + p.customer_bleed == pytest.approx(r["W_core"])
    assert r["W_ngv"] == pytest.approx(p.ngv_share * r["W_cool"])
    T3 = r["stations"]["3"][0]
    assert T3 < r["T41"] < r["T4"]  # NGV cooling air dilutes the gas before the rotor


def test_choke_mass_flux_sls():
    p = load_inputs()[0]
    assert choke_mass_flux(p.P0, p.T0, p.cold) == pytest.approx(241.3, abs=0.1)


def test_envelope_runs_and_matches_its_targets(inputs):
    p, t, initial, raw, _ = inputs
    env = thrust_envelope(p, t, initial, raw, tol=1e-9, c_max=0.04, step=0.02)
    assert [e["cooling_fraction"] for e in env] == [0.0, 0.02, 0.04]
    assert env[0]["W2_kg_s"] == pytest.approx(t.combustor_air * (1 + p.bpr), rel=1e-3)
