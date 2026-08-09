"""Guards the late-bound configuration contract.

These tests exist because the failure they prevent is silent. If provider code
snapshots a config constant via ``from .ai_client import _OPENROUTER_API_KEY``,
the suite's 83 ``monkeypatch.setattr(ai_client_module, ...)`` sites mutate a
name nobody reads -- so tests keep passing while the code under test talks to
the real environment with real credentials.
"""
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from cogs.aimoderation import settings
from cogs.aimoderation import ai_client as ai_client_module

PACKAGE_DIR = Path(ai_client_module.__file__).parent

# Names whose values the suite reconfigures by patching the ai_client module.
# Reading any of these through a from-import defeats those patches.
PATCHED_CONFIG_NAMES = frozenset(
    {
        "_OPENROUTER_API_KEY",
        "_OPENROUTER_BASE_URL",
        "_OPENROUTER_CHAT_MODEL",
        "_OPENROUTER_TALK_CHAT_MODEL",
        "_OPENROUTER_CHAT_DISABLE_REASONING",
        "_RELAYROUTER_API_KEY",
        "_RELAYROUTER_BASE_URL",
        "_RELAYROUTER_VISION_MODEL",
        "_AIMODEL_API_KEY",
        "_AIMODEL_BASE_URL",
        "_AIMODEL_CONVERSATION_API_KEY",
        "_AIMODEL_CONVERSATION_MODEL",
        "_DEEPSEEK_API_KEY",
        "_DEEPSEEK_API_MODEL",
        "_DO_API_KEY",
        "_DO_BASE_URL",
        "_deepseek_api_enabled",
    }
)


class LateBoundSettingsTests(unittest.TestCase):
    def test_setting_reflects_patches_applied_to_ai_client(self) -> None:
        with patch.object(ai_client_module, "_OPENROUTER_API_KEY", "patched-key"):
            self.assertEqual(
                settings.setting("_OPENROUTER_API_KEY"),
                "patched-key",
            )
        # And returns to the real module value once the patch is lifted.
        self.assertEqual(
            settings.setting("_OPENROUTER_API_KEY"),
            ai_client_module._OPENROUTER_API_KEY,
        )

    def test_call_reflects_patched_predicates(self) -> None:
        with patch.object(
            ai_client_module,
            "_deepseek_api_enabled",
            return_value=True,
        ):
            self.assertTrue(settings.call("_deepseek_api_enabled"))
        with patch.object(
            ai_client_module,
            "_deepseek_api_enabled",
            return_value=False,
        ):
            self.assertFalse(settings.call("_deepseek_api_enabled"))

    def test_setting_supports_defaults_for_optional_names(self) -> None:
        self.assertEqual(
            settings.setting("_NOT_A_REAL_SETTING", "fallback"),
            "fallback",
        )
        with self.assertRaises(AttributeError):
            settings.setting("_NOT_A_REAL_SETTING")

    def test_every_late_bound_name_still_exists_on_ai_client(self) -> None:
        """Fail if a config name read by ``providers/`` was deleted.

        Provider lanes resolve configuration by string at call time, so these
        names have no textual reference left in ai_client.py. A linter or
        "find usages" sweep reports them unused, and deleting one breaks that
        lane at runtime while static analysis stays silent. This test is the
        thing that makes such a deletion fail loudly instead.
        """
        pattern = re.compile(
            r"settings\.(?:setting|call)\(\s*[\"'](_[A-Za-z0-9_]+)[\"']"
        )
        referenced: dict[str, set[str]] = {}
        for path in sorted((PACKAGE_DIR / "providers").glob("*.py")):
            for name in pattern.findall(path.read_text(encoding="utf-8")):
                referenced.setdefault(name, set()).add(path.name)

        self.assertTrue(referenced, "expected provider modules to read settings")

        missing = sorted(
            f"{name} (read by {', '.join(sorted(files))})"
            for name, files in referenced.items()
            if not hasattr(ai_client_module, name)
        )
        self.assertEqual(
            missing,
            [],
            "These names are read late-bound by provider lanes but no longer "
            "exist on ai_client; restore them or update the readers:\n  "
            + "\n  ".join(missing),
        )

    def test_no_sibling_module_snapshots_patched_config(self) -> None:
        """Fail loudly if a module from-imports a patched config name.

        This is the regression guard: such an import binds a snapshot, so the
        suite's patches stop reaching the code that reads it, and provider
        tests would pass while hitting the real environment.
        """
        offenders: list[str] = []
        for path in sorted(PACKAGE_DIR.glob("**/*.py")):
            if path.name in {"ai_client.py", "settings.py"}:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                if not (node.module or "").endswith("ai_client"):
                    continue
                for alias in node.names:
                    if alias.name in PATCHED_CONFIG_NAMES:
                        offenders.append(
                            f"{path.name}:{node.lineno} imports {alias.name}"
                        )

        self.assertEqual(
            offenders,
            [],
            "Read these through settings.setting()/settings.call() instead; a "
            "from-import snapshots the value and silently defeats the test "
            "suite's patches:\n  " + "\n  ".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
