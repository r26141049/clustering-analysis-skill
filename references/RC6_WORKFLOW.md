## Historical post1 release decision — 2026-11-15 (current post3 status in POST3_R2_RELEASE_READINESS.md)

**ACCEPTED: rc6 Plan B personal Skill, version 1.0.0rc6.post1.** The user explicitly approved request RC6-PLANB-HISTORY-WAIVER-20261115-COMPAT01 with response A. See references/RELEASE_ACCEPTANCE.json (RELEASE_ACCEPTANCE.json within references). For post1 only, this decision superseded older disabled/NOT ACCEPTED/pending-history language retained below as historical review records; it does not rewrite historical failures.

Adopt the approved 60-required-function replacement matrix in references/RC6_FUNCTIONAL_COVERAGE_MATRIX.csv. Original 33-case sources, historical applicability/port records and the old Stage3 Gower fixture remain HISTORICAL EVIDENCE LOST, never PASS; stop demanding recovery. No necessary functional test or research Hard Gate is waived. Legacy automated release-checker history prerequisites are superseded only for this documented user-approved manual release decision; do not claim that legacy runner was executed or passed.

Plan B PNG/offline HTML/A-B-C human acceptance remains PASS. Inline chat display retains historical FAIL; native clickable buttons remain unfinished and nonblocking. Independent Plugin host installation remains NOT RUN/NOT VERIFIED, outside the confirmed personal Skill scope. Do not interpret this release acceptance as approval of new research fits, publishing to third parties or deployment of independent services.

## Plan B delivery contract — 2026-11-15 (preserved for post3)

Use Plan B: every necessary statistical figure must be an individually openable/downloadable PNG attachment in its own stage BEFORE asking that stage approval. A/B/C text choices are supported; native clickable buttons and inline chat images are optional, nonblocking. Preserve historical inline FAIL and unfinished-button records. Never change them to PASS or remove them.

Historical Iris repair record (not the current Stage 1 run): user confirms Stage 1–5 links appeared in the later repair response and sampled Stage 1 geometry, Stage 4 WCSS and stability opened successfully. These THREE files have human open PASS only. Other attachments remain human NOT VERIFIED. The original run lacked stage-local attachments before approval: timing FAIL remains; late repair is not retrospective compliance. Current final human acceptance: Stage 1–4 timely PNG attachment delivery and stage-level human opening PASS; Stage 5 offline HTML human reading including the K=3 partition PASS (2026-11-15). Final user acceptance also confirms Stage 5 final_partition.png opens with the correct K-means K=3 partition: overall Plan B image-delivery human acceptance PASS. Do not fabricate per-file opening receipts for other files; image delivery is no longer a Plan B release blocker. Overall release remains NOT ACCEPTED pending remaining required evidence; see RELEASE_READINESS_REVIEW.md in references. See references/PLAN_B_ACCEPTANCE.md (or PLAN_B_ACCEPTANCE.md within references). Do not rerun research to obtain that evidence without a new explicit request.

Plan B does not waive Hard Gates, four-method statistical checks, literature/research acceptance or actual plugin-loader installation validation. Package status remains NOT ACCEPTED while required evidence is absent. Source/plugin/delivery ZIP preparation is not release approval; native plugin import NOT RUN is not installability PASS. Keep stage authorization tokens, scope and distinct-turn controls unchanged. Preserve approved scientific results.

## Required PNG attachments and separate inline acceptance (2026-11-15)

This section supersedes older inline-first/fallback-only instructions throughout this package.
At EVERY Stage 1–5 that generates statistical figures, deliver ALL actual PNGs as individually clickable/openable/downloadable attachments in the CURRENT stage response, alongside interpretations. Final ZIP retention, filenames, paths, JSON, private image reads and rich image output alone never satisfy this minimum. Inline images, if available, are additional; they never replace PNG attachment links.

Call CLI `stage_attachments(stage=N)` after the current stage figures exist. It reuses existing files, validates every PNG and returns `attachment_markdown` plus per-file hashes/receipts. Emit ALL returned Markdown links as normal links (not image syntax or code blocks) in the current user-facing response before asking the stage decision. On Work, `[name.png](<sandbox:/absolute/path/name.png>)` is the attachment route. JSON output is construction only, not delivery. On unsupported hosts use the supported file-attachment upload route. Missing/unopenable attachments are a distinct P0 delivery defect; report it and repair file delivery before requesting the next research decision. Never fit/refit to repair presentation.

