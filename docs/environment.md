# CLTML Kernel Build Environment & Safety Recovery Guide
=============================================================
**Document Version:** 1.0.0 (Stage 1 Deliverable)  
**Author:** CLTML Research Team (PES University, CSE-AIML)  
**Project:** CLTML Linux Kernel Implementation  

---

## 1. Verified Target System Specification

All kernel module and userspace benchmarks in this directory have been compiled, verified, and benchmarked against the following exact hardware and toolchain environment:

| Property | Value / Configuration |
| :--- | :--- |
| **Operating System** | Linux (Arch-based CachyOS) |
| **Kernel Release (`uname -r`)** | `7.3.0-4-cachyos` |
| **Kernel Architecture** | `x86_64` (Little Endian, 48-bit VA, 39-bit PA) |
| **Kernel Scheduling Model** | `SMP PREEMPT_DYNAMIC` |
| **Host CPU Model** | Intel(R) Core(TM) 5 210H (12 Logical CPUs, 8 Cores) |
| **CPU Microarchitecture** | Raptor Lake / Alder Lake hybrid (64-byte L1/L2/L3 cache lines) |
| **CPU Max Frequency** | 4.80 GHz |
| **Host C Compiler** | `clang version 23.1.4` (Target: `x86_64-pc-linux-gnu`) |
| **Secondary C Compiler** | `gcc (GCC) 16.2.1 20260810` |
| **Kernel Build Tree** | `/lib/modules/7.3.0-4-cachyos/build` (Full Kbuild tree present) |
| **Python Virtual Environment**| `.venv/bin/python` (Python 3.14 + NumPy 2.5.4 + Pandas 3.0.6 + Matplotlib 3.11.2) |

---

## 2. Kbuild Compilation & Toolchain Rules

Because modern high-performance distribution kernels (such as CachyOS) are compiled with Clang/LLVM and enable advanced compiler features (`-fms-anonymous-structs`, `-fsplit-lto-unit`, ThinLTO), out-of-tree kernel modules targeting this kernel must be invoked using Clang as the compiler driver:

### 2.1 Out-of-Tree Kernel Module Build Command
```bash
# Build cltml_module.ko using Clang toolchain against running kernel headers:
make -C /lib/modules/$(uname -r)/build M=$(pwd) CC=clang LLVM=1 modules
```

### 2.2 Userspace C11 Benchmark Build Command
```bash
# Compile native userspace benchmark with GCC or Clang (-O3, native vectorization, pthreads):
gcc -O3 -march=native -Wall -Wextra -pthread cltml_benchmark.c -o cltml_benchmark -lm
```

### 2.3 Complete End-to-End Pipeline Execution
```bash
# Run offline pipeline to train GBDT, compile tables, build headers, and run benchmarks:
./.venv/bin/python cltml_pipeline.py --output-dir .
```

---

## 3. Kernel Debugging Configuration Checklist

When preparing a test environment or disposable virtual machine for CLTML module testing, verify that the kernel configuration (`/proc/config.gz` or `/boot/config-$(uname -r)`) enables the following diagnostic and validation facilities:

| Kernel Config Flag | Purpose for CLTML Validation | Status on Target |
| :--- | :--- | :---: |
| `CONFIG_DEBUG_KERNEL` | Enables kernel debugging infrastructure | Enabled |
| `CONFIG_DEBUG_ATOMIC_SLEEP` | Immediately catches any attempt to sleep or call mutex from atomic/spinlock context | Enabled |
| `CONFIG_PROVE_LOCKING` | Lockdep deadlock detection engine | Optional / Debug |
| `CONFIG_LOCKDEP` | Tracks lock acquisition order and hierarchy | Optional / Debug |
| `CONFIG_KASAN` | Kernel Address Sanitizer (detects out-of-bounds array reads in LUT) | Optional / VM |
| `CONFIG_KCSAN` | Kernel Concurrency Sanitizer (detects race conditions in epoch switching) | Optional / VM |
| `CONFIG_PREEMPT_DYNAMIC` | Supports dynamic preemption models | Enabled |

---

## 4. Module Lifecycle, Testing & Recovery Instructions

> [!CAUTION]
> **Safety Protocol:** Kernel modules execute in Ring 0 (privileged CPU mode). A null pointer dereference, floating-point instruction, or atomic sleep violation will panic or lock up the kernel. Always adhere to the following protocol.

### 4.1 Loading and Exercising the Module
```bash
# 1. Insert module with default parameters (CLTML enabled, 4 worker threads):
sudo insmod cltml_module.ko cltml_enabled=1 cltml_num_threads=4

# 2. Inspect kernel ring buffer output:
sudo dmesg | tail -n 25

# 3. Read runtime statistics from sysfs:
cat /sys/module/cltml_module/parameters/cltml_enabled
cat /sys/module/cltml_module/parameters/cltml_mode

# 4. Trigger safe dynamic kill-switch (disables ML inference, enforces static fallback):
echo 0 | sudo tee /sys/module/cltml_module/parameters/cltml_enabled

# 5. Safely unload module (all worker kthreads are gracefully stopped):
sudo rmmod cltml_module
```

### 4.2 Recovery Procedure in Case of Hang or Crash
1. **Magic SysRq Key Recovery:**
   - If a test module deadlocks, trigger kernel sync and unmount via SysRq:
     `Alt + SysRq + S` (Sync dirty buffers to disk)  
     `Alt + SysRq + U` (Remount filesystems read-only)  
     `Alt + SysRq + B` (Immediate reboot)
2. **GRUB Boot Menu Recovery:**
   - If a kernel panic occurs, reboot into GRUB, choose **Advanced Options**, and select the verified fallback kernel.
3. **Disposable VM Quarantine:**
   - For all high-stress lockdep and KCSAN experiments, execute within a QEMU/KVM virtual machine before deploying to bare-metal hardware.
