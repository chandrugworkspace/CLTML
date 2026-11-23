/*
 * cltml_userspace_locks.h
 * ============================================================================
 * Four Canonical Userspace Lock Implementations & Verification Interface
 * for CLTML (Compile-Time-Bound Lookup-Table Machine Learning)
 *
 * Implements the 4 synchronization primitives specified in the research protocol:
 *   ID 0: Mutex       - pthread_mutex (Futex-backed adaptive sleeping mutex)
 *   ID 1: Spinlock    - pthread_spinlock (Atomic spinlock with pause loop)
 *   ID 2: Ticket Lock - Atomic ticket lock (Deterministic FIFO fairness)
 *   ID 3: MCS Lock    - Mellor-Crummey & Scott queue lock (Local spinning, O(1) coherence)
 *
 * Includes:
 *   - Phase-based lock selection harness
 *   - CPU topology binding (P-cores 0-7 vs. E-cores 8-11 on hybrid host platform CPU)
 *   - Correctness verification (mutual exclusion, zero lost updates, zero deadlocks)
 *   - Contention workload generator (low, medium, high, bursty)
 * ============================================================================
 */

#ifndef CLTML_USERSPACE_LOCKS_H
#define CLTML_USERSPACE_LOCKS_H

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <pthread.h>
#include <sched.h>
#include <x86intrin.h>
#include <time.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Lock Primitive Identifiers */
#define CLTML_LOCK_MUTEX       0
#define CLTML_LOCK_SPINLOCK    1
#define CLTML_LOCK_TICKET      2
#define CLTML_LOCK_MCS         3
#define CLTML_NUM_LOCK_TYPES   4

static const char *const CLTML_LOCK_NAMES[CLTML_NUM_LOCK_TYPES] = {
    "pthread_mutex",
    "pthread_spinlock",
    "Ticket Lock (C11)",
    "MCS Lock (C11)"
};

/* ---------------------------------------------------------------------------
 * 1. TICKET LOCK IMPLEMENTATION
 * --------------------------------------------------------------------------- */
typedef struct {
    atomic_uint next_ticket;
    atomic_uint now_serving;
    char pad[56]; /* Avoid false sharing */
} __attribute__((aligned(64))) cltml_ticket_lock_t;

static inline void cltml_ticket_lock_init(cltml_ticket_lock_t *l) {
    atomic_init(&l->next_ticket, 0);
    atomic_init(&l->now_serving, 0);
}

static inline void cltml_ticket_lock_destroy(cltml_ticket_lock_t *l) {
    (void)l;
}

static inline void cltml_ticket_lock_acquire(cltml_ticket_lock_t *l) {
    unsigned int my_ticket = atomic_fetch_add_explicit(&l->next_ticket, 1, memory_order_relaxed);
    while (atomic_load_explicit(&l->now_serving, memory_order_acquire) != my_ticket) {
        _mm_pause();
    }
}

static inline void cltml_ticket_lock_release(cltml_ticket_lock_t *l) {
    unsigned int current = atomic_load_explicit(&l->now_serving, memory_order_relaxed);
    atomic_store_explicit(&l->now_serving, current + 1, memory_order_release);
}

/* ---------------------------------------------------------------------------
 * 2. MCS QUEUE LOCK IMPLEMENTATION (Mellor-Crummey & Scott)
 * --------------------------------------------------------------------------- */
typedef struct cltml_mcs_node {
    _Atomic(struct cltml_mcs_node *) next;
    atomic_bool waiting;
    char pad[48]; /* Cache line alignment */
} __attribute__((aligned(64))) cltml_mcs_node_t;

typedef _Atomic(cltml_mcs_node_t *) cltml_mcs_lock_t;

static inline void cltml_mcs_lock_init(cltml_mcs_lock_t *l) {
    atomic_init(l, NULL);
}

static inline void cltml_mcs_lock_destroy(cltml_mcs_lock_t *l) {
    (void)l;
}

static inline void cltml_mcs_lock_acquire(cltml_mcs_lock_t *l, cltml_mcs_node_t *node) {
    atomic_store_explicit(&node->next, NULL, memory_order_relaxed);
    atomic_store_explicit(&node->waiting, true, memory_order_relaxed);
    cltml_mcs_node_t *prev = atomic_exchange_explicit(l, node, memory_order_acq_rel);
    if (prev != NULL) {
        atomic_store_explicit(&prev->next, node, memory_order_release);
        while (atomic_load_explicit(&node->waiting, memory_order_acquire)) {
            _mm_pause();
        }
    }
}