Acceptance has three independent columns:
1. PNG generation: PASS only for existing complete decodable PNGs, with path/hash.
2. PNG attachment delivery (minimum, mandatory): construction PASS is separate from actual response submission; human open/download remains UNVERIFIED until the user confirms. User-reported absent/unopenable attachments are FAIL. Check every generated figure in each stage, not only a representative figure or final ZIP.
3. Chat inline display (advanced): this Iris/K-means human test is FAIL. Do not relabel it PASS from decoding, attachment success, image-content construction or submission. Do not repeat already failed inline mechanisms; no inline retry during attachment remediation.

Historical Iris run: PNG generation PASS; stage-local PNG attachment delivery FAIL (Stage 1 confirmed absent, Stage 2–5 individual links likewise omitted in transcript); inline display FAIL per human report. A late repair does not retroactively pass stage-local delivery. New links can be submitted for separate human opening checks. Keep candidate release NOT ACCEPTED; this patch does not establish end-to-end human acceptance.

# rc6 research workflow and presentation contract

## Stage 1 → 2 → 3

Generate real marginal EDA plus exact-data scatter (two numeric features) or pair matrix (first four numeric features). Do not use supplementary labels, IDs, dataset names or presumed benchmark group counts. Retain all selected model features; this is a display limit, not dimensionality reduction. Explain alias mapping, scale, correlation, missingness, IQR flags and projection limitations.

After preprocessing approval, inspect the approved-model plots with the host image reader. Call `record_visual_evidence(observations,basis,limitations)` in S2_REVIEW. Supply all five keys: nonconvex, curved, unequal_density, isolated_regions, coarse_fine_structure. Each requires `{value: observed|not_observed|uncertain, reason: actual plot interpretation}`. Basis must list current `geometry_paths`; backend stores their SHA256. An uncertain observation is valid. This is explicit agent visual interpretation, never an automatic shape detector or human acceptance. If fewer than two numeric features, use empty visual evidence/UNREVIEWED, explain why scatter geometry is unavailable, and assess mixed-variable distances substantively.

`eda_handoff` preserves n, p, selected features/types, ranges, Spearman pairs, missingness, IQR flags, evidence/uncertainty, model hash. `assess_methods` carries it into every method row, separating computational_feasibility, statistical suitability status and empirical_support. If geometry is unreviewed, do not rank computationally feasible center/medoid methods as primary by default. Inspect the plot or honestly disclose insufficient evidence. An observed curve plus usable neighborhood diagnostics can prioritize DBSCAN for shape/density exploration; it does not choose eps, K or a winner. Compare Ward (compact variance), Single (connectivity/chaining), Complete (diameter), Average (average distance). A medoid does not recover arbitrary curves.

Before presenting Stage 3, call `candidate_guidance(configs)` and use its EDA hash, visual interpretation, ranges/correlations/extremes and search boundaries. State EDA-supported hypotheses separately from exploratory defaults. Explain K lower/upper limits and the purpose of each coarse/fine candidate; never default Iris to three or derive best K from n/p. With no clear clue, use bounded exploratory settings and say so. For DBSCAN, cite measured neighbor-distance ranges/quantiles, explain min_samples includes self, and discuss bridging, noise and fragmentation. Every config key needs source and rationale; allowed origins add methodological_limit to the rc5 list. Stage 3 payload binds `eda_context`; report config keeps that same plan.

At Stage 4, unresolved trends, boundary optima or conflicting indicators require a disclosed limitation and an offer to return to Stage 3. Do not secretly expand fits or force consensus. Parallel alternatives and no-final-model remain valid.

## One method decision, six independent gates

Present assessment first; call `propose_method_choices()` BEFORE showing the available numbered method choices to the user. It returns a single token bound to the options, assessment, model and EDA hash. The user's exact number/name (`1`, `K-means`, `我選擇 K-means`) goes to `respond(item="method",token=...,response=FULL_ORIGINAL_REPLY,message_id=ACTUAL_MESSAGE_REF,source="user")`. The same reply selects and authorizes that method for Stage 3 planning. Reload status; do not ask for A again. Never reinterpret an old reply under a newly issued menu. A bare A with a multi-method menu needs clarification.

Keep compatibility `propose_method` for existing operator code, but normal conversations use the choices API. An unambiguous name matching its single pending method also approves it. Never mutate the approved options payload to insert the choice; `method()` derives the selected method from the consumed response under that payload. A method decision cannot authorize execution. Six gates remain preprocess, method, candidates execution, results confirmation, final research decision, delivery confirmation. Diagnostics already bound in Stage 3 require no extra gate.

