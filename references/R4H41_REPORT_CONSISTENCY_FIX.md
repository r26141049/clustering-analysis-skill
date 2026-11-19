# R4H.4.1 / dev16 — Minimal report and authorization-description repair

- Baseline: R4H.4 dev15; original source and historical research ZIPs remain intact.
- Actual Stage 3 / Stage 4 authorizations and clustering algorithms are unchanged.
- Stage 4 Python code narrative now follows the study's persisted workflow:
  auto-continuation / older Stage 4 result confirmation / legacy Stage 3 fitting.
- Stage 5 coordinate summaries explicitly disclose **model_feature_snapshot**
  coordinates and the persisted per-feature fitted preprocessing scale/transform.
  The independent raw-unit group tables remain on the original unit scale.
- The approved operator's original selection limitations (including possible
  wording '提案非最終核准') stay byte-identical in config.json. Report adds a
  separate factual explanation of the now-approved Stage 4 final selection;
  delivery is still a separate Stage 5 gate.
- No permission tokens/approval records are forged, migrated, or altered.
- Do not regenerate the user's previously approved research reports in place;
  new reports use the revised generator, with independent formal acceptance pending.
- README and workflow graphic stay as-is in the dev package; GitHub preview
  prepared for dev15 requires final sync after dev16 is accepted.

## QA status for dev16 (2026-11-19)

- New real-archive-based and new gated Stage 5 report tests: **6/6 PASS**.
  Iris and Two Moons values were read from the user's saved research ZIPs;
  there was no new clustering fit on those studies.
- Inherited R4H.4 stage workflow/EDA tests: **6/6 PASS**.
- Inherited R4H.2 preprocessing disclosure tests: **7/7 PASS**.
- Inherited R4H.1 chat PNG-link layout tests: **4/4 PASS**.
- Existing archived-stage executable-code tests: **2/2 PASS** after adding
  a truthful saved-label fallback when old fixture metrics lack `clusters`.
- Inherited R4H.3 legacy workflows: first 3 tests PASS, long fourth
  candidate-expansion regression **TIMEOUT**. No full-suite PASS claim.
- Four-method/five-route full dev16 E2E, strict reproduction, Work UI, and
  native Quarto host acceptance: **NOT RUN** (separately scoped release gates).
