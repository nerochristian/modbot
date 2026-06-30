from __future__ import annotations

import unittest

from types import SimpleNamespace

from cogs.automod_setup import _extract_json_object, _setup_user_prompt, validate_automod_update


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
            [{"key": "bad_words", "question": "How should blocked words be handled?", "answer": "Common slurs only"}],
        )
        self.assertNotIn('"defaults"', prompt)
        self.assertNotIn('"nigger"', prompt)
        self.assertNotIn('"kill yourself"', prompt)
        self.assertIn('"schema"', prompt)


if __name__ == "__main__":
    unittest.main()
