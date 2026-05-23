"""A/B interface toy model package.

The package provides a modular version of the original single-file script:

- band construction and basis indexing;
- laser, intramaterial SOC, and spin-conserving interlayer Hamiltonian construction;
- unitary density-matrix propagation;
- phenomenological post-pulse relaxation channels;
- observable collection and plotting;
- command-line interface through ``abinterface-run``.
"""

from .config import ModelConfig
from .simulation import SimulationResult, run_simulation

__all__ = ["ModelConfig", "SimulationResult", "run_simulation"]
