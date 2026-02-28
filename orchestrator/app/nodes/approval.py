from __future__ import annotations

from typing import Any, Dict

from app.edits import apply_approval_edits

def build_approval_request(state: Dict[str, Any]) -> Dict[str, Any]:
    plan = state.get("plan", {}) or {}
    required_roles = (state.get("policy", {}) or {}).get("approvals_required", []) or ["SRE_APPROVER"]
    return {
        "message": "Approval required before continuing (risky actions present).",
        "required_roles": required_roles,
        "actions_requiring_approval": [a for a in (plan.get("actions", []) or []) if a.get("requires_approval")],
        "options": ["approve", "deny", "edit"],
        "edit_schema": {
            "remove_action_ids": ["<action_id>", "..."],
            "set_action_fields": {"<action_id>": {"risk":"low|medium|high", "requires_approval": "true|false"}},
            "append_plan_notes": "string"
        }
    }

def approval_gate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    # Blocked by policy
    if state.get("policy", {}).get("allowed") is False:
        state["status"] = "blocked"
        return state

    decision = state.get("approval_decision")

    if decision in ("approve", "deny", "edit"):
        if decision == "deny":
            state["status"] = "denied"
            return state

        if decision == "edit":
            state = apply_approval_edits(state)

        state["status"] = "running"
        return state

    if bool(state.get("approval_required", False)):
        state["approval_request"] = build_approval_request(state)
        state["status"] = "needs_approval"
    return state
