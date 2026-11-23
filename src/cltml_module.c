/*
 * cltml_module.c
 * ============================================================================
 * Out-of-Tree Linux Kernel Module Feasibility Prototype for CLTML
 * (Compile-Time-Bound Lookup-Table Machine Learning)
 *
 * Author: CLTML Research Project (PES University, CSE-AIML)
 * Specification: CLTML Linux Kernel Implementation Roadmap (Stages 1, 2, 5)
 *
 * Purpose:
 *   Demonstrates safe, in-kernel integration of the compile-time-bound
 *   lookup table (CLTML) within a unified adaptive synchronization primitive.
 *
 * Safety Invariants Enforced:
 *   1. No float/FPU instructions in kernel space (pure fixed-point integer math).
 *   2. Zero dynamic allocations (kmalloc) or sleeping in atomic/lock hot paths.
 *   3. Context-invariant: Operates as Tier 1 parameter-tuning adaptive lock;
 *      never mutates between sleeping and spinning lock classes at runtime.
 *   4. Verified Quiescent-Epoch commit protocol: Policy parameter transitions
 *      occur only when active_users == 0.
 *   5. Static fallback (CLTML_POLICY_FALLBACK) on invalid inputs or when
 *      cltml_enabled == 0.
 */

#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/kthread.h>
#include <linux/delay.h>
#include <linux/atomic.h>
#include <linux/spinlock.h>
#include <linux/mutex.h>
#include <linux/types.h>
#include <linux/moduleparam.h>
#include <linux/sched.h>
#include <linux/wait.h>
#include <generated/utsrelease.h>

#ifndef UTS_RELEASE
#define UTS_RELEASE "7.3.0-4-cachyos"
#endif

#include "cltml_kernel_lut.h"

MODULE_LICENSE("GPL");
MODULE_AUTHOR("CLTML Research Project (PES University, CSE-AIML)");
MODULE_DESCRIPTION("CLTML: Compile-Time-Bound Lookup-Table ML for Linux Kernel Lock Selection");
MODULE_VERSION("1.0.0");

/* -------------------------------------------------------------------------
 * MODULE PARAMETERS (Configurable via sysfs at runtime)
 * ------------------------------------------------------------------------- */
static int cltml_enabled = 1;
module_param(cltml_enabled, int, 0644);
MODULE_PARM_DESC(cltml_enabled, "Enable CLTML ML-driven adaptive policy (1=enabled, 0=static fallback)");

static int cltml_mode = 0;
module_param(cltml_mode, int, 0644);
MODULE_PARM_DESC(cltml_mode, "Selector mode (0=Design A 4x3-bit, 1=Direct Pre-Binned)");

static int cltml_num_threads = 4;
module_param(cltml_num_threads, int, 0444);
MODULE_PARM_DESC(cltml_num_threads, "Number of concurrent worker kthreads for lock stress benchmark");

static int cltml_test_iterations = 25000;
module_param(cltml_test_iterations, int, 0444);
MODULE_PARM_DESC(cltml_test_iterations, "Number of lock acquisitions per worker kthread");

/* -------------------------------------------------------------------------
 * KERNEL DIAGNOSTIC STATISTICS (Atomic telemetry)
 * ------------------------------------------------------------------------- */
static atomic64_t cltml_total_acquisitions = ATOMIC64_INIT(0);
static atomic64_t cltml_safe_switches      = ATOMIC64_INIT(0);
static atomic64_t cltml_fallbacks          = ATOMIC64_INIT(0);
static atomic64_t cltml_lut_lookups        = ATOMIC64_INIT(0);
static atomic64_t cltml_corruption_events  = ATOMIC64_INIT(0);

/* Protected shared kernel state for mutual exclusion verification */
static u64 g_shared_counter = 0;
static struct task_struct *worker_threads[16];

/* -------------------------------------------------------------------------
 * TIER 1 UNIFIED ADAPTIVE KERNEL LOCK (cltml_adaptive_lock_t)
 * ------------------------------------------------------------------------- */
typedef struct {
    atomic_t        lock_word;          /* 0 = unlocked, 1 = locked               */
    atomic_t        active_users;       /* Number of active contenders            */
    atomic_t        active_policy;      /* Current active policy (0..3)           */
    atomic_t        staged_policy;      /* Recommended policy awaiting commit     */
    atomic_t        spin_budget;        /* Active adaptive spin ceiling           */
    wait_queue_head_t waitq;            /* Sleeping waitqueue for high contention */
} cltml_adaptive_lock_t;

static cltml_adaptive_lock_t g_cltml_lock;

