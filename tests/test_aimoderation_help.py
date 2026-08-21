"""The help gate.

``_HELP_RE`` used to be a bare ``\\b(help|commands)\\b``, which matched the word
anywhere in a message. ``_recover_tool_decision`` tested it *before* the
concrete action checks, so the help menu outranked real moderation commands:

    "help me ban @user"        -> command list, nobody banned
    "thanks for the help"      -> command list
    "i need help understanding" -> command list

The pattern is now scoped to actual requests for help, and the ordering in
``_recover_tool_decision`` puts concrete actions first as a second line of
defence.
"""
from __future__ import annotations

import pytest

from cogs.aimoderation.parsing import MessageParsingMixin


HELP_REQUESTS = [
    "help",
    "help!",
    "help?",
    "commands",
    "command",
    "cmds",
    "help me",
    "show me the commands",
    "list commands",
    "show help",
    "give me the help",
    "help menu",
    "command list",
    "what can you do",
    "how do i use you",
    "how do you work",
]

NOT_HELP_REQUESTS = [
    # The word appears, but the message is not asking for the menu.
    "thanks for the help",
    "thanks for the help!",
    "can you help me with something",
    "i need help understanding this",
    "he helped me a lot",
    "helpful tips please",
    "that was really helpful",
    "no help needed",
    # And an action request that merely mentions help must stay an action.
    "help me ban @user",
    "help me kick @user",
    "ban @user for being unhelpful",
]


@pytest.mark.parametrize("text", HELP_REQUESTS)
def test_help_requests_match(text):
    assert MessageParsingMixin._HELP_RE.search(text), f"help request missed: {text!r}"


@pytest.mark.parametrize("text", NOT_HELP_REQUESTS)
def test_incidental_help_mentions_do_not_match(text):
    assert not MessageParsingMixin._HELP_RE.search(text), f"false help match: {text!r}"


@pytest.mark.parametrize(
    "text", ["help me ban @user", "help me kick @user", "help me timeout @user 10m"]
)
def test_action_requests_that_say_help_are_still_actions(parser, text):
    """The action must win: showing a menu here silently drops the command."""
    assert parser._looks_like_mod_request(text), f"action lost to help: {text!r}"


def test_help_check_runs_after_action_checks_in_recovery():
    """Ordering guard for _recover_tool_decision.

    Asserted on source order because the function needs a live discord.Message
    to call. If the help branch ever moves back above the action branches, a
    loosened pattern silently eats moderation commands again.
    """
    import inspect

    from cogs.aimoderation.aimoderation import AIModeration

    source = inspect.getsource(AIModeration._recover_tool_decision)
    # Match the call itself, not the bare name -- the name also appears in the
    # explanatory comment above the action checks.
    help_at = source.index("self._HELP_RE.search")
    warn_at = source.index("self._looks_like_warning_action")
    assert warn_at < help_at, "_HELP_RE is tested before the concrete action checks"
