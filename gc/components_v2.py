from __future__ import annotations

"""
Universal Components V2 for this bot.

How to use:
1. Put this file anywhere in a discord.py 2.7+ bot repository.
2. Load it once during startup, before your bot sends messages:
      import importlib.util
      from pathlib import Path

      universal_v2 = Path("components_v2.py")
      spec = importlib.util.spec_from_file_location("components_v2_universal", universal_v2)
      module = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(module)
3. If you rename it to `components_v2_universal.py`, you can simply do:
      import components_v2_universal
4. After it is loaded, normal Discord calls such as:
      await channel.send(embed=embed, view=view)
      await interaction.response.send_message(embed=embed)
      await interaction.followup.send(embed=embed, view=view)
      await message.edit(embed=embed, view=view)
   are forced into Components V2.
5. Raw `discord.Embed` objects become V2 containers. Existing buttons/selects
   are moved into V2 action rows so they stay with the converted embed.
6. Sends with only plain text are left alone.
7. Pass ``use_v2=False`` to preserve a classic embed for a specific send/edit.

This file is standalone. It does not depend on any other project file.
"""

from collections import OrderedDict
from contextvars import ContextVar
from typing import Any, Iterable, Optional

import discord
from discord.utils import MISSING


_INSTALLED = False
_ORIGINALS: dict[str, Any] = {}
_V2_TOP_LEVEL_TYPES = {1, 9, 10, 12, 13, 14, 17}
_ACTIVE_ACTOR: ContextVar[Optional[Any]] = ContextVar(
    "docket_components_v2_actor",
    default=None,
)
_INTERACTION_ACTORS: OrderedDict[str, Any] = OrderedDict()
_MAX_INTERACTION_ACTORS = 2048


def _is_missing(value: Any) -> bool:
    return value is MISSING


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _markdown_link(label: str, url: Any) -> str:
    url_text = _clean_text(url)
    if not url_text:
        return label
    return f"[{label}]({url_text})"


def _embed_image_url(embed: discord.Embed, attribute: str) -> Optional[str]:
    image = getattr(embed, attribute, None)
    url = _clean_text(getattr(image, "url", None))
    return url or None


def _component_type(item: discord.ui.Item[Any]) -> Optional[int]:
    try:
        data = item.to_component_dict()
        value = data.get("type")
        return int(value) if value is not None else None
    except Exception:
        return None


def ensure_layout_view_action_rows(view: discord.ui.LayoutView) -> discord.ui.LayoutView:
    children = list(getattr(view, "children", []))
    if not children:
        return view

    needs_fix = any((_component_type(child) not in _V2_TOP_LEVEL_TYPES) for child in children)
    if not needs_fix:
        return view

    action_rows: dict[int, list[discord.ui.Item[Any]]] = {}
    layout_items: list[discord.ui.Item[Any]] = []

    for child in children:
        component_type = _component_type(child)
        if component_type in _V2_TOP_LEVEL_TYPES:
            layout_items.append(child)
            continue

        row = getattr(child, "row", None)
        row_index = row if isinstance(row, int) and row >= 0 else 0
        action_rows.setdefault(row_index, []).append(child)

    view.clear_items()
    for item in layout_items:
        view.add_item(item)
    for row_index in sorted(action_rows):
        for start in range(0, len(action_rows[row_index]), 5):
            view.add_item(discord.ui.ActionRow(*action_rows[row_index][start : start + 5]))

    try:
        children = list(getattr(view, "children", []))
        containers = [child for child in children if isinstance(child, discord.ui.Container)]
        action_row_items = [child for child in children if isinstance(child, discord.ui.ActionRow)]
        if containers and action_row_items:
            last_container = containers[-1]
            view.clear_items()
            for item in children:
                if not isinstance(item, discord.ui.ActionRow):
                    view.add_item(item)
            for row in action_row_items:
                last_container.add_item(row)
    except Exception:
        pass

    return view


def _embed_to_container(embed: discord.Embed) -> discord.ui.Container:
    parts: list[str] = []

    author_name = _clean_text(getattr(embed.author, "name", None))
    if author_name:
        author_url = getattr(embed.author, "url", None)
        parts.append(f"**{_markdown_link(author_name, author_url)}**")

    title = _clean_text(embed.title)
    if title:
        parts.append(f"## {_markdown_link(title, embed.url)}")

    description = _clean_text(embed.description)
    if description:
        parts.append(description)

    for field in embed.fields:
        name = _clean_text(field.name)
        value = _clean_text(field.value)
        if name or value:
            parts.append(f"**{name or 'Field'}**\n{value or '-'}")

    footer_text = _clean_text(getattr(embed.footer, "text", None))
    if footer_text:
        parts.append(footer_text)

    timestamp = getattr(embed, "timestamp", None)
    if timestamp:
        try:
            parts.append(f"<t:{int(timestamp.timestamp())}:f>")
        except Exception:
            pass

    text = "\n\n".join(parts).strip() or "\u200b"
    children: list[discord.ui.Item[Any]] = []

    thumbnail_url = _embed_image_url(embed, "thumbnail")
    if thumbnail_url:
        children.append(
            discord.ui.Section(
                discord.ui.TextDisplay(text),
                accessory=discord.ui.Thumbnail(thumbnail_url),
            )
        )
    else:
        children.append(discord.ui.TextDisplay(text))

    image_url = _embed_image_url(embed, "image")
    if image_url:
        children.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        children.append(discord.ui.MediaGallery(discord.MediaGalleryItem(image_url)))

    colour = getattr(embed, "colour", None) or getattr(embed, "color", None)
    accent_color = getattr(colour, "value", None)
    if isinstance(accent_color, int):
        return discord.ui.Container(*children, accent_color=accent_color)
    return discord.ui.Container(*children)


