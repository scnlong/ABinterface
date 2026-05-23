# A/B Interface Chain Model

This repository contains a modular Python implementation of a toy density-matrix
model for short-time laser-driven carrier and spin redistribution at a
non-matching A/B material interface.

The current default mechanism is

```text
A_v up -> A_c up -> A_c down -> B_c down -> B_v down
```

The model intentionally separates:

1. material-internal SOC-derived diagonal splitting;
2. material-internal SOC up/down mixing;
3. spin-conserving interlayer hopping;
4. post-pulse intramaterial `c -> v` relaxation.

The earlier direct interface-SOC spin-flip channel
`A_c up <-> B_v down` is no longer part of the default model.  The impact
excitation branch has also been removed from the main code because it was too
phenomenological for the present short-time chain mechanism.

## Package layout

```text
src/abinterface/
  basis.py          basis indexing and projections
  bands.py          non-matching A/B no-SOC energies plus SOC-derived splitting
  laser.py          laser pulse and optical matrix elements
  hamiltonian.py    material SOC, interlayer hopping, and laser Hamiltonian
  density.py        density-matrix initialization and unitary propagation
  relaxation.py     post-pulse interlayer and intramaterial rate channels
  observables.py    projected observables
  simulation.py     high-level propagation driver
  plotting.py       plots, CSV output, and textual diagnostics
  cli.py            command-line interface
  gui.py            Tkinter desktop GUI
```

## Installation

```bash
pip install -e .
```

or run without installation from the repository root:

```bash
PYTHONPATH=src python -m abinterface --help
```

## Example CLI run

```bash
PYTHONPATH=src python -m abinterface \
  --N 12 \
  --pulse-duration 20 \
  --t-final 70 \
  --dt 0.02 \
  --carrier full \
  --omega-eV 2.0 \
  --lambda-soc-A 0.05 \
  --lambda-soc-B 0.05 \
  --soc-mix-cb-A 0.02 \
  --soc-mix-cb-B 0.02 \
  --tAB 0.08 \
  --W-downhill 0.01 \
  --W-intra 0.03 \
  --compare-time-1 22 \
  --compare-time-2 50 \
  --delta-color-scale 0.08 \
  --delta-color-norm linear
```

## Desktop GUI

After installation:

```bash
abinterface-gui
```

Without installation:

```bash
PYTHONPATH=src python -m abinterface.gui
```

On Linux, install Tk support if needed:

```bash
sudo apt install python3-tk
```

The GUI exposes the same model parameters as the CLI.  Numeric fields can be
edited manually; common parameters also have sliders.  Click **Run simulation**
to generate PNG and CSV outputs in the selected output directory.

## Physical model

The one-particle basis is ordered as

```text
A_up, A_down, B_up, B_down
```

with `N` states in each block.  The first `N/2` are valence-like and the second
`N/2` are conduction-like.

The time-dependent Hamiltonian is

```text
H(t) = H_static + H_laser(t)
```

where

```text
H_static = H_bands + H_SOC_mix + H_interlayer
```

`H_bands` is built from no-SOC gaps, offsets, and bandwidths.  The diagonal SOC
splitting is derived from `lambda_soc_A` and `lambda_soc_B`; no independent
spin-splitting parameters are exposed.

`H_SOC_mix` contains material-internal up/down mixing, especially in the
conduction bands.  This term enables the coherent step

```text
A_c up -> A_c down
```

`H_interlayer` contains spin-conserving interlayer hopping, primarily

```text
A_c,s <-> B_c,s
```

controlled by `tAB`.

After the pulse, phenomenological rate channels model:

1. spin-conserving interlayer downhill transfer;
2. intramaterial spin-conserving `c -> v` relaxation.

Rate updates use exponential probabilities `p = 1 - exp(-R*dt)`, so there is no
user-facing collision-fraction parameter.

## Outputs

For the output prefix `interface_chain_model`, the standard outputs are:

```text
*_projected_material_spin.png
*_pathway_projected_occupations.png
*_projected_spin.png
*_projected_magnetic_moment.png
*_projection_vs_eigen_occupation.png
*_relaxation_diagnostics.png
*_observables.csv
*_state_occupation_change_from_pulse_end_levels.png
*_state_occupation_change_from_pulse_end_levels.csv
```

`*_pathway_projected_occupations.png` is the most direct check of the proposed
chain mechanism.

## Tests

```bash
pip install -e .[dev]
pytest
```


## GUI layout update

The GUI uses a tabbed layout so that parameters are grouped by model component:

```text
Bands
SOC + Interlayer
Laser
Rates + Time
Plotting
```

Each tab uses a compact two-column arrangement.  The top bar contains output
directory selection, **Run simulation**, **Reset**, and **Open output**.  The
**Reset** button restores all parameter widgets to `ModelConfig` defaults.
