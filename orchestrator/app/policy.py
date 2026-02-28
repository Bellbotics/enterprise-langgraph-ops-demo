from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

ICN_RE = re.compile(r"\b\d{10}V\d{6}\b")
CLAIM_ID_RE = re.compile(r"\b\d{8,12}\b")

def redact_text(text: str) -> Tuple[str, int]:
    redactions = 0
    def _sub(pattern, repl, s):
        nonlocal redactions
        new_s, n = pattern.subn(repl, s)
        redactions += n
        return new_s
    text = _sub(ICN_RE, "[REDACTED_ICN]", text)
    # Claim IDs are trickier; for demo we redact generic long numbers.
    text = _sub(CLAIM_ID_RE, "[REDACTED_ID]", text)
    return text, redactions

def policy_gate(state: Dict[str, Any], policy_cfg: Dict[str, Any]) -> Dict[str, Any]:
    env = state.get("env", "dev")
    plan = state.get("plan", {}) or {}
    actions = plan.get("actions", []) or []

    blocks: List[str] = []
    approvals_required: List[str] = []

    # Env rules
    env_rules = (policy_cfg.get("env_rules") or {}).get(env, {})
    require_approval = bool(env_rules.get("require_approval", env != "dev"))
    max_risk = env_rules.get("max_risk", "high")

    risk_order = {"low": 0, "medium": 1, "high": 2}
    max_risk_num = risk_order.get(max_risk, 2)

    # PII redaction pass over common text fields
    redactions = 0
    if isinstance(state.get("symptom"), str):
        state["symptom"], r = redact_text(state["symptom"])
        redactions += r

    for sig_i, sig in enumerate(state.get("signals") or []):
        if isinstance(sig, str):
            new_sig, r = redact_text(sig)
            redactions += r
            (state["signals"])[sig_i] = new_sig

    # Validate actions
    for a in actions:
        risk = a.get("risk", "medium")
        if risk_order.get(risk, 1) > max_risk_num:
            blocks.append(f"action_risk_exceeds_env_max:{a.get('id','unknown')}")
        if require_approval or a.get("requires_approval", False):
            role = a.get("suggested_owner_role", "SRE_APPROVER")
            if role not in approvals_required:
                approvals_required.append(role)

    # Additional policy constraints (simple allow/deny list)
    deny_patterns = policy_cfg.get("deny_output_patterns") or []
    for pat in deny_patterns:
        if isinstance(pat, str) and pat and pat in (state.get("symptom") or ""):
            blocks.append(f"deny_pattern_matched:{pat}")

    allowed = len(blocks) == 0
    state["policy"] = {
        "allowed": allowed,
        "blocks": blocks,
        "redactions_applied": redactions,
        "approvals_required": approvals_required,
    }
    return state
