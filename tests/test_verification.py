import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord

from cogs.verification import Verification, VerificationPanelLayout, WebsiteVerificationLayout
from utils.server_setup import apply_verification_gate


ROOT = Path(__file__).resolve().parents[1]


def test_website_mode_never_silently_falls_back_to_discord_captcha() -> None:
    source = (ROOT / "cogs" / "verification.py").read_text(encoding="utf-8")

    assert 'settings.get("verification_method") == "website"' in source
    assert '"Website Verification Unavailable"' in source
    assert "Cloudflare Turnstile" in source
    assert 'republish_panel = bool(gate_result.get("updated"))' in source
    assert 'await stale_panel.delete()' in source
    assert 'stale_panel.delete(reason=' not in source
    assert '"verification_panel_message_id": str(panel_message.id)' in source


class _PermissionChannel:
    def __init__(self, channel_id: int, name: str):
        self.id = channel_id
        self.name = name
        self._overwrites: dict[int, discord.PermissionOverwrite] = {}
        self.set_permissions = AsyncMock(side_effect=self._save_permissions)

    def overwrites_for(self, role):
        return self._overwrites.get(role.id, discord.PermissionOverwrite())

    async def _save_permissions(self, role, *, overwrite, reason):
        self._overwrites[role.id] = overwrite


class _PermissionGuild:
    def __init__(self, roles, channels):
        self._roles = {role.id: role for role in roles}
        self.channels = channels

    def get_role(self, role_id):
        return self._roles.get(role_id)


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
            ["Verify now", "How it works"],
        )
        self.assertEqual(
            [button.custom_id for button in buttons],
            ["verification:start", "verification:tutorial"],
        )

        text = _panel_text(view)
        self.assertIn("Unlock this server", text)
        self.assertIn("Complete one private security check", text)
        self.assertIn("No password", text)
        self.assertIn("Usually under a minute", text)


class VerificationRoleRepairTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_acknowledges_discord_before_member_lookup(self) -> None:
        state = {"acknowledged": False}

        async def defer_response(*, ephemeral, thinking):
            self.assertTrue(ephemeral)
            self.assertTrue(thinking)
            state["acknowledged"] = True

        response = SimpleNamespace(
            is_done=lambda: state["acknowledged"],
            defer=AsyncMock(side_effect=defer_response),
            send_message=AsyncMock(),
        )
        interaction = SimpleNamespace(
            guild=SimpleNamespace(id=999),
            response=response,
            edit_original_response=AsyncMock(),
        )
        cog = Verification.__new__(Verification)

        async def resolve_member(_interaction, *, guild_id):
            self.assertEqual(guild_id, 999)
            self.assertTrue(state["acknowledged"])
            return None, None

        cog._resolve_guild_member = AsyncMock(side_effect=resolve_member)

        await cog._start_captcha(
            interaction,
            regenerate=True,
            purpose="server",
        )

        response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
        response.send_message.assert_not_awaited()
        interaction.edit_original_response.assert_awaited_once()

    async def test_website_start_returns_the_secure_checkpoint_after_deferring(self) -> None:
        state = {"acknowledged": False}

        async def defer_response(*, ephemeral, thinking):
            state["acknowledged"] = True

        response = SimpleNamespace(
            is_done=lambda: state["acknowledged"],
            defer=AsyncMock(side_effect=defer_response),
            send_message=AsyncMock(),
        )
        interaction = SimpleNamespace(
            guild=SimpleNamespace(id=999),
            response=response,
            edit_original_response=AsyncMock(),
        )
        unverified_role = SimpleNamespace(id=456)
        verified_role = SimpleNamespace(id=789)
        guild = SimpleNamespace(id=999, name="Test Guild", icon=None, banner=None)
        member = SimpleNamespace(id=222, roles=[unverified_role])
        cog = Verification.__new__(Verification)
        cog._cooldowns = {}
        cog._resolve_guild_member = AsyncMock(return_value=(guild, member))
        cog._is_server_verification_enabled = AsyncMock(return_value=True)
        cog._get_roles = AsyncMock(return_value=(unverified_role, verified_role))
        cog._get_settings = AsyncMock(return_value={"verification_method": "website"})
        cog._website_verification_url = AsyncMock(
            return_value="https://docketbot.xyz/verify/signed-token"
        )

        await cog._start_captcha(
            interaction,
            regenerate=True,
            purpose="server",
        )

        response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
        response.send_message.assert_not_awaited()
        interaction.edit_original_response.assert_awaited_once()
        payload = interaction.edit_original_response.await_args.kwargs
        self.assertIsInstance(payload["view"], WebsiteVerificationLayout)

    async def test_verified_role_is_hidden_from_verification_channel(self) -> None:
        unverified_role = SimpleNamespace(id=456, name="Unverified")
        verified_role = SimpleNamespace(id=789, name="Verified")
        verify_channel = _PermissionChannel(100, "verify")
        welcome_channel = _PermissionChannel(101, "welcome")
        general_channel = _PermissionChannel(102, "general")
        guild = _PermissionGuild(
            [unverified_role, verified_role],
            [verify_channel, welcome_channel, general_channel],
        )

        result = await apply_verification_gate(guild, {
            "verification_enabled": True,
            "unverified_role": unverified_role.id,
            "verified_role": verified_role.id,
            "verify_channel": verify_channel.id,
            "welcome_channel": welcome_channel.id,
        })

        self.assertEqual(result["errors"], [])
        self.assertTrue(verify_channel.overwrites_for(unverified_role).view_channel)
        self.assertTrue(verify_channel.overwrites_for(unverified_role).read_message_history)
        self.assertFalse(verify_channel.overwrites_for(unverified_role).send_messages)
        self.assertFalse(verify_channel.overwrites_for(verified_role).view_channel)
        self.assertTrue(welcome_channel.overwrites_for(unverified_role).view_channel)
        self.assertTrue(welcome_channel.overwrites_for(unverified_role).read_message_history)
        self.assertIsNone(welcome_channel.overwrites_for(verified_role).view_channel)
        self.assertFalse(general_channel.overwrites_for(unverified_role).view_channel)
        self.assertIsNone(general_channel.overwrites_for(unverified_role).read_message_history)
        self.assertIsNone(general_channel.overwrites_for(verified_role).view_channel)

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

    async def test_successful_verification_atomically_replaces_waiting_role(self) -> None:
        guild = SimpleNamespace(id=999)
        everyone = SimpleNamespace(id=guild.id)
        regular_role = SimpleNamespace(id=111)
        waiting_role = SimpleNamespace(id=456)
        verified_role = SimpleNamespace(id=789)
        updated_member = SimpleNamespace(roles=[regular_role, verified_role])
        member = SimpleNamespace(
            id=222,
            guild=guild,
            roles=[everyone, regular_role, waiting_role],
            edit=AsyncMock(return_value=updated_member),
        )

        result = await Verification._apply_verified_roles(
            member,
            waiting_role,
            verified_role,
            reason="Verification captcha passed",
        )

        self.assertIs(result, updated_member)
        member.edit.assert_awaited_once()
        final_roles = member.edit.await_args.kwargs["roles"]
        self.assertEqual({role.id for role in final_roles}, {regular_role.id, verified_role.id})

    async def test_startup_reconciliation_removes_waiting_role_from_verified_members(self) -> None:
        waiting_role = SimpleNamespace(id=456)
        verified_role = SimpleNamespace(id=789)
        both = SimpleNamespace(
            id=222,
            roles=[waiting_role, verified_role],
            remove_roles=AsyncMock(),
        )
        waiting_only = SimpleNamespace(
            id=333,
            roles=[waiting_role],
            remove_roles=AsyncMock(),
        )
        guild = SimpleNamespace(id=999, members=[both, waiting_only])

        removed = await Verification._reconcile_verified_members(
            guild,
            waiting_role,
            verified_role,
        )

        self.assertEqual(removed, 1)
        both.remove_roles.assert_awaited_once_with(
            waiting_role,
            reason="Verification role reconciliation",
        )
        waiting_only.remove_roles.assert_not_awaited()

    async def test_startup_recreates_a_deleted_unverified_role(self) -> None:
        verified_role = SimpleNamespace(id=789, name="Memberms", managed=False)
        replacement_waiting_role = SimpleNamespace(id=456, name="Unverified", managed=False)
        guild = SimpleNamespace(
            id=999,
            roles=[verified_role],
            get_role=lambda role_id: verified_role if role_id == verified_role.id else None,
            create_role=AsyncMock(return_value=replacement_waiting_role),
        )
        database = SimpleNamespace(update_settings=AsyncMock())
        cog = Verification.__new__(Verification)
        cog.bot = SimpleNamespace(db=database)
        settings = {
            "verified_role": verified_role.id,
            "verification_role": verified_role.id,
            "unverified_role": 123,
        }

        unverified, verified = await cog._ensure_verification_roles(guild, settings)

        self.assertIs(unverified, replacement_waiting_role)
        self.assertIs(verified, verified_role)
        self.assertEqual(settings["unverified_role"], replacement_waiting_role.id)
        guild.create_role.assert_awaited_once()
        database.update_settings.assert_awaited_once_with(guild.id, settings)

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
