"""Command-line interface for the A/B interface chain model."""

import argparse

from .config import ModelConfig
from .plotting import plot_all, print_summary
from .simulation import run_simulation


def build_parser() -> argparse.ArgumentParser:
    """Build and return the command-line parser."""
    d = ModelConfig()
    parser = argparse.ArgumentParser(
        description=(
            "Toy density-matrix model for laser-driven A/B interface redistribution "
            "with material-internal SOC spin mixing and spin-conserving interlayer transfer."
        )
    )

    # Band structure.
    parser.add_argument("--N", type=int, default=d.N, help="Bands per material per spin; must be even.")
    parser.add_argument("--gap-A", type=float, default=d.gap_A, help="No-SOC band gap of material A in eV.")
    parser.add_argument("--gap-B", type=float, default=d.gap_B, help="No-SOC band gap of material B in eV.")
    parser.add_argument("--offset-A", type=float, default=d.offset_A, help="Rigid no-SOC energy offset of A in eV.")
    parser.add_argument("--offset-B", type=float, default=d.offset_B, help="Rigid no-SOC energy offset of B in eV.")
    parser.add_argument("--bandwidth-v-A", type=float, default=d.bandwidth_v_A, help="A valence bandwidth in eV.")
    parser.add_argument("--bandwidth-c-A", type=float, default=d.bandwidth_c_A, help="A conduction bandwidth in eV.")
    parser.add_argument("--bandwidth-v-B", type=float, default=d.bandwidth_v_B, help="B valence bandwidth in eV.")
    parser.add_argument("--bandwidth-c-B", type=float, default=d.bandwidth_c_B, help="B conduction bandwidth in eV.")

    # Material SOC.
    parser.add_argument("--lambda-soc-A", type=float, default=d.lambda_soc_A, help="Material-internal SOC diagonal splitting scale for A in eV.")
    parser.add_argument("--lambda-soc-B", type=float, default=d.lambda_soc_B, help="Material-internal SOC diagonal splitting scale for B in eV.")
    parser.add_argument("--soc-mix-cb-A", type=float, default=d.soc_mix_cb_A, help="A conduction-band SOC up/down mixing in eV.")
    parser.add_argument("--soc-mix-cb-B", type=float, default=d.soc_mix_cb_B, help="B conduction-band SOC up/down mixing in eV.")
    parser.add_argument("--soc-mix-vb-A", type=float, default=d.soc_mix_vb_A, help="A valence-band SOC up/down mixing in eV.")
    parser.add_argument("--soc-mix-vb-B", type=float, default=d.soc_mix_vb_B, help="B valence-band SOC up/down mixing in eV.")

    # Spin-conserving interlayer Hamiltonian.
    parser.add_argument("--tAB", type=float, default=d.tAB, help="Spin-conserving A_c,s <-> B_c,s hopping in eV.")
    parser.add_argument("--tAB-vv", type=float, default=d.tAB_vv, help="Optional spin-conserving A_v,s <-> B_v,s hopping in eV.")
    parser.add_argument("--interface-band-width", type=float, default=d.interface_band_width, help="Band-index width for interlayer hopping.")
    parser.add_argument("--hybrid-energy-width", type=float, default=d.hybrid_energy_width, help="Energy mismatch width for interlayer hopping.")

    # Laser.
    parser.add_argument("--A0", type=float, default=d.A0, help="Laser field amplitude in model units.")
    parser.add_argument("--omega-eV", type=float, default=d.omega_eV, help="Photon energy in eV.")
    parser.add_argument("--pulse-duration", type=float, default=d.pulse_duration, help="Pulse duration in fs.")
    parser.add_argument("--carrier", choices=["full", "rwa"], default=d.carrier, help="full carrier or envelope-only RWA drive.")
    parser.add_argument("--dA0", type=float, default=d.dA0, help="Optical dipole scale for A.")
    parser.add_argument("--dB0", type=float, default=d.dB0, help="Optical dipole scale for B.")
    parser.add_argument("--optical-energy-width", type=float, default=d.optical_energy_width, help="Fallback optical resonance width in eV.")
    parser.add_argument("--optical-energy-width-A", type=float, default=None, help="A-specific optical resonance width.")
    parser.add_argument("--optical-energy-width-B", type=float, default=None, help="B-specific optical resonance width.")
    parser.add_argument("--band-overlap-width", type=float, default=d.band_overlap_width, help="Band-edge overlap width for optical/relaxation matrix elements.")

    # Relaxation.
    parser.add_argument("--W-downhill", type=float, default=d.W_downhill, help="Post-pulse spin-conserving interlayer downhill transfer scale in 1/fs.")
    parser.add_argument("--W-intra", type=float, default=d.W_intra, help="Default intramaterial c->v relaxation scale in 1/fs.")
    parser.add_argument("--W-intra-A", type=float, default=None, help="A-specific c->v relaxation scale; defaults to W-intra.")
    parser.add_argument("--W-intra-B", type=float, default=None, help="B-specific c->v relaxation scale; defaults to W-intra.")

    # Time and comparison.
    parser.add_argument("--t-final", type=float, default=d.t_final, help="Final simulation time in fs.")
    parser.add_argument("--dt", type=float, default=d.dt, help="Time step in fs.")
    parser.add_argument("--compare-time-ref", type=float, default=None, help="Reference time for state-level plots; default pulse end.")
    parser.add_argument("--compare-time-1", type=float, default=None, help="Left-panel comparison time.")
    parser.add_argument("--compare-time-2", type=float, default=None, help="Right-panel comparison time.")

    # Output and plotting.
    parser.add_argument("--plot-mode", choices=["delta", "absolute"], default=d.plot_mode, help="Plot changes or absolute occupations.")
    parser.add_argument("--max-plot-points", type=int, default=d.max_plot_points, help="Maximum plotted time points.")
    parser.add_argument("--level-half-length", type=float, default=d.level_half_length, help="Half-length of level lines.")
    parser.add_argument("--level-x-jitter", type=float, default=d.level_x_jitter, help="Horizontal jitter inside material/spin columns.")
    parser.add_argument("--level-linewidth", type=float, default=d.level_linewidth, help="Level-line width.")
    parser.add_argument("--level-alpha", type=float, default=d.level_alpha, help="Level-line alpha.")
    parser.add_argument("--delta-color-scale", type=float, default=d.delta_color_scale, help="Manual signed Delta-n color scale; <=0 automatic.")
    parser.add_argument("--delta-color-percentile", type=float, default=d.delta_color_percentile, help="Automatic color-scale percentile.")
    parser.add_argument("--delta-color-norm", choices=["linear", "symlog"], default=d.delta_color_norm, help="Color normalization.")
    parser.add_argument("--delta-color-linthresh-fraction", type=float, default=d.delta_color_linthresh_fraction, help="SymLog linear-threshold fraction.")
    parser.add_argument("--delta-colormap", default=d.delta_colormap, help="Diverging colormap name.")
    parser.add_argument("--output-prefix", default=d.output_prefix, help="Output file prefix.")
    return parser


