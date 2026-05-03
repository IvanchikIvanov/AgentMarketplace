from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.contracts.common import MessageEnvelope, MessageType, new_envelope
from src.marketplace import MarketplaceCoordinator
from src.registry_hub.client import RegistryClient
from src.trust import generate_signing_keypair, sign_envelope


class MockAxl:
    def __init__(self) -> None:
        self.queues: dict[str, list[MessageEnvelope]] = {}

    def send_envelope(self, destination_peer_id: str, envelope: MessageEnvelope) -> None:
        self.queues.setdefault(destination_peer_id, []).append(envelope)
        print(f"  [axl] -> {destination_peer_id}: {envelope.message_type} corr={envelope.correlation_id}")

    def take(self, peer_id: str) -> MessageEnvelope | None:
        if not self.queues.get(peer_id):
            return None
        return self.queues[peer_id].pop(0)


def banner(msg: str) -> None:
    print(f"\n=== {msg} ===")


def main() -> None:
    REGISTRY = "http://127.0.0.1:8080"
    admin = RegistryClient(REGISTRY, write_token="admin_demo_token")

    banner("1. Bootstrap owners (admin)")
    admin._post("/owners", json={"owner_id": "owner-polymarket", "display_name": "Polymarket Owner"})
    admin._post("/owners", json={"owner_id": "owner-trader", "display_name": "Trader Owner"})
    print("  owners: owner-polymarket, owner-trader")

    banner("2. Generate signing keys")
    buyer_kp = generate_signing_keypair(key_id="buyer-key")
    seller_kp = generate_signing_keypair(key_id="seller-key")
    print(f"  buyer key_id={buyer_kp.key_id} pubkey_b64[:16]={buyer_kp.public_key_b64[:16]}...")
    print(f"  seller key_id={seller_kp.key_id} pubkey_b64[:16]={seller_kp.public_key_b64[:16]}...")

    banner("3. Register buyer agent-polymarket (free, public)")
    admin.upsert_agent({
        "owner_id": "owner-polymarket",
        "agent_id": "agent-polymarket",
        "display_name": "Polymarket Analyst Agent",
        "description": "Buys risk_review for BTC up/down decisions.",
        "status": "active",
        "visibility_mode": "public",
        "access_policy": "public",
        "pricing_mode": "free",
        "topics": ["polymarket", "btc"],
        "capabilities": ["market_analysis"],
        "primary_category": "analysis",
        "domains": ["prediction_markets"],
        "risk_level": "decision_support",
    })
    admin.upsert_key(
        agent_id="agent-polymarket",
        payload={"key_id": buyer_kp.key_id, "public_key": buyer_kp.public_key_b64, "status": "active"},
    )
    print("  buyer registered + signing key uploaded")

    banner("4. Register seller agent-trader (per_query risk_review, public)")
    admin.upsert_agent({
        "owner_id": "owner-trader",
        "agent_id": "agent-trader",
        "display_name": "Trader Risk Review Agent",
        "description": "Sells risk_review with veto-style policy analysis.",
        "status": "active",
        "visibility_mode": "public",
        "access_policy": "public",
        "pricing_mode": "per_query",
        "pricing_policy": {"currency": "USD", "capability_prices": {"risk_review": 0.25}},
        "topics": ["risk", "polymarket"],
        "capabilities": ["risk_review"],
        "primary_category": "analysis",
        "secondary_categories": ["finance", "security"],
        "service_types": ["risk_review", "decision_support"],
        "domains": ["trading", "prediction_markets"],
        "risk_level": "decision_support",
        "trust_summary": {"verified_owner": True},
    })
    admin.upsert_endpoint(
        agent_id="agent-trader",
        payload={"axl_peer_id": "peer-trader-local", "mode": "axl", "priority": 10, "active": True},
    )
    admin.upsert_key(
        agent_id="agent-trader",
        payload={"key_id": seller_kp.key_id, "public_key": seller_kp.public_key_b64, "status": "active"},
    )
    print("  seller registered + endpoint + signing key uploaded")

    banner("5. Buyer discovers provider via HTTP /agents (with agent token)")
    # NOTE: write_token is also passed because POST /agents/{id}/quote and
    # POST /usage/events are currently gated by the global write token
    # rather than by an agent-scoped policy. This is a known limitation of
    # the current auth model — see review notes on multi-tenant binding.
    buyer_client = RegistryClient(REGISTRY, write_token="admin_demo_token")
    axl = MockAxl()
    buyer_marketplace = MarketplaceCoordinator(
        registry=buyer_client,
        axl=axl,
        signing_private_key_b64=buyer_kp.private_key_b64,
        signing_key_id=buyer_kp.key_id,
        key_resolver=lambda agent_id, key_id, message_created_at=None: buyer_client.get_agent_public_key(
            agent_id=agent_id, key_id=key_id
        ),
    )
    provider = buyer_marketplace.discover_provider(
        capability="risk_review",
        topics=["risk"],
        access_policies=["public"],
        source_agent_id="agent-polymarket",
    )
    if provider is None:
        raise SystemExit("provider_not_found")
    print(f"  found: agent_id={provider.agent_id} owner={provider.owner_id}")
    print(f"  peer={provider.axl_peer_id} pricing={provider.pricing_mode} capability={provider.capability}")

    banner("6. Buyer: create quote, accept, sign + send AGENT_QUERY")
    paid = buyer_marketplace.quote_accept_and_send_query(
        buyer_agent_id="agent-polymarket",
        buyer_owner_id="owner-polymarket",
        provider=provider,
        query="Review BTC up/down martingale entry on 1h",
        context={
            "recommendation": {
                "entry_price": 0.52,
                "spread": 0.02,
                "confidence": 0.8,
                "liquidity": 12000,
                "fair_distance": 0.02,
                "recommendation": "enter",
                "side": "up",
            }
        },
    )
    print(f"  quote_id={paid.quote['quote_id']} status={paid.quote.get('status')}")
    print(f"  envelope message_id={paid.envelope.message_id}")
    print(f"  envelope signed by pubkey_id={paid.envelope.metadata.get('pubkey_id')}")

    banner("7. Seller picks up envelope, evaluates risk_review, signs reply")
    incoming = axl.take("peer-trader-local")
    if incoming is None:
        raise SystemExit("seller_did_not_receive")
    print(f"  seller received: type={incoming.message_type} from={incoming.sender}")
    print(f"  seller verifies buyer signature ...")
    from src.trust import verify_envelope_signature
    buyer_pub = buyer_client.get_agent_public_key(agent_id="agent-polymarket", key_id=buyer_kp.key_id)
    sig_ok = verify_envelope_signature(incoming, public_key_b64=buyer_pub or "")
    print(f"  buyer-signature-valid={sig_ok}")

    rec = (incoming.payload.get("context") or {}).get("recommendation") or {}
    spread = float(rec.get("spread") or 0.0)
    liquidity = float(rec.get("liquidity") or 0.0)
    decision = "approve" if (spread < 0.05 and liquidity > 5000) else "veto"
    reply_payload: dict[str, Any] = {
        "reply": f"risk_review={decision}",
        "decision": decision,
        "veto": decision == "veto",
        "confidence": 0.82,
        "quote_id": incoming.payload["quote_id"],
        "request_id": incoming.payload["request_id"],
        "provenance": {
            "tools_used": ["risk_review"],
            "source_ts": int(time.time()),
            "limitations": ["deterministic policy review", "does not place orders"],
        },
    }
    reply_env = sign_envelope(
        new_envelope(
            message_type=MessageType.AGENT_REPLY,
            sender="agent-trader",
            receiver="agent-polymarket",
            correlation_id=incoming.correlation_id,
            payload=reply_payload,
        ),
        private_key_b64=seller_kp.private_key_b64,
        pubkey_id=seller_kp.key_id,
    )
    print(f"  decision={decision} confidence=0.82")
    print(f"  reply signed by pubkey_id={reply_env.metadata.get('pubkey_id')}")

    banner("8. Buyer verifies seller signature & records usage")
    usage = buyer_marketplace.record_usage_from_reply(
        buyer_agent_id="agent-polymarket",
        seller_agent_id="agent-trader",
        capability="risk_review",
        reply=reply_env,
        quote_id=str(paid.quote["quote_id"]),
    )
    print(f"  usage_id={usage['usage_id']} status={usage['status']}")
    print(f"  buyer={usage['buyer_agent_id']} seller={usage['seller_agent_id']}")

    banner("9. Read-back: owner usage from registry")
    usage_rows = buyer_client.list_owner_usage("owner-polymarket")
    for u in usage_rows:
        print(
            f"  - capability={u.get('capability')} status={u.get('status')} "
            f"units={u.get('units')} quote_id={u.get('quote_id')}"
        )

    banner("10. Tampered-reply must be rejected")
    tampered = sign_envelope(
        new_envelope(
            message_type=MessageType.AGENT_REPLY,
            sender="agent-trader",
            receiver="agent-polymarket",
            correlation_id=incoming.correlation_id,
            payload={**reply_payload, "decision": "approve_TAMPERED"},
        ),
        private_key_b64=buyer_kp.private_key_b64,
        pubkey_id=buyer_kp.key_id,
    )
    try:
        buyer_marketplace.record_usage_from_reply(
            buyer_agent_id="agent-polymarket",
            seller_agent_id="agent-trader",
            capability="risk_review",
            reply=tampered,
            quote_id=str(paid.quote["quote_id"]),
        )
        print("  ERROR: tampered reply was accepted")
    except ValueError as exc:
        print(f"  rejected as expected: {exc}")

    print("\n=== live_marketplace_demo_ok ===")


if __name__ == "__main__":
    main()
