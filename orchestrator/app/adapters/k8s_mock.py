from __future__ import annotations

from typing import Any, Dict

def fetch_k8s_summary(service: str, scenario: str) -> Dict[str, Any]:
    if scenario == "pdf_heavy_memory":
        return {
            "recent_restarts": 6,
            "oom_killed": True,
            "hpa_scale_events": 2,
            "notes": "Pods restarted with OOMKilled; consider workload isolation and memory limits/requests."
        }
    if scenario == "hikari_pool_exhaustion":
        return {
            "recent_restarts": 0,
            "oom_killed": False,
            "hpa_scale_events": 1,
            "notes": "No OOM; latency and errors likely downstream/DB-bound."
        }
    return {
        "recent_restarts": 0,
        "oom_killed": False,
        "hpa_scale_events": 0,
        "notes": "Normal cluster signals."
    }
