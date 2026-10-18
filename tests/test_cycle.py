import math
from dataclasses import replace

import pytest

from engine.M0_engine.analysis.cycle import (
    calibrate,
    first_deviation,
    load_inputs,
    run,
    thrust_envelope,
    validation_case,
    validation_rows,
)
from tools.thermo import (
    ConstantCp,
    NasaGas,
    burner,
    choke_mass_flux,
    compressor,
    compressor_is,
    mix,
    nozzle,
    turbine_for_work,
    turbine_is_for_work,
)

GAS = NasaGas()
CONST = ConstantCp(1005.0, 1.4)


@pytest.fixture(scope="module")
def inputs():
    return load_inputs()


@pytest.fixture(scope="module")
def calibrated(inputs):
    """Girão validation case: W2, T4 against its thrust and fuel flow (the rated case is infeasible in v4)."""
    p, _, initial, _, refs = inputs
    pv, tv = validation_case(p, refs)
    r, _ = calibrate(pv, tv, initial)
    return pv, tv, r


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


def test_isentropic_components_roundtrip():
    for gas in (GAS, CONST):
        Tt_c, Pt_c, w = compressor_is(300.0, 1e5, 3.0, 1.0, gas)
        assert compressor_is(300.0, 1e5, 3.0, 1.0, gas)[0] == pytest.approx(compressor(300.0, 1e5, 3.0, 1.0, gas)[0])
        Tt_t, Pt_t, pi = turbine_is_for_work(Tt_c, Pt_c, w, 1.0, gas)
        assert (Tt_t, Pt_t, pi) == pytest.approx((300.0, 1e5, 3.0))
    # isentropic efficiency is the ratio of ideal to actual enthalpy rise
    T_is = compressor_is(300.0, 1e5, 3.0, 1.0, GAS)[0]
    T_out, _, w = compressor_is(300.0, 1e5, 3.0, 0.85, GAS)
    assert (GAS.h(T_is) - GAS.h(300.0)) / w == pytest.approx(0.85)
    assert GAS.h(T_out) - GAS.h(300.0) == pytest.approx(w)


def test_constant_cp_compressor_is_closed_form():
    Tt, Pt, w = compressor(288.15, 101325.0, 4.0, 0.9, CONST)
    assert Tt == pytest.approx(288.15 * 4.0 ** (0.4 / 1.4 / 0.9))
    assert w == pytest.approx(1005.0 * (Tt - 288.15))


def test_nozzle_choking():
    critical = (2 / 2.4) ** (-1.4 / 0.4)
    assert not nozzle(300.0, 0.99 * critical * 1e5, 1e5, CONST).choked
    n = nozzle(300.0, 1.2 * critical * 1e5, 1e5, CONST)
    assert n.choked
    assert n.V == pytest.approx(math.sqrt(2 * 1005.0 * (300.0 - 300.0 * 2 / 2.4)))
    assert n.F_per_W > n.V  # pressure thrust added
    # variable cp: choked exit velocity equals the local speed of sound
    n = nozzle(1100.0, 3e5, 1e5, GAS, 0.02)
    Ts = GAS.T_from_phi(GAS.phi(1100.0, 0.02) + GAS.R(0.02) * math.log(n.p_exit / 3e5), 0.02)
    assert n.choked
    assert n.V == pytest.approx(math.sqrt(GAS.gamma(Ts, 0.02) * GAS.R(0.02) * Ts), rel=1e-9)


def test_nozzle_coefficients():
    base = nozzle(1100.0, 3e5, 1e5, GAS, 0.02)
    n = nozzle(1100.0, 3e5, 1e5, GAS, 0.02, cfg=1.01, cd=0.99)
    assert n.F_per_W == pytest.approx(1.01 * base.F_per_W)  # thrust coefficient scales gross thrust
    assert n.A == pytest.approx(base.A / 0.99)  # discharge coefficient scales the area only
    assert n.p_exit == base.p_exit


# --- cycle -----------------------------------------------------------------------

def ideal_params(p):
    return replace(
        p, gas=CONST, inlet_recovery=1.0, FPR=1.5, eta_fan_outer=1.0, eta_fan_inner=1.0, eta_booster=1.0,
        eta_hpc=1.0, eta_hpt=1.0, eta_lpt=1.0, pr_fan_inner=1.5, pr_booster=2.0 / 1.5, duct_25_24=1.0,
        burner_eta=1.0, burner_pr=1.0, duct_45_44=1.0, duct_6_5=1.0, bypass_duct=1.0, mech_eff=1.0,
        cfg_18=1.0, cfg_8=1.0, cd_18=1.0, cd_8=1.0, include_fuel_mass=False, opr=10.0, bpr=5.0,
        ngv=0.0, hpt_rotor=0.0, leak=0.0, hp_power_offtake=0.0, customer_bleed=0.0,
    )


