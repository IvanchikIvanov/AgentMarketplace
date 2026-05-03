from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from marketplace_core.contracts.common import MessageEnvelope


@dataclass(frozen=True)
class InMemoryEnvelope:
    sender_peer_id: str
    destination_peer_id: str
    envelope: MessageEnvelope


class InMemoryTransportHub:
    def __init__(self) -> None:
        self._queues: dict[str, deque[InMemoryEnvelope]] = defaultdict(deque)

    def connect(self, peer_id: str) -> "InMemoryTransport":
        return InMemoryTransport(peer_id=peer_id, hub=self)

    def send(self, message: InMemoryEnvelope) -> None:
        self._queues[message.destination_peer_id].append(message)

    def recv_once(self, peer_id: str) -> tuple[str, MessageEnvelope] | None:
        queue = self._queues[peer_id]
        if not queue:
            return None
        message = queue.popleft()
        return message.sender_peer_id, message.envelope


class InMemoryTransport:
    def __init__(self, *, peer_id: str, hub: InMemoryTransportHub) -> None:
        self.peer_id = peer_id
        self.hub = hub

    def send_envelope(self, destination_peer_id: str, envelope: MessageEnvelope) -> None:
        self.hub.send(
            InMemoryEnvelope(
                sender_peer_id=self.peer_id,
                destination_peer_id=destination_peer_id,
                envelope=envelope,
            )
        )

    def recv_once(self) -> tuple[str, MessageEnvelope] | None:
        return self.hub.recv_once(self.peer_id)

