import unittest
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, MagicMock

from utils.deepseek_web import DeepSeekWebClient


class DeepSeekWebHelperTests(unittest.TestCase):
    def test_completion_stream_exposes_metadata_and_source_urls(self) -> None:
        body = (
            b'data: {"v":{"results":[{"url":"https://example.com/page?q=1"}]}}\n'
            b'data: {"content":"Generated conversation title"}\n'
            b'data: [DONE]\n'
        )

        metadata, sources = DeepSeekWebClient._parse_completion_stream(body)

        self.assertEqual(metadata, "Generated conversation title")
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
    async def test_vision_uses_named_channel_session(self) -> None:
        client = DeepSeekWebClient()
        client._run = AsyncMock(return_value="image answer")

        result = await client.vision(
            "What is this?",
            [("image.png", "image/png", b"image")],
            session_key="guild:channel:vision",
            session_name="Soul -> General [Vision]",
        )

        self.assertEqual(result, "image answer")
        call = client._run.await_args
        self.assertEqual(call.kwargs["lane"], "chat:guild:channel:vision")
        self.assertEqual(call.kwargs["ui_mode"], "Vision")
        self.assertTrue(call.kwargs["reuse_existing"])
        self.assertEqual(call.kwargs["session_name"], "Soul -> General [Vision]")

    async def test_image_upload_skips_obsolete_vision_handoff(self) -> None:
        client = DeepSeekWebClient()
        page = MagicMock()
        file_input = MagicMock()
        page.locator.return_value = file_input
        file_input.count = AsyncMock(return_value=1)
        file_input.first.set_input_files = AsyncMock()
        client._wait_for_image_ready = AsyncMock()

        await client._attach_images(
            page,
            [("image.png", "image/png", b"image")],
        )

        file_input.first.set_input_files.assert_awaited_once()
        client._wait_for_image_ready.assert_awaited_once_with(page)
        page.get_by_text.assert_not_called()

    async def test_image_upload_waits_for_enabled_send_button(self) -> None:
        client = DeepSeekWebClient()
        page = MagicMock()
        ready_button = MagicMock()
        page.locator.return_value.first = ready_button
        ready_button.wait_for = AsyncMock()

        await client._wait_for_image_ready(page)

        page.locator.assert_called_once_with(
            "div.ds-button--primary.ds-button--circle"
            ":not(.ds-button--disabled)"
        )
        ready_button.wait_for.assert_awaited_once_with(
            state="visible",
            timeout=30_000,
        )

    async def test_restored_vision_chat_does_not_click_header_label(self) -> None:
        client = DeepSeekWebClient()
        client._set_mode = AsyncMock()
        page = MagicMock()
        page.url = "https://chat.deepseek.com/a/chat/s/abc1234567890-def"

        await client._configure_request_mode(
            page,
            ui_mode="Vision",
            reuse_existing=True,
        )

        client._set_mode.assert_not_awaited()

    async def test_new_vision_chat_selects_vision_mode(self) -> None:
        client = DeepSeekWebClient()
        client._set_mode = AsyncMock()
        page = MagicMock()
        page.url = "https://chat.deepseek.com/"

        await client._configure_request_mode(
            page,
            ui_mode="Vision",
            reuse_existing=True,
        )

        client._set_mode.assert_awaited_once_with(page, "Vision")

    async def test_image_prompt_is_filled_before_file_upload(self) -> None:
        client = DeepSeekWebClient()
        events: list[str] = []
        textbox = MagicMock()
        textbox.fill = AsyncMock(side_effect=lambda _: events.append("prompt"))
        client._attach_images = AsyncMock(
            side_effect=lambda *_args, **_kwargs: events.append("image")
        )

        await client._prepare_image_submission(
            MagicMock(),
            textbox,
            "What is this?",
            [("image.png", "image/png", b"image")],
        )

        self.assertEqual(events, ["prompt", "image"])

    async def test_image_submission_clicks_primary_send_button(self) -> None:
        client = DeepSeekWebClient()
        page = MagicMock()
        textbox = MagicMock()
        candidates = MagicMock()
        send_button = MagicMock()
        page.locator.return_value = candidates
        candidates.count = AsyncMock(return_value=1)
        candidates.nth.return_value = send_button
        send_button.is_visible = AsyncMock(return_value=True)
        send_button.click = AsyncMock()
        textbox.press = AsyncMock()

        await client._submit_prompt(
            page,
            textbox,
            has_images=True,
        )

        send_button.click.assert_awaited_once_with(timeout=5_000)
        textbox.press.assert_not_awaited()

    async def test_cookie_consent_uses_necessary_only_and_persists(self) -> None:
        client = DeepSeekWebClient()
        page = MagicMock()
        candidates = MagicMock()
        button = MagicMock()
        context = MagicMock()
        client._context = context
        page.get_by_text.return_value = candidates
        candidates.count = AsyncMock(return_value=1)
        candidates.nth.return_value = button
        candidates.first.wait_for = AsyncMock()
        button.is_visible = AsyncMock(return_value=True)
        button.click = AsyncMock()
        context.storage_state = AsyncMock()

        await client._ensure_cookie_choice(page)

        button.click.assert_awaited_once_with(timeout=5_000)
        context.storage_state.assert_awaited_once_with(
            path=str(client.storage_state_path)
        )

    async def test_current_chat_is_renamed_from_sidebar_menu(self) -> None:
        client = DeepSeekWebClient()
        page = MagicMock()
        page.url = "https://chat.deepseek.com/a/chat/s/abc1234567890-def"
        link = MagicMock()
        menu_button = MagicMock()
        rename_candidates = MagicMock()
        rename_option = MagicMock()
        input_candidates = MagicMock()
        rename_input = MagicMock()

        def locator(selector: str) -> MagicMock:
            if selector.startswith('a[href='):
                return link
            if selector.startswith("input.ds-input__input"):
                return input_candidates
            raise AssertionError(f"Unexpected selector: {selector}")

        page.locator.side_effect = locator
        page.get_by_text.return_value = rename_candidates
        page.wait_for_function = AsyncMock()
        link.count = AsyncMock(return_value=1)
        link.is_visible = AsyncMock(return_value=True)
        link.hover = AsyncMock()
        link.locator.return_value = menu_button
        menu_button.count = AsyncMock(return_value=1)
        menu_button.click = AsyncMock()
        rename_candidates.count = AsyncMock(return_value=1)
        rename_candidates.nth.return_value = rename_option
        rename_option.is_visible = AsyncMock(return_value=True)
        rename_option.click = AsyncMock()
        input_candidates.count = AsyncMock(return_value=1)
        input_candidates.nth.return_value = rename_input
        rename_input.is_visible = AsyncMock(return_value=True)
        rename_input.fill = AsyncMock()
        rename_input.press = AsyncMock()

        renamed = await client._rename_current_chat(page, "Soul -> General")

        self.assertTrue(renamed)
        rename_input.fill.assert_awaited_once_with("Soul -> General")
        rename_input.press.assert_awaited_once_with("Enter")

    async def test_fast_copy_uses_new_rendered_assistant_message(self) -> None:
        client = DeepSeekWebClient()
        page = MagicMock()
        answers = MagicMock()
        latest = MagicMock()
        page.locator.return_value = answers
        answers.count = AsyncMock(return_value=2)
        answers.nth.return_value = latest
        latest.inner_text = AsyncMock(
            return_value="Anomaly Hospital released on December 20, 2024."
        )
        client._extract_answer = AsyncMock(
            return_value=(
                "Anomaly Hospital released on December 20, 2024.",
                ["https://www.roblox.com/games/example"],
            )
        )

        answer, sources = await client._copy_rendered_answer(
            page,
            before_count=1,
            before_fingerprint="Previous answer",
        )

        self.assertEqual(
            answer,
            "Anomaly Hospital released on December 20, 2024.",
        )
        self.assertEqual(sources, ["https://www.roblox.com/games/example"])

    async def test_channel_chat_always_reuses_named_session(self) -> None:
        client = DeepSeekWebClient()
        client._run = AsyncMock(return_value="verified answer")

        result = await client.chat(
            "What is the current build?",
            session_key="guild:channel",
            session_name="Soul -> General",
            continue_session=False,
            search=True,
        )

        self.assertEqual(result, "verified answer")
        call = client._run.await_args
        self.assertTrue(call.kwargs["search"])
        self.assertFalse(call.kwargs["deepthink"])
        self.assertTrue(call.kwargs["reuse_existing"])
        self.assertEqual(call.kwargs["session_name"], "Soul -> General")

    def test_channel_session_index_round_trips_only_safe_urls(self) -> None:
        with TemporaryDirectory() as directory:
            client = DeepSeekWebClient()
            client.session_index_path = client.session_index_path.__class__(
                directory
            ) / "sessions.json"
            client._channel_sessions = {
                "1:2": {
                    "url": "https://chat.deepseek.com/a/chat/s/abc1234567890-def",
                    "name": "Soul -> General",
                    "renamed": True,
                },
                "unsafe": {
                    "url": "https://example.com/a/chat/s/abc1234567890-def",
                    "name": "Bad",
                    "renamed": True,
                },
            }
            client._write_channel_sessions()

            loaded = client._load_channel_sessions()

        self.assertEqual(set(loaded), {"1:2"})
        self.assertEqual(loaded["1:2"]["name"], "Soul -> General")


if __name__ == "__main__":
    unittest.main()
