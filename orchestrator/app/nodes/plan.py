from __future__ import annotations

from typing import Any, Dict, List

def plan_node(state: Dict[str, Any]) -> Dict[str, Any]:
    scenario = state.get("scenario","generic")
    lane = state.get("lane","light")
    diagnosis = state.get("diagnosis", {}) or {}
    confidence = float(diagnosis.get("confidence", 0.5))

    actions: List[Dict[str, Any]] = []
    if scenario == "hikari_pool_exhaustion":
        actions = [
            {
                "id":"verify_db_waits",
                "title":"Verify DB waits/locks + top queries",
                "description":"Pull top waits, long-running queries, and identify missing indexes/lock contention.",
                "risk":"low",
                "requires_approval": False,
                "suggested_owner_role":"DBA",
                "artifact_types":["ticket","slack"]
            },
            {
                "id":"tune_hikari",
                "title":"Tune Hikari pool + timeouts (after DB verification)",
                "description":"Adjust pool size/timeouts/leak detection with staged rollout.",
                "risk":"medium",
                "requires_approval": True,
                "suggested_owner_role":"SRE_APPROVER",
                "artifact_types":["git_patch","ticket","slack"]
            },
            {
                "id":"move_reporting_async",
                "title":"Move heavy reporting off request path",
                "description":"Isolate heavy reporting/DB aggregation into async worker or scheduled job.",
                "risk":"high",
                "requires_approval": True,
                "suggested_owner_role":"ARCH_APPROVER",
                "artifact_types":["git_patch","ticket","slack"]
            },
        ]
    elif scenario == "pdf_heavy_memory":
        actions = [
            {
                "id":"isolate_heavy_lane",
                "title":"Split heavy PDF processing into worker deployment",
                "description":"Introduce durable work item + worker-heavy lane to prevent API pod memory spikes.",
                "risk":"high",
                "requires_approval": True,
                "suggested_owner_role":"ARCH_APPROVER",
                "artifact_types":["git_patch","ticket","slack"]
            },
            {
                "id":"resource_tuning",
                "title":"Set worker memory requests/limits + concurrency caps",
                "description":"Tune worker resources and limit concurrency to stabilize memory usage.",
                "risk":"medium",
                "requires_approval": True,
                "suggested_owner_role":"SRE_APPROVER",
                "artifact_types":["git_patch","ticket","slack"]
            },
        ]
    else:
        actions = [
            {
                "id":"collect_more_evidence",
                "title":"Collect more evidence",
                "description":"Add adapters for logs/traces/deploy history; rerun with richer signals.",
                "risk":"low",
                "requires_approval": False,
                "suggested_owner_role":"SRE",
                "artifact_types":["ticket","slack"]
            }
        ]

    # Risk & confidence gating meta
    requires_approval = any(a.get("requires_approval") for a in actions)
    if confidence < 0.6:
        # Low confidence -> force approval even for medium steps
        for a in actions:
            if a.get("risk") in ("medium", "high"):
                a["requires_approval"] = True

    state["plan"] = {
        "lane": lane,
        "summary": f"Proposed actions for scenario={scenario} (confidence={confidence:.2f})",
        "actions": actions
    }
    state["approval_required"] = requires_approval
    return state
