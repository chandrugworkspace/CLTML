# ==============================================================================
# CLTML Research Project Master Makefile
# Authors: Chandru G and Chethan S
# Department of Computer Science and Engineering (AI & ML), PES University
# ==============================================================================

SHELL := /bin/bash
PYTHON := .venv/bin/python
CHROMIUM := chromium

.PHONY: all run pipeline figures reconcile benchmark userspace pdf clean help

run:
	@./run.sh

all: pipeline figures reconcile
	@echo "=============================================================================="
	@echo "  CLTML End-to-End Build Completed Successfully!"
	@echo "  PDF output: cltml_research_paper.pdf"
	@echo "  LaTeX source: paper/CLTML_IEEE_Research_Paper.tex"
	@echo "  Single Source of Truth: data/cltml_metrics.json"
	@echo "=============================================================================="

help:
	@echo "Available Targets:"
	@echo "  make all         - Run complete pipeline, figures, reconciliation, and PDF compilation"
	@echo "  make pipeline    - Train GBDT, generate 4 KB LUT, compile benchmark, run simulations"
	@echo "  make figures     - Generate publication-quality figures (Fig 1-4) at 300 DPI"
	@echo "  make reconcile   - Synchronize all metrics to LaTeX and HTML, render PDF"
	@echo "  make benchmark   - Recompile and execute native C11 microbenchmark"
	@echo "  make pdf         - Re-render paper PDF via Chromium headless"
	@echo "  make clean       - Remove generated temporary files and build artifacts"

pipeline:
	@echo "[Step 1/3] Running end-to-end CLTML simulation & benchmark pipeline..."
	$(PYTHON) scripts/cltml_pipeline.py

figures:
	@echo "[Step 2/3] Generating publication figures..."
	$(PYTHON) scripts/generate_figures.py

reconcile:
	@echo "[Step 3/3] Reconciling LaTeX, HTML, and compiling PDF..."
	$(PYTHON) scripts/reconcile_and_generate.py

benchmark:
	@echo "Compiling and executing src/cltml_benchmark..."
	gcc -O3 -Wall -pthread -Isrc src/cltml_benchmark.c -o src/cltml_benchmark -lm
	./src/cltml_benchmark
	@rm -f cltml_c_timings.json

userspace:
	@echo "Compiling and executing src/cltml_userspace_benchmark..."
	gcc -O3 -Wall -pthread -Isrc src/cltml_userspace_benchmark.c -o src/cltml_userspace_benchmark -lm
	./src/cltml_userspace_benchmark

pdf:
	@echo "Rendering PDF via Chromium headless..."
	$(CHROMIUM) --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
		--user-data-dir=/tmp/chromium-data \
		--print-to-pdf=paper/cltml_research_paper.pdf \
		paper/Review_Paper_IEEE.html
	@cp paper/cltml_research_paper.pdf ./cltml_research_paper.pdf
	@pdfinfo cltml_research_paper.pdf | grep -E "Pages|File size"

clean:
	@echo "Cleaning temporary build files..."
	rm -rf /tmp/chromium-data
	rm -f src/cltml_benchmark src/cltml_userspace_benchmark src/*.ko src/*.o
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	@echo "Clean completed."