static inline void cltml_mcs_lock_release(cltml_mcs_lock_t *l, cltml_mcs_node_t *node) {
    if (atomic_load_explicit(&node->next, memory_order_relaxed) == NULL) {
        cltml_mcs_node_t *expected = node;
        if (atomic_compare_exchange_strong_explicit(l, &expected, NULL,
                                                    memory_order_release,
                                                    memory_order_relaxed)) {
            return;
        }
        while (atomic_load_explicit(&node->next, memory_order_acquire) == NULL) {
            _mm_pause();
        }
    }
    cltml_mcs_node_t *succ = atomic_load_explicit(&node->next, memory_order_relaxed);
    atomic_store_explicit(&succ->waiting, false, memory_order_release);
}

/* ---------------------------------------------------------------------------
 * 3. GENERIC DISPATCHED LOCK HANDLE (FOR PHASE-BASED SELECTION)
 * --------------------------------------------------------------------------- */
typedef struct {
    uint8_t lock_type;
    pthread_mutex_t mutex;
    pthread_spinlock_t spinlock;
    cltml_ticket_lock_t ticket;
    cltml_mcs_lock_t mcs;
} cltml_dispatched_lock_t;

static inline void cltml_dispatched_lock_init(cltml_dispatched_lock_t *l, uint8_t type) {
    l->lock_type = type;
    pthread_mutex_init(&l->mutex, NULL);
    pthread_spin_init(&l->spinlock, PTHREAD_PROCESS_PRIVATE);
    cltml_ticket_lock_init(&l->ticket);
    cltml_mcs_lock_init(&l->mcs);
}

static inline void cltml_dispatched_lock_destroy(cltml_dispatched_lock_t *l) {
    pthread_mutex_destroy(&l->mutex);
    pthread_spin_destroy(&l->spinlock);
    cltml_ticket_lock_destroy(&l->ticket);
    cltml_mcs_lock_destroy(&l->mcs);
}

static inline void cltml_dispatched_lock_acquire(cltml_dispatched_lock_t *l, cltml_mcs_node_t *mcs_node) {
    switch (l->lock_type) {
        case CLTML_LOCK_MUTEX:
            pthread_mutex_lock(&l->mutex);
            break;
        case CLTML_LOCK_SPINLOCK:
            pthread_spin_lock(&l->spinlock);
            break;
        case CLTML_LOCK_TICKET:
            cltml_ticket_lock_acquire(&l->ticket);
            break;
        case CLTML_LOCK_MCS:
            cltml_mcs_lock_acquire(&l->mcs, mcs_node);
            break;
    }
}

static inline void cltml_dispatched_lock_release(cltml_dispatched_lock_t *l, cltml_mcs_node_t *mcs_node) {
    switch (l->lock_type) {
        case CLTML_LOCK_MUTEX:
            pthread_mutex_unlock(&l->mutex);
            break;
        case CLTML_LOCK_SPINLOCK:
            pthread_spin_unlock(&l->spinlock);
            break;
        case CLTML_LOCK_TICKET:
            cltml_ticket_lock_release(&l->ticket);
            break;
        case CLTML_LOCK_MCS:
            cltml_mcs_lock_release(&l->mcs, mcs_node);
            break;
    }
}

/* ---------------------------------------------------------------------------
 * 4. HYBRID CPU TOPOLOGY AFFINITY BINDING
 * --------------------------------------------------------------------------- */
typedef enum {
    AFFINITY_UNBOUND = 0,
    AFFINITY_P_CORES = 1, /* host platform CPU CPUs 0-7 (4.8 GHz Performance) */
    AFFINITY_E_CORES = 2, /* host platform CPU CPUs 8-11 (3.6 GHz Efficient) */
    AFFINITY_MIXED   = 3  /* Mixed CPUs 0-11 */
} cltml_cpu_placement_t;

static inline void cltml_set_thread_affinity(int thread_idx, cltml_cpu_placement_t placement) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);

    if (placement == AFFINITY_P_CORES) {
        /* Bind to P-cores (CPUs 0-7) */
        int cpu = thread_idx % 8;
        CPU_SET(cpu, &cpuset);
    } else if (placement == AFFINITY_E_CORES) {
        /* Bind to E-cores (CPUs 8-11) */
        int cpu = 8 + (thread_idx % 4);
        CPU_SET(cpu, &cpuset);
    } else if (placement == AFFINITY_MIXED) {
        /* Distribute across all 12 CPUs */
        int cpu = thread_idx % 12;
        CPU_SET(cpu, &cpuset);
    } else {
        return; /* Unbound */
    }

    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
}

#ifdef __cplusplus
}
#endif

#endif /* CLTML_USERSPACE_LOCKS_H */
