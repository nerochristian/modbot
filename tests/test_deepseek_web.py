import unittest
from unittest.mock import AsyncMock

from utils.deepseek_web import DeepSeekWebClient


class DeepSeekWebHelperTests(unittest.TestCase):
    def test_completion_stream_returns_final_content_and_source_urls(self) -> None:
        body = (
            b'data: {"v":{"results":[{"url":"https://example.com/page?q=1"}]}}\n'
            b'data: {"content":"Final answer[reference:4]"}\n'
            b'data: [DONE]\n'
        )

        answer, sources = DeepSeekWebClient._parse_completion_stream(body)

        self.assertEqual(answer, "Final answer")
        self.assertEqual(sources, ["https://example.com/page"])

    def test_limit_prompt_preserves_newest_and_oldest_context(self) -> None:
        prompt = "A" * 100 + "B" * 100

        result = DeepSeekWebClient._limit_prompt(prompt, limit=80)

        self.assertEqual(len(result), 80)
        self.assertTrue(result.startswith("A"))
        self.assertTrue(result.endswith("B"))
        self.assertIn("[older context trimmed]", result)

    def test_clean_answer_removes_citation_ui_artifacts(self) -> None:
        raw = (
            "markdown\nCopy\n**Answer**\n-\n2\n\n"
            "Released on June 10, 2026-.\n```"
        )

        result = DeepSeekWebClient._clean_answer(raw)

        self.assertEqual(result, "**Answer**\n\nReleased on June 10, 2026.")

    def test_challenge_detection_is_case_insensitive(self) -> None:
        self.assertTrue(
            DeepSeekWebClient._looks_like_challenge(
                "Checking your browser before accessing DeepSeek"
            )
        )
        self.assertFalse(
            DeepSeekWebClient._looks_like_challenge("Start chatting with Instant")
        )

    def test_clean_answer_spaces_research_sections(self) -> None:
        result = DeepSeekWebClient._clean_answer(
            "• **Origin and history**\nThe project began in 1985."
        )

        self.assertEqual(
            result,
            "• **Origin and history**\n\nThe project began in 1985.",
        )

    def test_browser_crash_detection_is_specific(self) -> None:
        self.assertTrue(
            DeepSeekWebClient._is_browser_crash_error(
                RuntimeError("Page.goto: Page crashed")
            )
        )
        self.assertFalse(
            DeepSeekWebClient._is_browser_crash_error(
                RuntimeError("Locator.evaluate: SyntaxError")
            )
        )

    def test_recycled_answer_node_is_detected_by_changed_text(self) -> None:
        self.assertTrue(
            DeepSeekWebClient._is_new_answer(
                before_count=2,
                before_fingerprint="Old answer",
                current_count=2,
                current_fingerprint="New answer",
            )
        )
        self.assertFalse(
            DeepSeekWebClient._is_new_answer(
                before_count=2,
                before_fingerprint="Old answer",
                current_count=2,
                current_fingerprint="Old answer",
            )
        )


class DeepSeekWebChatModeTests(unittest.IsolatedAsyncioTestCase):
    async def test_normal_chat_can_enable_search_without_deepthink(self) -> None:
        client = DeepSeekWebClient()
        client._run = AsyncMock(return_value="verified answer")

        result = await client.chat(
            "What is the current build?",
            session_key="guild:channel",
            continue_session=True,
            search=True,
        )

        self.assertEqual(result, "verified answer")
        call = client._run.await_args
        self.assertTrue(call.kwargs["search"])
        self.assertFalse(call.kwargs["deepthink"])
        self.assertTrue(call.kwargs["reuse_existing"])


if __name__ == "__main__":
    unittest.main()
