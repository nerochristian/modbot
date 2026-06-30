from __future__ import annotations

import unittest
from datetime import timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from cogs.behavior_profiling import (
    DATABASE_MESSAGE_LIMIT,
    EMBED_DESCRIPTION_LIMIT,
    MAX_CONTEXT_CHARS,
    MAX_COLLECTED_MESSAGES,
    MAX_MESSAGE_CHARS,
    MAX_PROMPT_MESSAGES,
    MAX_PROMPT_SAMPLES,
    MAX_PROFILE_WORDS,
    BehaviorProfiling,
    ProfileCorpus,
    ProfileMessage,
    _build_prompt,
    _clean_profile_output,
    _coerce_message,
    _merge_messages,
    _normalize_content,
    _split_profile_pages,
)


class BehaviorProfilingHelpersTests(unittest.TestCase):
    def test_normalize_content_removes_controls_and_bounds_length(self) -> None:
        content = "  hello\x00\n\tworld  " + ("x" * MAX_MESSAGE_CHARS)

        normalized = _normalize_content(content)

        self.assertTrue(normalized.startswith("hello world "))
        self.assertEqual(len(normalized), MAX_MESSAGE_CHARS)
        self.assertTrue(normalized.endswith("…"))

    def test_coerce_message_supports_database_rows(self) -> None:
        message = _coerce_message(
            {
                "message_id": "123",
                "content": "  first\nsecond  ",
                "timestamp": "2026-06-30T12:00:00Z",
            }
        )

        self.assertIsNotNone(message)
        assert message is not None
        self.assertEqual(message.message_id, 123)
        self.assertEqual(message.content, "first second")
        self.assertEqual(message.created_at.tzinfo, timezone.utc)

    def test_merge_deduplicates_message_ids_and_keeps_newest_messages(self) -> None:
        tracked = [
            ProfileMessage(message_id=index, content=f"db-{index}")
            for index in range(1, 4)
        ]
        history = [
            ProfileMessage(message_id=3, content="history-3"),
            ProfileMessage(message_id=4, content="history-4"),
        ]

        merged = _merge_messages(tracked, history)

        self.assertEqual([message.message_id for message in merged], [1, 2, 3, 4])
        self.assertEqual(merged[2].content, "history-3")

    def test_profile_window_tracks_one_thousand_messages(self) -> None:
        self.assertEqual(DATABASE_MESSAGE_LIMIT, 1_000)
        self.assertEqual(MAX_COLLECTED_MESSAGES, 1_000)
        self.assertEqual(MAX_PROMPT_MESSAGES, 1_000)

    def test_prompt_is_bounded_and_samples_the_full_message_window(self) -> None:
        messages = [
            ProfileMessage(message_id=index, content=f"message-{index}-" + ("x" * 300))
            for index in range(1_000)
        ]

        prompt, count = _build_prompt(messages, "target-user")
        context = prompt.split("<message_excerpts>\n", 1)[1].split(
            "\n</message_excerpts>", 1
        )[0]

        self.assertLessEqual(len(context), MAX_CONTEXT_CHARS)
        self.assertEqual(count, MAX_PROMPT_SAMPLES)
        self.assertIn("target-user", prompt)
        self.assertIn("message-0-", context)
        self.assertIn("message-999-", context)

    def test_profile_output_removes_fences_neutralizes_mentions_and_caps_words(
        self,
    ) -> None:
        raw = (
            "```text\n@everyone "
            + " ".join(f"word-{index}" for index in range(1_000))
            + "\n```"
        )

        cleaned = _clean_profile_output(raw)

        self.assertNotIn("```", cleaned)
        self.assertIn("@\u200beveryone", cleaned)
        self.assertLessEqual(len(cleaned.split()), MAX_PROFILE_WORDS)

    def test_long_profile_splits_at_discord_safe_boundaries(self) -> None:
        profile = "\n\n".join(
            f"## Section {index}\n" + (f"detail-{index} " * 180)
            for index in range(6)
        )

        pages = _split_profile_pages(profile)

        self.assertGreater(len(pages), 1)
        self.assertTrue(all(len(page) <= EMBED_DESCRIPTION_LIMIT for page in pages))
        self.assertTrue(all(page.strip() for page in pages))

    def test_corpus_reports_combined_source(self) -> None:
        corpus = ProfileCorpus(messages=(), database_count=3, history_count=2)

        self.assertEqual(corpus.source_label, "tracked data + channel history")


class BehaviorProfilingAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_profile_uses_provider_interface_and_cleans_result(
        self,
    ) -> None:
        cog = BehaviorProfiling(SimpleNamespace())
        ai_client = SimpleNamespace(
            config=SimpleNamespace(model="configured-model"),
            _call=AsyncMock(return_value="```\n- Communication: calm\n```"),
        )

        result = await cog._generate_profile(ai_client, "prompt")

        self.assertEqual(result, "- Communication: calm")
        ai_client._call.assert_awaited_once()
        self.assertEqual(ai_client._call.await_args.kwargs["model"], "configured-model")
        self.assertEqual(ai_client._call.await_args.kwargs["max_tokens"], 1_800)
        self.assertTrue(ai_client._call.await_args.kwargs["long_answer"])

    async def test_cooldown_blocks_immediate_repeat(self) -> None:
        cog = BehaviorProfiling(SimpleNamespace())

        self.assertEqual(await cog._claim_cooldown(1, 2), 0.0)
        self.assertGreater(await cog._claim_cooldown(1, 2), 0.0)


if __name__ == "__main__":
    unittest.main()
