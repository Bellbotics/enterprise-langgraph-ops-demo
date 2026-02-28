from __future__ import annotations

import os
import yaml
from typing import Any, Dict

from langgraph.graph import StateGraph, END

from app.state import OpsState, REDUCERS
from app.nodes.intake import intake_node
from app.nodes.evidence import evidence_k8s, evidence_datadog, evidence_db
from app.nodes.diagnose import diagnose_node
from app.nodes.plan import plan_node
from app.nodes.comms import comms_and_artifacts_node
from app.nodes.approval import approval_gate_node
from app.policy import policy_gate
from app.storage import build_checkpointer

def load_policy_cfg() -> Dict[str, Any]:
    path = os.getenv("POLICY_PATH", "/app/app/policies/policy.yaml")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

def config_for_thread(thread_id: str) -> Dict[str, Any]:
    # LangGraph uses RunnableConfig with a "configurable.thread_id" for checkpointing.
    return {"configurable": {"thread_id": thread_id}}

def build_graph():
    policy_cfg = load_policy_cfg()

    g = StateGraph(OpsState)

    # Reducers for parallel merges
    for key, reducer in REDUCERS.items():
        try:
            g.add_reducer(key, reducer)  # newer versions
        except Exception:
            # older versions may not expose add_reducer; safe to ignore for demo
            pass

    g.add_node("intake", intake_node)

    # Evidence collection in parallel
    g.add_node("evidence_k8s", evidence_k8s)
    g.add_node("evidence_datadog", evidence_datadog)
    g.add_node("evidence_db", evidence_db)

    g.add_node("diagnose", diagnose_node)
    g.add_node("plan", plan_node)

    # Policy gate as a node
    g.add_node("policy", lambda s: policy_gate(s, policy_cfg))

    # Approval gate
    g.add_node("approval", approval_gate_node)

    # Artifacts
    g.add_node("artifacts", comms_and_artifacts_node)

    # Flow
    g.set_entry_point("intake")
    g.add_edge("intake", "evidence_k8s")
    g.add_edge("intake", "evidence_datadog")
    g.add_edge("intake", "evidence_db")

    # Join evidence into diagnose (graph will merge state)
    g.add_edge("evidence_k8s", "diagnose")
    g.add_edge("evidence_datadog", "diagnose")
    g.add_edge("evidence_db", "diagnose")

    g.add_edge("diagnose", "plan")
    g.add_edge("plan", "policy")
    g.add_edge("policy", "approval")

    # Conditional: if needs_approval -> END (API returns approval_request); else continue
    def route_after_approval(state: Dict[str, Any]) -> str:
        status = state.get("status")
        if status == "needs_approval":
            return END
        if status in ("blocked", "denied"):
            return END
        return "artifacts"

    g.add_conditional_edges("approval", route_after_approval, {"artifacts": "artifacts", END: END})
    g.add_edge("artifacts", END)

    # Compile with persistence when available.
    # We build checkpointer at import-time and keep it alive for the process.
    # For Postgres, ensure DATABASE_URL is set.
    global _CHECKPOINTER
    if "_CHECKPOINTER" not in globals():
        # Create one and keep it for the lifetime of the service.
        cm = build_checkpointer()
        _CHECKPOINTER = cm.__enter__()  # noqa: SLF001

    try:
        return g.compile(checkpointer=_CHECKPOINTER)  # type: ignore[arg-type]
    except TypeError:
        # Older versions: compile() may not accept checkpointer
        return g.compile()
