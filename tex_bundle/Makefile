.PHONY: pdf figures bundle clean

PYTHON ?= python3
export TEXMFCACHE := $(CURDIR)/build/tex-cache
export TEXMFVAR := $(CURDIR)/build/tex-cache

pdf:
	mkdir -p "$(TEXMFCACHE)"
	latexmk -lualatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build main.tex
	cp build/main.pdf report.pdf

figures:
	$(PYTHON) scripts/make_figures.py

bundle: pdf
	$(PYTHON) scripts/build_bundle.py

clean:
	latexmk -C -outdir=build main.tex
