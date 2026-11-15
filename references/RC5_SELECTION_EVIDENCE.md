> rc6: Read RC6_WORKFLOW.md first. Its one-step method-choice, EDA-handoff, image-content and delivery-state rules supersede conflicting historical instructions below.

# Stage 3–5 evidence contract

## Stage 3 request fields

`propose_candidates(configs,basis,evidence,budget,diagnostics_plan,parameter_sources,search_rationale,boundary_limitations,initialization_plan=None)`.

Each parameter_sources element has exactly the keys of the matching config. Each value is `{source: data_diagnostic|research_purpose|exploratory_default|user_specified, rationale: nonempty string}`. Declare meaningful K exploration/range limits or actual eps/min_samples diagnostic bases; min_samples includes self. "Exploratory default" is not statistically inferred. A user cannot authorize an undocumented future expansion. Four-field diagnostics_plan remains fraction/repeats/seed/policy. K-means also binds 2–20 explicit initialization seeds; each causes one separate n_init=1 fit per candidate. Primary candidate n_init still controls its native multi-start fitting. Exact total fits = N + N*repeats + N*initialization_seeds; verification reruns the same total. memory_mb uses a conservative working-set estimate, not OS RSS hard isolation; seconds_per_fit applies per subprocess, not report rendering time.

## Actual outputs

All methods: `candidate_comparison.csv`, complete selection_evidence.json, group sizes, silhouette/effective n/observation-set hash, ARI distribution and per-group max-Jaccard with failures/nulls. K-means: inertia versus K, explicit restart seeds/inertia/convergence. Hierarchical: actual dendrogram (last20 subtrees when truncated), merge heights K→K−1, adjacent proposal-cut ARI sensitivity. This is not an unperformed linkage sensitivity experiment. PAM: objective, actual internal input Row medoids (private source IDs are not published). DBSCAN: eps/min_samples versus nonnoise groups/noise/valid silhouette/effective n, and core/border/noise counts.

Each PNG/SVG has a `.plot_data.json` containing its real plotted values. Undefined numerical measures are None/NA, never zero. CSV preserves all candidate parameters and their source. Equal-looking clusters across different K are not assumed to be the same object. Requested K and actual nonnoise group count remain distinct. Adjacent-cut ARI is computed on all identical full-data IDs, while subsampling ARI compares original induced labels with a refit on identical sampled IDs. Jaccard is max match, excludes noise as candidate group and retains losses to noise in the denominator.

## Interpretation

Mean silhouette alone does not select a natural K. WCSS/PAM objective decrease alone cannot justify a larger K. Merge-height jumps are descriptive, not significance or natural-group proof. DBSCAN silhouettes may exclude different observations: compare effective n and observation-set hash, not score alone. Initialization stability is not global optimality. ARI/Jaccard have no universal pass cutoff here. No weighted composite ranking.

If preferred parameters lie on a boundary or trends remain unresolved, disclose limitation and propose a revised Stage3 range before more fits. Conflicting evidence may support retained alternatives, new exploration or no-final-model. `selection_explanation` must cover chosen_reason, each candidate_reasons[str(index)], conflicts and limitations; optional retained_candidates expresses parallel alternatives. One final_index or null preserves existing workflow.

## Stage 5

Verify hash-bound Stage4 files, copy figures/CSV/sidecars without refitting, include every parameter, effective n, diagnostic failures and final explanation in MD/Python QMD. Report raw-unit profiles and valid denominators separately from transformed data. No final assignment when no model is selected. Quarto success requires actual CLI rendering; otherwise honest Markdown fallback. `reproduce.py --verify` redoes approved candidate/subsampling/initialization fits and checks exact stored scientific evidence; record real logs. Only final delivery confirmation completes analysis.
