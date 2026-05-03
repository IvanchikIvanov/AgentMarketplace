from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

try:
    from enum import StrEnum
except ImportError:  # Python < 3.11 compatibility
    class StrEnum(str, Enum):
        pass

SCHEMA_VERSION = 2


class MessageType(StrEnum):
    # Legacy runtime flow (compatibility)
    SIGNAL_REQUEST = "signal_request"
    SIGNAL_RESPONSE = "signal_response"
    EXECUTION_DECISION = "execution_decision"
    EXECUTION_REPORT = "execution_report"
    MARKET_SNAPSHOT_DELPHI = "market_snapshot_delphi"
    MARKET_SNAPSHOT_POLYMARKET = "market_snapshot_polymarket"
    ARB_RECOMMENDATION = "arb_recommendation"

    # Protocol v2: knowledge exchange family
    AGENT_QUERY = "agent_query"
    AGENT_REPLY = "agent_reply"
    AGENT_OBSERVATION = "agent_observation"
    AGENT_HYPOTHESIS = "agent_hypothesis"
    AGENT_RISK_ALERT = "agent_risk_alert"
    AGENT_CONFIDENCE_UPDATE = "agent_confidence_update"
    AGENT_SUMMARY = "agent_summary"
    AGENT_COUNTER_ANALYSIS = "agent_counter_analysis"

    # Protocol v2: action lifecycle family
    AGENT_INTENT = "agent_intent"
    AGENT_ACTION_REQUEST = "agent_action_request"
    AGENT_ACTION_RESULT = "agent_action_result"
    AGENT_EXECUTION_VETO = "agent_execution_veto"
    AGENT_REQUEST_CONFIRMATION = "agent_request_confirmation"

    # Protocol v2: commercial/query lifecycle family
    AGENT_QUOTE_REQUEST = "agent_quote_request"
    AGENT_QUOTE = "agent_quote"
    AGENT_USAGE_RECEIPT = "agent_usage_receipt"

    # Protocol v2: control/ops family
    AGENT_HEARTBEAT = "agent_heartbeat"
    AGENT_CAPABILITY_ANNOUNCE = "agent_capability_announce"
    AGENT_POLICY_UPDATE = "agent_policy_update"


KNOWLEDGE_MESSAGE_TYPES: set[str] = {
    MessageType.AGENT_QUERY,
    MessageType.AGENT_REPLY,
    MessageType.AGENT_OBSERVATION,
    MessageType.AGENT_HYPOTHESIS,
    MessageType.AGENT_RISK_ALERT,
    MessageType.AGENT_CONFIDENCE_UPDATE,
    MessageType.AGENT_SUMMARY,
    MessageType.AGENT_COUNTER_ANALYSIS,
}

ACTION_MESSAGE_TYPES: set[str] = {
    MessageType.AGENT_INTENT,
    MessageType.AGENT_ACTION_REQUEST,
    MessageType.AGENT_ACTION_RESULT,
    MessageType.AGENT_EXECUTION_VETO,
    MessageType.AGENT_REQUEST_CONFIRMATION,
}

COMMERCIAL_MESSAGE_TYPES: set[str] = {
    MessageType.AGENT_QUOTE_REQUEST,
    MessageType.AGENT_QUOTE,
    MessageType.AGENT_USAGE_RECEIPT,
}

CONTROL_MESSAGE_TYPES: set[str] = {
    MessageType.AGENT_HEARTBEAT,
    MessageType.AGENT_CAPABILITY_ANNOUNCE,
    MessageType.AGENT_POLICY_UPDATE,
}


@dataclass(frozen=True)
class MessageEnvelope:
    message_id: str
    correlation_id: str
    schema_version: int
    message_type: str
    sender: str
    receiver: str
    created_at: int
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
            "schema_version": self.schema_version,
            "message_type": self.message_type,
            "sender": self.sender,
            "receiver": self.receiver,
            "created_at": self.created_at,
            "payload": self.payload,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "MessageEnvelope":
        required = {
            "message_id",
            "correlation_id",
            "schema_version",
            "message_type",
            "sender",
            "receiver",
            "created_at",
            "payload",
        }
        missing = required.difference(data.keys())
        if missing:
            raise ValueError(f"Envelope missing keys: {sorted(missing)}")
        payload = data["payload"]
        if not isinstance(payload, dict):
            raise ValueError("Envelope payload must be object")
        metadata = data.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise ValueError("Envelope metadata must be object")
        return MessageEnvelope(
            message_id=str(data["message_id"]),
            correlation_id=str(data["correlation_id"]),
            schema_version=int(data["schema_version"]),
            message_type=str(data["message_type"]),
            sender=str(data["sender"]),
            receiver=str(data["receiver"]),
            created_at=int(data["created_at"]),
            payload=payload,
            metadata=metadata,
        )

    def message_family(self) -> str:
        mtype = str(self.message_type)
        if mtype in KNOWLEDGE_MESSAGE_TYPES:
            return "knowledge"
        if mtype in ACTION_MESSAGE_TYPES:
            return "action"
        if mtype in COMMERCIAL_MESSAGE_TYPES:
            return "commercial"
        if mtype in CONTROL_MESSAGE_TYPES:
            return "control"
        return "legacy"


def new_id() -> str:
    return uuid.uuid4().hex


def new_envelope(
    *,
    message_type: MessageType | str,
    sender: str,
    receiver: str,
    payload: dict[str, Any],
    correlation_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> MessageEnvelope:
    return MessageEnvelope(
        message_id=new_id(),
        correlation_id=correlation_id or new_id(),
        schema_version=SCHEMA_VERSION,
        message_type=str(message_type),
        sender=sender,
        receiver=receiver,
        created_at=int(time.time()),
        payload=payload,
        metadata=metadata or {},
    )
