from __future__ import annotations

import json
from typing import Any

import httpx

from marketplace_core.contracts.common import MessageEnvelope


class HttpEnvelopeTransport:
    """Reference HTTP transport.

    This adapter is intentionally tiny: it posts envelopes to a peer endpoint.
    Receiving is application-specific and usually implemented as a webhook
    route that calls `MessageEnvelope.from_dict(...)`.
    """

    def __init__(self, *, peer_id: str, endpoint_url: str, timeout_sec: float = 10.0) -> None:
        self.peer_id = peer_id
        self.endpoint_url = endpoint_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def send_envelope(self, destination_peer_id: str, envelope: MessageEnvelope) -> None:
        with httpx.Client(timeout=self.timeout_sec) as client:
            response = client.post(
                self.endpoint_url,
                headers={
                    "Content-Type": "application/json",
                    "X-From-Peer-Id": self.peer_id,
                    "X-Destination-Peer-Id": destination_peer_id,
                },
                content=envelope.to_json().encode("utf-8"),
            )
            response.raise_for_status()

    def recv_once(self) -> tuple[str, MessageEnvelope] | None:
        raise NotImplementedError("http transport receives through the host application's webhook route")


def parse_http_envelope(*, body: bytes | str, headers: dict[str, Any]) -> tuple[str, MessageEnvelope]:
    raw = body.decode("utf-8") if isinstance(body, bytes) else body
    sender_peer_id = str(headers.get("X-From-Peer-Id") or headers.get("x-from-peer-id") or "")
    return sender_peer_id, MessageEnvelope.from_dict(json.loads(raw))
