# CLTML Synchronization Contract & Invariant Specification
=============================================================
**Document Version:** 1.0.0 (Stage 0 Deliverable)  
**Author:** CLTML Research Team (PES University, CSE-AIML)  
**Scope:** Linux Kernel Synchronization Architecture & Safe ML Policy Adaptation  

---

## 1. Problem Statement and Scope

CLTML (Compile-Time-Bound Lookup-Table Machine Learning) addresses the inference-latency bottleneck in learned kernel synchronization. Traditional ML models (GBDTs, neural networks) require 300–1,200 ns for inference, which violates the sub-100 ns Linux kernel lock fast-path ceiling by 3× to 12×. 

While CLTML achieves sub-15 ns inference via compile-time quantized lookup tables (LUTs), integrating learned policies into the Linux kernel requires strict adherence to kernel synchronization semantics. In the Linux kernel, locking primitives are not interchangeable black boxes:
1. **`spinlock_t` / `qspinlock`**: Must never sleep; disables kernel preemption; safe in atomic and interrupt contexts.
2. **`mutex`**: May sleep; calls scheduler (`schedule()`); strictly forbidden in atomic, interrupt, or spinlock-holding contexts.
3. **`rcu_read_lock()` / `synchronize_rcu()`**: Non-blocking reader critical sections paired with asynchronous or deferred reclamation; requires explicit epoch reclamation contracts.

This document formally defines the **CLTML Synchronization Contract**, specifying calling contexts, permitted policy spaces, the quiescent-epoch transition protocol, and memory-ordering invariants.

---

## 2. Calling Context Invariants & Execution Boundaries

### 2.1 Execution Context Matrix

| Execution Context | May Sleep? | Preemption Allowed? | Safe with Spinlock? | Safe with Mutex? | CLTML Macro-Policy Switching Allowed? |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **HardIRQ (Interrupt)** | **NO** | NO | YES (`spin_lock_irqsave`) | **NEVER (BUG/Panic)** | **NO** (Parameters must remain invariant) |
| **SoftIRQ / Tasklet / Timer** | **NO** | NO | YES (`spin_lock_bh`) | **NEVER (BUG/Panic)** | **NO** (Parameters must remain invariant) |
| **Atomic / RCU Read Section** | **NO** | NO | YES | **NEVER (BUG/Panic)** | **NO** (Atomic context violation) |
| **Preemptible Task Context** | **YES** | YES | YES (Brief hold) | YES | **YES** (Subject to Quiescent Gate) |

> [!IMPORTANT]
> **Cardinal Invariant 1 (Context Immutability):**  
> Under no circumstances may an active synchronization object switch between a sleeping primitive (`mutex`) and a non-sleeping primitive (`spinlock_t` / `qspinlock`) if callers may invoke the lock from atomic, SoftIRQ, or HardIRQ contexts. Violation invokes `CONFIG_DEBUG_ATOMIC_SLEEP` and results in kernel panic (`BUG: scheduling while atomic`).

---

## 3. Two-Tier Operational Architecture

To balance theoretical research exploration with deployable kernel safety, CLTML defines two operational tiers:

```
+-----------------------------------------------------------------------------------+
|                        CLTML OPERATIONAL ARCHITECTURE                             |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [Tier 1: Kernel In-Band Target]               [Tier 2: Macro Exploration]        |
|  Unified Adaptive Primitive                     Discrete Macro Selection           |
|  (Adaptive Spin-Then-Sleep Mutex)              (Subsystem-Level Specialization)    |
|                                                                                   |
|  - Caller Context: Preemptible Task Context     - Caller Context: Initialization/  |
|  - Synchronization Contract: Identical across     Controlled Subsystem Dispatch   |
|    all policy recommendations                   - Explores trade-offs across:      |
|  - CLTML Action: Dynamic tuning of:               0 = qspinlock (single-socket)   |
|    * Spin retry limit (spin_threshold)            1 = Cohort Lock (NUMA traffic)   |
|    * Exponential backoff scale                    2 = RCU Read-Path (read-heavy)   |
|    * NUMA batch handoff limit                     3 = Adaptive Mutex (high qdepth) |
|  - Safety Guarantee: 100% type safety;         - Safety Guarantee: Fixed at       |
|    zero risk of atomic-sleep violation            object allocation or epoch gate |
+-----------------------------------------------------------------------------------+
```

### 3.1 Tier 1: Unified Adaptive In-Band Primitive (Primary Kernel Milestone)
In Tier 1, the lock primitive is a unified **Adaptive Spin-Then-Sleep Lock (`cltml_adaptive_lock`)**:
- Callers always use standard, consistent locking semantics.
- CLTML tunes **internal execution parameters**:
  - `POLICY_LOW_SPIN`: 0–32 pause spins before sleeping (optimal for long critical sections).
  - `POLICY_MED_SPIN`: 128–256 pause spins (balanced throughput).
  - `POLICY_HIGH_SPIN`: 1024–2048 pause spins (avoids context switch when lock holder is actively running).
  - `POLICY_NUMA_PASS`: Cohort local socket batching limit (4–32 iterations).
