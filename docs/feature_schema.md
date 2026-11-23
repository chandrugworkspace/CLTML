# CLTML Feature Schema & Hardware Counter Specification
=============================================================
**Document Version:** 1.0.0 (Stage 3 Deliverable)  
**Author:** CLTML Research Team (PES University, CSE-AIML)  
**Project:** CLTML Linux Kernel Implementation  

---

## 1. Overview and Feature Definitions

CLTML uses 8 hardware performance counter (PMC) and kernel-derived metrics to characterize concurrency and memory contention regimes. To guarantee zero floating-point operations in kernel space, all features are represented in fixed-point integer arithmetic scaled by `CLTML_FP_SCALE = 100` (e.g., $43.5\% \to 4350$).

### 1.1 Complete 8-Feature Matrix

| Index | Feature Name | Short Desc | Physical Unit | Kernel Fixed-Point Scale | Source in Dataset A (Analytical) | Equivalent PMU Event in Dataset B (Live Kernel) |
| :---: | :--- | :--- | :---: | :---: | :--- | :--- |
| **F0** | `llc_miss_rate` | Last-Level Cache Miss Ratio | % | ×100 (0–10,000) | Calibrated beta distribution | `LLC-load-misses` / `LLC-loads` |
| **F1** | `cross_numa_traffic` | Cross-Socket Interconnect Traffic | MB/s or % | ×100 (0–10,000) | Multi-socket NUMA model | `offcore_response.all_reads.l3_miss_remote` |
| **F2** | `lock_queue_depth` | Average Waiter Queue Length | Threads | ×100 (0–12,800) | Poisson arrival & M/M/1 model | `qspinlock.mcs_nodes` / lockdep depth |
| **F3** | `read_write_ratio` | Proportion of Read Operations | % | ×100 (0–10,000) | Workload read-ratio parameter | Instruction profile (loads vs stores) |
| **F4** | `cas_retry_rate` | Atomic CAS Failure/Retry Ratio | % | ×100 (0–10,000) | Contention collision model | `mem_inst_retired.lock_loads` |
| **F5** | `hold_time_cv` | Critical Section Hold Time CV | Ratio ($\sigma/\mu$) | ×100 (0–5,000) | Log-normal variance model | Lock hold time timestamp delta ($\sigma/\mu$) |
| **F6** | `l3_hit_latency_ns` | Mean L3 Cache Access Latency | Nanoseconds | ×100 (0–5,000) | Architecture baseline (4–20 ns) | PEBS memory load latency profiling |
| **F7** | `cpu_runq_len` | Scheduler Runnable Queue Depth | Tasks | ×100 (0–6,400) | Process scheduling load | `rq->nr_running` (per-CPU runqueue) |

---

## 2. Dataset A (Analytical) vs. Dataset B (Live Kernel PMU)

A primary threat to validity identified in literature surveys is conflating simulated or analytical traces with live hardware measurements. CLTML explicitly segregates data sources:

```
+---------------------------------------------------------------------------------------+
|                               DATASET ARCHITECTURE                                    |
+---------------------------------------------------------------------------------------+
|  [DATASET A: Offline Analytical Synthesis]   [DATASET B: Live Linux Kernel Traces]    |
|  - 16,000 trace windows (12K train / 4K test)- Captured via Linux `perf_event` and     |
|  - Modeled across two distinct regimes:        kernel tracepoints                     |
|    * PARSEC: compute-bound, steady-state     - Hardware: Intel Core 5 210H,           |
|    * SPECjbb2015: bursty NUMA transactions     12 logical CPUs, Linux 7.3.0 CachyOS   |
|  - Calibrated to empirical measurements from - Events: cycles, instructions, LLC      |
|    David et al. [1] & Dice et al. [5]          misses, context-switches, migrations   |
|  - Purpose: GBDT training & LUT compilation  - Purpose: Validating runtime inference  |
|    in pure NumPy across all parameter ranges   under real system noise and jitter     |
+---------------------------------------------------------------------------------------+
```

---

## 3. Sampling Overhead vs. Staleness Trade-Off

Reading hardware performance counters directly on every lock acquisition is physically infeasible:
- **Synchronous PMC Reading (`rdpmc` / `perf_event_read`):** Incurs 120–250 CPU cycles (~40–80 ns) per read, which would consume 50%–100% of the entire 100 ns fast-path budget before executing the lock logic!
- **CLTML Asynchronous Epoch Sampling (Recommended Protocol):**
  - A background per-socket or per-CPU timer (e.g. 10 ms or 100 ms epoch) samples PMCs and updates a per-CPU pre-binned register or cached index.
  - The hot-path lock acquisition reads **only the pre-computed quantized index** (or evaluates the 3-step branchless integer quantizer).
  - **Overhead:** $<0.05\%$ CPU utilization.
  - **Staleness Bound:** Feature inputs reflect the contention regime of the preceding 10 ms window. Because server contention regimes (e.g. batch transactions vs steady-state reads) persist for thousands of lock acquisitions (hundreds of milliseconds), 10 ms staleness causes $<0.8\%$ policy misclassification while saving 98% of PMC reading overhead.

---

## 4. Gain-Based Feature Importance & Subset Selection

Evaluating all 8 counters at runtime would require an index of $2^{24}$ entries (16 MB), destroying L1/L2 cache locality. CLTML solves this by pruning features using GBDT **Gain-Based Feature Importance**:

```
Feature Importance Ranking (GBDT Gain %):
  Rank 1: F3 (read_write_ratio)     : 43.31%  ===============> Captures 98.22%
  Rank 2: F1 (cross_numa_traffic)   : 37.91%  ===============> of total decision
  Rank 3: F2 (lock_queue_depth)     : 15.17%  ===============> gain!
  Rank 4: F4 (cas_retry_rate)       :  1.83%  ===============>
  -------------------------------------------------------------
  Remaining 4 features (F0,F5,F6,F7):  1.78% combined (pruned from LUT)
```

### 4.1 12-Bit Quantization Mapping

#### Design A: 4 Features × 3 Bits = 12 Bits ($8^4 = 4,096$ states, 4.0 KB)
- Features: `F3` (read/write), `F1` (NUMA traffic), `F2` (queue depth), `F4` (CAS retry)
- Each feature is partitioned into 8 quantile bins using 7 fixed-point thresholds.
- Index arithmetic:
  $$\text{idx} = (b_0 \ll 9) \mid (b_1 \ll 6) \mid (b_2 \ll 3) \mid b_3$$

#### Design B: 3 Features × 4 Bits = 12 Bits ($16^3 = 4,096$ states, 4.0 KB)
- Features: `F3` (read/write), `F1` (NUMA traffic), `F2` (queue depth)
- Each feature is partitioned into 16 quantile bins using 15 fixed-point thresholds.
- Index arithmetic:
  $$\text{idx} = (b_0 \ll 8) \mid (b_1 \ll 4) \mid b_2$$
