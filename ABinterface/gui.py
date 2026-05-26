"""Tkinter desktop GUI for the coherent A/B interface model.

This version uses a tabbed, two-column layout rather than one long vertical
scrolling form.  It is easier to use on normal laptop screens and keeps the
main controls visible at the top.
"""

import contextlib
import io
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .config import ModelConfig
from .plotting import plot_all, print_summary
from .simulation import run_simulation


class ParameterGrid(ttk.Frame):
    """Compact two-column parameter grid.

    Each parameter is displayed as:
        label | entry/combobox/checkbutton | optional slider | short hint

    Parameters are automatically split between two vertical columns so that a
    group usually fits on a single screen without scrolling.
    """

    def __init__(self, parent: tk.Widget, specs: list[tuple[str, object, str, str, list[str] | None, tuple[float, float] | None]]) -> None:
        super().__init__(parent, padding=10)
        self.vars: dict[str, tk.Variable] = {}
        self.specs = specs
        self._build()

    def _build(self) -> None:
        n_left = (len(self.specs) + 1) // 2

        left = ttk.Frame(self)
        right = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        right.grid(row=0, column=1, sticky="nsew", padx=(14, 0))
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        for idx, spec in enumerate(self.specs):
            frame = left if idx < n_left else right
            row = idx if idx < n_left else idx - n_left
            var = self._add_param(frame, row, *spec)
            self.vars[spec[0]] = var

    def _add_param(
        self,
        parent: ttk.Frame,
        row: int,
        name: str,
        default: object,
        help_text: str,
        kind: str,
        choices: list[str] | None,
        slider: tuple[float, float] | None,
    ) -> tk.Variable:
        label = ttk.Label(parent, text=name, width=26)
        label.grid(row=row, column=0, sticky="w", padx=(0, 5), pady=3)

        if kind == "bool":
            var = tk.BooleanVar(value=bool(default))
            widget = ttk.Checkbutton(parent, variable=var)
            widget.grid(row=row, column=1, sticky="w", padx=(4, 4), pady=3)
        elif kind == "choice":
            var = tk.StringVar(value=str(default))
            widget = ttk.Combobox(parent, textvariable=var, values=choices or [], state="readonly", width=12)
            widget.grid(row=row, column=1, sticky="ew", padx=(4, 4), pady=3)
        else:
            var = tk.StringVar(value="" if default is None else str(default))
            widget = ttk.Entry(parent, textvariable=var, width=13)
            widget.grid(row=row, column=1, sticky="ew", padx=(4, 4), pady=3)

            if slider is not None and default is not None:
                vmin, vmax = slider
                scale_var = tk.DoubleVar(value=float(default))

                def scale_to_entry(_value: str) -> None:
                    var.set(f"{scale_var.get():.6g}")

                def entry_to_scale(*_args: object) -> None:
                    with contextlib.suppress(ValueError):
                        v = float(var.get())
                        if vmin <= v <= vmax:
                            scale_var.set(v)

                scale = ttk.Scale(parent, from_=vmin, to=vmax, variable=scale_var, command=scale_to_entry)
                scale.grid(row=row, column=2, sticky="ew", padx=(4, 4), pady=3)
                var.trace_add("write", entry_to_scale)

        hint = ttk.Label(parent, text=help_text, foreground="#555555", wraplength=300)
        hint.grid(row=row, column=3, sticky="w", padx=(5, 0), pady=3)
        parent.columnconfigure(1, weight=0)
        parent.columnconfigure(2, weight=1)
        return var


