"""Argument extraction for moderation actions.

Routing decides *whether* to act; these functions decide *what* the action
does. A silent miss here is worse than a routing miss, because the action
still runs -- with a wrong duration, a wrong count, or "No reason provided"
in the audit log.
"""
from __future__ import annotations

import pytest


# --- Durations --------------------------------------------------------------

@pytest.mark.parametrize(
    "text,seconds",
    [
        ("30s", 30),
        ("10m", 600),
        ("1h", 3600),
        ("2 days", 172800),
        ("1w", 604800),
        ("for 10 minutes", 600),
        ("5 mins", 300),
        ("2 hrs", 7200),
        ("timeout @user for 1 hour", 3600),
    ],
)
def test_duration_units_parse(parser, text, seconds):
    assert parser._parse_duration_seconds(text) == seconds


@pytest.mark.parametrize("text", ["forever", "90", "a while", "", "soon"])
def test_unparseable_duration_is_none(parser, text):
    """None must mean 'unspecified' so callers can apply their own default."""
    assert parser._parse_duration_seconds(text) is None


def test_duration_does_not_match_inside_words(parser):
    """A bare 'd'/'m' inside a word must not be read as a unit."""
    assert parser._parse_duration_seconds("ban 3 dummies") is None


# --- Purge counts -----------------------------------------------------------

@pytest.mark.parametrize(
    "text,amount",
    [
        ("purge 20", 20),
        ("clear 5", 5),
        ("delete the last 50 messages", 50),
        ("purge 100 messages", 100),
    ],
)
def test_purge_amount_parses(parser, text, amount):
    assert parser._extract_purge_amount(text) == amount


def test_purge_without_a_count_is_none(parser):
    assert parser._extract_purge_amount("purge") is None


# --- Warning counts ---------------------------------------------------------

@pytest.mark.parametrize(
    "text,count",
    [("warn @user", 1), ("warn @user twice", 2), ("warn @user 3 times", 3)],
)
def test_warning_count(parser, text, count):
    assert parser._extract_warning_count(text) == count


def test_warning_count_defaults_to_one(parser):
    """Absent an explicit count a warning is a single warning, never zero."""
    assert parser._extract_warning_count("warn @user for being rude") >= 1


# --- Reasons ----------------------------------------------------------------

def test_because_clause_is_extracted_as_reason(parser):
    assert parser._extract_reason("kick @u because he was rude") == "he was rude"


def test_missing_reason_is_none_not_empty_string(parser):
    """Callers distinguish None (infer one) from '' (an empty reason)."""
    assert parser._extract_reason("ban @u") is None


# --- Lookup vs action -------------------------------------------------------
# "warn @user" acts; "show warnings for @user" reads. Conflating them is how a
# read-only query turns into a punishment.

@pytest.mark.parametrize(
    "text",
    ["warn @user", "warn @user for spam", "warn @user twice"],
)
def test_warning_action_is_an_action(parser, text):
    assert parser._looks_like_warning_action(text)
    assert not parser._looks_like_warning_lookup(text)


@pytest.mark.parametrize(
    "text",
    [
        "show warnings for @user",
        "list warnings for @user",
        "how many warnings does @user have",
    ],
)
def test_warning_lookup_is_not_an_action(parser, text):
    assert not parser._looks_like_warning_action(text), f"lookup treated as action: {text!r}"


@pytest.mark.parametrize(
    "text",
    ["show history for @user", "show me @user's modlogs", "get the record for @user"],
)
def test_history_lookup_detected(parser, text):
    assert parser._looks_like_history_lookup(text), f"history lookup missed: {text!r}"


# --- Image questions --------------------------------------------------------

# This predicate is a deliberately narrow FAST PATH, not a general image
# classifier: it catches deictic questions ("what is this") that are
# meaningless without looking at the attachment, and sends them straight to the
# vision lane ahead of action routing. Descriptive phrasings ("describe this
# photo") are not matched here and do not need to be -- they fall through to
# the ordinary conversation gate. The property that matters is the one asserted
# in test_descriptive_image_phrasings_are_not_moderation below.
@pytest.mark.parametrize(
    "text",
    [
        "what is this",
        "who is this",
        "what's this",
        "what is that",
        "who are these",
        "what are those",
    ],
)
def test_deictic_image_questions_take_the_fast_path(parser, text):
    assert parser._looks_like_image_question(text)


@pytest.mark.parametrize("text", ["ban @user", "hello there", "purge 10"])
def test_non_image_text_is_not_an_image_question(parser, text):
    assert not parser._looks_like_image_question(text)


@pytest.mark.parametrize(
    "text",
    [
        "what is in this image",
        "what's in this picture",
        "describe this photo",
        "describe this image",
        "what does this say",
    ],
)
def test_descriptive_image_phrasings_are_not_moderation(parser, text):
    """They may skip the fast path, but they must never look like an action.

    Reaching conversation via the normal gate is fine; being mistaken for a
    moderation command is not.
    """
    assert not parser._looks_like_mod_request(text)
    assert not parser._looks_like_advanced_action_request(text)
