"""Discord mention patterns shared between the cog and the parsing mixin.

Defined here rather than in either consumer so both import the same compiled
objects. Duplicating these regexes is how two copies silently drift apart and
one path starts accepting IDs the other rejects.
"""
from __future__ import annotations

import re

_MENTION_RE = re.compile(r"<@!?(\d+)>")
_ROLE_MENTION_RE = re.compile(r"<@&(\d+)>")
_CHANNEL_MENTION_RE = re.compile(r"<#(\d+)>")

__all__ = ["_MENTION_RE", "_ROLE_MENTION_RE", "_CHANNEL_MENTION_RE"]
