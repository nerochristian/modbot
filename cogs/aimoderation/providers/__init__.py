"""Per-lane API request shapes.

Legion Edge is the only text provider, so ``legion.py`` splits work by LANE
rather than by vendor, and the boundaries are deliberate and enforced by the
callers: the talking lane sends no tools and no images, structured decisions
and synthesis stay on their own models, and moderation/routing/memory run on
the protected lane's explicit allow-list.

``google.py`` is the one non-Legion module, and it exists out of necessity
rather than preference: all nine Legion models are text-only, so every lane
that has to look at a picture -- conversational vision, moderation vision,
image screening, and reverse-image identification -- runs on Gemini and Cloud
Vision instead.

Neither module reaches the web for search. Legion Edge has no search
capability at all (no plugins, no native ``web_search`` tool), so search and
research sources come from :mod:`cogs.aimoderation.search`, which does its own
SERP queries and page fetching, and the models here only synthesize what it
gathered.

Lane modules MUST read configuration through
:mod:`cogs.aimoderation.settings` rather than importing constants from
``ai_client``. A ``from``-import snapshots the value and silently defeats the
test suite's patches -- see ``settings`` for the full explanation.
"""
from __future__ import annotations

from .google import GoogleImageEvidence, GoogleImageSearchLaneMixin
from .legion import LegionLaneMixin, strip_reasoning

__all__ = [
    "GoogleImageEvidence",
    "GoogleImageSearchLaneMixin",
    "LegionLaneMixin",
    "strip_reasoning",
]
