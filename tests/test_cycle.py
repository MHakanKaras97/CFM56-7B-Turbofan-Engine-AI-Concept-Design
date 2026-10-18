import math
from dataclasses import replace

import pytest

from engine.M0_engine.analysis.cycle import (
    calibrate,
    combustor_air_target,
    cooling_sweep,
    load_inputs,
    run,
    thrust_envelope,
)
from tools.thermo import (
    ConstantCp,
    NasaGas,
    burner,
    choke_mass_flux,
    compressor,
    mix,
    nozzle,
    turbine_for_work,
)

GAS = NasaGas()
CONST = ConstantCp(1005.0, 1.4)


@pytest.fixture(scope="module")
def inputs():
    return load_inputs()


@pytest.fixture(scope="module")
def calibrated(inputs):
    """v3 calibration: W2, T4, FPR against thrust, fuel and V18/V8 at the input cooling fraction."""
    p, t, initial, raw, _ = inputs
    r, _ = calibrate(p, t, initial)
    return p, t, r


# --- thermo ----------------------------------------------------------------------

@pytest.mark.parametrize("T, cp", [(300.0, 1005.0), (1000.0, 1142.0)])
def test_air_cp_matches_tables(T, cp):
    assert GAS.cp(T) == pytest.approx(cp, rel=0.01)


@pytest.mark.parametrize("f", [0.0, 0.02, 0.04])
def test_enthalpy_continuous(f):
    # across the 1000 K polynomial break
    eps = 1e-6
    assert GAS.h(1000.0 + eps, f) - GAS.h(1000.0 - eps, f) == pytest.approx(0.0, abs=0.01)
    # dh/dT equals cp on both sides of the break
    for T in (999.0, 1001.0):
        assert (GAS.h(T + 1e-3, f) - GAS.h(T - 1e-3, f)) / 2e-3 == pytest.approx(GAS.cp(T, f), rel=1e-6)
    # zero at the LHV reference temperature for every composition
    assert GAS.h(298.15, f) == pytest.approx(0.0, abs=1e-6)


def test_inverse_functions_roundtrip():
    for T, f in ((250.0, 0.0), (800.0, 0.0), (1600.0, 0.03)):
        assert GAS.T_from_h(GAS.h(T, f), f) == pytest.approx(T, rel=1e-10)
        assert GAS.T_from_phi(GAS.phi(T, f), f) == pytest.approx(T, rel=1e-10)


def test_burner_with_zero_fuel_keeps_temperature():
    assert burner(811.5, 811.5, 0.995, 43e6, GAS) == pytest.approx(0.0, abs=1e-15)


def test_burner_energy_balance():
    f = burner(800.0, 1600.0, 0.995, 43e6, GAS)
    assert 0.0 < f < GAS.f_stoich
    assert GAS.h(800.0) + 0.995 * f * 43e6 == pytest.approx((1 + f) * GAS.h(1600.0, f), rel=1e-12)


def test_mixing_identical_streams_keeps_temperature():
    for T, f in ((811.5, 0.0), (1500.0, 0.025)):
        W, Tm, fm = mix(40.0, T, f, 10.0, T, f, GAS)
        assert (W, Tm, fm) == pytest.approx((50.0, T, f), rel=1e-10)


def test_mixing_air_into_products_conserves_fuel_and_enthalpy():
    W, T, f = mix(40.0, 1600.0, 0.03, 10.0, 800.0, 0.0, GAS)
    assert f == pytest.approx(40.0 * 0.03 / 1.03 / (50.0 - 40.0 * 0.03 / 1.03))
    assert W * GAS.h(T, f) == pytest.approx(40.0 * GAS.h(1600.0, 0.03) + 10.0 * GAS.h(800.0), rel=1e-10)


def test_turbine_inverts_compressor_at_eff1():
    for gas in (GAS, CONST):
        Tt_c, Pt_c, w = compressor(300.0, 1e5, 3.0, 1.0, gas)
        Tt_t, Pt_t, pi = turbine_for_work(Tt_c, Pt_c, w, 1.0, gas)
        assert (Tt_t, Pt_t, pi) == pytest.approx((300.0, 1e5, 3.0))


def test_constant_cp_compressor_is_closed_form():
    Tt, Pt, w = compressor(288.15, 101325.0, 4.0, 0.9, CONST)
    assert Tt == pytest.approx(288.15 * 4.0 ** (0.4 / 1.4 / 0.9))
    assert w == pytest.approx(1005.0 * (Tt - 288.15))


