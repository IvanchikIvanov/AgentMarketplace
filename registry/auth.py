from __future__ import annotations

import json
import os
import secrets

from fastapi import Header, HTTPException


def registry_write_token() -> str:
    return os.environ.get("REGISTRY_WRITE_TOKEN", "").strip()


def bearer_token(authorization: str | None) -> str:
    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        return ""
    return authorization[len(prefix) :].strip()


def registry_agent_tokens() -> dict[str, str]:
    raw = os.environ.get("REGISTRY_AGENT_TOKENS", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {}
        for pair in raw.split(","):
            if ":" not in pair:
                continue
            agent_id, token = pair.split(":", 1)
            parsed[agent_id.strip()] = token.strip()
    if not isinstance(parsed, dict):
        return {}
    return {str(agent_id): str(token) for agent_id, token in parsed.items() if str(agent_id) and str(token)}


def require_registry_write_auth(authorization: str | None = Header(default=None)) -> None:
    expected = registry_write_token()
    supplied = bearer_token(authorization)
    if not expected:
        raise HTTPException(status_code=503, detail="registry_write_token_not_configured")
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="registry_write_auth_required")


def require_source_agent_auth(
    source_agent_id: str | None = None,
    authorization: str | None = Header(default=None),
) -> None:
    if not source_agent_id:
        return
    expected = registry_agent_tokens().get(source_agent_id)
    supplied = bearer_token(authorization)
    if not expected:
        raise HTTPException(status_code=403, detail="source_agent_auth_not_configured")
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="source_agent_auth_required")
