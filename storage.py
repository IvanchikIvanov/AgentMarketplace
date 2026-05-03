"""Backward-compatible import path for registry persistence.

New code should import from `marketplace_core.registry.storage`.
"""

from marketplace_core.registry.storage import MarketplaceStorage, Storage

__all__ = ["MarketplaceStorage", "Storage"]

