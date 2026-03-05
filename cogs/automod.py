"""
AutoMod V4 – Streamlined Modular Moderation System

Filters: BadWord, Link, Spam, Scam, Invite, MentionSpam, Caps, NewAccount, AI
All configuration via /automod slash commands.
"""

import os
import re
import json
import asyncio
import hashlib
import logging
import difflib
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import unicodedata

import discord
from discord import app_commands
from discord.ext import commands, tasks

try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from utils.embeds import ModEmbed
from utils.logging import send_log_embed
from utils.checks import is_admin, is_mod, is_bot_owner_id
from config import Config

logger = logging.getLogger("AutoMod")

# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class Severity(Enum):
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EXTREME = 5

class ActionType(Enum):
    NONE = "none"
    LOG = "log"
    WARN = "warn"
    DELETE = "delete"
    MUTE = "mute"
    KICK = "kick"
    BAN = "ban"
    TEMPBAN = "tempban"
    QUARANTINE = "quarantine"

class FilterCategory(Enum):
    CONTENT = "content"
    BEHAVIOR = "behavior"
    IDENTITY = "identity"
    SECURITY = "security"

@dataclass
class FilterResult:
    """Result from a filter check."""
    triggered: bool
    reason: str = ""
    severity: Severity = Severity.LOW
    action: ActionType = ActionType.WARN
    confidence: float = 1.0
    category: FilterCategory = FilterCategory.CONTENT
    metadata: Dict[str, Any] = field(default_factory=dict)
    matched_patterns: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.triggered and self.action == ActionType.WARN:
            severity_action = {
                Severity.EXTREME: ActionType.BAN,
                Severity.CRITICAL: ActionType.KICK,
                Severity.HIGH: ActionType.MUTE,
                Severity.MEDIUM: ActionType.DELETE,
            }
            self.action = severity_action.get(self.severity, ActionType.WARN)

@dataclass
class UserHistory:
    """In-memory violation history for a user (session-scoped)."""
    user_id: int
    guild_id: int
    violations: List[Dict[str, Any]] = field(default_factory=list)
    warnings: int = 0
    mutes: int = 0
    kicks: int = 0
    last_violation: Optional[datetime] = None

    def add_violation(self, result: FilterResult):
        self.violations.append({
            "timestamp": datetime.now(timezone.utc),
            "reason": result.reason,
            "severity": result.severity.value,
            "action": result.action.value,
        })
        self.last_violation = datetime.now(timezone.utc)
        if result.action == ActionType.WARN:
            self.warnings += 1
        elif result.action == ActionType.MUTE:
            self.mutes += 1
        elif result.action == ActionType.KICK:
            self.kicks += 1

    def get_risk_score(self) -> float:
        if not self.violations:
            return 0.0
        score, now = 0.0, datetime.now(timezone.utc)
        weights = {0: 1, 1: 2, 2: 5, 3: 10, 4: 20, 5: 50}
        for v in self.violations:
            decay = max(0.1, 1.0 - ((now - v["timestamp"]).days / 30))
            score += weights.get(v["severity"], 1) * decay
        if len(self.violations) > 5:
            score *= 1.5
        if len(self.violations) > 10:
            score *= 2.0
        return min(100.0, score)

# =============================================================================
# PATTERN LIBRARY
# =============================================================================

class PatternLibrary:
    CONFUSABLES = {
        'a': ['а', 'ａ', '@', '4', 'ā', 'ă', 'ą'],
        'e': ['е', 'ｅ', '3', 'ē', 'ė', 'ę'],
        'i': ['і', 'ｉ', '1', '!', 'ī', 'į'],
        'o': ['о', 'ｏ', '0', 'ō', 'ő'],
        'u': ['υ', 'ｕ', 'ū', 'ů', 'ų'],
        's': ['ѕ', 'ｓ', '$', '5'],
        'n': ['п', 'ｎ'], 'c': ['с', 'ｃ'], 'g': ['ɡ', 'ｇ', '9'], 'k': ['κ', 'ｋ'],
    }

    TOXICITY_PATTERNS = {
        'racial': [r'n[i1!]gg[ea@]r?', r'n[i1!]gg[ua@]', r'ch[i1!]nk', r'sp[i1!]c', r'k[i1!]ke', r'c[o0]{2,}n', r'g[o0]{2,}k', r'wet\s?back'],
        'homophobic': [r'f[a@4]gg?[o0]t', r'f[a@4]g', r'tr[a@4]nn[yi1]', r'd[yi1]ke'],
        'ableist': [r'ret[a@4]rd', r'ret[a@4]rd[e3]d'],
        'threats': [r'k[yi1]{2,}\s?s', r'k[i1]ll\s+(your|ur)?\s?self', r'end\s+(your|ur)\s+life', r'commit\s+suicide', r'shoot\s+up', r'bomb\s+threat'],
        'harassment': [r'r[a@4]pe', r'doxx?', r'swat', r'die\s+in\s+a\s+fire'],
    }

    SCAM_PATTERNS = [
        r'free\s+nitro', r'steam\s+gift', r'claim\s+your\s+(prize|reward)',
        r'@everyone.*http', r'bit\.ly', r'tinyurl', r'goo\.gl',
        r'click\s+here.*prize', r'verify\s+account', r'limited\s+time\s+offer',
    ]

    INVITE_PATTERNS = [r'discord\.gg/[\w-]+', r'discord(?:app)?\.com/invite/[\w-]+', r'dsc\.gg/[\w-]+']

    SUSPICIOUS_LINKS = [r'bit\.ly', r'tinyurl', r'grabify', r'iplogger', r'.*\.ru/', r'.*\.su/', r'.*\.tk/', r'steamcommunity\.com.*trade']

    INVISIBLE_CHARS = ['\u200b', '\u200c', '\u200d', '\u2060', '\ufeff']

    @staticmethod
    def normalize_unicode(text: str) -> str:
        text = unicodedata.normalize('NFD', text)
        return ''.join(c for c in text if not unicodedata.combining(c))

    @staticmethod
    def expand_confusables(pattern: str) -> str:
        for char, alts in PatternLibrary.CONFUSABLES.items():
            if char in pattern:
                pattern = pattern.replace(char, f"[{char}{''.join(alts)}]")
        return pattern

    @staticmethod
    def strip_invisible(text: str) -> str:
        for c in PatternLibrary.INVISIBLE_CHARS:
            text = text.replace(c, '')
        return text

