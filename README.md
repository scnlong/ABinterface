# A/B Interface Elementary-Channel Model

This repository contains a modular Python implementation of a density-matrix toy
model for short-time laser-driven carrier and spin redistribution at a
non-matching A/B material interface.

The software is intended for qualitative mechanism analysis.  It is not a
first-principles TDDFT, GW, Boltzmann transport, or microscopic scattering code.
The model is useful for testing how elementary optical excitation, material
spin-orbit coupling, spin-conserving interlayer transfer, and phenomenological
post-pulse relaxation combine to produce projected occupation changes.

## Important modeling clarification

The code **does not hard-code a single sequential trajectory** such as

```text
A_v up -> A_c up -> A_c down -> B_c down -> B_v down
```

Instead, it implements a set of elementary optical, SOC-mixing, interlayer, and
relaxation channels.  Under suitable band alignment and parameter choices, the
combined density-matrix dynamics can display a population redistribution pattern
that is naturally interpreted as the effective chain above.

This distinction matters.  The propagated object is a one-particle density
matrix, not a classical tagged electron.  Therefore the software directly
computes projected occupations and coherences.  Statements such as
`A_v up -> A_c up -> A_c down -> B_c down -> B_v down` should be read as an
**emergent pathway interpretation** of occupation changes, not as an imposed
ordered list of transitions.

The implemented elementary processes are:

1. laser-driven, spin-conserving intramaterial optical excitation
   `A_v s <-> A_c s` and `B_v s <-> B_c s`;
2. material-internal SOC-derived diagonal splitting and coherent up/down mixing
   inside valence and conduction manifolds;
3. spin-conserving interlayer hopping, primarily `A_c s <-> B_c s`, with
   optional `A_v s <-> B_v s` hopping;
4. post-pulse spin-conserving interlayer downhill transfer derived from the
   interlayer hopping matrix;
5. post-pulse spin-conserving intramaterial `c -> v` relaxation.

The earlier direct interface-SOC spin-flip channel `A_c up <-> B_v down` is not
part of the default model.  The impact-excitation branch has also been removed
from the main code because it was too phenomenological for the present
short-time elementary-channel model.

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

You will see an interface similar to:

![](doc/figure/screenshot.png)

Without installation:

```bash
PYTHONPATH=src python -m abinterface.gui
```

On Linux, install Tk support if needed:

```bash
sudo apt install python3-tk
```

The GUI exposes the same model parameters as the CLI.  It uses a tabbed layout:

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

`H_SOC_mix` contains material-internal up/down mixing.  These off-diagonal terms
allow projected occupation and coherence to move between spin-up-like and
spin-down-like components of the same material and band manifold.  They do not
by themselves hard-code a macroscopic pathway.

`H_interlayer` contains spin-conserving interlayer hopping, primarily

```text
A_c,s <-> B_c,s
```

controlled by `tAB`.  Optional valence-valence interlayer hopping can be enabled
with `tAB_vv`.

After the pulse, phenomenological rate channels model:

1. spin-conserving interlayer downhill transfer;
2. intramaterial spin-conserving `c -> v` relaxation.

Rate updates use exponential probabilities `p = 1 - exp(-R*dt)`, so there is no
user-facing collision-fraction parameter.

## Meaning of the filter parameters

Several parameters are not independent physical observables.  They are compact
model filters that determine which elementary channels are strong or weak.

### `interface_band_width`

`interface_band_width` controls the band-index selectivity of spin-conserving
interlayer hopping.  It appears in a Gaussian-like factor comparing the distance
of two states from their relevant band edges.  Small values make interlayer
hopping concentrated between similarly edge-like states, for example CBM-like
states on A and B.  Large values allow more remote conduction or valence states
to couple across the interface.

In short:

```text
interface_band_width = band-index width for A/B interlayer hopping
```

### `hybrid_energy_width`

`hybrid_energy_width` controls how strongly the interlayer hopping is suppressed
when the two coupled A/B states are energetically mismatched.  In the model this
is an energy-space Gaussian factor.  A small value only allows nearly resonant
A/B states to hybridize strongly; a large value makes the interlayer hopping
less sensitive to energy mismatch.

In short:

```text
hybrid_energy_width = energy-mismatch width for A/B interlayer hopping
```

### `band_overlap_width`

`band_overlap_width` controls the band-index selectivity of intramaterial
valence-conduction matrix elements.  It is used for the optical `v <-> c`
couplings and reused in the hierarchy of intramaterial `c -> v` relaxation
matrix elements.  The code measures distance from the VBM and CBM so that
VBM-like states couple most naturally to CBM-like states.

In short:

```text
band_overlap_width = band-index width for intramaterial v-c optical/relaxation matrix elements
```

### `optical_energy_width`

`optical_energy_width` controls the optical resonance window.  A transition
`v -> c` is strongest when `E_c - E_v` is close to the photon energy
`omega_eV`.  The width parameter determines how quickly non-resonant transitions
are suppressed.  Material-specific values can be supplied with
`optical_energy_width_A` and `optical_energy_width_B`; if left blank, they fall
back to `optical_energy_width`.

In short:

```text
optical_energy_width = photon-resonance width for intramaterial optical excitation
```

