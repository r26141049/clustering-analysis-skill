"""Dependency-free persistence, explicit consent and revision-bound hard gates.

Consent is an operator assertion recording a real user response, not an
authentication mechanism. Agents must never manufacture user responses.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import os
import shutil
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta


def utcnow():
    return datetime.now(timezone.utc)


class WorkspaceTemp:
    """Inherited-ACL temp directories for sandboxed Windows runtimes.

    Python's owner-only mkdtemp ACL can exclude an impersonated sandbox token.
    Use a dedicated agent-private workspace, never a shared/public directory.
    """
    def __init__(self, prefix="clustering-"):
        self.base = Path(os.environ.get("CLUSTERING_TEMP_ROOT", str(Path.cwd()/".clustering_tmp"))).resolve()
        self.base.mkdir(parents=True, exist_ok=True)
        self.path = self.base/(prefix+uuid.uuid4().hex)
        self.path.mkdir(mode=0o777)
        self.name = str(self.path)

    def __enter__(self):
        return self.name

    def cleanup(self):
        resolved = self.path.resolve()
        if resolved.parent != self.base or self.path.is_symlink():
            raise ValueError("Refusing temp cleanup outside the verified workspace root")
        if self.path.exists():
            shutil.rmtree(self.path)

    def __exit__(self, *args):
        self.cleanup()

METHODS = ("kmeans", "hierarchical", "dbscan", "pam")
PENDING_RESEARCH = {"hopkins": "NOT VALIDATED", "vat": "NOT VALIDATED",
                    "gap": "NOT VALIDATED"}


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if hasattr(value, "tolist"):
        return clean(value.tolist())
    if hasattr(value, "item"):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def digest(value):
    return hashlib.sha256(json.dumps(clean(value), sort_keys=True,
                          ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(clean(value), ensure_ascii=False, indent=2,
                              allow_nan=False), encoding="utf-8")
    os.replace(tmp, path)


class Gate:
    """Explicit decisions bound to session, stage, item, revision and proposal.

    User-message provenance is recorded, not authenticated by this local API.
    A qa_fixture decision can never serve as evidence of real-user acceptance.
    """
    ORDER = {"roles": 1, "preprocess": 1, "method": 2, "candidates": 3,
             "results": 3, "final": 4, "delivery": 5}
    TRANSITIONS = {
        "roles": ("S1_ROLE_REVIEW", "S1_ROLE_REVIEW", "S1_REVIEW"),
        "preprocess": ("S1_REVIEW", "S1_REVIEW", "S2_REVIEW"),
        "method": ("S2_REVIEW", "S2_REVIEW", "S3_PLAN"),
        "candidates": ("S3_PLAN", "S3_PERMISSION", "S3_EXECUTE"),
        "results": ("S3_EXECUTE", "S3_RESULTS", "S4_REVIEW"),
        "final": ("S4_REVIEW", "S4_REVIEW", "S5_READY"),
        "delivery": ("S5_READY", "S5_REVIEW", "COMPLETE")}
    AFFIRMATIVE = {"同意", "批准", "確認", "是", "a", "approve", "yes", "confirm"}
    TTL_SECONDS = 86400
    PHASE_REQUIREMENTS = {
        "S1_ROLE_REVIEW": (), "S1_REVIEW": (), "S2_REVIEW": ("preprocess",),
        "S3_PLAN": ("preprocess", "method"), "S3_PERMISSION": ("preprocess", "method"),
        "S3_EXECUTE": ("preprocess", "method", "candidates"),
        "S3_RESULTS": ("preprocess", "method", "candidates"),
        "S4_REVIEW": ("preprocess", "method", "candidates", "results"),
        "S5_READY": ("preprocess", "method", "candidates", "results", "final"),
        "S5_REVIEW": ("preprocess", "method", "candidates", "results", "final"),
        "COMPLETE": tuple(ORDER)}

    def __init__(self, state=None):
        self.state = copy.deepcopy(state) if state else {
            "auth_format": 2, "session_id": uuid.uuid4().hex,
            "phase": "S1_REVIEW", "revision": 0, "approvals": {},
            "payloads": {}, "proposals": {}, "events": [], "used_message_ids": [], "complete": False}
        # Isolate Stage 4 candidate-execution transitions by session. Never
        # silently migrate or re-authorize already approved historical studies.
        self.TRANSITIONS = dict(type(self).TRANSITIONS)
        self.PHASE_REQUIREMENTS = dict(type(self).PHASE_REQUIREMENTS)
        if self.state.get('stage4_candidate_execution', False):
            self.TRANSITIONS['candidates'] = ('S3_PLAN','S3_PERMISSION','S4_EXECUTE')
            self.TRANSITIONS['results'] = ('S4_EXECUTE','S4_RESULTS','S4_REVIEW')
            self.PHASE_REQUIREMENTS['S4_EXECUTE'] = ('preprocess','method','candidates')
            self.PHASE_REQUIREMENTS['S4_RESULTS'] = ('preprocess','method','candidates')
        if self.state.get('stage4_auto_diagnostics', False):
            if not self.state.get('stage4_candidate_execution', False):
                raise ValueError('Automatic Stage 4 diagnostics require Stage 4 candidate execution')
            for phase in ('S4_REVIEW','S5_READY','S5_REVIEW','COMPLETE'):
                self.PHASE_REQUIREMENTS[phase] = tuple(k for k in self.PHASE_REQUIREMENTS[phase] if k != 'results')
        if self.state.get("auth_format") != 2 or not self.state.get("session_id") or "used_message_ids" not in self.state:
            raise ValueError("RC1/legacy consent cannot be trusted as RC2 approval; start a new session and reconfirm")

    def dependencies(self, key):
        prior = list(self.ORDER)[:list(self.ORDER).index(key)]
        return {k: self.state["approvals"][k]["token"] for k in prior if k in self.state["approvals"]}

    def _token(self, key, proposal):
        return digest({"session_id": self.state["session_id"], "item": key,
            **{k: proposal[k] for k in ("stage", "revision", "nonce", "payload_hash", "dependencies", "expires_at")}})

    def affected_stage(self):
        """Find modified approved/pending content before any authorized action."""
        required = self.PHASE_REQUIREMENTS.get(self.state["phase"])
        if required is None:
            return 1
        if self.state.get("role_gate_required") and self.state["phase"] not in ("S1_ROLE_REVIEW", "S1_REVIEW") and "roles" not in self.state["approvals"]:
            return 1
        for key in required:
            if key == 'roles' and not self.state.get('role_gate_required',False):
                continue
            if key not in self.state["approvals"]:
                return self.ORDER[key]
        for key in self.ORDER:
            payload = self.state["payloads"].get(key)
            p = self.state["proposals"].get(key)
            approval = self.state["approvals"].get(key)
            if payload is None and p is None and approval is None:
                continue
            try:
                if p is None or payload is None or p["stage"] != self.ORDER[key] or p["payload_hash"] != digest(payload):
                    return self.ORDER[key]
                if p["dependencies"] != self.dependencies(key) or p["token"] != self._token(key, p):
                    return self.ORDER[key]
                if approval is not None and (p["status"] != "APPROVED" or
                    approval["token"] != p["token"] or approval["payload_hash"] != p["payload_hash"] or
                    approval["stage"] != self.ORDER[key] or approval["item"] != key or
                    approval["session_id"] != self.state["session_id"] or
                    approval["decision"]["message_id"] not in self.state["used_message_ids"]):
                    return self.ORDER[key]
            except (KeyError, TypeError, ValueError):
                return self.ORDER[key]
        return None

    def ensure_integrity(self):
        stage = self.affected_stage()
        if stage is not None:
            self.revise(stage, "Approved or pending payload/dependency binding changed")
            raise PermissionError("Settings changed: affected and downstream approvals revoked")

    def expect(self, phase):
        self.ensure_integrity()
        if self.state["phase"] != phase:
            raise PermissionError(f"Expected {phase}; current {self.state['phase']}")

    def event(self, action, **details):
        self.state["events"].append({"time": utcnow().isoformat(),
            "action": action, "revision": self.state["revision"], **clean(details)})

    def propose(self, key, payload, phase, next_phase):
        if key not in self.TRANSITIONS or (phase, next_phase) != self.TRANSITIONS[key][:2]:
            raise PermissionError("Proposal item/stage/phase binding does not match the fixed workflow")
        self.expect(phase)
        prior = list(self.ORDER)[:list(self.ORDER).index(key)]
        if not self.state.get("role_gate_required", False):
            prior = [k for k in prior if k != "roles"]
        if self.state.get('stage4_auto_diagnostics', False):
            prior = [k for k in prior if k != 'results']
        if any(k not in self.state["approvals"] for k in prior):
            raise PermissionError("Prerequisite approvals missing")
        return self._new_proposal(key, payload, next_phase)

    def _new_proposal(self, key, payload, next_phase):
        self.state["payloads"][key] = copy.deepcopy(clean(payload))
        p = {"stage": self.ORDER[key], "revision": self.state["revision"],
             "nonce": uuid.uuid4().hex, "payload_hash": digest(payload),
             "dependencies": self.dependencies(key), "expires_at": (utcnow()+timedelta(seconds=self.TTL_SECONDS)).isoformat(),
             "status": "PENDING"}
        p["token"] = self._token(key, p)
        self.state["proposals"][key] = p
        self.state["approvals"].pop(key, None)
        self.state["phase"] = next_phase
        self.event("propose", key=key, payload_hash=p["payload_hash"], token=p["token"], expires_at=p["expires_at"])
        return p["token"]

    def renew(self, key):
        if key not in self.TRANSITIONS:
            raise ValueError("Unknown approval item")
        self.expect(self.TRANSITIONS[key][1])
        if key not in self.state["payloads"]:
            raise PermissionError("No pending payload to renew")
        return self._new_proposal(key, self.state["payloads"][key], self.state["phase"])

    def approve(self, key, token, decision, phase, next_phase):
        if key not in self.TRANSITIONS or (phase, next_phase) != self.TRANSITIONS[key][1:]:
            raise PermissionError("Approval cannot change the fixed stage/item transition")
        self.expect(phase)
        p = self.state["proposals"].get(key)
        if p is None or p["status"] != "PENDING" or token != p["token"] or p["revision"] != self.state["revision"]:
            raise PermissionError("Approval is absent, rejected, consumed or stale")
        if utcnow() >= datetime.fromisoformat(p["expires_at"]):
            raise PermissionError("Pending approval token expired; review and renew before responding")
        fields = {"value", "stage", "item", "response", "source", "message_id"}
        if not isinstance(decision, dict) or set(decision) != fields:
            raise PermissionError("Explicit structured decision required; nonempty text is not consent")
        d = copy.deepcopy(decision)
        if d["value"] not in {"APPROVE", "REJECT", "REVISE", "CLARIFY", "UNCERTAIN"} or type(d["stage"]) is not int or d["stage"] != self.ORDER[key] or d["item"] != key:
            raise PermissionError("Decision value/stage/item does not match pending approval")
        if d["source"] not in {"user", "qa_fixture"} or not isinstance(d["message_id"], str) or not d["message_id"].strip():
            raise PermissionError("Decision source and distinct message reference required")
        if not isinstance(d["response"], str) or not d["response"].strip():
            raise PermissionError("Missing reply cannot authorize an action")
        from .consent import classify
        parsed = classify(d["response"], key, self.state["payloads"][key])
        if d["value"] == "APPROVE" and parsed["value"] != "APPROVE":
            raise PermissionError("Reply does not unambiguously approve the pending scope; revise or clarify")
        if d["value"] == "REVISE" and parsed["value"] != "REVISE":
            raise PermissionError("REVISE requires a revision request")
        if any(a["decision"]["source"] != d["source"] for a in self.state["approvals"].values()):
            raise PermissionError("QA fixture and user-declared approval cannot be mixed; restart/reconfirm from Stage 1")
        if d["message_id"] in self.state["used_message_ids"]:
            raise PermissionError("Reply reference already consumed; a new proposal/revision requires a fresh user reply")
        self.state["used_message_ids"].append(d["message_id"])
        if d["value"] == "REVISE":
            self.event("decision", key=key, decision=d, advanced=False)
            self.revise(min(parsed["stage"], self.ORDER[key]), "User requested revision: "+d["response"])
            return False
        if d["value"] != "APPROVE":
            p["status"] = "REJECTED" if d["value"] == "REJECT" else "PENDING"
            self.event("decision", key=key, decision=d, advanced=False)
            return False
        p["status"] = "APPROVED"
        self.state["approvals"][key] = {"session_id": self.state["session_id"],
            "stage": self.ORDER[key], "item": key, "revision": self.state["revision"],
            "token": token, "payload_hash": p["payload_hash"], "decision": d,
            "scope_constraints": copy.deepcopy(parsed.get("restrictions", []))}
        self.state["phase"] = next_phase
        self.state["complete"] = next_phase == "COMPLETE"
        self.event("approve", key=key, payload_hash=p["payload_hash"], token=token, decision=d,
                   scope_constraints=parsed.get("restrictions", []))
        return True

    def revise(self, stage, reason):
        if type(stage) is not int or stage not in range(1, 6) or not reason.strip():
            raise ValueError("Valid stage and reason required")
        # Reject attempts to jump forward disguised as revision.
        current = int(self.state["phase"][1]) if self.state["phase"] != "COMPLETE" else 5
        if stage > current:
            raise PermissionError("Revision cannot skip ahead")
        self.state["revision"] += 1
        for key, number in self.ORDER.items():
            if number >= stage:
                self.state["approvals"].pop(key, None)
                self.state["payloads"].pop(key, None)
                self.state["proposals"].pop(key, None)
        self.state["complete"] = False
        self.state["phase"] = {1: "S1_ROLE_REVIEW" if self.state.get("role_gate_required") else "S1_REVIEW", 2: "S2_REVIEW",
                               3: "S3_PLAN", 4: "S4_REVIEW", 5: "S5_READY"}[stage]
        self.event("revise", stage=stage, reason=reason)


def budget_check(n, budget, *, pam=False):
    """Conservative working-set estimate; not an OS memory allocation guarantee."""
    required = {"memory_mb", "seconds_per_fit", "max_rows", "max_candidates"}
    if set(budget) != required:
        raise ValueError(f"Budget requires exactly {sorted(required)}")
    if any(type(budget[k]) not in (int, float) or not math.isfinite(budget[k])
           or budget[k] <= 0 for k in required):
        raise ValueError("Budget values must be finite positive numbers")
    if any(type(budget[k]) is not int for k in ("max_rows", "max_candidates")):
        raise ValueError("Row and candidate limits must be integers")
    if n > budget["max_rows"]:
        raise MemoryError("Approved row limit exceeded")
    lower = 8 * n * n
    estimate = lower * 12
    if estimate > budget["memory_mb"] * 1024**2:
        raise MemoryError("Estimated pairwise working set exceeds approved memory")
    return {"matrix_lower_bytes": lower, "working_estimate_bytes": estimate,
            "safety_multiplier": 12, "pam_complexity": "BUILD/SWAP O(k*n^3); row/time limits enforced" if pam else None}