def config_from_args(args: argparse.Namespace) -> ModelConfig:
    """Convert parsed arguments to :class:`ModelConfig`."""
    return ModelConfig(
        N=args.N,
        gap_A=args.gap_A,
        gap_B=args.gap_B,
        offset_A=args.offset_A,
        offset_B=args.offset_B,
        bandwidth_v_A=args.bandwidth_v_A,
        bandwidth_c_A=args.bandwidth_c_A,
        bandwidth_v_B=args.bandwidth_v_B,
        bandwidth_c_B=args.bandwidth_c_B,
        lambda_soc_A=args.lambda_soc_A,
        lambda_soc_B=args.lambda_soc_B,
        soc_mix_cb_A=args.soc_mix_cb_A,
        soc_mix_cb_B=args.soc_mix_cb_B,
        soc_mix_vb_A=args.soc_mix_vb_A,
        soc_mix_vb_B=args.soc_mix_vb_B,
        tAB=args.tAB,
        tAB_vv=args.tAB_vv,
        interface_band_width=args.interface_band_width,
        hybrid_energy_width=args.hybrid_energy_width,
        A0=args.A0,
        omega_eV=args.omega_eV,
        pulse_duration=args.pulse_duration,
        carrier=args.carrier,
        dA0=args.dA0,
        dB0=args.dB0,
        optical_energy_width=args.optical_energy_width,
        optical_energy_width_A=args.optical_energy_width_A,
        optical_energy_width_B=args.optical_energy_width_B,
        band_overlap_width=args.band_overlap_width,
        W_downhill=args.W_downhill,
        W_intra=args.W_intra,
        W_intra_A=args.W_intra_A,
        W_intra_B=args.W_intra_B,
        t_final=args.t_final,
        dt=args.dt,
        compare_time_ref=args.compare_time_ref,
        compare_time_1=args.compare_time_1,
        compare_time_2=args.compare_time_2,
        plot_mode=args.plot_mode,
        max_plot_points=args.max_plot_points,
        level_half_length=args.level_half_length,
        level_x_jitter=args.level_x_jitter,
        level_linewidth=args.level_linewidth,
        level_alpha=args.level_alpha,
        delta_color_scale=args.delta_color_scale,
        delta_color_percentile=args.delta_color_percentile,
        delta_color_norm=args.delta_color_norm,
        delta_color_linthresh_fraction=args.delta_color_linthresh_fraction,
        delta_colormap=args.delta_colormap,
        output_prefix=args.output_prefix,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the model from the command line."""
    parser = build_parser()
    args = parser.parse_args(argv)
    config = config_from_args(args).resolved()
    result = run_simulation(config)
    print_summary(result)
    plot_all(result)


if __name__ == "__main__":
    main()
