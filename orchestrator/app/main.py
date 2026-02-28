from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.graph import build_graph, config_for_thread
from app.metrics import RUNS_TOTAL, APPROVALS_TOTAL, POLICY_BLOCKS_TOTAL, ARTIFACTS_WRITTEN_TOTAL, Timer

app = FastAPI(title="Enterprise Ops Copilot with Guardrails (LangGraph Demo)")
graph = build_graph()

OUT_DIR = Path(os.getenv("OUT_DIR", "/app/out"))
OUT_DIR.mkdir(parents=True, exist_ok=True)

RUN_INDEX: Dict[str, Dict[str, Any]] = {}

class RunRequest(BaseModel):
    env: str = Field(default="dev")
    service: str
    symptom: str
    scenario: str = Field(default="generic")
    severity: str = Field(default="medium")
    signals: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    # Optional: client-supplied ticket/run id (useful for mapping to Jira/ServiceNow)
    thread_id: Optional[str] = None

class ResumeRequest(BaseModel):
    thread_id: str
    decision: str  # approve|deny|edit
    edits: Optional[Dict[str, Any]] = None

def require_role(role_header: Optional[str], allowed: set[str]):
    if role_header is None:
        raise HTTPException(status_code=401, detail="Missing X-Role header")
    if role_header not in allowed:
        raise HTTPException(status_code=403, detail=f"Role {role_header} not allowed; required one of {sorted(allowed)}")

def write_artifacts(thread_id: str, artifacts: Dict[str, Any]) -> Dict[str, str]:
    out_path = OUT_DIR / thread_id
    out_path.mkdir(parents=True, exist_ok=True)

    written: Dict[str, str] = {}

    if "slack_update_md" in artifacts:
        p = out_path / "slack_update.md"
        p.write_text(artifacts["slack_update_md"], encoding="utf-8")
        ARTIFACTS_WRITTEN_TOTAL.labels("slack").inc()
        written["slack_update_md"] = str(p)

    if "ticket_payload_json" in artifacts:
        p = out_path / "ticket_payload.json"
        p.write_text(json.dumps(artifacts["ticket_payload_json"], indent=2), encoding="utf-8")
        ARTIFACTS_WRITTEN_TOTAL.labels("ticket").inc()
        written["ticket_payload_json"] = str(p)

    if "git_patch_diff" in artifacts:
        p = out_path / "git_patch.diff"
        p.write_text(artifacts["git_patch_diff"], encoding="utf-8")
        ARTIFACTS_WRITTEN_TOTAL.labels("git_patch").inc()
        written["git_patch_diff"] = str(p)

    if "triage_report_json" in artifacts:
        p = out_path / "triage_report.json"
        p.write_text(json.dumps(artifacts["triage_report_json"], indent=2), encoding="utf-8")
        ARTIFACTS_WRITTEN_TOTAL.labels("triage_report").inc()
        written["triage_report_json"] = str(p)

    return written

def _graph_get_state(thread_id: str) -> Optional[Dict[str, Any]]:
    cfg = config_for_thread(thread_id)
    # Compiled graphs typically expose get_state(). We call defensively.
    if hasattr(graph, "get_state"):
        try:
            s = graph.get_state(cfg)  # type: ignore[attr-defined]
            # LangGraph state object usually has .values
            if hasattr(s, "values"):
                return dict(s.values)  # type: ignore[attr-defined]
            # Or it might already be dict-like
            return dict(s)
        except Exception:
            return None
    return None

