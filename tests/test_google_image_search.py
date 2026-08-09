from __future__ import annotations

from cogs.aimoderation.providers.google import (
    GoogleImageSearchLaneMixin,
)


def test_web_detection_preserves_ocr_and_exact_matching_pages() -> None:
    evidence = GoogleImageSearchLaneMixin._parse_google_web_detection(
        {
            "responses": [
                {
                    "fullTextAnnotation": {"text": "@RhanFuka_8812\nOC"},
                    "logoAnnotations": [
                        {"description": "Artist mark", "score": 0.91}
                    ],
                    "webDetection": {
                        "bestGuessLabels": [{"label": "snake girl artwork"}],
                        "webEntities": [
                            {"description": "original character", "score": 0.88}
                        ],
                        "pagesWithMatchingImages": [
                            {
                                "url": "https://artist.example/post/123",
                                "pageTitle": "RhanFuka OC",
                                "fullMatchingImages": [
                                    {"url": "https://cdn.example/image.png"}
                                ],
                            }
                        ],
                        "fullMatchingImages": [
                            {"url": "https://cdn.example/image.png"}
                        ],
                    },
                }
            ]
        }
    )

    assert evidence.exact_match is True
    assert evidence.source_urls == ("https://artist.example/post/123",)
    assert "@RhanFuka_8812 OC" in evidence.ocr_text
    assert "full match" in evidence.context
    assert "original character" in evidence.context


def test_visually_similar_results_are_not_treated_as_exact_matches() -> None:
    evidence = GoogleImageSearchLaneMixin._parse_google_web_detection(
        {
            "responses": [
                {
                    "webDetection": {
                        "bestGuessLabels": [{"label": "anime character"}],
                        "visuallySimilarImages": [
                            {"url": "https://cdn.example/similar.png"}
                        ],
                    }
                }
            ]
        }
    )

    assert evidence.available is True
    assert evidence.exact_match is False
    assert evidence.source_urls == ()


def test_grounded_response_extracts_google_citations() -> None:
    content = GoogleImageSearchLaneMixin._parse_google_grounded_response(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    "This is an original snake-girl character by "
                                    "@RhanFuka_8812."
                                )
                            }
                        ]
                    },
                    "groundingMetadata": {
                        "groundingChunks": [
                            {
                                "web": {
                                    "uri": "https://artist.example/post/123",
                                    "title": "Artist post",
                                }
                            }
                        ]
                    },
                }
            ]
        }
    )

    assert content is not None
    assert "original snake-girl character" in content
    assert "__BOT_SOURCES__" in content
    assert "https://artist.example/post/123" in content


def test_grounded_response_uses_only_exact_match_fallback_sources() -> None:
    content = GoogleImageSearchLaneMixin._parse_google_grounded_response(
        {
            "candidates": [
                {"content": {"parts": [{"text": "The watermark names the artist."}]}}
            ]
        },
        fallback_source_urls=("https://artist.example/post/123",),
    )

    assert content == (
        "The watermark names the artist.\n\n"
        "__BOT_SOURCES__\n"
        "- https://artist.example/post/123"
    )


def test_source_merge_is_deduplicated() -> None:
    merged = GoogleImageSearchLaneMixin._merge_grounded_sources(
        "Answer\n\n__BOT_SOURCES__\n- https://one.example/post",
        ("https://one.example/post", "https://two.example/post"),
    )

    assert merged.count("https://one.example/post") == 1
    assert merged.count("https://two.example/post") == 1
