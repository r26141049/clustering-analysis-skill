"""Persistent orchestration of Stage 1–5; all transitions explicit and recorded."""
from __future__ import annotations
import copy
import csv
import json
from pathlib import Path
import shutil
import pandas as pd
from .core import Gate, budget_check, digest, file_hash, write_json
from .data import audit, preprocess, method_assessment
from .locking import transaction


class Session:
    def __init__(self, directory):
        import threading
        if not hasattr(self, '_transaction_mutex'):
            self._transaction_mutex = threading.RLock()
            self._transaction_local = threading.local()
        self.directory = Path(directory).resolve()
        self.state = json.loads((self.directory/"session.json").read_text(encoding="utf-8"))
        self.gate = Gate(self.state["gate"])
        from .core import METHODS
        old_method = self.state["gate"].get("payloads", {}).get("method", {}).get("method")
        if old_method is not None and old_method not in METHODS:
            raise ValueError("Unsupported legacy method in rc5 Four-Method Edition; start a new session; old authorizations cannot be reused")
        if any(result.get("method") not in METHODS for result in self.state.get("results", [])):
            raise ValueError("Unsupported legacy result method; no silent conversion is allowed")

        self._disk_hash = file_hash(self.directory/"session.json")
        self._integrity()

    @classmethod
    def create(cls, csv_path, directory, dictionary=None):
        source, directory = Path(csv_path).resolve(), Path(directory).resolve()
        if directory.exists() and any(directory.iterdir()):
            raise FileExistsError("Use a new empty analysis directory")
        with source.open(encoding="utf-8-sig", newline="") as f:
            header = next(csv.reader(f))
        if len(header) != len(set(header)) or any(not h for h in header):
            raise ValueError("Duplicate/empty CSV column names")
        raw = pd.read_csv(source, encoding="utf-8-sig")
        eda = audit(raw, dictionary)
        directory.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, directory/"input.original.csv")
        write_json(directory/"session.json", {"format_version": 2, "input_sha256": file_hash(source),
            "dictionary": dictionary or {}, "eda": eda, "gate": Gate().state,
            "results": [], "diagnostics": None, "final_index": None})
        s = cls(directory)
        from .figures import eda_figures
        eda_figures(raw, eda, directory/"eda_figures")
        from .workflow_evidence import geometry_figures
        schema = {row['column']: {**row, 'type':row['statistical_type']} for row in eda['columns']}
        geometry_figures(raw, schema, directory/"eda_figures")
        return s

    def _integrity(self):
        if file_hash(self.directory/"input.original.csv") != self.state["input_sha256"]:
            raise ValueError("Immutable input snapshot changed; start a new Stage 1 session")
        affected = self.gate.affected_stage()
        payloads = self.gate.state["payloads"]
        if affected is None and "preprocess" in self.gate.state["approvals"]:
            approved = payloads["preprocess"]
            if digest(self.state.get("model_data")) != approved.get("model_hash") or digest(self.state.get("fitted_preprocessing")) != approved.get("fitted_preprocessing_hash"):
                affected = 1
        method_payload = payloads.get('method', {})
        bound_eda = method_payload.get('eda_hash')
        if bound_eda is None:
            prior_handoff = method_payload.get('assessment', {}).get('eda_handoff')
            bound_eda = digest(prior_handoff) if prior_handoff else None
        if affected is None and bound_eda is not None and bound_eda != digest(self.state.get('eda_handoff')):
            affected = 2
        if affected is None:
            for basis in self.state.get('eda_handoff', {}).get('visual', {}).get('basis', []):
                if isinstance(basis, dict) and (not Path(basis['path']).is_file() or file_hash(basis['path']) != basis['sha256']):
                    affected = 2
                    break
        if affected is None and "results" in payloads and payloads["results"]["results_hash"] != digest(self.state["results"]):
            affected = 3
        if affected is None and "final" in payloads and payloads["final"]["diagnostics_hash"] != digest(self.state["diagnostics"]):
            affected = 4
        if affected is None and "final" in self.gate.state["approvals"] and self.state["final_index"] != payloads["final"]["candidate_index"]:
            affected = 4
        if affected is not None:
            self.revise(affected, "Approved settings, model data or results changed; downstream authorization invalidated")
            raise PermissionError("Changed analysis content invalidated affected and downstream approvals/results")

    def _expect(self, phase):
        self._integrity()
        self.gate.expect(phase)

    def raw(self):
        self._integrity()
        return pd.read_csv(self.directory/"input.original.csv", encoding="utf-8-sig")

    def save(self):
        self._integrity()
        self.state["gate"] = self.gate.state
        write_json(self.directory/"session.json", self.state)

    @transaction
    def propose_preprocessing(self, plan):
        self._integrity()
        # Validate on an in-memory copy only. No approved model dataset is stored.
        model, fitted = preprocess(self.raw(), plan)
        old = self.gate.state["payloads"].get("preprocess")
        if old is not None and "preprocess" in self.gate.state["approvals"] and digest(old["plan"]) != digest(plan):
            self.revise(1, "Approved preprocessing proposal changed")
        self._expect("S1_REVIEW")
        token = self.gate.propose("preprocess", {"input_hash": self.state["input_sha256"],
            "plan": plan, "model_hash": digest(model.to_dict(orient="list")),
            "fitted_preprocessing_hash": digest(fitted)}, "S1_REVIEW", "S1_REVIEW")
        self.save()
        return token

    @transaction
    def respond_stage1(self, choice, token=None, decision=None, response=""):
        self._expect("S1_REVIEW")
        if choice not in {"A", "B", "C"}:
            raise ValueError("Choose A accept, B revise or C supplement")
        if choice == "A" and response:
            raise PermissionError("RC2 approval uses decision only; conflicting legacy response is not accepted")
        if choice != "A":
            self.gate.state["payloads"].pop("preprocess", None)
            self.gate.state["proposals"].pop("preprocess", None)
            self.gate.event("stage1_wait", choice=choice, response=response)
            self.save()
            return
        payload = self.gate.state["payloads"].get("preprocess")
        if payload is None:
            raise PermissionError("No preprocessing proposal")
        model, fitted = preprocess(self.raw(), payload["plan"])
        accepted = self._gate_approve("preprocess", token, decision, "S1_REVIEW", "S2_REVIEW")
        if not accepted:
            self.save()
            return False
        if digest(model.to_dict(orient="list")) != payload["model_hash"] or digest(fitted) != payload["fitted_preprocessing_hash"]:
            self.revise(1, "Preprocessing output changed since proposal")
            raise PermissionError("Preprocessing output changed; new approval required")
        self.state["fitted_preprocessing"] = fitted
        self.state["model_data"] = model.to_dict(orient="list")
        self.state["model_hash"] = digest(self.state["model_data"])
        model_schema = {c: {**payload["plan"]["schema"][c], "type":
            "numeric" if payload["plan"]["schema"][c]["type"] == "count" and
            (payload["plan"]["actions"][c].get("scale", "none") != "none" or
             payload["plan"]["actions"][c].get("transform", "none") != "none")
             else payload["plan"]["schema"][c]["type"]} for c in model}
        self.state["approved_eda"] = audit(model, model_schema)
        from .workflow_evidence import summarize, geometry_figures
        paths = geometry_figures(model, model_schema, self.directory/"approved_eda_figures")
        self.state['geometry_paths'] = paths
        self.state['eda_handoff'] = summarize(model, self.state['approved_eda'], model_schema, self.state['model_hash'])
        model.to_csv(self.directory/"approved_model_data.csv", index=False)
        self.save()
        return True

    def plan(self):
        self._integrity()
        if "preprocess" not in self.gate.state["approvals"]:
            raise PermissionError("Stage 1 not approved")
        return copy.deepcopy(self.gate.state["payloads"]["preprocess"]["plan"])

    def model(self):
        self._integrity()
        if digest(self.state.get("model_data")) != self.state.get("model_hash"):
            raise ValueError("Approved model data changed")
        return pd.DataFrame(self.state["model_data"])

    @transaction
    def record_visual_evidence(self, observations, basis, limitations):
        self._expect('S2_REVIEW')
        if 'method' in self.gate.state['payloads']:
            self.revise(2, 'Visual interpretation changed; previous method choices invalidated')
        from .workflow_evidence import validate_visual
        visual = validate_visual(observations, basis, limitations, self.state.get('geometry_paths', []))
        self.state['eda_handoff']['visual'] = visual
        self.save()
        return self.state['eda_handoff']

    @transaction
    def propose_method_choices(self):
        self._expect('S2_REVIEW')
        result = self.assess_methods(self.state.get('assessment', {}).get('purpose', 'exploratory_partition'))
        options = {str(i+1): row['method'] for i, row in enumerate(result['methods']) if row['status'] != '不適合'}
        if not options: raise ValueError('No compatible options; revise preprocessing or clarify purpose')
        payload = {'options': options, 'assessment': result, 'model_hash': self.state['model_hash'],
                   'eda_hash': digest(self.state.get('eda_handoff'))}
        token = self.gate.propose('method', payload, 'S2_REVIEW', 'S2_REVIEW')
        self.save()
        return {'token': token, 'options': options, 'scope': 'Choose one method and enter Stage 3 planning only; no model execution'}

    def candidate_guidance(self, configs):
        self._expect('S3_PLAN')
        from .workflow_evidence import candidate_context
        return candidate_context(self.state['eda_handoff'], self.method(), configs, self.state.get('assessment', {}).get('density_diagnostic'))

    @transaction
    def assess_methods(self, purpose="exploratory_partition"):
        self._expect("S2_REVIEW")
        from .suitability import assess
        result = assess(self.model(), self.plan(), self.state["approved_eda"], purpose, self.state.get("eda_handoff"))
        from .figures import density_figure
        figure = density_figure(result["density_diagnostic"], self.directory/"eda_figures"/"stage2_density.svg")
        result["figures"] = [figure] if figure else []
        self.state["assessment"] = result
        self.save()
        from .figures import preview_assets
        result["figure_previews"] = preview_assets(result.get("figures", []))
        return result

    @transaction
    def propose_method(self, method):
        self._integrity()
        from .core import METHODS
        if not isinstance(method, str) or method not in METHODS:
            raise ValueError("Choose one supported method: " + ", ".join(METHODS))
        old = self.gate.state["payloads"].get("method")
        if old is not None:
            self._validate_method_payload(old)
        if old is not None and "method" in self.gate.state["approvals"] and self.method() != method:
            self.revise(2, "Approved method selection changed")
        self._expect("S2_REVIEW")
        result = self.assess_methods(self.state.get("assessment", {}).get("purpose", "exploratory_partition"))
        row = next((r for r in result["methods"] if r["method"] == method), None)
        if row is None or row["status"] == "不適合":
            raise ValueError("Incompatible method; revise Stage 1 if geometry must change")
        token = self.gate.propose("method", {"method": method, "assessment": result,
            "model_hash": self.state["model_hash"]}, "S2_REVIEW", "S2_REVIEW")
        self.save()
        return token

    @transaction
    def approve_method(self, token, decision):
        self._integrity()
        self._validate_method_payload(self.gate.state["payloads"].get("method"))
        accepted = self._gate_approve("method", token, decision, "S2_REVIEW", "S3_PLAN")
        self.save()
        return accepted

    def _validate_method_payload(self, payload):
        """Validate the two schemas emitted by the supported method entrypoints.

        Do not rewrite a hash-bound proposal or derive authorization from a menu.
        The consumed decision, validated by Gate, selects an approved menu item.
        """
        from .core import METHODS
        if not isinstance(payload, dict):
            raise ValueError("Method payload must be an object")
        menu = "options" in payload
        required = {"options", "assessment", "model_hash", "eda_hash"} if menu else {"method", "assessment", "model_hash"}
        if set(payload) != required:
            raise ValueError("Invalid method payload fields; expected " + ", ".join(sorted(required)))
        if payload["model_hash"] != self.state.get("model_hash"):
            raise ValueError("Method payload is not bound to the current model")
        assessment = payload["assessment"]
        rows = assessment.get("methods") if isinstance(assessment, dict) else None
        if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
            raise ValueError("Method payload requires assessment method rows")
        statuses = {"適合", "有條件適用", "不適合", "資訊不足"}
        if any(not isinstance(row.get("method"), str) or row["method"] not in METHODS
               or not isinstance(row.get("status"), str) or row["status"] not in statuses for row in rows):
            raise ValueError("Invalid assessed method or suitability status")
        names = [row["method"] for row in rows]
        if len(set(names)) != len(names) or set(names) != set(METHODS):
            raise ValueError("Assessment must contain each of the four supported methods once")
        allowed = {row["method"] for row in rows if row["status"] != "不適合"}
        if menu:
            options = payload["options"]
            if (not isinstance(options, dict) or not options
                    or any(not isinstance(key, str) or not key.strip() for key in options)
                    or any(not isinstance(value, str) or value not in allowed for value in options.values())
                    or len(set(options.values())) != len(options)):
                raise ValueError("Method options require distinct supported assessed methods")
            if payload["eda_hash"] != digest(self.state.get("eda_handoff")):
                raise ValueError("Method payload is not bound to the current EDA")
        elif not isinstance(payload["method"], str) or payload["method"] not in allowed:
            raise ValueError("Single-method payload requires a supported assessed method")

    def method(self):
        self._integrity()
        if "method" not in self.gate.state["approvals"]:
            raise PermissionError("No approved single method")
        payload = self.gate.state["payloads"].get("method")
        self._validate_method_payload(payload)
        if 'options' in payload:
            from .consent import classify
            decision = self.gate.state['approvals']['method']['decision']
            parsed = classify(decision['response'], 'method', payload)
            selected = parsed.get('selected_method')
            if parsed.get('value') != 'APPROVE' or selected not in payload['options'].values():
                raise ValueError("Approved method decision does not select a current option")
            return selected
        return payload['method']

    @transaction
    def propose_candidates(self, configs, basis, evidence, budget, diagnostics_plan=None, parameter_sources=None, search_rationale=None, boundary_limitations=None, initialization_plan=None):
        from .engine import validate_config
        self._integrity()
        if basis not in {"exploratory-only", "evidence-supported"} or not isinstance(evidence, str) or not evidence.strip():
            raise ValueError("Declare candidate basis and actual supporting evidence/limitations")
        if not isinstance(configs, list) or not configs or len(configs) > budget["max_candidates"]:
            raise ValueError("Empty/over-budget candidate list")
        from .selection_evidence import validate_search_plan
        validate_search_plan(self.method(), configs, parameter_sources, search_rationale, boundary_limitations, initialization_plan)
        if basis == "evidence-supported" and not any(origin["source"] == "data_diagnostic" for row in parameter_sources for origin in row.values()):
            raise ValueError("Evidence-supported candidates require an explicit data_diagnostic parameter source")
        if diagnostics_plan is None:
            raise ValueError("rc5 requires a bound diagnostics_plan before execution")
        estimates = budget_check(len(self.model()), budget, pam=self.method() == "pam")
        for config in configs:
            validate_config(self.method(), config, len(self.model()))
        if diagnostics_plan is not None:
            self._validate_diagnostics_plan(diagnostics_plan, len(configs))
        payload = {"configs": configs, "basis": basis, "evidence": evidence,
            "budget": budget, "estimates": estimates, "method": self.method(),
            "model_hash": self.state["model_hash"], "parameter_sources": parameter_sources,
            "search_rationale": search_rationale, "boundary_limitations": boundary_limitations,
            "initialization_plan": initialization_plan}
        if self.state.get('eda_handoff'):
            from .workflow_evidence import candidate_context
            payload['eda_context'] = candidate_context(self.state['eda_handoff'], self.method(), configs, self.state.get('assessment', {}).get('density_diagnostic'))
        if diagnostics_plan is not None:
            payload["diagnostics_plan"] = diagnostics_plan
            fits = len(configs)*diagnostics_plan["repeats"]
            initial_fits = len(configs)*len(initialization_plan["seeds"]) if initialization_plan else 0
            payload["authorization_scope"] = {"initialization_diagnostic_fits": initial_fits,"candidate_fits": len(configs), "routine_diagnostic_fits": fits,
                "verification_fits": len(configs)+fits+initial_fits, "seconds_per_fit": budget["seconds_per_fit"],
                "worst_case_seconds_including_verification": 2*(len(configs)+fits+initial_fits)*budget["seconds_per_fit"],
                "routine_execution_limit": "one diagnostic batch; failure consumes budget"}
        old = self.gate.state["payloads"].get("candidates")
        if old and "candidates" in self.gate.state["approvals"] and digest(old) != digest(payload):
            self.revise(3, "Approved candidate settings changed")
        self._expect("S3_PLAN")
        token = self.gate.propose("candidates", payload, "S3_PLAN", "S3_PERMISSION")
        self.save()
        return token

    @transaction
    def permit_execution(self, token, decision):
        self._integrity()
        accepted = self._gate_approve("candidates", token, decision, "S3_PERMISSION", "S3_EXECUTE")
        self.save()
        return accepted

    @transaction
    def fit_candidates(self):
        from .engine import bounded_fit
        self._expect("S3_EXECUTE")
        payload = self.gate.state["payloads"]["candidates"]
        model, plan = self.model(), self.plan()
        schema = {c: plan["schema"][c] for c in model}
        if self.state.get('candidate_batch_consumed'):
            raise PermissionError('Candidate batch budget consumed; revise Stage 3 and obtain fresh authorization')
        self.state['candidate_batch_consumed'] = self.gate.state['approvals']['candidates']['token']
        self.gate.event('candidate_batch_started', token=self.state['candidate_batch_consumed'])
        self.save()
        results = []
        try:
            for config in payload["configs"]:
                results.append(bounded_fit(model, schema, plan["weights"], self.method(), config, payload["budget"]))
        except Exception as exc:
            self.state["results"] = []
            self.state["fit_error"] = f"{type(exc).__name__}: {exc}"
            self.gate.event("fit_failure", error=self.state["fit_error"])
            self.revise(3, 'Candidate fit failed; previous batch consumed and fresh approval required')
            raise
        self.state["results"] = results
        from .figures import result_figure, preview_assets
        result_figure(results, self.directory/'candidate_figures'/'candidate_quality.svg')
        self.state['candidate_previews'] = preview_assets([self.directory/'candidate_figures'/'candidate_quality.svg'])
        self.state.pop("fit_error", None)
        token = self.gate.propose("results", {"results_hash": digest(results), "count": len(results),
            "candidate_hash": digest(payload)}, "S3_EXECUTE", "S3_RESULTS")
        self.save()
        return token

    @transaction
    def confirm_results(self, token, decision):
        self._integrity()
        payload = self.gate.state["payloads"].get("results", {})
        if payload.get("results_hash") != digest(self.state["results"]):
            raise ValueError("Candidate results changed")
        accepted = self._gate_approve("results", token, decision, "S3_RESULTS", "S4_REVIEW")
        self.save()
        return accepted

    @transaction
    def diagnose(self, fraction=.8, repeats=20, seed=17, policy="fixed_full_data_preprocessing"):
        from .engine import stability
        self._expect("S4_REVIEW")
        payload = self.gate.state["payloads"]["candidates"]
        allowed = payload.get("diagnostics_plan")
        if allowed is None:
            raise PermissionError("Legacy candidate plan has no bound diagnostic authorization; return to Stage 3 and obtain approval")
        if allowed is not None:
            requested = {"fraction": fraction, "repeats": repeats, "seed": seed, "policy": policy}
            if requested != allowed:
                raise PermissionError("Diagnostic settings exceed or differ from approved plan; obtain explicit revised authorization")
            if self.state.get("diagnostics_budget_consumed"):
                raise PermissionError("Approved diagnostic fit budget already consumed; revise the scope before additional work")
            self.state["diagnostics_budget_consumed"] = True
            self.gate.event("diagnostics_budget_consumed", fits=len(self.state["results"])*repeats + (len(self.state["results"])*len(payload["initialization_plan"]["seeds"]) if payload.get("initialization_plan") else 0),
                            settings=requested)
            self.save()
        result = []
        for fitted in self.state["results"]:
            result.append(stability(self.raw(), self.model(), self.plan(), self.method(), fitted,
                payload["budget"], fraction, repeats, seed, policy,
                audit_path=self.directory/"fit_runtime_events.jsonl", candidate_index=len(result)))
        diagnostics = {"stability": result, "selection": "No automatic winner or weighted composite; user decision required",
            "boundary_warning": "If a preferred candidate is at either search boundary, consider returning to Stage 3; never auto-expand",
            "wcss_caution": "WCSS reduction alone is insufficient for selecting K",
            "interpretation": "分群具探索性；品質或穩定性並不證明自然群組存在"}
        from .selection_evidence import initialization_diagnostics, build_selection_evidence
        diagnostics["initialization"] = initialization_diagnostics(self, payload.get("initialization_plan"))
        self.state["diagnostics"] = diagnostics
        self.save()
        diagnostics["selection_evidence"] = build_selection_evidence(self)
        self.state["diagnostics"] = diagnostics
        self.save()
        return diagnostics

    @transaction
    def sensitivity(self, candidate_index, alternative_plan):
        """Legacy entrypoint fails closed; variants need a new disclosed plan."""
        self._expect('S4_REVIEW')
        raise PermissionError('Additional sensitivity fits are not bound to Stage 3; revise Stage 1 for changed preprocessing or Stage 3 for parameter variants and approve a new budget')

    @transaction
    def propose_final(self, candidate_index, rationale, selection_explanation=None):
        self._integrity()
        from .selection_evidence import validate_explanation
        validate_explanation(selection_explanation, len(self.state["results"]), candidate_index)
        old = self.gate.state["payloads"].get("final")
        if old and "final" in self.gate.state["approvals"] and (old["candidate_index"] != candidate_index or old["rationale"] != rationale or old.get("selection_explanation") != selection_explanation):
            self.revise(4, "Approved final decision changed")
        self._expect("S4_REVIEW")
        if not rationale.strip() or self.state["diagnostics"] is None:
            raise PermissionError("Stage 4 diagnostics and explicit rationale required")
        if candidate_index is not None:
            if type(candidate_index) is not int or not 0 <= candidate_index < len(self.state["results"]):
                raise ValueError("Select an existing candidate index or null for no-final-model")
            result = self.state["results"][candidate_index]
            if not result["info"].get("converged", False):
                raise ValueError("Unconverged candidate cannot be final")
        token = self.gate.propose("final", {"candidate_index": candidate_index, "rationale": rationale,
            "results_hash": digest(self.state["results"]), "diagnostics_hash": digest(self.state["diagnostics"]), "selection_explanation": selection_explanation},
            "S4_REVIEW", "S4_REVIEW")
        self.save()
        return token

    @transaction
    def approve_final(self, token, decision):
        self._integrity()
        payload = self.gate.state["payloads"].get("final", {})
        if payload.get("results_hash") != digest(self.state["results"]) or payload.get("diagnostics_hash") != digest(self.state["diagnostics"]):
            raise ValueError("Diagnostics or candidates changed after final proposal")
        accepted = self._gate_approve("final", token, decision, "S4_REVIEW", "S5_READY")
        if accepted:
            self.state["final_index"] = self.gate.state["payloads"]["final"]["candidate_index"]
        self.save()
        return accepted

    @transaction
    def report(self, destination):
        from .report import build_report
        self._expect("S5_READY")
        # Prevent report paths from overwriting the session or an older delivery.
        destination = Path(destination).resolve()
        if destination == self.directory or destination in self.directory.parents:
            raise ValueError("Report cannot overwrite session/ancestor")
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError("Use a fresh empty report directory")
        manifest = build_report(self, destination)
        token = self.gate.propose("delivery", manifest, "S5_READY", "S5_REVIEW")
        self.state["report_directory"] = str(destination)
        self.save()
        return {"token": token, "manifest": manifest}

    @transaction
    def confirm_delivery(self, token, decision):
        self._integrity()
        report = Path(self.state["report_directory"])
        bound = self.gate.state['payloads']['delivery']
        if json.loads((report/'manifest.json').read_text(encoding='utf-8')) != bound:
            raise ValueError('Delivery manifest changed after proposal')
        actual = {p.relative_to(report).as_posix() for p in report.rglob('*') if p.is_file()
            and p.name != 'manifest.json' and '__pycache__' not in p.relative_to(report).parts and '.clustering_tmp' not in p.relative_to(report).parts}
        if actual != set(bound['hashes']):
            raise ValueError('Delivery artifact set changed; use refresh_delivery before confirmation')
        for name, expected in bound['hashes'].items():
            if file_hash(report/name) != expected:
                raise ValueError("Delivery changed after proposal")
        accepted = self._gate_approve("delivery", token, decision, "S5_REVIEW", "COMPLETE")
        if not accepted:
            self.save()
            return False
        self.gate.state["complete"] = True
        contains_fixture = any(a["decision"]["source"] == "qa_fixture" for a in self.gate.state["approvals"].values())
        confirmed_status = "QA_FIXTURE_CONFIRMED" if contains_fixture else "USER_CONFIRMATION_RECORDED"
        write_json(report/"delivery_confirmation.json", {"status": confirmed_status,
            "approved_manifest_payload_hash": token, "confirmation": self.gate.state["events"][-1]})
        manifest_path = report/"manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        from .presentation import synchronize_status
        synchronize_status(report, confirmed_status)
        from .presentation import validate_report_images
        validate_report_images(report)
        manifest['preconfirmation_hashes'] = manifest['hashes']
        manifest['hashes'] = {p.relative_to(report).as_posix(): file_hash(p) for p in sorted(report.rglob('*'))
            if p.is_file() and p.name != 'manifest.json' and '__pycache__' not in p.relative_to(report).parts and '.clustering_tmp' not in p.relative_to(report).parts}
        manifest["status"] = confirmed_status
        write_json(manifest_path, manifest)
        self.save()
        return True

    @transaction
    def renew_confirmation(self, item):
        self._integrity()
        token = self.gate.renew(item)
        self.save()
        return token

    @transaction
    def revise(self, stage, reason):
        self.gate.revise(stage, reason)
        self._clear_after_revision(stage, reason)

    def _clear_after_revision(self, stage, reason):
        prior_report = self.state.get("report_directory")
        if prior_report:
            old = Path(prior_report)/"manifest.json"
            if old.is_file():
                manifest = json.loads(old.read_text(encoding="utf-8"))
                from .presentation import synchronize_status
                try:
                    synchronize_status(Path(prior_report), 'OBSOLETE_AFTER_REVISION')
                except (OSError, ValueError) as exc:
                    # A corrupt old image must never prevent revocation. Retain
                    # existing embedded content and mark all surviving prose obsolete.
                    import re
                    manifest['presentation_status_error'] = str(exc)
                    for name in ('analysis.md','analysis.qmd','analysis_offline.html','analysis.html'):
                        path=Path(prior_report)/name
                        if path.is_file():
                            text=path.read_text(encoding='utf-8')
                            text=re.sub(r'<!-- RC6_CURRENT_STATUS -->.*?<!-- /RC6_CURRENT_STATUS -->',
                                '<!-- RC6_CURRENT_STATUS -->OBSOLETE_AFTER_REVISION<!-- /RC6_CURRENT_STATUS -->',text,flags=re.S)
                            text=re.sub(r'&lt;!-- RC6_CURRENT_STATUS --&gt;.*?&lt;!-- /RC6_CURRENT_STATUS --&gt;',
                                '&lt;!-- RC6_CURRENT_STATUS --&gt;OBSOLETE_AFTER_REVISION&lt;!-- /RC6_CURRENT_STATUS --&gt;',text,flags=re.S)
                            path.write_text(text,encoding='utf-8')
                manifest['hashes'] = {p.relative_to(Path(prior_report)).as_posix():file_hash(p)
                    for p in sorted(Path(prior_report).rglob('*')) if p.is_file() and p.name != 'manifest.json'
                    and '__pycache__' not in p.relative_to(Path(prior_report)).parts and '.clustering_tmp' not in p.relative_to(Path(prior_report)).parts}
                manifest["status"] = "OBSOLETE_AFTER_REVISION"
                manifest["revision_reason"] = reason
                write_json(old, manifest)
            self.state.setdefault("prior_reports", []).append({"directory": prior_report,
                "status": "OBSOLETE_AFTER_REVISION", "stage": stage, "reason": reason})
        if stage <= 3:
            self.state["results"] = []
            self.state["diagnostics"] = None
            self.state.pop("diagnostics_budget_consumed", None)
            self.state.pop('candidate_batch_consumed', None)
            self.state.pop('candidate_previews', None)
            candidate_dir = self.directory/'candidate_figures'
            if candidate_dir.exists(): shutil.rmtree(candidate_dir)
            self.state.pop("sensitivity", None)
            evidence_dir = self.directory/"selection_evidence"
            if evidence_dir.exists():
                shutil.rmtree(evidence_dir)
        if stage <= 2:
            self.state.pop("assessment", None)
            for density in (self.directory/'eda_figures').glob('stage2_density.*'):
                density.unlink()
            if stage == 2 and self.state.get('eda_handoff'):
                from .workflow_evidence import summarize
                model = pd.DataFrame(self.state['model_data'])
                schema = {row['column']:{**row,'type':row['statistical_type']} for row in self.state['approved_eda']['columns']}
                self.state['eda_handoff'] = summarize(model, self.state['approved_eda'], schema, self.state['model_hash'])
        if stage == 1:
            approved_geometry = self.directory/'approved_eda_figures'
            if approved_geometry.exists(): shutil.rmtree(approved_geometry)
            for key in ("model_data", "model_hash", "fitted_preprocessing", "approved_eda", "eda_handoff", "geometry_paths"):
                self.state.pop(key, None)
            p = self.directory/"approved_model_data.csv"
            if p.exists():
                p.unlink()
        if stage <= 4:
            self.state["final_index"] = None
        self.state.pop("report_directory", None)
        self.save()


    @staticmethod
    def _validate_diagnostics_plan(plan, candidates):
        if set(plan) != {"fraction", "repeats", "seed", "policy"}:
            raise ValueError("Explicit diagnostics fraction/repeats/seed/policy required")
        if not 0 < plan["fraction"] < 1 or type(plan["repeats"]) is not int or not 2 <= plan["repeats"] <= 100:
            raise ValueError("Diagnostic fraction/repeats outside bounded range")
        if type(plan["seed"]) is not int or not 0 <= plan["seed"] < 2**32:
            raise ValueError("Valid diagnostic seed required")
        if plan["policy"] not in {"fixed_full_data_preprocessing", "refit_preprocessing"}:
            raise ValueError("Unknown preprocessing policy")
        if candidates * plan["repeats"] > 800:
            raise ValueError("Diagnostic fit count exceeds bounded scope")

    @transaction
    def respond(self, item, token, response, message_id, source="user"):
        """Parse actual reply, then use the unchanged six gate transitions.

        An explicit REVISE invalidates downstream state before any advancement.
        No method choice authorizes execution and no execution reply confirms results.
        """
        from .consent import classify
        if item not in self.gate.TRANSITIONS:
            raise ValueError("Unknown approval item")
        from datetime import datetime
        from .core import utcnow
        self._expect(self.gate.TRANSITIONS[item][1])
        pending = self.gate.state['proposals'].get(item)
        if (not pending or pending['status'] != 'PENDING' or token != pending['token']
                or pending['revision'] != self.gate.state['revision']):
            raise PermissionError('Missing, stale, consumed or cross-item pending token')
        if utcnow() >= datetime.fromisoformat(pending['expires_at']):
            raise PermissionError('Pending approval token expired; review and renew')
        parsed = classify(response, item, self.gate.state["payloads"].get(item))
        decision = {"value": parsed["value"], "stage": self.gate.ORDER[item],
                    "item": item, "response": response, "source": source, "message_id": message_id}
        if parsed["value"] == "REVISE":
            pending,following = self.gate.TRANSITIONS[item][1:]
            self._gate_approve(item, token, decision, pending, following)
            return {**parsed, "advanced": False}
        handlers = {"preprocess": lambda: self.respond_stage1("A", token, decision),
                    "method": lambda: self.approve_method(token, decision),
                    "candidates": lambda: self.permit_execution(token, decision),
                    "results": lambda: self.confirm_results(token, decision),
                    "final": lambda: self.approve_final(token, decision),
                    "delivery": lambda: self.confirm_delivery(token, decision)}
        advanced = handlers[item]()
        return {**parsed, "advanced": bool(advanced)}

    @transaction
    def respond_observed(self, item, token, response):
        """Receive a *new, directly observed* user reply when no host ID exists.

        This is an operator assertion of a fresh user turn, not proof of a
        platform-verified click or identity.  The local receipt identifies this
        single backend invocation; the original reply, current proposal token,
        stage and all six Gate checks remain mandatory.  Do not invoke this
        method for inferred, repeated, rewritten or assistant-generated text.
        """
        import uuid
        if not isinstance(response, str) or not response.strip():
            raise PermissionError('Directly observed nonempty user reply required')
        if not isinstance(token, str) or not token:
            raise PermissionError('Current pending proposal token required')
        if item not in self.gate.TRANSITIONS:
            raise ValueError('Unknown approval item')
        receipt = 'local-agent-observed:' + uuid.uuid4().hex
        # This event deliberately states its weaker provenance, rather than
        # claiming the host provided a platform message_id or signed click.
        self.gate.event('local_reply_receipt', item=item, message_id=receipt,
                        provenance='AGENT_ASSERTED_NEW_USER_TURN_NOT_PLATFORM_VERIFIED',
                        response_hash=digest(response), proposal_token_hash=digest(token))
        result = self.respond(item, token, response, receipt, source='user')
        self.save()
        return {**result, 'receipt': {
            'message_id': receipt,
            'provenance': 'AGENT_ASSERTED_NEW_USER_TURN_NOT_PLATFORM_VERIFIED',
            'platform_authenticated': False}}

    @transaction
    def diagnose_approved(self):
        """Execute previously disclosed routine work, without another approval gate."""
        self._expect("S4_REVIEW")
        plan = self.gate.state["payloads"]["candidates"].get("diagnostics_plan")
        if plan is None:
            raise PermissionError("Legacy candidate budget has no routine diagnostic authorization; return to Stage 3 and approve a bound plan")
        return self.diagnose(**plan)


    @transaction
    def refresh_delivery(self):
        """Rebind report-only edits and newly generated real logs, never models.

        Existing delivery authorization is revoked. Protected scientific files
        must match the original delivery hashes; final confirmation is fresh.
        """
        from .core import file_hash
        self._integrity()
        if self.gate.state["phase"] not in {"S5_REVIEW", "COMPLETE"}:
            raise PermissionError("No report delivery to refresh")
        report = Path(self.state["report_directory"])
        prior = self.gate.state["payloads"]["delivery"]
        protected = {"config.json", "candidate_results.json", "diagnostics.json", "model_details.json",
                     "raw_feature_snapshot.json", "model_feature_snapshot.json", "eda_handoff.json"}
        protected.update(n for n in prior["hashes"] if n.endswith(".csv") or (n.startswith("selection_evidence/") or n.startswith("figures/")))
        for name in protected:
            if file_hash(report/name) != prior["hashes"][name]:
                raise PermissionError("Scientific snapshot changed; delivery-only refresh forbidden")
        self.revise(5, "Refresh report text/log hashes without fitting or changing approved data")
        receipt = report/"delivery_confirmation.json"
        if receipt.exists():
            receipt.unlink()
        from .presentation import synchronize_status
        synchronize_status(report, 'AWAITING_USER_DELIVERY_CONFIRMATION')
        from .presentation import validate_report_images
        validate_report_images(report)
        manifest = {**prior, "status": "AWAITING_USER_DELIVERY_CONFIRMATION"}
        manifest["hashes"] = {p.relative_to(report).as_posix(): file_hash(p) for p in sorted(report.rglob("*"))
             if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.relative_to(report).parts and ".clustering_tmp" not in p.relative_to(report).parts}
        write_json(report/"manifest.json", manifest)
        token = self.gate.propose("delivery", manifest, "S5_READY", "S5_REVIEW")
        self.state["report_directory"] = str(report)
        self.save()
        return {"token": token, "manifest": manifest}


    def _gate_approve(self, key, token, decision, phase, next_phase):
        """Route revisions through Session cleanup for every public approval API."""
        from .consent import classify
        parsed = classify(decision.get("response"), key, self.gate.state["payloads"].get(key)) if isinstance(decision, dict) else {}
        accepted = self.gate.approve(key, token, decision, phase, next_phase)
        if isinstance(decision, dict) and decision.get("value") == "REVISE":
            self._clear_after_revision(min(parsed["stage"], self.gate.ORDER[key]), decision["response"])
        return accepted
