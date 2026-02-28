from __future__ import annotations

from typing import Any, Dict, List

def build_ticket_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    plan = state.get("plan", {}) or {}
    diagnosis = state.get("diagnosis", {}) or {}
    return {
        "title": f"[{state.get('env','dev').upper()}] {state.get('service')} - {state.get('symptom')}",
        "priority": state.get("severity", "medium"),
        "labels": ["ops-copilot", "langgraph-demo", state.get("scenario","unknown")],
        "description": {
            "diagnosis": diagnosis,
            "plan": plan,
            "evidence": state.get("evidence", {}),
        }
    }
