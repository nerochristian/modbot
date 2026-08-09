"""Per-provider API lanes.

Each module here owns the request shape for one upstream gateway. Lane
boundaries are deliberate and enforced by the callers: the talking lane sends
no tools and no images, search/research/vision stay on Luna, and the protected
moderation/memory lane stays pinned to Nemotron.

Provider modules MUST read configuration through
:mod:`cogs.aimoderation.settings` rather than importing constants from
``ai_client``. A ``from``-import snapshots the value and silently defeats the
test suite's patches -- see ``settings`` for the full explanation, and
``tests/test_aimoderation_settings.py`` for the guard that enforces it.
"""
from __future__ import annotations

from .aimodel import AiModelLaneMixin
from .gateways import GatewayLaneMixin
from .openrouter import OpenRouterLaneMixin

__all__ = [
    "AiModelLaneMixin",
    "GatewayLaneMixin",
    "OpenRouterLaneMixin",
]
