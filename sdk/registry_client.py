from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import httpx


class RegistryClient:
    def __init__(self, base_url: str, *, timeout_sec: float = 8.0, write_token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.write_token = write_token if write_token is not None else os.environ.get("REGISTRY_WRITE_TOKEN", "")

    @staticmethod
    def _agent_tokens() -> dict[str, str]:
        raw = os.environ.get("REGISTRY_AGENT_TOKENS", "").strip()
        if not raw:
            return {}
        if raw.startswith("{"):
            import json

            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return {}
            if not isinstance(parsed, dict):
                return {}
            return {str(agent_id): str(token) for agent_id, token in parsed.items() if str(agent_id) and str(token)}
        out: dict[str, str] = {}
        for pair in raw.split(","):
            if ":" not in pair:
                continue
            agent_id, token = pair.split(":", 1)
            out[agent_id.strip()] = token.strip()
        return {agent_id: token for agent_id, token in out.items() if agent_id and token}

    def _auth_allowed_for_base_url(self) -> bool:
        parsed = urlparse(self.base_url)
        host = (parsed.hostname or "").lower()
        return parsed.scheme == "https" or host in {"127.0.0.1", "localhost", "::1"}

    def _auth_headers(
        self,
        *,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        source_agent_id: str | None = None,
    ) -> dict[str, str]:
        out = dict(headers or {})
        if "Authorization" in out or not self._auth_allowed_for_base_url():
            return out
        if source_agent_id:
            token = self._agent_tokens().get(source_agent_id, "")
            if token:
                out["Authorization"] = f"Bearer {token}"
            return out
        if method.upper() != "GET" and self.write_token:
            out["Authorization"] = f"Bearer {self.write_token}"
        return out

    def _get(self, path: str, **kwargs: Any) -> httpx.Response:
        source_agent_id = kwargs.pop("source_agent_id", None)
        kwargs["headers"] = self._auth_headers(
            method="GET",
            path=path,
            headers=kwargs.get("headers"),
            source_agent_id=source_agent_id,
        )
        with httpx.Client(timeout=self.timeout_sec) as c:
            resp = c.get(f"{self.base_url}{path}", **kwargs)
            resp.raise_for_status()
            return resp

    def _post(self, path: str, **kwargs: Any) -> httpx.Response:
        kwargs["headers"] = self._auth_headers(method="POST", path=path, headers=kwargs.get("headers"))
        with httpx.Client(timeout=self.timeout_sec) as c:
            resp = c.post(f"{self.base_url}{path}", **kwargs)
            resp.raise_for_status()
            return resp

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        try:
            return self._get(f"/agents/{agent_id}").json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    def get_directory_agent(self, agent_id: str) -> dict[str, Any] | None:
        try:
            return self._get(f"/directory/agents/{agent_id}").json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    def list_agents(
        self,
        *,
        status: str = "active",
        visibility_modes: list[str] | None = None,
        topics: list[str] | None = None,
        capabilities: list[str] | None = None,
        pricing_modes: list[str] | None = None,
        access_policies: list[str] | None = None,
        min_reputation: float | None = None,
        source_agent_id: str | None = None,
        primary_category: str | None = None,
        secondary_categories: list[str] | None = None,
        service_types: list[str] | None = None,
        domains: list[str] | None = None,
        risk_levels: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        modes = visibility_modes or ["public", "approved_only"]
        params = [("status", status)] + [("visibility_mode", mode) for mode in modes]
        params += [("topic", topic) for topic in topics or []]
        params += [("capability", capability) for capability in capabilities or []]
        params += [("pricing_mode", mode) for mode in pricing_modes or []]
        params += [("access_policy", policy) for policy in access_policies or []]
        if min_reputation is not None:
            params.append(("min_reputation", str(min_reputation)))
        if source_agent_id:
            params.append(("source_agent_id", source_agent_id))
        if primary_category:
            params.append(("primary_category", primary_category))
        params += [("secondary_category", category) for category in secondary_categories or []]
        params += [("service_type", service_type) for service_type in service_types or []]
        params += [("domain", domain) for domain in domains or []]
        params += [("risk_level", risk_level) for risk_level in risk_levels or []]
        data = self._get("/agents", params=params, source_agent_id=source_agent_id).json()
        return list(data.get("agents", []))

    def list_directory_agents(
        self,
        *,
        status: str = "active",
        visibility_modes: list[str] | None = None,
        topics: list[str] | None = None,
        capabilities: list[str] | None = None,
        pricing_modes: list[str] | None = None,
        access_policies: list[str] | None = None,
        min_reputation: float | None = None,
        source_agent_id: str | None = None,
        primary_category: str | None = None,
        secondary_categories: list[str] | None = None,
        service_types: list[str] | None = None,
        domains: list[str] | None = None,
        risk_levels: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        modes = visibility_modes or ["public", "approved_only"]
        params = [("status", status)] + [("visibility_mode", mode) for mode in modes]
        params += [("topic", topic) for topic in topics or []]
        params += [("capability", capability) for capability in capabilities or []]
        params += [("pricing_mode", mode) for mode in pricing_modes or []]
        params += [("access_policy", policy) for policy in access_policies or []]
        if min_reputation is not None:
            params.append(("min_reputation", str(min_reputation)))
        if source_agent_id:
            params.append(("source_agent_id", source_agent_id))
        if primary_category:
            params.append(("primary_category", primary_category))
        params += [("secondary_category", category) for category in secondary_categories or []]
        params += [("service_type", service_type) for service_type in service_types or []]
        params += [("domain", domain) for domain in domains or []]
        params += [("risk_level", risk_level) for risk_level in risk_levels or []]
        data = self._get("/directory/agents", params=params, source_agent_id=source_agent_id).json()
        return list(data.get("agents", []))

    def list_directory_categories(self) -> list[dict[str, Any]]:
        data = self._get("/directory/categories").json()
        return list(data.get("categories", []))

    def search_directory_agents(
        self,
        *,
        query: str,
        visibility_modes: list[str] | None = None,
        source_agent_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        modes = visibility_modes or ["public", "approved_only"]
        params = [("q", query), ("limit", str(limit))] + [("visibility_mode", mode) for mode in modes]
        if source_agent_id:
            params.append(("source_agent_id", source_agent_id))
        data = self._get("/directory/search", params=params, source_agent_id=source_agent_id).json()
        return list(data.get("agents", []))

    def upsert_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/agents", json=payload).json()

    def upsert_endpoint(self, *, agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post(f"/agents/{agent_id}/endpoints", json=payload).json()

    def heartbeat(self, *, agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post(f"/agents/{agent_id}/heartbeat", json=payload).json()

    def upsert_key(self, *, agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post(f"/agents/{agent_id}/keys", json=payload).json()

    def create_quote(self, *, seller_agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post(f"/agents/{seller_agent_id}/quote", json=payload).json()

    def accept_quote(self, quote_id: str, *, buyer_agent_id: str) -> dict[str, Any]:
        return self._post(f"/quotes/{quote_id}/accept", json={"buyer_agent_id": buyer_agent_id}).json()

    def record_usage_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/usage/events", json=payload).json()

    def list_owner_usage(self, owner_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        data = self._get(f"/owners/{owner_id}/usage", params={"limit": limit}).json()
        return list(data.get("usage", []))

    def get_agent_public_key(self, *, agent_id: str, key_id: str) -> str | None:
        data = self._get(f"/agents/{agent_id}/keys", params={"key_id": key_id}).json()
        keys = list(data.get("keys", []))
        if not keys:
            return None
        return str(keys[0].get("public_key") or "")
