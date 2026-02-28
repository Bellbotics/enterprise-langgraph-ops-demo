from __future__ import annotations

from typing import Any, Dict

def fetch_db_summary(service: str, scenario: str) -> Dict[str, Any]:
    if scenario == "hikari_pool_exhaustion":
        return {
            "active_connections": 980,
            "max_connections": 1000,
            "avg_query_ms": 2200,
            "top_waits": ["LCK_M_S", "PAGEIOLATCH_SH"],
            "notes": "High active connections and long queries; possible lock contention and missing indexes."
        }
    return {
        "active_connections": 120,
        "max_connections": 1000,
        "avg_query_ms": 180,
        "top_waits": [],
        "notes": "DB not obviously saturated."
    }
