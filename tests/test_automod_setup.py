from __future__ import annotations

import asyncio
import unittest

from types import SimpleNamespace
from unittest.mock import patch

from cogs.automod_setup import (
    SetupReviewView,
    SetupProfile,
    call_deepseek_json,
    _extract_json_object,
    _modal_update_from_fields,
    _parse_generated_questions,
    _parse_profiles,
    _review_description,
    _setup_user_prompt,
    validate_automod_update,
)


class AutoModSetupValidationTests(unittest.TestCase):
    def test_extract_json_object_accepts_fenced_model_output(self) -> None:
        self.assertEqual(
            _extract_json_object('```json\n{"settings": {"automod_enabled": true}}\n```'),
            {"settings": {"automod_enabled": True}},
        )

    def test_validate_update_drops_unknown_keys_and_bounds_numbers(self) -> None:
        update = validate_automod_update(
            {
                "settings": {
                    "automod_enabled": "yes",
                    "automod_spam_threshold": 4,
                    "automod_spam_window": 999,
                    "automod_punishment": "mute",
                    "not_a_setting": True,
                }
            }
        )
        self.assertEqual(
            update,
            {
                "automod_enabled": True,
                "automod_spam_threshold": 4,
                "automod_punishment": "timeout",
            },
        )

    def test_validate_update_normalizes_lists(self) -> None:
        update = validate_automod_update(
            {
                "automod_badwords": [" Bad Phrase ", "bad phrase", "x", "none"],
                "automod_whitelisted_domains": ["HTTPS://WWW.Example.COM/path", "bad domain"],
                "automod_allowed_invites": ["https://discord.gg/Alpha", "Alpha"],
            }
        )
        self.assertEqual(update["automod_badwords"], ["bad phrase"])
        self.assertEqual(update["automod_whitelisted_domains"], ["www.example.com", "bad domain"])
        self.assertEqual(update["automod_allowed_invites"], ["alpha"])

    def test_validate_update_rejects_empty_valid_payload(self) -> None:
        with self.assertRaises(ValueError):
            validate_automod_update({"settings": {"not_a_setting": True}})

    def test_setup_prompt_does_not_send_default_bad_word_list(self) -> None:
        prompt = _setup_user_prompt(
            SimpleNamespace(id=1, name="Test Guild", member_count=100),
            "Stop raids and scam links",
            SetupProfile(name="Balanced Security", description="Balanced profile", focus="Scams and raids"),
            [{"key": "bad_words", "question": "How should blocked words be handled?", "answer": "Common slurs only"}],
        )
        self.assertNotIn('"defaults"', prompt)
        self.assertNotIn('"nigger"', prompt)
        self.assertNotIn('"kill yourself"', prompt)
        self.assertIn('"schema"', prompt)
        self.assertIn('"selected_profile"', prompt)

    def test_parse_profiles_requires_three_distinct_profiles(self) -> None:
        profiles = _parse_profiles(
            {
                "profiles": [
                    {"name": "Light", "description": "Mostly logs problems.", "focus": "Low friction"},
                    {"name": "Balanced", "description": "Stops scams and spam.", "focus": "General safety"},
                    {"name": "Strict", "description": "Locks down raids.", "focus": "High security"},
                ]
            }
        )
        self.assertEqual([profile.name for profile in profiles], ["Light", "Balanced", "Strict"])

    def test_parse_generated_questions_requires_mostly_closed_questions(self) -> None:
        payload = {
            "questions": [
                {"key": "spam", "question": "How strict should spam be?", "type": "choice", "options": ["Light", "Normal", "Strict"]},
                {"key": "links", "question": "How should links work?", "type": "choice", "options": ["Dangerous only", "Allowlist", "Block most"]},
                {"key": "invites", "question": "How should invites work?", "type": "choice", "options": ["Block", "Allow approved"]},
                {"key": "raids", "question": "Watch new accounts?", "type": "choice", "options": ["Off", "3 days", "7 days"]},
                {"key": "mentions", "question": "Mass mention limit?", "type": "choice", "options": ["3", "5", "8"]},
                {"key": "punish", "question": "Default action?", "type": "choice", "options": ["Warn", "Timeout"]},
                {"key": "security", "question": "Scam action?", "type": "choice", "options": ["Timeout", "Ban"]},
                {"key": "custom", "question": "Any exact words?", "type": "text"},
            ]
        }
        questions = _parse_generated_questions(payload)
        self.assertEqual(len(questions), 8)
        self.assertGreaterEqual(sum(question.is_closed for question in questions), 7)

    def test_review_description_surfaces_editable_panels(self) -> None:
        description = _review_description(
            {
                "automod_badwords_enabled": True,
                "automod_badwords": ["custombad"],
                "automod_links_enabled": True,
                "automod_links_mode": "allowlist",
                "automod_links_whitelist": ["youtube.com"],
                "automod_whitelisted_domains": ["discord.com"],
                "automod_invites_enabled": True,
                "automod_allowed_invites": ["abc123"],
                "automod_scam_protection": True,
                "automod_spam_threshold": 4,
                "automod_spam_window": 8,
                "automod_max_mentions": 3,
                "automod_punishment": "warn",
                "automod_security_punishment": "timeout",
            },
            "Generated setup.",
        )

        self.assertIn("Review the generated setup", description)
        self.assertIn("**Blocked Words**", description)
        self.assertIn("custombad", description)
        self.assertIn("**Links**", description)
        self.assertIn("youtube.com", description)
        self.assertIn("**Invites and Security**", description)
        self.assertIn("abc123", description)
        self.assertIn("**Limits and Actions**", description)

    def test_review_view_has_expected_setup_buttons(self) -> None:
        view = SetupReviewView(1, {}, {}, "summary")
        labels = [getattr(item, "label", None) for item in view.children]

        self.assertIn("Blocked Words", labels)
        self.assertIn("Links", labels)
        self.assertIn("Invites", labels)
        self.assertIn("Limits", labels)
        self.assertIn("Actions", labels)
        self.assertIn("Save Setup", labels)

    def test_modal_update_from_fields_validates_review_edits(self) -> None:
        update = _modal_update_from_fields(
            {
                "automod_badwords_enabled": "off",
                "automod_badwords": "custombad\ncustombad\nx",
                "automod_links_mode": "allowlist",
                "automod_links_whitelist": "https://www.youtube.com/watch?v=1\nx.com",
                "automod_spam_threshold": "6",
            }
        )

        self.assertEqual(update["automod_badwords_enabled"], False)
        self.assertEqual(update["automod_badwords"], ["custombad"])
        self.assertEqual(update["automod_links_mode"], "allowlist")
        self.assertEqual(update["automod_links_whitelist"], ["www.youtube.com", "x.com"])
        self.assertEqual(update["automod_spam_threshold"], 6)


