from __future__ import annotations

import json
from typing import Any, Dict, List

from app.adapters.ticketing_stub import build_ticket_payload
from app.adapters.git_stub import build_patch_diff

def comms_and_artifacts_node(state: Dict[str, Any]) -> Dict[str, Any]:
    artifacts = state.get("artifacts", {}) or {}
    plan = state.get("plan", {}) or {}
    diagnosis = state.get("diagnosis", {}) or {}
    evidence = state.get("evidence", {}) or {}

    # Slack update
    actions = plan.get("actions", []) or []
    action_lines = []
    for a in actions[:5]:
        action_lines.append(f"- *{a.get('title')}* (risk={a.get('risk')}, approval={'yes' if a.get('requires_approval') else 'no'})")

    slack = f"""*Ops Copilot Update* — {state.get('service')} ({state.get('env')})
*Symptom:* {state.get('symptom')}
*Likely cause:* {diagnosis.get('primary')} (confidence={diagnosis.get('confidence')})
*Key signals:* {', '.join(state.get('signals') or [])}

*Proposed actions:*
{chr(10).join(action_lines)}

*Notes:* This is an artifact-driven recommendation; no production changes are applied by the tool.
"""
    artifacts["slack_update_md"] = slack

    # Ticket payload + patch diff
    artifacts["ticket_payload_json"] = build_ticket_payload(state)
    artifacts["git_patch_diff"] = build_patch_diff(state)

    # Full triage report
    artifacts["triage_report_json"] = {
        "thread_id": state.get("thread_id"),
        "correlation_id": state.get("correlation_id"),
        "env": state.get("env"),
        "service": state.get("service"),
        "scenario": state.get("scenario"),
        "lane": state.get("lane"),
        "diagnosis": diagnosis,
        "hypotheses": state.get("hypotheses", []),
        "evidence": evidence,
        "plan": plan,
        "policy": state.get("policy", {}),
    }

    state["artifacts"] = artifacts
    return state
