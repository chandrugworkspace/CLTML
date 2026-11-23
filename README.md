# CLTML: Compile-Time Lookup Tables for Inference-Latency-Bounded Lock Selection in the Linux Kernel

### *A Constraint Review and Feasibility Study*

**Authors:**
- **Chandru G** — *Department of Computer Science and Engineering (AI & ML), PES University, Bengaluru, Karnataka, India* (`chandrug@pesu.pes.edu`)
- **Chethan S** — *Department of Computer Science and Engineering (AI & ML), PES University, Bengaluru, Karnataka, India* (`chethans@pesu.pes.edu`)

**Research Paper:** [`cltml_research_paper.pdf`](cltml_research_paper.pdf)

---

## 📌 Abstract

Lock contention limits how well multicore systems scale, and learned lock policies have a timing problem of their own: a model that runs at decision time can take longer than the lock operation it was supposed to speed up. We present **CLTML**, a feasibility study that compiles an offline gradient-boosted decision-tree (GBDT) policy into a fixed-size lookup table of 4,096 entries (4 KB), indexed by a 12-bit quantized feature key.

The study pairs a PRISMA-informed constraint review with three separate tiers of evidence:
1. **Native userspace measurements** on Intel Core 5 210H and Ultra 7 255HX hosts;
2. **Analytical multi-socket NUMA projections**;
3. **Proposed architecture** for context-compatible primitive selection.

On 16,000 analytically generated workload windows (12,000 training, 4,000 held out):
- The float GBDT matches generator oracle labels **95.23%** of the time.
- The 4-feature/3-bit LUT matches them **95.05%** of the time (a gap of only 0.18 percentage points).
- The LUT directly agrees with its GBDT teacher on **97.42%** of inputs.
- In native C, inline quantize-and-lookup takes **4.10 ns** (11.0 cycles) and pre-binned lookup takes **1.47 ns** (4.0 cycles), well within the 100 ns kernel fast-path budget.
- Under the held-out oracle cost model, Design A achieves **1.04 ns** mean regret and **+0.60%** cost overhead (compared to +49.26% overhead and 86.16 ns regret for static qspinlock).

---

## 🏗️ Architectural Imperatives

CLTML satisfies five kernel-oriented constraints:
1. **Zero FPU Usage:** Pure fixed-point integer arithmetic (`CLTML_FP_SCALE = 100`), eliminating `kernel_fpu_begin()` / `kernel_fpu_end()` overhead and safe for atomic/interrupt contexts.
2. **Deterministic $O(1)$ Bounded Execution:** Constant-time quantization and table read with bit-masking (`& 0x0FFF`) preventing memory violations.
3. **L1 Cache-Resident Footprint:** Exactly 4,096 bytes (covering 64 cache lines at 64B/line), fitting inside standard 32 KB L1 data caches.
4. **Strict Kernel Stack Bounds:** Less than 64 bytes of stack space, honoring kernel thread stack caps (8 KB / 16 KB).
5. **Exhaustive Verifiability:** Exactly 4,096 indices exhaustively verifiable for bounds and valid output codes.

---

## 📂 Repository Structure

```
.
├── cltml_research_paper.pdf       # Publication research paper (Camera-Ready PDF)
├── Makefile                       # Project build and execution automation
├── CMakeLists.txt                 # CMake build configuration
├── run.sh                         # Master end-to-end benchmark and reproduction script
├── CLTML_CHANGELOG.md             # Comprehensive revision history & changelog
├── CLTML_TECHNICAL_AUDIT.md       # Technical audit and claim verification ledger
├── src/
│   ├── cltml_table.h              # Freestanding C11 header containing 4 KB LUT & thresholds
│   ├── cltml_kernel_lut.h         # Kernel-compatible lookup table definition
│   ├── cltml_benchmark.c          # C11 hot-path timing and quiescent-epoch stress harness
│   ├── cltml_userspace_benchmark.c# 4-lock empirical benchmark (Mutex, Spinlock, Ticket, MCS)
│   ├── cltml_userspace_locks.h    # C11 ticket lock and MCS lock implementations
│   ├── cltml_module.c             # Out-of-tree Linux kernel module (Tier 1 spin-ceiling tuning)
│   └── Kbuild                     # Linux kernel module build script
├── scripts/
│   ├── cltml_pipeline.py          # Offline GBDT training, quantization, and regret analysis
│   ├── validate_lut_4096.py       # Exhaustive 4,096-state bijective verification suite
│   ├── generate_figures.py        # Generation of publication-quality Figures 1–4
│   ├── reconcile_and_generate.py  # Metrics synchronization and paper compiler
│   ├── update_html_paper.py       # HTML token reconciliation
│   └── host_info.py               # Hardware specification reader
├── data/
│   ├── cltml_metrics.json         # Single source of truth for all quantitative metrics
│   ├── cltml_c_timings.json       # High-resolution TSC cycle timings from C11 benchmark
│   ├── cltml_userspace_results.json # Multi-threaded throughput across thread counts
│   ├── cltml_empirical_traces.csv # 4,000 empirical traces recorded on physical silicon
│   └── screening_prisma_data.csv  # PRISMA literature screening decisions
├── paper/
│   ├── cltml_research_paper.pdf   # Mirrored publication research paper
│   ├── CLTML_IEEE_Research_Paper.tex # IEEE LaTeX source template
│   ├── Review_Paper_IEEE.html     # Two-column IEEE formatted HTML paper
│   └── figures/                   # High-resolution 300 DPI figures
├── docs/
│   ├── cltml_design_contract.md   # Formal synchronization contract & Cardinal Invariant 1
│   ├── feature_schema.md          # Telemetry counter and feature normalization schema
│   ├── environment.md             # Kernel testbed and development configuration
│   ├── ROADMAP_ALIGNMENT_REPORT.md# Roadmap and stage verification report
│   └── CLTML_Project_Review_Deck.pptx # Project presentation slide deck
└── review/
    ├── reproducibility_readme.md  # Detailed reproduction instructions
    ├── numerical_consistency_audit.md # Mathematical proofs and derivations
    ├── claims_evidence_ledger.csv # Mapping of 30 manuscript claims to verifiable data
    ├── reference_audit.csv        # Audit of authentic references with DOIs
    └── final_peer_review.md       # External peer review report
```

