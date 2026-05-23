"""Band energies and SOC-derived diagonal spin splitting."""

from __future__ import annotations

import numpy as np

from .config import ModelConfig


def soc_derived_spin_splittings(config: ModelConfig) -> tuple[float, float]:
    """Return diagonal SOC-induced spin splittings for A and B.

    Convention:
        E_up = E0 + split/2
        E_dn = E0 - split/2

    The chain mechanism uses spin-down CBM above spin-up CBM in both materials.
    Therefore both splittings are negative and their magnitudes come from
    material-internal SOC parameters, not from interlayer hopping.
    """
    return -abs(config.lambda_soc_A), -abs(config.lambda_soc_B)


def build_energies(config: ModelConfig) -> np.ndarray:
    """Construct diagonal one-particle energies.

    The input gaps, offsets, and bandwidths define the no-SOC band positions.
    SOC then adds diagonal spin splitting derived from lambda_soc_A/B.
    """
    N = config.N
    nv = N // 2

    vA = np.linspace(config.bandwidth_v_A, 0.0, nv)
    cA = np.linspace(0.0, config.bandwidth_c_A, nv)
    vB = np.linspace(config.bandwidth_v_B, 0.0, nv)
    cB = np.linspace(0.0, config.bandwidth_c_B, nv)

    Ev_A = config.offset_A - 0.5 * config.gap_A - vA
    Ec_A = config.offset_A + 0.5 * config.gap_A + cA
    Ev_B = config.offset_B - 0.5 * config.gap_B - vB
    Ec_B = config.offset_B + 0.5 * config.gap_B + cB

    split_A, split_B = soc_derived_spin_splittings(config)

    E_A_up = np.concatenate([Ev_A, Ec_A]) + 0.5 * split_A
    E_A_dn = np.concatenate([Ev_A, Ec_A]) - 0.5 * split_A
    E_B_up = np.concatenate([Ev_B, Ec_B]) + 0.5 * split_B
    E_B_dn = np.concatenate([Ev_B, Ec_B]) - 0.5 * split_B

    return np.concatenate([E_A_up, E_A_dn, E_B_up, E_B_dn])