# =============================================================================
# FILTERS
# =============================================================================

def _normalize(text: str) -> str:
    text = text.lower()
    text = PatternLibrary.normalize_unicode(text)
    text = PatternLibrary.strip_invisible(text)
    return re.sub(r'\s+', ' ', text).strip()


class BadWordFilter:
    """Badword filter with evasion detection and fuzzy matching."""
    PRIORITY = 90

    def __init__(self):
        self._compiled: Dict[str, re.Pattern] = {}

    async def check(self, message: discord.Message, settings: dict, ctx: dict) -> FilterResult:
        badwords = settings.get("automod_badwords", [])
        if not badwords:
            return FilterResult(False)
        content = _normalize(message.content)
        if not content:
            return FilterResult(False)

        for word in badwords:
            if word not in self._compiled:
                escaped = re.escape(word.lower())
                expanded = PatternLibrary.expand_confusables(escaped)
                self._compiled[word] = re.compile(r'\b' + expanded + r'\b', re.IGNORECASE)

        matched = [w for w, p in self._compiled.items() if p.search(content)]

        # Fuzzy fallback (only if regex found nothing)
        if not matched:
            for msg_word in content.split():
                if len(msg_word) < 4:  # skip short words to avoid false positives
                    continue
                for bw in badwords:
                    if difflib.SequenceMatcher(None, msg_word, bw.lower()).ratio() >= 0.90:
                        matched.append(f"{bw} (~match)")

        if not matched:
            return FilterResult(False)

        severity = Severity.MEDIUM
        for m in matched:
            base = m.split(" (")[0]
            for pat_list in PatternLibrary.TOXICITY_PATTERNS.get('threats', []):
                if base in pat_list:
                    severity = Severity.CRITICAL
                    break
            for key in ('racial', 'homophobic'):
                for pat_list in PatternLibrary.TOXICITY_PATTERNS.get(key, []):
                    if base in pat_list:
                        severity = max(severity, Severity.HIGH, key=lambda s: s.value)

        user_hist = ctx.get('user_history')
        if user_hist and user_hist.warnings >= 3:
            severity = Severity(min(severity.value + 1, Severity.EXTREME.value))

        return FilterResult(True, reason="Prohibited language detected", severity=severity, category=FilterCategory.CONTENT, matched_patterns=matched[:3])


class LinkFilter:
    """Block unauthorized links, flag suspicious URLs."""
    PRIORITY = 80
    _URL_RE = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(),]|%[0-9a-fA-F]{2})+')

    async def check(self, message: discord.Message, settings: dict, ctx: dict) -> FilterResult:
        if not settings.get("automod_links_enabled", True):
            return FilterResult(False)
        urls = self._URL_RE.findall(message.content)
        if not urls:
            return FilterResult(False)

        whitelist = settings.get("automod_links_whitelist", [])
        wl_domains = settings.get("automod_whitelisted_domains", [])
        suspicious, blocked = [], []

        for url in urls:
            m = re.search(r'://([^/]+)', url)
            if not m:
                continue
            domain = m.group(1).lower()
            if any(d in domain for d in wl_domains) or any(p in url for p in whitelist):
                continue
            if any(re.search(p, url, re.IGNORECASE) for p in PatternLibrary.SUSPICIOUS_LINKS):
                suspicious.append(url)
            else:
                blocked.append(url)

        if suspicious:
            return FilterResult(True, reason="Suspicious link detected (potential phishing)", severity=Severity.HIGH, action=ActionType.DELETE, category=FilterCategory.SECURITY, matched_patterns=suspicious[:2], confidence=0.9)
        if blocked:
            return FilterResult(True, reason="Unauthorized link posted", severity=Severity.MEDIUM, category=FilterCategory.CONTENT, matched_patterns=blocked[:2])
        return FilterResult(False)


class SpamFilter:
    """Multi-layer spam detection: flood, duplicates, character spam."""
    PRIORITY = 85

    def __init__(self):
        self._history: Dict[Tuple, deque] = defaultdict(lambda: deque(maxlen=100))
        self._dupes: Dict[Tuple, Dict[str, List[datetime]]] = defaultdict(lambda: defaultdict(list))
        self._cooldowns: Set[Tuple] = set()

    async def check(self, message: discord.Message, settings: dict, ctx: dict) -> FilterResult:
        threshold = settings.get("automod_spam_threshold", 5)
        if threshold <= 0:
            return FilterResult(False)

        key = (message.guild.id, message.author.id, message.channel.id)
        now = datetime.now(timezone.utc)

        # Flood
        self._history[key].append(now)
        recent = [t for t in self._history[key] if (now - t).total_seconds() < 5]
        if len(recent) >= threshold and key not in self._cooldowns:
            self._cooldowns.add(key)
            asyncio.create_task(self._clear_cooldown(key))
            asyncio.create_task(self._cleanup_spam(message, threshold))
            return FilterResult(True, reason=f"Message flood ({len(recent)} msgs/5s)", severity=Severity.HIGH, action=ActionType.MUTE, category=FilterCategory.BEHAVIOR, metadata={"count": len(recent)})

        # Duplicates
        h = hashlib.md5(message.content.encode()).hexdigest()
        self._dupes[key][h].append(now)
        self._dupes[key][h] = [t for t in self._dupes[key][h] if (now - t).total_seconds() < 60]
        if len(self._dupes[key][h]) >= 3:
            return FilterResult(True, reason=f"Duplicate message spam ({len(self._dupes[key][h])}x)", severity=Severity.MEDIUM, action=ActionType.MUTE, category=FilterCategory.BEHAVIOR)

        # Character spam
        if len(message.content) > 20 and len(set(message.content)) < 5:
            return FilterResult(True, reason="Character spam detected", severity=Severity.LOW, category=FilterCategory.BEHAVIOR)

        return FilterResult(False)

    async def _clear_cooldown(self, key):
        await asyncio.sleep(10)
        self._cooldowns.discard(key)

    async def _cleanup_spam(self, message: discord.Message, count: int):
        try:
            msgs = []
            async for m in message.channel.history(limit=min(count + 5, 100)):
                if m.author.id == message.author.id and (discord.utils.utcnow() - m.created_at).total_seconds() < 10:
                    msgs.append(m)
            if len(msgs) > 1:
                await message.channel.delete_messages(msgs)
        except Exception:
            pass


