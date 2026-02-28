from __future__ import annotations

from typing import Any, Dict, List

def diagnose_node(state: Dict[str, Any]) -> Dict[str, Any]:
    scenario = state.get("scenario", "generic")
    evidence = state.get("evidence", {}) or {}

    hypotheses: List[Dict[str, Any]] = []
    diagnosis: Dict[str, Any] = {"primary": None, "confidence": 0.5, "notes": ""}

    if scenario == "hikari_pool_exhaustion":
        db = (evidence.get("db") or {})
        dd = (evidence.get("datadog") or {})
        conf = 0.75 if db.get("active_connections", 0) > 900 else 0.6
        hypotheses = [
            {"id":"db_saturation", "title":"DB saturation / lock contention", "confidence": conf,
             "verify":["check top waits", "identify long-running queries", "index analysis"]},
            {"id":"connection_leak", "title":"Connection leak in app", "confidence": 0.45,
             "verify":["enable leak detection threshold", "review transaction boundaries"]},
        ]
        diagnosis = {
            "primary": "DB saturation / long-running queries causing pool starvation",
            "confidence": conf,
            "notes": dd.get("notes","")
        }

    elif scenario == "pdf_heavy_memory":
        k8s = (evidence.get("k8s") or {})
        conf = 0.8 if k8s.get("oom_killed") else 0.6
        hypotheses = [
            {"id":"heavy_workload_competes", "title":"Heavy jobs competing with request handling", "confidence": conf,
             "verify":["separate worker deployment", "measure per-request memory spikes"]},
            {"id":"payload_bloat", "title":"Large payload or embedded images cause memory spikes", "confidence": 0.65,
             "verify":["profile heap", "stream processing", "cap upload size"]},
        ]
        diagnosis = {
            "primary": "Memory pressure from heavy workloads (OOMKilled signals)",
            "confidence": conf,
            "notes": (k8s.get("notes") or "")
        }
    else:
        hypotheses = [
            {"id":"needs_more_signals", "title":"Insufficient signals", "confidence": 0.4,
             "verify":["collect p95 latency trend", "recent deploys", "downstream dependency health"]}
        ]
        diagnosis = {"primary": "Unknown", "confidence": 0.4, "notes": "Add more evidence adapters or scenario rules."}

    state["hypotheses"] = hypotheses
    state["diagnosis"] = diagnosis
    return state
