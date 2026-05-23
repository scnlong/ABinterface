"""Laser pulse and intramaterial optical matrix elements."""

from __future__ import annotations

import numpy as np

from .config import ModelConfig
from .constants import HBAR_EV_FS


def envelope_sin2(t_fs: float, pulse_duration: float) -> float:
    """Return a compact sin^2 pulse envelope."""
    if t_fs < 0.0 or t_fs > pulse_duration:
        return 0.0
    return float(np.sin(np.pi * t_fs / pulse_duration) ** 2)


def laser_field(t_fs: float, config: ModelConfig) -> float:
    """Return the scalar laser field entering the model Hamiltonian.

    ``full`` mode keeps the optical carrier:
        ``A0 * sin^2(pi t/T) * cos(omega t / hbar)``.

    ``rwa`` mode keeps only the envelope.  It is useful for debugging slow
    population dynamics but is not a full-carrier propagation.
    """
    env = envelope_sin2(t_fs, config.pulse_duration)
    if config.carrier == "full":
        return float(config.A0 * env * np.cos(config.omega_eV * t_fs / HBAR_EV_FS))
    if config.carrier == "rwa":
        return float(config.A0 * env)
    raise ValueError("carrier must be 'full' or 'rwa'")


def dipole_matrix_element(
    material: str,
    v_local: int,
    c_local: int,
    delta_e: float,
    config: ModelConfig,
) -> float:
    """Return state-dependent optical/relaxation matrix-element amplitude.

    The same hierarchy is reused for optical excitation and intramaterial
    relaxation.  This keeps the model compact and avoids a separate artificial
    band-spreading parameter.

    Index convention:
        ``v_local = 0 ... nv-1``, where ``nv-1`` is the VBM.
        ``c_local = 0 ... nv-1``, where ``0`` is the CBM.

    Therefore the band-edge distances are:
        ``v_edge_distance = (nv - 1) - v_local`` and
        ``c_edge_distance = c_local``.

    This corrected definition preferentially couples CBM with VBM and prevents
    the unphysical uniform color pattern caused by the older ``c_local-v_local``
    overlap.
    """
    if material == "A":
        d0 = config.dA0
        width = config.optical_energy_width_A
    elif material == "B":
        d0 = config.dB0
        width = config.optical_energy_width_B
    else:
        raise ValueError("material must be 'A' or 'B'")

    assert width is not None
    resonance = 1.0 if width <= 0.0 else np.exp(-0.5 * ((delta_e - config.omega_eV) / width) ** 2)

    nv = config.N // 2
    v_edge_distance = (nv - 1) - v_local
    c_edge_distance = c_local
    overlap = np.exp(-0.5 * ((c_edge_distance - v_edge_distance) / config.band_overlap_width) ** 2)
    return float(d0 * resonance * overlap)