Transactions serialize the entire local Session read/validation/write using an advisory OS lock, reload when another instance committed, and retain gate token/expiry/revision/dependency/message binding. Use Session/CLI entrypoints, never edit session.json or use Gate alone as a concurrent persistent backend. A local token is provenance, not identity authentication. Windows lock path needs separate runtime validation; no distributed lock claim.

## Proactive image output at every stage

Stage 1: EDA marginal + geometry. Stage 2: approved geometry + measured neighbor-distance diagnostic when available. Stage 3: candidate quality after authorized fitting. Stage 4: selection-evidence/sensitivity/stability charts. Stage 5: principal result/selection charts and complete attachments. Batch 1–3 figures (maximum 4); explain each in Traditional Chinese using the exact measured values. Never refit for display.

JSON stdout and a PNG path are TEXT, not a rich image. `present_figures(stage,start=0,limit=3)` returns MCP-compatible image content with actual base64 PNG bytes, receipts and next_start. It validates the complete PNG, not just signature. **Do not dump these base64 bytes as text to the user.** The caller must forward image blocks to a supported image channel. On this Work host, use `tools.view_image` plus `functions.image` to forward existing PNGs, or forward `image(block)` directly when the tool result exposes ImageContent. This requires no custom server/OAuth/UI.

Example Work orchestration (replace only with actual current PNG paths from figure_previews):

```javascript
const result = await tools.view_image({path: actualPngPath});
image(result.image_url);
```

This produces an image output item. `view_image` used privately without forwarding is not client display. Work also supports `![caption](sandbox:/absolute/path/chart.png)` in a response; treat it as a fallback whose successful rendering is not guaranteed. Plain `[chart](...)`, bare paths and relative `figures/a.png` in chat are attachments/text only. If inline output fails or the host has no image channel, give actual accessible PNG attachments, state the limitation and retain P0 unverified. Retain SVG vector attachments. Never generate substitute illustrations.

A Python process cannot prove what a chat client painted. Separate three states: file_output PASS (exists, decodes, accessible); content_constructed PASS / interface_submission SUBMITTED only after the host accepted a rich image output; human_visible UNVERIFIED until the actual user verifies it. Do not set displayed=true from decoding. Record tool-output evidence, but do not call simulated sinks formal UI acceptance. A content-construction unit test does not prove submission; actual forwarded image tool outputs provide submission evidence.

## Report and final state

Markdown/QMD use verified PNG; SVG retained. `analysis_offline.html` embeds every PNG as a data URI and uses escaped prewrapped report prose/tables; it needs no Quarto, JavaScript, network or relative image files. It is a readable fallback, not a claim of Quarto rendering. Quarto status remains separate.

Stage 4 result/diagnostic hashes and the approved explanation remain the source for CSV/JSON/plots/MD/HTML. Do not change historical approved research choices. Final delivery confirmation updates MD/QMD/offline HTML (and rendered HTML if present), manifest status and hashes together, retains original reviewed hashes in preconfirmation_hashes, and writes a confirmation receipt. Historical decision_log remains historical. Refresh revokes the delivery approval and resets the current report status, requiring a fresh reply; it cannot alter scientific snapshots. Revised old reports carry OBSOLETE status in their manifest.

Report conditional fixed-parameter subsampling limitations, fixed versus refit preprocessing and Gower range re-estimation. Different noise-excluded silhouette observation sets are not directly comparable as identical populations. No forced winner, invented pass threshold or composite ranking.

## Release restriction

Development candidate v1.0.0rc6 remains NOT ACCEPTED and disabled. File tests, engineering simulations and tool image submission do not satisfy actual Stage 1–5 client-visible human acceptance, formal installation, research/literature acceptance or real-user Hard Gate verification.

The `sensitivity` compatibility action now fails closed. Put new same-method parameter variants into a revised Stage 3 candidate budget; changed preprocessing requires Stage 1 approval. Candidate fitting consumes its batch before the first fit; failure revokes Stage 3 authorization. Revisions remove stale downstream figures and mark old report prose obsolete. Current delivery confirmation checks the exact proposed manifest and file set; new logs/attachments require refresh. `presentation_validation.json` records all MD/QMD references and exact embedded PNG bytes, without claiming host submission or human visibility.
