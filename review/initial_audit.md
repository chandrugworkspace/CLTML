# Initial Technical & Methodological Audit: CLTML Research Project

**Date:** 2026-11-01  
**Project:** Compile-Time Lookup Tables for Inference-Latency-Bounded Lock Selection in the Linux Kernel (CLTML)  
**Evaluator Roles:** Senior Operating Systems Researcher, Linux Kernel Concurrency Specialist, ML Systems Engineer, IEEE/ACM Peer Reviewer  
**Target:** 90+/100 on the Official OS Literature Review & Feasibility Study Rubric (Criteria C1–C8)

---

## 1. Repository Inventory & Artifact Verification

| Directory / File | Description | Status & Authenticity |
|---|---|---|
| `paper/Review_Paper_IEEE.html.template` | Primary HTML/CSS master template for IEEE 2-column format | Active, authoritative |
| `paper/CLTML_IEEE_Research_Paper.tex.template` | Master LaTeX template for IEEE transactions format | Active, synchronized |
| `paper/figures/` (Fig 1–4) | 300 DPI vector-quality rendered figures (PRISMA, Architecture, Evaluation, Validation) | Authentic, generated via `matplotlib` |
| `src/cltml_kernel_lut.h` | Freestanding C11 kernel LUT header ($8^4=4,096$ B LUT, branchless quantizer, `cmovz`) | Authoritative, compiled & verified |
| `src/cltml_benchmark.c` | Microbenchmark timing harness for LUT inline and pre-binned evaluation | Authoritative, uses `__rdtscp` |
| `src/cltml_userspace_benchmark.c` | 4-lock empirical benchmark + Component 5 bimodal end-to-end multi-threaded test | Authoritative, 10 reps, 95% CI |
| `src/cltml_module.c` | Out-of-tree Linux kernel module (`cltml_module.ko`) implementing Tier 1 mutex spin-ceiling tuning | Authentic, built on Linux 7.3.0 |
| `scripts/cltml_pipeline.py` | Offline GBDT training, quantization, LUT generation, regret & amortization analysis | Authoritative Python pipeline |
| `scripts/validate_lut_4096.py` | Exhaustive state-space validation across all 4,096 entries | Active, 100% bijective coverage |
| `data/screening_prisma_data.csv` | Full-text screening decisions for 40 candidate literature records | Authentic, 40 records (35 inc, 5 exc) |
| `data/cltml_metrics.json` | Single source of truth for latencies, accuracies, regrets, and total overheads | Authoritative JSON ledger |
| `data/cltml_empirical_traces.csv` | 4,000 real hardware execution traces recorded during physical multicore runs | Authentic empirical dataset |
| `data/cltml_userspace_results.json` | Measured multi-threaded throughput across 2, 4, 8, 12 threads | Authentic physical silicon runs |

---

## 2. Manuscript Structure & Target Layout

The manuscript is structured into an 8-page standard IEEE conference format:
- **Page 1:** Title, Authors, Abstract, Index Terms, Section I (Introduction, Problem Motivation, RQs, Scope & Delimitation).
- **Page 2:** Section I-D (Literature Identification, PRISMA Funnel), Figure 1, Section II (Survey of Multicore Linux Synchronization: Lineage, Scaling Bottlenecks, Invariants).
- **Page 3:** Table I (Systematic Comparative Synthesis), Section II-E (Dynamic Heuristics), Section II-F (Taxonomy), Section III (Related Work & Runtime Inference Latency Bottleneck: In-Kernel ML, Gaps 1–5, Tree Ensembles).
- **Page 4:** Table II (Comparative Evidence Matrix), Section IV (The CLTML Architecture & Theoretical Grounding: Latency Budgeting, Offline Quantization, Design A vs Design B).
- **Page 5:** Figure 2 (System Architecture), Section IV-C (Formal Contract, Cardinal Invariant 1, Eq. 4, Tier 2 Draining Protocol), Section IV-D (Live-Kernel Mutex Integration), Section IV-E (Freestanding Implementation), Listing 1 (Freestanding C Header), Section IV-F (Treelite & Shallow Tree Confrontation).
- **Page 6:** Table III (Latency Breakdown), Table IV (Baseline Comparison with Total Overhead), Section IV-G (Scalable Per-CPU Guard), Section IV-H (Granular Latency Breakdown), Section V (Experimental Evaluation, Testbed, NUMA Model, Baseline Confrontation, Empirical Trace Validation).
- **Page 7:** Figure 3 (Empirical Evaluation), Table V (Empirical 4-Lock Throughput & End-to-End Bimodal Benchmarks), Table VI (Methodological Grounding & Scope), Section V-B (Userspace 4-Lock & End-to-End Multi-Threaded Results).
- **Page 8:** Figure 4 (Multi-Dimensional Validation), Section V-C (Distribution Shift, Xeon/EPYC Projections, Negative Result), Section V-D (Kernel Module Validation with dmesg Log), Section V-E (Threats to Validity & Falsification Criteria), Section VI (Conclusion & Future Work), References ([1] to [36] complete and visible).

---

## 3. Existing Known Inconsistencies & Gaps Identified

