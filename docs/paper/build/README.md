# Paper build tools

The paper PDFs and Word file in `../` are **generated**, not hand-edited. This directory contains
the generators and the frozen numeric source they read.

## The one rule

**Every number in the paper comes from `metrics.json`.** No simulation result is typed into the
prose by hand. `metrics.json` is in turn produced by parsing the MATLAB logs in
`../../../results/log_*.txt`, so the paper can never silently disagree with the logs.

```
../../../results/log_*.txt
        |  extract_metrics.py
        v
   metrics.json  ----+
                     |  content_zh.py / content_en.py   (prose, tables, equations)
                     v
             build_all.py  ----  ir_render_docx.py  ->  <out>/zh/*.docx
                           ----  ir_render_tex.py   ->  <out>/en/*.tex
             build_public.py -- (same content, author block emptied) ->  ../*
```

## About the paper shipped here

The copy in `../` is the **extended version with the author block removed**, so that this public
repository carries the technical content without personal contact details. The full submission
set (Chinese Word and English IEEE LaTeX, each in three lengths, with author details) is built by
`build_all.py` and kept outside version control.

## Files

| File | Role |
|---|---|
| `extract_metrics.py` | parses `results/log_*.txt` into `metrics.json`; **fails loudly** if any expected table is missing, rather than emitting a silent `None` |
| `metrics.json` | the frozen numeric source (also a readable record of every result quoted in the paper) |
| `refs.py` | the reference list, with a verification note per entry (26 entries; every DOI cross-checked against Crossref) |
| `content_zh.py`, `content_en.py` | the paper content (same structure, same keys, same numbers in both languages); the `g(block, minlv)` helper selects content per length version |
| `paper_docx.py` | conference-paper front matter on top of the project's pure-stdlib `.docx` engine |
| `ir_render_docx.py`, `ir_render_tex.py` | render the shared content model to Word and to IEEEtran LaTeX |
| `build_all.py` | driver: builds the full submission set (3 lengths x 2 languages) |
| `build_public.py` | builds the author-free copy that is committed here |
| `measure_tables.py` | compiles the `.tex` once and records each table's **measured** natural width into `table_widths.json`, so the renderer can decide per table between a single-column float and a full-width `table*` |
| `table_widths.json` | the measured widths produced by the above |
| `check_docx_layout.py` | parses the generated `.docx` and asserts no table or figure exceeds the text column |
| `check_citations.py` | asserts every reference is cited in the text and no citation points at a missing entry |

## Reproducing the build

These scripts expect the **workspace layout** they were written for, where the MATLAB project and
the paper sources sit side by side:

```
<root>/
  matlab_simulink/     # the simulation project (supplies results/ and figures/)
  conference_paper/
    tools/             # these scripts
    zh/  en/  public/  # output
```

To rebuild from a clone of this repository, either

* point them at a checkout, or
* simply edit the paths at the top of `build_all.py` (`ROOT`, `FIG_SRC`).

```bash
python extract_metrics.py     # logs -> metrics.json   (needs ../../../results/)
python build_all.py           # -> ../zh/*.docx and ../en/*.tex
python measure_tables.py      # -> table_widths.json, then re-run build_all.py
python build_public.py        # -> ../public/*  (author-free, the copy committed here)
python check_citations.py     # reference <-> citation consistency
python check_docx_layout.py ../public
```

The English `.tex` compiles with a standard TeX Live installation:

```bash
pdflatex wig-rbf-flight-control-paper-en.tex   # run twice so cross-references settle
```

The Chinese `.docx` needs only Word (or LibreOffice) to export a PDF.

## Note on the frozen metrics

`metrics.json` is committed deliberately: it lets a reader check any number quoted in the paper
against the log it came from, without having to re-run MATLAB. If you change the model, re-run
`run_all`, then re-run `extract_metrics.py` and `build_all.py` so the paper follows.
