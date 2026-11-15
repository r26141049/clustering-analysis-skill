## RC6-GATE-BRIDGE-01 — 對話入口回覆收據（post2，待驗收）

在宿主無法取得原生使用者 `message_id` 時，請在收到**本輪新使用者的原始回覆**後呼叫：

```json
{"action":"respond_observed","session":"/path/to/session","item":"preprocess","token":"CURRENT_PENDING_TOKEN","response":"A"}
```

- `respond_observed` 不需要 `message_id`；它將收到的單次 CLI 互動標記為 `AGENT_ASSERTED_NEW_USER_TURN_NOT_PLATFORM_VERIFIED`，絕不宣稱平台已驗證真人點擊。
- 請先 `status` 取得當前唯一 pending item 與 token，並向使用者展示當前提案範圍。只允許直接觀察到的最新使用者回覆，不得重播、改寫、猜測或自行生成回覆。
- `B：為什麼保留極端值？` 是詢問理由，不代表同意或真正修訂；先解釋，保留原提案，收到新 `A` 再提交。若使用者明確要求修改內容，原方案的授權失效，必須展示新方案並取得新的批准。
- 缺答覆、拒絕、過期、跨 session、跨 item、修訂後舊 token、已消耗 token、QA 與使用者來源混用仍由同一 Gate 拒絕。
- Host 可提供實際獨立使用者回合參照時，請仍使用既有 `respond(item,token,response,message_id,source=user)`；不可用本機收據偽裝成已認證平台識別碼。此機制不是身分驗證，也不能單憑本機收據證明兩次 CLI 呼叫是兩次真人回覆。

---

> rc6: Read RC6_WORKFLOW.md first. Its one-step method-choice, EDA-handoff, image-content and delivery-state rules supersede conflicting historical instructions below.

# rc5 operator guide

Run the local Python CLI `python -m clustering_native --request /absolute/request.json`, one action per invocation, and reload status after each. No external service or account is required. Use a fresh session and never edit session JSON to bypass controls.

Actions: create(csv,dictionary); status; propose_preprocessing(plan); respond(item,token,response,message_id,source); assess_methods(purpose); propose_method(method); propose_candidates (see RC5_SELECTION_EVIDENCE.md); fit_candidates after candidates APPROVE only; diagnose_approved after separate results APPROVE; propose_final(candidate_index,rationale,selection_explanation); report(destination) after final APPROVE; refresh_delivery after report-only changes; confirm_delivery via respond; revise(stage,reason); renew_confirmation(item).

Methods exactly kmeans/hierarchical/dbscan/pam. Retired legacy methods fail closed on load and direct solver/config calls. See history for prior-version applicability only.

Use A for the current pending approval, B revise, C supplement/pause as explicitly described by PURE_SKILL_INTERACTION.md. Do not infer approval from a nonempty string, UI color or unknown sentence. Gate tokens bind session,stage,item,revision,proposal hash,nonce,dependencies and24-hour TTL. Preserve full reply and distinct message reference. All six approvals are independent; QA provenance is never human acceptance.

Preprocessing schema covers every original column; actions/positive weights cover only features. Feature types and missing/scale/transform semantics remain unchanged from rc4. ID/supplementary labels never participate in scaling or geometry. No automatic row deletion or external-label tuning.

Stage3 metadata and all computational budgets must be visible before permission. diagnose_approved consumes one bound batch even if fits fail. Evidence plotting uses stored outputs only. Never repeat diagnostics to obtain more favorable results. Changing search/settings goes through revise and new authorization. Source identifiers remain private; internal Row medoids refer to actual input row positions.