---

## ⚡ Quick Start & Reproduction

### Prerequisites
- **OS:** Linux (evaluated on CachyOS / Arch Linux, Linux 6.8+ LTS)
- **Toolchain:** GCC 14.2+ / Clang 18.1+, `pthread`, `make`, `cmake`
- **Python:** Python 3.10+ with `numpy`, `pandas`, `matplotlib`

### Execute Complete Master Suite
To run all state-space verifications, cycle-accurate timing benchmarks, multi-threaded userspace tests, and the machine learning pipeline:

```bash
./run.sh
```

Or run individual reproduction steps:

#### 1. Validate Lookup Table Bijective Safety (4,096 States)
```bash
python3 scripts/validate_lut_4096.py
```
*Output: 4,096 unique valid states, 0 out-of-bounds violations, 0 invalid codes.*

#### 2. C11 Hot-Path Decision Latency & Stress Harness
```bash
gcc -O3 -march=native -pthread src/cltml_benchmark.c -o src/cltml_benchmark -lm
./src/cltml_benchmark
```
*Output: 4.10 ns decision latency, 10,000,000 quiescent acquisitions with 0 mutual exclusion violations.*

#### 3. Physical Multi-Threaded 4-Lock Benchmark
```bash
gcc -O3 -march=native -pthread src/cltml_userspace_benchmark.c -o src/cltml_userspace_benchmark -lm
./src/cltml_userspace_benchmark
```
*Output: Contention scaling across 1–12 threads for Mutex, Spinlock, Ticket, and MCS locks.*

#### 4. Offline GBDT Training & Regret Analysis Pipeline
```bash
python3 scripts/cltml_pipeline.py --samples 16000
```
*Output: Trains GBDT, verifies teacher agreement (97.42%), compiles 4 KB LUT, and exports `data/cltml_metrics.json`.*

---

## 📊 Summary of Validated Results

| Selector / Model Policy | Memory Footprint | Latency (ns) | TSC Cycles | Speedup vs Float | Oracle Accuracy | Mean Regret | Cost Overhead |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Oracle Selector (Theoretical)** | 0 B | 0.00 ns | — | — | 100.00% | 0.00 ns | +0.00% |
| **CLTML Pre-Binned 12-Bit LUT** | 4 KB | **1.47 ns** | **4.0 cyc** | **242.2×** | 95.05% | 1.04 ns | +0.60% |
| **CLTML Design A (4×3-Bit Inline)** | 4 KB | **4.10 ns** | **11.0 cyc** | **86.8×** | 95.05% | 1.04 ns | +0.60% |
| **Integer GBDT (AOT Expression)** | Native Code | 92.82 ns | 249.5 cyc | 3.8× | 95.23% | 1.10 ns | +0.63% |
| **Full Float GBDT (Pointer-Chase)** | 64 trees (1,900 nodes) | 356.07 ns | 957.1 cyc | 1.0× | 95.23% | 1.10 ns | +0.63% |
| **Static qspinlock Baseline** | 4 B | 0.00 ns | — | — | 35.27% | 86.16 ns | +49.26% |
| **Amortized GBDT (1/1024 acq)** | Stored Pointer | 0.35 ns | 0.9 cyc | — | 21.95% | 136.39 ns | +77.98% |

---

## 📜 Citation & License

```bibtex
@inproceedings{cltml2026,
  author    = {Chandru G and Chethan S},
  title     = {Compile-Time Lookup Tables for Inference-Latency-Bounded Lock Selection in the Linux Kernel: A Constraint Review and Feasibility Study},
  institution = {PES University},
  year      = {2026}
}
```

Licensed under the [Apache License, Version 2.0](LICENSE) or academic open-source license.
