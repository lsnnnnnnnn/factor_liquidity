.PHONY: all figures pdf bundle clean

PYTHON ?= python3
export TEXMFCACHE := $(CURDIR)/build/tex-cache
export TEXMFVAR := $(CURDIR)/build/tex-cache
export MPLCONFIGDIR := $(CURDIR)/build/matplotlib-cache

all: figures
	$(MAKE) pdf

figures:
	$(PYTHON) scripts/make_current_report.py

pdf:
	mkdir -p "$(TEXMFCACHE)"
	latexmk -lualatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build main.tex
	cp build/main.pdf report.pdf

bundle: all
	$(PYTHON) scripts/build_bundle.py

clean:
	latexmk -C -outdir=build main.tex
