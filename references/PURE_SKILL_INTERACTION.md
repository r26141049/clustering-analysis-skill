## Required PNG attachments and separate inline acceptance (2026-11-15)

This section supersedes older inline-first/fallback-only instructions throughout this package.
At EVERY Stage 1–5 that generates statistical figures, deliver ALL actual PNGs as individually clickable/openable/downloadable attachments in the CURRENT stage response, alongside interpretations. Final ZIP retention, filenames, paths, JSON, private image reads and rich image output alone never satisfy this minimum. Inline images, if available, are additional; they never replace PNG attachment links.

Call CLI `stage_attachments(stage=N)` after the current stage figures exist. It reuses existing files, validates every PNG and returns `attachment_markdown` plus per-file hashes/receipts. Emit ALL returned Markdown links as normal links (not image syntax or code blocks) in the current user-facing response before asking the stage decision. On Work, `[name.png](<sandbox:/absolute/path/name.png>)` is the attachment route. JSON output is construction only, not delivery. On unsupported hosts use the supported file-attachment upload route. Missing/unopenable attachments are a distinct P0 delivery defect; report it and repair file delivery before requesting the next research decision. Never fit/refit to repair presentation.

Acceptance has three independent columns:
1. PNG generation: PASS only for existing complete decodable PNGs, with path/hash.
2. PNG attachment delivery (minimum, mandatory): construction PASS is separate from actual response submission; human open/download remains UNVERIFIED until the user confirms. User-reported absent/unopenable attachments are FAIL. Check every generated figure in each stage, not only a representative figure or final ZIP.
3. Chat inline display (advanced): this Iris/K-means human test is FAIL. Do not relabel it PASS from decoding, attachment success, image-content construction or submission. Do not repeat already failed inline mechanisms; no inline retry during attachment remediation.

Historical Iris run: PNG generation PASS; stage-local PNG attachment delivery FAIL (Stage 1 confirmed absent, Stage 2–5 individual links likewise omitted in transcript); inline display FAIL per human report. A late repair does not retroactively pass stage-local delivery. New links can be submitted for separate human opening checks. Keep candidate release NOT ACCEPTED; this patch does not establish end-to-end human acceptance.

> rc6: Read RC6_WORKFLOW.md first. Its one-step method-choice, EDA-handoff, image-content and delivery-state rules supersede conflicting historical instructions below.

# Pure Skill interaction policy (rc5 Four-Method Edition)

## Scope and dependencies

Use the installed `clustering_native` implementation. Keep Stage 1–5, six independent approvals, statistical algorithms and existing token checks unchanged. Treat the standalone Stage 1 MCP prototype as archived optional future work, not as a runtime dependency, install requirement or formal acceptance prerequisite for pure-Skill operation. Pause MCP deployment, OAuth setup and direct Plugin event-bridge development until explicitly requested again. Do not label rc5 formally release-accepted just because this interaction policy is adopted.

## Single-choice decisions

Present the current proposal, exact approval scope and applicable budget before asking. Do not ask the user to compose a sentence or configure services. Prefer an actually supported single-select chat-choice component; use its current documented interface, not an invented API. Component rendering is optional and must not block analysis.

Bind each question before display to a frozen record: unique question reference and exact question text, analysis session ID/path (operator-only), stage, pending item, revision, payload hash, exact token and expiry. The frontend must not choose a filesystem path. On response, compare the returned question reference and current backend state to that frozen record. Do not substitute a new token or newest proposal for an old selection. Keep the complete returned question/answer envelope and actual distinct user-turn reference; the answer field itself is the original reply to `respond`, not an affirmative substring extracted from natural language. A clickable option is chat input relayed by the assistant, NOT a direct/authenticated Plugin click callback.

Use exact short supported answers (e.g. option `A`) with concrete labels in the question (`A = accept the displayed preprocessing only`). Do not decorate the answer value with an unsupported approval sentence and then strip it. When the component cannot preserve the question binding, fall back to a plain question listing A/B/C and wait for the user's single choice.

For plain text, accept a bare choice only when there is exactly one currently displayed, unambiguous pending question in the conversation and its frozen binding is still current. If multiple/stale contexts exist, redisplay the still-current proposal with a new question reference and obtain a fresh response. Never infer which session a bare A should authorize.

For approval, call the existing `Session.respond`/CLI `respond` with the exact current token, answer, `source=user` and a traceable new user-turn reference. Read `status` afterward. Only a real backend APPROVE and expected state transition advance. Do not override CLARIFY, create fictitious user replies or use qa_fixture approvals in real analysis. Expiry, consumption, cross-session/stage, revision and dependency failures stay blocked under existing controls. Never claim pointer-event attestation.

## Per-stage actions (do not add or merge gates)

- Stage 1: A accept; B revise; C supplement. Validate the frozen binding for every option. A uses `respond`. For B/C, use the existing native Stage 1 non-approval/revision/supplement path, discard the superseded proposal as specified, and stay in Stage 1. In particular, do not send a C supplement choice through an approval parser and misreport its legacy rejection as acceptance. Collect details as needed; no new approval is inferred from a revision.
- Stage 2: clickable method choices or a short numbered method menu first select a proposal, never authorize fitting. Present the actual method proposal and obtain its own A confirmation through the method gate. A previous method-menu selection cannot be reused as that confirmation.
- Stage 3: keep planning, execution approval and result confirmation separate. Present A approve this candidate/budget proposal, B revise, C pause where appropriate. Result confirmation requires its own later user turn and results token. Do not map one A to both gates.
- Stage 4: present a concrete candidate or no-final-model decision, then ask A accept, B revise, C pause. A validates only the displayed final-decision gate. Keep the existing no-final-model report branch.
- Stage 5: A confirm the displayed current delivery; B request changes; C defer. Only the delivery gate marks COMPLETE. Refreshing report hashes invalidates the prior delivery question/token and requires a fresh choice.

B/C meanings outside Stage 1 must be stated explicitly. Handle them through existing allowed revision/pause actions; they never create an approval. Natural language is optional for explanatory details and remains subject to the existing bounded recognizer when used as a decision.

## Figures

Prefer the already human-confirmed Work inline-view mechanism with the actual existing PNG bytes embedded in a supported response fragment. Follow the host's current visualization instructions and size limits; split large image groups. Do not install an app, start a service, regenerate scientific plots or re-fit models just to display an image. The pure Skill does not require the optional MCP prototype.

Keep English text inside statistical figures and Traditional Chinese explanations nearby. Preserve feature-alias mappings and display limits. A tool successfully reading an image is not evidence of client rendering. Record decoding, response output and user-confirmed visibility separately; never set a positive displayed claim from file existence alone.

If inline views are unsupported, try a real PNG Markdown image. If unavailable, provide openable PNG/SVG attachments and honestly say inline display could not be confirmed. Keep all research attachments. Missing optional presentation capability does not waive statistical or authorization requirements.
