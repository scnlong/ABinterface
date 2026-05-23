"""Basis indexing utilities.

The one-particle basis is ordered as four material/spin blocks:

    A_up, A_down, B_up, B_down.

Each block contains ``N`` local states.  The first ``N/2`` are valence-like and
the last ``N/2`` are conduction-like.  The model uses this basis for Hamiltonian
construction, projections, and state-resolved plotting.
"""

from __future__ import annotations

import numpy as np


def idx_A_up(i: int, N: int) -> int:
    return i


def idx_A_dn(i: int, N: int) -> int:
    return N + i


def idx_B_up(i: int, N: int) -> int:
    return 2 * N + i


def idx_B_dn(i: int, N: int) -> int:
    return 3 * N + i


def valence_indices(N: int) -> list[int]:
    """Return all diabatic valence-like state indices."""
    nv = N // 2
    out: list[int] = []
    for i in range(nv):
        out.extend([idx_A_up(i, N), idx_A_dn(i, N), idx_B_up(i, N), idx_B_dn(i, N)])
    return out


def conduction_indices(N: int) -> list[int]:
    """Return all diabatic conduction-like state indices."""
    nv = N // 2
    out: list[int] = []
    for i in range(nv, N):
        out.extend([idx_A_up(i, N), idx_A_dn(i, N), idx_B_up(i, N), idx_B_dn(i, N)])
    return out


def block_label(index: int, N: int) -> tuple[str, int]:
    """Map a global basis index to a human-readable block label and local index."""
    if 0 <= index < N:
        return "A_up", index
    if N <= index < 2 * N:
        return "A_dn", index - N
    if 2 * N <= index < 3 * N:
        return "B_up", index - 2 * N
    if 3 * N <= index < 4 * N:
        return "B_dn", index - 3 * N
    raise ValueError("index out of range")


def state_labels_and_spin(N: int) -> tuple[list[str], np.ndarray]:
    """Return text labels and spin tags for all diabatic states.

    Spin tag is ``+1`` for spin up and ``-1`` for spin down.
    """
    labels: list[str] = []
    spin: list[int] = []
    nv = N // 2
    for block, s in [("A", +1), ("A", -1), ("B", +1), ("B", -1)]:
        for i in range(N):
            band = "v" if i < nv else "c"
            local = i if i < nv else i - nv
            labels.append(f"{block} {band}{local} {'up' if s > 0 else 'dn'}")
            spin.append(s)
    return labels, np.asarray(spin, dtype=int)
