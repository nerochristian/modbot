"""Chat-vs-moderate routing heuristics.

Why this file matters
---------------------
``_looks_like_mod_request`` runs BEFORE the model router. When it returns
False the message is handed to the conversation surface and the moderation
router is never called at all, so a miss here is invisible: the bot simply
chats back at someone asking for a ban.

That is not hypothetical. ``_ACTION_PREFIX_RE`` used to require a politeness
clause, so "hey can you ban @user" routed correctly while "hey ban @user"
silently became chat -- 15 of 23 ordinary phrasings missed that way. These
cases lock that class of regression out.

The error costs are deliberately asymmetric. A false positive still passes
through the model router (which can answer CHAT) and ``validate_tool_access``,
so it is recoverable; a false negative never reaches the router at all. These
tests therefore demand recall on action phrasings and guard precision only on
clearly conversational text.
"""
from __future__ import annotations

import pytest


def detected(parser, text: str) -> bool:
    """Mirror the on_message gate: either predicate opens the moderation path."""
    return bool(
        parser._looks_like_mod_request(text)
        or parser._looks_like_advanced_action_request(text)
    )


BARE_IMPERATIVES = [
    "ban @user for spam",
    "kick @user",
    "mute @user",
    "timeout @user 10m",
    "unban @user",
    "untimeout @user",
    "warn @user for insults",
    "purge 20",
    "clear 10 messages",
    "delete the last 5 messages",
]

# The exact shapes that regressed. Each is a leading token that is NOT a
# politeness word, which is what the old pattern required.
FILLER_PREFIXED = [
    "hey ban @user",
    "yo ban @user",
    "ok ban @user",
    "okay kick @user",
    "alright ban @user",
    "so ban @user",
    "just ban @user",
    "now ban @user",
    "quick ban @user",
    "um kick @user",
    "actually kick @user",
    "honestly ban @user",
    "seriously ban @user",
    "bro ban @user",
    "bruh ban @user",
    "dude timeout @user 1h",
    "man ban @user",
    "mate kick @user",
    "guys ban @user",
    "mods ban @user",
    "admin ban @user",
    "staff kick @user",
    "hey mute @user for 10m",
    "yo timeout @user 5m",
]

POLITE = [
    "please ban @user",
    "pls ban @user",
    "plz ban @user",
    "can you ban @user",
    "could you ban @user",
    "would you kick @user",
    "will you mute @user",
    "can u ban @user",
    "could you please ban @user",
    "can someone ban @user",
    "can anyone kick @user",
]

SUGGESTION = [
    "you should ban @user",
    "u should ban @user",
    "i think you should ban @user",
    "i reckon you should kick @user",
    "someone should ban @user",
    "somebody needs to ban @user",
    "you need to ban @user",
    "you gotta ban @user",
    "you have to kick @user",
    "we should ban @user",
    "maybe ban @user",
    "perhaps kick @user",
    "let's ban @user",
    "lets ban @user",
]

STACKED = [
    "hey bro can you please ban @user",
    "yo mods please kick @user",
    "hey can you please timeout @user 10m",
    "ok so can you ban @user",
    "alright guys please ban @user",
]

# Text a person would plausibly say to a chatbot that must NOT trigger an action
# path. Note these discuss moderation without requesting it.
CONVERSATIONAL = [
    "hey what's up",
    "how are you doing today",
    "what's the weather like",
    "who made you",
    "tell me a joke",
    "what model are you using",
    "i got banned from another server yesterday",
    "that ban was unfair imo",
    "is banning people fun",
    "what does timeout mean",
    "hey do you like pizza",
    "so what do you think about that",
    "just wondering how you work",
    "man this server is quiet",
    "good morning everyone",
    "lol that was funny",
    "thanks",
    "why did you say that",
]


@pytest.mark.parametrize("text", BARE_IMPERATIVES)
def test_bare_imperative_is_moderation(parser, text):
    assert detected(parser, text), f"bare imperative missed: {text!r}"


@pytest.mark.parametrize("text", FILLER_PREFIXED)
def test_filler_prefixed_is_moderation(parser, text):
    """The exact regression: a non-politeness leading token must still route."""
    assert detected(parser, text), f"filler-prefixed request missed: {text!r}"


@pytest.mark.parametrize("text", POLITE)
def test_polite_request_is_moderation(parser, text):
    assert detected(parser, text), f"polite request missed: {text!r}"


@pytest.mark.parametrize("text", SUGGESTION)
def test_suggestion_framing_is_moderation(parser, text):
    assert detected(parser, text), f"suggestion framing missed: {text!r}"


@pytest.mark.parametrize("text", STACKED)
def test_stacked_prefixes_are_moderation(parser, text):
    """Several prefixes in a row must all peel; the stripper loops for this."""
    assert detected(parser, text), f"stacked-prefix request missed: {text!r}"


@pytest.mark.parametrize("text", CONVERSATIONAL)
def test_conversation_is_not_moderation(parser, text):
    assert not detected(parser, text), f"chat misrouted to moderation: {text!r}"


def test_recall_on_action_phrasings_is_total(parser):
    """Aggregate recall guard.

    Parametrized cases show *which* phrasing broke; this asserts the overall
    rate, so a future change that trades several phrasings for one cannot pass
    quietly.
    """
    corpus = BARE_IMPERATIVES + FILLER_PREFIXED + POLITE + SUGGESTION + STACKED
    missed = [t for t in corpus if not detected(parser, t)]
    assert not missed, f"{len(missed)}/{len(corpus)} action phrasings missed: {missed}"


def test_case_and_whitespace_are_insensitive(parser):
    for text in ["  HEY BAN @user  ", "Hey Ban @user", "hey,  ban @user"]:
        assert detected(parser, text), f"normalization failed: {text!r}"


def test_strip_action_prefix_leaves_the_verb_first(parser):
    """The stripper exists to expose the verb to an ^-anchored pattern."""
    for text in ["hey ban @user", "you should ban @user", "hey bro can you please ban @user"]:
        stripped = parser._normalize_chat_text(parser._strip_action_prefix(text))
        assert stripped.startswith("ban"), f"{text!r} -> {stripped!r}"


def test_stripper_does_not_consume_the_whole_message(parser):
    """A message that is only filler must not strip down to nothing weirdly."""
    for text in ["hey", "please", "bro"]:
        assert parser._strip_action_prefix(text) is not None


# --- Model-routing escalation ----------------------------------------------
# _requires_model_routing forces the deterministic quick-router to stand down
# for requests it cannot represent (filters, bulk scope, conditionals).

@pytest.mark.parametrize(
    "text",
    [
        "ban everyone who joined today",
        "kick members without roles",
        "purge all channels",
        "ban all accounts created less than 3 days ago",
        "timeout everybody who posted a link",
        "kick users that have no avatar except staff",
    ],
)
def test_broad_or_conditional_requests_need_the_model(parser, text):
    assert parser._requires_model_routing(text), f"should escalate to model: {text!r}"


@pytest.mark.parametrize("text", ["ban @user", "kick @user for spam", "timeout @user 10m"])
def test_simple_targeted_requests_skip_model_routing(parser, text):
    assert not parser._requires_model_routing(text), f"should stay deterministic: {text!r}"
