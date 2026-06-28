import unittest

from utils.deepseek_web import DeepSeekWebClient


class DeepSeekWebHelperTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
