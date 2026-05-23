"""Plotting utilities for simulation results."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib.cm import ScalarMappable
import numpy as np

from .bands import soc_derived_spin_splittings
from .basis import idx_A_dn, idx_A_up, idx_B_dn, idx_B_up, state_labels_and_spin
from .config import ModelConfig
from .laser import laser_field
from .simulation import SimulationResult


def col(data: np.ndarray, keys: list[str], name: str) -> np.ndarray:
    return data[:, keys.index(name)]


def maybe_delta(y: np.ndarray, mode: str) -> np.ndarray:
    return y - y[0] if mode == "delta" else y


def choose_indices(n: int, max_points: int) -> np.ndarray:
    if max_points <= 0 or n <= max_points:
        return np.arange(n)
    stride = int(np.ceil(n / max_points))
    return np.arange(0, n, stride)


def _savefig(fig: plt.Figure, path: str | Path) -> None:
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_state_occupation_comparison(result: SimulationResult) -> None:
    """Write the state-resolved level plot and CSV data."""
    config = result.config
    energies = result.diagnostics["energies"]
    assert isinstance(energies, np.ndarray)
    rho_snapshots = result.diagnostics["rho_snapshots"]
    compare_indices = result.diagnostics["compare_indices"]
    compare_times_actual = result.diagnostics["compare_times_actual"]
    assert isinstance(rho_snapshots, dict)
    idx_ref, idx1, idx2 = compare_indices  # type: ignore[misc]
    t_ref, t1, t2 = compare_times_actual  # type: ignore[misc]

    rho_ref = rho_snapshots[idx_ref]
    rho1 = rho_snapshots[idx1]
    rho2 = rho_snapshots[idx2]
    occ_ref = np.real(np.diag(rho_ref))
    occ1 = np.real(np.diag(rho1))
    occ2 = np.real(np.diag(rho2))
    delta1 = occ1 - occ_ref
    delta2 = occ2 - occ_ref

    N = config.N
    _, spin = state_labels_and_spin(N)
    group_x = np.zeros(4 * N)
    for i in range(4 * N):
        if i < N:
            group_x[i] = 0.0
        elif i < 2 * N:
            group_x[i] = 1.0
        elif i < 3 * N:
            group_x[i] = 2.0
        else:
            group_x[i] = 3.0

    local_offsets = np.zeros(4 * N)
    for base in [0, N, 2 * N, 3 * N]:
        for local in range(N):
            local_offsets[base + local] = (local - (N - 1) / 2.0) * config.level_x_jitter

    x_center = group_x + local_offsets
    half_len = config.level_half_length

    cmap = plt.get_cmap(config.delta_colormap)
    all_delta = np.concatenate([delta1, delta2])
    abs_delta = np.abs(all_delta)
    nonzero = abs_delta[abs_delta > 0.0]
    if config.delta_color_scale > 0.0:
        vmax = config.delta_color_scale
    elif nonzero.size:
        vmax = max(float(np.percentile(nonzero, config.delta_color_percentile)), 1.0e-12)
    else:
        vmax = 1.0

    if config.delta_color_norm == "linear":
        norm: mcolors.Normalize = mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    else:
        norm = mcolors.SymLogNorm(
            linthresh=max(config.delta_color_linthresh_fraction * vmax, 1.0e-12),
            vmin=-vmax,
            vmax=vmax,
            base=10.0,
        )

    def draw(ax: plt.Axes, delta: np.ndarray, title: str) -> None:
        max_abs_delta = float(np.max(np.abs(delta))) if len(delta) else 0.0
        for i, (E, dn) in enumerate(zip(energies, delta, strict=True)):
            ax.hlines(
                E,
                x_center[i] - half_len,
                x_center[i] + half_len,
                color=cmap(norm(np.clip(dn, -vmax, vmax))),
                linewidth=config.level_linewidth,
                alpha=config.level_alpha,
            )
        ax.set_title(f"{title}\nmax |Δn|={max_abs_delta:.3g}")
        ax.set_xlim(-0.55, 3.55)
        ax.set_xticks([0, 1, 2, 3])
        ax.set_xticklabels(["A up", "A down", "B up", "B down"])
        ax.set_ylabel("energy / eV")
        ax.grid(axis="y", linewidth=0.4, alpha=0.35)

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.6), sharey=True, constrained_layout=True)
    draw(axes[0], delta1, f"t = {t1:.2f} fs relative to pulse end {t_ref:.2f} fs")
    draw(axes[1], delta2, f"t = {t2:.2f} fs relative to pulse end {t_ref:.2f} fs")
    axes[1].set_ylabel("")
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes, shrink=0.88, pad=0.02)
    cbar.set_label(rf"$\Delta n_i$, clipped at $\pm${vmax:.3g}")
    fig.suptitle(
        "State-resolved occupation change relative to laser pulse end\n"
        "red = increased, blue = decreased; chain model: intramaterial SOC + spin-conserving interlayer transfer",
        fontsize=11,
    )
    _savefig(fig, f"{config.output_prefix}_state_occupation_change_from_pulse_end_levels.png")

    x = np.arange(4 * N)
    out = np.column_stack([x, spin, energies, occ_ref, occ1, occ2, delta1, delta2, group_x])
    header = (
        "state_index,spin(+1_up_-1_down),energy_eV,"
        f"occupation_ref_t_{t_ref:.6f}_fs,"
        f"occupation_t1_{t1:.6f}_fs,"
        f"occupation_t2_{t2:.6f}_fs,"
        "delta_t1_minus_ref,delta_t2_minus_ref,"
        "group_x(0_Aup_1_Adn_2_Bup_3_Bdn)"
    )
    np.savetxt(
        f"{config.output_prefix}_state_occupation_change_from_pulse_end_levels.csv",
        out,
        delimiter=",",
        header=header,
        comments="",
    )


def plot_all(result: SimulationResult) -> None:
    """Write all standard PNG and CSV outputs."""
    config = result.config
    times = result.times
    data = result.data
    keys = result.keys
    ind = choose_indices(len(times), config.max_plot_points)
    t = times[ind]

    def y(name: str) -> np.ndarray:
        return maybe_delta(col(data, keys, name), config.plot_mode)[ind]

    ylabel = "change in occupation" if config.plot_mode == "delta" else "occupation"

    def mark(ax: plt.Axes) -> None:
        ax.axvline(config.pulse_duration, linestyle=":", linewidth=1.0, label="pulse end")

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    for name, label in [("A_up", "A up"), ("A_dn", "A down"), ("B_up", "B up"), ("B_dn", "B down")]:
        ax.plot(t, y(name), label=label)
    mark(ax)
    ax.set_xlabel("time / fs")
    ax.set_ylabel(ylabel)
    ax.set_title(f"Projected material/spin occupation ({config.plot_mode})")
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    _savefig(fig, f"{config.output_prefix}_projected_material_spin.png")

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    for name, label in [
        ("A_v_up", "A VB up"),
        ("A_c_up", "A CB up"),
        ("A_c_dn", "A CB down"),
        ("B_c_dn", "B CB down"),
        ("B_v_dn", "B VB down"),
        ("B_c_up", "B CB up"),
    ]:
        ax.plot(t, y(name), label=label)
    mark(ax)
    ax.set_xlabel("time / fs")
    ax.set_ylabel(ylabel)
    ax.set_title("Pathway-resolved projected occupations")
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    _savefig(fig, f"{config.output_prefix}_pathway_projected_occupations.png")

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    ax.plot(t, y("spin_up"), label="total spin up")
    ax.plot(t, y("spin_dn"), label="total spin down")
    mark(ax)
    ax.set_xlabel("time / fs")
    ax.set_ylabel(ylabel)
    ax.set_title(f"Projected spin occupation ({config.plot_mode})")
    ax.legend(frameon=False)
    fig.tight_layout()
    _savefig(fig, f"{config.output_prefix}_projected_spin.png")

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    ax.plot(t, y("moment"), label="M = N_up - N_down")
    mark(ax)
    ax.set_xlabel("time / fs")
    ax.set_ylabel("change in magnetic moment / mu_B" if config.plot_mode == "delta" else "magnetic moment / mu_B")
    ax.set_title(f"Projected magnetic moment ({config.plot_mode})")
    ax.legend(frameon=False)
    fig.tight_layout()
    _savefig(fig, f"{config.output_prefix}_projected_magnetic_moment.png")

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    ax.plot(t, y("valence"), label="diabatic valence")
    ax.plot(t, y("conduction"), label="diabatic conduction")
    ax.plot(t, y("eig_occ_low"), "--", label="static-eigen low subspace")
    ax.plot(t, y("eig_occ_high"), "--", label="static-eigen high subspace")
    mark(ax)
    laser_waveform = np.array([laser_field(tt, config) for tt in times])
    ax2 = ax.twinx()
    ax2.plot(times[ind], laser_waveform[ind], ":", linewidth=1.0, alpha=0.7, label="laser field")
    ax2.set_ylabel("laser field F(t)")
    ax.set_xlabel("time / fs")
    ax.set_ylabel(ylabel)
    ax.set_title(f"Projection vs static-eigenstate occupation ({config.plot_mode})")
    ax.legend(frameon=False, loc="best")
    fig.tight_layout()
    _savefig(fig, f"{config.output_prefix}_projection_vs_eigen_occupation.png")

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    ax.plot(t, col(data, keys, "interlayer_rate")[ind], label="spin-conserving interlayer rate")
    ax.plot(t, col(data, keys, "intra_rate")[ind], label="intra c→v rate")
    ax.plot(t, col(data, keys, "interlayer_cumulative")[ind], label="cumulative interlayer")
    ax.plot(t, col(data, keys, "intra_cumulative")[ind], label="cumulative intra c→v")
    mark(ax)
    ax.set_xlabel("time / fs")
    ax.set_ylabel("rate / cumulative count")
    ax.set_title("Post-pulse interlayer/intramaterial diagnostics")
    ax.legend(frameon=False)
    fig.tight_layout()
    _savefig(fig, f"{config.output_prefix}_relaxation_diagnostics.png")

    np.savetxt(
        f"{config.output_prefix}_observables.csv",
        np.column_stack([times, data]),
        delimiter=",",
        header="time_fs," + ",".join(keys),
        comments="",
    )

    plot_state_occupation_comparison(result)


def print_summary(result: SimulationResult) -> None:
    """Print concise numerical diagnostics for a run."""
    config = result.config
    energies = result.diagnostics["energies"]
    assert isinstance(energies, np.ndarray)
    N = config.N
    nv = N // 2
    split_A, split_B = soc_derived_spin_splittings(config)

    print("Model summary")
    print("-------------")
    print("A/B bands are non-matching by construction.")
    print("Mechanism: A_v up -> A_c up -> A_c down -> B_c down -> B_v down")
    print(f"A: gap={config.gap_A}, offset={config.offset_A}, bw_v={config.bandwidth_v_A}, bw_c={config.bandwidth_c_A}")
    print(f"B: gap={config.gap_B}, offset={config.offset_B}, bw_v={config.bandwidth_v_B}, bw_c={config.bandwidth_c_B}")
    print(f"Material SOC: lambda_soc_A={config.lambda_soc_A}, lambda_soc_B={config.lambda_soc_B}")
    print(f"SOC-derived diagonal spin splitting: split_A={split_A:.6g} eV; split_B={split_B:.6g} eV")
    print(f"SOC mixing: A_CB={config.soc_mix_cb_A}, B_CB={config.soc_mix_cb_B}, A_VB={config.soc_mix_vb_A}, B_VB={config.soc_mix_vb_B}")
    print(f"Interlayer spin-conserving hopping: tAB_cc={config.tAB}, tAB_vv={config.tAB_vv}")

    A_vbm_up = idx_A_up(nv - 1, N)
    A_vbm_dn = idx_A_dn(nv - 1, N)
    A_cbm_up = idx_A_up(nv, N)
    A_cbm_dn = idx_A_dn(nv, N)
    B_vbm_up = idx_B_up(nv - 1, N)
    B_vbm_dn = idx_B_dn(nv - 1, N)
    B_cbm_up = idx_B_up(nv, N)
    B_cbm_dn = idx_B_dn(nv, N)
    print("Band-edge alignment and spin ordering:")
    for label, idx in [
        ("A VBM up", A_vbm_up),
        ("A VBM dn", A_vbm_dn),
        ("A CBM up", A_cbm_up),
        ("A CBM dn", A_cbm_dn),
        ("B VBM up", B_vbm_up),
        ("B VBM dn", B_vbm_dn),
        ("B CBM up", B_cbm_up),
        ("B CBM dn", B_cbm_dn),
    ]:
        print(f"  {label} = {energies[idx]:.6g} eV")
    print("Band-edge checks:")
    print(f"  A CBM dn - A CBM up = {energies[A_cbm_dn] - energies[A_cbm_up]:.6g} eV")
    print(f"  B CBM dn - B CBM up = {energies[B_cbm_dn] - energies[B_cbm_up]:.6g} eV")
    print(f"  min(B CBM) - max(A CBM) = {min(energies[B_cbm_up], energies[B_cbm_dn]) - max(energies[A_cbm_up], energies[A_cbm_dn]):.6g} eV")
    print(f"  min(B VBM) - max(A VBM) = {min(energies[B_vbm_up], energies[B_vbm_dn]) - max(energies[A_vbm_up], energies[A_vbm_dn]):.6g} eV")

    print(f"number of spin-conserving interlayer transfer channels = {len(result.diagnostics['interlayer_channels'])}")
    print(f"number of intramaterial c->v channels = {len(result.diagnostics['intra_channels'])}")
    print(f"W_intra_A = {config.W_intra_A}; W_intra_B = {config.W_intra_B}")
    intra = result.diagnostics["intra_channels"]
    if intra:
        rates = np.asarray([float(ch["rate"]) for ch in intra])
        print("Intramaterial c->v channel-rate diagnostics:")
        print(f"  min rate = {rates.min():.6g} 1/fs")
        print(f"  median rate = {np.median(rates):.6g} 1/fs")
        print(f"  max rate = {rates.max():.6g} 1/fs")

    idx_ref = result.diagnostics["compare_indices"][0]
    rho_ref = result.diagnostics["rho_snapshots"][idx_ref]
    occ_ref = np.real(np.diag(rho_ref))
    A_val = np.sum(occ_ref[0:nv]) + np.sum(occ_ref[N:N + nv])
    A_cond = np.sum(occ_ref[nv:N]) + np.sum(occ_ref[N + nv:2 * N])
    B_val = np.sum(occ_ref[2 * N:2 * N + nv]) + np.sum(occ_ref[3 * N:3 * N + nv])
    B_cond = np.sum(occ_ref[2 * N + nv:3 * N]) + np.sum(occ_ref[3 * N + nv:4 * N])
    print("Pulse-end projected carrier diagnostics:")
    print(f"  A valence holes = {2 * nv - A_val:.6g}; A conduction electrons = {A_cond:.6g}")
    print(f"  B valence holes = {2 * nv - B_val:.6g}; B conduction electrons = {B_cond:.6g}")
