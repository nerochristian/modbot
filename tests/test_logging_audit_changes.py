import unittest
from types import SimpleNamespace

import discord

from cogs.logging_cog import Logging


class AuditChangeFormattingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.logging = object.__new__(Logging)

    def test_diff_proxies_show_role_changes(self) -> None:
        before_permissions = discord.Permissions.none()
        after_permissions = discord.Permissions.none()
        after_permissions.update(view_channel=True, manage_roles=True)
        entry = SimpleNamespace(
            changes=SimpleNamespace(
                before=SimpleNamespace(
                    name="VIP",
                    colour=discord.Colour.red(),
                    hoist=False,
                    mentionable=False,
                    permissions=before_permissions,
                ),
                after=SimpleNamespace(
                    name="Premium VIP",
                    colour=discord.Colour.blue(),
                    hoist=True,
                    mentionable=True,
                    permissions=after_permissions,
                ),
            )
        )

        lines = self.logging._audit_change_lines(entry)

        self.assertIn("**Name:** VIP → Premium VIP", lines)
        self.assertIn("**Color:** #e74c3c → #3498db", lines)
        self.assertIn("**Displayed separately:** No → Yes", lines)
        self.assertIn("**Mentionable:** No → Yes", lines)
        permission_line = next(line for line in lines if line.startswith("**Permissions changed:**"))
        self.assertIn("View Channels", permission_line)
        self.assertIn("Manage Roles", permission_line)

    def test_duplicate_colour_alias_is_only_reported_once(self) -> None:
        before = discord.Colour.red()
        after = discord.Colour.green()
        entry = SimpleNamespace(
            changes=SimpleNamespace(
                before=SimpleNamespace(colour=before, color=before),
                after=SimpleNamespace(colour=after, color=after),
            )
        )

        lines = self.logging._audit_change_lines(entry)

        self.assertEqual(lines, ["**Color:** #e74c3c → #2ecc71"])


if __name__ == "__main__":
    unittest.main()
