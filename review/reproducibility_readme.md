# CLTML Research Artifact & Reproducibility Package

Welcome to the official reproducibility package for:
**CLTML: Compile-Time Lookup Tables for Inference-Latency-Bounded Lock Selection in the Linux Kernel**

This repository provides all source code, datasets, offline training pipelines, C11 benchmark harnesses, freestanding kernel headers, out-of-tree Linux kernel module sources, and execution logs to reproduce every claim, figure, table, and metric reported in the paper.

---

## 1. Directory Structure

```
.
├── src/
│   ├── cltml_kernel_lut.h          # Freestanding C11 header containing the 4 KB LUT & branchless quantizer
│   ├── cltml_benchmark.c           # Quiescent-epoch and inline microbenchmark timing harness
│   ├── cltml_userspace_benchmark.c # 4-lock empirical benchmark & bimodal multi-threaded test (Component 5)
│   ├── cltml_userspace_locks.h     # C11 ticket lock and MCS lock implementations
│   ├── cltml_module.c              # Out-of-tree Linux kernel module implementing Tier 1 spin-ceiling tuning
│   └── Makefile / Kbuild           # Kernel module build infrastructure
├── scripts/
│   ├── cltml_pipeline.py           # Offline training, quantization, regret analysis, amortization sweep
│   ├── validate_lut_4096.py        # Exhaustive 4,096-state safety and coverage verification suite
│   ├── generate_figures.py         # Generation of publication-quality Figures 1–4
│   ├── update_html_paper.py        # Token reconciliation for HTML master paper
│   └── reconcile_and_generate.py   # Master build and PDF compilation pipeline
├── data/
│   ├── screening_prisma_data.csv   # PRISMA literature screening decisions for 40 full-text candidates
│   ├── cltml_metrics.json          # Single source of truth for all quantitative metrics
│   ├── cltml_empirical_traces.csv  # 4,000 empirical execution traces recorded on physical silicon
│   ├── cltml_c_timings.json        # High-resolution TSC cycle timings from C11 benchmark
│   └── cltml_userspace_results.json# Measured multi-threaded throughput across 2, 4, 8, 12 threads
├── paper/
│   ├── Review_Paper_IEEE.html      # Generated pixel-perfect two-column IEEE HTML
│   ├── CLTML_IEEE_Research_Paper.tex # Generated IEEE LaTeX source
│   ├── cltml_research_paper.pdf    # Target compiled research paper PDF (strictly 8 pages)
│   └── figures/                    # High-resolution 300 DPI figures (PNG)
└── review/
    ├── initial_audit.md            # Phase 0 baseline technical audit
    ├── numerical_consistency_audit.md # Complete mathematical derivations and state-space proof
    ├── claims_evidence_ledger.csv  # Ledger mapping all 30 manuscript claims to source evidence
    ├── reference_audit.csv         # Audit of all 36 authentic references with DOIs
    ├── screening_contingency_matrix.csv # Complete 2x2 reviewer contingency matrices
    ├── reproducibility_report.md   # Step-by-step reproduction guide and platform specs
    └── final_peer_review.md        # Comprehensive external peer-review assessment (94/100)
```

---

## 2. Requirements & Environment Setup

- **Hardware:** x86_64 CPU with invariant Time Stamp Counter (TSC). Evaluated on Intel Core 5 210H (12 execution threads).
- **OS:** Linux (evaluated on CachyOS / Arch Linux with kernel 7.3.0, compatible with Linux 6.8+ LTS).
- **Compilers:** GCC 14.2.1+ or Clang/LLVM 18.1.8+ with `-O3 -march=native -pthread`.
- **Python:** Python 3.10+ with `lightgbm`, `scikit-learn`, `numpy`, `pandas`, `matplotlib`.

To set up the Python environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install lightgbm scikit-learn numpy pandas matplotlib
```

---

## 3. Quick-Start Reproduction Commands

### Command 1: Validate Lookup Table Bijective Safety (Table IV, Sec. IV-E)
```bash
python3 scripts/validate_lut_4096.py
```
*Output: 4,096 unique valid states, 0 out-of-bounds, 0 invalid codes.*

### Command 2: Execute Physical End-to-End Multi-Threaded Benchmark (Table V, Sec. V-B)
```bash
gcc -O3 -march=native -pthread src/cltml_userspace_benchmark.c -o src/cltml_userspace_benchmark
./src/cltml_userspace_benchmark
```
*Output: Measured throughput across 2, 4, 8, 12 threads; CLTML achieves 7.48 Mops at 12T (+17.6% over best static spinlock).*

### Command 3: Run Full Machine Learning & Regret Pipeline (Table IV, Sec. V-A)
```bash
.venv/bin/python scripts/cltml_pipeline.py --samples 16000
```
*Output: Recomputes all regret metrics, amortization sweep, and empirical trace accuracy; exports `data/cltml_metrics.json`.*

### Command 4: Compile Final 8-Page IEEE PDF
```bash
python3 scripts/reconcile_and_generate.py
```
*Output: Verifies 8 pages via `pdfinfo` and generates `cltml_research_paper.pdf`.*
