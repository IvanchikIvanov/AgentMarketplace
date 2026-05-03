from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from marketplace_core.contracts.common import MessageEnvelope, MessageType, new_envelope
from marketplace_core.trust import sign_envelope, verify_envelope_signature

KeyResolver = Callable[..., str | None]
CapabilityHandler = Callable[[dict[str, Any], MessageEnvelope], dict[str, Any]]


@dataclass(frozen=True)
class SellerCapability:
    name: str
    handler: CapabilityHandler


class SellerRuntime:
    """Seller-side SDK helper for validating queries and returning signed replies."""

    def __init__(
        self,
        *,
        agent_id: str,
        signing_private_key_b64: str,
        signing_key_id: str,
        key_resolver: KeyResolver | None = None,
        require_signed_queries: bool = True,
    ) -> None:
        self.agent_id = agent_id
        self.signing_private_key_b64 = signing_private_key_b64
        self.signing_key_id = signing_key_id
        self.key_resolver = key_resolver
        self.require_signed_queries = require_signed_queries
        self._capabilities: dict[str, CapabilityHandler] = {}

    def register_capability(self, capability: SellerCapability) -> None:
        self._capabilities[capability.name] = capability.handler

    def handle_query(self, envelope: MessageEnvelope) -> MessageEnvelope:
        if envelope.message_type != MessageType.AGENT_QUERY:
            raise ValueError("seller_requires_agent_query")
        if envelope.receiver != self.agent_id:
            raise ValueError("seller_query_wrong_receiver")
        self._verify_query(envelope)
        capability = str(envelope.payload.get("capability") or "")
        handler = self._capabilities.get(capability)
        if handler is None:
            payload = {
                "reply": f"Capability {capability} is not registered.",
                "confidence": 0.0,
                "capability": capability,
                "quote_id": envelope.payload.get("quote_id"),
                "provenance": {"tools_used": [], "error": "capability_not_found"},
            }
        else:
            payload = dict(handler(dict(envelope.payload), envelope))
            payload.setdefault("capability", capability)
            payload.setdefault("quote_id", envelope.payload.get("quote_id"))
            payload.setdefault("provenance", {"tools_used": [capability]})
        reply = new_envelope(
            message_type=MessageType.AGENT_REPLY,
            sender=self.agent_id,
            receiver=envelope.sender,
            correlation_id=envelope.correlation_id,
            payload=payload,
        )
        return sign_envelope(
            reply,
            private_key_b64=self.signing_private_key_b64,
            pubkey_id=self.signing_key_id,
        )

    def _verify_query(self, envelope: MessageEnvelope) -> None:
        if not self.require_signed_queries:
            return
        key_id = str(envelope.metadata.get("pubkey_id") or "")
        if not key_id:
            raise ValueError("signed_query_required")
        if self.key_resolver is None:
            raise ValueError("query_key_resolver_required")
        try:
            public_key = self.key_resolver(envelope.sender, key_id, envelope.created_at)
        except TypeError:
            public_key = self.key_resolver(envelope.sender, key_id)
        if not public_key:
            raise ValueError("buyer_public_key_not_found")
        if not verify_envelope_signature(envelope, public_key_b64=public_key):
            raise ValueError("buyer_query_signature_invalid")
