"""Discord presentation layer for AI conversation responses.

Pure formatting: turning a model's text into embeds, chunks, and the sources
button. Nothing here performs network or model calls, so these helpers are
directly unit-testable without a bot instance.

Implemented as a mixin rather than free functions because the test suite
reaches them as class attributes (``AIModeration._build_research_embeds``,
``AIModeration._compact_research_spacing``, ...). Keeping them bound to the
class preserves those call sites and any ``patch.object`` on them.

The only host requirement is ``self.reply(message, ...)``, provided by the cog.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

import discord

from .types import ConversationMode, ConversationSignals


class _SourcesView(discord.ui.View):
    """Reveals research citations on demand instead of inlining raw URLs.

    The research system prompt forbids URLs in the answer body, so sources
    travel separately and surface through this button.
    """

    def __init__(self, sources_text: str):
        super().__init__(timeout=None)
        self.sources_text = sources_text

    @discord.ui.button(
        label="View Sources",
        style=discord.ButtonStyle.secondary,
        emoji="🔗",
    )
    async def view_sources(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        embed = discord.Embed(
            title="Research Sources",
            description=self.sources_text[:4096],
            color=discord.Color.from_rgb(88, 101, 242),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ResponseRenderingMixin:
    """Formats and delivers conversation responses to Discord."""

    # Exposed on the class so existing ``self._SourcesView(...)`` call sites and
    # tests keep working after the move out of the cog body.
    _SourcesView = _SourcesView

    @staticmethod
    def _build_ai_status_embed(response: str) -> discord.Embed:
        return discord.Embed(
            title="AI Status",
            description=response[:4000],
            color=discord.Color.orange(),
        )

    @staticmethod
    def _compact_research_spacing(response: str) -> str:
        """Keep one visual blank line between blocks without altering code fences."""
        sections = re.split(r"(```[\s\S]*?```)", response)
        for index in range(0, len(sections), 2):
            section = re.sub(r"[ \t]+\n", "\n", sections[index])
            sections[index] = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", section)
        return "".join(sections).strip()

    def _build_research_embed(self, response: str, query: str = "") -> discord.Embed:
        # Named explicitly rather than via ``self`` because tests call this
        # unbound as ``AIModeration._build_research_embed(None, response, ...)``;
        # a ``self.`` lookup would raise AttributeError on None.
        return ResponseRenderingMixin._build_research_embeds(response, query)[0]

    @classmethod
    def _build_research_embeds(
        cls,
        response: str,
        query: str,
    ) -> List[discord.Embed]:
        heading = re.match(
            r"^\s*(?:\*\*)?#{1,3}\s+(.+?)(?:\*\*)?\s*(?:\n|$)",
            response,
        )
        if heading:
            title = heading.group(1).strip()
            response = response[heading.end():].lstrip()
        else:
            clean_query = re.sub(r"\s+", " ", query).strip()
            title = f"🔍 {clean_query}" if clean_query else "🔍 Research"
        response = cls._compact_research_spacing(response)
        if len(title) > 256:
            title = title[:253].rstrip() + "..."
        # .strip() matters: _split_response returns [] for blank input, and the
        # loop below (plus _build_research_embed's [0]) needs at least one chunk.
        chunks = cls._split_response(
            response.strip() or "No research summary was returned.",
            max_len=3_900,
        )
        embeds: List[discord.Embed] = []
        total = len(chunks)
        for index, chunk in enumerate(chunks, start=1):
            page_title = title
            if total > 1:
                suffix = f" ({index}/{total})"
                page_title = f"{title[: max(1, 256 - len(suffix))].rstrip()}{suffix}"
            embeds.append(
                discord.Embed(
                    title=page_title,
                    description=chunk,
                    color=discord.Color.from_rgb(88, 101, 242),
                )
            )
        return embeds

    @staticmethod
    def _split_research_sources(response: str) -> Tuple[str, Optional[str]]:
        for marker in ("\n\n__BOT_SOURCES__\n", "\n\n**Sources**\n"):
            if marker in response:
                answer, sources = response.split(marker, 1)
                clean_sources = sources.strip()
                return answer.rstrip(), (
                    f"**Sources:**\n{clean_sources}" if clean_sources else None
                )
        return response, None

    async def _deliver_response(
        self,
        message: discord.Message,
        response: str,
        signals: ConversationSignals,
    ) -> None:
        """Deliver a conversation response with smart formatting."""
        response, sources_text = self._split_research_sources(response)

        is_research = signals.mode == ConversationMode.RESEARCH

        # A research answer with no verifiable sources is reported as
        # unavailable rather than presented as fact.
        if is_research and not sources_text:
            await self.reply(
                message,
                embed=self._build_ai_status_embed(
                    "Live search is unavailable right now because the response "
                    "did not include verifiable source links."
                ),
            )
            return

        # When Luna chooses to search during ordinary chat, keep OpenRouter's
        # citations accessible without turning the concise answer into a
        # research embed.
        view = self._SourcesView(sources_text) if sources_text else None

        if is_research:
            embeds = self._build_research_embeds(response, message.content or "")
            for index, embed in enumerate(embeds):
                current_view = view if index == len(embeds) - 1 else None
                sent = await self.reply(message, embed=embed, view=current_view)
                if not sent:
                    break
            return

        # Short responses: plain text
        if len(response) <= 1900:
            await self.reply(message, content=response, view=view)
            return

        # Very long responses: split into chunks
        chunks = self._split_response(response, max_len=1900)
        if not chunks:
            # Long but entirely whitespace. Silence would look like the bot
            # ignoring the message, so say something instead.
            await self.reply(
                message,
                content="I got an empty response from the AI. Try rephrasing that.",
            )
            return
        for index, chunk in enumerate(chunks):
            current_view = view if index == len(chunks) - 1 else None
            sent = await self.reply(message, content=chunk, view=current_view)
            if not sent:
                break

    _FENCE_RE = re.compile(r"^```([A-Za-z0-9_+-]*)\s*$", re.MULTILINE)

    @staticmethod
    def _split_response(text: str, max_len: int = 1900) -> List[str]:
        """Split a long response into chunks at natural boundaries.

        Two properties matter beyond the length limit:

        Code fences are re-balanced across the cut. Splitting mid-fence used to
        emit chunk 1 with an opener and no closer, chunk 2 with neither (so the
        code rendered as prose), and chunk 3 with a stray closer. Each chunk is
        now closed at its end and reopened -- with the same language tag -- at
        the start of the next.

        Blank chunks are dropped. Discord rejects an empty message, so a
        whitespace-only response longer than max_len used to produce a chunk
        that could only fail at the API.
        """
        if not text.strip():
            return []
        if len(text) <= max_len:
            return [text]

        chunks: List[str] = []
        remaining = text
        # Language tag of the fence left open by the previous chunk, if any.
        open_fence: Optional[str] = None

        while remaining:
            prefix = f"```{open_fence}\n" if open_fence is not None else ""
            # Reserve room for the prefix and a closing fence so a re-balanced
            # chunk cannot exceed the limit.
            budget = max_len - len(prefix) - 4

            if len(remaining) + len(prefix) <= max_len:
                chunk, remaining = prefix + remaining, ""
            else:
                split_at = remaining.rfind("\n\n", 0, budget)
                if split_at < budget // 3:
                    split_at = remaining.rfind("\n", 0, budget)
                if split_at < budget // 3:
                    split_at = remaining.rfind(". ", 0, budget)
                    if split_at > 0:
                        split_at += 1  # Include the period
                if split_at < budget // 3:
                    split_at = budget

                chunk = prefix + remaining[:split_at].rstrip()
                remaining = remaining[split_at:].lstrip()

            # An odd number of fences means this chunk ends inside a block.
            fences = ResponseRenderingMixin._FENCE_RE.findall(chunk)
            if len(fences) % 2:
                open_fence = fences[-1]
                chunk += "\n```"
            else:
                open_fence = None

            if chunk.strip():
                chunks.append(chunk)

        return chunks
