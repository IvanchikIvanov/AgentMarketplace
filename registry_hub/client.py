"""Backward-compatible import path for the Registry SDK client.

New code should import from `marketplace_core.sdk.registry_client`.
"""

from marketplace_core.sdk.registry_client import RegistryClient

__all__ = ["RegistryClient"]

