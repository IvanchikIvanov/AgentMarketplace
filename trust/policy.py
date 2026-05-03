from __future__ import annotations

from dataclasses import dataclass

from ..contracts.agent import AgentVisibilityMode


@dataclass(frozen=True)
class AccessPolicyDecision:
    allow: bool
    reason: str


def evaluate_access_policy(
    *,
    visibility_mode: str,
    source_agent_id: str,
    target_agent_id: str,
    approved_pairs: set[tuple[str, str]] | None = None,
) -> AccessPolicyDecision:
    mode = AgentVisibilityMode(visibility_mode)
    if mode == AgentVisibilityMode.PUBLIC:
        return AccessPolicyDecision(True, "public")
    if source_agent_id == target_agent_id:
        return AccessPolicyDecision(True, "self")
    approved = approved_pairs or set()
    if mode == AgentVisibilityMode.APPROVED_ONLY:
        if (source_agent_id, target_agent_id) in approved or (target_agent_id, source_agent_id) in approved:
            return AccessPolicyDecision(True, "approved_peer")
        return AccessPolicyDecision(False, "not_approved")
    return AccessPolicyDecision(False, "private")
