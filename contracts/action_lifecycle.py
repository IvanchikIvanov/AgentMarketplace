from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ActionLifecyclePolicy:
    require_confirmation: bool = True
    require_signed_request: bool = True
    allow_live_execution: bool = False


@dataclass(frozen=True)
class ActionRequestPayload:
    action_type: str
    target_venue: str
    instrument_id: str
    side: str
    max_notional_usd: float
    limit_price: float | None
    dry_run: bool
    rationale: str
    risk_review_id: str | None = None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ActionRequestPayload":
        return ActionRequestPayload(
            action_type=str(data.get("action_type", "")),
            target_venue=str(data.get("target_venue", "")),
            instrument_id=str(data.get("instrument_id", "")),
            side=str(data.get("side", "")),
            max_notional_usd=float(data.get("max_notional_usd", 0.0) or 0.0),
            limit_price=None if data.get("limit_price") is None else float(data["limit_price"]),
            dry_run=bool(data.get("dry_run", True)),
            rationale=str(data.get("rationale", "")),
            risk_review_id=None if data.get("risk_review_id") is None else str(data["risk_review_id"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "target_venue": self.target_venue,
            "instrument_id": self.instrument_id,
            "side": self.side,
            "max_notional_usd": self.max_notional_usd,
            "limit_price": self.limit_price,
            "dry_run": self.dry_run,
            "rationale": self.rationale,
            "risk_review_id": self.risk_review_id,
        }