@app.post("/run")
def run(req: RunRequest, x_role: Optional[str] = Header(default=None, alias="X-Role")):
    require_role(x_role, {"SRE", "DEV", "OPS"})

    thread_id = req.thread_id or str(uuid.uuid4())
    cfg = config_for_thread(thread_id)

    with Timer():
        state = req.model_dump()
        state["thread_id"] = thread_id
        # Execute graph; if it needs approval, it will END with status=needs_approval
        result = graph.invoke(state, config=cfg)

    policy = result.get("policy", {}) or {}
    for reason in (policy.get("blocks") or []):
        POLICY_BLOCKS_TOTAL.labels(reason).inc()

    RUN_INDEX[thread_id] = {"status": result.get("status"), "service": req.service, "env": req.env, "scenario": req.scenario}

    status = result.get("status", "failed")
    if status == "needs_approval":
        RUNS_TOTAL.labels("needs_approval").inc()
        return {
            "thread_id": thread_id,
            "status": status,
            "approval_request": result.get("approval_request"),
            "policy": policy,
        }

    if status in ("blocked", "denied"):
        RUNS_TOTAL.labels(status).inc()
        return {
            "thread_id": thread_id,
            "status": status,
            "policy": policy,
            "errors": result.get("errors", []),
        }

    artifacts = result.get("artifacts", {}) or {}
    written = write_artifacts(thread_id, artifacts)
    RUNS_TOTAL.labels("completed").inc()
    return {
        "thread_id": thread_id,
        "status": "completed",
        "policy": policy,
        "artifacts_written": written,
        "summary": (artifacts.get("triage_report_json") or {}).get("diagnosis"),
    }

@app.post("/resume")
def resume(req: ResumeRequest, x_role: Optional[str] = Header(default=None, alias="X-Role")):
    require_role(x_role, {"SRE_APPROVER", "ARCH_APPROVER", "DBA_APPROVER"})

    decision = req.decision.lower().strip()
    if decision not in ("approve", "deny", "edit"):
        raise HTTPException(status_code=400, detail="decision must be approve|deny|edit")

    # Load last persisted state for this thread and continue from there.
    prior = _graph_get_state(req.thread_id)
    if prior is None:
        raise HTTPException(status_code=404, detail="No persisted state found for thread_id (did you run /run first?)")

    # Enforce separation-of-duties: approver role must match what policy requested for this run.
    required_roles = ((prior.get("policy") or {}).get("approvals_required") or [])
    if required_roles and x_role not in set(required_roles):
        raise HTTPException(status_code=403, detail=f"Role {x_role} cannot approve this run; required one of {required_roles}")

    prior["approval_decision"] = decision
    prior["approval_edits"] = req.edits

    if decision == "approve":
        APPROVALS_TOTAL.labels("approve").inc()
    elif decision == "deny":
        APPROVALS_TOTAL.labels("deny").inc()
    else:
        APPROVALS_TOTAL.labels("edit").inc()

    cfg = config_for_thread(req.thread_id)
    with Timer():
        result = graph.invoke(prior, config=cfg)

    status = result.get("status", "failed")
    RUN_INDEX[req.thread_id] = {"status": status}

    if status in ("denied", "blocked"):
        RUNS_TOTAL.labels(status).inc()
        return {"thread_id": req.thread_id, "status": status, "policy": result.get("policy")}

    artifacts = result.get("artifacts", {}) or {}
    written = write_artifacts(req.thread_id, artifacts)
    RUNS_TOTAL.labels("completed").inc()
    return {
        "thread_id": req.thread_id,
        "status": "completed",
        "artifacts_written": written,
        "summary": (artifacts.get("triage_report_json") or {}).get("diagnosis"),
    }

@app.get("/state/{thread_id}")
def get_state(thread_id: str, x_role: Optional[str] = Header(default=None, alias="X-Role")):
    require_role(x_role, {"SRE", "DEV", "OPS", "SRE_APPROVER", "ARCH_APPROVER", "DBA_APPROVER"})
    out_path = OUT_DIR / thread_id

    persisted = _graph_get_state(thread_id)
    return {
        "thread_id": thread_id,
        "index": RUN_INDEX.get(thread_id),
        "persisted_state": persisted,
        "artifact_dir": str(out_path) if out_path.exists() else None,
        "files": [p.name for p in out_path.iterdir()] if out_path.exists() else [],
    }

@app.get("/metrics")
def metrics():
    data = generate_latest()
    return PlainTextResponse(data.decode("utf-8"), media_type=CONTENT_TYPE_LATEST)

@app.get("/healthz")
def healthz():
    return {"ok": True}
