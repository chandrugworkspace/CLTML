# Reproducibility & Artifact Audit Report: CLTML Research Project

**Date:** 2026-11-01  
**Project:** Compile-Time Lookup Tables for Inference-Latency-Bounded Lock Selection in the Linux Kernel (CLTML)  
**Host Platform:** Intel Core 5 210H (8 physical cores / 12 logical threads: 4 P-cores @ up to 4.80 GHz, 4 E-cores @ 3.60 GHz, 12 MB L3 cache)  
**Operating System:** CachyOS Linux (Kernel 7.3.0-4-cachyos, x86_64, Linux 6.8+ LTS compatible)  
**Toolchain:** GCC 14.2.1, Clang/LLVM 18.1.8, Python 3.14 / venv Python 3.12 (LightGBM, scikit-learn, numpy, pandas)

---

## 1. Reproducibility Matrix

| Research Result / Claim | Script / Harness | Input Data | Target Environment | Verified Output / Artifact |
|---|---|---|---|---|
| **Exhaustive LUT 4,096-State Safety** | `scripts/validate_lut_4096.py` | `src/cltml_kernel_lut.h` | Standalone Python 3 | 4,096 bijective states, 0 out-of-bounds, 0 invalid codes |
| **Inline LUT Lookup Latency (3.76 ns)**| `src/cltml_benchmark.c` | Model table in L1 | Intel Core 5 210H, serialized `__rdtscp` | 10M acquisitions: 3.76 ns inline (10.1 TSC cycles), p95 4.26 ns |
| **Offline GBDT & Quantization (95.05%)**| `scripts/cltml_pipeline.py` | 16,000 calibrated trace windows | LightGBM, float & 12-bit int | Accuracy: 95.23% (GBDT) $\to$ 95.05% (LUT), Regret: 1.04 ns |
| **Real Empirical Trace Evaluation** | `scripts/cltml_pipeline.py` | `data/cltml_empirical_traces.csv` | 4,000 physical hardware traces | Accuracy: 99.48% (GBDT), 90.55% (CLTML LUT) |
| **Amortization Lag Sensitivity Sweep** | `scripts/cltml_pipeline.py` | Trace windows with phase shifts | Epochs $E \in \{16, 32, 64, 128, 256, 1024\}$ | Total overhead: 113.54 ns ($E=16$) to 136.72 ns ($E=1024$) |
| **End-to-End Multi-Threaded Benchmark**| `src/cltml_userspace_benchmark.c`| Bimodal phase-shifting workload | 1 to 12 threads, 10 repetitions | 12T: 7.48 ± 0.03 Mops (+17.6% over spinlock, +158% over MCS) |
| **Mutual Exclusion & Zero Lost Updates**| `src/cltml_userspace_benchmark.c`| Counter increment stress test | 4 threads × 200,000 increments | 800,000 / 800,000 counter match, 0 lost updates, 0 deadlocks |
| **Userspace Quiescent Guard Stress** | `src/cltml_benchmark.c` | Concurrent policy replacement | 12 threads, 238,262 switches | 0 stale dereferences, 0 use-after-free, 0 race conditions |
| **Kernel Module Spin-Ceiling Tuning** | `src/cltml_module.c` | `insmod cltml_module.ko` | Linux 7.3.0 kernel space | 4 kthreads, 100,000 iters, 14,562 safe switches, 0 crashes |
| **Static Kernel Stack Footprint (<64 B)**| `gcc -fstack-usage` | `src/cltml_kernel_lut.h` | GCC `-O3` x86_64 target | `cltml_kernel_select_4x3`: 8 to 32 bytes static stack frame |
| **NUMA Interconnect Throughput Scaling**| `scripts/generate_figures.py` | Queuing transfer model $L(c)$ | Analytical simulation (1–64 cores) | Static: 2.1 Mops/s collapse; CLTML: 42.5 Mops/s sustained |

---

## 2. Step-by-Step Reproduction Instructions

### 2.1 Reproducing Exhaustive 4,096 Lookup Table State Validation
```bash
python3 scripts/validate_lut_4096.py
```
*Expected Output:*
```
Total states evaluated: 4096
Unique indices generated: 4096
Missing indices in [0, 4095]: 0
Out-of-bounds indices: 0
Invalid policy codes: 0
SUCCESS: All 4,096 states covered bijectively with zero violations!
```

### 2.2 Compiling & Running the Physical End-to-End Multi-Threaded Benchmark
```bash
gcc -O3 -march=native -pthread src/cltml_userspace_benchmark.c -o src/cltml_userspace_benchmark
./src/cltml_userspace_benchmark
```
*Expected Output:*
```
[Component 5] End-to-End Bimodal Multi-Threaded Workload Benchmark (10 repetitions)
  12 Threads:
    Static Mutex:    4.00 +- 0.02 Mops/s
    Static Spinlock: 6.36 +- 0.15 Mops/s
    Static Ticket:   2.30 +- 0.03 Mops/s
    Static MCS:      2.90 +- 0.04 Mops/s
    CLTML Dynamic:   7.48 +- 0.03 Mops/s (+17.6% net gain over best static baseline)
  Saved 4,000 empirical traces to data/cltml_empirical_traces.csv
```

### 2.3 Running the Complete Offline ML & Regret Evaluation Pipeline
```bash
.venv/bin/python scripts/cltml_pipeline.py --samples 16000
```
*Expected Output:*
```
Training LightGBM model...
Evaluating baselines...
  Float GBDT:     Accuracy = 95.23%, Total Overhead = 336.30 ns
  CLTML Design A: Accuracy = 95.05%, Total Overhead = 4.80 ns (70x reduction)
  Empirical Traces: GBDT = 99.48%, CLTML LUT = 90.55%
Amortization Sweep:
  Epoch 16:   Total Overhead = 113.54 ns
  Epoch 1024: Total Overhead = 136.72 ns
Exported data/cltml_metrics.json successfully!
```

### 2.4 Building and Testing the Out-of-Tree Linux Kernel Module
```bash
cd src && make
sudo insmod cltml_module.ko
dmesg | tail -n 10
sudo rmmod cltml_module
```
*Expected Output:*
```
[  142.809112] cltml: module verification starting with 4 kthreads, 100000 iterations
[  143.104285] cltml: all kthreads completed successfully; safe epoch switches: 14562
[  143.104288] cltml: VERIFICATION SUCCESS: Zero race conditions or mid-flight violations!
```

---

## 3. Disclosed Threats to Reproducibility & Hardware Dependencies

1. **Physical Silicon vs. Multi-Socket Servers:** Physical microbenchmarks were executed on an Intel Core 5 210H hybrid processor. All multi-socket NUMA scaling results (32 and 64 cores) are explicitly designated as **analytically modeled projections** using David et al.'s queuing transfer equation.
2. **Timer Serialization:** Timing depends on invariant Time Stamp Counter (TSC) availability (`__rdtscp`). On non-x86 architectures (e.g. ARM64), equivalent cycle counters (`CNTVCT_EL0`) must be substituted.
3. **Kernel Version Compatibility:** The out-of-tree module was built and verified on Linux kernel 7.3.0-4-cachyos. Mainline LTS compatibility spans Linux 6.8+ LTS; earlier kernels prior to 5.4 require legacy mutex structure definitions.
