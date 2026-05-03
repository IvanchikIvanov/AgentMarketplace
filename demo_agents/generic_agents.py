from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from marketplace_core.contracts.common import MessageEnvelope
from marketplace_core.sdk.seller import SellerCapability, SellerRuntime


@dataclass(frozen=True)
class DemoAgentProfile:
    owner_id: str
    agent_id: str
    display_name: str
    description: str
    primary_category: str
    secondary_categories: list[str]
    service_types: list[str]
    domains: list[str]
    topics: list[str]
    capabilities: list[str]
    pricing_mode: str
    pricing_policy: dict[str, Any]
    risk_level: str = "informational"
    axl_peer_id: str = ""

    def registry_payload(self) -> dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "description": self.description,
            "status": "active",
            "visibility_mode": "public",
            "access_policy": "public",
            "pricing_mode": self.pricing_mode,
            "pricing_policy": self.pricing_policy,
            "trust_summary": {"demo_agent": True, "verified_owner": True},
            "primary_category": self.primary_category,
            "secondary_categories": self.secondary_categories,
            "service_types": self.service_types,
            "domains": self.domains,
            "risk_level": self.risk_level,
            "metadata": {
                "topics": self.topics,
                "capabilities": self.capabilities,
                "message_types_supported": ["agent_query", "agent_reply"],
                "query_enabled": True,
                "demo": True,
            },
        }


DEMO_BUYER = DemoAgentProfile(
    owner_id="owner-demo-buyer",
    agent_id="demo-buyer",
    display_name="Demo Buyer Agent",
    description="Requests capabilities from providers and records usage after signed replies.",
    primary_category="automation",
    secondary_categories=["operations"],
    service_types=["orchestration"],
    domains=["demo"],
    topics=["demo", "workflow"],
    capabilities=["provider_discovery"],
    pricing_mode="free",
    pricing_policy={},
    axl_peer_id="peer-demo-buyer",
)

DEMO_DATA_AGENT = DemoAgentProfile(
    owner_id="owner-demo-data",
    agent_id="demo-data-agent",
    display_name="Demo Data Agent",
    description="Provides small normalized demo datasets to other agents.",
    primary_category="data",
    secondary_categories=["knowledge"],
    service_types=["data_feed", "data_enrichment"],
    domains=["demo", "examples"],
    topics=["data", "normalization"],
    capabilities=["demo_dataset"],
    pricing_mode="free",
    pricing_policy={},
    axl_peer_id="peer-demo-data",
)

DEMO_ANALYSIS_AGENT = DemoAgentProfile(
    owner_id="owner-demo-analysis",
    agent_id="demo-analysis-agent",
    display_name="Demo Analysis Agent",
    description="Turns a request payload into a concise analytical summary.",
    primary_category="analysis",
    secondary_categories=["research"],
    service_types=["analysis", "summary"],
    domains=["demo", "reports"],
    topics=["analysis", "summary"],
    capabilities=["summarize_payload"],
    pricing_mode="per_query",
    pricing_policy={"currency": "USD", "capability_prices": {"summarize_payload": 0.05}},
    risk_level="decision_support",
    axl_peer_id="peer-demo-analysis",
)

DEMO_PROFILES = [DEMO_BUYER, DEMO_DATA_AGENT, DEMO_ANALYSIS_AGENT]


class DemoAnalysisProvider:
    def __init__(self, *, profile: DemoAgentProfile, private_key_b64: str, key_id: str) -> None:
        self.profile = profile
        self.runtime = SellerRuntime(
            agent_id=profile.agent_id,
            signing_private_key_b64=private_key_b64,
            signing_key_id=key_id,
            require_signed_queries=False,
        )
        self.runtime.register_capability(
            SellerCapability(name="summarize_payload", handler=self._summarize_payload)
        )

    def handle_query(self, envelope: MessageEnvelope) -> MessageEnvelope:
        return self.runtime.handle_query(envelope)

    def _summarize_payload(self, payload: dict[str, Any], _envelope: MessageEnvelope) -> dict[str, Any]:
        context = dict(payload.get("context") or {})
        keys = ", ".join(sorted(str(k) for k in context.keys())) or "no context keys"
        return {
            "reply": f"Demo summary: received {keys}; recommended next step is human review of the generated report.",
            "confidence": 0.86,
            "provenance": {"tools_used": ["demo_summary"], "demo": True},
        }