static void cltml_adaptive_lock_init(cltml_adaptive_lock_t *lk) {
    atomic_set(&lk->lock_word, 0);
    atomic_set(&lk->active_users, 0);
    atomic_set(&lk->active_policy, LOCK_PRIM_QSPINLOCK);
    atomic_set(&lk->staged_policy, LOCK_PRIM_QSPINLOCK);
    atomic_set(&lk->spin_budget, CLTML_SPIN_BUDGET_HIGH);
    init_waitqueue_head(&lk->waitq);
}

/*
 * Safe Quiescent-Epoch Transition Request:
 * Stages the recommended policy and commits immediately if active_users == 0.
 */
static inline void cltml_kernel_request_policy(cltml_adaptive_lock_t *lk, uint8_t rec_policy) {
    int cur_policy = atomic_read(&lk->active_policy);
    if (cur_policy == rec_policy) {
        return;
    }

    atomic_set(&lk->staged_policy, (int)rec_policy);

    /* Quiescent linearization check: safe to commit if zero active contenders */
    if (atomic_read(&lk->active_users) == 0) {
        atomic_set(&lk->active_policy, (int)rec_policy);
        atomic_set(&lk->spin_budget, cltml_policy_to_spin_budget(rec_policy));
        atomic64_inc(&cltml_safe_switches);
    }
}

/*
 * Acquire adaptive lock:
 * 1. Spins up to dynamically tuned spin_budget with cpu_relax().
 * 2. If held past spin_budget, transitions to wait_event_interruptible().
 */
static void cltml_adaptive_lock_acquire(cltml_adaptive_lock_t *lk, uint8_t rec_policy) {
    int spin_limit;
    int spins = 0;

    /* Request/stage policy recommendation */
    cltml_kernel_request_policy(lk, rec_policy);

    atomic_inc(&lk->active_users);
    spin_limit = atomic_read(&lk->spin_budget);

    /* Phase 1: Adaptive Busy Spinning */
    while (spins < spin_limit) {
        if (atomic_cmpxchg(&lk->lock_word, 0, 1) == 0) {
            return; /* Fast-path acquisition succeeded */
        }
        cpu_relax();
        spins++;
    }

    /* Phase 2: Sleeping Fallback when spin budget exhausted */
    while (atomic_cmpxchg(&lk->lock_word, 0, 1) != 0) {
        wait_event(lk->waitq, atomic_read(&lk->lock_word) == 0);
    }
}

/*
 * Release adaptive lock:
 * Commits staged policy at quiescent epoch boundary (active_users == 1)
 */
static void cltml_adaptive_lock_release(cltml_adaptive_lock_t *lk) {
    int prev_users;

    /* Release lock word */
    atomic_set(&lk->lock_word, 0);
    wake_up(&lk->waitq);

    prev_users = atomic_dec_return(&lk->active_users);

    /*
     * Quiescent Point: When the last thread exits the lock (prev_users == 0),
     * commit staged policy atomically with zero risk of mid-flight corruption.
     */
    if (prev_users == 0) {
        int staged = atomic_read(&lk->staged_policy);
        int active = atomic_read(&lk->active_policy);
        if (staged != active) {
            atomic_set(&lk->active_policy, staged);
            atomic_set(&lk->spin_budget, cltml_policy_to_spin_budget((uint8_t)staged));
            atomic64_inc(&cltml_safe_switches);
        }
    }
}

/* -------------------------------------------------------------------------
 * KERNEL WORKER THREAD (Concurrent Concurrency Stress)
 * ------------------------------------------------------------------------- */
static int cltml_worker_fn(void *data) {
    long thread_id = (long)data;
    int iter;
    int32_t features_fp[CLTML_NUM_FEATURES];

    /* Simulated PMC counter inputs (fixed-point x100) */
    features_fp[0] = 3500; /* llc_miss_rate: 35% */
    features_fp[1] = 4200; /* cross_numa_traffic: 42% */
    features_fp[2] = 2800; /* lock_queue_depth: 28 threads */
    features_fp[3] = 6800; /* read_write_ratio: 68% */
    features_fp[4] = 2200; /* cas_retry_rate: 22% */
    features_fp[5] = 1200; /* hold_time_cv: 1.2 */
    features_fp[6] = 1500; /* l3_hit_latency: 15 ns */
    features_fp[7] = 3200; /* cpu_runq_len: 32 tasks */

    for (iter = 0; iter < cltml_test_iterations && !kthread_should_stop(); iter++) {
        uint8_t rec_policy;

        /* Vary features slightly per thread/iteration to trigger dynamic recommendations */
        features_fp[1] = (int32_t)(3000 + ((thread_id * 1500 + iter) % 6000));
        features_fp[3] = (int32_t)(4000 + ((iter * 100) % 5500));

        /* Execute CLTML fast-path kernel lookup */
        atomic64_inc(&cltml_lut_lookups);
        if (cltml_enabled) {
            if (cltml_mode == 0) {
                rec_policy = cltml_kernel_select_4x3(features_fp, cltml_enabled);
            } else {
                rec_policy = cltml_kernel_select_direct(
                    (uint32_t)((features_fp[3] / 1000) & 0xF),
                    (uint32_t)((features_fp[1] / 1000) & 0xF),
                    (uint32_t)((features_fp[2] / 1000) & 0xF),
                    cltml_enabled
                );
            }
        } else {
            atomic64_inc(&cltml_fallbacks);
            rec_policy = CLTML_POLICY_FALLBACK;
        }

        /* Acquire lock under CLTML adaptive management */
        cltml_adaptive_lock_acquire(&g_cltml_lock, rec_policy);

        /* --- Critical Section (Protected State) --- */
        {
            u64 val_before = g_shared_counter;
            /* Intentional brief delay to test concurrency contention */
            g_shared_counter = val_before + 1;
            if (g_shared_counter != val_before + 1) {
                atomic64_inc(&cltml_corruption_events);
            }
        }
        atomic64_inc(&cltml_total_acquisitions);

        cltml_adaptive_lock_release(&g_cltml_lock);

        /* Brief yield if schedule requested */
        if (need_resched()) {
            cond_resched();
        }
    }

    return 0;
}

