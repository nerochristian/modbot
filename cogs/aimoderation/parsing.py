"""Message text parsing and intent classification.

Turns raw Discord message text into structured intent: what action was asked
for, against whom, for how long, and with what reason. Also decides whether a
message needs the model router at all (``_requires_model_routing``) and builds
the conversation signals that select the reply lane
(``_build_conversation_signals``).

Almost everything here is a pure function of ``(str, dict)`` -- no network, no
Discord API, no bot state -- so the parsing rules are directly testable. The
exceptions, which read ``self.bot.user`` to skip the bot's own mention or
resolve targets from ``message.mentions``:

    _extract_purge_target_from_mentions, _extract_dm_target_from_mentions,
    _bulk_timeout_arguments, _warning_arguments, _quick_route

and one async method, ``_build_conversation_signals``, which may await the
router classifier.

Implemented as a mixin, not free functions: the cog and its tests reach these
as attributes (``self._quick_route``, ``AIModeration._extract_purge_args``), and
the regex class-vars are looked up through ``self``, so inheritance keeps every
existing call site working.

Requires from the composing class: ``self.bot``, ``self.ai``, and
``self.clean_content(message)``.
"""
from __future__ import annotations

import re
from typing import Any, ClassVar, Dict, Optional

import discord

from .types import (
    ConversationMode,
    ConversationSignals,
    Decision,
    DecisionType,
    ToolType,
)

# Shared with the cog module; imported rather than duplicated so the patterns
# cannot drift apart.
from .patterns import _CHANNEL_MENTION_RE, _MENTION_RE, _ROLE_MENTION_RE

_SNOWFLAKE_RE = re.compile(r"\b(\d{15,22})\b")

_REPLY_TARGET_RE = re.compile(
    r"\b(?:this|that)\s+(?:guy|dude|person|member|user|one)|\b(?:him|her|them|that\s+user|this\s+user)\b",
    re.IGNORECASE,
)

_LIVE_WORLD_NEWS_RE = re.compile(
    r"\b(?:what(?:'s|\s+is)\s+(?:going\s+on|happening)\s+(?:in|around)\s+(?:the\s+)?world|"
    r"what(?:'s|\s+is)\s+happening\s+globally|current\s+events|"
    r"(?:world|global)\s+(?:news|headlines)|(?:news|headlines)\s+(?:today|right\s+now))\b",
    re.IGNORECASE,
)

def _looks_like_image_question_text(content: str) -> bool:
    low = re.sub(r"\s+", " ", (content or "").strip().lower())
    return bool(
        re.search(r"\b(?:who|what)\s+(?:is|are)\s+(?:this|that|it|these|those)\b", low)
        or re.search(r"\b(?:who|what)'s\s+(?:this|that|it)\b", low)
    )


