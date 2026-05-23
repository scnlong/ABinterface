"""Phenomenological post-pulse relaxation channels.

The coherent Hamiltonian already contains:
    - intramaterial SOC spin mixing;
    - spin-conserving A/B interlayer hopping.

The rate channels here represent open-system/bath-assisted population
redistribution after the laser pulse.  All one-body rates use exponential
probabilities p = 1-exp(-rate*dt), which keeps occupations bounded without a
manual collision-fraction parameter.
"""

from __future__ import annotations

import numpy as np

from .basis import idx_A_dn, idx_A_up, idx_B_dn, idx_B_up
from .config import ModelConfig
from .laser import dipole_matrix_element

Channel = dict[str, float | int | str]


def build_interlayer_transfer_channels(energies: np.ndarray, H_inter: np.ndarray, config: ModelConfig) -> list[Channel]:
    """Build spin-conserving interlayer downhill transfer channels.

    A channel i -> j is allowed if:
        E_i > E_j
        <j|H_inter|i> is nonzero

    Because H_inter contains only spin-conserving A<->B hopping, these channels
    describe ordinary interlayer transfer, not interface SOC spin flip.
    """
    channels: list[Channel] = []
    scale = max(config.tAB * config.tAB, 1.0e-20)

    for i in range(len(energies)):
        for j in range(len(energies)):
            tij = H_inter[j, i]
            amp2 = abs(tij) ** 2
            if amp2 <= 0.0:
                continue

            dE = float(energies[i] - energies[j])
            if dE <= 0.0:
                continue

            channels.append({
                "i": i,
                "j": j,
                "rate": config.W_downhill * amp2 / scale,
                "dE": dE,
                "amp": float(abs(tij)),
            })

    return channels


def apply_one_body_relaxation(rho: np.ndarray, channels: list[Channel], dt_fs: float) -> tuple[np.ndarray, float]:
    """Apply one-electron incoherent channels ``i -> j``.

    For each channel:
        p = 1 - exp(-rate * dt)
        dn = p * n_i * (1-n_j)
    """
    if not channels:
        return rho, 0.0

    rho2 = rho.copy()
    diag = np.real(np.diag(rho2)).copy()
    total = 0.0

    for ch in channels:
        i = int(ch["i"])
        j = int(ch["j"])
        rate = float(ch["rate"])
        pauli = diag[i] * (1.0 - diag[j])
        if pauli <= 0.0 or rate <= 0.0:
            continue

        p = 1.0 - np.exp(-rate * dt_fs)
        dn = p * pauli
        if dn <= 0.0:
            continue

        diag[i] -= dn
        diag[j] += dn
        total += dn

    diag = np.clip(diag, 0.0, 1.0)
    np.fill_diagonal(rho2, diag)

    if total > 0.0:
        rho2 = np.diag(np.diag(rho2)).astype(complex)
    else:
        rho2 = 0.5 * (rho2 + rho2.conj().T)

    return rho2, total


def build_intramaterial_relaxation_channels(energies: np.ndarray, config: ModelConfig) -> list[Channel]:
    """Build spin-conserving intramaterial ``c -> v`` relaxation channels.

    Rate hierarchy:
        Gamma_{c->v} = W_intra_X * M(v,c)^2 * J(E_c-E_v)

    M(v,c) reuses the optical matrix-element hierarchy, so different bands
    relax at different rates without an artificial time-spreading parameter.
    """
    N = config.N
    nv = N // 2
    channels: list[Channel] = []

    for c in range(nv, N):
        c_local = c - nv
        for v in range(nv):
            pairs = [
                ("A", idx_A_up(c, N), idx_A_up(v, N), "A_up"),
                ("A", idx_A_dn(c, N), idx_A_dn(v, N), "A_dn"),
                ("B", idx_B_up(c, N), idx_B_up(v, N), "B_up"),
                ("B", idx_B_dn(c, N), idx_B_dn(v, N), "B_dn"),
            ]
            for material, i, j, label in pairs:
                dE = float(energies[i] - energies[j])
                if dE <= 0.0:
                    continue

                Wmat = config.W_intra_A if material == "A" else config.W_intra_B
                assert Wmat is not None

                m = dipole_matrix_element(material, v, c_local, dE, config)
                d0 = config.dA0 if material == "A" else config.dB0
                matrix_weight = (abs(m) / abs(d0)) ** 2 if abs(d0) > 1.0e-14 else 0.0

                if material == "A":
                    energy_scale = max(config.gap_A + config.bandwidth_v_A + config.bandwidth_c_A, 1.0e-12)
                else:
                    energy_scale = max(config.gap_B + config.bandwidth_v_B + config.bandwidth_c_B, 1.0e-12)

                bath_weight = (dE / energy_scale) * np.exp(-dE / energy_scale)
                rate = float(Wmat * matrix_weight * bath_weight)
                if rate <= 0.0:
                    continue

                channels.append({
                    "i": i,
                    "j": j,
                    "rate": rate,
                    "dE": dE,
                    "label": label,
                    "matrix_weight": float(matrix_weight),
                    "bath_weight": float(bath_weight),
                })

    return channels



# Impact excitation was intentionally removed from the main model.
# Reason: without explicit electron-electron Coulomb matrix elements and a
# controlled bath/spectral function, it is an extra phenomenological channel.
# For the current short-time chain mechanism, the interpretable processes are:
#   material-internal SOC mixing,
#   spin-conserving interlayer transfer,
#   intramaterial c -> v relaxation.