## Optical matrix-element formula and parameter mapping

The laser term uses material-internal optical couplings of the form

```text
d^X_vc = d^X_0
         exp[-(E_c - E_v - omega_eV)^2 / (2 sigma_opt,X^2)]
         exp[-(d_c - d_v)^2 / (2 band_overlap_width^2)]
```

where `X` is either material `A` or material `B`.

For material `A`,

```text
d^A_0 = dA0
sigma_opt,A = optical_energy_width_A
```

If `optical_energy_width_A` is left blank, it falls back to
`optical_energy_width`.

For material `B`,

```text
d^B_0 = dB0
sigma_opt,B = optical_energy_width_B
```

If `optical_energy_width_B` is left blank, it falls back to
`optical_energy_width`.

The quantities `E_c` and `E_v` are not direct user inputs.  They are generated
from the no-SOC band parameters plus SOC-derived diagonal splitting:

```text
gap_A / gap_B
offset_A / offset_B
bandwidth_c_A / bandwidth_c_B
bandwidth_v_A / bandwidth_v_B
lambda_soc_A / lambda_soc_B
```

For a conduction state, `d_c` is the distance from the CBM in band-index space:

```text
CBM        -> d_c = 0
next CB    -> d_c = 1
next CB    -> d_c = 2
...
```

For a valence state, `d_v` is the distance from the VBM:

```text
VBM        -> d_v = 0
next lower -> d_v = 1
next lower -> d_v = 2
...
```

Thus `band_overlap_width` controls how strongly VBM-like states couple to
CBM-like states and how quickly this coupling falls off for mismatched band-edge
distances.  The optical matrix element is controlled by four distinct
ingredients:

```text
dA0 / dB0                   -> material-dependent optical coupling scale
omega_eV                    -> photon energy
optical_energy_width_*       -> resonance energy window
band_overlap_width           -> band-index overlap window
```

This formula also explains why increasing `dA0` or `dB0` alone may not strongly
increase excitation: the transition must still be sufficiently resonant with
`omega_eV` and sufficiently allowed by the band-index overlap factor.

## Why `W_downhill` is kept separate from `tAB`

`tAB` is the coherent interlayer hopping amplitude in the Hamiltonian.  It
controls static hybridization and coherent A/B mixing.  By itself, however, a
Hamiltonian hopping amplitude does not determine an irreversible post-pulse
downhill transfer rate.  A one-way downhill process also requires an implicit
environment, dephasing channel, phonon bath, electronic scattering phase space,
or some other dissipative mechanism that can absorb the released energy.

For this reason the model keeps a separate phenomenological parameter:

```text
W_downhill
```

`W_downhill` sets the global time scale of bath-assisted interlayer downhill
transfer.  The interlayer hopping matrix still determines the relative strength
of different transfer channels, but `W_downhill` determines how fast the
incoherent transfer proceeds overall.

The current toy-model rate has the form

```text
Gamma_i->j = W_downhill * |<j|H_interlayer|i>|^2 / tAB^2
```

for downhill channels with `E_i > E_j`.  This normalization is intentional.  It
separates two roles:

```text
tAB         -> coherent interlayer hybridization in H_static
W_downhill -> phenomenological irreversible transfer time scale
```

Equivalently, `W_downhill` may be viewed as an effective rate scale that already
absorbs the reference strength of the interlayer hopping and the unknown bath
spectral factor.  This is not a microscopic Fermi-golden-rule calculation.  It
is a controlled toy-model choice that makes it easier to tune coherent mixing
and incoherent downhill transfer separately.

A more microscopic model could instead use a rate proportional to
`|<j|H_interlayer|i>|^2` times an explicit bath spectral density.  That would
require additional physical input not present in this code.


## Parameter summary

| Parameter group | Parameters | Role |
|---|---|---|
| Band structure | `N`, `gap_A/B`, `offset_A/B`, `bandwidth_v_A/B`, `bandwidth_c_A/B` | Define the no-SOC A/B band ladders and band alignment. |
| SOC | `lambda_soc_A/B`, `soc_mix_cb_A/B`, `soc_mix_vb_A/B` | Define diagonal SOC-derived splitting and material-internal up/down mixing. |
| Interlayer hopping | `tAB`, `tAB_vv`, `interface_band_width`, `hybrid_energy_width` | Define spin-conserving A/B hopping and its band-index/energy filters. |
| Laser coupling | `A0`, `omega_eV`, `carrier`, `pulse_duration`, `dA0`, `dB0`, `optical_energy_width_*`, `band_overlap_width` | Define the pulse and intramaterial optical excitation matrix elements. |
| Rate processes | `W_downhill`, `W_intra`, `W_intra_A/B` | Define phenomenological post-pulse transfer and relaxation time scales. |
| Plotting | `compare_time_*`, `delta_color_scale`, `delta_color_norm`, `level_*` | Define output diagnostics and figure appearance. |

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

`*_pathway_projected_occupations.png` should be understood as a diagnostic plot
for selected projected occupations.  It helps evaluate whether the independent
channels produce an emergent chain-like redistribution pattern.  It is not proof
that the code forced a tagged electron to follow a unique trajectory.

## Tests

```bash
pip install -e .[dev]
pytest
```