class ScamFilter:
    """Scam / phishing detection."""
    PRIORITY = 95

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE) for p in PatternLibrary.SCAM_PATTERNS]

    async def check(self, message: discord.Message, settings: dict, ctx: dict) -> FilterResult:
        if not settings.get("automod_scam_protection", True):
            return FilterResult(False)
        content = _normalize(message.content)
        matched = [p.pattern for p in self._patterns if p.search(content)]
        if matched:
            return FilterResult(True, reason="Potential scam/phishing attempt", severity=Severity.CRITICAL, action=ActionType.BAN, category=FilterCategory.SECURITY, matched_patterns=matched[:3], confidence=0.95)
        if ('@everyone' in message.content or '@here' in message.content) and 'http' in message.content.lower():
            return FilterResult(True, reason="Suspicious mass ping with link", severity=Severity.HIGH, action=ActionType.KICK, category=FilterCategory.SECURITY, confidence=0.9)
        return FilterResult(False)


class MentionSpamFilter:
    PRIORITY = 88

    async def check(self, message: discord.Message, settings: dict, ctx: dict) -> FilterResult:
        limit = settings.get("automod_max_mentions", 5)
        if limit <= 0:
            return FilterResult(False)
        total = len(message.mentions) + len(message.role_mentions)
        if total < limit:
            return FilterResult(False)
        sev = Severity.CRITICAL if total >= limit * 2 else (Severity.HIGH if total >= limit * 1.5 else Severity.MEDIUM)
        return FilterResult(True, reason=f"Mass mention spam ({total} mentions)", severity=sev, action=ActionType.MUTE, category=FilterCategory.BEHAVIOR, metadata={"count": total})


class InviteFilter:
    PRIORITY = 75

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE) for p in PatternLibrary.INVITE_PATTERNS]

    async def check(self, message: discord.Message, settings: dict, ctx: dict) -> FilterResult:
        if not settings.get("automod_invites_enabled", True):
            return FilterResult(False)
        allowed = settings.get("automod_allowed_invites", [])
        for p in self._patterns:
            if p.search(message.content):
                if any(inv in message.content for inv in allowed):
                    continue
                return FilterResult(True, reason="Unauthorized Discord invite link", severity=Severity.MEDIUM, category=FilterCategory.CONTENT)
        return FilterResult(False)


class CapsFilter:
    PRIORITY = 60

    async def check(self, message: discord.Message, settings: dict, ctx: dict) -> FilterResult:
        threshold = settings.get("automod_caps_percentage", 70)
        min_len = settings.get("automod_caps_min_length", 10)
        if threshold <= 0 or len(message.content) < min_len:
            return FilterResult(False)
        alpha = [c for c in message.content if c.isalpha()]
        if not alpha:
            return FilterResult(False)
        ratio = sum(1 for c in alpha if c.isupper()) / len(alpha) * 100
        if ratio >= threshold:
            return FilterResult(True, reason=f"Excessive caps ({int(ratio)}%)", severity=Severity.LOW, action=ActionType.DELETE, category=FilterCategory.BEHAVIOR, metadata={"pct": ratio})
        return FilterResult(False)


class NewAccountFilter:
    PRIORITY = 50

    async def check(self, message: discord.Message, settings: dict, ctx: dict) -> FilterResult:
        days = settings.get("automod_newaccount_days", 0)
        if days <= 0:
            return FilterResult(False)
        age = (datetime.now(timezone.utc) - message.author.created_at).days
        if age < days:
            return FilterResult(True, reason=f"New account ({age} days old)", severity=Severity.INFO, action=ActionType.LOG, category=FilterCategory.IDENTITY, metadata={"age": age})
        return FilterResult(False)


class AIFilter:
    """AI content moderation via Gemini (optional)."""
    PRIORITY = 70

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key and GEMINI_AVAILABLE else None
        self.model = "gemini-2.5-flash"
        self._cache: Dict[str, FilterResult] = {}

    async def check(self, message: discord.Message, settings: dict, ctx: dict) -> FilterResult:
        if not self.client or not settings.get("automod_ai_enabled", False):
            return FilterResult(False)
        content = message.content.strip()
        if not content or len(content) < 5:
            return FilterResult(False)

        cache_key = hashlib.md5(content.encode()).hexdigest()
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            min_sev = settings.get("automod_ai_min_severity", 4)
            return cached if cached.triggered and cached.metadata.get('ai_severity', 0) >= min_sev else FilterResult(False)

        try:
            hist = ctx.get('user_history')
            hist_ctx = ""
            if hist and hist.violations:
                recent = [v['reason'] for v in hist.violations[-3:]]
                hist_ctx = f"\nUser has {len(hist.violations)} prior violations. Recent: {recent}"

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self._analyze, content, hist_ctx)

            # Maintain cache (cap at 500)
            if len(self._cache) >= 500:
                for k in list(self._cache.keys())[:125]:
                    del self._cache[k]
            self._cache[cache_key] = result

            min_sev = settings.get("automod_ai_min_severity", 4)
            if result.triggered and result.metadata.get('ai_severity', 0) >= min_sev:
                return result
        except Exception as e:
            logger.error(f"AI filter error: {e}")
        return FilterResult(False)

    def _analyze(self, content: str, history: str) -> FilterResult:
        try:
            prompt = f"""Analyze this Discord message for policy violations.

Message: "{content}"
{history}

Check for: toxicity, threats, NSFW, spam, scams, misinformation.
Be context-aware and lenient with ambiguous cases.

Respond ONLY with valid JSON:
{{"violation": true/false, "category": "toxicity|threats|nsfw|spam|scam|other", "severity": 1-10, "confidence": 0.0-1.0, "reason": "concise explanation"}}"""

            config = genai_types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=200,
                response_mime_type="application/json"
            )
            comp = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            resp = comp.text
            if "```json" in resp:
                resp = resp.split("```json")[1].split("```")[0]
            elif "```" in resp:
                resp = resp.split("```")[1].split("```")[0]
            data = json.loads(resp.strip())

            if data.get("violation"):
                ai_sev = data.get("severity", 1)
                sev_map = {range(1, 3): Severity.LOW, range(3, 5): Severity.MEDIUM, range(5, 7): Severity.HIGH, range(7, 9): Severity.CRITICAL, range(9, 11): Severity.EXTREME}
                severity = Severity.MEDIUM
                for r, s in sev_map.items():
                    if ai_sev in r:
                        severity = s
                        break
                return FilterResult(True, reason=f"AI: {data.get('reason', 'Policy violation')}", severity=severity, confidence=data.get("confidence", 0.5), category=FilterCategory.CONTENT, metadata={"ai_severity": ai_sev, "ai_category": data.get("category")})
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
        return FilterResult(False)


