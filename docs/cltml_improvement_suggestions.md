# CLTML Paper: Improvement Suggestions

Current score: **64/100** (band 50–64). Realistic target after the fixes below: **75–80**.
Items are ordered by priority. Reference claims marked *verify* are from reviewer knowledge and must be checked against the real sources.

---

## P0. Fix before anything else (integrity risks)

### 1. Correct the reference list
| Ref | Problem | Action |
|---|---|---|
| [13] | LAKE (ASPLOS 2023) authors are Fingler, Tarte, Yu, Szekely, Akella, Rossbach, not "Eizenberg, Shao". Body text repeats the wrong name. LAKE is accelerator offload for kernel ML, not locks. | Fix authors in list and text. Describe LAKE accurately. |
| [8] | CNA is by Dice and Kogan. Kashyap et al. (SOSP 2019) is ShflLock. | Add the CNA paper; cite [8] only for shuffling locks. |
| [25] | Michael and Scott (JPDC 1998), not Scott alone. Also cited for "PMC encodings differ across Intel/AMD/ARM", which it does not cover. | Fix authors; replace the citation for the PMC claim. |
| [12] | Park et al. "Spin-then-sleep…" not recognised. | Find the real paper or remove. |
| [18] | EOS, arXiv:1508.06356: authors/title not recognised. | Verify on arXiv or remove. |
| [21] | "Bolt" as GBDT-via-LUT not recognised; the Bolt I know is vector compression (KDD 2017). | Verify; otherwise replace. |
| [22] | TreeLUT title looks altered. | Copy exact title from arXiv. |
| [27]–[29] | Persistent memory / driver synthesis: unrelated to locks. | Remove unless actually cited. |
| [26]–[31] | Not cited in the body text. Contradicts your own EC3. | Cite them where relevant or delete. |

Also fix mismatched citations:
- [9] (2001) and [10] (2013) are cited for MDS/TAA mitigations, which came later. Cite Intel advisories or kernel docs instead.
- [14] is cited for "ML on PMC signals". It is a scalability study.
- [19] (DQN) is not a kernel paper; cite it only as RL background.

### 2. Verify or cite every specific number
Each of these needs a source or must be removed or labelled as your own measurement:
- David et al.: "28 algorithms, 48 cores"
- Guiroux et al.: "19 algorithms, 36 apps" (counts look wrong or swapped; *verify*)
- "4–6 ns L3 hit" (too low for L3)
- "<8% of lock sites cause >85% of wait time"
- "2.1×–3.2× cohort gain", "500 µs starvation"
- "50–200 ms adaptation lag"
- "50–100 ns fast-path budget"
- "87% → 61% under async prediction" (this appears to be from your own simulation; say so)

### 3. Rename the synthetic regimes
"PARSEC" and "SPECjbb2015" results are from an analytical trace model, not benchmark runs.
- Use "PARSEC-like" and "SPECjbb-like" everywhere (tables, abstract, text).
- State in the abstract: "evaluated on synthetic traces from a calibrated analytical model."

### 4. Do not call the references "audit-verified" until they are
Remove "verified", "audit-verified" and "zero fabricated" wording unless every entry is checked against DOI, publisher page or arXiv.

---

## P1. Strengthen the technical content

### 5. Break down the true end-to-end cost
The 3.45 ns "pre-binned" number assumes counters were already read and binned.
- Add a cost breakdown: counter read, quantize, LUT lookup, switch gate.
- Measure or cite `rdpmc` cost. PMCs are per-core, not per-lock.
- Prefer software per-lock features (queue depth, R/W ratio, CAS retries) over PMC features where possible.
- Present the pre-binned latency as a lower bound, not the headline.

### 6. Make the baseline comparison fair
CLTML-v2 (95.48%) beats the 32-tree float GBDT (89.88%) because it uses a bigger teacher (25 rounds, depth 5) and extra features.
- Add a row for the v2 teacher itself (float) and show v2's retention relative to it.
- Add a row for the 32-tree GBDT with the same extra features.
- Report the accuracy loss of the table vs its own teacher, which is the actual claim.

### 7. Address the circular evaluation
Labels, features and costs all come from one generator, so accuracy is partly tautological. The static `qspinlock` scoring exactly 25.00% suggests a class-balanced set.
- Report class balance and the per-class confusion matrix.
- Train on one parameter setting of the generator and test on shifted settings (distribution shift).
- Report mean and 95% CI over at least 10 random seeds.
- Where possible, use a real source of traces (a userspace lock library such as `pthread` / `libslock` on real hardware, or `perf lock` / lockstat data from a real workload).

### 8. Measure the switching guard under real contention
`active_users` is a shared atomic updated on every acquire and release. That can recreate the cache-line bouncing the paper tries to avoid.
- Benchmark `cltml_lock_t` at 1–64+ threads, ideally across sockets.
- Compare throughput to a plain `qspinlock`-like baseline.
- Report how often the drain gate (`MAX_DEFERRED_SWITCHES = 256`) fires and the pause it causes.

