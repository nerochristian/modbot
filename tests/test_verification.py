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
        action_rows = [
            child for child in container.children
            if isinstance(child, discord.ui.ActionRow)
        ]
        self.assertEqual(len(action_rows), 1)
        buttons = action_rows[0].children
        self.assertEqual(
            [button.label for button in buttons],
            ["Start verification", "How it works"],
        )
        self.assertEqual(
            [button.custom_id for button in buttons],
            ["verification:start", "verification:tutorial"],
        )

        text = _panel_text(view)
        self.assertIn("Verification required", text)
        self.assertIn("### Welcome to this server", text)
        self.assertIn("Unlock your access", text)
        self.assertIn("No password", text)
        self.assertIn("Automatic access", text)
        self.assertIn("Single-use link", text)


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

    def test_existing_regular_member_is_selected_for_verification(self) -> None:
        waiting_role = SimpleNamespace(id=456)
        verified_role = SimpleNamespace(id=789)
        regular_role = SimpleNamespace(id=111)
        permissions = SimpleNamespace(
            administrator=False,
            manage_guild=False,
            manage_channels=False,
            moderate_members=False,
        )
        member = SimpleNamespace(
            id=222,
            bot=False,
            roles=[regular_role],
            guild_permissions=permissions,
        )

        self.assertTrue(Verification._member_needs_waiting_role(
            member,
            owner_id=999,
            unverified_role=waiting_role,
            verified_role=verified_role,
            staff_role_ids=set(),
        ))

    def test_existing_staff_member_is_not_selected_for_verification(self) -> None:
        waiting_role = SimpleNamespace(id=456)
        verified_role = SimpleNamespace(id=789)
        staff_role = SimpleNamespace(id=111)
        permissions = SimpleNamespace(
            administrator=False,
            manage_guild=False,
            manage_channels=False,
            moderate_members=True,
        )
        member = SimpleNamespace(
            id=222,
            bot=False,
            roles=[staff_role],
            guild_permissions=permissions,
        )

        self.assertFalse(Verification._member_needs_waiting_role(
            member,
            owner_id=999,
            unverified_role=waiting_role,
            verified_role=verified_role,
            staff_role_ids={staff_role.id},
        ))


if __name__ == "__main__":
    unittest.main()