class ABInterfaceGUI(tk.Tk):
    """Main desktop GUI."""

    def __init__(self) -> None:
        super().__init__()
        self.title("A/B Interface Chain Model")
        self.geometry("1280x760")
        self.minsize(1050, 620)

        self.defaults = ModelConfig()
        self.vars: dict[str, tk.Variable] = {}
        self.panels: dict[str, ParameterGrid] = {}
        self.queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "ABinterface_output"))

        self._build()
        self.after(100, self._poll)

    def _build(self) -> None:
        # Top bar: always visible.
        top = ttk.Frame(self, padding=(8, 8, 8, 4))
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Output directory:").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.output_dir).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(top, text="Browse", command=self._browse).grid(row=0, column=2, padx=4)

        self.run_button = ttk.Button(top, text="Run simulation", command=self._run_clicked)
        self.run_button.grid(row=0, column=3, padx=4)

        self.reset_button = ttk.Button(top, text="Reset", command=self._reset_defaults)
        self.reset_button.grid(row=0, column=4, padx=4)

        ttk.Button(top, text="Open output", command=self._open_output).grid(row=0, column=5, padx=4)

        # Main body: tabs on top, log on bottom.  This is more compact than a
        # long vertical form and avoids scrolling in most screen sizes.
        main = ttk.PanedWindow(self, orient="vertical")
        main.grid(row=1, column=0, sticky="nsew")
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(main)
        main.add(self.notebook, weight=4)

        log_frame = ttk.Frame(main, padding=(8, 4, 8, 8))
        main.add(log_frame, weight=2)
        log_frame.rowconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)

        ttk.Label(log_frame, text="Run log / diagnostics").grid(row=0, column=0, sticky="w")
        self.log = tk.Text(log_frame, wrap="word", height=10)
        self.log.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scroll.set)

        self._build_tabs()

    def _build_tabs(self) -> None:
        d = self.defaults

        tab_specs: list[tuple[str, list[tuple[str, object, str, str, list[str] | None, tuple[float, float] | None]]]] = [
            ("Bands", [
                ("N", d.N, "Bands per material/spin; must be even.", "int", None, (2, 40)),
                ("gap_A", d.gap_A, "No-SOC A gap in eV.", "float", None, (0.1, 4.0)),
                ("gap_B", d.gap_B, "No-SOC B gap in eV.", "float", None, (0.1, 4.0)),
                ("offset_A", d.offset_A, "Rigid A offset in eV.", "float", None, (-2.0, 2.0)),
                ("offset_B", d.offset_B, "Rigid B offset in eV.", "float", None, (-2.0, 2.0)),
                ("bandwidth_v_A", d.bandwidth_v_A, "A valence bandwidth.", "float", None, (0.0, 3.0)),
                ("bandwidth_c_A", d.bandwidth_c_A, "A conduction bandwidth.", "float", None, (0.0, 3.0)),
                ("bandwidth_v_B", d.bandwidth_v_B, "B valence bandwidth.", "float", None, (0.0, 3.0)),
                ("bandwidth_c_B", d.bandwidth_c_B, "B conduction bandwidth.", "float", None, (0.0, 3.0)),
            ]),
            ("SOC + Interlayer", [
                ("lambda_soc_A", d.lambda_soc_A, "Signed SOC splitting for A. Negative: spin-down above spin-up.", "float", None, (-0.5, 0.5)),
                ("lambda_soc_B", d.lambda_soc_B, "Signed SOC splitting for B. Negative: spin-down above spin-up.", "float", None, (-0.5, 0.5)),
                ("soc_mix_cb_A", d.soc_mix_cb_A, "A CB up/down SOC mixing in eV.", "float", None, (0.0, 0.2)),
                ("soc_mix_cb_B", d.soc_mix_cb_B, "B CB up/down SOC mixing in eV.", "float", None, (0.0, 0.2)),
                ("soc_mix_vb_A", d.soc_mix_vb_A, "A VB up/down SOC mixing in eV.", "float", None, (0.0, 0.1)),
                ("soc_mix_vb_B", d.soc_mix_vb_B, "B VB up/down SOC mixing in eV.", "float", None, (0.0, 0.1)),
                ("tAB", d.tAB, "A_c,s <-> B_c,s hopping in eV.", "float", None, (0.0, 0.5)),
                ("tAB_vv", d.tAB_vv, "Optional A_v,s <-> B_v,s hopping in eV.", "float", None, (0.0, 0.5)),
                ("interface_band_width", d.interface_band_width, "Band-index width for interlayer hopping.", "float", None, (0.1, 20.0)),
                ("hybrid_energy_width", d.hybrid_energy_width, "Energy mismatch width for interlayer hopping.", "float", None, (0.0, 10.0)),
            ]),
            ("Laser", [
                ("A0", d.A0, "Laser amplitude.", "float", None, (0.0, 2.0)),
                ("omega_eV", d.omega_eV, "Photon energy in eV.", "float", None, (0.1, 5.0)),
                ("pulse_duration", d.pulse_duration, "Pulse duration in fs.", "float", None, (1.0, 100.0)),
                ("carrier", d.carrier, "Full carrier or RWA envelope.", "choice", ["full", "rwa"], None),
                ("dA0", d.dA0, "Optical dipole scale for A.", "float", None, (0.0, 5.0)),
                ("dB0", d.dB0, "Optical dipole scale for B.", "float", None, (0.0, 5.0)),
                ("optical_energy_width", d.optical_energy_width, "Fallback optical width.", "float", None, (0.0, 10.0)),
                ("optical_energy_width_A", d.optical_energy_width_A, "A-specific width; blank means fallback.", "float", None, (0.0, 10.0)),
                ("optical_energy_width_B", d.optical_energy_width_B, "B-specific width; blank means fallback.", "float", None, (0.0, 10.0)),
                ("band_overlap_width", d.band_overlap_width, "Band-edge overlap width for optical couplings.", "float", None, (0.1, 20.0)),
            ]),
            ("Time", [
                ("t_final", d.t_final, "Final time in fs.", "float", None, (1.0, 300.0)),
                ("dt", d.dt, "Time step in fs.", "float", None, (0.001, 0.2)),
                ("compare_time_ref", d.compare_time_ref, "Reference time; blank means pulse end.", "float", None, (0.0, 300.0)),
                ("compare_time_1", d.compare_time_1, "Left-panel comparison time.", "float", None, (0.0, 300.0)),
                ("compare_time_2", d.compare_time_2, "Right-panel comparison time.", "float", None, (0.0, 300.0)),
            ]),
            ("Plotting", [
                ("plot_mode", d.plot_mode, "delta or absolute.", "choice", ["delta", "absolute"], None),
                ("max_plot_points", d.max_plot_points, "Maximum plotted points.", "int", None, (100, 50000)),
                ("delta_color_scale", d.delta_color_scale, "Manual Delta-n color scale; <=0 auto.", "float", None, (0.0, 1.0)),
                ("delta_color_norm", d.delta_color_norm, "Color normalization.", "choice", ["linear", "symlog"], None),
                ("delta_color_percentile", d.delta_color_percentile, "Auto color percentile.", "float", None, (1.0, 100.0)),
                ("delta_color_linthresh_fraction", d.delta_color_linthresh_fraction, "SymLog linear threshold fraction.", "float", None, (0.001, 1.0)),
                ("delta_colormap", d.delta_colormap, "Colormap name.", "choice", ["bwr", "seismic", "coolwarm", "RdBu_r", "PiYG"], None),
                ("level_half_length", d.level_half_length, "Half-length of state-level lines.", "float", None, (0.05, 1.0)),
                ("level_x_jitter", d.level_x_jitter, "Horizontal jitter inside columns.", "float", None, (0.0, 0.1)),
                ("level_linewidth", d.level_linewidth, "State-level line width.", "float", None, (0.1, 8.0)),
                ("level_alpha", d.level_alpha, "State-level alpha.", "float", None, (0.05, 1.0)),
            ]),
        ]

        for title, specs in tab_specs:
            panel = ParameterGrid(self.notebook, specs)
            self.notebook.add(panel, text=title)
            self.panels[title] = panel
            self.vars.update(panel.vars)

    def _reset_defaults(self) -> None:
        """Reset all GUI controls to ModelConfig defaults."""
        self.defaults = ModelConfig()
        old_output = str(Path.cwd() / "ABinterface_gui_output")
        self.output_dir.set(old_output)

        for panel in self.panels.values():
            for name, default, *_rest in panel.specs:
                var = panel.vars[name]
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(default))
                else:
                    var.set("" if default is None else str(default))

        self._append("Parameters reset to defaults.\n")

    def _parse_float(self, name: str) -> float | None:
        v = str(self.vars[name].get()).strip()
        if v == "":
            return None
        return float(v)

    def _parse_int(self, name: str) -> int:
        return int(float(str(self.vars[name].get()).strip()))

    def _make_config(self) -> ModelConfig:
        return ModelConfig(
            N=self._parse_int("N"),
            gap_A=float(self._parse_float("gap_A")),
            gap_B=float(self._parse_float("gap_B")),
            offset_A=float(self._parse_float("offset_A")),
            offset_B=float(self._parse_float("offset_B")),
            bandwidth_v_A=float(self._parse_float("bandwidth_v_A")),
            bandwidth_c_A=float(self._parse_float("bandwidth_c_A")),
            bandwidth_v_B=float(self._parse_float("bandwidth_v_B")),
            bandwidth_c_B=float(self._parse_float("bandwidth_c_B")),
            lambda_soc_A=float(self._parse_float("lambda_soc_A")),
            lambda_soc_B=float(self._parse_float("lambda_soc_B")),
            soc_mix_cb_A=float(self._parse_float("soc_mix_cb_A")),
            soc_mix_cb_B=float(self._parse_float("soc_mix_cb_B")),
            soc_mix_vb_A=float(self._parse_float("soc_mix_vb_A")),
            soc_mix_vb_B=float(self._parse_float("soc_mix_vb_B")),
            tAB=float(self._parse_float("tAB")),
            tAB_vv=float(self._parse_float("tAB_vv")),
            interface_band_width=float(self._parse_float("interface_band_width")),
            hybrid_energy_width=float(self._parse_float("hybrid_energy_width")),
            A0=float(self._parse_float("A0")),
            omega_eV=float(self._parse_float("omega_eV")),
            pulse_duration=float(self._parse_float("pulse_duration")),
            carrier=str(self.vars["carrier"].get()),  # type: ignore[arg-type]
            dA0=float(self._parse_float("dA0")),
            dB0=float(self._parse_float("dB0")),
            optical_energy_width=float(self._parse_float("optical_energy_width")),
            optical_energy_width_A=self._parse_float("optical_energy_width_A"),
            optical_energy_width_B=self._parse_float("optical_energy_width_B"),
            band_overlap_width=float(self._parse_float("band_overlap_width")),
            t_final=float(self._parse_float("t_final")),
            dt=float(self._parse_float("dt")),
            compare_time_ref=self._parse_float("compare_time_ref"),
            compare_time_1=self._parse_float("compare_time_1"),
            compare_time_2=self._parse_float("compare_time_2"),
            plot_mode=str(self.vars["plot_mode"].get()),  # type: ignore[arg-type]
            max_plot_points=self._parse_int("max_plot_points"),
            level_half_length=float(self._parse_float("level_half_length")),
            level_x_jitter=float(self._parse_float("level_x_jitter")),
            level_linewidth=float(self._parse_float("level_linewidth")),
            level_alpha=float(self._parse_float("level_alpha")),
            delta_color_scale=float(self._parse_float("delta_color_scale")),
            delta_color_norm=str(self.vars["delta_color_norm"].get()),  # type: ignore[arg-type]
            delta_color_percentile=float(self._parse_float("delta_color_percentile")),
            delta_color_linthresh_fraction=float(self._parse_float("delta_color_linthresh_fraction")),
            delta_colormap=str(self.vars["delta_colormap"].get()),
            output_prefix=str(Path(self.output_dir.get()).expanduser() / "ABinterface"),
        ).resolved()

    def _browse(self) -> None:
        directory = filedialog.askdirectory(initialdir=self.output_dir.get() or str(Path.cwd()))
        if directory:
            self.output_dir.set(directory)

    def _open_output(self) -> None:
        path = Path(self.output_dir.get()).expanduser()
        if not path.exists():
            messagebox.showinfo("Output directory", "The output directory does not exist yet.")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror("Open output failed", str(exc))

    def _run_clicked(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Simulation running", "A simulation is already running.")
            return
        try:
            cfg = self._make_config()
        except Exception as exc:
            messagebox.showerror("Invalid parameters", str(exc))
            return

        Path(self.output_dir.get()).expanduser().mkdir(parents=True, exist_ok=True)
        self.log.delete("1.0", "end")
        self._append("Starting simulation...\n")
        self._append(f"Output directory: {self.output_dir.get()}\n")
        self.run_button.configure(state="disabled")
        self.reset_button.configure(state="disabled")
        self.worker = threading.Thread(target=self._worker_run, args=(cfg,), daemon=True)
        self.worker.start()

    def _worker_run(self, cfg: ModelConfig) -> None:
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                result = run_simulation(cfg)
                print_summary(result)
                plot_all(result)
            self.queue.put(buf.getvalue())
            self.queue.put("\nRun finished successfully.\n")
        except Exception as exc:
            self.queue.put(f"\nERROR: {exc}\n")
        finally:
            self.queue.put("__DONE__")

    def _poll(self) -> None:
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg == "__DONE__":
                    self.run_button.configure(state="normal")
                    self.reset_button.configure(state="normal")
                else:
                    self._append(msg)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _append(self, msg: str) -> None:
        self.log.insert("end", msg)
        self.log.see("end")


def main() -> None:
    app = ABInterfaceGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
