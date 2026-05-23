"""Observable definitions for the A/B interface model."""

import numpy as np

from .basis import conduction_indices, valence_indices
from .config import ModelConfig
from .density import static_eigenbasis_occupations


def projected_observables(rho: np.ndarray, config: ModelConfig) -> dict[str, float]:
    """Return material-, spin-, and band-projected diabatic occupations."""
    N = config.N
    nv = N // 2
    diag = np.real(np.diag(rho))

    A_up = float(np.sum(diag[0:N]))
    A_dn = float(np.sum(diag[N:2 * N]))
    B_up = float(np.sum(diag[2 * N:3 * N]))
    B_dn = float(np.sum(diag[3 * N:4 * N]))
    spin_up = A_up + B_up
    spin_dn = A_dn + B_dn

    A_v_up = float(np.sum(diag[0:nv]))
    A_c_up = float(np.sum(diag[nv:N]))
    A_v_dn = float(np.sum(diag[N:N + nv]))
    A_c_dn = float(np.sum(diag[N + nv:2 * N]))

    B_v_up = float(np.sum(diag[2 * N:2 * N + nv]))
    B_c_up = float(np.sum(diag[2 * N + nv:3 * N]))
    B_v_dn = float(np.sum(diag[3 * N:3 * N + nv]))
    B_c_dn = float(np.sum(diag[3 * N + nv:4 * N]))

    return {
        "A_up": A_up,
        "A_dn": A_dn,
        "B_up": B_up,
        "B_dn": B_dn,
        "A_v_up": A_v_up,
        "A_c_up": A_c_up,
        "A_v_dn": A_v_dn,
        "A_c_dn": A_c_dn,
        "B_v_up": B_v_up,
        "B_c_up": B_c_up,
        "B_v_dn": B_v_dn,
        "B_c_dn": B_c_dn,
        "spin_up": spin_up,
        "spin_dn": spin_dn,
        "moment": spin_up - spin_dn,
        "valence": float(np.sum(diag[valence_indices(N)])),
        "conduction": float(np.sum(diag[conduction_indices(N)])),
        "particle_number": float(np.real(np.trace(rho))),
    }


def eigen_observables(rho: np.ndarray, evals_static: np.ndarray, evecs_static: np.ndarray, n_occ: int) -> dict[str, float]:
    """Return occupations and energy in the static eigenbasis."""
    occ = static_eigenbasis_occupations(rho, evecs_static)
    return {
        "eig_occ_low": float(np.sum(occ[:n_occ])),
        "eig_occ_high": float(np.sum(occ[n_occ:])),
        "eig_energy": float(np.sum(occ * evals_static)),
    }


def observable_keys() -> list[str]:
    """Ordered observable column names for output arrays and CSV files."""
    return [
        "A_up",
        "A_dn",
        "B_up",
        "B_dn",
        "A_v_up",
        "A_c_up",
        "A_v_dn",
        "A_c_dn",
        "B_v_up",
        "B_c_up",
        "B_v_dn",
        "B_c_dn",
        "spin_up",
        "spin_dn",
        "moment",
        "valence",
        "conduction",
        "particle_number",
        "eig_occ_low",
        "eig_occ_high",
        "eig_energy",
        "interlayer_rate",
        "interlayer_cumulative",
        "intra_rate",
        "intra_cumulative",
    ]


def collect_observables(
    rho: np.ndarray,
    evals_static: np.ndarray,
    evecs_static: np.ndarray,
    interlayer_cumulative: float,
    intra_cumulative: float,
    config: ModelConfig,
) -> dict[str, float]:
    """Collect all observables at one time."""
    obs = projected_observables(rho, config)
    obs.update(eigen_observables(rho, evals_static, evecs_static, 2 * config.N))
    obs["interlayer_rate"] = 0.0
    obs["interlayer_cumulative"] = interlayer_cumulative
    obs["intra_rate"] = 0.0
    obs["intra_cumulative"] = intra_cumulative
    return obs
