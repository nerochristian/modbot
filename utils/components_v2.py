"""
Discord Components v2 helpers (LayoutView + layout items).

This module provides:
- Embed -> Components v2 "card" conversion
- Optional runtime monkeypatch so existing embed-based code sends v2 layouts
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Optional

import discord


_V2_TOP_LEVEL_TYPES = {1, 9, 10, 12, 13, 14, 17}
_TS_ONLY_RE = re.compile(
    r"^(?:"
    r"<t:\d+(?::[tTdDfFR])?>"
    r"|"
    r"\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}:\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
    r")$"
)


def _component_type(item: discord.ui.Item[Any]) -> Optional[int]:
    try:
        data = item.to_component_dict()
        t = data.get("type")
        return int(t) if t is not None else None
    except Exception:
        return None


def ensure_layout_view_action_rows(view: discord.ui.LayoutView) -> discord.ui.LayoutView:
    """
    Ensure a Components v2 LayoutView only has valid top-level item types.

    Discord Components v2 requires top-level items to be layout components (e.g. Container/Section/TextDisplay)
    or ActionRow. Interactive components like Button/Select must be wrapped inside an ActionRow.
    """

    children = list(getattr(view, "children", []))
    if not children:
        return view

    needs_fix = any((_component_type(c) not in _V2_TOP_LEVEL_TYPES) for c in children)
    if not needs_fix:
        return view

    action_rows: dict[int, list[discord.ui.Item[Any]]] = {}
    layout_items: list[discord.ui.Item[Any]] = []

    for child in children:
        t = _component_type(child)
        if t in _V2_TOP_LEVEL_TYPES:
            layout_items.append(child)
            continue

        row = getattr(child, "row", None)
        row_index = row if isinstance(row, int) and row >= 0 else 0
        action_rows.setdefault(row_index, []).append(child)

    view.clear_items()
    for item in layout_items:
        view.add_item(item)
    for row_index in sorted(action_rows.keys()):
        view.add_item(discord.ui.ActionRow(*action_rows[row_index]))

    # Prefer placing action rows inside the last container, so buttons render "inside the card".
    # This keeps existing v1-style Views looking more like native v2 panels.
    try:
        children = list(getattr(view, "children", []))
        containers = [c for c in children if isinstance(c, discord.ui.Container)]
        action_row_items = [c for c in children if isinstance(c, discord.ui.ActionRow)]
        if containers and action_row_items:
            last_container = containers[-1]
            view.clear_items()
            for item in children:
                if isinstance(item, discord.ui.ActionRow):
                    continue
                view.add_item(item)
            for row in action_row_items:
                last_container.add_item(row)
    except Exception:
        pass

    return view


def branded_panel_container(
    *,
    title: str,
    description: str,
    banner_url: Optional[str] = None,
    logo_url: Optional[str] = None,
    accent_color: Optional[int] = None,
    banner_separated: bool = False,
) -> discord.ui.Container:
    """
    Build a Components v2 "panel" container with an optional banner and logo thumbnail.
    """

    children: list[discord.ui.Item[Any]] = []

    title = (title or "").strip()
    description = (description or "").strip()
    header = "\n".join([x for x in [f"**{title}**" if title else "", description] if x]).strip()

    has_banner = False
    if banner_url:
        banner_url = (banner_url or "").strip()
        if banner_url:
            children.append(discord.ui.MediaGallery(discord.MediaGalleryItem(banner_url)))
            has_banner = True

    if has_banner and banner_separated and header:
        children.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))

    if header:
        if logo_url:
            logo_url = (logo_url or "").strip()
        if logo_url:
            children.append(
                discord.ui.Section(
                    discord.ui.TextDisplay(header),
                    accessory=discord.ui.Thumbnail(logo_url),
                )
            )
        else:
            children.append(discord.ui.TextDisplay(header))

    if accent_color is not None:
        return discord.ui.Container(*children, accent_color=accent_color)
    return discord.ui.Container(*children)


def _get_embed_thumbnail_url(embed: discord.Embed) -> Optional[str]:
    try:
        url = getattr(embed.thumbnail, "url", None)
        return url or None
    except Exception:
        return None


def _get_embed_image_url(embed: discord.Embed) -> Optional[str]:
    try:
        url = getattr(embed.image, "url", None)
        return url or None
    except Exception:
        return None


def _get_embed_footer_text(embed: discord.Embed) -> Optional[str]:
    try:
        text = getattr(embed.footer, "text", None)
        text = (text or "").strip()
        if text and _TS_ONLY_RE.fullmatch(text):
            return None
        return text or None
    except Exception:
        return None


def _accent_color_from_embed(embed: discord.Embed) -> Optional[int]:
    try:
        color = embed.color
        if isinstance(color, discord.Colour):
            value = int(color.value)
            return value or None
        if isinstance(color, int):
            return color or None
    except Exception:
        pass
    return None


def _format_timestamp(ts: Any) -> Optional[str]:
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts.isoformat(sep=" ", timespec="seconds")
    return None


def container_from_embed(embed: discord.Embed) -> discord.ui.Container:
    accent = _accent_color_from_embed(embed)
    children: list[discord.ui.Item[Any]] = []

    title = (embed.title or "").strip()
    desc = (embed.description or "").strip()

    author_name = ""
    try:
        author_name = (getattr(embed.author, "name", "") or "").strip()
    except Exception:
        author_name = ""

    header_lines: list[str] = []
    if author_name:
        header_lines.append(f"**{author_name}**")
    if title:
        header_lines.append(f"**{title}**")
    if desc:
        header_lines.append(desc)

    header_text = "\n".join(header_lines).strip()
    thumb_url = _get_embed_thumbnail_url(embed)
    if header_text:
        if thumb_url:
            children.append(
                discord.ui.Section(
                    discord.ui.TextDisplay(header_text),
                    accessory=discord.ui.Thumbnail(thumb_url),
                )
            )
        else:
            children.append(discord.ui.TextDisplay(header_text))

    for field in embed.fields:
        name = (field.name or "").strip()
        value = (field.value or "").strip()
        if not name and not value:
            continue
        children.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        if name and value:
            children.append(discord.ui.TextDisplay(f"**{name}**\n{value}"))
        elif name:
            children.append(discord.ui.TextDisplay(f"**{name}**"))
        else:
            children.append(discord.ui.TextDisplay(value))

    image_url = _get_embed_image_url(embed)
    if image_url:
        children.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        children.append(
            discord.ui.MediaGallery(discord.MediaGalleryItem(image_url))
        )

    footer_text = _get_embed_footer_text(embed)
    # Don't surface embed timestamps in Components v2 cards.
    meta = footer_text
    if meta:
        children.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        children.append(discord.ui.TextDisplay(f"*{meta}*"))

    if accent is not None:
        return discord.ui.Container(*children, accent_color=accent)
    return discord.ui.Container(*children)


def _normalize_embeds(
    *,
    embed: Any = None,
    embeds: Any = None,
) -> list[discord.Embed]:
    out: list[discord.Embed] = []
    if embed and isinstance(embed, discord.Embed):
        out.append(embed)
    if embeds:
        for e in embeds:
            if isinstance(e, discord.Embed):
                out.append(e)
    return out


async def layout_view_from_embeds(
    *,
    content: Any = None,
    embed: Any = None,
    embeds: Any = None,
    existing_view: Optional[discord.ui.BaseView] = None,
) -> discord.ui.LayoutView:
    if existing_view is None:
        view = discord.ui.LayoutView()
        existing_children: list[discord.ui.Item[Any]] = []
    else:
        existing_children = list(getattr(existing_view, "children", []))
        if isinstance(existing_view, discord.ui.LayoutView):
            view = existing_view
        else:
            timeout = getattr(existing_view, "timeout", 180.0)
            view = discord.ui.LayoutView(timeout=timeout)

    if existing_children:
        view.clear_items()

    if content not in (None, discord.utils.MISSING, ...):
        try:
            content_text = content if isinstance(content, str) else str(content)
        except Exception:
            content_text = None
        if content_text:
            content_text = content_text.strip()
        if content_text:
            view.add_item(discord.ui.Container(discord.ui.TextDisplay(content_text)))

    for e in _normalize_embeds(embed=embed, embeds=embeds):
        container = container_from_embed(e)
        if container.children:
            view.add_item(container)

    for child in existing_children:
        view.add_item(child)
    return ensure_layout_view_action_rows(view)


def patch_components_v2() -> None:
    """
    Monkeypatch discord.py send methods to convert embeds into Components v2 layouts.

    This lets existing code continue creating embeds, while the library sends LayoutView cards.
    It also patches common edit methods so code editing messages with embeds keeps working.
    """

    if getattr(patch_components_v2, "_patched", False):
        return

    from discord.utils import MISSING

    original_interaction_send = discord.InteractionResponse.send_message
    original_webhook_send = discord.Webhook.send
    original_messageable_send = discord.abc.Messageable.send
    original_interaction_edit_original = discord.Interaction.edit_original_response
    original_interaction_response_edit = discord.InteractionResponse.edit_message
    original_message_edit = discord.Message.edit
    original_webhook_edit_message = discord.Webhook.edit_message
    original_webhook_message_edit = discord.WebhookMessage.edit

    async def patched_interaction_send_message(self, *args, **kwargs):
        content = args[0] if args else kwargs.pop("content", MISSING)
        kwargs.pop("content", None)
        embed = kwargs.get("embed", MISSING)
        embeds = kwargs.get("embeds", MISSING)
        view = kwargs.get("view", MISSING)

        has_embed = embed is not MISSING and embed is not None
        has_embeds = embeds is not MISSING and bool(embeds)
        has_content = content is not MISSING and content not in (None, "", ...)

        if (has_embed or has_embeds or has_content) and (
            view in (MISSING, None) or hasattr(view, "children")
        ):
            layout = await layout_view_from_embeds(
                content=content,
                embed=None if embed is MISSING else embed,
                embeds=None if embeds is MISSING else embeds,
                existing_view=None if view is MISSING else view,
            )
            layout = ensure_layout_view_action_rows(layout)
            kwargs["view"] = layout
            kwargs.pop("embed", None)
            kwargs.pop("embeds", None)
            # Components v2 messages cannot include a content field.
            content = MISSING
        elif isinstance(view, discord.ui.LayoutView) and content is not MISSING:
            # Components v2 messages cannot include a content field; move it into a TextDisplay.
            layout = await layout_view_from_embeds(
                content=content,
                embed=None,
                embeds=None,
                existing_view=view,
            )
            layout = ensure_layout_view_action_rows(layout)
            kwargs["view"] = layout
            content = MISSING
        elif isinstance(view, discord.ui.LayoutView):
            kwargs["view"] = ensure_layout_view_action_rows(view)

        if content is MISSING:
            return await original_interaction_send(self, **kwargs)
        return await original_interaction_send(self, content=content, **kwargs)

    async def _coerce_to_v2_view(*, content: Any, embed: Any, embeds: Any, view: Any) -> tuple[Any, Any, Any, Any]:
        """
        Convert embed(s)/content into a LayoutView so the request is compatible with Components v2.

        Returns (content, embed, embeds, view) with embeds removed and content moved into the view.
        """

        has_embed = embed is not MISSING and embed is not None
        has_embeds = embeds is not MISSING and bool(embeds)

        has_content = content is not MISSING and content not in (None, "", ...)

        if (has_embed or has_embeds or has_content) and (view in (MISSING, None) or hasattr(view, "children")):
            layout = await layout_view_from_embeds(
                content=content,
                embed=None if embed is MISSING else embed,
                embeds=None if embeds is MISSING else embeds,
                existing_view=None if view is MISSING else view,
            )
            layout = ensure_layout_view_action_rows(layout)
            return (MISSING, None, None, layout)

        if isinstance(view, discord.ui.LayoutView) and content is not MISSING:
            layout = await layout_view_from_embeds(
                content=content,
                embed=None,
                embeds=None,
                existing_view=view,
            )
            layout = ensure_layout_view_action_rows(layout)
            return (MISSING, embed if embed is not MISSING else None, embeds if embeds is not MISSING else None, layout)

        if isinstance(view, discord.ui.LayoutView):
            return (content, embed if embed is not MISSING else None, embeds if embeds is not MISSING else None, ensure_layout_view_action_rows(view))

        return (content, embed if embed is not MISSING else None, embeds if embeds is not MISSING else None, view)

    async def patched_webhook_send(self, *args, **kwargs):
        content = args[0] if args else kwargs.pop("content", MISSING)
        kwargs.pop("content", None)
        embed = kwargs.get("embed", MISSING)
        embeds = kwargs.get("embeds", MISSING)
        view = kwargs.get("view", MISSING)

        has_embed = embed is not MISSING and embed is not None
        has_embeds = embeds is not MISSING and bool(embeds)
        has_content = content is not MISSING and content not in (None, "", ...)

        if (has_embed or has_embeds or has_content) and (
            view in (MISSING, None) or hasattr(view, "children")
        ):
            layout = await layout_view_from_embeds(
                content=content,
                embed=None if embed is MISSING else embed,
                embeds=None if embeds is MISSING else embeds,
                existing_view=None if view is MISSING else view,
            )
            layout = ensure_layout_view_action_rows(layout)
            kwargs["view"] = layout
            kwargs.pop("embed", None)
            kwargs.pop("embeds", None)
            content = MISSING
        elif isinstance(view, discord.ui.LayoutView) and content is not MISSING:
            layout = await layout_view_from_embeds(
                content=content,
                embed=None,
                embeds=None,
                existing_view=view,
            )
            layout = ensure_layout_view_action_rows(layout)
            kwargs["view"] = layout
            content = MISSING
        elif isinstance(view, discord.ui.LayoutView):
            kwargs["view"] = ensure_layout_view_action_rows(view)

        if content is MISSING:
            return await original_webhook_send(self, **kwargs)
        return await original_webhook_send(self, content=content, **kwargs)

    async def patched_messageable_send(self, *args, **kwargs):
        content = args[0] if args else kwargs.pop("content", MISSING)
        kwargs.pop("content", None)
        embed = kwargs.get("embed", None)
        embeds = kwargs.get("embeds", None)
        view = kwargs.get("view", None)

        has_embed = embed is not None
        has_embeds = bool(embeds)
        has_content = content is not MISSING and content not in (None, "", ...)

        if (has_embed or has_embeds or has_content) and (view is None or hasattr(view, "children")):
            layout = await layout_view_from_embeds(
                content=content,
                embed=embed,
                embeds=embeds,
                existing_view=view,
            )
            layout = ensure_layout_view_action_rows(layout)
            kwargs["view"] = layout
            kwargs.pop("embed", None)
            kwargs.pop("embeds", None)
            content = MISSING
        elif isinstance(view, discord.ui.LayoutView) and content is not MISSING:
            layout = await layout_view_from_embeds(
                content=content,
                embed=None,
                embeds=None,
                existing_view=view,
            )
            layout = ensure_layout_view_action_rows(layout)
            kwargs["view"] = layout
            content = MISSING
        elif isinstance(view, discord.ui.LayoutView):
            kwargs["view"] = ensure_layout_view_action_rows(view)

        if content is MISSING:
            return await original_messageable_send(self, **kwargs)
        return await original_messageable_send(self, content=content, **kwargs)

    async def patched_interaction_edit_original_response(self, *args, **kwargs):
        content = kwargs.get("content", MISSING)
        kwargs.pop("content", None)
        embed = kwargs.get("embed", MISSING)
        embeds = kwargs.get("embeds", MISSING)
        view = kwargs.get("view", MISSING)

        content, embed, embeds, view = await _coerce_to_v2_view(
            content=content,
            embed=embed,
            embeds=embeds,
            view=view,
        )

        if view is not MISSING:
            kwargs["view"] = view
        if embed is None:
            kwargs.pop("embed", None)
        if embeds is None:
            kwargs.pop("embeds", None)

        if content is MISSING:
            return await original_interaction_edit_original(self, **kwargs)
        return await original_interaction_edit_original(self, content=content, **kwargs)

    async def patched_interaction_response_edit_message(self, *args, **kwargs):
        content = kwargs.get("content", MISSING)
        kwargs.pop("content", None)
        embed = kwargs.get("embed", MISSING)
        embeds = kwargs.get("embeds", MISSING)
        view = kwargs.get("view", MISSING)

        content, embed, embeds, view = await _coerce_to_v2_view(
            content=content,
            embed=embed,
            embeds=embeds,
            view=view,
        )

        if view is not MISSING:
            kwargs["view"] = view
        if embed is None:
            kwargs.pop("embed", None)
        if embeds is None:
            kwargs.pop("embeds", None)

        if content is MISSING:
            return await original_interaction_response_edit(self, **kwargs)
        return await original_interaction_response_edit(self, content=content, **kwargs)

    async def patched_message_edit(self, *args, **kwargs):
        content = kwargs.get("content", MISSING)
        kwargs.pop("content", None)
        embed = kwargs.get("embed", MISSING)
        embeds = kwargs.get("embeds", MISSING)
        view = kwargs.get("view", MISSING)

        content, embed, embeds, view = await _coerce_to_v2_view(
            content=content,
            embed=embed,
            embeds=embeds,
            view=view,
        )

        if view is not MISSING:
            kwargs["view"] = view
        if embed is None:
            kwargs.pop("embed", None)
        if embeds is None:
            kwargs.pop("embeds", None)

        if content is MISSING:
            return await original_message_edit(self, **kwargs)
        return await original_message_edit(self, content=content, **kwargs)

    async def patched_webhook_edit_message(self, *args, **kwargs):
        content = kwargs.get("content", MISSING)
        kwargs.pop("content", None)
        embed = kwargs.get("embed", MISSING)
        embeds = kwargs.get("embeds", MISSING)
        view = kwargs.get("view", MISSING)

        content, embed, embeds, view = await _coerce_to_v2_view(
            content=content,
            embed=embed,
            embeds=embeds,
            view=view,
        )

        if view is not MISSING:
            kwargs["view"] = view
        if embed is None:
            kwargs.pop("embed", None)
        if embeds is None:
            kwargs.pop("embeds", None)

        if content is MISSING:
            return await original_webhook_edit_message(self, *args, **kwargs)
        return await original_webhook_edit_message(self, *args, content=content, **kwargs)

    async def patched_webhook_message_edit(self, *args, **kwargs):
        content = kwargs.get("content", MISSING)
        kwargs.pop("content", None)
        embed = kwargs.get("embed", MISSING)
        embeds = kwargs.get("embeds", MISSING)
        view = kwargs.get("view", MISSING)

        content, embed, embeds, view = await _coerce_to_v2_view(
            content=content,
            embed=embed,
            embeds=embeds,
            view=view,
        )

        if view is not MISSING:
            kwargs["view"] = view
        if embed is None:
            kwargs.pop("embed", None)
        if embeds is None:
            kwargs.pop("embeds", None)

        if content is MISSING:
            return await original_webhook_message_edit(self, *args, **kwargs)
        return await original_webhook_message_edit(self, *args, content=content, **kwargs)

    discord.InteractionResponse.send_message = patched_interaction_send_message  # type: ignore[assignment]
    discord.Webhook.send = patched_webhook_send  # type: ignore[assignment]
    discord.abc.Messageable.send = patched_messageable_send  # type: ignore[assignment]
    discord.Interaction.edit_original_response = patched_interaction_edit_original_response  # type: ignore[assignment]
    discord.InteractionResponse.edit_message = patched_interaction_response_edit_message  # type: ignore[assignment]
    discord.Message.edit = patched_message_edit  # type: ignore[assignment]
    discord.Webhook.edit_message = patched_webhook_edit_message  # type: ignore[assignment]
    discord.WebhookMessage.edit = patched_webhook_message_edit  # type: ignore[assignment]

    patch_components_v2._patched = True  # type: ignore[attr-defined]