### 9. Restrict which policies are swappable
A sleeping mutex cannot replace a spinlock in atomic or IRQ context. An RCU "path" is a data-structure design choice, and writers still need a lock.
- Limit runtime switching to compatible modes (for example, qspinlock vs NUMA-aware variant, or spin/sleep patience thresholds).
- State explicitly which kernel contexts allow which policies.
- Move RCU vs lock choice to a design-time or per-subsystem decision, not a per-acquisition one.

### 10. Justify or relax the per-acquisition premise
The "latency wall" only exists if the model must run on every acquisition.
- Add a short analysis: decision per lock instance per epoch (for example every N ms), which amortises even a 637 ns model.
- Then show why CLTML is still valuable (no FPU, tiny, auditable, deterministic) rather than only fast.

### 11. Test cache realism
A 4–8 KB table in a tight loop over 1,024 windows stays warm in L1.
- Add a benchmark that interleaves a cache-polluting workload between lookups.
- Report cold-miss latency alongside warm latency.

---

## P2. Literature review improvements

### 12. Add missing related work
Add and compare at least these (*verify details*):
- **LinnOS** (OSDI 2020): in-kernel NN inference with latency constraints; the closest comparator for RQ2.
- **KML** (kernel ML library): ML inside the Linux kernel.
- **ML-based load balancing in the Linux kernel**.
- **Concord / application-informed kernel synchronization** (OSDI 2022).
- **BRAVO** (biased locking), and **mainline CNA**.
- eBPF-based policy frameworks.

### 13. Give the taxonomy real exemplars
Class 1 currently cites [13] and [14], neither of which is an ML lock selector.
- For each of the three classes, list at least two real systems or state honestly that none exist.
- If few ML lock selectors exist, say that explicitly. It strengthens your gap claim.

### 14. Improve Table II
- Add a normalised column (ns or cycles per acquisition, throughput relative to a baseline) with the platform noted.
- Keep the non-comparability note.

### 15. Fix "28 peer-reviewed + 3 foundational"
[3], [30], [31] are books or documents, [18] and [22] are preprints, and [19] is off-topic. Re-count honestly and report categories (peer-reviewed, preprint, book, documentation).

---

## P3. Methodology section

### 16. Make the review reproducible
- Report the record count **per database** (IEEE Xplore, ACM DL, USENIX, arXiv, Semantic Scholar) for Q1–Q3.
- Give exact search dates and filters (years, fields).
- Add a second query for the ML + OS side (for example "learned OS policy", "ML in kernel", "in-kernel inference").
- Remove **EC3** ("uncited bibliography entries"); it is not a screening criterion. The 17 removed entries should be described as "removed after reference verification".
- State who screened and how disagreements were handled (even if it was one person).
- Treat Connected Papers, SciSpace, Zotero and Overleaf as tools, not methodology steps.

---

## P4. Writing, figures and tables

### 17. Fix inconsistencies
- Header says 1,024 held-out test windows; text says 4,000. Reconcile.
- Fig. 3 shows v1 only; Table III shows v1 and v2. Update the figure to include v2 and the teacher.
- Make sure the abstract, Table III and conclusion quote identical numbers.

### 18. Add figures and tables
- Latency breakdown figure (counter read, quantize, lookup, gate).
- Confusion matrix for CLTML-v2.
- Accuracy vs table size (1, 2, 4, 8, 16 KB) to show the trade-off.
- Table of dataset details: windows per regime, class balance, train/test split, seeds.
- Multi-thread scaling plot for `cltml_lock_t`.

### 19. Add a Threats to Validity subsection
Cover: synthetic traces, cost model calibration, single CPU, userspace not kernel, warm cache, PMC-to-lock attribution, policy interchangeability.

### 20. Tighten claims
- Replace "resolves" with "reduces" (Gap 1 is mitigated, not solved).
- Avoid "100% at quiescent boundaries, zero violations" without stating the test size and what a violation means.
- Use "feasibility study" in the title or abstract.

---

## Suggested revised outline

1. Introduction and RQs (reframed premise)
2. Review method (per-database counts, corrected criteria)
3. Static and NUMA-aware locks
4. ML in kernels and learned synchronization (LinnOS, KML, Concord, and so on) with taxonomy
5. Where the latency actually matters (per-acquisition vs per-epoch analysis)
6. CLTML design (compatible-policy switching only)
7. Synthetic-trace evaluation plus a real-hardware lock benchmark
8. Threats to validity
9. Conclusion

---

## Quick checklist

- [ ] All references verified against DOI, publisher or arXiv
- [ ] Every statistic cited or labelled as own measurement
- [ ] "PARSEC-like" / "SPECjbb-like" naming everywhere
- [ ] End-to-end cost including feature collection
- [ ] v2 compared against its own teacher
- [ ] Seeds and confidence intervals reported
- [ ] Multi-thread `active_users` benchmark
- [ ] Switching limited to compatible policies
- [ ] LinnOS, KML, Concord added and compared
- [ ] Per-database search counts, EC3 removed
- [ ] Fig. 3 / Table III and test-set sizes reconciled
- [ ] Threats to Validity section added