def test_ideal_limit_matches_closed_form(inputs):
    p = ideal_params(inputs[0])
    T4, W2 = 1000.0, 300.0
    r = run(p, W2, T4)
    assert not r["n18"].choked and not r["n8"].choked  # closed form assumes full expansion

    g, cp, T0 = 1.4, 1005.0, p.T0
    k = (g - 1) / g
    tau_lam, tau_c, tau_f, alpha = T4 / T0, p.opr ** k, p.FPR ** k, p.bpr
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
    assert r["W_sec"] > 0
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
    assert r["thrust"] == pytest.approx(t.thrust, rel=1e-6)
    assert r["W_fuel"] == pytest.approx(t.fuel, rel=1e-6)
    assert r["FPR"] == p.FPR  # input, not solved


def test_pressure_chain(calibrated):
    p, _, r = calibrated
    st = r["stations"]
    assert st["3"][1] / st["2"][1] == pytest.approx(p.opr)
    assert st["25"][1] / st["2"][1] == pytest.approx(p.core_pr_25_2)
    assert st["25"][1] / st["24"][1] == pytest.approx(p.duct_25_24)
    assert st["21"][1] / st["2"][1] == pytest.approx(p.pr_fan_inner)
    assert st["24"][1] / st["21"][1] == pytest.approx(p.pr_booster)
    assert st["44"][1] == st["43"][1]
    assert st["4"][1] / st["3"][1] == pytest.approx(p.burner_pr)
    assert st["45"][1] / st["44"][1] == pytest.approx(p.duct_45_44)
    assert st["8"][1] / st["5"][1] == pytest.approx(p.duct_6_5)
    assert st["18"][1] / st["13"][1] == pytest.approx(p.bypass_duct)


def test_secondary_air_and_t41(calibrated):
    p, _, r = calibrated
    assert r["W_comb"] + r["W_sec"] + p.customer_bleed == pytest.approx(r["W_core"])
    assert (r["W_ngv"], r["W_rotor"], r["W_leak"]) == pytest.approx(
        (p.ngv * r["W_core"], p.hpt_rotor * r["W_core"], p.leak * r["W_core"]))
    assert p.secondary_fraction == pytest.approx(0.13)
    T3 = r["stations"]["3"][0]
    assert T3 < r["T41"] < r["T4"]  # NGV cooling air dilutes the gas before the rotor
    st = r["stations"]
    assert st["44"][0] < st["43"][0]  # HPT rotor cooling mixes in at 44
    assert st["45"][0] < st["44"][0]  # leakage returns at 45
    assert st["3"][2] == pytest.approx(r["W_core"] - r["W_leak"])  # leakage leaves before the HPC exit


def test_leakage_takes_part_of_hpc_work(calibrated):
    p, _, r = calibrated
    gas, st = p.gas, calibrated[2]["stations"]
    w_hpc = gas.h(st["3"][0]) - gas.h(st["25"][0])
    assert gas.h(r["T_leak"]) - gas.h(st["25"][0]) == pytest.approx(p.leak_bleed_point * w_hpc)
    assert r["P_hpc"] == pytest.approx(r["W3"] * w_hpc + r["W_leak"] * p.leak_bleed_point * w_hpc)


VALIDATION_ITEMS = ["W2", "T13", "P13", "T21", "T25", "P25", "T3", "P3", "W3", "W31", "T4", "T41", "T43", "P44",
                    "T44", "T45", "T5", "P5", "EGT"]  # gas-path order
VALIDATION_OPEN = {"P5"}  # v4.1 open deviation, see docs/status.md


@pytest.mark.parametrize("item", VALIDATION_ITEMS)
def test_validation_against_girao(item, inputs, calibrated, request):
    if item in VALIDATION_OPEN:
        request.applymarker(pytest.mark.xfail(strict=True, reason="v4.1 deviation from Girão, decision open"))
    _, _, _, raw, refs = inputs
    row = next(x for x in validation_rows(calibrated[2], raw, refs) if x["item"] == item)
    assert row["result"] == "pass", row


def test_validation_rows_follow_gas_path(inputs, calibrated):
    _, _, _, raw, refs = inputs
    rows = validation_rows(calibrated[2], raw, refs)
    assert [x["item"] for x in rows] == VALIDATION_ITEMS
    first = first_deviation(rows)
    assert first is None or all(abs(x["deviation_pct"]) <= 1.0 for x in rows[:rows.index(first)])


def test_choke_mass_flux_sls():
    p = load_inputs()[0]
    assert choke_mass_flux(p.T0, p.P0, p.gas) == pytest.approx(241.3, abs=0.1)


def test_envelope_points_match_fuel(calibrated):
    p, t, r = calibrated
    env = thrust_envelope(p, t, W2_min=r["W2"] - 10.0, W2_max=r["W2"] + 10.0, step=10.0)
    assert len(env) == 3
    for e in env:
        assert run(p, e["W2_kg_s"], e["T4_K"])["W_fuel"] == pytest.approx(t.fuel, rel=1e-4)
    assert env[1]["thrust_kN"] == pytest.approx(r["thrust"] / 1000.0, rel=1e-3)
