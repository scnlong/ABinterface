import numpy as np

from ABinterface.bands import build_energies, soc_derived_spin_splittings
from ABinterface.basis import idx_A_up, idx_A_dn, idx_B_up, idx_B_dn
from ABinterface.config import ModelConfig
from ABinterface.simulation import run_simulation


def test_soc_splitting_sign_controls_spin_ordering():
    cfg = ModelConfig(N=12, lambda_soc_A=-0.05, lambda_soc_B=0.04).resolved()
    split_A, split_B = soc_derived_spin_splittings(cfg)
    assert split_A == cfg.lambda_soc_A
    assert split_B == cfg.lambda_soc_B

    energies = build_energies(cfg)
    nv = cfg.N // 2
    A_cbm_up = energies[idx_A_up(nv, cfg.N)]
    A_cbm_dn = energies[idx_A_dn(nv, cfg.N)]
    B_cbm_up = energies[idx_B_up(nv, cfg.N)]
    B_cbm_dn = energies[idx_B_dn(nv, cfg.N)]
    A_vbm_up = energies[idx_A_up(nv - 1, cfg.N)]
    A_vbm_dn = energies[idx_A_dn(nv - 1, cfg.N)]
    B_vbm_up = energies[idx_B_up(nv - 1, cfg.N)]
    B_vbm_dn = energies[idx_B_dn(nv - 1, cfg.N)]

    # Negative split: E_down > E_up. Positive split: E_up > E_down.
    assert A_cbm_dn > A_cbm_up
    assert B_cbm_up > B_cbm_dn
    assert A_vbm_dn > A_vbm_up
    assert B_vbm_up > B_vbm_dn
    assert min(B_cbm_up, B_cbm_dn) > max(A_cbm_up, A_cbm_dn)
    assert min(B_vbm_up, B_vbm_dn) > max(A_vbm_up, A_vbm_dn)


def test_small_simulation_conserves_particle_number():
    cfg = ModelConfig(N=4, t_final=4.0, pulse_duration=2.0, dt=0.1, compare_time_1=3.0, compare_time_2=4.0, max_plot_points=20).resolved()
    result = run_simulation(cfg)
    particle = result.data[:, result.keys.index("particle_number")]
    assert np.allclose(particle, particle[0], atol=1e-10)
    assert result.data.shape[0] == int(round(cfg.t_final / cfg.dt)) + 1
