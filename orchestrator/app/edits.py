from __future__ import annotations

from typing import Any, Dict, List, Optional

def apply_approval_edits(state: Dict[str, Any]) -> Dict[str, Any]:
    """Apply approver edits to the plan/actions.

    Supported edits payload (examples):
      {
        "remove_action_ids": ["move_reporting_async"],
        "set_action_fields": {
          "tune_hikari": {"risk":"low", "requires_approval": false}
        },
        "append_plan_notes": "Only do tuning after verifying top waits"
      }

    This keeps the demo portable and avoids coupling to any specific ITSM/Git tooling.
    """
    edits = state.get("approval_edits") or {}
    if not isinstance(edits, dict):
        return state

    plan = state.get("plan") or {}
    actions = list(plan.get("actions") or [])

    remove_ids = set(edits.get("remove_action_ids") or [])
    if remove_ids:
        actions = [a for a in actions if a.get("id") not in remove_ids]

    set_fields = edits.get("set_action_fields") or {}
    if isinstance(set_fields, dict) and set_fields:
        for a in actions:
            aid = a.get("id")
            if aid in set_fields and isinstance(set_fields[aid], dict):
                for k, v in set_fields[aid].items():
                    a[k] = v

    notes = edits.get("append_plan_notes")
    if isinstance(notes, str) and notes.strip():
        existing = plan.get("summary") or ""
        plan["summary"] = (existing + " | " + notes.strip()).strip(" |")

    plan["actions"] = actions
    state["plan"] = plan

    # Recompute approval_required based on remaining actions
    state["approval_required"] = any(a.get("requires_approval") for a in actions)
    return state
