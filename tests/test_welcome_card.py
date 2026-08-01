from __future__ import annotations

import io

from PIL import Image

from utils.welcome_card import (
    WelcomeCardOptions,
    _render_welcome_card_sync,
    welcome_card_options_from_settings,
)


def test_dashboard_settings_only_control_welcome_background() -> None:
    options = welcome_card_options_from_settings(
        {
            "welcome_bg_url": "  https://cdn.example.com/welcome.png  ",
            "welcome_card_blur": 40,
            "welcome_card_overlay": 90,
            "welcome_card_layout": "left",
            "welcome_card_label": "CUSTOM",
            "welcome_card_text_color": "#ff0000",
            "welcome_card_ring": False,
            "welcome_card_badges": True,
        }
    )

    assert options.custom_bg_url == "https://cdn.example.com/welcome.png"
    assert options.width == 1024
    assert options.height == 500
    assert options.avatar_size == 248
    assert options.bg_blur == 0
    assert options.overlay_opacity == 0
    assert options.layout == "center"
    assert options.welcome_label == "WELCOME"
    assert options.text_color == 0xFFFFFF
    assert options.ring_enabled is True
    assert options.show_badges is False


def test_fixed_welcome_renderer_matches_reference_geometry() -> None:
    background = Image.new("RGBA", (1024, 500), (20, 40, 60, 255))
    avatar = Image.new("RGBA", (512, 512), (180, 25, 45, 255))

    png = _render_welcome_card_sync(
        background,
        avatar,
        None,
        [],
        (255, 255, 255),
        "IGNORED",
        "Surreny",
        "ignored",
        "Ignored Server",
        1337,
        WelcomeCardOptions(),
    )

    rendered = Image.open(io.BytesIO(png)).convert("RGBA")
    assert rendered.size == (1024, 500)
    assert rendered.getpixel((0, 0)) == (20, 40, 60, 255)
    assert rendered.getpixel((512, 45)) == (255, 255, 255, 255)
    assert rendered.getpixel((512, 175)) == (180, 25, 45, 255)

    headline = rendered.crop((250, 315, 775, 386))
    name = rendered.crop((250, 386, 775, 440))
    assert sum(1 for r, g, b, _ in headline.getdata() if r > 240 and g > 240 and b > 240) > 1_000
    assert sum(1 for r, g, b, _ in name.getdata() if r > 240 and g > 240 and b > 240) > 200
