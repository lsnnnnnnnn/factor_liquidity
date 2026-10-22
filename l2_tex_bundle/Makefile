.PHONY: all figures pdf bundle clean

PYTHON ?= python3
export TEXMFCACHE := $(CURDIR)/build/tex-cache
export TEXMFVAR := $(CURDIR)/build/tex-cache
export MPLCONFIGDIR := $(CURDIR)/build/matplotlib-cache

all: figures pdf

figures:
	$(PYTHON) scripts/make_figures.py
	$(PYTHON) scripts/make_execution_update.py
	$(PYTHON) scripts/make_execution_tables.py
	$(PYTHON) scripts/make_sample3_update.py
	$(PYTHON) scripts/make_sample3_restoration.py
	$(PYTHON) scripts/make_sample3_targets.py

pdf:
	mkdir -p "$(TEXMFCACHE)"
	latexmk -lualatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build main.tex
	cp build/main.pdf report.pdf

bundle: all
	$(PYTHON) scripts/build_bundle.py

clean:
	latexmk -C -outdir=build main.tex