class MessageParsingMixin:
    """Intent extraction and routing predicates for message text."""

    _MOD_REQUEST_RE: ClassVar[re.Pattern] = re.compile(
        r"^(warn|kick|ban|unban|mute|timeout|unmute|untimeout|purge|clear|clean|"
        r"wipe|nuke|delete\b|remove\b|shut\s+up|silence|bench|boot|banish|"
        r"add\s+role|give\s+role|take\s+role|create\s+role|make\s+role|role\b|"
        r"create\s+channel|make\s+channel|add\s+channel|clone\s+channel|reorder\s+channel|spin\s+up|make\s+room|create\s+room|"
        r"create\s+category|make\s+category|archive\s+category|organize\s+categor|"
        r"create\s+thread|make\s+thread|archive\s+thread|close\s+thread|convert\b|"
        r"lock|unlock|lockdown|open\s+invite|invite|"
        r"set\b|edit\b|update\b|nickname|move|drag|disconnect|pin|unpin|emoji|"
        r"make\s+(?:an?\s+)?event|create\s+(?:an?\s+)?event|schedule|remind|dm\s|announce|"
        r"poll|reaction\s+role|button\s+role|dropdown\s+role|welcome|goodbye|onboard|"
        r"archive|signup|give\s+everyone|remove\s+everyone|mass\s|bulk\s|"
        r"make\s+(?:a\s+)?(?:private|project|category|group)|create\s+(?:a\s+)?project|homework|assignment|deadline|attendance|"
        r"delete\s+(?:the\s+)?(?:group|category|project)|ticket|support|faq|"
        r"report|stats|analytics|activity|inactive|find\s+inactive|scan\s+(?:this\s+)?channel|"
        r"safety\s+(?:check|audit)|summarize\s+(?:mod(?:eration)?\s+)?actions?|leaderboard|xp|"
        r"verify|verification|captcha|raid|anti[-\s]?raid|anti[-\s]?nuke|"
        r"queue|matchmaking|tournament|team\s+balanc|voice|vc|afk|"
        r"turn\s+this|"
        r"react|ping\s+everyone|ping\s+all|"
        r"fetch|get\s+(?:audit|logs?|members?|roles?|channels?|cases?|warnings?)|"
        r"how\s+many\s+(?:members?|users?|roles?|channels?|warnings?|cases?|messages?)|"
        r"count\s+(?:members?|users?|roles?|channels?|warnings?|cases?|messages?)|"
        r"(?:print|display)\s+(?:audit|logs?|members?|users?|roles?|channels?|cases?|warnings?|activity))\b",
        re.IGNORECASE,
    )
    _CONDITIONAL_ACTION_RE: ClassVar[re.Pattern] = re.compile(
        r"^(?:(?:if|when|whenever)\s+someone|every\s+time\s+someone)\b.+?(?:"
        r"(?:then|,)\s*(?:(?:can|could|would|will)\s+you\s+|please\s+)?"
        r"(?:warn|kick|ban|unban|mute|timeout|unmute|quarantine|delete|remove|"
        r"purge|lock|unlock|give|add|assign|take|send|dm|notify|alert|log|create|"
        r"react|reply|block|welcome|say)\b|"
        r"(?:warn|kick|ban|unban|mute|timeout|unmute|quarantine|delete|remove|"
        r"purge|lock|unlock|give|add|assign|take|send|dm|notify|alert|log|create|"
        r"react|reply|block|welcome|say)\s+"
        r"(?:them|that\s+user|the\s+user|the\s+message|it|a\s+role|the\s+role)\b"
        r")",
        re.IGNORECASE,
    )
    # Matches a request FOR help, not the word "help" in passing.
    #
    # The old pattern was a bare \b(help|commands)\b, so any message containing
    # the word routed to the help menu: "thanks for the help", "i need help
    # understanding this", and -- because _recover_tool_decision tested this
    # before the action checks -- "help me ban @user", which showed a command
    # list instead of banning anyone.
    _HELP_RE: ClassVar[re.Pattern] = re.compile(
        # The whole message is the request: "help", "commands", "help me".
        r"^(?:help|commands?|cmds)\b[\s!?.]*$"
        r"|^help\s+me\b[\s!?.]*$"
        # Explicitly asking to see it.
        r"|^(?:show|list|send|give|display)\s+(?:me\s+)?(?:the\s+|your\s+)?(?:help|commands?)\b"
        r"|\bhelp\s+(?:menu|page|command)\b"
        r"|\bcommand\s+list\b"
        # Capability questions.
        r"|\bwhat\s+can\s+you\s+do\b"
        r"|\bhow\s+do\s+i\s+use\s+you\b"
        r"|\bhow\s+do\s+you\s+work\b",
        re.IGNORECASE,
    )
    _DURATION_UNITS: ClassVar[Dict[str, int]] = {
        "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
        "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
        "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
        "d": 86400, "day": 86400, "days": 86400,
        "w": 604800, "week": 604800, "weeks": 604800,
    }
    _DURATION_RE: ClassVar[re.Pattern] = re.compile(
        r"(\d+)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes"
        r"|h|hr|hrs|hour|hours|d|day|days|w|week|weeks)(?![a-z])",
        re.IGNORECASE,
    )
    # Leading filler that must come off before _MOD_REQUEST_RE, which is
    # anchored at ^ and therefore only ever sees the first word.
    #
    # The previous pattern made the interjection optional but the politeness
    # clause MANDATORY, so it matched "hey can you ban @user" yet stripped
    # nothing from "hey ban @user" -- the anchored verb match then failed and
    # the request was silently handled as chat. 15 of 23 ordinary phrasings
    # ("yo ban", "ok ban", "just ban", "you should ban", "bro ban") missed that
    # way. Each alternative below strips independently instead, and the caller
    # applies this repeatedly to peel stacked prefixes.
    #
    # Erring wide is the safe direction here: a false positive still passes
    # through the model router (which can return CHAT) and validate_tool_access,
    # while a false negative never reaches the router at all.
    _ACTION_PREFIX_RE: ClassVar[re.Pattern] = re.compile(
        r"^\s*(?:"
        # Vocatives and discourse markers.
        r"(?:hey|yo|ok|okay|alright|aight|um|uh|erm|so|now|quick|quickly|just|"
        r"actually|honestly|seriously|please|pls|plz|bro|bruh|dude|man|mate|"
        r"guys|admin|admins|mod|mods|staff)\b[\s,]*"
        # Direct request framing.
        r"|(?:can|could|would|will|can'?t|cant)\s+(?:you|u|someone|somebody|anyone|we)\b\s*"
        # Suggestion framing: "you should", "i think you should", "someone needs to".
        r"|(?:i\s+(?:think|reckon|believe|feel\s+like)\s+)?"
        r"(?:you|u|someone|somebody|we)\s+"
        r"(?:should|need\s+to|needs\s+to|gotta|have\s+to|has\s+to|must|ought\s+to)\b\s*"
        r"|(?:maybe|perhaps|possibly)\b\s*"
        r"|(?:let'?s|let\s+us)\b\s*"
        # "help me ban @user" is a ban request. The trailing \s+ is required so
        # a bare "help me" is left intact for _HELP_RE to claim as the menu.
        r"|(?:help\s+me)\s+"
        r")",
        re.IGNORECASE,
    )
    _WARNING_LOOKUP_RE: ClassVar[re.Pattern] = re.compile(
        r"(?:"
        r"^(?:warnings?|warn(?:ing)?\s+history)\b|"
        r"\b(?:what(?:'s|\s+is|\s+are)|show|list|check|view|get|pull|fetch|display|how\s+many)\b"
        r".{0,100}\b(?:warnings?|warn(?:ing)?\s+history)\b|"
        r"\b(?:warnings?|warn(?:ing)?\s+history)\b.{0,60}\b(?:for|of|on)\b"
        r")",
        re.IGNORECASE,
    )
    _HISTORY_LOOKUP_RE: ClassVar[re.Pattern] = re.compile(
        r"(?:"
        # "show/pull/get ... actions/history/record/modlogs/rap sheet ..."
        r"\b(?:what(?:'?s|\s+is|\s+are)?|show|list|check|view|get|pull|fetch|display|give\s+me|see|look\s+up|lookup)\b"
        r".{0,60}\b(?:actions?|history|records?|modlogs?|mod\s+logs?|rap\s+sheet|dossier|track\s+record|priors?|"
        r"case\s+history|prior\s+actions?|past\s+actions?|infractions?|offen[cs]es?)\b|"
        # "actions/history/record ... for/on/of @user"
        r"\b(?:actions?|history|records?|modlogs?|mod\s+logs?|rap\s+sheet|dossier|track\s+record|priors?|"
        r"case\s+history|infractions?|offen[cs]es?)\b.{0,40}\b(?:for|on|of|against)\b|"
        # bare "modlogs @user" / "history @user"
        r"^(?:modlogs?|mod\s+logs?|history|rap\s+sheet)\b"
        r")",
        re.IGNORECASE,
    )
    _WARNING_ACTION_RE: ClassVar[re.Pattern] = re.compile(
        r"^(?:"
        r"warn\b|"
        r"(?:give|issue|add|apply)\b.{0,120}\bwarn(?:ing)?s?\b"
        r")",
        re.IGNORECASE,
    )
    _PREVIOUS_MESSAGE_TARGET_RE: ClassVar[re.Pattern] = re.compile(
        r"(?:"
        r"\b(?:person|user|member|author)\s+who\s+(?:sent|wrote|posted)\s+"
        r"(?:the\s+)?message\s+(?:immediately\s+)?before\s+(?:mine|me|this)\b|"
        r"\b(?:author|sender)\s+of\s+(?:the\s+)?(?:immediately\s+)?previous\s+message\b|"
        r"\b(?:immediately\s+)?previous\s+(?:message\s+)?(?:author|sender)\b|"
        r"\blast\s+(?:person|user|member)\s+to\s+(?:message|speak|post)\s+before\s+me\b"
        r")",
        re.IGNORECASE,
    )
    _PREVIOUS_MESSAGE_SAFE_GUARD_RE: ClassVar[re.Pattern] = re.compile(
        r"\s*,?\s*unless\s+(?:(?:they(?:'re|\s+are)|it\s+is)\s+)?"
        r"(?:(?:a\s+)?bot\s+or\s+(?:a\s+)?(?:protected\s+)?staff|"
        r"(?:protected\s+)?staff\s+or\s+(?:a\s+)?bot)\s*[.!?]*\s*$",
        re.IGNORECASE,
    )
    _WARNING_COUNT_RE: ClassVar[re.Pattern] = re.compile(
        r"\b(?P<count>\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|a|an)\s+"
        r"(?:separate\s+)?(?:warn(?:ing)?s?|times?)\b|"
        r"\bwarn(?:ing)?s?\s*[x*]\s*(?P<post_multiplier>\d{1,3})\b|"
        r"\b[x*]\s*(?P<pre_multiplier>\d{1,3})\s*warn(?:ing)?s?\b|"
        r"\b(?P<suffix_multiplier>\d{1,3})\s*[x*]\s*warn(?:ing)?s?\b|"
        r"\b(?P<frequency>once|twice|thrice)\b",
        re.IGNORECASE,
    )
    _WARNING_NUMBER_WORDS: ClassVar[Dict[str, int]] = {
        "a": 1,
        "an": 1,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "once": 1,
        "twice": 2,
        "thrice": 3,
    }
    @staticmethod
    def _looks_like_image_question(content: str) -> bool:
        return _looks_like_image_question_text(content)

    def _normalize_chat_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip().lower()).strip("`")

    def _strip_action_prefix(self, text: str) -> str:
        previous = text or ""
        current = previous
        for _ in range(6):
            current = self._ACTION_PREFIX_RE.sub("", current).strip()
            if current == previous:
                break
            previous = current
        return current

    def _looks_like_mod_request(self, content: str) -> bool:
        low = self._normalize_chat_text(self._strip_action_prefix(content))
        return bool(
            self._looks_like_warning_action(low)
            or self._looks_like_warning_lookup(low)
            or self._looks_like_history_lookup(low)
            or
            self._MOD_REQUEST_RE.match(low)
            or self._CONDITIONAL_ACTION_RE.match(low)
        )

    def _looks_like_warning_action(self, content: str) -> bool:
        low = self._normalize_chat_text(self._strip_action_prefix(content))
        return bool(self._WARNING_ACTION_RE.match(low))

    def _targets_previous_message_author(self, content: str) -> bool:
        low = self._normalize_chat_text(self._strip_action_prefix(content))
        return bool(self._PREVIOUS_MESSAGE_TARGET_RE.search(low))

    def _looks_like_warning_lookup(self, content: str) -> bool:
        low = self._normalize_chat_text(content)
        if self._looks_like_warning_action(low):
            return False
        return bool(self._WARNING_LOOKUP_RE.search(low))

    def _looks_like_history_lookup(self, content: str) -> bool:
        """Detect 'show actions/history/record/modlogs for @user' style requests."""
        low = self._normalize_chat_text(self._strip_action_prefix(content))
        if self._looks_like_warning_action(low):
            return False
        return bool(self._HISTORY_LOOKUP_RE.search(low))

    def _looks_like_advanced_action_request(self, content: str) -> bool:
        low = self._normalize_chat_text(self._strip_action_prefix(content))
        if self._looks_like_warning_lookup(low):
            return True
        if self._looks_like_history_lookup(low):
            return True
        if self._HELP_RE.search(low):
            return True
        if self._looks_like_mod_request(low):
            return True
        if self._extract_dm_args(content):
            return True
        prefix = r"^(?:please\s+|can\s+you\s+|could\s+you\s+)?"
        action_patterns = (
            r"(?:create|make|build|set up|delete|remove|archive|lock|unlock|clone|reorder|move|sync)\b",
            r"(?:schedule|remind|announce|dm)\b",
            r"(?:role|channel|category|thread|event|ticket|poll|project|homework|assignment|deadline|emoji|emote)\b",
            r"(?:raid|verification|welcome|goodbye|reaction role|leaderboard|attendance|inactive)\b",
            r"(?:open\s+up|reopen)\s+(?:this\s+)?(?:channel|chat|here)\b",
            r"(?:slowmode|slow\s+mode)\b",
            r"(?:send|move|drag)\b.*\b(?:vc|voice|voice\s+channel|channel|room)\b",
            r"(?:disconnect|dc)\b.*\b(?:vc|voice|voice\s+channel)\b",
            r"(?:summarize|summary|report)\s+(?:this\s+)?(?:channel|thread|chat|messages?|logs?|activity)\b",
            r"(?:show|list|fetch|get)\s+(?:audit|logs?|members?|users?|roles?|channels?|cases?|warnings?|inactive|activity|staff|admins?)\b",
            r"(?:who|which\s+members?|which\s+users?)\s+(?:has|have|is|are)\s+(?:the\s+)?[\w\s@#&-]*(?:role|admin|staff|permission|muted|banned|timed\s+out)\b",
            r"(?:who|which\s+members?|which\s+users?)\s+(?:joined|left|boosted|were\s+warned|got\s+warned|was\s+warned)\b",
            r"(?:how\s+many|count)\s+(?:members?|users?|roles?|channels?|warnings?|cases?|messages?)\b",
            r"(?:show|summarize|export|count|find|rank|compare|identify|calculate|route|escalate|"
            r"correlate|close|assign|audit|require)\b.*\b(?:warnings?|history|timeouts?|bans?|cases?|appeals?|channels?|reports?|"
            r"tickets?|audit|moderation|permissions?|members?|roles?|emojis?|stickers?|announcements?|"
            r"threads?|suggestions?|configuration|overwrites?|activity|requests?|complaints?|problems?|disputes?|actions?|settings?)\b",
            r"mark\s+as\s+age[ -]?restricted\b",
            r"rename\b.*\b(?:channel|role|emoji|sticker|server)\b",
            r"rename\s+with\s+an?\s+archived\s+prefix\b",
            r"post\b.*\bannouncement\b",
        )
        return any(re.match(prefix + pattern, low) for pattern in action_patterns)

    def _requires_model_routing(self, content: str) -> bool:
        """Keep conditional, bulk, and multi-step actions out of simple routes.

        The deterministic router is intentionally narrow: it is reliable for a
        direct action with an explicit target, but it cannot preserve arbitrary
        filters, exclusions, schedules, permission overwrites, or workflows.
        Those requests must reach the configured moderation model before a tool
        or guarded Python plan is selected.
        """
        low = self._normalize_chat_text(self._strip_action_prefix(content))
        if not low:
            return False

        # This relative target is fully groundable from Discord history. Keep it
        # on the typed warning path, including the common bot/staff safety guard,
        # instead of allowing an arbitrary Python plan to imitate a warning.
        routing_low = low
        if self._looks_like_warning_action(low) and self._targets_previous_message_author(low):
            routing_low = self._PREVIOUS_MESSAGE_SAFE_GUARD_RE.sub("", low)

        broad_scope = re.search(
            # "every" on its own covers "every single user", "every member",
            # "every account" -- phrasings that mean the whole server but were
            # missed by the everyone/everybody/all/each set, so a mass action
            # stayed on the deterministic path instead of going to the model.
            r"\b(?:everyone|everybody|every|all|each)\b|"
            r"\b(?:members?|users?|accounts?|messages?|threads?|invites?|roles?)\s+"
            r"(?:who|that|with|without|matching|created|joined|pending|playing|holding)\b|"
            r"\bacross\s+(?:the\s+)?(?:server|guild|channels?)\b|"
            r"\ball\s+(?:accessible\s+)?(?:text\s+)?channels?\b",
            routing_low,
        )
        conditional = re.search(
            r"\b(?:if|when|whenever|unless|until)\b|"
            r"\b(?:more|less|older|newer)\s+than\b|"
            r"\b(?:inactive|pending)\s+for\b|"
            r"\b(?:doesn'?t|does\s+not|do\s+not|without)\s+have\b",
            routing_low,
        )
        exclusions = re.search(
            r"\b(?:except|excluding|exclude|while\s+respecting|protected\s+roles?)\b",
            routing_low,
        )
        multi_step = re.search(
            r"\b(?:and\s+then|then|after|before)\b.*\b"
            r"(?:delete|remove|archive|lock|warn|timeout|kick|ban|export|copy|send|move)\b|"
            r"\b(?:copy|export|summarize|log|record)\b.*\b(?:and\s+then|then)\b",
            routing_low,
        )
        workflow = re.search(
            r"\b(?:automod|raid|lockdown|onboarding|verification\s+flow|"
            r"ticket\s+workflow|appeals?|audit\s+(?:entries|snapshot|review)|"
            r"analytics?|workload\s+report|schedule|scheduled|recurring|"
            r"backup|restore|reaction[ -]?role|forum|signups?|reminder\s+sequence)\b",
            routing_low,
        )
        permission_matrix = re.search(
            r"\b(?:allow|deny|reset|inherit|sync)\b.*\bpermissions?\b|"
            r"\b(?:allow|deny)\b.*\b(?:viewing|sending|attachments?|threads?|mention[ -]?everyone)\b",
            routing_low,
        )
        return bool(
            broad_scope
            or conditional
            or exclusions
            or multi_step
            or workflow
            or permission_matrix
        )

    async def _build_conversation_signals(self, content: str) -> ConversationSignals:
        low = self._normalize_chat_text(content)

        explicit_research = bool(re.search(
            r"\b(research|deep\s*(?:dive|research|analysis|think)|investigate|"
            r"full\s+breakdown|comprehensive|in[-\s]?depth|detailed\s+analysis|"
            r"compare\s+(?:sources|reports))\b",
            low,
        ))
        explicit_search = bool(re.search(
            r"\b(fact[\s-]?check|verify|look\s*up|search|browse|check\s+(?:online|the\s+web))\b",
            low,
        ))
        current_hint = bool(
            re.search(
                r"\b(latest|current(?:ly)?|right\s+now|today|tonight|yesterday|tomorrow|"
                r"recent(?:ly)?|newest|upcoming|this\s+(?:week|month|year|season)|"
                r"version|patch|update|release|price|weather|forecast|news|schedule|"
                r"president|prime\s+minister|governor|mayor|ceo|owner|officeholder|"
                r"law|legal|regulation|policy|stock|crypto|exchange\s+rate|"
                r"available|availability|recommend(?:ed|ation|ations)?)\b",
                low,
            )
            or _LIVE_WORLD_NEWS_RE.search(low)
        )
        casual_followup = bool(re.fullmatch(
            r"(?:what'?s new|what is new|what'?s up|what is the ai thingy|what'?s the ai thingy|what do you mean|what is that|what's that|huh|wdym|hi|hey|hello|yo)\??",
            low,
        ))
        mentions_moderation = self._looks_like_mod_request(content)
        asks_for_sources = bool(re.search(r"\b(sources?|citations?|proof|links?)\b", low))
        fallback_route = (
            "research"
            if explicit_research and not casual_followup and not mentions_moderation
            else "search"
            if explicit_search or current_hint or asks_for_sources
            else "normal"
        )
        route = fallback_route
        confidence = 0.95 if route == "research" else 0.9 if route == "search" else 0.0
        mod_intent = "action" if mentions_moderation else "none"

        classifier = getattr(self.ai, "classify_intent", None) or getattr(
            self.ai, "classify_research_route", None
        )
        # The regex is precise but not complete: when it already says "moderation"
        # we trust it and skip the network hop, and when it says "no" we let Ling
        # look again, because that is where the misses are.
        should_classify = bool(
            callable(classifier)
            and not casual_followup
            and not mentions_moderation
            and not explicit_research
            and not explicit_search
            and not asks_for_sources
        )
        if should_classify:
            decision = await classifier(content)
            if isinstance(decision, dict):
                candidate = str(decision.get("route") or "").strip().lower()
                candidate = {
                    "normal_chat": "normal",
                    "search_deepthink": "research",
                }.get(candidate, candidate)
                if candidate in {"normal", "search", "research"}:
                    route = candidate
                    try:
                        confidence = float(decision.get("confidence", 1.0))
                    except (TypeError, ValueError):
                        confidence = 1.0
                candidate_mod = str(decision.get("moderation") or "").strip().lower()
                if candidate_mod in {"action", "lookup", "guidance"}:
                    # Ling only ever upgrades: it caught phrasing the regex missed.
                    # It is never allowed to talk the regex out of a match.
                    mentions_moderation = True
                    mod_intent = candidate_mod
                    route = "normal"

        research_request = route == "research"
        search_request = route in {"search", "research"}
        mode = (
            ConversationMode.MOD_GUIDANCE
            if mod_intent == "guidance"
            else ConversationMode.RESEARCH
            if research_request
            else ConversationMode.STANDARD
        )

        # Live search is the OpenRouter search lane: Luna's web_search tool and
        # the Sonar research pre-fetch. Both report through has_web_search.
        research_capable = bool(getattr(self.ai, "has_web_search", True))
        show_indicator = research_capable and mode == ConversationMode.RESEARCH

        return ConversationSignals(
            mode=mode,
            confidence=confidence,
            show_research_indicator=show_indicator,
            asks_for_current_info=current_hint,
            asks_for_sources=asks_for_sources,
            asks_for_long_answer=research_request,
            mentions_moderation=mentions_moderation,
            requires_web_search=search_request,
        )

    def _parse_duration_seconds(self, text: str) -> Optional[int]:
        if not text:
            return None
        total = sum(
            int(amount) * self._DURATION_UNITS[unit.lower()]
            for amount, unit in self._DURATION_RE.findall(text)
        )
        if total:
            return total
        # A bare "for <n>" used to be read as <n> minutes. That silently turned
        # "timeout @user for 3 offenses" into a real 3-minute timeout reported
        # as success, and "for 5 strikes" into 5 minutes -- a confidently wrong
        # punishment, which is worse than none. Only accept the bare form when
        # the number is followed by a duration-ish word or ends the request, so
        # the caller falls back to timeout_default_seconds instead of guessing.
        m = re.search(
            r"\bfor\s+(\d+)\s*(?:more\s+)?"
            r"(?:mins?|minutes?|m)?\s*$",
            text,
            re.IGNORECASE,
        )
        return int(m.group(1)) * 60 if m else None

    def _parse_lookback_seconds(self, text: str) -> Optional[int]:
        if not text:
            return None

        normalized = re.sub(r"\b(hr|hrs)\b", "hour", text, flags=re.IGNORECASE)
        m = re.search(
            r"\b(?:last|past|previous|within)\s+(?:(\d+)\s*)?"
            r"(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days|w|week|weeks)\b",
            normalized,
            re.IGNORECASE,
        )
        if not m:
            return None
        amount = int(m.group(1) or 1)
        return amount * self._DURATION_UNITS[m.group(2).lower()]

    @staticmethod
    def _extract_purge_amount(text: str) -> Optional[int]:
        action = r"(?:purge|clear|clean|delete|remove|wipe|nuke)"
        patterns = (
            rf"\b{action}\b\s+(?:the\s+)?(?:last|latest|previous|most\s+recent)\s+"
            r"(\d{1,4})\s*(?:messages?|msgs?|chat\s+messages?)\b",
            rf"\b{action}\b\s+(\d{{1,4}})\s*(?:messages?|msgs?)?\b",
            rf"\b{action}\b[^\n]{{0,40}}?\b(\d{{1,4}})\s*(?:messages?|msgs?)\b",
        )
        for pattern in patterns:
            match = re.search(pattern, text or "", re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def _extract_purge_target_id(text: str) -> Optional[int]:
        # Take the FIRST match, not the last. "purge 20 messages from @Alice
        # because reported by @Bob" yields (from, Alice) then (by, Bob); using
        # matches[-1] purged Bob -- the person who reported it -- and reported
        # success. The first "from/by/of @user" is the requested target; any
        # later mention is attribution or context.
        match = re.search(r"\b(?:from|by|of)\s+<@!?(\d{15,22})>", text, re.IGNORECASE)
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None

    @staticmethod
    def _extract_purge_channel_id(text: str) -> Optional[int]:
        matches = list(_CHANNEL_MENTION_RE.finditer(text or ""))
        if not matches:
            return None
        try:
            return int(matches[-1].group(1))
        except ValueError:
            return None

    @staticmethod
    def _purge_scope_is_ambiguous(text: str, args: Dict[str, Any]) -> bool:
        low = re.sub(r"\s+", " ", (text or "").strip().lower())
        if not args.get("target_user_id"):
            return False
        if not re.search(r"\ball\b", low):
            return False
        if args.get("channel_id") or args.get("lookback_seconds"):
            return False
        if re.search(r"\b(?:in|from)\s+(?:this channel|this chat|here|current channel)\b", low):
            return False
        if re.search(r"\b(?:all channels|every channel|serverwide|server-wide|whole server|entire server)\b", low):
            return False
        return True

    @staticmethod
    def _purge_all_channels_requested(text: str) -> bool:
        low = re.sub(r"\s+", " ", (text or "").strip().lower())
        return bool(re.search(r"\b(?:all channels|every channel|serverwide|server-wide|whole server|entire server)\b", low))

    def _extract_purge_target_from_mentions(self, message: discord.Message) -> Optional[int]:
        if not self.bot.user:
            return None

        mentions = [int(match.group(1)) for match in re.finditer(r"<@!?(\d{15,22})>", message.content or "")]
        bot_id = self.bot.user.id
        if mentions and mentions[0] == bot_id:
            mentions = mentions[1:]
        if not mentions:
            return None

        content = self.clean_content(message)
        explicit_target = self._extract_purge_target_id(content)
        if explicit_target is not None:
            return explicit_target

        if re.search(r"\b(?:from|by|of)\s*$", content, re.IGNORECASE):
            return mentions[0]
        if re.match(r"^\s*(?:purge|clear|clean)\b", content, re.IGNORECASE):
            return mentions[0]
        if re.search(r"\b(?:purge|clear|clean|delete|remove|wipe|nuke)\b", content, re.IGNORECASE) and re.search(
            r"\b(?:messages?|msgs?|chat)\b", content, re.IGNORECASE
        ):
            return mentions[0]
        return None

    @staticmethod
    def _extract_dm_args(content: str) -> Dict[str, Any]:
        text = (content or "").strip()
        patterns = (
            r"^(?:dm|message|direct\s+message)\s+<@!?(\d{15,22})>\s*[,;:]?\s+(.+)$",
            r"^send\s+(?:a\s+)?dm\s+to\s+<@!?(\d{15,22})>\s*[,;:]?\s+(.+)$",
            r"^send\s+<@!?(\d{15,22})>\s*[,;:]?\s+(?!to\b|into\b|in\b|vc\b|voice\b)(.+)$",
        )
        for pattern in patterns:
            match = re.match(pattern, text, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            return {
                "target_user_id": int(match.group(1)),
                "message": match.group(2).strip().strip('"'),
            }
        return {}

    def _extract_dm_target_from_mentions(self, message: discord.Message) -> Optional[int]:
        if not self.bot.user:
            return None
        mentions = [
            user.id
            for user in message.mentions
            if user.id != self.bot.user.id and not getattr(user, "bot", False)
        ]
        return mentions[0] if mentions else None

    def _extract_dm_message(self, content: str) -> Optional[str]:
        args = self._extract_dm_args(content)
        if args.get("message"):
            return str(args["message"])
        text = (content or "").strip()
        text = re.sub(r"^(?:dm|message|direct\s+message)\s+", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"^send\s+(?:a\s+)?dm\s+to\s+", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"^send\s+", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"^<@!?\d{15,22}>\s*[,;:]?\s*", "", text).strip()
        return text.strip('"') or None

    def _extract_purge_args(self, content: str) -> Dict[str, Any]:
        args: Dict[str, Any] = {}
        amount = self._extract_purge_amount(content)
        if amount is not None:
            args["amount"] = amount
        target_id = self._extract_purge_target_id(content)
        if target_id is None and (
            re.match(r"^\s*(?:purge|clear|clean)\b", content or "", re.IGNORECASE)
            or (
                re.search(r"\b(?:delete|remove|wipe|nuke|purge|clear|clean)\b", content or "", re.IGNORECASE)
                and re.search(r"\b(?:messages?|msgs?|chat)\b", content or "", re.IGNORECASE)
            )
        ):
            mention = _MENTION_RE.search(content or "")
            if mention:
                try:
                    target_id = int(mention.group(1))
                except ValueError:
                    target_id = None
        if target_id is not None:
            args["target_user_id"] = target_id
        channel_id = self._extract_purge_channel_id(content)
        if channel_id is not None:
            args["channel_id"] = channel_id
        lookback_seconds = self._parse_lookback_seconds(content)
        if lookback_seconds:
            args["lookback_seconds"] = lookback_seconds
        if self._purge_all_channels_requested(content):
            args["all_channels_requested"] = True
        if self._purge_scope_is_ambiguous(content, args):
            args["needs_channel_scope"] = True
        return args

    def _extract_reason(self, text: str) -> Optional[str]:
        if not text:
            return None
        m = re.search(r"\b(?:because|reason\s*:?)\s+(.+)$", text, re.IGNORECASE)
        if not m:
            return None
        return m.group(1).strip().rstrip(".") or None

    def _extract_role_name(self, text: str) -> Optional[str]:
        if not text:
            return None
        m = re.search(r'["\']([^"\']{1,100})["\']', text)
        if m:
            return m.group(1).strip()
        m = re.search(
            r"(?:add|give|remove|take)\s+role\s+(.+?)(?:\s+(?:to|from|for|because|reason)\b|$)",
            text, re.IGNORECASE,
        )
        if not m:
            return None
        raw = m.group(1).strip().strip("`").lstrip("@").strip()
        return _ROLE_MENTION_RE.sub(r"\1", raw) or None

    @staticmethod
    def _is_bulk_timeout_request(text: str) -> bool:
        """Return whether a timeout request explicitly targets a member set."""
        normalized = (text or "").lower().replace("’", "'")
        return bool(
            re.search(
                r"\b(?:everyone|everybody|anyone|anybody|all\s+(?:members?|users?|people)|"
                r"members?|users?|people)\s+(?:who|that|without\b)",
                normalized,
            )
            or re.search(
                r"\b(?:mute|timeout|time\s+out)\s+(?:everyone|everybody|anyone|anybody|all)\b",
                normalized,
            )
        )

    def _bulk_timeout_arguments(
        self,
        message: discord.Message,
        content: str,
    ) -> Dict[str, Any]:
        """Build a grounded bulk-timeout scope from the Discord message."""
        args: Dict[str, Any] = {"all_members": True}
        excluded_user_ids: list[int] = []
        normalized = (content or "").replace("’", "'")
        exclusion_clause = re.search(
            r"\b(?:except(?:\s+for)?|excluding)\s+(.+?)(?:\s+\b(?:for|because|reason)\b|$)",
            normalized,
            re.IGNORECASE,
        )
        if exclusion_clause:
            clause = exclusion_clause.group(1)
            if re.search(r"\b(?:me|myself)\b", clause, re.IGNORECASE):
                excluded_user_ids.append(message.author.id)
            for member in getattr(message, "mentions", []) or []:
                if member.bot or (self.bot.user and member.id == self.bot.user.id):
                    continue
                if member.id not in excluded_user_ids:
                    excluded_user_ids.append(member.id)
        if excluded_user_ids:
            args["exclude_user_ids"] = excluded_user_ids

        role_mentions = list(getattr(message, "role_mentions", []) or [])
        if role_mentions:
            role = role_mentions[0]
            args["exclude_role_id"] = role.id
            args["exclude_role_name"] = role.name
        elif role_match := _ROLE_MENTION_RE.search(content or ""):
            args["exclude_role_id"] = int(role_match.group(1))
        elif not excluded_user_ids:
            role_name_match = re.search(
                r"\b(?:without|except(?:\s+for)?|who\s+(?:doesn't|does\s+not|don't|do\s+not)\s+have)"
                r"\s+(?:the\s+)?role\s+(.+?)"
                r"(?:\s+\b(?:for|because|reason)\b|\s+\d+\s*(?:s|m|h|d|w)\b|$)",
                normalized,
                re.IGNORECASE,
            )
            if role_name_match:
                role_name = role_name_match.group(1).strip(" .,:;`'\"@")
                if role_name:
                    args["exclude_role_name"] = role_name
        return args

    def _extract_channel_create_args(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None

        m = re.match(
            r"^\s*(?:create|make|add|build|open|spin\s+up|set\s+up)\s+(?:a|an)?\s*"
            r"(?:(text|voice|stage|forum)\s+)?(?:channel|room)\b"
            r"(?:\s+(?:named|called|as)?\s*(.+))?$",
            text,
            re.IGNORECASE,
        )
        if not m:
            return None

        channel_type = (m.group(1) or "text").lower()
        raw_name = (m.group(2) or "").strip()
        raw_name = re.split(r"\s+\b(?:because|reason|in category|under category)\b", raw_name, maxsplit=1, flags=re.IGNORECASE)[0]
        name = raw_name.strip().strip("`'\"#").strip()

        args: Dict[str, Any] = {"type": channel_type}
        if name:
            args["name"] = name

        reason = self._extract_reason(text)
        if reason:
            args["reason"] = reason

        return args

    def _extract_simple_name_after(self, text: str, object_words: str) -> Optional[str]:
        m = re.search(
            r"\b(?:named|called|as)\s+([#@\w][\w\- ]{0,90})$",
            text,
            re.IGNORECASE,
        )
        if not m:
            m = re.search(
                rf"\b{object_words}\b\s+(?:named\s+|called\s+|as\s+)?([#@\w][\w\- ]{{0,90}})$",
                text,
                re.IGNORECASE,
            )
        if not m:
            return None
        name = re.split(r"\s+\b(?:because|reason|for|in category|under category)\b", m.group(1), maxsplit=1, flags=re.IGNORECASE)[0]
        name = name.strip().strip("`'\"#@").strip()
        return name or None

    def _extract_target_hint(self, text: str) -> Optional[str]:
        m = re.search(
            r"\b(?:to|from|on)\s+(.+?)(?:\s+(?:for|because|reason)\b|$)",
            text, re.IGNORECASE,
        )
        return m.group(1).strip() if m else None

    def _extract_message_id(self, text: str) -> Optional[int]:
        m = _SNOWFLAKE_RE.search(text)
        if not m:
            return None
        try:
            return int(m.group(1))
        except ValueError:
            return None

    def _extract_trailing_reason(self, text: str, command: str) -> Optional[str]:
        """Extracts reason from text like 'warn @user ur silly'."""
        text = re.sub(rf"^{command}\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<@!?\d+>", "", text)
        text = text.strip()
        return text or None

    def _extract_moderation_reason(self, text: str, command: str) -> Optional[str]:
        """Extract a reason from compact moderation commands without target filler."""
        raw = re.sub(rf"^\s*{command}\b", "", text or "", flags=re.IGNORECASE)
        raw = re.sub(r"<@!?\d+>|<@&\d+>|<#\d+>", " ", raw)
        raw = re.sub(r"\b\d+\s*(?:s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days|w|week|weeks)\b", " ", raw, flags=re.IGNORECASE)
        raw = _REPLY_TARGET_RE.sub(" ", raw)
        raw = re.sub(r"\b(?:for|because|reason\s*:?)\b", " ", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s+", " ", raw).strip(" .,:;-")
        return raw or None

    def _extract_warning_count(self, text: str) -> int:
        # A count is only a count when it sits in the command, next to the verb
        # or the target -- not anywhere in the sentence. "<n> times" matched
        # globally, so "warn @user because he did it 3 times" issued THREE
        # warnings, enough to trip auto-escalation into a mute/kick/ban from a
        # single message. Narrative text after for/because/reason:, or after a
        # pronoun/verb describing the offence, is the moderator explaining what
        # happened rather than asking for repeats.
        raw_text = text or ""
        command_part = re.split(
            r"\b(?:for|because|reason\s*:?|since|as\s+they|after)\b",
            raw_text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        # Drop a trailing narrative clause ("he spammed 5 times in a row"):
        # a subject pronoun followed by a past-tense verb starts a description.
        command_part = re.split(
            r"\b(?:he|she|they|it|this\s+user|the\s+user)\s+\w+ed\b",
            command_part,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        match = self._WARNING_COUNT_RE.search(command_part)
        if not match:
            return 1
        raw = next((group for group in match.groups() if group), "1").lower()
        if raw.isdigit():
            return int(raw)
        return self._WARNING_NUMBER_WORDS.get(raw, 1)

    def _extract_warning_reason(self, text: str) -> Optional[str]:
        raw = text or ""
        explicit = re.search(
            r"\b(?:for|because|reason\s*:?)\s+(.+)$",
            raw,
            re.IGNORECASE,
        )
        if explicit:
            reason = explicit.group(1)
        else:
            reason = re.sub(
                r"^\s*(?:warn|give|issue|add|apply)\b",
                " ",
                raw,
                count=1,
                flags=re.IGNORECASE,
            )
            reason = re.sub(r"<@!?\d+>|<@&\d+>|<#\d+>", " ", reason)
            reason = self._WARNING_COUNT_RE.sub(" ", reason, count=1)
            reason = re.sub(
                r"\b(?:warn(?:ing)?s?|times?)\b",
                " ",
                reason,
                flags=re.IGNORECASE,
            )
            reason = _REPLY_TARGET_RE.sub(" ", reason)
            reason = re.sub(
                r"^\s*(?:to|on)?\s*(?:them|him|her|this\s+(?:user|member)|the\s+(?:user|member))?\s*",
                "",
                reason,
                count=1,
                flags=re.IGNORECASE,
            )
        reason = re.sub(r"\s+", " ", reason).strip(" .,:;-")
        return reason or None

    def _warning_arguments(self, message: discord.Message, content: str) -> Dict[str, Any]:
        args: Dict[str, Any] = {"warning_count": self._extract_warning_count(content)}
        previous_message_target = self._targets_previous_message_author(content)
        if previous_message_target:
            args["target_previous_message_author"] = True
            args["respect_staff_protection"] = bool(
                re.search(r"\b(?:bot|staff|protected)\b", content, re.IGNORECASE)
            )
        explicit_reason = re.search(
            r"\b(?:for|because|reason\s*:?)\s+(.+)$",
            content,
            re.IGNORECASE,
        )
        reason = (
            explicit_reason.group(1).strip(" .,:;-")
            if explicit_reason
            else "Message immediately before the moderation request"
            if previous_message_target
            else self._extract_warning_reason(content)
        )
        if reason:
            args["reason"] = reason
        non_bot_mentions = [
            member
            for member in message.mentions
            if not member.bot and (not self.bot.user or member.id != self.bot.user.id)
        ]
        if non_bot_mentions:
            args["target_user_id"] = non_bot_mentions[0].id
        return args

    def _quick_route(self, message: discord.Message, content: str) -> Optional[Decision]:
        if not content:
            return None
        content = self._strip_action_prefix(content)
        low = content.strip().lower().lstrip(" ,:;-")

        if self._looks_like_warning_action(low):
            return Decision(
                type=DecisionType.TOOL_CALL,
                reason="rule: warn",
                tool=ToolType.WARN,
                arguments=self._warning_arguments(message, content),
            )

        if self._looks_like_warning_lookup(low):
            args: Dict[str, Any] = {}
            non_bot_mentions = [
                member
                for member in message.mentions
                if not member.bot and (not self.bot.user or member.id != self.bot.user.id)
            ]
            if non_bot_mentions:
                args["target_user_id"] = non_bot_mentions[0].id
            return Decision(
                type=DecisionType.TOOL_CALL,
                reason="rule: get_warnings",
                tool=ToolType.GET_WARNINGS,
                arguments=args,
            )

        if self._looks_like_history_lookup(low):
            args: Dict[str, Any] = {}
            non_bot_mentions = [
                member
                for member in message.mentions
                if not member.bot and (not self.bot.user or member.id != self.bot.user.id)
            ]
            if non_bot_mentions:
                args["target_user_id"] = non_bot_mentions[0].id
            return Decision(
                type=DecisionType.TOOL_CALL,
                reason="rule: get_history",
                tool=ToolType.GET_HISTORY,
                arguments=args,
            )

        if re.match(r"^(add|give)\s+role\b", low):
            role = self._extract_role_name(content)
            return Decision(
                type=DecisionType.TOOL_CALL, reason="rule: add_role",
                tool=ToolType.ADD_ROLE,
                arguments={"role_name": role} if role else {},
            )
        if re.match(r"^(remove|take)\s+role\b", low):
            role = self._extract_role_name(content)
            return Decision(
                type=DecisionType.TOOL_CALL, reason="rule: remove_role",
                tool=ToolType.REMOVE_ROLE,
                arguments={"role_name": role} if role else {},
            )
        if re.match(r"^(create|make|add|build|open|spin\s+up|set\s+up)\s+(?:a|an)?\s*(?:(?:text|voice|stage|forum)\s+)?(?:channel|room)\b", low):
            return Decision(
                type=DecisionType.TOOL_CALL, reason="rule: create_channel",
                tool=ToolType.CREATE_CHANNEL,
                arguments=self._extract_channel_create_args(content) or {},
            )
        if re.match(r"^(unmute|untimeout|remove\s+timeout|un-?timeout)\b", low):
            return Decision(type=DecisionType.TOOL_CALL, reason="rule: untimeout", tool=ToolType.UNTIMEOUT, arguments={})
        if re.match(r"^(mute|timeout|time\s*out)\b", low):
            args: Dict[str, Any] = {}
            bulk_timeout = self._is_bulk_timeout_request(content)
            if bulk_timeout:
                args.update(self._bulk_timeout_arguments(message, content))
            secs = self._parse_duration_seconds(content)
            if secs:
                args["seconds"] = secs
            reason = (
                self._extract_reason(content)
                if bulk_timeout
                else self._extract_moderation_reason(content, r"(?:mute|timeout|time\s*out)")
            )
            if reason:
                args["reason"] = reason
            if not bulk_timeout and message.mentions:
                non_bot = [
                    mentioned
                    for mentioned in message.mentions
                    if not mentioned.bot
                    and (not self.bot.user or mentioned.id != self.bot.user.id)
                ]
                if non_bot:
                    args["target_user_id"] = non_bot[0].id
            return Decision(type=DecisionType.TOOL_CALL, reason="rule: timeout", tool=ToolType.TIMEOUT, arguments=args)
        dm_args = self._extract_dm_args(content)
        if dm_args:
            return Decision(
                type=DecisionType.TOOL_CALL,
                reason="rule: dm_user",
                tool=ToolType.DM_USER,
                arguments=dm_args,
            )
        m = re.match(r"^(purge|clear|clean)\b(?:\s+(\d{1,4}))?", low)
        if m:
            args = self._extract_purge_args(content)
            return Decision(type=DecisionType.TOOL_CALL, reason="rule: purge", tool=ToolType.PURGE, arguments=args)
        if re.match(r"^(delete|remove|wipe|nuke)\b.*\b(?:messages?|msgs?|chat)\b", low):
            return Decision(
                type=DecisionType.TOOL_CALL,
                reason="rule: targeted purge",
                tool=ToolType.PURGE,
                arguments=self._extract_purge_args(content),
            )
        if re.match(r"^kick\b", low):
            reason = self._extract_moderation_reason(content, "kick")
            args = {"reason": reason} if reason else {}
            if message.mentions:
                non_bot = [m for m in message.mentions if not m.bot and (not self.bot.user or m.id != self.bot.user.id)]
                if non_bot:
                    args["target_user_id"] = non_bot[0].id
            return Decision(type=DecisionType.TOOL_CALL, reason="rule: kick", tool=ToolType.KICK, arguments=args)
        if re.match(r"^unban\b", low):
            reason = self._extract_moderation_reason(content, "unban")
            args = {"reason": reason} if reason else {}
            if message.mentions:
                non_bot = [m for m in message.mentions if not m.bot and (not self.bot.user or m.id != self.bot.user.id)]
                if non_bot:
                    args["target_user_id"] = non_bot[0].id
            return Decision(type=DecisionType.TOOL_CALL, reason="rule: unban", tool=ToolType.UNBAN, arguments=args)
        if re.match(r"^ban\b", low):
            reason = self._extract_moderation_reason(content, "ban")
            args = {"reason": reason} if reason else {}
            if message.mentions:
                non_bot = [m for m in message.mentions if not m.bot and (not self.bot.user or m.id != self.bot.user.id)]
                if non_bot:
                    args["target_user_id"] = non_bot[0].id
            return Decision(type=DecisionType.TOOL_CALL, reason="rule: ban", tool=ToolType.BAN, arguments=args)
        return None
