from __future__ import annotations

from typing import Any, Dict

def fetch_datadog_summary(service: str, scenario: str) -> Dict[str, Any]:
    # Mock data that looks like what enterprises see in APM/metrics.
    if scenario == "hikari_pool_exhaustion":
        return {
            "error_rate_5xx": 0.18,
            "p95_latency_ms": 4200,
            "apm_top_errors": ["SQLTransientConnectionException", "HikariPool - Connection is not available"],
            "notes": "Symptoms consistent with DB connection pool saturation or long-running queries."
        }
    if scenario == "pdf_heavy_memory":
        return {
            "error_rate_5xx": 0.11,
            "p95_latency_ms": 3100,
            "apm_top_errors": ["OutOfMemoryError", "GC overhead limit exceeded"],
            "notes": "Memory pressure during heavy jobs; look for large payloads or image-heavy PDFs."
        }
    return {
        "error_rate_5xx": 0.03,
        "p95_latency_ms": 750,
        "apm_top_errors": [],
        "notes": "No strong signals from mock APM."
    }
