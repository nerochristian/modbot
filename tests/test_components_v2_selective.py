import asyncio

import discord

from utils.components_v2 import (
    _view_has_buttons,
    ensure_layout_view_action_rows,
    layout_view_from_embeds,
)


def _all_children(item):
    for child in getattr(item, "children", []):
        yield child
        yield from _all_children(child)


def test_button_view_is_detected_but_select_only_view_is_not() -> None:
    button_view = discord.ui.View()
    button_view.add_item(discord.ui.Button(label="Continue", custom_id="continue"))
    select_view = discord.ui.View()
    select_view.add_item(
        discord.ui.Select(
            custom_id="choice",
            options=[discord.SelectOption(label="One", value="one")],
        )
    )

    assert _view_has_buttons(button_view) is True
    assert _view_has_buttons(select_view) is False


def test_embed_button_is_nested_inside_the_converted_container() -> None:
    classic_view = discord.ui.View()
    classic_view.add_item(discord.ui.Button(label="Confirm", custom_id="confirm"))

    layout = asyncio.run(
        layout_view_from_embeds(
            embed=discord.Embed(title="Confirm action", description="Keep this card's existing content."),
            existing_view=classic_view,
        )
    )

    assert isinstance(layout, discord.ui.LayoutView)
    assert not any(isinstance(child, discord.ui.ActionRow) for child in layout.children)
    containers = [child for child in layout.children if isinstance(child, discord.ui.Container)]
    assert containers
    assert any(isinstance(child, discord.ui.Button) for child in _all_children(containers[-1]))


def test_existing_top_level_action_row_moves_inside_last_container() -> None:
    layout = discord.ui.LayoutView()
    container = discord.ui.Container(discord.ui.TextDisplay("Interactive card"))
    layout.add_item(container)
    layout.add_item(discord.ui.ActionRow(discord.ui.Button(label="Open", custom_id="open")))

    ensure_layout_view_action_rows(layout)

    assert not any(isinstance(child, discord.ui.ActionRow) for child in layout.children)
    assert any(isinstance(child, discord.ui.Button) for child in _all_children(container))
