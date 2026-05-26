"""Hamiltonian construction for the A/B interface chain model.

Compared with the earlier interface-SOC model, this version does not use a
direct A_c_up <-> B_v_down spin-flip interface hopping as the default mechanism.
It also does not hard-code the full sequence

    A_v up -> A_c up -> A_c down -> B_c down -> B_v down.

Instead, the Hamiltonian contains elementary coherent couplings:
    1. material-internal SOC diagonal splitting;
    2. material-internal SOC up/down mixing inside CB/VB manifolds;
    3. spin-conserving interlayer A_c,s <-> B_c,s hopping;
    4. laser-driven spin-conserving intramaterial v <-> c excitation.

The chain-like pathway is an optional interpretation of the resulting projected
occupation dynamics, not an imposed algorithmic rule.
"""

import numpy as np

from .basis import idx_A_dn, idx_A_up, idx_B_dn, idx_B_up
from .config import ModelConfig
from .laser import dipole_matrix_element, laser_field


def energy_filter(delta: float, width: float) -> float:
    """Gaussian energy-mismatch filter; disabled when ``width <= 0``."""
    if width <= 0.0:
        return 1.0
    return float(np.exp(-0.5 * (delta / width) ** 2))


def same_band_weight(local_a: int, local_b: int, width: float) -> float:
    """Band-index filter for same-manifold A<->B hopping.

    ``local_a`` and ``local_b`` are distances from the relevant band edge:
    for conduction states, 0 is CBM; for valence states, 0 is VBM.
    """
    if width <= 0.0:
        return 1.0
    return float(np.exp(-0.5 * ((local_a - local_b) / width) ** 2))


def add_laser_couplings(H: np.ndarray, energies: np.ndarray, field: float, config: ModelConfig) -> None:
    """Add spin-conserving intramaterial optical couplings to ``H`` in-place."""
    N = config.N
    nv = N // 2
    for v in range(nv):
        for c in range(nv, N):
            pairs = [
                ("A", idx_A_up(v, N), idx_A_up(c, N)),
                ("A", idx_A_dn(v, N), idx_A_dn(c, N)),
                ("B", idx_B_up(v, N), idx_B_up(c, N)),
                ("B", idx_B_dn(v, N), idx_B_dn(c, N)),
            ]
            for material, i, j in pairs:
                d = dipole_matrix_element(material, v, c - nv, float(energies[j] - energies[i]), config)
                hij = d * field
                H[i, j] += hij
                H[j, i] += np.conjugate(hij)


def add_intramaterial_soc_mixing(H: np.ndarray, config: ModelConfig) -> np.ndarray:
    """Add material-internal SOC up/down mixing and return its matrix.

    The diagonal SOC splitting is already included in the band energies.  This
    function adds the off-diagonal spin-mixing part:
        X_b_m,up <-> X_b_m,down

    The conduction-band mixing allows coherent transfer of projected occupation
    between up-like and down-like CB components.  It can support an
    Ac_up-to-Ac_down interpretation in suitable parameter regimes, but the code
    propagates the full density matrix and does not tag individual electrons.
    """
    N = config.N
    nv = N // 2
    H_soc = np.zeros_like(H)

    for i in range(N):
        is_valence = i < nv
        amp_A = config.soc_mix_vb_A if is_valence else config.soc_mix_cb_A
        amp_B = config.soc_mix_vb_B if is_valence else config.soc_mix_cb_B

        pairs = [
            (idx_A_up(i, N), idx_A_dn(i, N), amp_A),
            (idx_B_up(i, N), idx_B_dn(i, N), amp_B),
        ]

        for up, dn, amp in pairs:
            if amp == 0.0:
                continue
            H[up, dn] += amp
            H[dn, up] += np.conjugate(amp)
            H_soc[up, dn] += amp
            H_soc[dn, up] += np.conjugate(amp)

    return H_soc


def add_interlayer_terms(H: np.ndarray, energies: np.ndarray, config: ModelConfig) -> np.ndarray:
    """Add spin-conserving A/B interlayer hopping and return its matrix.

    Default physical meaning:
        A_c,s <-> B_c,s

    This is ordinary spin-conserving tunneling/hybridization.  It does not flip
    spin.  Optional valence-valence hopping can be enabled by setting tAB_vv>0.
    """
    N = config.N
    nv = N // 2
    H_inter = np.zeros_like(H)

    # Conduction-conduction spin-conserving A<->B hopping.
    for cA in range(nv, N):
        locA = cA - nv
        for cB in range(nv, N):
            locB = cB - nv
            weight = same_band_weight(locA, locB, config.interface_band_width)
            pairs = [
                (idx_A_up(cA, N), idx_B_up(cB, N)),
                (idx_A_dn(cA, N), idx_B_dn(cB, N)),
            ]
            for i, j in pairs:
                detuning = float(energies[i] - energies[j])
                tij = config.tAB * weight * energy_filter(detuning, config.hybrid_energy_width)
                if tij == 0.0:
                    continue
                H[i, j] += np.conjugate(tij)
                H[j, i] += tij
                H_inter[i, j] += np.conjugate(tij)
                H_inter[j, i] += tij

    # Optional valence-valence spin-conserving A<->B hopping.
    if config.tAB_vv != 0.0:
        for vA in range(nv):
            locA = (nv - 1) - vA  # 0 at VBM
            for vB in range(nv):
                locB = (nv - 1) - vB
                weight = same_band_weight(locA, locB, config.interface_band_width)
                pairs = [
                    (idx_A_up(vA, N), idx_B_up(vB, N)),
                    (idx_A_dn(vA, N), idx_B_dn(vB, N)),
                ]
                for i, j in pairs:
                    detuning = float(energies[i] - energies[j])
                    tij = config.tAB_vv * weight * energy_filter(detuning, config.hybrid_energy_width)
                    if tij == 0.0:
                        continue
                    H[i, j] += np.conjugate(tij)
                    H[j, i] += tij
                    H_inter[i, j] += np.conjugate(tij)
                    H_inter[j, i] += tij

    return H_inter


def build_static_hamiltonian(energies: np.ndarray, config: ModelConfig) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return ``H_static``, interlayer hopping matrix, and SOC-mixing matrix."""
    H = np.diag(energies).astype(complex)
    H_soc = add_intramaterial_soc_mixing(H, config)
    H_inter = add_interlayer_terms(H, energies, config)
    return H, H_inter, H_soc


def build_time_hamiltonian(t_fs: float, energies: np.ndarray, H_static: np.ndarray, config: ModelConfig) -> np.ndarray:
    """Return ``H_static + H_laser(t)``."""
    H = H_static.copy()
    field = laser_field(t_fs, config)
    add_laser_couplings(H, energies, field, config)
    return H