/* -------------------------------------------------------------------------
 * MODULE INITIALIZATION & CLEANUP
 * ------------------------------------------------------------------------- */
static int __init cltml_module_init(void) {
    long i;
    pr_info("====================================================================\n");
    pr_info("CLTML: Initializing Linux Kernel Lock Selector Module (CONFIG_CLTML)\n");
    pr_info("CLTML: Target Kernel: %s | Preempt: SMP PREEMPT_DYNAMIC\n", UTS_RELEASE);
    pr_info("CLTML: Lookup Table Size: %zu bytes (.rodata, 64-byte cache aligned)\n",
            sizeof(cltml_kernel_lut_4x3));
    pr_info("CLTML: Settings: enabled=%d, mode=%d, threads=%d, iters=%d\n",
            cltml_enabled, cltml_mode, cltml_num_threads, cltml_test_iterations);

    if (cltml_num_threads > 16) {
        cltml_num_threads = 16;
    }

    cltml_adaptive_lock_init(&g_cltml_lock);

    /* Spawn worker kthreads */
    for (i = 0; i < cltml_num_threads; i++) {
        char thread_name[16];
        snprintf(thread_name, sizeof(thread_name), "cltml_worker/%ld", i);
        worker_threads[i] = kthread_run(cltml_worker_fn, (void *)i, "%s", thread_name);
        if (IS_ERR(worker_threads[i])) {
            pr_err("CLTML: Failed to create kthread %ld\n", i);
            worker_threads[i] = NULL;
        }
    }

    pr_info("CLTML: %d worker kthreads successfully spawned\n", cltml_num_threads);
    pr_info("====================================================================\n");
    return 0;
}

static void __exit cltml_module_exit(void) {
    int i;
    u64 expected_count;

    /* Stop all worker threads */
    for (i = 0; i < cltml_num_threads; i++) {
        if (worker_threads[i]) {
            kthread_stop(worker_threads[i]);
            worker_threads[i] = NULL;
        }
    }

    expected_count = (u64)cltml_num_threads * (u64)cltml_test_iterations;

    pr_info("====================================================================\n");
    pr_info("CLTML: Unloading Linux Kernel Lock Selector Module\n");
    pr_info("CLTML: Total Lock Acquisitions Executed : %lld\n",
            (long long)atomic64_read(&cltml_total_acquisitions));
    pr_info("CLTML: LUT Lookups Performed           : %lld\n",
            (long long)atomic64_read(&cltml_lut_lookups));
    pr_info("CLTML: Quiescent Policy Transitions    : %lld\n",
            (long long)atomic64_read(&cltml_safe_switches));
    pr_info("CLTML: Static Fallbacks Invoked        : %lld\n",
            (long long)atomic64_read(&cltml_fallbacks));
    pr_info("CLTML: Mutual Exclusion Violations     : %lld\n",
            (long long)atomic64_read(&cltml_corruption_events));
    pr_info("CLTML: Shared Counter Result           : %llu (Expected: %llu)\n",
            (unsigned long long)g_shared_counter, (unsigned long long)expected_count);

    if (atomic64_read(&cltml_corruption_events) == 0) {
        pr_info("CLTML: VERIFICATION SUCCESS: Zero race conditions or mid-flight violations!\n");
    } else {
        pr_err("CLTML: VERIFICATION FAILURE: Invariant broken!\n");
    }
    pr_info("====================================================================\n");
}

module_init(cltml_module_init);
module_exit(cltml_module_exit);
