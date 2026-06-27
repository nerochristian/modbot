"""Deterministic, testable rule engine for the AutoMod cog.

This module does not perform Discord moderation actions.  It only decides
whether a message violates a configured rule and which policy should be used.
Keeping detection separate from enforcement makes dry-run testing safe and
prevents rule code from deleting or punishing users by accident.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import unicodedata
from collections import Counter, OrderedDict, defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Iterable, Mapping, Optional
from urllib.parse import urlsplit

import aiohttp


logger = logging.getLogger("AutoMod.Engine")


class Severity(Enum):
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class Action(str, Enum):
    LOG = "log"
    WARN = "warn"
    TIMEOUT = "timeout"
    KICK = "kick"
    BAN = "ban"
    QUARANTINE = "quarantine"


class Category(str, Enum):
    CONTENT = "content"
    BEHAVIOR = "behavior"
    SECURITY = "security"
    IDENTITY = "identity"


@dataclass(frozen=True)
class RuleMatch:
    rule: str
    reason: str
    severity: Severity
    category: Category
    delete_message: bool = True
    evidence: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RecentViolation:
    guild_id: int
    user_id: int
    channel_id: int
    rule: str
    reason: str
    severity: str
    occurred_at: float


ZERO_WIDTH_TRANSLATION = str.maketrans("", "", "\u200b\u200c\u200d\u2060\ufeff")
LEET_TRANSLATION = str.maketrans(
    {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "@": "a",
        "$": "s",
        "!": "i",
        "а": "a",  # Cyrillic a
        "е": "e",  # Cyrillic e
        "і": "i",  # Cyrillic i
        "о": "o",  # Cyrillic o
        "с": "c",  # Cyrillic c
        "р": "p",  # Cyrillic p
        "х": "x",  # Cyrillic x
    }
)
URL_RE = re.compile(
    r"(?i)\b((?:https?://|www\.)[^\s<>]+|(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/[^\s<>]*)?)"
)
INVITE_RE = re.compile(
    r"(?i)(?:https?://)?(?:www\.)?(?:discord\.gg|discord(?:app)?\.com/invite|dsc\.gg)/([\w-]+)"
)


def normalize_text(value: str) -> str:
    """Normalize common Unicode and leetspeak evasions without losing words."""
    value = unicodedata.normalize("NFKC", value or "").translate(ZERO_WIDTH_TRANSLATION)
    value = value.casefold().translate(LEET_TRANSLATION)
    value = "".join(
        char for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", value).strip()


def _keyword_pattern(keyword: str) -> Optional[re.Pattern[str]]:
    normalized = normalize_text(keyword)
    characters = [re.escape(char) for char in normalized if char.isalnum()]
    if not characters:
        return None
    flexible = r"[\W_]*".join(characters)
    return re.compile(rf"(?<!\w){flexible}(?!\w)", re.IGNORECASE)


def _unique_strings(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip().casefold()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def normalize_domain(value: str) -> str:
    raw = (value or "").strip().casefold().rstrip(".")
    if not raw:
        return ""
    candidate = raw if "://" in raw else f"https://{raw}"
    try:
        host = urlsplit(candidate).hostname or ""
        return host.encode("idna").decode("ascii").casefold().rstrip(".")
    except (UnicodeError, ValueError):
        return ""


def domain_matches(domain: str, configured_domain: str) -> bool:
    configured = normalize_domain(configured_domain)
    return bool(configured and (domain == configured or domain.endswith(f".{configured}")))


def extract_domains(content: str) -> list[str]:
    domains: list[str] = []
    for raw in URL_RE.findall(content or ""):
        cleaned = raw.rstrip(".,;:!?)]}\"")
        domain = normalize_domain(cleaned)
        if domain and domain not in domains:
            domains.append(domain)
    return domains


class Rule:
    name = "base"
    setting_key = ""
    priority = 0

    async def check(
        self,
        message: Any,
        settings: Mapping[str, Any],
        *,
        dry_run: bool = False,
    ) -> Optional[RuleMatch]:
        raise NotImplementedError

    async def close(self) -> None:
        return None

    def prune(self, now: float) -> None:
        return None


class ScamRule(Rule):
    name = "scams"
    setting_key = "automod_scam_protection"
    priority = 100
    _strong_patterns = tuple(
        re.compile(pattern, re.IGNORECASE)
        for pattern in (
            r"\bfree\s+(?:discord\s+)?nitro\b",
            r"\bclaim\s+(?:your\s+)?(?:prize|reward|gift)\b",
            r"\b(?:steam|discord)\s+gift\b",
            r"\bverify\s+(?:your\s+)?account\b",
            r"\bcrypto\s+(?:giveaway|airdrop)\b",
        )
    )
    _dangerous_domains = (
        "grabify.link",
        "iplogger.org",
        "iplogger.com",
        "2no.co",
        "yip.su",
    )

    async def check(self, message: Any, settings: Mapping[str, Any], *, dry_run: bool = False) -> Optional[RuleMatch]:
        content = normalize_text(getattr(message, "content", ""))
        domains = extract_domains(getattr(message, "content", ""))
        dangerous = [
            domain for domain in domains
            if any(domain_matches(domain, blocked) for blocked in self._dangerous_domains)
        ]
        if dangerous:
            return RuleMatch(
                self.name,
                "Known tracking or credential-theft link",
                Severity.CRITICAL,
                Category.SECURITY,
                evidence=tuple(dangerous[:3]),
            )

        matched = [pattern.pattern for pattern in self._strong_patterns if pattern.search(content)]
        has_link = bool(domains or INVITE_RE.search(getattr(message, "content", "")))
        mass_ping = "@everyone" in content or "@here" in content
        if matched and has_link:
            return RuleMatch(
                self.name,
                "Likely scam or phishing message",
                Severity.CRITICAL if mass_ping else Severity.HIGH,
                Category.SECURITY,
                evidence=tuple(matched[:2]),
            )
        if mass_ping and has_link and any(word in content for word in ("free", "claim", "gift", "verify")):
            return RuleMatch(
                self.name,
                "Suspicious mass mention with a promotional link",
                Severity.HIGH,
                Category.SECURITY,
            )
        return None


class BadWordsRule(Rule):
    name = "words"
    setting_key = "automod_badwords_enabled"
    priority = 90

    def __init__(self) -> None:
        self._cache_key: tuple[str, ...] = ()
        self._patterns: list[tuple[str, re.Pattern[str]]] = []

    def _patterns_for(self, words: Iterable[Any]) -> list[tuple[str, re.Pattern[str]]]:
        normalized_words = tuple(_unique_strings(words))
        if normalized_words != self._cache_key:
            compiled: list[tuple[str, re.Pattern[str]]] = []
            for word in normalized_words:
                pattern = _keyword_pattern(word)
                if pattern is not None:
                    compiled.append((word, pattern))
            self._cache_key = normalized_words
            self._patterns = compiled
        return self._patterns

    async def check(self, message: Any, settings: Mapping[str, Any], *, dry_run: bool = False) -> Optional[RuleMatch]:
        content = normalize_text(getattr(message, "content", ""))
        if not content:
            return None
        matched = [word for word, pattern in self._patterns_for(settings.get("automod_badwords", [])) if pattern.search(content)]
        if not matched:
            return None
        return RuleMatch(
            self.name,
            "Blocked word or phrase",
            Severity.HIGH if len(matched) > 1 else Severity.MEDIUM,
            Category.CONTENT,
            evidence=tuple(matched[:3]),
        )


class MentionsRule(Rule):
    name = "mentions"
    setting_key = "automod_mentions_enabled"
    priority = 80

    async def check(self, message: Any, settings: Mapping[str, Any], *, dry_run: bool = False) -> Optional[RuleMatch]:
        limit = max(1, int(settings.get("automod_max_mentions", 5)))
        user_ids = {getattr(item, "id", item) for item in getattr(message, "mentions", [])}
        role_ids = {getattr(item, "id", item) for item in getattr(message, "role_mentions", [])}
        total = len(user_ids) + len(role_ids)
        if total < limit:
            return None
        severity = Severity.CRITICAL if total >= limit * 2 else Severity.HIGH
        return RuleMatch(
            self.name,
            f"Mass mention spam ({total} unique mentions)",
            severity,
            Category.BEHAVIOR,
            metadata={"count": total},
        )


class SpamRule(Rule):
    name = "spam"
    setting_key = "automod_spam_enabled"
    priority = 85

    def __init__(self) -> None:
        self._messages: dict[tuple[int, int], Deque[tuple[float, str]]] = defaultdict(deque)

    @staticmethod
    def _fingerprint(content: str) -> str:
        normalized = normalize_text(content)
        return hashlib.blake2s(normalized.encode("utf-8"), digest_size=8).hexdigest()

    async def check(self, message: Any, settings: Mapping[str, Any], *, dry_run: bool = False) -> Optional[RuleMatch]:
        content = getattr(message, "content", "") or ""
        normalized = normalize_text(content)
        if not normalized:
            return None

        if len(normalized) >= 16:
            compact = re.sub(r"\s", "", normalized)
            if compact:
                most_common = Counter(compact).most_common(1)[0][1]
                if most_common / len(compact) >= 0.8:
                    return RuleMatch(
                        self.name,
                        "Repeated-character spam",
                        Severity.LOW,
                        Category.BEHAVIOR,
                    )

        if dry_run:
            return None

        guild_id = int(getattr(getattr(message, "guild", None), "id", 0))
        user_id = int(getattr(getattr(message, "author", None), "id", 0))
        key = (guild_id, user_id)
        now = time.monotonic()
        spam_window = min(60, max(2, int(settings.get("automod_spam_window", 5))))
        duplicate_window = min(300, max(5, int(settings.get("automod_duplicate_window", 30))))
        retention = max(spam_window, duplicate_window)
        entries = self._messages[key]
        while entries and now - entries[0][0] > retention:
            entries.popleft()

        fingerprint = self._fingerprint(content)
        entries.append((now, fingerprint))
        flood_count = sum(1 for created, _ in entries if now - created <= spam_window)
        flood_limit = min(50, max(2, int(settings.get("automod_spam_threshold", 5))))
        if flood_count >= flood_limit:
            return RuleMatch(
                self.name,
                f"Message flood ({flood_count} messages in {spam_window}s)",
                Severity.HIGH,
                Category.BEHAVIOR,
                metadata={"count": flood_count, "window": spam_window},
            )

        duplicate_count = sum(
            1 for created, existing in entries
            if existing == fingerprint and now - created <= duplicate_window
        )
        duplicate_limit = min(20, max(2, int(settings.get("automod_duplicate_threshold", 3))))
        if duplicate_count >= duplicate_limit:
            return RuleMatch(
                self.name,
                f"Duplicate message spam ({duplicate_count} copies in {duplicate_window}s)",
                Severity.MEDIUM,
                Category.BEHAVIOR,
                metadata={"count": duplicate_count, "window": duplicate_window},
            )
        return None

    def prune(self, now: float) -> None:
        stale_keys: list[tuple[int, int]] = []
        for key, entries in self._messages.items():
            while entries and now - entries[0][0] > 300:
                entries.popleft()
            if not entries:
                stale_keys.append(key)
        for key in stale_keys:
            self._messages.pop(key, None)


class InvitesRule(Rule):
    name = "invites"
    setting_key = "automod_invites_enabled"
    priority = 75

    async def check(self, message: Any, settings: Mapping[str, Any], *, dry_run: bool = False) -> Optional[RuleMatch]:
        content = getattr(message, "content", "") or ""
        codes = [match.group(1).casefold() for match in INVITE_RE.finditer(content)]
        if not codes:
            return None
        allowed = {
            value.rsplit("/", 1)[-1].casefold()
            for value in _unique_strings(settings.get("automod_allowed_invites", []))
        }
        blocked = [code for code in codes if code not in allowed]
        if not blocked:
            return None
        return RuleMatch(
            self.name,
            "Discord invite is not allowed",
            Severity.MEDIUM,
            Category.CONTENT,
            evidence=tuple(blocked[:3]),
        )


class LinksRule(Rule):
    name = "links"
    setting_key = "automod_links_enabled"
    priority = 70
    _suspicious_domains = (
        "bit.ly",
        "tinyurl.com",
        "tiny.one",
        "cutt.ly",
        "rb.gy",
        "is.gd",
    )

    async def check(self, message: Any, settings: Mapping[str, Any], *, dry_run: bool = False) -> Optional[RuleMatch]:
        domains = extract_domains(getattr(message, "content", ""))
        if not domains:
            return None
        allowed_values = list(settings.get("automod_links_whitelist", [])) + list(
            settings.get("automod_whitelisted_domains", [])
        )
        blocked: list[str] = []
        mode = str(settings.get("automod_links_mode", "dangerous")).casefold()
        for domain in domains:
            if any(domain_matches(domain, allowed) for allowed in allowed_values):
                continue
            if mode == "allowlist" or any(
                domain_matches(domain, suspicious) for suspicious in self._suspicious_domains
            ):
                blocked.append(domain)
        if not blocked:
            return None
        reason = "Domain is not on the allowlist" if mode == "allowlist" else "Shortened or suspicious link"
        return RuleMatch(
            self.name,
            reason,
            Severity.HIGH if mode == "dangerous" else Severity.MEDIUM,
            Category.SECURITY if mode == "dangerous" else Category.CONTENT,
            evidence=tuple(blocked[:3]),
        )


class CapsRule(Rule):
    name = "caps"
    setting_key = "automod_caps_enabled"
    priority = 60

    async def check(self, message: Any, settings: Mapping[str, Any], *, dry_run: bool = False) -> Optional[RuleMatch]:
        content = getattr(message, "content", "") or ""
        letters = [char for char in content if char.isalpha()]
        minimum = min(500, max(5, int(settings.get("automod_caps_min_length", 10))))
        if len(letters) < minimum:
            return None
        percentage = round(sum(char.isupper() for char in letters) * 100 / len(letters))
        threshold = min(100, max(50, int(settings.get("automod_caps_percentage", 70))))
        if percentage < threshold:
            return None
        return RuleMatch(
            self.name,
            f"Excessive capital letters ({percentage}%)",
            Severity.LOW,
            Category.BEHAVIOR,
            metadata={"percentage": percentage},
        )


class NewAccountRule(Rule):
    name = "new_accounts"
    setting_key = "automod_newaccount_enabled"
    priority = 40

    async def check(self, message: Any, settings: Mapping[str, Any], *, dry_run: bool = False) -> Optional[RuleMatch]:
        author = getattr(message, "author", None)
        created_at = getattr(author, "created_at", None)
        if created_at is None:
            return None
        threshold = min(365, max(0, int(settings.get("automod_newaccount_days", 7))))
        if threshold == 0:
            return None
        now = getattr(message, "created_at", None)
        if now is None:
            from discord.utils import utcnow
            now = utcnow()
        age_days = max(0, int((now - created_at).total_seconds() // 86400))
        if age_days >= threshold:
            return None
        return RuleMatch(
            self.name,
            f"Account is only {age_days} day{'s' if age_days != 1 else ''} old",
            Severity.INFO,
            Category.IDENTITY,
            delete_message=False,
            metadata={"age_days": age_days},
        )


class AIRule(Rule):
    name = "ai"
    setting_key = "automod_ai_enabled"
    priority = 50

    def __init__(self) -> None:
        self._api_key = os.getenv("DO_API_KEY", "").strip()
        self._base_url = os.getenv("DO_INFERENCE_BASE_URL", "https://inference.digitalocean.com/v1").rstrip("/")
        self._model = os.getenv("DO_AUTOMOD_MODEL", "deepseek-4-flash")
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: OrderedDict[str, tuple[float, Optional[RuleMatch]]] = OrderedDict()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=12, connect=4)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def check(self, message: Any, settings: Mapping[str, Any], *, dry_run: bool = False) -> Optional[RuleMatch]:
        if not self._api_key:
            return None
        content = (getattr(message, "content", "") or "").strip()
        if len(content) < 8:
            return None
        cache_key = hashlib.blake2s(content.encode("utf-8"), digest_size=16).hexdigest()
        now = time.monotonic()
        cached = self._cache.get(cache_key)
        if cached and cached[0] > now:
            self._cache.move_to_end(cache_key)
            return cached[1]

        prompt = (
            "Classify this Discord message for harassment, credible threats, sexual exploitation, "
            "or targeted hate. Return JSON only with keys violation (boolean), severity (1-10), "
            "and reason (short string). Do not flag ordinary profanity or disagreement.\n\n"
            f"Message: {content[:2500]}"
        )
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 150,
            "response_format": {"type": "json_object"},
        }
        try:
            session = await self._get_session()
            async with session.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
            ) as response:
                if response.status != 200:
                    logger.warning("AI moderation returned HTTP %s", response.status)
                    result = None
                else:
                    body = await response.json(content_type=None)
                    raw = body["choices"][0]["message"]["content"].strip()
                    if raw.startswith("```"):
                        raw = raw.strip("`")
                        if raw.startswith("json"):
                            raw = raw[4:].strip()
                    parsed = json.loads(raw)
                    score = min(10, max(1, int(parsed.get("severity", 1))))
                    minimum = min(10, max(1, int(settings.get("automod_ai_min_severity", 7))))
                    if parsed.get("violation") is True and score >= minimum:
                        severity = Severity.CRITICAL if score >= 9 else Severity.HIGH if score >= 7 else Severity.MEDIUM
                        result = RuleMatch(
                            self.name,
                            f"AI review: {str(parsed.get('reason') or 'policy violation')[:180]}",
                            severity,
                            Category.CONTENT,
                            metadata={"score": score},
                        )
                    else:
                        result = None
        except (aiohttp.ClientError, TimeoutError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("AI moderation check failed: %s", exc)
            result = None

        self._cache[cache_key] = (now + 600, result)
        self._cache.move_to_end(cache_key)
        while len(self._cache) > 500:
            self._cache.popitem(last=False)
        return result

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()

    def prune(self, now: float) -> None:
        for key, (expires_at, _) in list(self._cache.items()):
            if expires_at <= now:
                self._cache.pop(key, None)


RULE_SETTING_KEYS: dict[str, str] = {
    "words": "automod_badwords_enabled",
    "spam": "automod_spam_enabled",
    "mentions": "automod_mentions_enabled",
    "caps": "automod_caps_enabled",
    "links": "automod_links_enabled",
    "invites": "automod_invites_enabled",
    "scams": "automod_scam_protection",
    "new_accounts": "automod_newaccount_enabled",
    "ai": "automod_ai_enabled",
}


class AutoModEngine:
    """Evaluate enabled rules and maintain bounded runtime-only telemetry."""

    def __init__(self) -> None:
        rules: list[Rule] = [
            ScamRule(),
            BadWordsRule(),
            SpamRule(),
            MentionsRule(),
            InvitesRule(),
            LinksRule(),
            CapsRule(),
            AIRule(),
            NewAccountRule(),
        ]
        self.rules = sorted(rules, key=lambda rule: rule.priority, reverse=True)
        self.stats: Counter[str] = Counter()
        self.rule_hits: Counter[str] = Counter()
        self.recent: Deque[RecentViolation] = deque(maxlen=250)
        self._last_trigger: dict[tuple[int, int, str], float] = {}

    async def evaluate(
        self,
        message: Any,
        settings: Mapping[str, Any],
        *,
        dry_run: bool = False,
    ) -> Optional[RuleMatch]:
        if not dry_run:
            self.stats["messages_checked"] += 1
        for rule in self.rules:
            if not bool(settings.get(rule.setting_key, False)):
                continue
            try:
                match = await rule.check(message, settings, dry_run=dry_run)
            except (TypeError, ValueError, AttributeError) as exc:
                logger.exception("Rule %s rejected invalid runtime data: %s", rule.name, exc)
                continue
            except Exception:
                logger.exception("Rule %s failed", rule.name)
                continue
            if match is None:
                continue
            if dry_run:
                return match

            guild_id = int(getattr(getattr(message, "guild", None), "id", 0))
            user_id = int(getattr(getattr(message, "author", None), "id", 0))
            channel_id = int(getattr(getattr(message, "channel", None), "id", 0))
            cooldown = 3600 if match.rule == "new_accounts" else max(
                1, min(300, int(settings.get("automod_violation_cooldown", 10)))
            )
            key = (guild_id, user_id, match.rule)
            now = time.monotonic()
            if now - self._last_trigger.get(key, 0) < cooldown:
                return None
            self._last_trigger[key] = now
            self.stats["violations_detected"] += 1
            self.rule_hits[match.rule] += 1
            self.recent.append(
                RecentViolation(
                    guild_id=guild_id,
                    user_id=user_id,
                    channel_id=channel_id,
                    rule=match.rule,
                    reason=match.reason,
                    severity=match.severity.name,
                    occurred_at=time.time(),
                )
            )
            return match
        return None

    @staticmethod
    def resolve_action(match: RuleMatch, settings: Mapping[str, Any]) -> Action:
        if match.category is Category.IDENTITY:
            return Action.LOG
        key = "automod_security_punishment" if match.category is Category.SECURITY else "automod_punishment"
        raw = str(settings.get(key, "timeout" if match.category is Category.SECURITY else "warn")).casefold()
        aliases = {"mute": "timeout", "delete": "log", "none": "log"}
        raw = aliases.get(raw, raw)
        try:
            return Action(raw)
        except ValueError:
            return Action.TIMEOUT if match.category is Category.SECURITY else Action.WARN

    @staticmethod
    def bypass_reason(message: Any, settings: Mapping[str, Any], owner_ids: set[int]) -> Optional[str]:
        author = getattr(message, "author", None)
        guild = getattr(message, "guild", None)
        channel = getattr(message, "channel", None)
        if author is None or guild is None or channel is None:
            return "unsupported message"
        if int(author.id) in owner_ids:
            return "bot owner"
        if bool(settings.get("automod_bypass_staff", True)) and getattr(author, "guild_permissions", None):
            permissions = author.guild_permissions
            if permissions.administrator or permissions.manage_guild or permissions.manage_messages:
                return "staff permissions"

        role_ids = {int(getattr(role, "id", role)) for role in getattr(author, "roles", [])}
        configured_roles = set()
        for value in (
            list(settings.get("automod_bypass_roles", []) or [])
            + list(settings.get("ignored_roles", []) or [])
            + [settings.get("automod_bypass_role_id")]
        ):
            try:
                if value:
                    configured_roles.add(int(value))
            except (TypeError, ValueError):
                continue
        if role_ids & configured_roles:
            return "bypass role"

        channel_ids = set()
        for value in list(settings.get("automod_bypass_channels", []) or []) + list(settings.get("ignored_channels", []) or []):
            try:
                channel_ids.add(int(value))
            except (TypeError, ValueError):
                continue
        channel_id = int(channel.id)
        parent_id = getattr(channel, "parent_id", None)
        if channel_id in channel_ids or (parent_id is not None and int(parent_id) in channel_ids):
            return "bypass channel"
        if int(author.id) in {int(value) for value in settings.get("automod_temp_bypass", []) or [] if str(value).isdigit()}:
            return "temporary bypass"
        return None

    def recent_for(self, guild_id: int, user_id: Optional[int] = None) -> list[RecentViolation]:
        return [
            item for item in reversed(self.recent)
            if item.guild_id == guild_id and (user_id is None or item.user_id == user_id)
        ]

    def mark_action(self, succeeded: bool) -> None:
        self.stats["actions_attempted"] += 1
        self.stats["actions_succeeded" if succeeded else "actions_failed"] += 1

    def prune(self) -> None:
        now = time.monotonic()
        for rule in self.rules:
            rule.prune(now)
        for key, triggered_at in list(self._last_trigger.items()):
            if now - triggered_at > 3600:
                self._last_trigger.pop(key, None)

    async def close(self) -> None:
        for rule in self.rules:
            await rule.close()
