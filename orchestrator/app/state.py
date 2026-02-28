from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TypedDict

Env = Literal["dev", "staging", "prod"]

class Action(TypedDict, total=False):
    id: str
    title: str
    description: str
    risk: Literal["low", "medium", "high"]
    requires_approval: bool
    suggested_owner_role: str
    artifact_types: List[str]  # e.g., ["git_patch", "ticket", "slack"]

class Evidence(TypedDict, total=False):
    k8s: Dict[str, Any]
    datadog: Dict[str, Any]
    db: Dict[str, Any]
    service: Dict[str, Any]

class PolicyResult(TypedDict, total=False):
    allowed: bool
    blocks: List[str]
    redactions_applied: int
    approvals_required: List[str]  # roles

class RunArtifacts(TypedDict, total=False):
    slack_update_md: str
    ticket_payload_json: Dict[str, Any]
    git_patch_diff: str
    triage_report_json: Dict[str, Any]

class OpsState(TypedDict, total=False):
    # Identifiers
    thread_id: str
    correlation_id: str

    # Input
    env: Env
    service: str
    symptom: str
    scenario: str
    severity: str
    signals: List[str]
    constraints: List[str]

    # Derived
    lane: Literal["light", "heavy"]
    evidence: Evidence
    hypotheses: List[Dict[str, Any]]
    diagnosis: Dict[str, Any]
    plan: Dict[str, Any]  # includes actions
    policy: PolicyResult

    # Approval
    approval_required: bool
    approval_request: Dict[str, Any]
    approval_decision: Optional[Literal["approve", "deny", "edit"]]
    approval_edits: Optional[Dict[str, Any]]

    # Output
    artifacts: RunArtifacts
    status: Literal["running", "needs_approval", "blocked", "completed", "denied", "failed"]
    errors: List[str]

def merge_lists(a: List[Any] | None, b: List[Any] | None) -> List[Any]:
    return (a or []) + (b or [])

def merge_dicts(a: Dict[str, Any] | None, b: Dict[str, Any] | None) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if a:
        out.update(a)
    if b:
        out.update(b)
    return out

# Reducers: when parallel branches write to the same keys, LangGraph needs merge rules.
REDUCERS = {
    "signals": merge_lists,
    "constraints": merge_lists,
    "errors": merge_lists,
    "hypotheses": merge_lists,
    "evidence": merge_dicts,
    "artifacts": merge_dicts,
}
