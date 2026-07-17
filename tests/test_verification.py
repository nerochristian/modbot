import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord

from cogs.verification import Verification, VerificationPanelLayout


def _panel_text(view: discord.ui.LayoutView) -> str:
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


class VerificationPanelTests(unittest.TestCase):
    def test_panel_is_a_polished_persistent_v2_flow(self) -> None:
        view = VerificationPanelLayout(SimpleNamespace(), guild=None)
        container = view.children[0]

        self.assertIsNone(view.timeout)
        self.assertIsInstance(container, discord.ui.Container)
        sections = [
            child for child in container.children
            if isinstance(child, discord.ui.Section)
        ]
        self.assertEqual(len(sections), 2)
        self.assertEqual(
            [section.accessory.label for section in sections],
            ["Verify me", "How it works"],
        )
        self.assertEqual(
            [section.accessory.custom_id for section in sections],
            ["verification:start", "verification:tutorial"],
        )

        text = _panel_text(view)
        self.assertIn("🔐 Member verification", text)
        self.assertIn("### Start your check", text)
        self.assertIn("### Need a hand?", text)
        self.assertIn("Private • One-time • Usually under a minute", text)


class VerificationRoleRepairTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_member_is_given_waiting_role_when_starting(self) -> None:
        waiting_role = SimpleNamespace(id=456)
        member = SimpleNamespace(roles=[], add_roles=AsyncMock())

        ready = await Verification._ensure_waiting_role(member, waiting_role)

        self.assertTrue(ready)
        member.add_roles.assert_awaited_once_with(
            waiting_role,
            reason="Verification started - assign waiting role",
        )

    async def test_existing_waiting_role_is_not_added_twice(self) -> None:
        waiting_role = SimpleNamespace(id=456)
        member = SimpleNamespace(roles=[waiting_role], add_roles=AsyncMock())

        ready = await Verification._ensure_waiting_role(member, waiting_role)

        self.assertTrue(ready)
        member.add_roles.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