def test_nozzle_choking():
    critical = (2 / 2.4) ** (-1.4 / 0.4)
    assert not nozzle(300.0, 0.99 * critical * 1e5, 1e5, 1.0, CONST).choked
    n = nozzle(300.0, 1.2 * critical * 1e5, 1e5, 1.0, CONST)
    assert n.choked
    assert n.V == pytest.approx(math.sqrt(2 * 1005.0 * (300.0 - 300.0 * 2 / 2.4)))
    assert n.F_per_W > n.V  # pressure thrust added
    # variable cp: choked exit velocity equals the local speed of sound
    n = nozzle(1100.0, 3e5, 1e5, 1.0, GAS, 0.02)
    Ts = GAS.T_from_phi(GAS.phi(1100.0, 0.02) + GAS.R(0.02) * math.log(n.p_exit / 3e5), 0.02)
    assert n.choked
    assert n.V == pytest.approx(math.sqrt(GAS.gamma(Ts, 0.02) * GAS.R(0.02) * Ts), rel=1e-9)


# --- cycle -----------------------------------------------------------------------

def ideal_params(p):
    return replace(
        p, gas=CONST, inlet_recovery=1.0, e_fan=1.0, e_booster=1.0, e_hpc=1.0, e_hpt=1.0, e_lpt=1.0,
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
    st, gas = r["stations"], p.gas
    shaft_load = r["P_fan"] + r["P_boost"] + r["P_hpc"] + p.hp_power_offtake
    mech_loss = shaft_load * (1 / p.mech_eff - 1)
    heat = p.burner_eta * r["W_fuel"] * p.LHV  # fuel enters at the enthalpy reference temperature
    bleed_out = p.customer_bleed * gas.h(st["3"][0])
    inflow = r["W2"] * gas.h(st["2"][0]) + heat
    outflow = r["W_byp"] * gas.h(st["18"][0]) + r["W8"] * gas.h(st["8"][0], st["8"][3])
    assert r["W_cool"] > 0
    assert outflow + mech_loss + p.hp_power_offtake + bleed_out == pytest.approx(inflow, rel=1e-9)


def test_fuel_mass_conserved(calibrated):
    _, _, r = calibrated
    W8, f8 = r["stations"]["8"][2], r["stations"]["8"][3]
    assert W8 * f8 / (1 + f8) == pytest.approx(r["W_fuel"], rel=1e-12)


def test_shaft_balance(calibrated):
    p, _, r = calibrated
    assert r["P_hpt"] * p.mech_eff == pytest.approx(r["P_hpc"] + p.hp_power_offtake)
    assert r["P_lpt"] * p.mech_eff == pytest.approx(r["P_fan"] + r["P_boost"])


def test_calibration_hits_targets(calibrated):
    p, t, r = calibrated
    assert r["thrust"] == pytest.approx(t.thrust, rel=1e-3)
    assert r["W_fuel"] == pytest.approx(t.fuel, rel=1e-3)
    assert r["velocity_ratio"] == pytest.approx(r["eta_fan_is"] * r["eta_lpt_is"], rel=1e-3)
    assert r["cooling_fraction"] == pytest.approx(0.18)  # input, not solved


def test_cooling_flows_and_t41(calibrated):
    p, _, r = calibrated
    assert r["W_comb"] + r["W_cool"] + p.customer_bleed == pytest.approx(r["W_core"])
    assert r["W_ngv"] == pytest.approx(p.ngv_share * r["W_cool"])
    T3 = r["stations"]["3"][0]
    assert T3 < r["T41"] < r["T4"]  # NGV cooling air dilutes the gas before the rotor


def test_combustor_air_comparison_hits_its_target(inputs, calibrated):
    p, t, _, _, _ = inputs
    r = combustor_air_target(p, t, calibrated[2], tol=1e-9)
    assert r["W_comb"] == pytest.approx(t.combustor_air, rel=1e-3)
    assert r["thrust"] == pytest.approx(t.thrust, rel=1e-3)


def test_cooling_sweep_rows(inputs, calibrated):
    p, t, _, raw, refs = inputs
    rows = cooling_sweep(p, t, calibrated[2], raw, refs, tol=1e-9)
    assert [row["cooling_fraction"] for row in rows] == pytest.approx([0.14, 0.16, 0.18, 0.20, 0.22])
    assert rows[2]["W2_kg_s"] == pytest.approx(calibrated[2]["W2"], rel=1e-4)


def test_choke_mass_flux_sls():
    p = load_inputs()[0]
    assert choke_mass_flux(p.T0, p.P0, p.gas) == pytest.approx(241.3, abs=0.1)


def test_envelope_runs_and_matches_its_targets(inputs):
    p, t, initial, raw, _ = inputs
    env = thrust_envelope(p, t, initial, raw, tol=1e-9, c_max=0.04, step=0.02)
    assert [e["cooling_fraction"] for e in env] == [0.0, 0.02, 0.04]
    assert env[0]["W2_kg_s"] == pytest.approx(t.combustor_air * (1 + p.bpr), rel=1e-3)
