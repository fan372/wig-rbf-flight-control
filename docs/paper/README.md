# Paper

The technical paper accompanying this repository, in two languages:

| File | Language | Notes |
|---|---|---|
| `wig-rbf-flight-control-paper-zh.docx` | Chinese | Word source, 21 pages |
| `wig-rbf-flight-control-paper-zh.pdf` | Chinese | same document as PDF |
| `wig-rbf-flight-control-paper-en.tex` | English | IEEEtran `conference` source |
| `wig-rbf-flight-control-paper-en.pdf` | English | compiled, 12 pages |
| `figures/` | -- | the 12 figures used by the English paper, with English labels |

**The author block has been removed from this copy.** The published versions carry the author's
name, affiliation and contact address; this repository ships the technical content without them.
The body text, equations, tables, figures and reference list are otherwise identical to the
submitted manuscript.

## What the paper claims

* The pitch-moment height derivative `dM/dh` is strictly positive across the whole flight
  envelope (+1.06 to +14.90 N m/m), i.e. the height static stability is negative; a component-wise
  decomposition attributes this to the tail downwash term, with the wing contributing a
  stabilising share.
* The phugoid-height coupled mode is unstable (real part up to +0.4875 1/s); switching the ground
  effect off returns it to neutral stability, so the instability is of ground-effect origin.
* A three-loop RBF adaptive controller (altitude outer loop, dynamic-surface attitude inner loop,
  airspeed loop) achieves uniform ultimate boundedness, and reduces the height-tracking RMS error
  from 0.1938 m to 0.0100 m under a deliberately mismatched plant.
* A discrete-time design constraint `Ts*Gamma_i*||phi_i||^2 < k_i` explains why the moment-channel
  adaptation gain must be three orders of magnitude smaller than the drag-channel gain.

Every number quoted in the paper is traceable to a log in `../../results/`; see
`build/README.md` for how the documents are generated and how to re-derive them.

## Building

```bash
cd build
pdflatex wig-rbf-flight-control-paper-en.tex     # run twice, then again for the bibliography
```

`figures/` must stay next to the `.tex` file. The Chinese `.docx` opens directly in Word or
LibreOffice.
