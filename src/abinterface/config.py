"""Configuration dataclass for the A/B interface model.

This version implements the chain mechanism discussed in the model notes:

    A_v up -> A_c up -> A_c down -> B_c down -> B_v down

The default model therefore separates three effects:

1. material-internal SOC:
   - diagonal spin splitting derived from lambda_soc_A/B;
   - coherent intramaterial spin mixing, especially in the conduction bands;

2. spin-conserving interlayer transfer:
   - A_c,s <-> B_c,s is the primary interface channel;

3. post-pulse intramaterial c -> v relaxation:
   - B_c down can relax into B_v down, while A and B also have their own
     spin-conserving c -> v relaxation channels.

The former impact-excitation branch has been removed from the main model.  It
was too phenomenological for the present short-time chain mechanism and tended
to obscure the pathway interpretation.

No independent spin-splitting input parameters are exposed.
"""

from dataclasses import dataclass
from typing import Literal

CarrierMode = Literal["full", "rwa"]
PlotMode = Literal["delta", "absolute"]
ColorNorm = Literal["linear", "symlog"]


@dataclass(slots=True)
class ModelConfig:
    """All user-facing parameters for one simulation."""

    # Basis size and band structure without SOC.
    N: int = 12
    gap_A: float = 1.5
    gap_B: float = 1.5
    offset_A: float = 0.0
    offset_B: float = 0.40
    bandwidth_v_A: float = 0.65
    bandwidth_c_A: float = 0.65
    bandwidth_v_B: float = 0.65
    bandwidth_c_B: float = 0.65

    # Material-internal SOC.  These are energy scales in eV.
    # Diagonal splittings are derived from these values.  The sign convention
    # is fixed internally so that spin-down CBM is above spin-up CBM by default.
    lambda_soc_A: float = 0.05
    lambda_soc_B: float = 0.05

    # Coherent intramaterial SOC spin mixing.  These are off-diagonal
    # up<->down matrix elements in eV, applied within each material and band
    # manifold.  The CB values are central for A_c_up -> A_c_down and
    # B_c_up/down mixing.
    soc_mix_cb_A: float = 0.020
    soc_mix_cb_B: float = 0.020
    soc_mix_vb_A: float = 0.003
    soc_mix_vb_B: float = 0.003

    # Spin-conserving interlayer/interface Hamiltonian.
    # tAB is now interpreted as A_c,s <-> B_c,s hopping, not interface
    # spin-flip hopping.  tAB_vv is optional valence-valence coupling.
    tAB: float = 0.08
    tAB_vv: float = 0.00
    interface_band_width: float = 3.0
    hybrid_energy_width: float = 3.0

    # Laser pulse and optical matrix elements.
    A0: float = 0.30
    omega_eV: float = 2.0
    pulse_duration: float = 20.0
    carrier: CarrierMode = "full"
    dA0: float = 1.0
    dB0: float = 1.0
    optical_energy_width: float = 2.5
    optical_energy_width_A: float | None = None
    optical_energy_width_B: float | None = None
    band_overlap_width: float = 2.5

    # Phenomenological post-pulse rates.
    # W_downhill applies to spin-conserving interlayer c-c/v-v downhill
    # transfer channels derived from the interlayer hopping matrix.
    W_downhill: float = 0.01
    W_intra: float = 0.03
    W_intra_A: float | None = None
    W_intra_B: float | None = None

    # Time propagation.
    t_final: float = 70.0
    dt: float = 0.02

    # State-resolved comparison times.
    compare_time_ref: float | None = None
    compare_time_1: float | None = None
    compare_time_2: float | None = None

    # Output and plotting.
    plot_mode: PlotMode = "delta"
    max_plot_points: int = 5000
    level_half_length: float = 0.38
    level_x_jitter: float = 0.012
    level_linewidth: float = 2.0
    level_alpha: float = 1.0
    delta_color_scale: float = 0.0
    delta_color_percentile: float = 80.0
    delta_color_norm: ColorNorm = "symlog"
    delta_color_linthresh_fraction: float = 0.03
    delta_colormap: str = "bwr"
    output_prefix: str = "interface_chain_model"

    def resolved(self) -> "ModelConfig":
        """Resolve dependent defaults and validate basic constraints."""
        if self.optical_energy_width_A is None:
            self.optical_energy_width_A = self.optical_energy_width
        if self.optical_energy_width_B is None:
            self.optical_energy_width_B = self.optical_energy_width
        if self.W_intra_A is None:
            self.W_intra_A = self.W_intra
        if self.W_intra_B is None:
            self.W_intra_B = self.W_intra
        if self.compare_time_ref is None:
            self.compare_time_ref = self.pulse_duration
        if self.compare_time_1 is None:
            self.compare_time_1 = self.pulse_duration + 2.0
        if self.compare_time_2 is None:
            self.compare_time_2 = min(self.t_final, self.pulse_duration + 30.0)
        self.validate()
        return self


    def validate(self) -> None:
        """Raise ``ValueError`` if the configuration is inconsistent."""
        if self.N % 2:
            raise ValueError("N must be even.")
        if self.N < 2:
            raise ValueError("N must be at least 2.")
        if self.pulse_duration > self.t_final:
            raise ValueError("pulse_duration must be <= t_final.")
        if self.dt <= 0.0:
            raise ValueError("dt must be positive.")
        for name in ["compare_time_ref", "compare_time_1", "compare_time_2"]:
            val = getattr(self, name)
            if val is None:
                continue
            if not (0.0 <= val <= self.t_final):
                raise ValueError(f"{name} must lie in [0, t_final].")
        if self.carrier not in ("full", "rwa"):
            raise ValueError("carrier must be 'full' or 'rwa'.")
        if self.plot_mode not in ("delta", "absolute"):
            raise ValueError("plot_mode must be 'delta' or 'absolute'.")
        if self.delta_color_norm not in ("linear", "symlog"):
            raise ValueError("delta_color_norm must be 'linear' or 'symlog'.")