def _extract_embeds(kwargs: dict[str, Any]) -> list[discord.Embed]:
    embeds: list[discord.Embed] = []

    embed = kwargs.get("embed", MISSING)
    if not _is_missing(embed) and embed is not None:
        embeds.append(embed)

    many = kwargs.get("embeds", MISSING)
    if not _is_missing(many) and many:
        embeds.extend(e for e in many if e is not None)

    return embeds


def _extract_content(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[tuple[Any, ...], Any]:
    content = kwargs.pop("content", MISSING)
    if args:
        content = args[0]
        args = args[1:]
    return args, content


def _iter_action_items(view: discord.ui.View | discord.ui.LayoutView) -> Iterable[discord.ui.Item[Any]]:
    for child in list(getattr(view, "children", [])):
        if isinstance(child, discord.ui.ActionRow):
            for item in list(getattr(child, "children", [])):
                yield item
            continue
        if isinstance(child, discord.ui.Container):
            for item in list(getattr(child, "children", [])):
                if isinstance(item, discord.ui.ActionRow):
                    for action_item in list(getattr(item, "children", [])):
                        yield action_item
            continue
        yield child


def _copy_existing_view(
    target: discord.ui.LayoutView,
    source: Any,
    *,
    put_actions_in_last_container: bool,
) -> discord.ui.LayoutView:
    if source is None or _is_missing(source):
        return target
    if not isinstance(source, (discord.ui.View, discord.ui.LayoutView)):
        return target

    if isinstance(source, discord.ui.LayoutView):
        source = ensure_layout_view_action_rows(source)
        for child in list(getattr(source, "children", [])):
            try:
                target.add_item(child)
            except Exception:
                pass
        return ensure_layout_view_action_rows(target)

    actions = list(_iter_action_items(source))
    if not actions:
        return target

    if put_actions_in_last_container:
        containers = [child for child in target.children if isinstance(child, discord.ui.Container)]
        if containers:
            for start in range(0, len(actions), 5):
                try:
                    containers[-1].add_item(discord.ui.ActionRow(*actions[start : start + 5]))
                except Exception:
                    pass
            return ensure_layout_view_action_rows(target)

    for start in range(0, len(actions), 5):
        try:
            target.add_item(discord.ui.ActionRow(*actions[start : start + 5]))
        except Exception:
            pass
    return ensure_layout_view_action_rows(target)


def _normalize_v2_payload(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    edit: bool = False,
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    use_v2 = kwargs.pop("use_v2", None)
    normalized_use_v2 = use_v2.strip().lower() if isinstance(use_v2, str) else use_v2
    if normalized_use_v2 is False or normalized_use_v2 in {"0", "false", "no", "off"}:
        return args, kwargs

    embeds = _extract_embeds(kwargs)
    view = kwargs.get("view", MISSING)

    explicitly_v2 = normalized_use_v2 is True or normalized_use_v2 in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not explicitly_v2 and any(
        embed.timestamp is not None
        and bool(_clean_text(getattr(embed.footer, "text", None)))
        for embed in embeds
    ):
        # A v2 container can only imitate footer text. Keep native Discord
        # embeds whenever a real footer/timestamp has already been supplied.
        return args, kwargs

    if not embeds:
        if not _is_missing(view) and isinstance(view, discord.ui.LayoutView):
            kwargs["view"] = ensure_layout_view_action_rows(view)
        return args, kwargs

    if not edit:
        args, content = _extract_content(args, kwargs)
    else:
        content = kwargs.get("content", MISSING)

    layout = discord.ui.LayoutView(timeout=getattr(view, "timeout", None) if not _is_missing(view) else None)
    if not _is_missing(content) and content not in (None, ""):
        layout.add_item(discord.ui.Container(discord.ui.TextDisplay(str(content))))
    for embed in embeds:
        layout.add_item(_embed_to_container(embed))

    kwargs["view"] = _copy_existing_view(layout, view, put_actions_in_last_container=True)

    if edit:
        kwargs.pop("embed", None)
        kwargs["embeds"] = []
        kwargs.setdefault("content", None)
        kwargs.setdefault("attachments", [])
    else:
        if "embed" in kwargs:
            kwargs.pop("embed", None)
        if "embeds" in kwargs:
            kwargs.pop("embeds", None)
        kwargs.pop("content", None)

    return args, kwargs


def _target_guild(target: Any) -> Optional[discord.Guild]:
    guild = getattr(target, "guild", None)
    if guild is not None:
        return guild
    parent = getattr(target, "_parent", None)
    return getattr(parent, "guild", None)


def _remember_interaction_actor(interaction: Any) -> Optional[Any]:
    actor = getattr(interaction, "user", None)
    token = _clean_text(getattr(interaction, "token", None))
    if actor is None or not token:
        return actor

    _INTERACTION_ACTORS[token] = actor
    _INTERACTION_ACTORS.move_to_end(token)
    while len(_INTERACTION_ACTORS) > _MAX_INTERACTION_ACTORS:
        _INTERACTION_ACTORS.popitem(last=False)
    return actor


def _actor_for_target(target: Any) -> Optional[Any]:
    interaction = getattr(target, "interaction", None)
    if interaction is not None:
        actor = _remember_interaction_actor(interaction)
        if actor is not None:
            return actor

    parent = getattr(target, "_parent", None)
    if parent is not None and getattr(parent, "user", None) is not None:
        return _remember_interaction_actor(parent)

    author = getattr(target, "author", None)
    if author is not None:
        return author

    token = _clean_text(getattr(target, "token", None))
    if token:
        actor = _INTERACTION_ACTORS.get(token)
        if actor is not None:
            _INTERACTION_ACTORS.move_to_end(token)
            return actor

    return _ACTIVE_ACTOR.get()


def _stamp_actor_payload(kwargs: dict[str, Any], actor: Any) -> bool:
    try:
        from utils.embeds import stamp_actor_footer
    except Exception:
        return False

    stamped = False
    embed = kwargs.get("embed", MISSING)
    if isinstance(embed, discord.Embed):
        kwargs["embed"] = stamp_actor_footer(embed, actor)
        stamped = True

    embeds = kwargs.get("embeds", MISSING)
    if isinstance(embeds, (list, tuple)):
        formatted: list[Any] = []
        for candidate in embeds:
            if isinstance(candidate, discord.Embed):
                candidate = stamp_actor_footer(candidate, actor)
                stamped = True
            formatted.append(candidate)
        kwargs["embeds"] = formatted
    return stamped


async def _apply_shared_status_emojis(target: Any, kwargs: dict[str, Any]) -> None:
    guild = _target_guild(target)
    if guild is None:
        return
    try:
        from utils.status_emojis import apply_status_emoji_overrides
    except Exception:
        return

    embed = kwargs.get("embed", MISSING)
    if isinstance(embed, discord.Embed):
        try:
            kwargs["embed"] = await apply_status_emoji_overrides(embed, guild)
        except Exception:
            pass

    embeds = kwargs.get("embeds", MISSING)
    if isinstance(embeds, (list, tuple)):
        formatted: list[Any] = []
        for candidate in embeds:
            if isinstance(candidate, discord.Embed):
                try:
                    candidate = await apply_status_emoji_overrides(candidate, guild)
                except Exception:
                    pass
            formatted.append(candidate)
        kwargs["embeds"] = formatted


def _patch_async_method(owner: Any, name: str, key: str, *, edit: bool = False) -> None:
    original = getattr(owner, name, None)
    if original is None or getattr(original, "_universal_components_v2", False):
        return

    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        actor = _actor_for_target(self)
        actor_token = None
        if actor is not None:
            actor_token = _ACTIVE_ACTOR.set(actor)
            if _stamp_actor_payload(kwargs, actor):
                # Components V2 cannot render Discord's native avatar/timestamp
                # footer. Invocation responses with an actor therefore stay classic.
                kwargs.setdefault("use_v2", False)
        await _apply_shared_status_emojis(self, kwargs)
        try:
            normalized_args, normalized_kwargs = _normalize_v2_payload(args, kwargs, edit=edit)
            return await original(self, *normalized_args, **normalized_kwargs)
        finally:
            if actor_token is not None:
                _ACTIVE_ACTOR.reset(actor_token)

    wrapper._universal_components_v2 = True  # type: ignore[attr-defined]
    _ORIGINALS[key] = original
    setattr(owner, name, wrapper)


def install_universal_components_v2() -> None:
    """Install process-wide Components V2 send/edit normalization."""
    global _INSTALLED
    if _INSTALLED:
        return

    _patch_async_method(discord.abc.Messageable, "send", "messageable_send")
    _patch_async_method(discord.InteractionResponse, "send_message", "interaction_send_message")
    _patch_async_method(discord.InteractionResponse, "defer", "interaction_defer")
    _patch_async_method(discord.InteractionResponse, "edit_message", "interaction_edit_message", edit=True)
    _patch_async_method(discord.Interaction, "edit_original_response", "interaction_edit_original", edit=True)
    _patch_async_method(discord.Webhook, "send", "webhook_send")
    _patch_async_method(discord.WebhookMessage, "edit", "webhook_message_edit", edit=True)
    _patch_async_method(discord.Message, "reply", "message_reply")
    _patch_async_method(discord.Message, "edit", "message_edit", edit=True)
    try:
        from discord.ext import commands
    except Exception:
        commands = None
    if commands is not None:
        _patch_async_method(commands.Context, "send", "commands_context_send")

    _INSTALLED = True


install_universal_components_v2()
