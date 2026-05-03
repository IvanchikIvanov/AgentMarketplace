from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .registry_client import RegistryClient
from ..contracts.common import MessageEnvelope, MessageType, new_envelope
from ..contracts.marketplace_flow import MarketplaceFlowState
from ..trust import sign_envelope, verify_envelope_signature

KeyResolver = Callable[..., str | None]


class BuyerTransport(Protocol):
    def send_envelope(self, destination_peer_id: str, envelope: MessageEnvelope) -> None:
        ...

    def recv_once(self) -> tuple[str, MessageEnvelope] | None:
        ...


@dataclass(frozen=True)
class MarketplaceProvider:
    agent_id: str
    owner_id: str
    axl_peer_id: str
    pricing_mode: str
    capability: str
    card: dict[str, Any]


@dataclass(frozen=True)
class PaidQuery:
    provider: MarketplaceProvider
    quote: dict[str, Any]
    envelope: MessageEnvelope


class MarketplaceCoordinator:
    """Buyer-side helper for discover -> quote -> signed query -> usage."""

    def __init__(
        self,
        *,
        registry: RegistryClient,
        transport: BuyerTransport | None = None,
        axl: BuyerTransport | None = None,
        signing_private_key_b64: str | None = None,
        signing_key_id: str | None = None,
        require_signed_paid_queries: bool = True,
        key_resolver: KeyResolver | None = None,
        require_signed_replies_for_usage: bool = True,
    ) -> None:
        if require_signed_paid_queries and not signing_private_key_b64:
            raise ValueError("signing_private_key_b64_required_for_signed_paid_queries")
        self.registry = registry
        self.transport = transport or axl
        if self.transport is None:
            raise ValueError("buyer_transport_required")
        self.signing_private_key_b64 = signing_private_key_b64
        self.signing_key_id = signing_key_id
        self.require_signed_paid_queries = require_signed_paid_queries
        self.key_resolver = key_resolver
        self.require_signed_replies_for_usage = require_signed_replies_for_usage
        self._pending_messages: list[tuple[str, MessageEnvelope]] = []

    def discover_provider(
        self,
        *,
        capability: str,
        topics: list[str] | None = None,
        pricing_modes: list[str] | None = None,
        access_policies: list[str] | None = None,
        min_reputation: float | None = None,
        source_agent_id: str | None = None,
    ) -> MarketplaceProvider | None:
        cards = self.registry.list_agents(
            topics=topics,
            capabilities=[capability],
            pricing_modes=pricing_modes,
            access_policies=access_policies,
            min_reputation=min_reputation,
            source_agent_id=source_agent_id,
        )
        for card in cards:
            endpoints = card.get("transport_endpoints")
            if not endpoints:
                full = self.registry.get_agent(str(card.get("agent_id")))
                endpoints = [] if full is None else full.get("transport_endpoints", [])
                card = full or card
            active = [ep for ep in endpoints if ep.get("active", 1)]
            if not active:
                continue
            active.sort(key=lambda ep: int(ep.get("priority", 100)))
            return MarketplaceProvider(
                agent_id=str(card["agent_id"]),
                owner_id=str(card.get("owner_id", "")),
                axl_peer_id=str(active[0]["axl_peer_id"]),
                pricing_mode=str(card.get("pricing_mode", "free")),
                capability=capability,
                card=card,
            )
        return None

    def quote_accept_and_send_query(
        self,
        *,
        buyer_agent_id: str,
        buyer_owner_id: str,
        provider: MarketplaceProvider,
        query: str,
        context: dict[str, Any],
        units: float = 1.0,
        ttl_sec: int = 300,
        correlation_id: str | None = None,
    ) -> PaidQuery:
        quote = self.registry.create_quote(
            seller_agent_id=provider.agent_id,
            payload={
                "buyer_agent_id": buyer_agent_id,
                "capability": provider.capability,
                "units": units,
                "ttl_sec": ttl_sec,
                "request_payload": {"query": query, "context": context},
            },
        )
        accepted = self.registry.accept_quote(str(quote["quote_id"]), buyer_agent_id=buyer_agent_id)
        env = new_envelope(
            message_type=MessageType.AGENT_QUERY,
            sender=buyer_agent_id,
            receiver=provider.agent_id,
            correlation_id=correlation_id,
            payload={
                "query": query,
                "capability": provider.capability,
                "context": context,
                "quote_id": accepted["quote_id"],
                "request_id": accepted["quote_id"],
            },
            metadata={
                "owner_id": buyer_owner_id,
                "agent_id": buyer_agent_id,
                "quote_id": accepted["quote_id"],
                "seller_agent_id": provider.agent_id,
                "seller_owner_id": provider.owner_id,
                "capability": provider.capability,
                "flow_state": MarketplaceFlowState.QUERY_SENT,
                "marketplace_ts": int(time.time()),
            },
        )
        signed = self._sign_if_configured(env)
        self.transport.send_envelope(provider.axl_peer_id, signed)
        return PaidQuery(provider=provider, quote=accepted, envelope=signed)

    def wait_for_reply_and_record_usage(
        self,
        *,
        paid_query: PaidQuery,
        buyer_agent_id: str,
        timeout_sec: float = 30.0,
        poll_sleep_sec: float = 0.2,
    ) -> dict[str, Any]:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            rec = self._take_pending_match(paid_query)
            if rec is None:
                rec = self.transport.recv_once()
            if rec is None:
                time.sleep(poll_sleep_sec)
                continue
            _sender_peer_id, reply = rec
            if not self._matches_paid_reply(paid_query, reply):
                self._pending_messages.append(rec)
                continue
            return self.record_usage_from_reply(
                buyer_agent_id=buyer_agent_id,
                seller_agent_id=paid_query.provider.agent_id,
                capability=paid_query.provider.capability,
                reply=reply,
                quote_id=str(paid_query.quote["quote_id"]),
            )
        raise TimeoutError("marketplace_reply_timeout")

    def record_usage_from_reply(
        self,
        *,
        buyer_agent_id: str,
        seller_agent_id: str,
        capability: str,
        reply: MessageEnvelope,
        quote_id: str | None = None,
        status: str = "completed",
    ) -> dict[str, Any]:
        if reply.message_type != MessageType.AGENT_REPLY:
            raise ValueError("usage_requires_agent_reply")
        self._verify_reply_for_usage(reply=reply, seller_agent_id=seller_agent_id)
        resolved_quote_id = quote_id or str(reply.payload.get("quote_id") or reply.metadata.get("quote_id") or "")
        return self.registry.record_usage_event(
            {
                "buyer_agent_id": buyer_agent_id,
                "seller_agent_id": seller_agent_id,
                "capability": capability,
                "message_type": str(reply.message_type),
                "units": 1.0,
                "status": status,
                "quote_id": resolved_quote_id or None,
                "request_id": str(reply.payload.get("request_id") or ""),
                "correlation_id": reply.correlation_id,
                "payload": {
                    "reply_message_id": reply.message_id,
                    "confidence": reply.payload.get("confidence"),
                    "provenance": reply.payload.get("provenance"),
                },
            }
        )

    def _sign_if_configured(self, envelope: MessageEnvelope) -> MessageEnvelope:
        if not self.signing_private_key_b64 or not self.signing_key_id:
            if self.require_signed_paid_queries:
                raise ValueError("signing_key_required_for_paid_query")
            return envelope
        return sign_envelope(
            envelope,
            private_key_b64=self.signing_private_key_b64,
            pubkey_id=self.signing_key_id,
        )

    def _take_pending_match(self, paid_query: PaidQuery) -> tuple[str, MessageEnvelope] | None:
        for idx, rec in enumerate(self._pending_messages):
            _sender_peer_id, reply = rec
            if self._matches_paid_reply(paid_query, reply):
                return self._pending_messages.pop(idx)
        return None

    @staticmethod
    def _matches_paid_reply(paid_query: PaidQuery, reply: MessageEnvelope) -> bool:
        return (
            reply.correlation_id == paid_query.envelope.correlation_id
            and reply.sender == paid_query.provider.agent_id
            and reply.message_type == MessageType.AGENT_REPLY
        )

    def _verify_reply_for_usage(self, *, reply: MessageEnvelope, seller_agent_id: str) -> None:
        if not self.require_signed_replies_for_usage:
            return
        key_id = str(reply.metadata.get("pubkey_id") or "")
        if not key_id:
            raise ValueError("signed_reply_required_for_usage")
        resolver = self.key_resolver
        if resolver:
            try:
                public_key = resolver(seller_agent_id, key_id, reply.created_at)
            except TypeError:
                public_key = resolver(seller_agent_id, key_id)
        else:
            public_key = self.registry.get_agent_public_key(agent_id=seller_agent_id, key_id=key_id)
        if not public_key:
            raise ValueError("seller_public_key_not_found")
        if not verify_envelope_signature(reply, public_key_b64=public_key):
            raise ValueError("seller_reply_signature_invalid")
