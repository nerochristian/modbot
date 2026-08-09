"""Regression guards for the converse() prologue stages.

These cover ``_load_conversation_memory`` and ``_describe_source_channel``,
extracted from ``converse()``. The memory test exists because of a real bug
introduced during that extraction: loading user and guild memory under a single
``try``/``except`` silently discarded the user's profile whenever the guild read
failed, so a partially-working database dropped memory from both the prompt and
the memory-update call. The full-suite test that caught it asserts through
``converse()``; this pins the behavior directly at the seam.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from cogs.aimoderation.ai_client import AIClient


def _client(db: object) -> AIClient:
    client = AIClient.__new__(AIClient)
    client.bot = SimpleNamespace(db=db)
    return client


class LoadConversationMemoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_both_memories_when_database_is_healthy(self) -> None:
        client = _client(
            SimpleNamespace(
                get_ai_memory=AsyncMock(return_value="USER"),
                get_guild_memory=AsyncMock(return_value="GUILD"),
            )
        )

        user_memory, guild_memory = await client._load_conversation_memory(
            SimpleNamespace(id=2),
            SimpleNamespace(id=1),
        )

        self.assertEqual((user_memory, guild_memory), ("USER", "GUILD"))

    async def test_guild_memory_failure_preserves_user_memory(self) -> None:
        """A partial database must not discard the memory it *can* serve.

        Guarding both reads with one try/except loses the already-fetched user
        memory when the guild read raises, which drops the user's profile from
        the prompt and from _update_memory_smart's stored-memory argument.
        """
        client = _client(
            SimpleNamespace(
                get_ai_memory=AsyncMock(return_value="USER"),
                get_guild_memory=AsyncMock(side_effect=RuntimeError("no table")),
            )
        )

        user_memory, guild_memory = await client._load_conversation_memory(
            SimpleNamespace(id=2),
            SimpleNamespace(id=1),
        )

        self.assertEqual(user_memory, "USER")
        self.assertEqual(guild_memory, "")

    async def test_missing_guild_memory_attribute_is_tolerated(self) -> None:
        # Mirrors fakes that only implement get_ai_memory.
        client = _client(SimpleNamespace(get_ai_memory=AsyncMock(return_value="USER")))

        user_memory, guild_memory = await client._load_conversation_memory(
            SimpleNamespace(id=2),
            SimpleNamespace(id=1),
        )

        self.assertEqual((user_memory, guild_memory), ("USER", ""))

    async def test_user_memory_failure_still_returns_guild_memory(self) -> None:
        client = _client(
            SimpleNamespace(
                get_ai_memory=AsyncMock(side_effect=RuntimeError("boom")),
                get_guild_memory=AsyncMock(return_value="GUILD"),
            )
        )

        user_memory, guild_memory = await client._load_conversation_memory(
            SimpleNamespace(id=2),
            SimpleNamespace(id=1),
        )

        self.assertEqual((user_memory, guild_memory), ("", "GUILD"))

    async def test_absent_database_yields_empty_memories(self) -> None:
        client = _client(None)

        self.assertEqual(
            await client._load_conversation_memory(
                SimpleNamespace(id=2),
                SimpleNamespace(id=1),
            ),
            ("", ""),
        )


class DescribeSourceChannelTests(unittest.TestCase):
    def test_renders_name_id_and_truncated_topic(self) -> None:
        message = SimpleNamespace(
            channel=SimpleNamespace(name="general", id=42, topic="t" * 600)
        )

        described = AIClient._describe_source_channel(message)

        self.assertTrue(described.startswith("#general (ID 42) | Topic: "))
        self.assertEqual(described.count("t"), 500)

    def test_returns_empty_string_without_a_channel(self) -> None:
        self.assertEqual(AIClient._describe_source_channel(None), "")
        self.assertEqual(
            AIClient._describe_source_channel(SimpleNamespace(channel=None)),
            "",
        )


if __name__ == "__main__":
    unittest.main()
