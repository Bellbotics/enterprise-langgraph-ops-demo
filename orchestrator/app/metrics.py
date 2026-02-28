from __future__ import annotations

import time
from prometheus_client import Counter, Histogram

RUNS_TOTAL = Counter("ops_runs_total", "Total runs", ["status"])
APPROVALS_TOTAL = Counter("ops_approvals_total", "Total approvals decisions", ["decision"])
POLICY_BLOCKS_TOTAL = Counter("ops_policy_blocks_total", "Total policy blocks", ["reason"])
ARTIFACTS_WRITTEN_TOTAL = Counter("ops_artifacts_written_total", "Total artifacts written", ["type"])
RUN_DURATION = Histogram("ops_run_duration_seconds", "Run duration seconds")

class Timer:
    def __enter__(self):
        self.start = time.time()
        return self
    def __exit__(self, exc_type, exc, tb):
        RUN_DURATION.observe(time.time() - self.start)
