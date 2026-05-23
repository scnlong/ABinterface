"""Density-matrix initialization and unitary propagation."""

from __future__ import annotations

import numpy as np

from .constants import HBAR_EV_FS


def initial_static_ground_density(H_static: np.ndarray, n_electrons: int) -> np.ndarray:
    """Return the filled ground-state density matrix of ``H_static``.

    The initial state is not a manually filled diabatic valence subspace.  It is
    the projector onto the lowest ``n_electrons`` static eigenstates.  This
    includes static interface hybridization and SOC mixing at ``t=0`` and avoids
    an artificial initial quench.
    """
    _, evecs = np.linalg.eigh(H_static)
    occ_vecs = evecs[:, :n_electrons]
    rho = occ_vecs @ occ_vecs.conj().T
    return 0.5 * (rho + rho.conj().T)


def midpoint_unitary(H: np.ndarray, dt_fs: float) -> np.ndarray:
    """Return ``exp(-i H dt / hbar)`` using dense diagonalization."""
    evals, evecs = np.linalg.eigh(H)
    phases = np.exp(-1.0j * evals * dt_fs / HBAR_EV_FS)
    return (evecs * phases) @ evecs.conj().T


def static_eigenbasis_occupations(rho: np.ndarray, evecs_static: np.ndarray) -> np.ndarray:
    """Return occupations after projecting ``rho`` into the static eigenbasis."""
    rho_eig = evecs_static.conj().T @ rho @ evecs_static
    return np.real(np.diag(rho_eig))
