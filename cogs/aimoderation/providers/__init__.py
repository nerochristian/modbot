"""Per-lane API request shapes.

OpenRouter is the only provider, so these modules split work by LANE rather
than by vendor, and the boundaries are deliberate and enforced by the callers:
the talking lane sends no tools and no images, search/research/vision stay on
their own models, and moderation/routing/memory run on the protected lane's
explicit allow-list.

``google.py`` is the one non-OpenRouter module, and it is not a provider: Cloud
Vision Web Detection plus a grounded Gemini pass supply the reverse-image and
OCR evidence that no OpenRouter model can produce. Web Detection runs for every
conversation image so the answering lane knows what the image actually is; the
grounded Gemini pass stays confined to explicit image-identification turns.

Lane modules MUST read configuration through
:mod:`cogs.aimoderation.settings` rather than importing constants from
``ai_client``. A ``from``-import snapshots the value and silently defeats the
test suite's patches -- see ``settings`` for the full explanation.
"""
from __future__ import annotations

from .google import GoogleImageEvidence, GoogleImageSearchLaneMixin
from .openrouter import OpenRouterLaneMixin

__all__ = [
    "GoogleImageEvidence",
    "GoogleImageSearchLaneMixin",
    "OpenRouterLaneMixin",
]
