# R4H.4 (dev15): Two Final Workflow Repairs

Baseline: `Clustering_post4_R4H3_Workflow_Simplification_DEVELOPMENT.zip` (`dev14`); source extracted to independent R4H.4 directory. **Development candidate; NOT formally ACCEPTED.**

## Fix 1 — R4H3-S3-EDA-CANDIDATE-ANCHOR-01

The original `multivariate_separation_hint` required very strong MST bridge gaps. In the real Iris model representation it returned INCONCLUSIVE even though `petal_length_cm` and `petal_width_cm` show the same substantial empty gap. Added `observed_projection_gap_hint` which verifies substantial empty feature-axis gaps, sufficient samples per segment, and >=90% agreement on pairwise observed co-memberships across **two different approved numeric features**. It uses only actual approved model data; no clustering model fit, Silhouette or stability score. The centered observed region count determines an initial *neighboring* K grid, not an asserted optimum. Fallback to a broader default range occurs when reliable EDA counts cannot be derived. Model-preprocessing and exploratory metric limitations are expressly recorded.

- Real Iris: 2 apparent regions on petal length and petal width => **K=2,3**.
- Controlled QA 3-region fixture => **K=2,3,4**.
- Controlled QA unseparated fixture => broad exploratory grid, no asserted natural K.
- Method cost budget constrains candidate count/time; it does not silently substitute K=5 for a strong observed anchor. A new approval is required for any extension.
- Caution: non-axis-aligned or manifold shapes may remain inconclusive; no universal computer-vision group-count claim.

## Fix 2 — R4H3-S4-REDUNDANT-GATE-01

The **new public CLI create path only** persists `stage4_auto_diagnostics=true` alongside `stage4_candidate_execution=true`. The Stage 3 user decision binds candidate configurations, model-fit budget, sampling fraction, repeats, seed, preprocessing policy and bounded fit budget. After authorized full-data fit, Stage 4 records a hash-bound result checkpoint and **actually invokes** `diagnose_approved()` for the pre-authorized Silhouette/stability/quality pipeline. There is no synthetic or inferred approval for results and no intermediate result-prompt. At `S4_REVIEW`, a *distinct real user final model approval* is still mandatory. Changed results invalidate authorization, repeat fit/evaluation is denied, failures consume the approved budget (no implicit retries), Stage 4 boundary extensions return to a fresh Stage 3 gate, and previously approved results/ARI batches are hash-checked and reused.

Legacy studies without the new flag preserve the preexisting `S3_RESULTS` or `S4_RESULTS` independent confirmation gate and historical approvals unchanged. Direct programmatic `Session.create` remains legacy by default unless the new option is selected. New public CLI studies use the auto-scope option; this separation is intentional.

Reports document the actual workflow. The operator `SKILL.md` and default prompt were updated. **README.md and assets/workflow.png were preserved byte-for-byte**, as requested for GitHub release planning.

## Tests completed

- New R4H.4 tests: first 5/5 PASS (including **real** subsampling ARI, final approval gate and result tampering), plus an independently executed expansion reuse test 1/1 PASS. An aggregate re-run of all six later timed out mid-run, therefore **aggregate run is not PASS**; individual PASS results remain recorded.
- Legacy R4H.3 workflow tests: 4/4 PASS, explicitly targeting the prior results-gated path.
- R4H.1 PNG/layout tests: 4/4 PASS.
- R4H.2 preprocessing tests: 7/7 PASS.
- R4G session persistence regression: first 2 PASS; combined suite timed out during the long PAM/Gower checkpoint case, so no PASS assigned to the remaining tests.
- Full five-route R4H.4 cross-method E2E: NOT RUN. Earlier R4H.3 five-route E2E passed, but those results must not be extrapolated to the changed candidate/gate path.
- Host UI real-world acceptance, full Quarto render: NOT RUN.

## Remaining release gates

1. The user tests actual Iris EDA planning and one new CLI Stage 4 auto continuation, including actual PNG opening.
2. Complete the R4H.4 cross-method E2E matrix and long persistence regression in a controlled environment before release acceptance.
3. Only after acceptance: `GITHUB-README-UPDATE-01` and `GITHUB-FLOWCHART-UPDATE-01`. Nothing has been pushed to GitHub.
