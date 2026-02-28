# Enterprise Ops Copilot with Guardrails (LangGraph Demo)
> **Portable across enterprises** • **Kubernetes-ready** • **Auditable + approval-gated** • **Artifact-driven (PR/ticket/slack)**

This repo is a **working, end-to-end demo** showing how to use **LangGraph** to orchestrate incident/work-item workflows with **enterprise-grade guardrails**:
- **Human-in-the-loop approvals** for risky actions (CAB/ITIL/SOX-friendly)
- **Persistent, resumable runs** (audit trail, replay, time-travel)
- **Policy-as-code gates** (redaction, environment rules, risk scoring)
- **RBAC** (separation of duties)
- **Pluggable adapters** (Datadog/Kubernetes/DB/Ticketing/Git) with safe mock implementations
- **Metrics for the orchestrator itself** (latency, cost estimates, run outcomes)

It also includes a tiny **Spring Boot “sample service”** to simulate common production failure modes (timeouts, pool exhaustion, memory pressure), plus **Kubernetes manifests** and **docker-compose** for local runs.

---

## Executive summary (non-technical)

### What this is
A **governed automation engine** for incident response and operational workflows. Instead of a chatbot answering questions, it:
1. **Collects evidence** (metrics/logs/events) from enterprise systems
2. **Forms a diagnosis** with confidence
3. **Proposes a remediation plan**
4. **Stops for approval** before anything risky
5. Produces **auditable change artifacts** (PR patches, ticket payloads, Slack updates)

### Why enterprises adopt this pattern
Enterprises need automation that is:
- **Safe** (no “agent went rogue”)
- **Auditable** (who approved what, when, and why)
- **Integratable** (fits existing tools: Jira/ServiceNow, Git, Datadog, Kubernetes)
- **Operationalizable** (has metrics, runbooks, error handling)

LangGraph is a good fit because it provides a **state machine for LLM workflows**, with built-in **persistence** and **interrupt/resume**.

### Business benefits (what leaders care about)
- **MTTR reduction**: consistent triage + quicker decisioning
- **Fewer repeat incidents**: standardized playbooks + postmortems
- **Less operational toil**: automated evidence gathering + draft comms/tickets
- **Governance by design**: approvals + policy gates + RBAC
- **Lower risk**: actions are artifact-driven (PR/ticket) instead of directly mutating prod

### Where this maps to VA Lighthouse (and also any enterprise)
- “Light vs Heavy” routing (fast path vs resource-intensive path)
- Downstream dependency timeouts / pool exhaustion / memory spikes
- Kubernetes-based operations and platform governance
- Compliance constraints (redaction, no PII leakage, approval gates)

### Pros / Cons
**Pros**
- Strong governance and auditability
- Works with existing enterprise toolchain
- Portable: adapters are pluggable (mock → real)
- Reliable: resumable and inspectable execution

**Cons / Tradeoffs**
- Requires upfront design: state schema, policies, and playbooks
- Needs ongoing tuning (confidence thresholds, risk scoring)
- Integrations require security review (tokens, allowlists, egress)
- Not a replacement for SREs—best used as **decision support + artifact generator**

---

## What’s in this repo

