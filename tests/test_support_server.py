import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

import discord

from cogs.support_server import (
    SUPPORT_TICKET_OPTIONS,
    SupportRequestPanelView,
    _ticket_option_for_storage,
    build_rules_view,
    build_status_view,
    build_welcome_view,
)


def _container_text(view: discord.ui.LayoutView) -> str:
    container = view.children[0]
    parts: list[str] = []
    for child in container.children:
        if isinstance(child, discord.ui.TextDisplay):
            parts.append(child.content)
        elif isinstance(child, discord.ui.Section):
            parts.extend(
                item.content
                for item in child.children
                if isinstance(item, discord.ui.TextDisplay)
            )
    return "\n".join(parts)


class SupportServerViewTests(unittest.TestCase):
    def test_welcome_panel_uses_heading_and_subtext_hierarchy(self) -> None:
        view = build_welcome_view("Docket Support")
        container = view.children[0]

        self.assertIsInstance(view, discord.ui.LayoutView)
        self.assertIsInstance(container, discord.ui.Container)
        self.assertIsInstance(container.children[0], discord.ui.MediaGallery)
        text = _container_text(view)
        self.assertIn("### Welcome to Docket Support", text)
        self.assertIn("## Docket support starts here", text)
        self.assertIn("-# Find answers", text)
        self.assertIn("## 🧭 Start here", text)

    def test_rules_panel_contains_security_and_ticket_guidance(self) -> None:
        text = _container_text(build_rules_view())

        self.assertIn("## 📜 Docket Support Rules", text)
        self.assertIn("Use the correct support channel", text)
        self.assertIn("Remove tokens and private data first", text)
        self.assertIn("Staff will never ask for your bot token", text)

    def test_ticket_workflows_have_valid_modal_contracts(self) -> None:
        self.assertEqual([option["id"] for option in SUPPORT_TICKET_OPTIONS], ["general", "bug", "feature"])
        for option in SUPPORT_TICKET_OPTIONS:
            stored = _ticket_option_for_storage(option)
            self.assertEqual(set(stored), {"id", "label", "description", "emoji", "questions"})
            self.assertGreaterEqual(len(stored["questions"]), 2)
            self.assertLessEqual(len(stored["questions"]), 5)

    def test_ticket_panels_are_persistent_beautiful_v2_cards(self) -> None:
        tickets_cog = SimpleNamespace()
        view = SupportRequestPanelView(tickets_cog, SUPPORT_TICKET_OPTIONS[1])
        container = view.children[0]
        action_rows = [
            child for child in container.children
            if isinstance(child, discord.ui.ActionRow)
        ]

        self.assertIsNone(view.timeout)
        self.assertEqual(len(action_rows), 1)
        select = action_rows[0].children[0]
        self.assertEqual(select.custom_id, "docket:support-ticket:bug")
        self.assertEqual(select.placeholder, "Report a bug…")
        self.assertIn("## 🐛 Bug Reports", _container_text(view))
        self.assertIn("-# Complete the form below", _container_text(view))

    def test_status_panel_reports_live_connection_metadata(self) -> None:
        bot = SimpleNamespace(
            start_time=datetime.now(timezone.utc),
            latency=0.042,
            version="3.4.0",
            user=SimpleNamespace(
                display_avatar=SimpleNamespace(url="https://example.com/docket.png")
            ),
        )
        view = build_status_view(bot)
        text = _container_text(view)

        self.assertIn("## 🟢 All systems operational", text)
        self.assertIn("Gateway latency: **42 ms**", text)
        self.assertIn("Version: **3.4.0**", text)


if __name__ == "__main__":
    unittest.main()