class AutoModSetupAITests(unittest.IsolatedAsyncioTestCase):
    async def test_call_deepseek_json_passes_web_session_identity(self) -> None:
        class WorkingWeb:
            enabled = True

            async def chat(self, prompt, **kwargs):
                self.prompt = prompt
                self.kwargs = kwargs
                return '{"ok": true}'

        web = WorkingWeb()
        cog = SimpleNamespace(
            bot=SimpleNamespace(
                get_cog=lambda name: SimpleNamespace(ai=SimpleNamespace(_deepseek_web=web)) if name == "AIModeration" else None
            )
        )

        payload = await call_deepseek_json(
            cog,
            "system",
            "user",
            session_key="automod-setup:1:2",
            session_name="Test AutoMod setup",
        )

        self.assertEqual(payload, {"ok": True})
        self.assertEqual(web.kwargs["session_key"], "automod-setup:1:2")
        self.assertEqual(web.kwargs["session_name"], "Test AutoMod setup")

    async def test_call_deepseek_json_falls_back_to_digitalocean_when_web_fails(self) -> None:
        class BrokenWeb:
            enabled = True

            async def chat(self, *args, **kwargs):
                raise RuntimeError("DeepSeek browser failure: Error")

        class FakeAI:
            _deepseek_web = BrokenWeb()

            async def _call_digitalocean(self, messages, *, temperature, max_tokens, json_mode):
                self.messages = messages
                self.temperature = temperature
                self.max_tokens = max_tokens
                self.json_mode = json_mode
                return '{"profiles": [{"name": "Safe", "description": "Blocks scams.", "focus": "Security"}]}'

        fake_ai = FakeAI()
        cog = SimpleNamespace(
            bot=SimpleNamespace(
                get_cog=lambda name: SimpleNamespace(ai=fake_ai) if name == "AIModeration" else None
            )
        )

        payload = await call_deepseek_json(cog, "system", "user", max_tokens=500)

        self.assertEqual(payload["profiles"][0]["name"], "Safe")
        self.assertTrue(fake_ai.json_mode)
        self.assertEqual(fake_ai.max_tokens, 500)

    async def test_call_deepseek_json_falls_back_when_web_stalls(self) -> None:
        class StalledWeb:
            enabled = True

            async def chat(self, *args, **kwargs):
                await asyncio.sleep(1)
                return '{"ok": false}'

        class FakeAI:
            _deepseek_web = StalledWeb()

            async def _call_digitalocean(self, messages, *, temperature, max_tokens, json_mode):
                self.messages = messages
                self.temperature = temperature
                self.max_tokens = max_tokens
                self.json_mode = json_mode
                return '{"ok": true}'

        fake_ai = FakeAI()
        cog = SimpleNamespace(
            bot=SimpleNamespace(
                get_cog=lambda name: SimpleNamespace(ai=fake_ai) if name == "AIModeration" else None
            )
        )

        with patch.dict("os.environ", {"DEEPSEEK_WEB_PRIMARY_TIMEOUT": "0.1"}):
            payload = await call_deepseek_json(cog, "system", "user", max_tokens=500)

        self.assertEqual(payload, {"ok": True})
        self.assertTrue(fake_ai.json_mode)
        self.assertEqual(fake_ai.max_tokens, 500)


if __name__ == "__main__":
    unittest.main()