# =============================================================================
# ENGINE
# =============================================================================

# Ordered by priority (highest first)
_FILTER_CLASSES = [ScamFilter, BadWordFilter, MentionSpamFilter, SpamFilter, LinkFilter, InviteFilter, AIFilter, CapsFilter, NewAccountFilter]


class AutoModEngine:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.filters = [cls() for cls in _FILTER_CLASSES]
        self.filters.sort(key=lambda f: f.PRIORITY, reverse=True)
        self.user_histories: Dict[Tuple[int, int], UserHistory] = {}
        self.stats = {"messages_checked": 0, "violations_detected": 0, "actions_taken": 0}

    def get_user_history(self, guild_id: int, user_id: int) -> UserHistory:
        key = (guild_id, user_id)
        if key not in self.user_histories:
            self.user_histories[key] = UserHistory(user_id, guild_id)
        return self.user_histories[key]

    async def check_bypass(self, message: discord.Message, settings: dict) -> Tuple[bool, str]:
        if is_bot_owner_id(message.author.id):
            return True, "Bot owner"
        bypass_role_id = settings.get("automod_bypass_role_id")
        if bypass_role_id:
            role = message.guild.get_role(bypass_role_id)
            if role and role in message.author.roles:
                return True, f"Bypass role: {role.name}"
        if message.author.id in (settings.get("automod_temp_bypass") or []):
            return True, "Temporary bypass"
        if message.channel.id in (settings.get("automod_bypass_channels") or []):
            return True, f"Bypass channel: {message.channel.name}"
        return False, ""

    async def process_message(self, message: discord.Message, settings: dict) -> Optional[FilterResult]:
        self.stats["messages_checked"] += 1
        user_hist = self.get_user_history(message.guild.id, message.author.id)
        ctx = {"user_history": user_hist, "risk_score": user_hist.get_risk_score(), "channel_type": str(message.channel.type)}

        for filt in self.filters:
            try:
                result = await filt.check(message, settings, ctx)
                if result.triggered:
                    self.stats["violations_detected"] += 1
                    user_hist.add_violation(result)
                    return result
            except Exception as e:
                logger.error(f"Filter {filt.__class__.__name__} error: {e}", exc_info=True)
        return None

    async def execute_action(self, message: discord.Message, result: FilterResult, settings: dict) -> Dict[str, Any]:
        user, guild = message.author, message.guild
        log = {"user_id": user.id, "action": result.action.value, "reason": result.reason, "success": False, "timestamp": datetime.now(timezone.utc)}

        try:
            if result.action != ActionType.LOG:
                try:
                    await message.delete()
                    log["message_deleted"] = True
                except Exception:
                    log["message_deleted"] = False

            if result.action == ActionType.DELETE:
                log["success"] = True
                log["details"] = "Message deleted"
            elif result.action == ActionType.BAN:
                await user.ban(reason=f"[AutoMod] {result.reason}", delete_message_days=settings.get("automod_ban_delete_days", 1))
                log.update(success=True, details="Permanently banned")
            elif result.action == ActionType.TEMPBAN:
                dur = settings.get("automod_tempban_duration", 86400)
                await user.ban(reason=f"[AutoMod] {result.reason} (Temp)")
                asyncio.create_task(self._schedule_unban(guild, user.id, dur))
                log.update(success=True, details=f"Temp banned for {dur}s")
            elif result.action == ActionType.KICK:
                await user.kick(reason=f"[AutoMod] {result.reason}")
                log.update(success=True, details="Kicked from server")
            elif result.action == ActionType.MUTE:
                dur = settings.get("automod_mute_duration", 3600)
                if result.severity == Severity.CRITICAL:
                    dur *= 4
                elif result.severity == Severity.HIGH:
                    dur *= 2
                await user.timeout(timedelta(seconds=dur), reason=f"[AutoMod] {result.reason}")
                log.update(success=True, details=f"Muted for {dur}s")
            elif result.action == ActionType.QUARANTINE:
                role_id = settings.get("automod_quarantine_role_id")
                role = guild.get_role(role_id) if role_id else None
                if role:
                    await user.add_roles(role, reason=f"[AutoMod] {result.reason}")
                    log.update(success=True, details="Quarantined")
                else:
                    await user.timeout(timedelta(minutes=30), reason=f"[AutoMod] {result.reason}")
                    log.update(success=True, details="Muted (quarantine unavailable)")
            elif result.action == ActionType.WARN:
                wid, wcount = await self.bot.db.add_warning(guild.id, user.id, self.bot.user.id, result.reason)
                log.update(success=True, details=f"Warning issued (#{wcount})")
                if settings.get("warn_thresholds_enabled"):
                    try:
                        ban_at = settings.get("warn_threshold_ban", 7)
                        kick_at = settings.get("warn_threshold_kick", 5)
                        mute_at = settings.get("warn_threshold_mute", 3)
                        if ban_at and wcount >= ban_at:
                            await guild.ban(user, reason=f"[AutoMod] Auto-ban: {wcount} warnings")
                            log["details"] += f" → Auto-banned ({wcount} warns)"
                        elif kick_at and wcount >= kick_at:
                            await guild.kick(user, reason=f"[AutoMod] Auto-kick: {wcount} warnings")
                            log["details"] += f" → Auto-kicked ({wcount} warns)"
                        elif mute_at and wcount >= mute_at:
                            await user.timeout(timedelta(seconds=settings.get("warn_mute_duration", 3600)), reason=f"[AutoMod] Auto-mute: {wcount} warnings")
                            log["details"] += f" → Auto-muted ({wcount} warns)"
                    except Exception as e:
                        log["details"] += f" (auto-punishment failed: {e})"
            elif result.action == ActionType.LOG:
                log.update(success=True, details="Logged only")

            self.stats["actions_taken"] += 1
        except discord.Forbidden:
            log["error"] = "Missing permissions"
        except Exception as e:
            log["error"] = str(e)
            logger.error(f"Action execution failed: {e}")
        return log

    async def _schedule_unban(self, guild: discord.Guild, user_id: int, duration: int):
        await asyncio.sleep(duration)
        try:
            user = await self.bot.fetch_user(user_id)
            await guild.unban(user, reason="[AutoMod] Temporary ban expired")
        except Exception:
            pass


