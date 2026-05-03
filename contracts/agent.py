from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

try:
    from enum import StrEnum
except ImportError:  # Python < 3.11 compatibility
    class StrEnum(str, Enum):
        pass


class AgentVisibilityMode(StrEnum):
    PUBLIC = "public"
    APPROVED_ONLY = "approved_only"
    PRIVATE = "private"


class AgentStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    DEPRECATED = "deprecated"


@dataclass(frozen=True)
class TransportEndpoint:
    axl_peer_id: str
    mode: str = "axl"
    priority: int = 100
    region: str | None = None
    active: bool = True
    last_seen_at: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "axl_peer_id": self.axl_peer_id,
            "mode": self.mode,
            "priority": self.priority,
            "region": self.region,
            "active": self.active,
            "last_seen_at": self.last_seen_at,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "TransportEndpoint":
        return TransportEndpoint(
            axl_peer_id=str(data["axl_peer_id"]),
            mode=str(data.get("mode", "axl")),
            priority=int(data.get("priority", 100)),
            region=None if data.get("region") is None else str(data.get("region")),
            active=bool(data.get("active", True)),
            last_seen_at=None if data.get("last_seen_at") is None else int(data["last_seen_at"]),
        )


@dataclass(frozen=True)
class AgentIdentity:
    owner_id: str
    agent_id: str
    visibility_mode: AgentVisibilityMode = AgentVisibilityMode.PUBLIC

    def to_metadata(self) -> dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "agent_id": self.agent_id,
            "visibility_mode": str(self.visibility_mode),
        }

    @staticmethod
    def from_metadata(metadata: dict[str, Any]) -> "AgentIdentity":
        return AgentIdentity(
            owner_id=str(metadata.get("owner_id", "")),
            agent_id=str(metadata.get("agent_id", "")),
            visibility_mode=AgentVisibilityMode(str(metadata.get("visibility_mode", AgentVisibilityMode.PUBLIC))),
        )


@dataclass(frozen=True)
class AgentCard:
    agent_id: str
    owner_id: str
    display_name: str
    description: str
    topics: list[str]
    capabilities: list[str]
    message_types_supported: list[str]
    access_policy: str
    pricing_mode: str
    primary_category: str = ""
    secondary_categories: list[str] = field(default_factory=list)
    service_types: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    risk_level: str = "informational"
    transport_endpoints: list[TransportEndpoint] = field(default_factory=list)
    agent_card_url: str | None = None
    public_signing_key: str | None = None
    reputation_metrics: dict[str, Any] = field(default_factory=dict)
    status: AgentStatus = AgentStatus.DRAFT
    last_seen_at: int | None = None
    supported_protocol_versions: list[str] = field(default_factory=lambda: ["2"])
    supported_transport_modes: list[str] = field(default_factory=lambda: ["axl"])
    policy_summary: str | None = None
    rate_limits: dict[str, Any] = field(default_factory=dict)
    compliance_tags: list[str] = field(default_factory=list)
    pricing_policy: dict[str, Any] = field(default_factory=dict)
    capabilities_schema: dict[str, Any] = field(default_factory=dict)
    provenance_policy: dict[str, Any] = field(default_factory=dict)
    trust_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "owner_id": self.owner_id,
            "display_name": self.display_name,
            "description": self.description,
            "topics": self.topics,
            "capabilities": self.capabilities,
            "message_types_supported": self.message_types_supported,
            "access_policy": self.access_policy,
            "pricing_mode": self.pricing_mode,
            "primary_category": self.primary_category,
            "secondary_categories": self.secondary_categories,
            "service_types": self.service_types,
            "domains": self.domains,
            "risk_level": self.risk_level,
            "transport_endpoints": [ep.to_dict() for ep in self.transport_endpoints],
            "agent_card_url": self.agent_card_url,
            "public_signing_key": self.public_signing_key,
            "reputation_metrics": self.reputation_metrics,
            "status": str(self.status),
            "last_seen_at": self.last_seen_at,
            "supported_protocol_versions": self.supported_protocol_versions,
            "supported_transport_modes": self.supported_transport_modes,
            "policy_summary": self.policy_summary,
            "rate_limits": self.rate_limits,
            "compliance_tags": self.compliance_tags,
            "pricing_policy": self.pricing_policy,
            "capabilities_schema": self.capabilities_schema,
            "provenance_policy": self.provenance_policy,
            "trust_summary": self.trust_summary,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AgentCard":
        return AgentCard(
            agent_id=str(data["agent_id"]),
            owner_id=str(data["owner_id"]),
            display_name=str(data.get("display_name", "")),
            description=str(data.get("description", "")),
            topics=[str(v) for v in data.get("topics", [])],
            capabilities=[str(v) for v in data.get("capabilities", [])],
            message_types_supported=[str(v) for v in data.get("message_types_supported", [])],
            access_policy=str(data.get("access_policy", "public")),
            pricing_mode=str(data.get("pricing_mode", "free")),
            primary_category=str(data.get("primary_category", "")),
            secondary_categories=[str(v) for v in data.get("secondary_categories", [])],
            service_types=[str(v) for v in data.get("service_types", [])],
            domains=[str(v) for v in data.get("domains", [])],
            risk_level=str(data.get("risk_level", "informational")),
            transport_endpoints=[
                TransportEndpoint.from_dict(ep)
                for ep in data.get("transport_endpoints", [])
                if isinstance(ep, dict)
            ],
            agent_card_url=None if data.get("agent_card_url") is None else str(data["agent_card_url"]),
            public_signing_key=None
            if data.get("public_signing_key") is None
            else str(data["public_signing_key"]),
            reputation_metrics=dict(data.get("reputation_metrics", {})),
            status=AgentStatus(str(data.get("status", AgentStatus.DRAFT))),
            last_seen_at=None if data.get("last_seen_at") is None else int(data["last_seen_at"]),
            supported_protocol_versions=[str(v) for v in data.get("supported_protocol_versions", ["2"])],
            supported_transport_modes=[str(v) for v in data.get("supported_transport_modes", ["axl"])],
            policy_summary=None if data.get("policy_summary") is None else str(data["policy_summary"]),
            rate_limits=dict(data.get("rate_limits", {})),
            compliance_tags=[str(v) for v in data.get("compliance_tags", [])],
            pricing_policy=dict(data.get("pricing_policy", {})),
            capabilities_schema=dict(data.get("capabilities_schema", {})),
            provenance_policy=dict(data.get("provenance_policy", {})),
            trust_summary=dict(data.get("trust_summary", {})),
        )
