from __future__ import annotations

from typing import Protocol

from marketplace_core.contracts.common import MessageEnvelope


class EnvelopeTransport(Protocol):
    """Transport interface for signed marketplace envelopes.

    Implementations can use in-memory queues, HTTP callbacks, message buses,
    or any other data plane. Registry and SDK code depend only on this small
    interface.
    """

    def send_envelope(self, destination_peer_id: str, envelope: MessageEnvelope) -> None:
        ...

    def recv_once(self) -> tuple[str, MessageEnvelope] | None:
        ...
