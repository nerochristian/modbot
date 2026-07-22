"""Generated 1,000-case natural-language action routing and review matrix."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from cogs.aimoderation import AIModeration, DecisionType, GuildSettings, ToolRegistry, ToolType


BOT_ID = 999_999_999_999_999_999
AUTHOR_ID = 111_111_111_111_111_111
TARGET_ID = 222_222_222_222_222_222
ROLE_ID = 333_333_333_333_333_333
CHANNEL_ID = 444_444_444_444_444_444


# Forty distinct action intents multiplied by twenty-five natural-language
# presentation variants. This keeps the production router generic while making
# the regression corpus broad and exactly reproducible.
ACTION_INTENTS: tuple[tuple[str, ToolType], ...] = (
    (f"warn <@{TARGET_ID}> for repeated spam", ToolType.WARN),
    (f"show warnings for <@{TARGET_ID}>", ToolType.GET_WARNINGS),
    (f"show moderation history for <@{TARGET_ID}>", ToolType.GET_HISTORY),
    (f"mute <@{TARGET_ID}> 10m for flooding chat", ToolType.TIMEOUT),
    (f"mute everyone who doesn't have the role <@&{ROLE_ID}>", ToolType.TIMEOUT),
    (f"mute everyone except me and <@{TARGET_ID}>", ToolType.TIMEOUT),
    (f"unmute <@{TARGET_ID}>", ToolType.UNTIMEOUT),
    (f"kick <@{TARGET_ID}> for repeated disruption", ToolType.KICK),
    (f"ban <@{TARGET_ID}> for malicious links", ToolType.BAN),
    (f"unban <@{TARGET_ID}>", ToolType.UNBAN),
    ("purge 25 messages", ToolType.PURGE),
    (f"delete messages from <@{TARGET_ID}>", ToolType.PURGE),
    (f"give role Helper to <@{TARGET_ID}>", ToolType.ADD_ROLE),
    (f"remove role Helper from <@{TARGET_ID}>", ToolType.REMOVE_ROLE),
    ("create role named Event Helper", ToolType.CREATE_ROLE),
    ("delete role named Old Helper", ToolType.DELETE_ROLE),
    ("create a text channel named reports", ToolType.CREATE_CHANNEL),
    ("delete channel named old-reports", ToolType.DELETE_CHANNEL),
    ("set slowmode to 30s", ToolType.EDIT_CHANNEL),
    ("lock this channel", ToolType.LOCK_CHANNEL),
    ("unlock this channel", ToolType.UNLOCK_CHANNEL),
    (f"set nickname for <@{TARGET_ID}> as Helper", ToolType.SET_NICKNAME),
    (f"move <@{TARGET_ID}> to voice channel Lounge", ToolType.MOVE_MEMBER),
    (f"disconnect <@{TARGET_ID}> from vc", ToolType.DISCONNECT_MEMBER),
    (f"dm <@{TARGET_ID}> please read the rules", ToolType.DM_USER),
    ("create an invite", ToolType.CREATE_INVITE),
    ("pin this message", ToolType.PIN_MESSAGE),
    ("unpin this message", ToolType.UNPIN_MESSAGE),
    ("create emoji named wave", ToolType.CREATE_EMOJI),
    ("delete emoji named oldwave", ToolType.DELETE_EMOJI),
    ("find inactive members from 30 days", ToolType.FIND_INACTIVE_MEMBERS),
    (f"scan the last 50 messages in <#{CHANNEL_ID}>", ToolType.SCAN_CHANNEL),
    ("summarize moderation actions", ToolType.SUMMARIZE_ACTIONS),
    ("run a server safety check", ToolType.SAFETY_CHECK),
    ("show help", ToolType.HELP),
    ("edit the server name to Community Hub", ToolType.EXECUTE_PYTHON),
    ("archive every inactive thread", ToolType.EXECUTE_PYTHON),
    ("create an event for Friday at 6pm", ToolType.EXECUTE_PYTHON),
    ("make a poll for movie night", ToolType.EXECUTE_PYTHON),
    ("set up a reaction role for announcements", ToolType.EXECUTE_PYTHON),
)

PREFIXES = ("", "please ", "can you ", "could you ", "yo can you ")


def _style_variants(text: str) -> tuple[str, ...]:
    return (
        text,
        f"{text}.",
        f"{text}!",
        f"{text}?",
        f"{text};",
    )


def _build_cases() -> tuple[tuple[str, ToolType], ...]:
    cases: list[tuple[str, ToolType]] = []
    for request, expected_tool in ACTION_INTENTS:
        for prefix in PREFIXES:
            for styled in _style_variants(request):
                cases.append((f"{prefix}{styled}", expected_tool))
    assert len(cases) == 1_000
    assert len({request for request, _ in cases}) == 1_000
    return tuple(cases)


ACTION_CASES = _build_cases()
READ_ONLY_TOOLS = {
    ToolType.HELP,
    ToolType.GET_WARNINGS,
    ToolType.GET_HISTORY,
    ToolType.FIND_INACTIVE_MEMBERS,
    ToolType.SCAN_CHANNEL,
    ToolType.SUMMARIZE_ACTIONS,
    ToolType.SAFETY_CHECK,
}


@pytest.mark.parametrize(
    ("prompt_text", "expected_tool"),
    ACTION_CASES,
    ids=[f"action-{index + 1:04d}" for index in range(len(ACTION_CASES))],
)
def test_generated_action_route_review_matrix(prompt_text: str, expected_tool: ToolType) -> None:
    cog = object.__new__(AIModeration)
    bot_user = SimpleNamespace(id=BOT_ID, bot=True)
    author = SimpleNamespace(id=AUTHOR_ID, mention=f"<@{AUTHOR_ID}>", bot=False)
    target = SimpleNamespace(id=TARGET_ID, mention=f"<@{TARGET_ID}>", bot=False)
    role = SimpleNamespace(id=ROLE_ID, name="Above all")
    channel_mention = SimpleNamespace(id=CHANNEL_ID, mention=f"<#{CHANNEL_ID}>")
    cog.bot = SimpleNamespace(user=bot_user)
    message = SimpleNamespace(
        author=author,
        mentions=[bot_user] + ([target] if f"<@{TARGET_ID}>" in prompt_text else []),
        role_mentions=[role] if f"<@&{ROLE_ID}>" in prompt_text else [],
        channel_mentions=[channel_mention] if f"<#{CHANNEL_ID}>" in prompt_text else [],
        channel=SimpleNamespace(id=CHANNEL_ID, mention=f"<#{CHANNEL_ID}>"),
        reference=None,
    )

    decision = cog._quick_route(message, prompt_text)
    if decision is None:
        decision = cog._recover_tool_decision(message, prompt_text)

    assert decision is not None
    assert decision.type == DecisionType.TOOL_CALL
    assert decision.tool == expected_tool

    needs_confirmation = cog._requires_confirmation(GuildSettings(), decision)
    assert needs_confirmation is (expected_tool not in READ_ONLY_TOOLS)
    if needs_confirmation:
        preview = cog._confirmation_preview(message, decision)
        assert ToolRegistry.get_metadata(expected_tool).display_name in preview
        assert author.mention in preview
        assert "Review the target and scope carefully" in preview
