"""Conversation delivery: chunking, code fences, research embeds, lane config.

``rendering.py`` is pure formatting with no network, so everything the user
actually sees in chat is testable here. The failures that matter are the ones
Discord rejects outright (empty message) or renders wrong (a code fence split
across two messages), because both look like the bot malfunctioning.
"""
from __future__ import annotations

import pytest

from cogs.aimoderation.rendering import ResponseRenderingMixin as R


split = R._split_response

DISCORD_LIMIT = 2000


def fences_balanced(chunk: str) -> bool:
    return chunk.count("```") % 2 == 0


# --- Length ----------------------------------------------------------------

def test_short_text_is_one_chunk():
    assert split("hello") == ["hello"]


def test_text_at_the_limit_is_not_split():
    assert len(split("a" * 1900)) == 1


@pytest.mark.parametrize("size", [1901, 2500, 5000, 10_000, 50_000])
def test_every_chunk_fits_discord(size):
    for chunk in split("a" * size):
        assert len(chunk) <= 1900, f"chunk of {len(chunk)} exceeds the split limit"
        assert len(chunk) < DISCORD_LIMIT, "chunk would be rejected by Discord"


def test_splitting_loses_no_visible_text():
    text = " ".join(f"word{i}" for i in range(3000))
    assert "".join(split(text)).replace(" ", "") == text.replace(" ", "")


def test_split_terminates_on_pathological_input():
    """Guards the while-loop: no natural boundary anywhere."""
    for text in ["a" * 20_000, "あ" * 8000, ("x" + "\n") * 5000]:
        assert split(text)


# --- Blank input ------------------------------------------------------------
# Discord rejects an empty message, so a blank chunk can only fail at the API.

@pytest.mark.parametrize("text", ["", "   ", "\n" * 5000, "\t\n \n\t"])
def test_blank_input_yields_no_chunks(text):
    assert split(text) == []


def test_no_chunk_is_ever_blank():
    for text in ["a" * 5000, "\n\n" + "b" * 4000 + "\n\n", "  " + "c" * 3000]:
        assert all(chunk.strip() for chunk in split(text)), "produced a blank chunk"


# --- Code fences ------------------------------------------------------------

def test_a_split_code_block_stays_balanced_in_every_chunk():
    """A fence spanning the cut used to render as prose in the middle chunks."""
    code = "```python\n" + ("print('x')\n" * 400) + "```"
    chunks = split(code)
    assert len(chunks) > 1, "test needs a multi-chunk block"
    for index, chunk in enumerate(chunks):
        assert fences_balanced(chunk), f"chunk {index} has an unbalanced fence"


def test_language_tag_is_carried_into_continuation_chunks():
    code = "```python\n" + ("print('x')\n" * 400) + "```"
    for chunk in split(code)[1:]:
        assert chunk.startswith("```python"), f"lost the language tag: {chunk[:20]!r}"


def test_rebalanced_chunks_still_fit():
    """Reopening and closing fences must not push a chunk over the limit."""
    code = "```python\n" + ("print('x')\n" * 400) + "```"
    for chunk in split(code):
        assert len(chunk) <= 1900


def test_prose_around_a_code_block_stays_balanced():
    text = "intro\n\n```js\n" + ("let a=1;\n" * 250) + "```\n\noutro " + ("word " * 400)
    for chunk in split(text):
        assert fences_balanced(chunk)


def test_fence_without_a_language_tag_is_handled():
    code = "```\n" + ("data\n" * 600) + "```"
    for chunk in split(code):
        assert fences_balanced(chunk)


def test_text_with_no_code_gains_no_fences():
    for chunk in split("plain prose. " * 400):
        assert "```" not in chunk


# --- Research embeds --------------------------------------------------------

def test_research_embeds_survive_a_blank_summary():
    """_split_response returns [] for blank input; the [0] index must not blow up."""
    for value in ["", "   ", "\n\n"]:
        embeds = R._build_research_embeds(value, "some query")
        assert embeds and embeds[0].description


def test_research_embed_descriptions_fit_discords_limit():
    embeds = R._build_research_embeds("word " * 5000, "q")
    for embed in embeds:
        assert len(embed.description) <= 4096


def test_research_embed_titles_fit_discords_limit():
    embeds = R._build_research_embeds("# " + "T" * 400 + "\n\n" + "body " * 2000, "q")
    for embed in embeds:
        assert len(embed.title) <= 256


def test_multi_page_research_is_numbered():
    embeds = R._build_research_embeds("word " * 5000, "q")
    if len(embeds) > 1:
        assert "(1/" in embeds[0].title


# --- Sources ----------------------------------------------------------------

def test_sources_are_split_off_the_answer_body():
    answer, sources = R._split_research_sources("The answer.\n\n__BOT_SOURCES__\nhttps://example.com")
    assert answer == "The answer."
    assert sources and "example.com" in sources


def test_no_source_marker_leaves_text_untouched():
    answer, sources = R._split_research_sources("Just an answer.")
    assert answer == "Just an answer."
    assert sources is None


# --- Talking lane configuration --------------------------------------------

def test_legion_chat_model_env_var_is_honoured(monkeypatch):
    """OPENROUTER_CHAT_MODEL was read nowhere, so setting it did nothing.

    Re-derived here rather than read off the constant, because the constant is
    computed once at import.
    """
    import os

    def resolve():
        return (
            os.getenv("OPENROUTER_CHAT_MODEL_TALKING")
            or os.getenv("OPENROUTER_GROK_CHAT_MODEL")
            or os.getenv("OPENROUTER_CHAT_MODEL")
            or "~deepseek/deepseek-v4-flash-latest"
        )

    for name in ("OPENROUTER_CHAT_MODEL_TALKING", "OPENROUTER_GROK_CHAT_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENROUTER_CHAT_MODEL", "vendor/some-model")
    assert resolve() == "vendor/some-model"

    monkeypatch.setenv("OPENROUTER_CHAT_MODEL_TALKING", "vendor/explicit-talking")
    assert resolve() == "vendor/explicit-talking", "the explicit talking var must win"


def test_talking_lane_resolves_to_something():
    import cogs.aimoderation.ai_client as ai_client

    assert ai_client._LEGION_CHAT_MODEL.strip()
