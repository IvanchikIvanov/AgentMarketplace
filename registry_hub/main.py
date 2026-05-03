"""Backward-compatible import path for the Registry Hub server.

New code should run `python -m marketplace_core.registry.server`.
"""

from marketplace_core.registry.server import *  # noqa: F401,F403

