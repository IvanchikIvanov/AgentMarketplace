from __future__ import annotations

from enum import Enum

try:
    from enum import StrEnum
except ImportError:  # Python < 3.11 compatibility
    class StrEnum(str, Enum):
        pass


class MarketplaceFlowState(StrEnum):
    DISCOVERED = "discovered"
    QUOTE_REQUESTED = "quote_requested"
    QUOTE_ACCEPTED = "quote_accepted"
    QUERY_SENT = "query_sent"
    REPLY_RECEIVED = "reply_received"
    USAGE_RECORDED = "usage_recorded"
    FAILED = "failed"


ALLOWED_TRANSITIONS: dict[MarketplaceFlowState, set[MarketplaceFlowState]] = {
    MarketplaceFlowState.DISCOVERED: {MarketplaceFlowState.QUOTE_REQUESTED},
    MarketplaceFlowState.QUOTE_REQUESTED: {MarketplaceFlowState.QUOTE_ACCEPTED, MarketplaceFlowState.FAILED},
    MarketplaceFlowState.QUOTE_ACCEPTED: {MarketplaceFlowState.QUERY_SENT, MarketplaceFlowState.FAILED},
    MarketplaceFlowState.QUERY_SENT: {MarketplaceFlowState.REPLY_RECEIVED, MarketplaceFlowState.FAILED},
    MarketplaceFlowState.REPLY_RECEIVED: {MarketplaceFlowState.USAGE_RECORDED, MarketplaceFlowState.FAILED},
}


def assert_transition(current: MarketplaceFlowState, next_state: MarketplaceFlowState) -> None:
    if next_state not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"invalid_marketplace_transition:{current}->{next_state}")