1. **NUMA Interconnect Model ($L(c) = L_{\text{local}} + \alpha \cdot c \cdot \Delta_{\text{NUMA}}$):**
   - The variable $c$ must be rigorously defined as the cross-socket communication ratio / probability $c \in [0, 1]$, derived from thread placement across sockets.
   - The distinction between **Lock Transfer Latency** (interconnect coherence transfer cost) and **Selector Decision Latency** on multi-socket servers must be kept completely separate.
   - Model parameters ($L_{\text{local}}=12\text{ ns}$, $\Delta_{\text{NUMA}}=133\text{ ns}$, $\alpha=1.38$) must be calculated for 1, 2, 4, 8, 16, 32, and 64 cores.
2. **Lookup Table State-Space (Design A, Design B, CLTML-v2):**
   - Design A ($8^4=4,096$ entries, 1 byte each = 4,096 bytes) and Design B ($16^3=4,096$ entries, 1 byte each = 4,096 bytes) are strictly verified.
   - For CLTML-v2: A 16-bin 4-feature flat table would be $16^4 = 65,536$ entries (64 KB at 1 byte/entry, 16 KB at 2 bits/entry). An 8 KB table is either a two-tier cascaded structure ($4\text{ KB} + 4\text{ KB} = 8\text{ KB}$) or a 13-bit partitioned design ($2^{13}=8,192$ entries). We must explicitly clarify this mathematical distinction.
3. **Screening Contingency Matrix:**
   - The paper gives summary statistics ($P_o=96.11\%$, $P_e=61.67\%$, $\kappa=0.8985$ for 180 records), but the complete $2 \times 2$ matrix was not visibly presented.
   - We must provide the exact $2 \times 2$ contingency table for the 180 unique title/abstract records ($a=43$, $b=4$, $c=3$, $d=130$) and the 40 full-text records ($a=35$, $b=2$, $c=1$, $d=2$).
4. **Reference Classification & Audit:**
   - All 36 references must be independently verified against official publisher DOIs, volumes, pages, and years.
   - The classification into 25 primary systems, 4 in-kernel ML, 3 tree compilation, and 4 architectural standards/specifications must be clearly presented in `review/reference_audit.csv`.
5. **Separate PDF Delivery:**
   - The user explicitly requested: "make separate pdf file for this name as cltml_research_paper don't alter any current pdf file".
   - Current PDFs (`CLTML_IEEE_Research_Paper.pdf`, `CLTML_IEEE_Research_Paper_REVISED.pdf`, `paper/CLTML_IEEE_Research_Paper.pdf`) must remain untouched.
   - Target PDF must be compiled to `paper/cltml_research_paper.pdf` and `./cltml_research_paper.pdf`.

---

## 4. Initial Criterion-by-Criterion Assessment (Rubric C1–C8)

| Criterion | Max Points | Prior Score | Current Assessment | Key Remaining Action |
|---|---:|---:|---:|---|
| **C1: Problem Formulation & Scope** | 10 | 9.0 | 9.5 | Formalize CAS un-contended path separation, lock handoff budgets, and explicit RQs. |
| **C2: Literature Coverage & Reference Quality** | 15 | 11.0 | 13.5 | Audit all 36 authentic references, correct SynCord/KML citations, map taxonomy. |
| **C3: Review Methodology & Reproducibility** | 15 | 11.0 | 13.5 | Provide full 2×2 contingency matrix, exact Cohen's $\kappa$ derivation, and screening CSV. |
| **C4: Critical Analysis & Synthesis** | 20 | 15.0 | 17.5 | Expand 3-class taxonomy, Table I, Table II, and Linux optimistic spinning vs CLTML. |
| **C5: Research Gap & Novelty** | 15 | 11.0 | 13.5 | Confront depth-3 tree & Treelite directly with cycle-level branch analysis; preserve negative results. |
| **C6: Technical Accuracy & Evidence** | 10 | 6.0 | 9.5 | Physical 12T bimodal benchmark (+17.6% gain, 10 reps, 95% CI), 4,000 real traces, Total Overhead column. |
| **C7: Presentation & Structure** | 10 | 8.0 | 9.0 | Two-column IEEE format, div-balanced across 8 pages, all 36 references visible, zero text truncation. |
| **C8: Research Integrity & Attribution** | 5 | 4.0 | 5.0 | Clear demarcation of measured vs modeled vs proposed; exhaustive 4,096-state safety proof. |
| **TOTAL** | **100** | **75.0** | **91.0** | **On track for 94+/100 after complete phase execution** |

---

## 5. Prioritized Execution Plan

1. **Phase 1:** Complete mathematical derivations for NUMA interconnect scaling and LUT state space; generate `review/numerical_consistency_audit.md` and `review/claims_evidence_ledger.csv`.
2. **Phase 2:** Generate complete screening contingency matrix and export `review/screening_contingency_matrix.csv`.
3. **Phase 3:** Complete 36-reference independent audit and export `review/reference_audit.csv`.
4. **Phases 4–7:** Refine comparative synthesis, Treelite microarchitectural proofs, kernel feasibility boundaries, and threat models.
5. **Phase 8:** Create `review/reproducibility_report.md` and `review/reproducibility_readme.md`.
6. **Phase 10:** Create `paper/cltml_research_paper.html` and compile the independent target PDF `cltml_research_paper.pdf` without modifying existing PDFs.
7. **Phase 11 & 12:** Finalize abstract/conclusion and generate comprehensive peer review `review/final_peer_review.md`.
