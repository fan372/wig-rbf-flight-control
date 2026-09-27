# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-26

First public release. The package contains a complete, reproducible study of ground-effect height
instability and RBF neural-network adaptive longitudinal control for a small WIG UAV.

### Added

* `src/wig_params.m`, `src/wig_truth_params.m` — nominal and true parameter sets with an explicit
  ground-effect mismatch, RAM effect and lift nonlinearity.
* `src/wig_ge.m` — ground-effect factor `kappa(h) = x^n / (A + x^n)` with its height derivative.
* `src/wig_aero.m` — wing, tail, fuselage and thrust contributions to lift, drag and pitching
  moment, with every moment component exposed for decomposition.
* `src/wig_dynamics.m`, `src/wig_trim.m`, `src/wig_linearize.m` — seventh-order longitudinal
  dynamics, trim solver and numerical linearisation.
* `src/wig_mdh_decomp.m` — component-wise decomposition of the pitch-moment height derivative
  `dM/dh`; closing residual is at machine precision (2.4e-12 N·m/m).
* `src/run_00_mdh.m` / `run_00_mdh_body.m` — height sweep of the decomposition, with a stacked-bar
  figure (`figures/fig12_mdh.png`).
* `src/wig_rbf_init.m`, `src/wig_rbf_phi.m`, `src/wig_proj.m` — RBF network construction,
  Gaussian basis evaluation and the projection operator.
* `src/wig_ctrl_init.m`, `src/wig_ctrl_update.m`, `src/wig_ctrl_pack.m`, `src/wig_ctrl_unpack.m` —
  the three-loop RBF adaptive controller and its state packing for Simulink.
* `src/wig_closedloop_eig.m` — sampled-data closed-loop linearisation that first warms up the
  adaptive loop, then solves for the true equilibrium of the frozen-parameter system, and only
  then forms the Jacobian.
* `src/msfcn_wig_plant.m`, `src/msfcn_wig_ctrl.m`, `src/build_simulink_model.m`,
  `src/run_simulink.m` — Level-2 MATLAB S-Functions and programmatic construction of the Simulink
  model, plus a cross-validation against the script simulation.
* `tests/run_tests.m` — a self-contained assertion suite for the model and controller invariants.
* `tools/word/`, `tools/pdf/` — pure Python-standard-library generators for the Word report and the
  PDF tutorial (no python-docx, no reportlab, no browser).
* `docs/tutorial/`, `docs/report/`, `docs/paper/` — the tutorial, the technical report and the
  conference paper (Chinese Word and English IEEE LaTeX).
* `ansys/README.md`, `ansys/data/ge_kappa_template.csv` — CFD workflow description and the data
  interface used by `src/wig_ge_fit_cfd.m`.

### Fixed

Corrections made during the final review pass. Each one is reproducible from the logs in
`results/`.

* **Layout of the English papers.** Several tables were wider than the IEEE two-column measure
  and ran into the neighbouring column, and some display equations crossed the column rule. The
  tables are now sized from their measured natural width — `tools/measure_tables.py` compiles the
  document and records it in `table_widths.json` — so each one is placed either in a single column
  or as a full-width `table*`. Captions now use `\caption` instead of a hand-built box, and
  IEEEtran's automatic subsection letters are no longer duplicated by the ones in the content
  model. The three English papers build with zero overfull boxes.
* **Chinese labels leaking into the English papers.** The LaTeX tables carried the Chinese row
  labels from the log, which pdfLaTeX cannot typeset, so the first column came out empty; the
  figures had Chinese axis labels. Both are now generated in English as well
  (`content_en.py` label map, `src/run_figs_en.m` into `figures_en/`). The Chinese figures and
  documents are unchanged.
* **Classical phugoid damping formula** (`run_00_stab_body.m`, `run_analysis_body.m`): the
  damping ratio was computed as `D/(m*V^2*omega_p)`, which is dimensionally inconsistent and
  under-reported the damping by a factor of `V` (0.0029 instead of 0.0527). Corrected to the
  Lanchester form `zeta_p = 1/(sqrt(2)*(L/D))`.
* **Pitch-moment decomposition** was previously quoted as three terms that did not sum to the
  numerically computed total (a 10% gap) and omitted the lift-softening term. It is now a
  four-term decomposition computed by `wig_mdh_decomp.m`, with an explicit closure check.
* **Closed-loop eigenvalue analysis** (`wig_closedloop_eig.m`) previously linearised about the
  *true-plant trim point* while freezing the adaptive weights at **zero**, so that the reported
  `max|z|` exceeded unity and contradicted the stable nonlinear simulations. The tool now warms
  the loop up to weight convergence, solves the genuine equilibrium of the frozen-parameter system
  (residual < 1e-16), and freezes the converged weights, giving `max|z| = 0.99942 < 1`.
* **Simulink cross-validation** (`run_simulink_body.m`) compared the controller *command*
  (`uout`) against the actuator *state* (`R.de`), producing a spurious 6.29 deg "elevator
  trajectory deviation". The comparison is now state-versus-state and command-versus-command, and
  the airspeed deviation column is computed instead of being hard-coded to `NaN`.
* **Static-margin calculation** (`run_analysis_body.m`) used a hard-coded tail lift-curve slope of
  3.7 instead of the model's own value.
* **Stale diagnostic logs**: `log_opt`, `log_cfdfit`, `log_clp`, `log_lag`, `log_dbg`, `log_chk`
  and `log_chk2` were produced by earlier, mutually inconsistent gain sets. The diagnostic scripts
  now take their gains from `wig_params.m`, and every log is regenerated by the shipped code.
* **Failed-experiment log** `log_sfprobe.txt` and its one-off API probe scripts were removed.

### Changed

* `wig_simulate.m` now honours `scn.Tend` with the documented default, reads the gust seed from
  the gust structure, records a touchdown flag, returns the terminal controller state
  (`R.ctrl_end`) for the equilibrium analysis, and calls `wig_aero` once instead of twice per step.
* `wig_ctrl_pack.m` / `wig_ctrl_unpack.m` validate the state-vector length instead of silently
  building a mis-sized vector when `xf` is empty.
* `wig_trim.m` clamps the normalised throttle consistently with `trm.dt`.
* Documentation no longer claims an anti-windup path through `wig_dynamics`; the unused
  `p.ctrl.k_aw` field was removed. Anti-windup is implemented inside `wig_ctrl_update.m` by
  freezing the adaptation while an actuator is saturated.
