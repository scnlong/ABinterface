"""A/B interface toy model package.

The package provides a modular version of the original single-file script:

- band construction and basis indexing;
- laser, intramaterial SOC, and spin-conserving interlayer Hamiltonian construction;
- unitary density-matrix propagation;
- coherent short-time density-matrix dynamics;
- observable collection and plotting;
- command-line interface through ``ABinterface-run``.
"""

from .config import ModelConfig
from .simulation import SimulationResult, run_simulation

__all__ = ["ModelConfig", "SimulationResult", "run_simulation"]
