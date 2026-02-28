from __future__ import annotations

from typing import Any, Dict

from app.adapters.datadog_mock import fetch_datadog_summary
from app.adapters.k8s_mock import fetch_k8s_summary
from app.adapters.sql_mock import fetch_db_summary

def evidence_k8s(state: Dict[str, Any]) -> Dict[str, Any]:
    state.setdefault("evidence", {})
    state["evidence"]["k8s"] = fetch_k8s_summary(state.get("service",""), state.get("scenario",""))
    return state

def evidence_datadog(state: Dict[str, Any]) -> Dict[str, Any]:
    state.setdefault("evidence", {})
    state["evidence"]["datadog"] = fetch_datadog_summary(state.get("service",""), state.get("scenario",""))
    return state

def evidence_db(state: Dict[str, Any]) -> Dict[str, Any]:
    state.setdefault("evidence", {})
    state["evidence"]["db"] = fetch_db_summary(state.get("service",""), state.get("scenario",""))
    return state
