# ANSYS CFD interface

This directory holds the **aerodynamic and structural simulation** work that closes the data loop
with the flight-dynamics and control simulation in `../src/`:

```
high-fidelity CFD data  ->  reduced-order control model
```

> **Scope note.** The repository's published results are produced entirely by the MATLAB/Simulink
> side, using the analytic ground-effect factor described below. **No CFD calculation has been
> carried out yet and no CFD result is claimed anywhere in this repository.** What is provided
> here is the directory layout, the data-interface definition and the templates needed to run the
> CFD study later. `src/wig_ge_fit_cfd.m` can read the resulting data and recalibrate the
> ground-effect parameters.

---

## 1. Status

| Item | Status | Note |
|---|---|---|
| Directory layout | done | `data/`, `cfd/`, `docs/` |
| Data interface | **working** | `src/wig_ge_fit_cfd.m` reads `data/ge_kappa.csv` |
| Data templates | provided | `data/ge_kappa_template.csv`, `data/aero_table_template.csv` |
| CFD cases | **not started** | requires an ANSYS Fluent/CFX licence and meshing resources |
| CFD reports, mesh-independence study, wind-tunnel comparison | **not started** | `cfd/` and `docs/` currently contain only `.gitkeep` |

### About `ge_kappa_template.csv` — read this before using it

`data/ge_kappa_template.csv` was **generated from the analytic ground-effect factor currently used
by the nominal model** (`A = 0.0641`, `n = 1.4622`), not measured or computed. It exists so that
the interface can be exercised and regression-tested end to end; running

```matlab
cd ../src
[A, n, R2] = wig_ge_fit_cfd('../ansys/data/ge_kappa_template.csv');
```

returns `A ≈ 0.06423`, `n ≈ 1.45030`, `R² ≈ 0.99874`, i.e. it recovers the model it was made
from. **This is a round-trip self-test of the fitting code, not a validation of the aerodynamic
model.** Replacing the file with real CFD data is precisely what the interface is for.

`data/ge_kappa.csv` — the file `wig_ge_fit_cfd` looks for by default — is **deliberately not
present**, so that a fresh clone cannot silently "calibrate" against the template. Calling
`wig_ge_fit_cfd()` with no argument therefore raises a clear error telling you to produce the
file first.

---

## 2. Proposed CFD work items

### 2.1 Steady ground-effect aerodynamics (highest priority)

**Purpose:** obtain lift, drag and pitching moment as functions of height `h`, in order to
calibrate the ground-effect factor

```
kappa(h) = (h/b)^n / (A + (h/b)^n)
```

| Item | Value |
|---|---|
| Aerofoil | cambered, matching the MATLAB model (`alpha_L0 ≈ -3 deg`) |
| Planform | rectangular wing, span 2.40 m, chord 0.40 m, `S = 0.96 m²` |
| Tail | span 0.80 m, area 0.18 m², raised 0.30 m |
| Height `h` | 0.030, 0.050, 0.075, 0.100, 0.150, 0.200, 0.250, 0.300, 0.400, 0.500, 0.750, 1.000, 1.500, 2.000 m |
| Incidence `alpha` | 0, 2, 4, 6, 8 deg (must cover the trim range 3-5 deg) |
| Speed | 18 m/s (`Ma ≈ 0.053`, incompressible) |
| Turbulence model | SST k-omega (recommended); realisable k-epsilon for comparison |
| Boundary conditions | ground: no-slip moving wall at free-stream speed, or slip wall; far field: pressure far field |
| Mesh | structured O- or C-grid, first cell `y+ ≈ 1`, at least 25 cells between ground and wing, refined near the ground |

**Outputs required for every `(h, alpha)` pair**

* `CL(h, alpha)` — used to infer the effective lift-curve slope `a_w(h)` and the ground-effect factor
* `CD(h, alpha)` — split into `CD0` and the induced part `CDi(h)`
* `Cm(h, alpha)` about the quarter chord — **the height-stability derivative `dCm/dh`**, which
  decides whether the configuration is height-stable
