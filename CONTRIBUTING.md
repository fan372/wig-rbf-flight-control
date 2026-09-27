# Contributing

Thanks for your interest in this project. This repository is a research code base for
wing-in-ground-effect (WIG) UAV longitudinal flight dynamics and RBF neural-network adaptive
control. Contributions that improve correctness, reproducibility or documentation are welcome.

## Ground rules

1. **Every number must be reproducible.** All quantitative statements in the documentation are
   backed by a text log in `results/`. If you change a model, a gain or a scenario, regenerate the
   logs and update the documents in the same pull request. Do not hand-edit numbers in the docs.
2. **Do not tune silently.** If you change a controller gain in `src/wig_params.m`, say so in the
   pull request description and include the before/after metrics.
3. **One concern per pull request.** Keep model changes, controller changes and documentation
   changes separate where possible.

## Development setup

Requirements are listed in `README.md` (MATLAB R2025b with Simulink; Python 3.8+ with the
standard library only, for the document toolchain).

```matlab
cd src
addpath(pwd)
run_00_smoke     % fast self-check: parameters, ground-effect factor, trim, 8 s closed loop
run_all          % full suite (~5 min): analysis, scenarios, Monte-Carlo, Simulink
```

```bash
# document toolchains (Python standard library only)
cd tools/word  && python selftest.py --no-com
cd tools/pdf   && python verify_pdf.py
```

## Unit tests

```matlab
cd tests
addpath(pwd)
run_tests        % exits non-zero if any assertion fails
```

`tests/run_tests.m` checks the invariants that the theory depends on: the ground-effect factor and
its derivative, the trim residual, the analytic pitch-moment decomposition against finite
differences, the RBF node counts and partition of unity, the projection-operator bound, the
pack/unpack round trip, and the Jacobian of the sampled closed-loop map.

## Coding style

* MATLAB: one public function per file, the function name equal to the file name; local helper
  functions at the bottom of the file after a `% ====` separator.
* Every public function starts with an H1 line, then a documented input/output block in Chinese,
  consistent with the rest of `src/`.
* Prefer explicit, named quantities over magic numbers; new tuning constants belong in
  `wig_params.m`.
* Keep `results/log_*.txt` in UTF-8. Scripts must not contain absolute paths.

## Reporting bugs

Please include:

* the exact command you ran,
* the full text of the relevant `results/log_*.txt`,
* `version` and `computer` output from MATLAB,
* whether the issue also reproduces with `run_00_smoke`.

## Scope

Out of scope for this repository: lateral-directional control, structural elasticity, and the CFD
calculations themselves (only the data interface is provided, see `ansys/README.md`).