- **Semantics are completely invariant to the caller.** The lock preserves mutual exclusion and caller guarantees regardless of the ML recommendation.

### 3.2 Tier 2: Architectural Macro-Primitive Exploration
In Tier 2 (the userspace research exploration), CLTML classifies workload regimes into four archetypes:
- `0 = qspinlock`: Low contention, uncontended fast path.
- `1 = Cohort Lock`: High cross-socket NUMA interconnect traffic.
- `2 = RCU / Seqlock Path`: Read-dominant concurrency ($\ge 80\%$ reads).
- `3 = Adaptive Spin-Then-Sleep Mutex`: High queue depth and high hold-time variance.

Tier 2 applies strictly at object initialization or within subsystems where caller context is guaranteed to be task-context preemptible, guarded by the Quiescent-Epoch Gate.

---

## 4. Quiescent-Epoch State Machine & Transition Protocol

To eliminate race conditions in policy updates (addressing the critique of naive `active_users` counters), CLTML enforces a formal four-state transition protocol:

```
               [ STATE: STABLE ]
              active_policy = P_cur
              staged_policy = P_cur
                     |
                     | cltml_request_policy(P_new)
                     v
               [ STATE: REQUESTED ]
              staged_policy = P_new
                     |
                     | atomic_compare_exchange(STABLE -> TRANSITIONING)
                     v
             [ STATE: TRANSITIONING ]
        Wait for active_epoch readers to reach 0
        (Quiescent Point Linearization)
                     |
                     | epoch_readers[old_epoch] == 0
                     v
               [ STATE: COMMITTED ]
              active_policy = P_new
              epoch = epoch + 1
                     |
                     v
               [ STATE: STABLE ]
```

### 4.1 State Machine Definitions

```c
typedef enum {
    CLTML_STATE_STABLE         = 0,  /* Lock executing under current active policy */
    CLTML_STATE_REQUESTED      = 1,  /* New recommendation staged in staged_policy */
    CLTML_STATE_TRANSITIONING  = 2,  /* Transition initiated; draining old epoch  */
    CLTML_STATE_COMMITTED      = 3   /* Policy committed; advancing epoch counter  */
} cltml_state_t;
```

### 4.2 Linearization Points & Memory Ordering
1. **Policy Staging:** A background or per-CPU sampler computes a recommended policy via `cltml_select_4x3_kernel()` and writes `staged_policy` with `memory_order_release`.
2. **Admission Invariant:** Any thread entering lock acquisition loads `active_policy` and the current `epoch_gen` using `memory_order_acquire`. It registers in `epoch_readers[epoch_gen & 1]`.
3. **Quiescent Point:** A transition is committed if and only if `epoch_readers[active_epoch ^ 1] == 0`.
4. **Transition Commit:** The state atomically transitions from `CLTML_STATE_TRANSITIONING` to `CLTML_STATE_COMMITTED` via `atomic_compare_exchange_strong_explicit` with `memory_order_acq_rel`.
5. **No Partial Visibility:** No thread can observe an inconsistent state or partially updated policy structure.

---

## 5. Fallback & Kill-Switch Guarantees

1. **Static Fallback Policy (`LOCK_POLICY_FALLBACK`):**
   If feature inputs are out of bounds, counters are unavailable, or memory state is corrupted, CLTML immediately resorts to the compile-time static fallback (`qspinlock` for spinning contexts; standard `mutex` for sleeping contexts).
2. **Global Runtime Kill-Switch:**
   Controlled via module parameter / sysfs `/sys/module/cltml_module/parameters/cltml_enabled`. When `cltml_enabled == 0`, all inference lookups are bypassed and default static execution is enforced with zero branching overhead.
3. **Starvation Bound:**
   When cohort batching or adaptive spinning is active, an anti-starvation ticket ceiling (default 64 cross-socket handoffs) ensures remote threads cannot be starved indefinitely.

---

## 6. Summary of Formal Guarantees

| Invariant | Mechanism | Verification Method |
| :--- | :--- | :--- |
| **Mutual Exclusion** | Underlying atomic lock word + acquire/release barriers | Formal assert in stress harness; zero overlap |
| **No Atomic Sleep** | Tier 1 parameter-only adaptation; strict context enforcement | Compile with `CONFIG_DEBUG_ATOMIC_SLEEP` |
| **Zero Memory Corruption** | Dual-epoch reader counter drain before commit | Stress test with 100,000+ transitions |
| **Sub-15 ns Decision Latency** | 4,096-byte `.rodata` array + branchless 3-step quantization | Microbenchmark cycle count (`__rdtsc()`) |
| **Safe Fallback** | Defensive range clamping + static fallback dispatch | Unit tests with NaN/saturated inputs |