* downwash angle `eps(h, alpha)` at the tail — to calibrate `eps_a` and the ground-effect
  attenuation of the downwash

**File to hand back to MATLAB** — `data/ge_kappa.csv`:

```csv
h_m,span_m,kappa
0.030,2.40,0.0312
0.050,2.40,0.0515
0.100,2.40,0.1301
...
```

where `kappa = CDi(h) / CDi(h -> inf)`. Once the file exists:

```matlab
cd ../src
[A, n, R2] = wig_ge_fit_cfd();      % reads ../ansys/data/ge_kappa.csv
p = wig_params();
p.ge_A = A;  p.ge_n = n;  p.ge_src = 'cfd';
% run_analysis / run_scenarios now use the CFD-calibrated ground-effect model
```

### 2.2 Unsteady and dynamic ground effect

* forced pitching oscillation, reduced frequency `k = omega*c/(2V) = 0.02-0.15`, to obtain the
  dynamic derivatives `Cmq` and `Cmadot`;
* rapid height variation (sine or ramp) to quantify the ground-effect hysteresis and to test
  whether the quasi-steady assumption holds;
* wave and sea-surface boundaries (if a maritime WIG is intended): equivalent roughness and wave
  height versus aerodynamic force.

### 2.3 Structural analysis (optional)

* static strength and modal analysis of the wing and tail boom (Workbench Static Structural + Modal);
* goal: obtain the first few elastic mode frequencies and check for coupling with the flight-control
  bandwidth (about 3-8 rad/s in this design);
* if the first bending frequency is below 5 Hz, a structural filter must be added to the MATLAB model.

---

## 3. Data loop

```
ANSYS Fluent  -->  data/ge_kappa.csv  -->  wig_ge_fit_cfd.m  -->  p.ge_A / p.ge_n
     |                                                                   |
     |                                                                   v
     +-->  data/aero_table.csv  -->  (optional) replace the aerodynamic model  -->  controller
                                                                                   |
                                        controller bandwidth / margins ------------+
                                        feed back to CFD: required h resolution
```

`data/aero_table_template.csv` defines the column layout for the optional full replacement of
`wig_aero.m` by a CFD table. Its rows are **placeholders with zero values**, to be overwritten by
real results.

---

## 4. Directory conventions

```
ansys/
  README.md                   this file
  data/
    ge_kappa_template.csv     ground-effect factor template (generated from the analytic model)
    ge_kappa.csv              real CFD output -- NOT in the repository, you produce it
    aero_table_template.csv   full aerodynamic-coefficient table layout (placeholder rows)
  cfd/                        Fluent/CFX project files, journals, UDFs        (empty)
  docs/                       CFD reports, mesh-independence study, tunnel comparison (empty)
```

---

## 5. Mapping to the MATLAB model

Quantities in the nominal parameter set that CFD can calibrate directly:

| Parameter | Current value | CFD source |
|---|---|---|
| `p.ge_A`, `p.ge_n` | 0.0641, 1.4622 | induced-drag variation with height (Section 2.1) |
| `p.a0` | 5.90 1/rad | free-air lift-curve slope |
| `p.CD0` | 0.0250 | free-air parasite drag |
| `p.Cmac` | -0.050 | pitching-moment coefficient about the aerodynamic centre |
| `p.eps0`, `p.eps_a` | 0.020, 0.350 | tail downwash angle and its gradient |
| `p.a_de` | 1.60 1/rad | elevator control effectiveness |

In the current model the true plant (`wig_truth_params.m`) is deliberately given a **ground-effect
strength mismatch** relative to the nominal model (`ge_A`: 0.0641 -> 0.045, `ge_n`: 1.4622 ->
1.300), together with a RAM effect and lift nonlinearity. This represents the situation in which
an engineering estimate has not been calibrated against CFD, and it is exactly what the adaptive
controller has to compensate online. Once CFD calibration is available the calibrated values can
be written into the nominal model, the mismatch shrinks, and both the compensation burden and the
weight magnitudes of the adaptive law decrease accordingly.