### Services
1. **orchestrator/** (Python + FastAPI)
   - LangGraph workflow engine
   - Endpoints to run/resume/list runs
   - Policy gate, RBAC, artifact generation
   - Prometheus metrics endpoint

2. **spring-service/** (Java + Spring Boot)
   - Simulates common enterprise failure modes
   - Exposes health + metrics
   - Intended as a stand-in for any “enterprise microservice” (including Lighthouse-like services)

### Deploy options
- **docker-compose**: fastest local demo (recommended first)
- **Kubernetes manifests**: realistic deployment pattern (kind/minikube/EKS)

---

## Quickstart (docker-compose) — 5 minutes

### Prereqs
- Docker Desktop (or docker engine)
- (Optional) Python 3.11+ locally if you want to run without containers

### Start everything
```bash
docker compose up --build
```

This brings up:
- Orchestrator: http://localhost:8000
- Spring Service: http://localhost:8080
- Postgres: used for run persistence (audit trail)



### Persistence (real resume)
This version uses LangGraph checkpointing so `/resume` **loads the last saved state** for the `thread_id` and continues from there. By default docker-compose sets `DATABASE_URL` to Postgres for persistence.

### Run a demo workflow (HikariPool / DB saturation scenario)
```bash
curl -s -X POST http://localhost:8000/run \
  -H 'Content-Type: application/json' \
  -H 'X-Role: SRE' \
  -d '{
    "env":"staging",
    "service":"sample-spring-service",
    "symptom":"DB connection timeouts and thread starvation",
    "signals":["spike in 5xx","increased latency"],
    "constraints":["no PII in outputs","approval required for risky changes"],
    "scenario":"hikari_pool_exhaustion"
  }' | jq
```

You will usually get **approval_required** back with a `thread_id`.

### Approve and resume
```bash
curl -s -X POST http://localhost:8000/resume \
  -H 'Content-Type: application/json' \
  -H 'X-Role: SRE_APPROVER' \
  -d '{
    "thread_id":"<THREAD_ID_FROM_PREVIOUS_RESPONSE>",
    "decision":"approve"
  }' | jq
```

Artifacts are written under:
- `orchestrator/out/<thread_id>/`
  - `slack_update.md`
  - `ticket_payload.json`
  - `git_patch.diff`
  - `triage_report.json`

---

## Quickstart (Kubernetes) — realistic enterprise demo

### Prereqs
- `kubectl`
- a cluster (kind/minikube/your enterprise k8s)
- optional: `kustomize`

### Deploy
```bash
kubectl apply -f k8s/
```

Port-forward:
```bash
kubectl port-forward deploy/orchestrator 8000:8000
kubectl port-forward deploy/sample-spring-service 8080:8080
```

Run the same curl commands as above.

---

## How the workflow works (technical)

### Core graph stages
1. **Intake & normalization**
   - Validates input, assigns `thread_id`, normalizes signals/constraints

2. **Evidence collection (parallel)**
   - K8s events (mock adapter)
   - “Datadog” metrics and recent errors (mock adapter)
   - DB symptoms (mock adapter)
   - Service self-metrics (calls spring-service `/actuator/metrics` if enabled)

3. **Diagnosis**
   - Generates hypotheses + confidence
   - Produces “what to verify next” if confidence is low

4. **Plan generation**
   - Produces ranked actions with risk score and blast radius
   - Generates change artifacts (patch/ticket/slack)

5. **Policy gate**
   - Redacts sensitive info
   - Enforces environment rules (prod always requires approvals; staging can be 1-approver; dev can auto-complete)
   - Requires escalation when risk/confidence thresholds are violated

6. **Approval interrupt + resume**
   - If the plan contains risky actions, the graph **interrupts**
   - Approver resumes the run with approve/deny/edit

7. **Finalize**
   - Writes final artifacts and a summary
   - Emits metrics about the run

### Why LangGraph here
LangGraph gives you:
- **Stateful, typed execution** (not ad-hoc agent loops)
- **Checkpointing** (auditability, restart, replay)
- **Interrupt/resume** (human approval gates)
- **Modularity** (subgraphs for reusable playbooks)

---

## Security & compliance posture (portable enterprise defaults)

This demo is intentionally designed to be “security review friendly”:

- **Artifact-driven changes**: generates diffs/tickets, doesn’t apply changes to prod
- **RBAC**: actions require roles; approvals require separate role
- **Policy gate**: redacts likely identifiers; blocks unsafe output patterns
- **Allowlist mindset**: adapter interfaces are explicit; real integrations are opt-in
- **Audit trail**: Postgres checkpointer stores every step’s state transitions

> Replace mock adapters with real integrations only after your organization’s standard security review (tokens, allowlists, logging, data handling).

---

## Metrics to track (for leadership + operations)

### Business metrics
- **Mean time to acknowledge (MTTA)** improvement
- **Mean time to resolution (MTTR)** improvement
- **# of incidents with standardized triage** (coverage)
- **% of incidents with reusable artifacts** (tickets, PRs, comms)

### Operational metrics (orchestrator)
Exposed at `GET /metrics` (Prometheus format):
- `ops_runs_total{status=...}`
- `ops_run_duration_seconds_bucket`
- `ops_approvals_total{decision=...}`
- `ops_artifacts_written_total{type=...}`
- `ops_policy_blocks_total{reason=...}`

### Quality metrics
- **Recommendation acceptance rate** (approved vs denied)
- **False positive rate** (bad diagnoses)
- **Confidence calibration** (how often “high confidence” is correct)
- **Change failure rate** (if you later wire to actual deployments)

---

## Extending to real enterprise systems
Adapters are intentionally thin. Common upgrades:

- **Datadog**: query metrics/traces/logs using official APIs
- **Kubernetes**: read events, pod restarts, HPA signals
- **Ticketing**: create Jira/ServiceNow tickets (or just payload generation)
- **Git**: open PRs (or just diffs) against config repos (Helm/Kustomize)
- **SSO**: replace header RBAC with JWT/OIDC
- **Secrets**: use Vault/KMS/Parameter Store for tokens

---

## FAQ

### Is this safe to run in production?
As-is, this demo **does not apply changes**—it generates artifacts. That’s intentional.
To make it production-grade you still need: secrets mgmt, allowlists, logging policies, integration hardening, and testing.

### Why not just use a single agent loop?
Because enterprises need:
- deterministic governance points
- auditable state history
- safe failure/retry behavior
- modular runbooks
LangGraph’s model fits those needs better than free-form loops.

---

## Troubleshooting

### Orchestrator says “approval_required” every time
That’s expected for staging/prod. To allow auto-complete:
- Use `env=dev` or adjust `policies/policy.yaml`.

### Postgres isn’t available
docker-compose starts Postgres. If you run locally without it, the orchestrator will fall back to **SQLite** persistence.

### I want to see the artifacts
They are written to:
- `orchestrator/out/<thread_id>/`

---

## Demo scripts (recommended flow)
1. Run “hikari_pool_exhaustion” → approval → artifacts generated
2. Run “pdf_heavy_memory” → routes to heavy lane playbook → approval → artifacts generated
3. Show `/state/<thread_id>` (now includes `persisted_state`) to demonstrate audit trail
4. Show `/metrics` to demonstrate operational readiness
5. For execs: show sample Slack update + ticket payload + git patch diff

---

## License
MIT (demo-friendly)



### Approver edits (edit plan instead of approve/deny)
Example: remove a high-risk action and downgrade another action's risk.
```bash
curl -s -X POST http://localhost:8000/resume \
  -H 'Content-Type: application/json' \
  -H 'X-Role: ARCH_APPROVER' \
  -d '{
    "thread_id":"<THREAD_ID>",
    "decision":"edit",
    "edits":{
      "remove_action_ids":["move_reporting_async"],
      "set_action_fields":{
        "tune_hikari": {"risk":"low", "requires_approval": false}
      },
      "append_plan_notes":"Proceed only after verifying top DB waits and long-running queries."
    }
  }'
```
