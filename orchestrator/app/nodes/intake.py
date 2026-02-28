from __future__ import annotations

import uuid
from typing import Any, Dict

def intake_node(state: Dict[str, Any]) -> Dict[str, Any]:
    state.setdefault("thread_id", state.get("thread_id") or str(uuid.uuid4()))
    state.setdefault("correlation_id", state.get("correlation_id") or str(uuid.uuid4()))
    state.setdefault("signals", [])
    state.setdefault("constraints", [])
    state.setdefault("errors", [])
    state.setdefault("status", "running")

    scenario = state.get("scenario", "generic")
    # Light vs heavy lane routing heuristic (portable across enterprises)
    if scenario in ("pdf_heavy_memory", "batch_job_backlog", "data_export_large"):
        state["lane"] = "heavy"
    else:
        state["lane"] = "light"
    return state
