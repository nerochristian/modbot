"""Research result gating: sources, citation cleanup, and the refusal contract.

The rule this module enforces: **never present research the bot cannot back
with a real, verifiable link.** A research answer with no source URLs is
refused (``_RESEARCH_UNAVAILABLE``) rather than dressed up as sourced.

That rule exists because of a specific past failure. The Sonar pre-fetch was
routed through a gateway that serves no ``perplexity/*`` model, so every
research turn got HTTP 400 -- and the code then attached a hardcoded
``https://perplexity.ai/`` placeholder purely to satisfy the source gate. The
bot claimed sourcing it did not have. Only genuine citation URLs count here.

Pure text functions with no network or model calls, so they are directly
unit-testable.
"""
from __future__ import annotations

import re
from typing import List, Optional

# Shown when research cannot be backed by verifiable links. Callers return this
# instead of an unsourced answer.
RESEARCH_UNAVAILABLE = (
    "Live search is unavailable right now because no verifiable source links "
    "were returned. I won't invent a current-events answer. Please try again shortly."
)

SOURCES_MARKER = "__BOT_SOURCES__"

# Maximum links attached to a research reply, to keep the sources embed readable.
_MAX_SOURCES = 8


class ResearchGatingMixin:
    """Source extraction and the verifiable-source gate.

    Static methods mixed into ``AIClient``; tests and internal call sites reach
    them as ``AIClient._finalize_research_response(...)``, including unbound.
    """

    @staticmethod
    def _research_source_urls(
        content: str,
        source_urls: Optional[List[str]] = None,
    ) -> List[str]:
        """Collect de-duplicated http(s) URLs from explicit sources, then body text."""
        urls: List[str] = []
        for url in source_urls or []:
            clean = str(url or "").strip().rstrip(".,;)>")
            if clean.startswith(("https://", "http://")) and clean not in urls:
                urls.append(clean)
        for url in re.findall(r"https?://[^\s<>]+", content or ""):
            clean = url.rstrip(".,;)>")
            if clean not in urls:
                urls.append(clean)
        return urls

    @staticmethod
    def _finalize_research_response(
        content: str,
        source_urls: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Return research only when it carries verifiable source URLs.

        Returns ``None`` when the answer cannot be sourced, so callers surface
        the refusal rather than an unbacked claim. ``source_urls`` carries the
        pre-fetch's real citations: the research prompt forbids URLs in the body
        and providers often omit citation annotations, so without them a good
        answer would fail this gate.
        """
        text = (content or "").strip()
        low = text.lower()
        if not text or (
            "search is unavailable in expert mode" in low
            or "please use instant mode" in low
        ):
            return None

        urls = ResearchGatingMixin._research_source_urls(text, source_urls)

        if SOURCES_MARKER in text:
            _, sources = text.split(SOURCES_MARKER, 1)
            if re.search(r"https?://", sources):
                return text
            text = text.split(SOURCES_MARKER, 1)[0].rstrip()

        if not urls:
            return None
        sources = "\n".join(f"- <{url}>" for url in urls[:_MAX_SOURCES])
        return f"{text}\n\n{SOURCES_MARKER}\n{sources}"

    @staticmethod
    def _strip_citation_tokens(text: str) -> str:
        """Remove provider citation markers, preserving real markdown links."""
        text = re.sub(r"\s*\[citation:\d+\]", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*\[source:\d+\]", "", text, flags=re.IGNORECASE)
        # Bare numeric citation markers such as "[1]" or "[2][7][10]". Research
        # providers emit these even when told not to, and the bot shows verified
        # links separately, so they are noise in a Discord reply. The negative
        # lookahead for "(" keeps real markdown links like "[1](https://x)"
        # intact, and requiring digits-only avoids touching "[WARN]" style text.
        text = re.sub(r"\s*(?:\[\d{1,3}\])+(?!\()", "", text)
        text = re.sub(r"\s+([,.;:])", r"\1", text)
        return text
