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
    def create(cls, csv_path, directory, dictionary=None, require_role_confirmation=False, stage4_candidate_execution=False, auto_stage4_diagnostics=False):
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
        gate = Gate().state
        if type(stage4_candidate_execution) is not bool or type(auto_stage4_diagnostics) is not bool:
            raise ValueError('Stage 4 workflow flags must be boolean')
        if auto_stage4_diagnostics and not stage4_candidate_execution:
            raise ValueError('Auto Stage 4 diagnostics need Stage 4 execution workflow')
        if auto_stage4_diagnostics:
            gate['stage4_auto_diagnostics'] = True
        if stage4_candidate_execution:
            gate['stage4_candidate_execution'] = True
        if require_role_confirmation:
            gate['role_gate_required'] = True
            gate['phase'] = 'S1_ROLE_REVIEW'
        write_json(directory/"session.json", {"format_version": 2, "input_sha256": file_hash(source),
            "dictionary": dictionary or {}, "eda": eda, "gate": gate,
            "results": [], "diagnostics": None, "final_index": None})
        s = cls(directory)
        from .figures import eda_figures
        eda_figures(raw, eda, directory/"eda_figures")
        from .workflow_evidence import geometry_figures
        schema = {row['column']: {**row, 'type':row['statistical_type']} for row in eda['columns']}
        geometry_figures(raw, schema, directory/"eda_figures")
        return s

    def evidence_path(self, original):
        """Locate archived figures without rewriting approval-bound path strings.

        A historical EDA basis may contain an absolute path from the prior
        execution directory. Only paths under the recorded original study root
        can be resolved inside a verified local checkpoint, and the stored
        SHA-256 remains authoritative.
        """
        path = Path(original)
        if path.is_file():
            return path
        marker = self.directory/'.session_origin.json'
        if marker.is_file():
            try:
                old = Path(json.loads(marker.read_text(encoding='utf-8'))['original_directory']).resolve()
                relative = path.relative_to(old)
                replacement = (self.directory/relative).resolve()
                if replacement.is_relative_to(self.directory) and replacement.is_file():
                    return replacement
            except (KeyError, ValueError, OSError):
                pass
        return path

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
                if isinstance(basis, dict) and (not self.evidence_path(basis['path']).is_file() or file_hash(self.evidence_path(basis['path'])) != basis['sha256']):
                    affected = 2
                    break
        if affected is None and "results" in payloads and payloads["results"]["results_hash"] != digest(self.state["results"]):
            affected = 3
        if affected is None and self.gate.state.get('stage4_auto_diagnostics') and self.state.get('stage4_execution_binding'):
            bound = self.state['stage4_execution_binding']
            if (bound.get('candidate_token') != self.gate.state['approvals'].get('candidates',{}).get('token')
                    or bound.get('results_hash') != digest(self.state['results'])):
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

    def suggested_feature_roles(self):
        """Tentative auditable roles from initial audit, never an approved choice."""
        self._integrity()
        return {r['column']: r['role'] for r in self.state['eda']['columns']}

    @transaction
    def propose_feature_roles(self, roles, research_question='', association_pairs=None):
        """Stage 1B separate Hard Gate for new studies. Not a model fit."""
        self._expect('S1_ROLE_REVIEW')
        from .data import ROLES
        raw=self.raw()
        if not isinstance(roles,dict) or set(roles)!=set(raw):
            raise ValueError('Declare a role for every source feature')
        if any(r not in ROLES - {'uncertain'} for r in roles.values()):
            raise ValueError('Choose feature, supplementary, id or exclude for every variable')
        if not any(r=='feature' for r in roles.values()):
            raise ValueError('At least one clustering feature required')
        if not isinstance(research_question,str) or not isinstance(association_pairs,(list,type(None))):
            raise ValueError('Research question and optional association pairs are required in proper form')
        for pair in association_pairs or []:
            if (not isinstance(pair,list) or len(pair)!=2 or pair[0]==pair[1]
                or any(c not in raw or roles[c] not in {'feature','supplementary'} for c in pair)):
                raise ValueError('Association pairs must name two distinct source variables')
        payload={'input_hash':self.state['input_sha256'],'roles':roles,
                 'research_question':research_question.strip(),'association_pairs':association_pairs or []}
        token=self.gate.propose('roles',payload,'S1_ROLE_REVIEW','S1_ROLE_REVIEW')
        self.save()
        return token

    @transaction
    def approve_feature_roles(self, token, decision):
        self._expect('S1_ROLE_REVIEW')
        payload=self.gate.state['payloads'].get('roles')
        if payload is None or payload['input_hash']!=self.state['input_sha256']:
            raise PermissionError('Feature roles not proposed for current immutable input')
        approved=self._gate_approve('roles',token,decision,'S1_ROLE_REVIEW','S1_REVIEW')
        if approved:
            self.state['approved_feature_roles']=copy.deepcopy(payload)
        self.save()
        return approved

    @transaction
    def propose_preprocessing(self, plan):
        self._integrity()
        # New studies must bind exactly the separately approved variable roles.
        if self.gate.state.get('role_gate_required'):
            if 'roles' not in self.gate.state['approvals']:
                raise PermissionError('Stage 1B role approval is required')
            approved_roles=self.gate.state['payloads']['roles']['roles']
            if set(plan.get('schema',{})) != set(approved_roles) or any(
                plan['schema'][c].get('role') != role for c,role in approved_roles.items()):
                raise PermissionError('Preprocessing role assignments differ from approved Stage 1B; revise Stage 1 first')
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
        visual = validate_visual(observations, [self.evidence_path(p) for p in basis], limitations,
                                 [self.evidence_path(p) for p in self.state.get('geometry_paths', [])])
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
        from .method_rationale import render_stage2_method_comparison, _short_reason, _flags
        visual = result.get('eda_handoff', {}).get('visual', {})
        priorities = [{'option': key, 'method': method,
                       'priority': next(row['recommendation_priority'] for row in result['methods']
                                        if row['method'] == method),
                       'reason': _short_reason(method, _flags(visual), result['purpose'])}
                      for key, method in options.items()]
        return {'token': token, 'options': options, 'recommendation_priorities': priorities,
                'comparison_markdown': render_stage2_method_comparison(result,options),
                'priority_legend': result['priority_legend'],
                'scope': 'Choose one method and enter Stage 3 planning only; no model execution'}

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
        from .education import DISCLOSURE
        result["statistical_disclosure"] = DISCLOSURE
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
        from .education import study_disclosure, planned_evidence
        _predisclosed = planned_evidence(self.method(), configs)
        payload = {"statistical_disclosure": study_disclosure(self.method(), configs, _predisclosed),
            "planned_metric_evidence": copy.deepcopy(_predisclosed), "configs": configs, "basis": basis, "evidence": evidence,
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
    def propose_candidate_expansion(self, new_configs, new_parameter_sources, reason,
                                    budget=None, diagnostics_plan=None):
        """At Stage 4 return to a *new* Stage 3 gate, reusing verified history.

        Only append new configurations; previously assessed candidates retain
        their exact configuration and ordering. No fitting happens here.
        Authorization on the new combined scope is mandatory.
        """
        self._expect('S4_REVIEW')
        if not isinstance(reason,str) or not reason.strip():
            raise ValueError('An observed boundary or other statistical reason is required')
        if (not isinstance(new_configs,list) or not new_configs or
            not isinstance(new_parameter_sources,list) or len(new_configs)!=len(new_parameter_sources)):
            raise ValueError('Explicit new configs and one source mapping per config required')
        prior = copy.deepcopy(self.gate.state['payloads']['candidates'])
        results = copy.deepcopy(self.state['results'])
        if len(results) != len(prior['configs']) or any(
                r['config'] != c for r,c in zip(results,prior['configs'])):
            raise PermissionError('Prior candidate evidence is incomplete or changed')
        legacy_bound = self.state.get('stage3_stability_bound')
        prior_diagnostics = self.state.get('diagnostics')
        if legacy_bound is not None:
            if digest(results) != legacy_bound['results_hash']:
                raise PermissionError('Historical Stage 3 stability binding mismatch')
            prior_stability = copy.deepcopy(self.state['stage3_stability'])
        elif prior_diagnostics is not None and len(prior_diagnostics.get('stability', [])) == len(results):
            # New boundary: prior Stage 4 diagnostics are the certified source.
            if 'final' in self.gate.state['approvals']:
                raise PermissionError('Revise final decision before expanding already selected model')
            prior_stability = copy.deepcopy(prior_diagnostics['stability'])
        else:
            raise PermissionError('Candidate expansion requires completed approved Stage 4 stability; diagnose first')
        if any(c in prior['configs'] for c in new_configs) or len({digest(c) for c in new_configs}) != len(new_configs):
            raise ValueError('Expansion must append unique, genuinely new configurations')
        from .engine import validate_config
        for c in new_configs:
            validate_config(self.method(), c, len(self.model()))
        combined = prior['configs']+copy.deepcopy(new_configs)
        new_budget = copy.deepcopy(budget) if budget is not None else copy.deepcopy(prior['budget'])
        if new_budget['max_candidates'] < len(combined):
            raise ValueError('New budget must cover the full revised candidate list')
        new_diag = copy.deepcopy(diagnostics_plan) if diagnostics_plan is not None else copy.deepcopy(prior['diagnostics_plan'])
        self._validate_diagnostics_plan(new_diag, len(combined))
        # Preserve immutable source snapshots only, never an authorization.
        archive = {'model_hash':self.state['model_hash'],'method':self.method(),
                   'results_hash':digest(results),'results':results,
                   'configs':copy.deepcopy(prior['configs']),
                   'stability':prior_stability,
                   'diagnostics_hash':digest(prior_diagnostics) if prior_diagnostics is not None else None,
                   'diagnostics_plan':copy.deepcopy(prior['diagnostics_plan']),
                   'previous_revision':self.gate.state['revision'],
                   'initialization':copy.deepcopy(self.state.get('diagnostics',{}).get('initialization',{})),
                   'initialization_plan':copy.deepcopy(prior.get('initialization_plan'))}
        self.revise(3, 'Explicit revised Stage 3 expansion requested: '+reason)
        self.state['candidate_reuse_archive'] = archive
        self.save()
        token = self.propose_candidates(
            combined, 'exploratory-only', prior['evidence']+' 擴展理由：'+reason,
            new_budget, new_diag,
            prior['parameter_sources']+copy.deepcopy(new_parameter_sources),
            prior['search_rationale']+' 新增探索：'+reason,
            prior['boundary_limitations']+' 擴展仍不是自然群數證明。',
            prior.get('initialization_plan'))
        self.gate.event('candidate_expansion_proposed', retained=len(prior['configs']),
                        new=len(new_configs), fits=0, new_authorization_required=True)
        self.save()
        return {'token':token,'reused_candidates_planned':len(prior['configs']),
                'new_candidates':len(new_configs),'total_candidates':len(combined),
                'status':'WAITING_NEW_STAGE3_EXECUTION_APPROVAL'}

    @transaction
    def permit_execution(self, token, decision):
        self._integrity()
        next_phase = self.gate.TRANSITIONS['candidates'][2]
        accepted = self._gate_approve("candidates", token, decision, "S3_PERMISSION", next_phase)
        self.save()
        return accepted

    @transaction
    def recover_interrupted_execution(self, reason):
        """Fail-closed recovery for a consumed authorized fit batch with no result.

        A crashed process may have spent part of its budget; never retry it
        under the old approval. Recreate the *same* proposal after revoking
        that approval, requiring a new observed user decision.
        """
        self._expect(self.gate.TRANSITIONS['candidates'][2])
        if not isinstance(reason,str) or not reason.strip():
            raise ValueError('Explicit interruption reason required')
        if not self.state.get('candidate_batch_consumed'):
            raise PermissionError('No consumed execution batch to recover; use normal authorized execution')
        if self.state.get('results'):
            raise PermissionError('Partial or completed results exist; inspect before any recovery')
        if 'results' in self.gate.state['payloads']:
            raise PermissionError('Results proposal exists; do not revise or re-run behind the review gate')
        payload=copy.deepcopy(self.gate.state['payloads']['candidates'])
        self.revise(3,'Previously authorized fit batch interrupted: '+reason)
        token=self.propose_candidates(payload['configs'],payload['basis'],payload['evidence'],
            payload['budget'],payload.get('diagnostics_plan'),
            payload['parameter_sources'],payload['search_rationale'],
            payload['boundary_limitations'],payload.get('initialization_plan'))
        self.gate.event('interrupted_execution_recovery_proposed',reused_fit_count=0,
                        original_batch_authorization_revoked=True,
                        new_authorization_required=True)
        self.save()
        return {'token':token,'status':'NEW_STAGE3_APPROVAL_REQUIRED',
                'original_execution_not_retried':True,
                'candidate_count':len(payload['configs'])}

    @transaction
    def fit_candidates(self):
        from .engine import bounded_fit
        self._expect(self.gate.TRANSITIONS['candidates'][2])
        payload = self.gate.state["payloads"]["candidates"]
        model, plan = self.model(), self.plan()
        schema = {c: plan["schema"][c] for c in model}
        if self.state.get('candidate_batch_consumed'):
            raise PermissionError('Candidate batch budget consumed; revise Stage 3 and obtain fresh authorization')
        self.state['candidate_batch_consumed'] = self.gate.state['approvals']['candidates']['token']
        self.gate.event('candidate_batch_started', token=self.state['candidate_batch_consumed'])
        self.save()
        results = []
        archive = self.state.get('candidate_reuse_archive')
        verified_cache = {}
        if archive is not None:
            if (archive['model_hash'] != self.state['model_hash'] or
                    archive['method'] != self.method() or
                    digest(archive['results']) != archive['results_hash'] or
                    [r['config'] for r in archive['results']] != archive['configs']):
                raise PermissionError('Historical candidate cache integrity failure; no fit performed')
            verified_cache = {digest(c):copy.deepcopy(r) for c,r in zip(archive['configs'],archive['results'])}
        reused_count = 0
        try:
            for config in payload["configs"]:
                old = verified_cache.get(digest(config))
                if old is not None:
                    results.append(copy.deepcopy(old))
                    reused_count += 1
                else:
                    results.append(bounded_fit(model, schema, plan["weights"], self.method(), config, payload["budget"]))
            self.gate.event('candidate_incremental_execution', reuse_count=reused_count,
                            new_fit_count=len(results)-reused_count,
                            scope='Approved full revised plan; previous models only reused after hash check')
        except Exception as exc:
            self.state["results"] = []
            self.state["fit_error"] = f"{type(exc).__name__}: {exc}"
            self.gate.event("fit_failure", error=self.state["fit_error"])
            self.revise(3, 'Candidate fit failed; previous batch consumed and fresh approval required')
            raise
        self.state["results"] = results
        # Full-data fits are authorized by Stage 3, executed in Stage 4 for
        # new sessions (legacy Stage 3 for older approved studies). The bound
        # diagnostic plan authorizes only Stage 4 subsampling; no re-fits.
        if archive is not None and archive.get('initialization_plan') == payload.get('initialization_plan'):
            self.state['initialization_reuse'] = {
                'runs':copy.deepcopy(archive.get('initialization',{}).get('runs',[])),
                'configs':copy.deepcopy(archive['configs']),
                'seeds':copy.deepcopy((archive.get('initialization_plan') or {}).get('seeds'))}
        # Retain the hash-checked, previously *approved* Stage 4 evaluations
        # across this revised Stage 3 execution; they are consumed at Stage 4.
        if archive is not None:
            self.state['stage4_evaluation_reuse'] = {
                'configs': copy.deepcopy(archive['configs']),
                'results_hash': archive['results_hash'],
                'stability': copy.deepcopy(archive['stability']),
                'diagnostics_plan': copy.deepcopy(archive['diagnostics_plan'])}
        self.state.pop('candidate_reuse_archive', None)
        self.state.pop('stage3_stability', None)
        self.state.pop('stage3_stability_bound', None)
        self.state.pop('diagnostics_budget_consumed', None)
        self.state['diagnostics'] = None
        # Fixed-K group-count bars merely repeat the chosen input parameter.
        # New research puts candidate fits in Stage 4 and delivers substantive
        # Stage 4 partition/quality/stability evidence after result confirmation.
        # Preserve legacy previews only when loading an old, already approved
        # session whose R4H.2 presentation contract requires one.
        if self.gate.state.get('stage4_candidate_execution', False):
            self.state['candidate_previews'] = []
        else:
            from .figures import candidate_partition_preview, preview_assets
            preview_dir = self.directory/'candidate_figures'
            preview_dir.mkdir(exist_ok=True)
            preview_path = candidate_partition_preview(model, results, preview_dir/'stage3_candidate_preview.svg')
            self.state['candidate_previews'] = preview_assets([preview_path]) if preview_path else []
        self.state.pop("fit_error", None)
        if self.gate.state.get('stage4_auto_diagnostics', False):
            # There is NO synthetic user approval for the now-removed result
            # gate: Stage 3 authorized both batches, and the final K selection
            # remains a genuine separate Stage 4 human gate.
            self.state['stage4_execution_binding'] = {
                'candidate_token':self.gate.state['approvals']['candidates']['token'],
                'results_hash':digest(results)}
            self.gate.state['phase']='S4_REVIEW'
            self.gate.event('stage4_authorized_fit_complete', result_count=len(results),
                            results_hash=digest(results), no_intermediate_result_gate=True)
            self.save()
            # Explicitly execute the previously authorized diagnostics in the
            # same action, not by prose instruction or a fabricated consent.
            diagnostics=self.diagnose_approved()
            return {'status':'STAGE4_DIAGNOSTICS_COMPLETE',
                    'candidate_count':len(results),
                    'stability_batches':len(diagnostics['stability']),
                    'final_selection_requires_user_approval':True}
        execution_phase, results_phase = self.gate.TRANSITIONS['results'][:2]
        token = self.gate.propose("results", {"results_hash": digest(results), "count": len(results),
            "candidate_hash": digest(payload)}, execution_phase, results_phase)
        self.save()
        return token

    @transaction
    def confirm_results(self, token, decision):
        if self.gate.state.get('stage4_auto_diagnostics',False):
            raise PermissionError('New Stage 4 execution uses the Stage 3 authorization; no results approval exists')
        self._integrity()
        payload = self.gate.state["payloads"].get("results", {})
        if payload.get("results_hash") != digest(self.state["results"]):
            raise ValueError("Candidate results changed")
        results_phase = self.gate.TRANSITIONS['results'][1]
        accepted = self._gate_approve("results", token, decision, results_phase, "S4_REVIEW")
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
        requested = {"fraction": fraction, "repeats": repeats, "seed": seed, "policy": policy}
        if requested != allowed:
            raise PermissionError("Diagnostic settings exceed or differ from approved plan; obtain explicit revised authorization")
        if self.state.get('diagnostics') is not None:
            raise PermissionError('Stage 4 diagnostic evidence already finalized')
        bound = self.state.get('stage3_stability_bound')
        if bound is not None:
            # Backward-compatible read of verified R4D studies; never rerun
            # already approved old Stage 3 work merely to migrate versions.
            if (bound['results_hash'] != digest(self.state['results'])
                    or bound['candidate_plan_hash'] != digest(payload)
                    or bound['diagnostics_plan_hash'] != digest(allowed)):
                raise PermissionError('Legacy Stage 3 stability binding changed')
            result = copy.deepcopy(self.state['stage3_stability'])
            if len(result) != len(self.state['results']) or any(len(d['runs']) != repeats for d in result):
                raise PermissionError('Incomplete legacy Stage 3 stability evidence')
            self.gate.event('legacy_stage3_stability_reused', additional_stability_fits=0)
        else:
            if self.state.get('diagnostics_budget_consumed'):
                raise PermissionError('Approved Stage 4 diagnostic budget already consumed')
            # A crash may have consumed part of the budget. Fail closed: no
            # replay using the same approval; revision required.
            self.state['diagnostics_budget_consumed'] = True
            self.gate.event('stage4_diagnostics_budget_consumed',
                            upper_fit_bound=len(self.state['results'])*repeats,
                            settings=requested)
            self.save()
            reuse = self.state.get('stage4_evaluation_reuse') or {}
            source_configs = reuse.get('configs', [])
            compatible = reuse.get('diagnostics_plan') == allowed
            result = []
            reused = 0
            try:
                for i, fitted in enumerate(self.state['results']):
                    cached = None
                    if (compatible and i < len(source_configs)
                            and fitted['config'] == source_configs[i]
                            and i < len(reuse.get('stability', []))):
                        prior = reuse['stability'][i]
                        if len(prior.get('runs', [])) == repeats:
                            cached = copy.deepcopy(prior)
                    if cached is not None:
                        result.append(cached)
                        reused += 1
                    else:
                        result.append(stability(self.raw(), self.model(), self.plan(), self.method(), fitted,
                            payload['budget'], fraction, repeats, seed, policy,
                            audit_path=self.directory/'fit_runtime_events.jsonl', candidate_index=i))
            except Exception as exc:
                self.gate.event('stage4_diagnostics_failed', error=f'{type(exc).__name__}: {exc}',
                                previous_completed=len(result), budget_consumed=True)
                self.save()
                raise
            self.gate.event('stage4_stability_evaluated', reused_batches=reused,
                            executed_batches=len(result)-reused, repeats=repeats,
                            full_data_candidate_refits=0)
            self.state.pop('stage4_evaluation_reuse', None)
        diagnostics = {"stability": result, "selection": "No automatic winner or weighted composite; user decision required",
            "boundary_warning": "If a preferred candidate is at either search boundary, consider returning to Stage 3; never auto-expand",
            "wcss_caution": "WCSS reduction alone is insufficient for selecting K",
            "interpretation": "分群具探索性；品質或穩定性並不證明自然群組存在"}
        from .selection_evidence import initialization_diagnostics, build_selection_evidence
        diagnostics["initialization"] = initialization_diagnostics(self, payload.get("initialization_plan"))
        self.state["diagnostics"] = diagnostics
        self.save()
        diagnostics["selection_evidence"] = build_selection_evidence(self)
        from pathlib import Path as _Path
        _evidence_path = _Path(diagnostics['selection_evidence']['directory'])/'selection_evidence.json'
        diagnostics['metric_contrast'] = json.loads(_evidence_path.read_text(encoding='utf-8'))['metric_contrast']
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
            from .figures import selected_partition_figure
            idx=self.state["final_index"]
            if idx is not None:
                path=selected_partition_figure(self.model(), self.state['results'][idx],
                    self.directory/'stage4_final_evidence'/'stage4_selected_partition.svg')
                if path:
                    self.state['stage4_selected_partition_hash'] = file_hash(path)
                    self.state['stage4_selected_partition_png_hash'] = file_hash(path.with_suffix('.png'))
                    self.state['stage4_selected_partition_source'] = digest(self.state['results'][idx]['labels'])
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
        # The research delivery is user-facing.  The Gate retains its real
        # authorization token internally in session.json; the report must not
        # export a raw token or its TTL even after delivery confirmation.
        from .privacy import public_output
        write_json(report/"delivery_confirmation.json", {"status": confirmed_status,
            "approved_manifest_payload_hash": digest(bound),
            "confirmation": public_output(self.gate.state["events"][-1]),
            "privacy": "Manifest content hash only; live approval credentials omitted"})
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
        if stage <= 1:
            self.state.pop('approved_feature_roles',None)
        if stage <= 3:
            self.state["results"] = []
            self.state["diagnostics"] = None
            self.state.pop("diagnostics_budget_consumed", None)
            self.state.pop('candidate_batch_consumed', None)
            self.state.pop('candidate_previews', None)
            self.state.pop('stage4_execution_binding', None)
            self.state.pop('stage3_stability', None)
            self.state.pop('stage3_stability_bound', None)
            if stage <= 2:
                self.state.pop('candidate_reuse_archive', None)
                self.state.pop('stage4_evaluation_reuse', None)
            self.state.pop('initialization_reuse', None)
            candidate_dir = self.directory/'candidate_figures'
            if candidate_dir.exists(): shutil.rmtree(candidate_dir)
            self.state.pop("sensitivity", None)
            evidence_dir = self.directory/"selection_evidence"
            if evidence_dir.exists():
                shutil.rmtree(evidence_dir)
        if stage <= 4:
            final_figures=self.directory/'stage4_final_evidence'
            if final_figures.exists():
                shutil.rmtree(final_figures)
            self.state.pop('stage4_selected_partition_hash',None)
            self.state.pop('stage4_selected_partition_png_hash',None)
            self.state.pop('stage4_selected_partition_source',None)
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
        handlers = {"roles": lambda: self.approve_feature_roles(token, decision),
                    "preprocess": lambda: self.respond_stage1("A", token, decision),
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