# =============================================================================
# COG
# =============================================================================

class AutoModV3(commands.Cog):
    """AutoMod system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.engine = AutoModEngine(bot)
        self.cleanup_task.start()

    async def cog_unload(self):
        self.cleanup_task.cancel()

    @tasks.loop(hours=1)
    async def cleanup_task(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        for key, hist in list(self.engine.user_histories.items()):
            if hist.last_violation and hist.last_violation < cutoff:
                del self.engine.user_histories[key]

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    async def _get_log_channel(self, guild: discord.Guild, settings: dict) -> Optional[discord.TextChannel]:
        cid = settings.get("automod_log_channel") or settings.get("log_channel")
        return guild.get_channel(cid) if cid else None

    async def _send_log(self, guild: discord.Guild, result: FilterResult, action_log: Dict, message: discord.Message, settings: dict):
        channel = await self._get_log_channel(guild, settings)
        if not channel:
            return
        color_map = {Severity.INFO: 0x3B82F6, Severity.LOW: 0xF59E0B, Severity.MEDIUM: 0xF97316, Severity.HIGH: 0xEF4444, Severity.CRITICAL: 0x991B1B, Severity.EXTREME: 0x8B0000}
        embed = discord.Embed(title="🛡️ AutoMod Action", color=color_map.get(result.severity, 0xF59E0B), timestamp=datetime.now(timezone.utc))
        embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.display_avatar.url)
        embed.add_field(name="Violation", value=result.reason, inline=False)
        embed.add_field(name="Severity", value=f"**{result.severity.name}** ({result.confidence:.0%})", inline=True)
        embed.add_field(name="Action", value=action_log.get("details", action_log["action"]), inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        if result.matched_patterns:
            embed.add_field(name="Matched", value=", ".join(f"||{p}||" for p in result.matched_patterns[:3]), inline=False)
        hist = self.engine.get_user_history(guild.id, message.author.id)
        embed.add_field(name="User History", value=f"Violations: {len(hist.violations)} | Risk: {hist.get_risk_score():.0f}/100", inline=True)
        preview = message.content[:500] + ("..." if len(message.content) > 500 else "")
        embed.add_field(name="Message", value=f"```{preview}```", inline=False)
        embed.set_footer(text=f"Category: {result.category.value}")
        await send_log_embed(channel, embed)

    async def _notify_user(self, user: discord.User, guild: discord.Guild, result: FilterResult, action_log: Dict):
        try:
            embed = discord.Embed(title="⚠️ AutoMod Alert", description=f"You triggered an automated moderation action in **{guild.name}**", color=0xEF4444, timestamp=datetime.now(timezone.utc))
            reason_text = result.reason
            if result.matched_patterns:
                reason_text += f" (saying: {', '.join(repr(p) for p in result.matched_patterns[:3])})"
            embed.add_field(name="Reason", value=reason_text, inline=False)
            embed.add_field(name="Action", value=action_log.get("details", result.action.value.replace("_", " ").title()), inline=False)
            embed.add_field(name="What now?", value="Please review the server rules. Repeated violations may result in permanent action.", inline=False)
            embed.set_footer(text="If you believe this was a mistake, contact server moderators")
            await user.send(embed=embed)
        except discord.Forbidden:
            pass
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")

    # ------------------------------------------------------------------
    # Listener
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        try:
            settings = await self.bot.db.get_settings(message.guild.id)
            if not settings.get("automod_enabled", True):
                return
            bypassed, _ = await self.engine.check_bypass(message, settings)
            if bypassed:
                return
            result = await self.engine.process_message(message, settings)
            if result and result.triggered:
                action_log = await self.engine.execute_action(message, result, settings)
                await self._send_log(message.guild, result, action_log, message, settings)
                if settings.get("automod_notify_users", True):
                    await self._notify_user(message.author, message.guild, result, action_log)
        except Exception as e:
            logger.error(f"AutoMod error: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Slash Commands
    # ------------------------------------------------------------------

    automod = app_commands.Group(name="automod", description="AutoMod Configuration")

    _TOGGLE_SETTINGS: Dict[str, Tuple[str, bool, str]] = {
        "automod_enabled": ("AutoMod", True, "Master switch"),
        "automod_links_enabled": ("Link Filter", True, "Block suspicious links"),
        "automod_invites_enabled": ("Invite Filter", True, "Block invite links"),
        "automod_scam_protection": ("Scam Protection", True, "Detect scam patterns"),
        "automod_ai_enabled": ("AI Moderation", False, "Run AI-based checks"),
        "automod_notify_users": ("Notify Users", True, "DM users after action"),
    }

    @staticmethod
    def _bool_text(v: bool) -> str:
        return "Enabled" if v else "Disabled"

    @staticmethod
    def _short_list(values: List[str], limit: int = 12) -> str:
        if not values:
            return "`None`"
        s = ", ".join(f"`{v}`" for v in values[:limit])
        return s + (f" ... (+{len(values) - limit})" if len(values) > limit else "")

    @staticmethod
    def _normalize_domain(raw: str) -> str:
        v = (raw or "").strip().lower()
        for prefix in ("http://", "https://"):
            if v.startswith(prefix):
                v = v[len(prefix):]
        return v.split("/", 1)[0].strip().strip(".")

    @staticmethod
    def _parse_csv(raw: str) -> List[str]:
        seen, out = set(), []
        for p in (raw or "").split(","):
            item = p.strip().lower()
            if item and item not in seen:
                seen.add(item)
                out.append(item)
        return out

    def _role_mention(self, guild, role_id) -> str:
        if not guild or not role_id:
            return "`Not set`"
        r = guild.get_role(int(role_id))
        return r.mention if r else "`Not set`"

    def _ch_mention(self, guild, ch_id) -> str:
        if not guild or not ch_id:
            return "`Not set`"
        c = guild.get_channel(int(ch_id))
        return c.mention if c else "`Not set`"

    @automod.command(name="config", description="View AutoMod configuration")
    @is_admin()
    async def automod_config(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        g = interaction.guild
        modules = "\n".join(f"**{name}:** {self._bool_text(bool(settings.get(k, d)))}" for k, (name, d, _) in self._TOGGLE_SETTINGS.items())
        embed = discord.Embed(title="AutoMod Configuration", color=Config.COLOR_INFO, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Modules", value=modules, inline=False)
        embed.add_field(name="Thresholds", value=f"Spam: `{settings.get('automod_spam_threshold', 5)}` msgs/5s\nCaps: `{settings.get('automod_caps_percentage', 70)}%` (min `{settings.get('automod_caps_min_length', 10)}`)\nMentions: `{settings.get('automod_max_mentions', 5)}`\nNew Account: `{settings.get('automod_newaccount_days', 7)}` days", inline=False)
        embed.add_field(name="Enforcement", value=f"Action: `{str(settings.get('automod_punishment', 'warn')).upper()}`\nMute: `{int(settings.get('automod_mute_duration', 3600)) // 60}` min\nTempban: `{int(settings.get('automod_tempban_duration', 86400)) // 3600}` hrs", inline=False)
        embed.add_field(name="Roles & Channels", value=f"Bypass: {self._role_mention(g, settings.get('automod_bypass_role_id'))}\nQuarantine: {self._role_mention(g, settings.get('automod_quarantine_role_id'))}\nLog: {self._ch_mention(g, settings.get('automod_log_channel'))}", inline=False)
        embed.add_field(name="Lists", value=f"Bad Words: `{len(settings.get('automod_badwords', []) or [])}`\nDomains: `{len(settings.get('automod_whitelisted_domains', []) or [])}`", inline=False)
        embed.add_field(name="Commands", value="`/automod toggle` · `/automod thresholds` · `/automod punishment`\n`/automod roles` · `/automod channels` · `/automod badwords` · `/automod domains`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @automod.command(name="toggle", description="Enable or disable AutoMod modules")
    @app_commands.describe(setting="Which setting to update", state="Optional explicit state")
    @app_commands.choices(setting=[
        app_commands.Choice(name="AutoMod (master)", value="automod_enabled"),
        app_commands.Choice(name="Links", value="automod_links_enabled"),
        app_commands.Choice(name="Invites", value="automod_invites_enabled"),
        app_commands.Choice(name="Scam Protection", value="automod_scam_protection"),
        app_commands.Choice(name="AI Moderation", value="automod_ai_enabled"),
        app_commands.Choice(name="Notify Users", value="automod_notify_users"),
    ])
    @is_admin()
    async def automod_toggle(self, interaction: discord.Interaction, setting: app_commands.Choice[str], state: Optional[bool] = None):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        label, default, help_text = self._TOGGLE_SETTINGS.get(setting.value, (setting.name, False, ""))
        current = bool(settings.get(setting.value, default))
        new = (not current) if state is None else bool(state)
        settings[setting.value] = new
        await self.bot.db.update_settings(interaction.guild_id, settings)
        await interaction.response.send_message(embed=ModEmbed.success("AutoMod Updated", f"**{label}** → **{self._bool_text(new)}**\n{help_text}"), ephemeral=True)

    @automod.command(name="thresholds", description="Set AutoMod thresholds")
    @app_commands.describe(spam_messages="Messages per 5s (0=off)", caps_percent="Caps % (0=off)", caps_min_chars="Min chars for caps check", max_mentions="Max mentions (0=off)", new_account_days="Min account age days (0=off)")
    @is_admin()
    async def automod_thresholds(self, interaction: discord.Interaction, spam_messages: Optional[app_commands.Range[int, 0, 30]] = None, caps_percent: Optional[app_commands.Range[int, 0, 100]] = None, caps_min_chars: Optional[app_commands.Range[int, 0, 500]] = None, max_mentions: Optional[app_commands.Range[int, 0, 30]] = None, new_account_days: Optional[app_commands.Range[int, 0, 365]] = None):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        updates = []
        for val, key, lbl in [(spam_messages, "automod_spam_threshold", "Spam"), (caps_percent, "automod_caps_percentage", "Caps %"), (caps_min_chars, "automod_caps_min_length", "Caps min"), (max_mentions, "automod_max_mentions", "Mentions"), (new_account_days, "automod_newaccount_days", "Account age")]:
            if val is not None:
                settings[key] = int(val)
                updates.append(f"{lbl} → `{int(val)}`")
        if updates:
            await self.bot.db.update_settings(interaction.guild_id, settings)
        await interaction.response.send_message(embed=ModEmbed.success("Thresholds", "\n".join(updates) or "No changes."), ephemeral=True)

    @automod.command(name="punishment", description="Set default punishment and durations")
    @app_commands.describe(action="Default action", mute_minutes="Mute duration (min)", tempban_hours="Tempban duration (hrs)", ban_delete_days="Ban msg delete days (0-7)")
    @app_commands.choices(action=[
        app_commands.Choice(name="Warn", value="warn"), app_commands.Choice(name="Delete", value="delete"),
        app_commands.Choice(name="Mute", value="mute"), app_commands.Choice(name="Kick", value="kick"),
        app_commands.Choice(name="Ban", value="ban"), app_commands.Choice(name="Temporary Ban", value="tempban"),
        app_commands.Choice(name="Quarantine", value="quarantine"), app_commands.Choice(name="Log Only", value="log"),
    ])
    @is_admin()
    async def automod_punishment(self, interaction: discord.Interaction, action: app_commands.Choice[str], mute_minutes: Optional[app_commands.Range[int, 1, 10080]] = None, tempban_hours: Optional[app_commands.Range[int, 1, 720]] = None, ban_delete_days: Optional[app_commands.Range[int, 0, 7]] = None):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        settings["automod_punishment"] = action.value
        updates = [f"Action → `{action.value.upper()}`"]
        if mute_minutes is not None:
            settings["automod_mute_duration"] = int(mute_minutes) * 60
            updates.append(f"Mute → `{int(mute_minutes)}` min")
        if tempban_hours is not None:
            settings["automod_tempban_duration"] = int(tempban_hours) * 3600
            updates.append(f"Tempban → `{int(tempban_hours)}` hrs")
        if ban_delete_days is not None:
            settings["automod_ban_delete_days"] = int(ban_delete_days)
            updates.append(f"Ban delete → `{int(ban_delete_days)}` days")
        await self.bot.db.update_settings(interaction.guild_id, settings)
        await interaction.response.send_message(embed=ModEmbed.success("Punishment Updated", "\n".join(updates)), ephemeral=True)

    @automod.command(name="roles", description="Set bypass and quarantine roles")
    @app_commands.describe(bypass_role="Bypass AutoMod", quarantine_role="Quarantine role", clear_bypass="Clear bypass", clear_quarantine="Clear quarantine")
    @is_admin()
    async def automod_roles(self, interaction: discord.Interaction, bypass_role: Optional[discord.Role] = None, quarantine_role: Optional[discord.Role] = None, clear_bypass: bool = False, clear_quarantine: bool = False):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        updates = []
        if clear_bypass:
            settings["automod_bypass_role_id"] = None; updates.append("Bypass cleared")
        elif bypass_role:
            settings["automod_bypass_role_id"] = bypass_role.id; updates.append(f"Bypass → {bypass_role.mention}")
        if clear_quarantine:
            settings["automod_quarantine_role_id"] = None; updates.append("Quarantine cleared")
        elif quarantine_role:
            settings["automod_quarantine_role_id"] = quarantine_role.id; updates.append(f"Quarantine → {quarantine_role.mention}")
        if updates:
            await self.bot.db.update_settings(interaction.guild_id, settings)
        await interaction.response.send_message(embed=ModEmbed.success("Roles", "\n".join(updates) or f"Bypass: {self._role_mention(interaction.guild, settings.get('automod_bypass_role_id'))}\nQuarantine: {self._role_mention(interaction.guild, settings.get('automod_quarantine_role_id'))}"), ephemeral=True)

    @automod.command(name="channels", description="Set log and bypass channels")
    @app_commands.describe(log_channel="Log channel", add_bypass_channel="Add bypass", remove_bypass_channel="Remove bypass", clear_log_channel="Clear log", clear_bypass_channels="Clear all bypass")
    @is_admin()
    async def automod_channels(self, interaction: discord.Interaction, log_channel: Optional[discord.TextChannel] = None, add_bypass_channel: Optional[discord.TextChannel] = None, remove_bypass_channel: Optional[discord.TextChannel] = None, clear_log_channel: bool = False, clear_bypass_channels: bool = False):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        updates = []
        if clear_log_channel:
            settings["automod_log_channel"] = None; updates.append("Log cleared")
        elif log_channel:
            settings["automod_log_channel"] = log_channel.id; updates.append(f"Log → {log_channel.mention}")
        bypass = set(int(v) for v in (settings.get("automod_bypass_channels") or []))
        if clear_bypass_channels:
            bypass.clear(); updates.append("Bypass channels cleared")
        if add_bypass_channel:
            bypass.add(add_bypass_channel.id); updates.append(f"Added bypass {add_bypass_channel.mention}")
        if remove_bypass_channel and remove_bypass_channel.id in bypass:
            bypass.remove(remove_bypass_channel.id); updates.append(f"Removed bypass {remove_bypass_channel.mention}")
        settings["automod_bypass_channels"] = sorted(bypass)
        if updates:
            await self.bot.db.update_settings(interaction.guild_id, settings)
        await interaction.response.send_message(embed=ModEmbed.success("Channels", "\n".join(updates) or "No changes."), ephemeral=True)

    @automod.command(name="badwords", description="Manage bad words list")
    @app_commands.describe(action="Action", words="Comma-separated words")
    @app_commands.choices(action=[app_commands.Choice(name="List", value="list"), app_commands.Choice(name="Add", value="add"), app_commands.Choice(name="Remove", value="remove"), app_commands.Choice(name="Clear", value="clear")])
    @is_admin()
    async def automod_badwords(self, interaction: discord.Interaction, action: app_commands.Choice[str], words: Optional[str] = None):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        current = list(settings.get("automod_badwords") or [])
        mode = action.value
        if mode == "list":
            return await interaction.response.send_message(embed=ModEmbed.info("Bad Words", f"`{len(current)}` words\n{self._short_list(current, 20)}"), ephemeral=True)
        if mode == "clear":
            settings["automod_badwords"] = []
            await self.bot.db.update_settings(interaction.guild_id, settings)
            return await interaction.response.send_message(embed=ModEmbed.success("Bad Words", "List cleared."), ephemeral=True)
        parsed = self._parse_csv(words or "")
        if not parsed:
            return await interaction.response.send_message(embed=ModEmbed.error("Missing Input", "Provide comma-separated words."), ephemeral=True)
        current_set, changed = set(current), []
        if mode == "add":
            for w in parsed:
                if w not in current_set:
                    current.append(w); current_set.add(w); changed.append(w)
            title = "Words Added"
        else:
            for w in parsed:
                if w in current_set:
                    current_set.remove(w); changed.append(w)
            current = [w for w in current if w in current_set]
            title = "Words Removed"
        settings["automod_badwords"] = current
        await self.bot.db.update_settings(interaction.guild_id, settings)
        await interaction.response.send_message(embed=ModEmbed.success(title, f"Changed: `{len(changed)}`\n{self._short_list(changed, 20)}\nTotal: `{len(current)}`"), ephemeral=True)

    @automod.command(name="domains", description="Manage whitelisted domains")
    @app_commands.describe(action="Action", domains="Comma-separated domains")
    @app_commands.choices(action=[app_commands.Choice(name="List", value="list"), app_commands.Choice(name="Add", value="add"), app_commands.Choice(name="Remove", value="remove"), app_commands.Choice(name="Clear", value="clear")])
    @is_admin()
    async def automod_domains(self, interaction: discord.Interaction, action: app_commands.Choice[str], domains: Optional[str] = None):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        current = [self._normalize_domain(v) for v in (settings.get("automod_whitelisted_domains") or []) if self._normalize_domain(v)]
        mode = action.value
        if mode == "list":
            return await interaction.response.send_message(embed=ModEmbed.info("Whitelisted Domains", f"`{len(current)}` domains\n{self._short_list(current, 20)}"), ephemeral=True)
        if mode == "clear":
            settings["automod_whitelisted_domains"] = []
            await self.bot.db.update_settings(interaction.guild_id, settings)
            return await interaction.response.send_message(embed=ModEmbed.success("Domains", "Cleared."), ephemeral=True)
        parsed = [self._normalize_domain(v) for v in self._parse_csv(domains or "") if self._normalize_domain(v)]
        if not parsed:
            return await interaction.response.send_message(embed=ModEmbed.error("Missing Input", "Provide comma-separated domains."), ephemeral=True)
        current_set, changed = set(current), []
        if mode == "add":
            for d in parsed:
                if d not in current_set:
                    current.append(d); current_set.add(d); changed.append(d)
            title = "Domains Added"
        else:
            for d in parsed:
                if d in current_set:
                    current_set.remove(d); changed.append(d)
            current = [d for d in current if d in current_set]
            title = "Domains Removed"
        settings["automod_whitelisted_domains"] = current
        await self.bot.db.update_settings(interaction.guild_id, settings)
        await interaction.response.send_message(embed=ModEmbed.success(title, f"Changed: `{len(changed)}`\n{self._short_list(changed, 20)}\nTotal: `{len(current)}`"), ephemeral=True)

    @automod.command(name="status", description="View AutoMod statistics")
    @is_mod()
    async def status(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(interaction.guild_id)
        stats = self.engine.stats
        embed = discord.Embed(title="🛡️ AutoMod Status", color=Config.COLOR_INFO, timestamp=datetime.now(timezone.utc))
        active = [f.__class__.__name__ for f in self.engine.filters]
        embed.add_field(name="Filters", value="\n".join(f"✓ {f}" for f in active), inline=False)
        embed.add_field(name="Stats (Session)", value=f"Checked: **{stats['messages_checked']:,}**\nViolations: **{stats['violations_detected']:,}**\nActions: **{stats['actions_taken']:,}**", inline=True)
        embed.add_field(name="Config", value=f"Action: **{str(settings.get('automod_punishment', 'warn')).upper()}**\nAI: {'✓' if settings.get('automod_ai_enabled') else '✗'}", inline=True)
        embed.set_footer(text=f"AutoMod V4 • {len(self.engine.filters)} filters")
        await interaction.response.send_message(embed=embed)

    @automod.command(name="history", description="View user violation history")
    @is_mod()
    async def user_history(self, interaction: discord.Interaction, user: discord.Member):
        hist = self.engine.get_user_history(interaction.guild_id, user.id)
        if not hist.violations:
            return await interaction.response.send_message(embed=ModEmbed.info("Clean Record", f"{user.mention} has no AutoMod violations."))
        risk = hist.get_risk_score()
        risk_level, color = ("🔴 CRITICAL", 0x991B1B) if risk >= 75 else ("🟠 HIGH", 0xF97316) if risk >= 50 else ("🟡 MEDIUM", 0xF59E0B) if risk >= 25 else ("🟢 LOW", 0x22C55E)
        embed = discord.Embed(title=f"📋 Violations: {user.name}", color=color, timestamp=datetime.now(timezone.utc))
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Risk", value=f"**{risk:.0f}/100** {risk_level}", inline=True)
        embed.add_field(name="Summary", value=f"Total: {len(hist.violations)} | Warns: {hist.warnings} | Mutes: {hist.mutes} | Kicks: {hist.kicks}", inline=True)
        recent = hist.violations[-5:]
        if recent:
            embed.add_field(name="Recent", value="\n".join(f"`{v['timestamp'].strftime('%m/%d %H:%M')}` {v['reason']}" for v in reversed(recent)), inline=False)
        await interaction.response.send_message(embed=embed)

    @automod.command(name="test", description="Test AutoMod with sample text")
    @is_admin()
    async def test_automod(self, interaction: discord.Interaction, content: str):
        await interaction.response.defer(ephemeral=True)

        class _Mock:
            def __init__(self, content, author, guild, channel):
                self.content = content
                self.author = author
                self.guild = guild
                self.channel = channel
                self.mentions = []
                self.role_mentions = []
                self.created_at = datetime.now(timezone.utc)

        mock = _Mock(content, interaction.user, interaction.guild, interaction.channel)
        settings = await self.bot.db.get_settings(interaction.guild_id)
        result = await self.engine.process_message(mock, settings)

        if result and result.triggered:
            embed = discord.Embed(title="⚠️ Violation Detected", color=0xEF4444)
            embed.add_field(name="Reason", value=result.reason, inline=False)
            embed.add_field(name="Severity", value=result.severity.name, inline=True)
            embed.add_field(name="Action", value=result.action.value.upper(), inline=True)
            if result.matched_patterns:
                embed.add_field(name="Matched", value=", ".join(f"||{p}||" for p in result.matched_patterns[:3]), inline=False)
        else:
            embed = ModEmbed.success("✅ Clean", "Passes all filters.")
        embed.add_field(name="Input", value=f"```{content[:500]}```", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoModV3(bot))
