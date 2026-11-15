> rc6: Read RC6_WORKFLOW.md first. Its one-step method-choice, EDA-handoff, image-content and delivery-state rules supersede conflicting historical instructions below.

# rc5 operator guide

Run the local Python CLI `python -m clustering_native --request /absolute/request.json`, one action per invocation, and reload status after each. No external service or account is required. Use a fresh session and never edit session JSON to bypass controls.

Actions: create(csv,dictionary); status; propose_preprocessing(plan); respond(item,token,response,message_id,source); assess_methods(purpose); propose_method(method); propose_candidates (see RC5_SELECTION_EVIDENCE.md); fit_candidates after candidates APPROVE only; diagnose_approved after separate results APPROVE; propose_final(candidate_index,rationale,selection_explanation); report(destination) after final APPROVE; refresh_delivery after report-only changes; confirm_delivery via respond; revise(stage,reason); renew_confirmation(item).

Methods exactly kmeans/hierarchical/dbscan/pam. Retired legacy methods fail closed on load and direct solver/config calls. See history for prior-version applicability only.

Use A for the current pending approval, B revise, C supplement/pause as explicitly described by PURE_SKILL_INTERACTION.md. Do not infer approval from a nonempty string, UI color or unknown sentence. Gate tokens bind session,stage,item,revision,proposal hash,nonce,dependencies and24-hour TTL. Preserve full reply and distinct message reference. All six approvals are independent; QA provenance is never human acceptance.

Preprocessing schema covers every original column; actions/positive weights cover only features. Feature types and missing/scale/transform semantics remain unchanged from rc4. ID/supplementary labels never participate in scaling or geometry. No automatic row deletion or external-label tuning.

Stage3 metadata and all computational budgets must be visible before permission. diagnose_approved consumes one bound batch even if fits fail. Evidence plotting uses stored outputs only. Never repeat diagnostics to obtain more favorable results. Changing search/settings goes through revise and new authorization. Source identifiers remain private; internal Row medoids refer to actual input row positions.
