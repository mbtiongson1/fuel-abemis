# Compiling the Final Paper and Slides

This directory contains the AI 201 mini-project final paper, slides, and proposal source. To compile the two PDFs yourself, follow the steps below.

## Files

| File | Purpose |
|---|---|
| `Final Paper.tex` | Full research paper (Roman-numeral sections I-XII + Appendix A-D) |
| `Final Slides.tex` | Beamer slide deck for the 10-minute defense |
| `references.bib` | BibTeX bibliography (10 entries, used by the paper only) |
| `acm_proc_article-sp.cls` | ACM proceedings class file (kept for reference; the current paper uses standard `article` to match `Project Proposal 1st Revision.tex` — see *Note on class file* below) |
| `Final Paper.pdf`, `Final Slides.pdf` | Pre-compiled outputs |

## One-time setup — TeX engine

The cleanest option on macOS is **tectonic**, a single-binary LaTeX engine that auto-fetches missing packages on first run. No `sudo` required.

```bash
brew install tectonic
```

Alternative: install **BasicTeX** or **MacTeX** (requires `sudo`):

```bash
brew install --cask basictex          # ~100 MB, needs sudo password during install
# or
brew install --cask mactex            # ~5 GB, full TeX Live
```

After BasicTeX/MacTeX install, restart your terminal or run:

```bash
eval "$(/usr/libexec/path_helper)"
sudo tlmgr update --self
sudo tlmgr install collection-fontsrecommended biblatex biber booktabs beamer pgf
```

## Compile the paper

From inside this directory:

```bash
cd "Mini-Project/Project Documents"
tectonic "Final Paper.tex"
```

That single command runs LaTeX + BibTeX automatically and produces `Final Paper.pdf`. Tectonic downloads any missing fonts/packages on the first run (one-time, ~30 s).

If using BasicTeX/MacTeX instead, you need three passes:

```bash
pdflatex -interaction=nonstopmode "Final Paper.tex"
bibtex "Final Paper"
pdflatex -interaction=nonstopmode "Final Paper.tex"
pdflatex -interaction=nonstopmode "Final Paper.tex"
```

## Compile the slides

```bash
tectonic "Final Slides.tex"
```

Or with pdflatex (slides do not use bibtex, so two passes suffice):

```bash
pdflatex -interaction=nonstopmode "Final Slides.tex"
pdflatex -interaction=nonstopmode "Final Slides.tex"
```

## Figures and image paths

Both `.tex` files use `\graphicspath{}` with **absolute paths** pointing into:

- `Mini-Project/Agricultural Machinery Inventory from ABEMIS/Regression Parameters Output V3/`
- `Mini-Project/Agricultural Machinery Inventory from ABEMIS/Analytics Output V2/`

If you move this directory, update the two `\graphicspath{...}` blocks at the top of each `.tex` file, or use relative paths instead.

The paper embeds **41 figures**: 2 SHAP plots, 24 OLS diagnostic plots (six scopes × four plot types each), 10 LIME local explanations, and 5 descriptive analytics charts. The slides embed 3 key figures (SHAP bar, SHAP beeswarm, one LIME example).

## Note on class file

The directory contains `acm_proc_article-sp.cls`, an ACM proceedings class. The current `Final Paper.tex` uses `\documentclass[10pt,twocolumn]{article}` instead, to match the preamble of `Project Proposal 1st Revision.tex`. To switch to the ACM class, the title block and section macros would need to be rewritten (the ACM class defines its own `\maketitle`, `\section`, etc.).

## Common compile issues

- **"File `*.png` not found"** — check the absolute paths in `\graphicspath{}`; they must match where the figures actually live on your machine.
- **"Package biblatex Error"** — install via `sudo tlmgr install biblatex biber` (BasicTeX) or use tectonic which auto-fetches.
- **Underfull `\vbox` warnings on appendix pages** — cosmetic only, caused by large single-figure pages. Safe to ignore.
- **Permission denied on `\write18`** — not needed for these documents; ignore.

## Re-running the analysis (optional)

If you want to regenerate the figures from scratch, activate the repo's venv and run the pipeline modules:

```bash
cd /Users/marcotiongson/Documents/fuel-abemis
source .venv/bin/activate

# Regenerate analytics + figures
python -m data.amtec_analytics
python -m models.ols_regression
python -m models.random_forest
python -m analysis.shap_analysis
python -m analysis.lime_explanations
python -m analysis.abemis_fuel_scoring
```

Then recompile both `.tex` files.
