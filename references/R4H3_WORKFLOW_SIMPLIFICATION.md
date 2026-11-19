# R4H.3 — Stage 3/4 Workflow Simplification and Metrics Scope

Version: `1.0.0rc6.post4.dev14` (development candidate). Baseline: R4H.2 dev13. R4H.2 source is retained unchanged in its original ZIP.

## Scope and execution

1. New **CLI-created** sessions persist `gate.stage4_candidate_execution=true`. Stage 3 only proposes and approves candidate configurations, provenance, runtime budgets and the bound Stage 4 diagnostic plan. It does not fit models or produce a candidate-execution figure.
2. Candidate approval moves the new session into `S4_EXECUTE`. The already-authorized `fit_candidates` executes full-data models in Stage 4 and enters `S4_RESULTS`. A new, distinct results confirmation is required before moving to `S4_REVIEW`, where `diagnose_approved` executes the exact bound Silhouette/stability/quality plan. Final model and delivery gates are unchanged. No implicit approval occurs.
3. Persisted legacy R4H.2 sessions **without** the flag retain `S3_EXECUTE` / `S3_RESULTS` gate transitions and their original approvals. Direct `Session.create` defaults to legacy mode for existing programmatic integrations; pass `stage4_candidate_execution=True` to opt into new semantics. The public CLI always opts into the new workflow.
4. New studies no longer produce `stage3_candidate_preview.png` or its redundant requested-K versus actual-K bar chart. The Stage 3 attachment endpoint correctly reports `NOT_APPLICABLE_PLANNING_ONLY`; Stage 4 delivers actual partition, quality, stability and method-specific images before final selection. Historical plots are never rewritten.
5. `calinski_harabasz` and `davies_bouldin` are removed from new fit calculations, planned-metric disclosure, selection extrema, selection-audit evidence, CSV metric output and study-specific references. Silhouette, common-ID resampling ARI, group sizes, WCSS/inertia where appropriate, Medoid objective, DBSCAN noise and Hierarchical-specific evidence remain. Historical immutable model JSON remains unaltered; new report tables omit removed legacy columns.
6. Stage 5 report headings, candidate planning table, execution/results table and archived five executable code blocks follow the revised Stage 3/4 responsibilities. `config.json.workflow` reports the actual path (new or legacy). Offline HTML and PNG/SVG delivery are retained.
7. A newly authorized candidate expansion returns from Stage 4 to the Stage 3 planning gate and, after fresh approval, executes only new candidates in Stage 4. Hash-verified prior candidate fits and compatible stability results are reused.

## Verification performed

- New R4H.3 workflow tests: **4/4 PASS** (gates, Stage 3 no charts, Stage 4 fits/confirmation/diagnostics, report, no CH/DB metrics, new-scope expansion with no refits).
- R4H.2 preprocessing-disclosure tests: **7/7 PASS**.
- R4H.1 safe-attachment tests: **4/4 PASS**.
- R4G persistent-session tests: **4/4 PASS**, including mixed PAM/Gower Stage 3→4 recovery in historical mode.
- R4E DBSCAN Stage 4 figures/report legacy integration: **PASS**.
- R4E K-means Stage 4 initialization/stability legacy integration: **PASS**.
- Additional Hierarchical/Ward and DBSCAN Euclidean `fit_one` checks: **2 PASS** (no removed metrics).
- Fresh R4H.3 K-medoids using PAM/Euclidean on a small QA numeric dataset: actual Stage 4 resampling and Stage 5 report; `reproduce.py --verify` **PASS**, both candidates verified; exit code 0. (QA fixture data; not a claim about the user's prior research.)
- One legacy R4E full incremental-extension test: **TIMEOUT**, no PASS inferred. A separately isolated R4H.3 incremental extension test DID PASS.
- Aggregate previously attempted long regression batch: **TIMEOUT**, not PASS.
- Full five-method R4H.3 end-to-end matrix, Work host UI, human PNG opening, native Quarto rendering: **NOT RUN**; formal release still NOT ACCEPTED.

## Deferred public release documentation

`README.md` and `assets/workflow.png` remain **byte-for-byte identical** to the original R4H.2 ZIP, at the user's explicit request. The README still mentions dev13; this is an intentional documentation exception for the development candidate, not an accepted published version. Update GitHub README and flowchart together at final release under `GITHUB-README-UPDATE-01` and `GITHUB-FLOWCHART-UPDATE-01`.

## Limits

The software can validate local file integrity and deterministic results but cannot certify chat UI image rendering. Any human release or platform-wide persistence claim remains separately gated.
