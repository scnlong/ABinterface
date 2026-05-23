"""Top-level simulation driver."""

from dataclasses import dataclass

import numpy as np

from .bands import build_energies
from .config import ModelConfig
from .density import initial_static_ground_density, midpoint_unitary
from .hamiltonian import build_static_hamiltonian, build_time_hamiltonian
from .observables import collect_observables, observable_keys
from .relaxation import (
    apply_one_body_relaxation,
    build_interlayer_transfer_channels,
    build_intramaterial_relaxation_channels,
)


@dataclass(slots=True)
class SimulationResult:
    """Container returned by :func:`run_simulation`."""

    times: np.ndarray
    data: np.ndarray
    keys: list[str]
    diagnostics: dict[str, object]
    config: ModelConfig


def run_simulation(config: ModelConfig) -> SimulationResult:
    """Run one complete density-matrix simulation."""
    config = config.resolved()
    energies = build_energies(config)
    H_static, H_inter, H_soc = build_static_hamiltonian(energies, config)

    evals_static, evecs_static = np.linalg.eigh(H_static)
    rho = initial_static_ground_density(H_static, 2 * config.N)

    interlayer_channels = build_interlayer_transfer_channels(energies, H_inter, config)
    intra_channels = build_intramaterial_relaxation_channels(energies, config)
    n_steps = int(round(config.t_final / config.dt))
    dt = config.t_final / n_steps
    times = np.linspace(0.0, config.t_final, n_steps + 1)

    compare_times = [config.compare_time_ref, config.compare_time_1, config.compare_time_2]
    compare_indices = [int(np.argmin(np.abs(times - float(t)))) for t in compare_times]
    rho_snapshots: dict[int, np.ndarray] = {}

    keys = observable_keys()
    data = np.zeros((n_steps + 1, len(keys)))
    interlayer_cumulative = 0.0
    intra_cumulative = 0.0

    obs = collect_observables(
        rho, evals_static, evecs_static, interlayer_cumulative, intra_cumulative, config
    )
    data[0] = [obs[k] for k in keys]
    if 0 in compare_indices:
        rho_snapshots[0] = rho.copy()

    for step in range(n_steps):
        t_mid = (step + 0.5) * dt

        # Coherent midpoint propagation under:
        #   H_static = H_bands + H_SOC_mix + H_interlayer
        # plus the laser pulse H_laser(t_mid).
        H_mid = build_time_hamiltonian(t_mid, energies, H_static, config)
        U_dt = midpoint_unitary(H_mid, dt)
        rho = U_dt @ rho @ U_dt.conj().T
        rho = 0.5 * (rho + rho.conj().T)

        post_pulse = t_mid > config.pulse_duration
        dn_interlayer = 0.0
        dn_intra = 0.0

        if post_pulse and config.W_downhill > 0.0:
            rho, dn_interlayer = apply_one_body_relaxation(rho, interlayer_channels, dt)
        if post_pulse and config.W_intra > 0.0:
            rho, dn_intra = apply_one_body_relaxation(rho, intra_channels, dt)
        interlayer_cumulative += dn_interlayer
        intra_cumulative += dn_intra

        obs = collect_observables(
            rho, evals_static, evecs_static, interlayer_cumulative, intra_cumulative, config
        )
        data[step + 1] = [obs[k] for k in keys]
        data[step + 1, keys.index("interlayer_rate")] = dn_interlayer / dt
        data[step + 1, keys.index("intra_rate")] = dn_intra / dt

        if (step + 1) in compare_indices:
            rho_snapshots[step + 1] = rho.copy()

    for idx in compare_indices:
        if idx not in rho_snapshots:
            rho_snapshots[idx] = rho.copy()

    diagnostics: dict[str, object] = {
        "energies": energies,
        "H_static": H_static,
        "H_interlayer": H_inter,
        "H_soc_mix": H_soc,
        "evals_static": evals_static,
        "evecs_static": evecs_static,
        "interlayer_channels": interlayer_channels,
        "intra_channels": intra_channels,
        "rho_snapshots": rho_snapshots,
        "compare_indices": compare_indices,
        "compare_times_actual": [float(times[i]) for i in compare_indices],
    }

    return SimulationResult(times=times, data=data, keys=keys, diagnostics=diagnostics, config=config)
