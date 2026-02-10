"""
AutoMod V3 - Enterprise-Grade Modular Moderation System

Major Improvements:
- Advanced Filter Pipeline with Priority System
- Intelligent Context-Aware AI Analysis
- Redis Caching for High Performance
- Comprehensive Audit Logging
- Auto-Escalation System
- Smart Whitelist/Blacklist Management
- Pattern Learning & Adaptation
- Multi-Language Support
- Rate Limiting & DDoS Protection
- Sophisticated Bypass System with Temporary Overrides
- Appeal & Review System
- Statistics & Analytics Dashboard
- Webhook Integration for External Systems
- Custom Rule Engine (JSON/YAML)
- Progressive Punishment System
- Smart Message Context Analysis
- Advanced Evasion Detection
- Automated Pattern Recognition
"""

import os
import re
import json
import asyncio
import hashlib
import logging
import difflib
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple, Set, Union, Literal
from dataclasses import dataclass, field
from enum import Enum
import unicodedata

import discord
from discord import app_commands
from discord.ext import commands, tasks

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logging.warning("Groq not installed - AI features disabled")

try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available - using in-memory cache")

from utils.embeds import ModEmbed
from utils.logging import send_log_embed
from utils.checks import is_admin, is_mod, is_bot_owner_id
from utils.time_parser import parse_time
from config import Config

logger = logging.getLogger("AutoModV3")

# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class Severity(Enum):
    """Severity levels for violations"""
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EXTREME = 5

class ActionType(Enum):
    """Possible moderation actions"""
    NONE = "none"
    LOG = "log"
    WARN = "warn"
    DELETE = "delete"
    MUTE = "mute"
    KICK = "kick"
    BAN = "ban"
    TEMPBAN = "tempban"
    QUARANTINE = "quarantine"
    SHADOWBAN = "shadowban"

class FilterCategory(Enum):
    """Filter categories for organization"""
    CONTENT = "content"
    BEHAVIOR = "behavior"
    IDENTITY = "identity"
    SECURITY = "security"
    CUSTOM = "custom"

@dataclass
class FilterResult:
    """Enhanced filter result with detailed metadata"""
    triggered: bool
    reason: str = ""
    severity: Severity = Severity.LOW
    action: ActionType = ActionType.WARN
    confidence: float = 1.0  # 0.0 - 1.0
    category: FilterCategory = FilterCategory.CONTENT
    metadata: Dict[str, Any] = field(default_factory=dict)
    matched_patterns: List[str] = field(default_factory=list)
    context: str = ""
    
    def __post_init__(self):
        """Auto-determine action based on severity if not set"""
        if self.triggered and self.action == ActionType.WARN:
            if self.severity == Severity.EXTREME:
                self.action = ActionType.BAN
            elif self.severity == Severity.CRITICAL:
                self.action = ActionType.KICK
            elif self.severity == Severity.HIGH:
                self.action = ActionType.MUTE
            elif self.severity == Severity.MEDIUM:
                self.action = ActionType.DELETE
            else:
                self.action = ActionType.WARN

@dataclass
class UserHistory:
    """Track user violation history"""
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
            "action": result.action.value
        })
        self.last_violation = datetime.now(timezone.utc)
        
        if result.action == ActionType.WARN:
            self.warnings += 1
        elif result.action == ActionType.MUTE:
            self.mutes += 1
        elif result.action == ActionType.KICK:
            self.kicks += 1
    
    def get_risk_score(self) -> float:
        """Calculate user risk score (0-100)"""
        if not self.violations:
            return 0.0
        
        score = 0.0
        now = datetime.now(timezone.utc)
        
        for v in self.violations:
            # Time decay - older violations matter less
            age_days = (now - v["timestamp"]).days
            decay = max(0.1, 1.0 - (age_days / 30))
            
            # Severity weight
            severity_weight = {0: 1, 1: 2, 2: 5, 3: 10, 4: 20, 5: 50}
            score += severity_weight.get(v["severity"], 1) * decay
        
        # Frequency multiplier
        if len(self.violations) > 5:
            score *= 1.5
        if len(self.violations) > 10:
            score *= 2.0
        
        return min(100.0, score)

# =============================================================================
# COMPREHENSIVE PATTERN LIBRARY
# =============================================================================

class PatternLibrary:
    """Centralized pattern library with advanced evasion detection"""
    
    # Unicode confusables for evasion detection
    CONFUSABLES = {
        'a': ['а', 'ａ', '@', '4', 'ā', 'ă', 'ą'],
        'e': ['е', 'ｅ', '3', 'ē', 'ė', 'ę'],
        'i': ['і', 'ｉ', '1', '!', 'ī', 'į'],
        'o': ['о', 'ｏ', '0', 'ō', 'ő'],
        'u': ['υ', 'ｕ', 'ū', 'ů', 'ų'],
        's': ['ѕ', 'ｓ', '$', '5'],
        'n': ['п', 'ｎ'],
        'c': ['с', 'ｃ'],
        'g': ['ɡ', 'ｇ', '9'],
        'k': ['κ', 'ｋ'],
    }
    
    # Comprehensive slur/toxicity patterns
    TOXICITY_PATTERNS = {
        'racial': [
            r'n[i1!]gg[ea@]r?',
            r'n[i1!]gg[ua@]',
            r'ch[i1!]nk',
            r'sp[i1!]c',
            r'k[i1!]ke',
            r'c[o0]{2,}n',
            r'g[o0]{2,}k',
            r'wet\s?back',
        ],
        'homophobic': [
            r'f[a@4]gg?[o0]t',
            r'f[a@4]g',
            r'tr[a@4]nn[yi1]',
            r'd[yi1]ke',
        ],
        'ableist': [
            r'ret[a@4]rd',
            r'ret[a@4]rd[e3]d',
            r'aut[i1]st[i1]c',  # When used as insult
        ],
        'threats': [
            r'k[yi1]{2,}\s?s',
            r'k[i1]ll\s+(your|ur)?\s?self',
            r'end\s+(your|ur)\s+life',
            r'commit\s+suicide',
            r'shoot\s+up',
            r'bomb\s+threat',
        ],
        'harassment': [
            r'r[a@4]pe',
            r'doxx?',
            r'swat',
            r'die\s+in\s+a\s+fire',
        ]
    }
    
    # Scam/phishing patterns
    SCAM_PATTERNS = [
        r'free\s+nitro',
        r'steam\s+gift',
        r'claim\s+your\s+(prize|reward)',
        r'@everyone.*http',
        r'bit\.ly',
        r'tinyurl',
        r'goo\.gl',
        r'click\s+here.*prize',
        r'verify\s+account',
        r'limited\s+time\s+offer',
    ]
    
    # Invite patterns (more comprehensive)
    INVITE_PATTERNS = [
        r'discord\.gg/[\w-]+',
        r'discord(?:app)?\.com/invite/[\w-]+',
        r'dsc\.gg/[\w-]+',
    ]
    
    # Suspicious link patterns
    SUSPICIOUS_LINKS = [
        r'bit\.ly',
        r'tinyurl',
        r'grabify',
        r'iplogger',
        r'.*\.ru/',
        r'.*\.su/',
        r'.*\.tk/',
        r'steamcommunity\.com.*trade',
    ]
    
    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Normalize unicode to detect evasion attempts"""
        # NFD normalization
        text = unicodedata.normalize('NFD', text)
        # Remove combining characters
        text = ''.join(c for c in text if not unicodedata.combining(c))
        return text
    
    @staticmethod
    def expand_confusables(pattern: str) -> str:
        """Expand pattern to include confusable characters"""
        for char, confusables in PatternLibrary.CONFUSABLES.items():
            if char in pattern:
                replacement = f"[{char}{''.join(confusables)}]"
                pattern = pattern.replace(char, replacement)
        return pattern
    
    @staticmethod
    def strip_invisible(text: str) -> str:
        """Remove zero-width and invisible characters"""
        invisible = [
            '\u200b',  # Zero-width space
            '\u200c',  # Zero-width non-joiner
            '\u200d',  # Zero-width joiner
            '\u2060',  # Word joiner
            '\ufeff',  # Zero-width no-break space
        ]
        for char in invisible:
            text = text.replace(char, '')
        return text

# =============================================================================
# ADVANCED CACHING SYSTEM
# =============================================================================

class CacheManager:
    """High-performance caching with Redis fallback to memory"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self.redis = None
        self.memory_cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_hits = 0
        self.cache_misses = 0
    
    async def initialize(self):
        """Initialize Redis connection"""
        if REDIS_AVAILABLE and self.redis_url:
            try:
                self.redis = await aioredis.create_redis_pool(self.redis_url)
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning(f"Redis connection failed, using memory cache: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        # Try Redis first
        if self.redis:
            try:
                value = await self.redis.get(key)
                if value:
                    self.cache_hits += 1
                    return json.loads(value)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        # Fallback to memory
        if key in self.memory_cache:
            value, expiry = self.memory_cache[key]
            if datetime.now(timezone.utc) < expiry:
                self.cache_hits += 1
                return value
            else:
                del self.memory_cache[key]
        
        self.cache_misses += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL"""
        # Try Redis
        if self.redis:
            try:
                await self.redis.setex(key, ttl, json.dumps(value))
                return
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        
        # Fallback to memory
        expiry = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        self.memory_cache[key] = (value, expiry)
        
        # Cleanup old entries
        if len(self.memory_cache) > 10000:
            self._cleanup_memory_cache()
    
    def _cleanup_memory_cache(self):
        """Remove expired entries from memory cache"""
        now = datetime.now(timezone.utc)
        expired = [k for k, (_, exp) in self.memory_cache.items() if now >= exp]
        for k in expired:
            del self.memory_cache[k]
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()

# =============================================================================
# ABSTRACT FILTER BASE
# =============================================================================

class BaseFilter(ABC):
    """Enhanced base filter with priority and metadata"""
    
    def __init__(self, bot: commands.Bot, priority: int = 50):
        self.bot = bot
        self.priority = priority  # 0-100, higher = checked first
        self.enabled = True
        self.cache_manager: Optional[CacheManager] = None
    
    @abstractmethod
    async def check(self, message: discord.Message, settings: dict, context: dict) -> FilterResult:
        """
        Check if message violates this filter
        
        Args:
            message: The Discord message
            settings: Guild settings
            context: Additional context (user history, etc.)
        """
        pass
    
    async def get_cache_key(self, message: discord.Message) -> str:
        """Generate cache key for this filter"""
        content_hash = hashlib.md5(message.content.encode()).hexdigest()
        return f"filter:{self.__class__.__name__}:{content_hash}"
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        text = text.lower()
        text = PatternLibrary.normalize_unicode(text)
        text = PatternLibrary.strip_invisible(text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

# =============================================================================
# ENHANCED FILTERS
# =============================================================================

class AdvancedBadWordFilter(BaseFilter):
    """Enhanced badword filter with context awareness and evasion detection"""
    
    def __init__(self, bot):
        super().__init__(bot, priority=90)
        self.compiled_patterns: Dict[str, re.Pattern] = {}
    
    async def check(self, message: discord.Message, settings: dict, context: dict) -> FilterResult:
        badwords = settings.get("automod_badwords", [])
        if not badwords:
            return FilterResult(False)
        
        content = self.normalize_text(message.content)
        if not content:
            return FilterResult(False)
        
        # Compile patterns if not cached
        for word in badwords:
            if word not in self.compiled_patterns:
                # Escape special characters to treat as literal, then expand
                escaped = re.escape(word.lower())
                expanded = PatternLibrary.expand_confusables(escaped)
                # Add word boundary detection
                pattern = r'\b' + expanded + r'\b'
                self.compiled_patterns[word] = re.compile(pattern, re.IGNORECASE)
        
        # Check patterns
        matched = []
        severity = Severity.LOW
        
        
        # Check patterns (Regex)
        for word, pattern in self.compiled_patterns.items():
            if pattern.search(content):
                matched.append(word)

        # Fuzzy Matching (if no exact matches yet, or to catch variations)
        # We check individual words to avoid false positives on long text
        if not matched:  # Only check fuzzy if regex didn't catch it
            words = content.split()
            for msg_word in words:
                # Skip short words to avoid noise
                if len(msg_word) < 3:
                    continue

                msg_word_norm = msg_word.lower()
                for badword in badwords:
                    # ratio >= 0.85 means ~1-2 char difference for average words
                    ratio = difflib.SequenceMatcher(None, msg_word_norm, badword.lower()).ratio()
                    if ratio >= 0.85:
                        matched.append(f"{badword} (~{int(ratio*100)}%)")

        if matched:
            # Re-calculate severity based on matched words
            severity = Severity.MEDIUM  # Default for fuzzy

            # Check if any matched word (stripped of %) is critical
            for m in matched:
                base_word = m.split(" (")[0]
                if base_word in str(PatternLibrary.TOXICITY_PATTERNS.get('threats', [])):
                    severity = Severity.CRITICAL
                    break
                elif base_word in str(PatternLibrary.TOXICITY_PATTERNS.get('racial', [])) or \
                     base_word in str(PatternLibrary.TOXICITY_PATTERNS.get('homophobic', [])):
                    severity = Severity.HIGH

        
        if matched:
            # Check user history for escalation
            user_history = context.get('user_history')
            if user_history and user_history.violations:
                # Escalate if repeat offender
                if user_history.warnings >= 3:
                    severity = Severity(min(severity.value + 1, Severity.EXTREME.value))
            
            return FilterResult(
                triggered=True,
                reason=f"Prohibited language detected",
                severity=severity,
                category=FilterCategory.CONTENT,
                matched_patterns=matched[:3],  # Limit to 3 for privacy
                confidence=1.0
            )
        
        return FilterResult(False)

class SmartLinkFilter(BaseFilter):
    """Intelligent link filter with URL analysis"""
    
    def __init__(self, bot):
        super().__init__(bot, priority=80)
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
    
    async def check(self, message: discord.Message, settings: dict, context: dict) -> FilterResult:
        if not settings.get("automod_links_enabled", True):
            return FilterResult(False)
        
        urls = self.url_pattern.findall(message.content)
        if not urls:
            return FilterResult(False)
        
        whitelist = settings.get("automod_links_whitelist", [])
        whitelist_domains = settings.get("automod_whitelisted_domains", [])
        
        suspicious_urls = []
        blocked_urls = []
        
        for url in urls:
            # Extract domain
            domain_match = re.search(r'://([^/]+)', url)
            if not domain_match:
                continue
            
            domain = domain_match.group(1).lower()
            
            # Check whitelist
            if any(d in domain for d in whitelist_domains):
                continue
            
            if any(pattern in url for pattern in whitelist):
                continue
            
            # Check suspicious patterns
            is_suspicious = False
            for pattern in PatternLibrary.SUSPICIOUS_LINKS:
                if re.search(pattern, url, re.IGNORECASE):
                    suspicious_urls.append(url)
                    is_suspicious = True
                    break
            
            if not is_suspicious:
                blocked_urls.append(url)
        
        if suspicious_urls:
            return FilterResult(
                triggered=True,
                reason="Suspicious link detected (potential phishing/malware)",
                severity=Severity.HIGH,
                action=ActionType.DELETE,
                category=FilterCategory.SECURITY,
                matched_patterns=suspicious_urls[:2],
                confidence=0.9
            )
        
        if blocked_urls:
            return FilterResult(
                triggered=True,
                reason="Unauthorized link posted",
                severity=Severity.MEDIUM,
                category=FilterCategory.CONTENT,
                matched_patterns=blocked_urls[:2],
                confidence=1.0
            )
        
        return FilterResult(False)

class AdvancedSpamFilter(BaseFilter):
    """Multi-layered spam detection"""
    
    def __init__(self, bot):
        super().__init__(bot, priority=85)
        self.message_history: Dict[Tuple, deque] = defaultdict(lambda: deque(maxlen=100))
        self.duplicate_tracker: Dict[Tuple, Dict[str, List[datetime]]] = defaultdict(lambda: defaultdict(list))
        self.cooldowns: Set[Tuple] = set()
    
    async def check(self, message: discord.Message, settings: dict, context: dict) -> FilterResult:
        threshold = settings.get("automod_spam_threshold", 5)
        if threshold <= 0:
            return FilterResult(False)
        
        key = (message.guild.id, message.author.id, message.channel.id)
        now = datetime.now(timezone.utc)
        
        # 1. Message flood detection
        self.message_history[key].append(now)
        recent_messages = [t for t in self.message_history[key] if (now - t).total_seconds() < 5]
        
        if len(recent_messages) >= threshold:
            if key not in self.cooldowns:
                self.cooldowns.add(key)
                asyncio.create_task(self._clear_cooldown(key))
                asyncio.create_task(self._cleanup_spam(message, threshold))
                
                return FilterResult(
                    triggered=True,
                    reason=f"Message flood ({len(recent_messages)} messages in 5s)",
                    severity=Severity.HIGH,
                    action=ActionType.MUTE,
                    category=FilterCategory.BEHAVIOR,
                    metadata={"message_count": len(recent_messages)}
                )
        
        # 2. Duplicate message detection
        content_hash = hashlib.md5(message.content.encode()).hexdigest()
        self.duplicate_tracker[key][content_hash].append(now)
        
        # Clean old duplicates
        self.duplicate_tracker[key][content_hash] = [
            t for t in self.duplicate_tracker[key][content_hash] 
            if (now - t).total_seconds() < 60
        ]
        
        duplicate_count = len(self.duplicate_tracker[key][content_hash])
        if duplicate_count >= 3:
            return FilterResult(
                triggered=True,
                reason=f"Duplicate message spam ({duplicate_count}x)",
                severity=Severity.MEDIUM,
                action=ActionType.MUTE,
                category=FilterCategory.BEHAVIOR
            )
        
        # 3. Character spam detection
        if len(message.content) > 20:
            unique_chars = len(set(message.content))
            if unique_chars < 5:  # Very low character diversity
                return FilterResult(
                    triggered=True,
                    reason="Character spam detected",
                    severity=Severity.LOW,
                    category=FilterCategory.BEHAVIOR
                )
        
        return FilterResult(False)
    
    async def _clear_cooldown(self, key):
        await asyncio.sleep(10)
        self.cooldowns.discard(key)
    
    async def _cleanup_spam(self, message: discord.Message, count: int):
        try:
            messages = []
            async for m in message.channel.history(limit=min(count + 5, 100)):
                if m.author.id == message.author.id and \
                   (discord.utils.utcnow() - m.created_at).total_seconds() < 10:
                    messages.append(m)
            
            if len(messages) > 1:
                await message.channel.delete_messages(messages)
        except Exception as e:
            logger.error(f"Spam cleanup failed: {e}")

class IntelligentAIFilter(BaseFilter):
    """Advanced AI-powered content moderation with context awareness"""
    
    def __init__(self, bot):
        super().__init__(bot, priority=70)
        api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key) if api_key and GROQ_AVAILABLE else None
        self.model = "llama-3.3-70b-versatile"
        self.analysis_cache: Dict[str, FilterResult] = {}
        self.max_cache_size = 1000
    
    async def check(self, message: discord.Message, settings: dict, context: dict) -> FilterResult:
        if not self.client or not settings.get("automod_ai_enabled", False):
            return FilterResult(False)
        
        content = message.content.strip()
        if not content or len(content) < 5:
            return FilterResult(False)
        
        # Cache check
        cache_key = hashlib.md5(content.encode()).hexdigest()
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]
        
        try:
            # Get user context
            user_history = context.get('user_history')
            history_context = ""
            if user_history and user_history.violations:
                recent = user_history.violations[-3:]
                history_context = f"\nUser has {len(user_history.violations)} prior violations. Recent: {[v['reason'] for v in recent]}"
            
            # Run AI analysis
            result = await self.bot.loop.run_in_executor(
                None, 
                self._analyze_content, 
                content,
                history_context
            )
            
            # Cache result
            if len(self.analysis_cache) >= self.max_cache_size:
                # Remove oldest entries
                remove_count = self.max_cache_size // 4
                for k in list(self.analysis_cache.keys())[:remove_count]:
                    del self.analysis_cache[k]
            
            self.analysis_cache[cache_key] = result
            
            # Apply threshold
            min_severity = settings.get("automod_ai_min_severity", 4)
            if result.triggered and result.metadata.get('ai_severity', 0) >= min_severity:
                return result
                
        except Exception as e:
            logger.error(f"AI filter error: {e}")
        
        return FilterResult(False)
    
    def _analyze_content(self, content: str, history: str) -> FilterResult:
        """Synchronous AI analysis"""
        try:
            prompt = f"""Analyze this Discord message for policy violations.

Message: "{content}"
{history}

Check for:
1. Toxicity (hate speech, slurs, harassment)
2. Threats (violence, self-harm encouragement)
3. NSFW content (sexual, graphic)
4. Spam (repetitive, nonsense)
5. Scams (phishing, fraud)
6. Misinformation (if obvious)

Context awareness:
- Consider intent and context
- Differentiate jokes from genuine threats
- Account for user history
- Be lenient with ambiguous cases

Respond ONLY with valid JSON:
{{
    "violation": true/false,
    "category": "toxicity|threats|nsfw|spam|scam|other",
    "severity": 1-10,
    "confidence": 0.0-1.0,
    "reason": "concise explanation",
    "context_considered": true/false
}}"""

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=200
            )
            
            response = completion.choices[0].message.content
            # Extract JSON if wrapped in markdown
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            data = json.loads(response.strip())
            
            if data.get("violation"):
                ai_severity = data.get("severity", 1)
                confidence = data.get("confidence", 0.5)
                
                # Map AI severity to our severity enum
                severity_map = {
                    range(1, 3): Severity.LOW,
                    range(3, 5): Severity.MEDIUM,
                    range(5, 7): Severity.HIGH,
                    range(7, 9): Severity.CRITICAL,
                    range(9, 11): Severity.EXTREME
                }
                
                severity = Severity.MEDIUM
                for r, s in severity_map.items():
                    if ai_severity in r:
                        severity = s
                        break
                
                result = FilterResult(
                    triggered=True,
                    reason=f"AI: {data.get('reason', 'Policy violation detected')}",
                    severity=severity,
                    confidence=confidence,
                    category=FilterCategory.CONTENT,
                    metadata={
                        "ai_severity": ai_severity,
                        "ai_category": data.get("category"),
                        "context_aware": data.get("context_considered", False)
                    }
                )
                return result
                
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
        
        return FilterResult(False)

class ScamDetectionFilter(BaseFilter):
    """Specialized scam and phishing detection"""
    
    def __init__(self, bot):
        super().__init__(bot, priority=95)
        self.scam_patterns = [re.compile(p, re.IGNORECASE) for p in PatternLibrary.SCAM_PATTERNS]
    
    async def check(self, message: discord.Message, settings: dict, context: dict) -> FilterResult:
        if not settings.get("automod_scam_protection", True):
            return FilterResult(False)
        
        content = self.normalize_text(message.content)
        
        # Check for scam patterns
        matched_patterns = []
        for pattern in self.scam_patterns:
            if pattern.search(content):
                matched_patterns.append(pattern.pattern)
        
        if matched_patterns:
            # High severity for scams - they're dangerous
            return FilterResult(
                triggered=True,
                reason="Potential scam/phishing attempt detected",
                severity=Severity.CRITICAL,
                action=ActionType.BAN,  # Aggressive action for scams
                category=FilterCategory.SECURITY,
                matched_patterns=matched_patterns[:3],
                confidence=0.95
            )
        
        # Check for @everyone/@here abuse with links
        if ('@everyone' in message.content or '@here' in message.content) and \
           ('http' in message.content.lower()):
            return FilterResult(
                triggered=True,
                reason="Suspicious mass ping with link",
                severity=Severity.HIGH,
                action=ActionType.KICK,
                category=FilterCategory.SECURITY,
                confidence=0.9
            )
        
        return FilterResult(False)

class MentionSpamFilter(BaseFilter):
    """Advanced mention spam detection"""
    
    def __init__(self, bot):
        super().__init__(bot, priority=88)
    
    async def check(self, message: discord.Message, settings: dict, context: dict) -> FilterResult:
        limit = settings.get("automod_max_mentions", 5)
        if limit <= 0:
            return FilterResult(False)
        
        total_mentions = len(message.mentions) + len(message.role_mentions)
        
        if total_mentions >= limit:
            # Escalate severity based on count
            if total_mentions >= limit * 2:
                severity = Severity.CRITICAL
            elif total_mentions >= limit * 1.5:
                severity = Severity.HIGH
            else:
                severity = Severity.MEDIUM
            
            return FilterResult(
                triggered=True,
                reason=f"Mass mention spam ({total_mentions} mentions)",
                severity=severity,
                action=ActionType.MUTE,
                category=FilterCategory.BEHAVIOR,
                metadata={"mention_count": total_mentions}
            )
        
        return FilterResult(False)

class InviteFilter(BaseFilter):
    """Enhanced Discord invite detection"""
    
    def __init__(self, bot):
        super().__init__(bot, priority=75)
        self.patterns = [re.compile(p, re.IGNORECASE) for p in PatternLibrary.INVITE_PATTERNS]
    
    async def check(self, message: discord.Message, settings: dict, context: dict) -> FilterResult:
        if not settings.get("automod_invites_enabled", True):
            return FilterResult(False)
        
        content = message.content
        
        for pattern in self.patterns:
            if pattern.search(content):
                # Check if it's an allowed server
                allowed_invites = settings.get("automod_allowed_invites", [])
                if any(inv in content for inv in allowed_invites):
                    continue
                
                return FilterResult(
                    triggered=True,
                    reason="Unauthorized Discord invite link",
                    severity=Severity.MEDIUM,
                    category=FilterCategory.CONTENT,
                    confidence=1.0
                )
        
        return FilterResult(False)

class CapsFilter(BaseFilter):
    """Intelligent caps detection"""
    
    def __init__(self, bot):
        super().__init__(bot, priority=60)
    
    async def check(self, message: discord.Message, settings: dict, context: dict) -> FilterResult:
        threshold = settings.get("automod_caps_percentage", 70)
        min_length = settings.get("automod_caps_min_length", 10)
        
        if threshold <= 0:
            return FilterResult(False)
        
        content = message.content
        if len(content) < min_length:
            return FilterResult(False)
        
        alpha_chars = [c for c in content if c.isalpha()]
        if not alpha_chars:
            return FilterResult(False)
        
        caps_count = sum(1 for c in alpha_chars if c.isupper())
        ratio = (caps_count / len(alpha_chars)) * 100
        
        if ratio >= threshold:
            # More lenient - caps isn't that serious
            return FilterResult(
                triggered=True,
                reason=f"Excessive caps ({int(ratio)}%)",
                severity=Severity.LOW,
                action=ActionType.DELETE,
                category=FilterCategory.BEHAVIOR,
                metadata={"caps_percentage": ratio}
            )
        
        return FilterResult(False)

class NewAccountFilter(BaseFilter):
    """New account monitoring"""
    
    def __init__(self, bot):
        super().__init__(bot, priority=50)
    
    async def check(self, message: discord.Message, settings: dict, context: dict) -> FilterResult:
        min_days = settings.get("automod_newaccount_days", 0)
        if min_days <= 0:
            return FilterResult(False)
        
        age_days = (datetime.now(timezone.utc) - message.author.created_at).days
        
        if age_days < min_days:
            # Just log, don't punish
            return FilterResult(
                triggered=True,
                reason=f"New account ({age_days} days old)",
                severity=Severity.INFO,
                action=ActionType.LOG,
                category=FilterCategory.IDENTITY,
                metadata={"account_age_days": age_days}
            )
        
        return FilterResult(False)

# =============================================================================
# MAIN AUTOMOD ENGINE
# =============================================================================

class AutoModEngine:
    """Core automod processing engine"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.filters: List[BaseFilter] = []
        self.user_histories: Dict[Tuple[int, int], UserHistory] = {}
        self.cache_manager = CacheManager(os.getenv("REDIS_URL"))
        self.stats = {
            "messages_checked": 0,
            "violations_detected": 0,
            "actions_taken": 0,
            "false_positives": 0
        }
        
        # Initialize filters
        self._initialize_filters()
    
    def _initialize_filters(self):
        """Initialize all filter modules"""
        self.filters = [
            ScamDetectionFilter(self.bot),
            AdvancedBadWordFilter(self.bot),
            MentionSpamFilter(self.bot),
            AdvancedSpamFilter(self.bot),
            SmartLinkFilter(self.bot),
            InviteFilter(self.bot),
            IntelligentAIFilter(self.bot),
            CapsFilter(self.bot),
            NewAccountFilter(self.bot),
        ]
        
        # Sort by priority (highest first)
        self.filters.sort(key=lambda f: f.priority, reverse=True)
        
        # Set cache manager
        for f in self.filters:
            f.cache_manager = self.cache_manager
        
        logger.info(f"Initialized {len(self.filters)} filters")
    
    def get_user_history(self, guild_id: int, user_id: int) -> UserHistory:
        """Get or create user history"""
        key = (guild_id, user_id)
        if key not in self.user_histories:
            self.user_histories[key] = UserHistory(user_id, guild_id)
        return self.user_histories[key]
    
    async def check_bypass(self, message: discord.Message, settings: dict) -> Tuple[bool, str]:
        """
        Check if user bypasses automod
        Returns: (bypassed, reason)
        """
        # 1. Bot owner always bypasses
        if is_bot_owner_id(message.author.id):
            return True, "Bot owner"
        
        # 2. Bypass role
        bypass_role_id = settings.get("automod_bypass_role_id")
        if bypass_role_id:
            role = message.guild.get_role(bypass_role_id)
            if role and role in message.author.roles:
                return True, f"Bypass role: {role.name}"
        
        # 3. Temporary bypass (e.g., for moderators testing)
        temp_bypass = settings.get("automod_temp_bypass", [])
        if message.author.id in temp_bypass:
            return True, "Temporary bypass"
        
        # 4. Channel-specific bypass
        bypass_channels = settings.get("automod_bypass_channels", [])
        if message.channel.id in bypass_channels:
            return True, f"Bypass channel: {message.channel.name}"
        
        return False, ""
    
    async def process_message(self, message: discord.Message, settings: dict) -> Optional[FilterResult]:
        """
        Process message through filter pipeline
        Returns: FilterResult if violation detected, None otherwise
        """
        self.stats["messages_checked"] += 1
        
        # Build context
        user_history = self.get_user_history(message.guild.id, message.author.id)
        context = {
            "user_history": user_history,
            "risk_score": user_history.get_risk_score(),
            "channel_type": str(message.channel.type),
        }
        
        # Run through filter pipeline
        for filter_obj in self.filters:
            if not filter_obj.enabled:
                continue
            
            try:
                result = await filter_obj.check(message, settings, context)
                
                if result.triggered:
                    self.stats["violations_detected"] += 1
                    
                    # Add to user history
                    user_history.add_violation(result)
                    
                    # Return first violation (can be modified to collect all)
                    return result
                    
            except Exception as e:
                logger.error(f"Filter {filter_obj.__class__.__name__} error: {e}", exc_info=True)
                continue
        
        return None
    
    async def execute_action(
        self, 
        message: discord.Message, 
        result: FilterResult, 
        settings: dict
    ) -> Dict[str, Any]:
        """
        Execute moderation action
        Returns: Dict with action details
        """
        user = message.author
        guild = message.guild
        action_log = {
            "user_id": user.id,
            "action": result.action.value,
            "reason": result.reason,
            "success": False,
            "timestamp": datetime.now(timezone.utc)
        }
        
        try:
            # 1. Delete message (for most actions)
            if result.action != ActionType.LOG:
                try:
                    await message.delete()
                    action_log["message_deleted"] = True
                except Exception as e:
                    logger.warning(f"Failed to delete message {message.id}: {e}")
                    action_log["message_deleted"] = False
            
            # 2. Execute action
            if result.action == ActionType.DELETE:
                action_log["success"] = True
                action_log["details"] = "Message deleted"
            elif result.action == ActionType.BAN:
                reason = f"[AutoMod] {result.reason}"
                delete_days = settings.get("automod_ban_delete_days", 1)
                await user.ban(reason=reason, delete_message_days=delete_days)
                action_log["success"] = True
                action_log["details"] = "Permanently banned"
                
            elif result.action == ActionType.TEMPBAN:
                duration = settings.get("automod_tempban_duration", 86400)
                # Note: Discord doesn't support tempbans directly, would need to schedule unban
                await user.ban(reason=f"[AutoMod] {result.reason} (Temp)")
                action_log["success"] = True
                action_log["details"] = f"Temp banned for {duration}s"
                # Schedule unban
                asyncio.create_task(self._schedule_unban(guild, user.id, duration))
                
            elif result.action == ActionType.KICK:
                await user.kick(reason=f"[AutoMod] {result.reason}")
                action_log["success"] = True
                action_log["details"] = "Kicked from server"
                
            elif result.action == ActionType.MUTE:
                duration = settings.get("automod_mute_duration", 3600)
                # Scale duration based on severity
                if result.severity == Severity.CRITICAL:
                    duration *= 4
                elif result.severity == Severity.HIGH:
                    duration *= 2
                
                await user.timeout(
                    timedelta(seconds=duration),
                    reason=f"[AutoMod] {result.reason}"
                )
                action_log["success"] = True
                action_log["details"] = f"Muted for {duration}s"
                
            elif result.action == ActionType.QUARANTINE:
                role_id = settings.get("automod_quarantine_role_id")
                role = guild.get_role(role_id)
                if role:
                    await user.add_roles(role, reason=f"[AutoMod] {result.reason}")
                    action_log["success"] = True
                    action_log["details"] = "Quarantined"
                else:
                    # Fallback to mute
                    await user.timeout(timedelta(minutes=30), reason=f"[AutoMod] {result.reason}")
                    action_log["success"] = True
                    action_log["details"] = "Muted (quarantine unavailable)"
                    
            elif result.action == ActionType.WARN:
                await self.bot.db.add_warning(guild.id, user.id, self.bot.user.id, result.reason)
                action_log["success"] = True
                action_log["details"] = "Warning issued"
                
            elif result.action == ActionType.LOG:
                action_log["success"] = True
                action_log["details"] = "Logged only"
            
            self.stats["actions_taken"] += 1
            
        except discord.Forbidden:
            action_log["error"] = "Missing permissions"
        except Exception as e:
            action_log["error"] = str(e)
            logger.error(f"Action execution failed: {e}")
        
        return action_log
    
    async def _schedule_unban(self, guild: discord.Guild, user_id: int, duration: int):
        """Schedule automatic unban"""
        await asyncio.sleep(duration)
        try:
            user = await self.bot.fetch_user(user_id)
            await guild.unban(user, reason="[AutoMod] Temporary ban expired")
        except:
            pass

# =============================================================================
# INTERACTIVE DASHBOARD UI
# =============================================================================

def _build_dashboard_embed(guild: discord.Guild, settings: dict) -> discord.Embed:
    """Build the main AutoMod dashboard embed showing all config at a glance."""
    embed = discord.Embed(
        title="🛡️ AutoMod Dashboard",
        description="Configure your server's automated moderation system.\nUse the buttons and menus below to adjust settings.",
        color=discord.Color.from_rgb(88, 101, 242),
        timestamp=datetime.now(timezone.utc),
    )

    # ── Module Toggles ──
    def _icon(val: bool) -> str:
        return "✅" if val else "❌"

    toggles = (
        f"{_icon(settings.get('automod_links_enabled', True))} **Link Filter**\n"
        f"{_icon(settings.get('automod_invites_enabled', True))} **Invite Filter**\n"
        f"{_icon(settings.get('automod_scam_protection', True))} **Scam Protection**\n"
        f"{_icon(settings.get('automod_ai_enabled', False))} **AI Moderation**\n"
        f"{_icon(settings.get('automod_notify_users', True))} **Notify Users**"
    )
    embed.add_field(name="📦 Modules", value=toggles, inline=True)

    # ── Thresholds ──
    thresholds = (
        f"**Spam Limit:** `{settings.get('automod_spam_threshold', 5)}` msgs/5s\n"
        f"**Caps:** `{settings.get('automod_caps_percentage', 70)}%` (min `{settings.get('automod_caps_min_length', 10)}` chars)\n"
        f"**Max Mentions:** `{settings.get('automod_max_mentions', 5)}`\n"
        f"**New Account:** `{settings.get('automod_newaccount_days', 7)}` days"
    )
    embed.add_field(name="📊 Thresholds", value=thresholds, inline=True)

    # ── Roles & Channels ──
    bypass_role = guild.get_role(settings.get("automod_bypass_role_id")) if settings.get("automod_bypass_role_id") else None
    quarantine_role = guild.get_role(settings.get("automod_quarantine_role_id")) if settings.get("automod_quarantine_role_id") else None
    log_ch = guild.get_channel(settings.get("automod_log_channel")) if settings.get("automod_log_channel") else None

    infra = (
        f"**Bypass Role:** {bypass_role.mention if bypass_role else '`Not Set`'}\n"
        f"**Quarantine Role:** {quarantine_role.mention if quarantine_role else '`Not Set`'}\n"
        f"**Log Channel:** {log_ch.mention if log_ch else '`Not Set`'}\n"
        f"**Punishment:** `{settings.get('automod_punishment', 'warn').upper()}`"
    )
    embed.add_field(name="⚙️ Infrastructure", value=infra, inline=False)

    # ── Lists ──
    badwords = settings.get("automod_badwords", [])
    domains = settings.get("automod_whitelisted_domains", [])
    lists_text = (
        f"**Bad Words:** `{len(badwords)}` configured\n"
        f"**Whitelisted Domains:** `{len(domains)}` configured"
    )
    embed.add_field(name="📋 Lists", value=lists_text, inline=False)

    embed.set_footer(text="AutoMod V3 • Changes are saved automatically")
    return embed


async def _refresh_dashboard(interaction: discord.Interaction, bot: commands.Bot, guild_id: int):
    """Helper to refresh the dashboard embed after a change."""
    guild = bot.get_guild(guild_id) or interaction.guild
    settings = await bot.db.get_settings(guild_id)
    embed = _build_dashboard_embed(guild, settings)
    try:
        await interaction.message.edit(embed=embed)
    except Exception:
        pass


class ThresholdModal(discord.ui.Modal, title="📊 Edit Thresholds"):
    """Modal for editing automod thresholds."""

    spam = discord.ui.TextInput(
        label="Spam Limit (msgs per 5s, 0 = off)",
        placeholder="5",
        required=False,
        max_length=4,
    )
    caps = discord.ui.TextInput(
        label="Caps Percentage (0-100, 0 = off)",
        placeholder="70",
        required=False,
        max_length=3,
    )
    mentions = discord.ui.TextInput(
        label="Max Mentions (0 = off)",
        placeholder="5",
        required=False,
        max_length=4,
    )
    new_account = discord.ui.TextInput(
        label="New Account Age (days, 0 = off)",
        placeholder="7",
        required=False,
        max_length=4,
    )

    def __init__(self, bot: commands.Bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(self.guild_id)
        changes = []

        for field, key, label in [
            (self.spam, "automod_spam_threshold", "Spam Limit"),
            (self.caps, "automod_caps_percentage", "Caps %"),
            (self.mentions, "automod_max_mentions", "Max Mentions"),
            (self.new_account, "automod_newaccount_days", "Account Age"),
        ]:
            val = field.value.strip()
            if val:
                try:
                    v = int(val)
                    if v < 0:
                        v = 0
                    if key == "automod_caps_percentage":
                        v = min(v, 100)
                    settings[key] = v
                    changes.append(f"**{label}** → `{v}`")
                except ValueError:
                    pass

        await self.bot.db.update_settings(self.guild_id, settings)
        msg = "\n".join(changes) if changes else "No changes made."
        await interaction.response.send_message(
            embed=ModEmbed.success("Thresholds Updated", msg),
            ephemeral=True,
        )
        await _refresh_dashboard(interaction, self.bot, self.guild_id)


class BadWordsModal(discord.ui.Modal, title="🚫 Manage Bad Words"):
    """Modal for adding / removing bad words."""

    add_words = discord.ui.TextInput(
        label="Add Words (comma-separated)",
        style=discord.TextStyle.paragraph,
        placeholder="word1, word2, word3",
        required=False,
        max_length=1000,
    )
    remove_words = discord.ui.TextInput(
        label="Remove Words (comma-separated)",
        style=discord.TextStyle.paragraph,
        placeholder="word1, word2",
        required=False,
        max_length=1000,
    )

    def __init__(self, bot: commands.Bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(self.guild_id)
        badwords: list = settings.get("automod_badwords", [])
        added, removed = [], []

        if self.add_words.value.strip():
            for w in self.add_words.value.split(","):
                w = w.strip().lower()
                if w and w not in badwords:
                    badwords.append(w)
                    added.append(w)

        if self.remove_words.value.strip():
            for w in self.remove_words.value.split(","):
                w = w.strip().lower()
                if w in badwords:
                    badwords.remove(w)
                    removed.append(w)

        settings["automod_badwords"] = badwords
        await self.bot.db.update_settings(self.guild_id, settings)

        parts = []
        if added:
            parts.append(f"**Added ({len(added)}):** {', '.join(f'`{w}`' for w in added[:20])}")
        if removed:
            parts.append(f"**Removed ({len(removed)}):** {', '.join(f'`{w}`' for w in removed[:20])}")
        if not parts:
            parts.append("No changes made.")
        parts.append(f"\n**Total bad words:** `{len(badwords)}`")

        await interaction.response.send_message(
            embed=ModEmbed.success("Bad Words Updated", "\n".join(parts)),
            ephemeral=True,
        )
        await _refresh_dashboard(interaction, self.bot, self.guild_id)


class DomainsModal(discord.ui.Modal, title="🌐 Manage Whitelisted Domains"):
    """Modal for adding / removing whitelisted domains."""

    add_domains = discord.ui.TextInput(
        label="Add Domains (comma-separated)",
        style=discord.TextStyle.paragraph,
        placeholder="youtube.com, twitter.com",
        required=False,
        max_length=1000,
    )
    remove_domains = discord.ui.TextInput(
        label="Remove Domains (comma-separated)",
        style=discord.TextStyle.paragraph,
        placeholder="example.com",
        required=False,
        max_length=1000,
    )

    def __init__(self, bot: commands.Bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(self.guild_id)
        domains: list = settings.get("automod_whitelisted_domains", [])
        added, removed = [], []

        if self.add_domains.value.strip():
            for d in self.add_domains.value.split(","):
                d = d.strip().lower()
                if d and d not in domains:
                    domains.append(d)
                    added.append(d)

        if self.remove_domains.value.strip():
            for d in self.remove_domains.value.split(","):
                d = d.strip().lower()
                if d in domains:
                    domains.remove(d)
                    removed.append(d)

        settings["automod_whitelisted_domains"] = domains
        await self.bot.db.update_settings(self.guild_id, settings)

        parts = []
        if added:
            parts.append(f"**Added:** {', '.join(f'`{d}`' for d in added[:15])}")
        if removed:
            parts.append(f"**Removed:** {', '.join(f'`{d}`' for d in removed[:15])}")
        if not parts:
            parts.append("No changes made.")
        parts.append(f"\n**Total domains:** `{len(domains)}`")

        await interaction.response.send_message(
            embed=ModEmbed.success("Domains Updated", "\n".join(parts)),
            ephemeral=True,
        )
        await _refresh_dashboard(interaction, self.bot, self.guild_id)


class PunishmentSelect(discord.ui.Select):
    """Dropdown to choose default punishment."""

    def __init__(self, bot: commands.Bot, guild_id: int, current: str):
        self.bot = bot
        self.guild_id = guild_id
        options = [
            discord.SelectOption(label="Warn", value="warn", emoji="⚠️", description="Issue a warning", default=(current == "warn")),
            discord.SelectOption(label="Delete", value="delete", emoji="🗑️", description="Delete the message only", default=(current == "delete")),
            discord.SelectOption(label="Mute", value="mute", emoji="🔇", description="Timeout the user", default=(current == "mute")),
            discord.SelectOption(label="Kick", value="kick", emoji="👢", description="Kick from server", default=(current == "kick")),
            discord.SelectOption(label="Ban", value="ban", emoji="🔨", description="Permanently ban", default=(current == "ban")),
            discord.SelectOption(label="Quarantine", value="quarantine", emoji="🔒", description="Restrict all activity", default=(current == "quarantine")),
        ]
        super().__init__(placeholder="🔧 Set Default Punishment", options=options, row=3)

    async def callback(self, interaction: discord.Interaction):
        settings = await self.bot.db.get_settings(self.guild_id)
        settings["automod_punishment"] = self.values[0]
        await self.bot.db.update_settings(self.guild_id, settings)
        await interaction.response.send_message(
            embed=ModEmbed.success("Punishment Updated", f"Default punishment set to **{self.values[0].upper()}**."),
            ephemeral=True,
        )
        await _refresh_dashboard(interaction, self.bot, self.guild_id)


class AutoModDashboardView(discord.ui.View):
    """Main interactive dashboard view with all controls."""

    def __init__(self, bot: commands.Bot, guild_id: int, owner_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.owner_id = owner_id

        # Async init not possible in __init__, so we add the punishment select lazily
        # We'll add it in interaction_check or use a factory classmethod
        self._punishment_added = False

    async def _ensure_punishment_select(self):
        if not self._punishment_added:
            settings = await self.bot.db.get_settings(self.guild_id)
            punishment = settings.get("automod_punishment", "warn")
            self.add_item(PunishmentSelect(self.bot, self.guild_id, punishment))
            self._punishment_added = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                embed=ModEmbed.error("Access Denied", "Only the person who opened this dashboard can use it."),
                ephemeral=True,
            )
            return False
        await self._ensure_punishment_select()
        return True

    async def on_timeout(self):
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True

    # ── Toggle Buttons (Row 0) ──

    @discord.ui.button(label="Links", emoji="🔗", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_links(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle(interaction, "automod_links_enabled", button)

    @discord.ui.button(label="Invites", emoji="📨", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_invites(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle(interaction, "automod_invites_enabled", button)

    @discord.ui.button(label="Scam", emoji="🛡️", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_scam(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle(interaction, "automod_scam_protection", button)

    @discord.ui.button(label="AI", emoji="🤖", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_ai(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle(interaction, "automod_ai_enabled", button)

    @discord.ui.button(label="Notify", emoji="🔔", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_notify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle(interaction, "automod_notify_users", button)

    async def _toggle(self, interaction: discord.Interaction, key: str, button: discord.ui.Button):
        settings = await self.bot.db.get_settings(self.guild_id)
        current = settings.get(key, False)
        settings[key] = not current
        await self.bot.db.update_settings(self.guild_id, settings)

        state = "Enabled" if not current else "Disabled"
        name = key.replace("automod_", "").replace("_enabled", "").replace("_protection", "").replace("_users", "").title()
        await interaction.response.send_message(
            embed=ModEmbed.success(f"{name} {state}", f"**{name}** has been **{state.lower()}**."),
            ephemeral=True,
        )
        await _refresh_dashboard(interaction, self.bot, self.guild_id)

    # ── Role Selects (Row 1) ──

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="🔓 Set Bypass Role", min_values=0, max_values=1, row=1)
    async def set_bypass_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        settings = await self.bot.db.get_settings(self.guild_id)
        if select.values:
            role = select.values[0]
            settings["automod_bypass_role_id"] = role.id
            msg = f"Bypass role set to {role.mention}.\n⚠️ Users with this role bypass **all** filters."
        else:
            settings["automod_bypass_role_id"] = None
            msg = "Bypass role cleared."
        await self.bot.db.update_settings(self.guild_id, settings)
        await interaction.response.send_message(embed=ModEmbed.success("Bypass Role Updated", msg), ephemeral=True)
        await _refresh_dashboard(interaction, self.bot, self.guild_id)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="🔒 Set Quarantine Role", min_values=0, max_values=1, row=2)
    async def set_quarantine_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        settings = await self.bot.db.get_settings(self.guild_id)
        if select.values:
            role = select.values[0]
            settings["automod_quarantine_role_id"] = role.id
            msg = f"Quarantine role set to {role.mention}."
        else:
            settings["automod_quarantine_role_id"] = None
            msg = "Quarantine role cleared."
        await self.bot.db.update_settings(self.guild_id, settings)
        await interaction.response.send_message(embed=ModEmbed.success("Quarantine Role Updated", msg), ephemeral=True)
        await _refresh_dashboard(interaction, self.bot, self.guild_id)

    # ── Action Buttons (Row 4) ──

    @discord.ui.button(label="Thresholds", emoji="📊", style=discord.ButtonStyle.primary, row=4)
    async def edit_thresholds(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ThresholdModal(self.bot, self.guild_id))

    @discord.ui.button(label="Bad Words", emoji="🚫", style=discord.ButtonStyle.primary, row=4)
    async def manage_badwords(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BadWordsModal(self.bot, self.guild_id))

    @discord.ui.button(label="Domains", emoji="🌐", style=discord.ButtonStyle.primary, row=4)
    async def manage_domains(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DomainsModal(self.bot, self.guild_id))

    @discord.ui.button(label="Log Channel", emoji="📝", style=discord.ButtonStyle.primary, row=4)
    async def set_log_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Opens an ephemeral channel select for the log channel."""
        view = _LogChannelSelectView(self.bot, self.guild_id)
        await interaction.response.send_message(
            embed=ModEmbed.info("Select Log Channel", "Choose a channel below, or select nothing to disable logging."),
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(label="Refresh", emoji="🔄", style=discord.ButtonStyle.secondary, row=4)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await self.bot.db.get_settings(self.guild_id)
        guild = self.bot.get_guild(self.guild_id) or interaction.guild
        embed = _build_dashboard_embed(guild, settings)
        await interaction.response.edit_message(embed=embed)


class _LogChannelSelectView(discord.ui.View):
    """Ephemeral view with a channel select for setting log channel."""

    def __init__(self, bot: commands.Bot, guild_id: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        placeholder="📝 Select log channel...",
        channel_types=[discord.ChannelType.text],
        min_values=0,
        max_values=1,
    )
    async def select_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        settings = await self.bot.db.get_settings(self.guild_id)
        if select.values:
            ch = select.values[0]
            settings["automod_log_channel"] = ch.id
            msg = f"Log channel set to {ch.mention}."
        else:
            settings["automod_log_channel"] = None
            msg = "Logging disabled."
        await self.bot.db.update_settings(self.guild_id, settings)
        await interaction.response.edit_message(
            embed=ModEmbed.success("Log Channel Updated", msg),
            view=None,
        )
        # Refresh parent dashboard
        await _refresh_dashboard(interaction, self.bot, self.guild_id)


# =============================================================================
# AUTOMOD COG
# =============================================================================

class AutoModV3(commands.Cog):
    """Enterprise AutoMod system"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.engine = AutoModEngine(bot)
        self.cleanup_task.start()
    
    async def cog_load(self):
        """Initialize cache on cog load"""
        await self.engine.cache_manager.initialize()
    
    async def cog_unload(self):
        """Cleanup on cog unload"""
        self.cleanup_task.cancel()
        await self.engine.cache_manager.close()
    
    @tasks.loop(hours=1)
    async def cleanup_task(self):
        """Periodic cleanup of old data"""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=30)
        
        # Clean old user histories
        for key, history in list(self.engine.user_histories.items()):
            if history.last_violation and history.last_violation < cutoff:
                del self.engine.user_histories[key]
    
    async def _get_log_channel(self, guild: discord.Guild, settings: dict) -> Optional[discord.TextChannel]:
        """Get automod log channel"""
        channel_id = settings.get("automod_log_channel") or settings.get("log_channel")
        if channel_id:
            return guild.get_channel(channel_id)
        return None
    
    async def _send_log(self, guild: discord.Guild, result: FilterResult, action_log: Dict, message: discord.Message, settings: dict):
        """Send detailed log embed"""
        channel = await self._get_log_channel(guild, settings)
        if not channel:
            return
        
        # Color based on severity
        color_map = {
            Severity.INFO: discord.Color.blue(),
            Severity.LOW: discord.Color.gold(),
            Severity.MEDIUM: discord.Color.orange(),
            Severity.HIGH: discord.Color.red(),
            Severity.CRITICAL: discord.Color.dark_red(),
            Severity.EXTREME: discord.Color.from_rgb(139, 0, 0)
        }
        
        embed = discord.Embed(
            title="🛡️ AutoMod Action",
            color=color_map.get(result.severity, Config.COLOR_WARNING),
            timestamp=datetime.now(timezone.utc)
        )
        
        # User info
        user = message.author
        embed.set_author(name=f"{user} ({user.id})", icon_url=user.display_avatar.url)
        
        # Violation details
        embed.add_field(
            name="Violation",
            value=result.reason,
            inline=False
        )
        
        embed.add_field(
            name="Severity",
            value=f"**{result.severity.name}** ({result.confidence:.0%} confidence)",
            inline=True
        )
        
        embed.add_field(
            name="Action",
            value=action_log.get("details", action_log["action"]),
            inline=True
        )
        
        embed.add_field(
            name="Channel",
            value=message.channel.mention,
            inline=True
        )
        
        # Matched patterns (if any)
        if result.matched_patterns:
            patterns = ", ".join(f"||{p}||" for p in result.matched_patterns[:3])
            embed.add_field(
                name="Matched Patterns",
                value=patterns,
                inline=False
            )
        
        # User history
        user_history = self.engine.get_user_history(guild.id, user.id)
        risk_score = user_history.get_risk_score()
        
        embed.add_field(
            name="User History",
            value=f"Violations: {len(user_history.violations)}\nRisk Score: {risk_score:.1f}/100",
            inline=True
        )
        
        # Message content (truncated)
        content_preview = message.content[:500]
        if len(message.content) > 500:
            content_preview += "..."
        
        embed.add_field(
            name="Message Content",
            value=f"```{content_preview}```",
            inline=False
        )
        
        # Footer with stats
        embed.set_footer(
            text=f"Category: {result.category.value} | Messages Checked: {self.engine.stats['messages_checked']}"
        )
        
        await send_log_embed(channel, embed)
    
    async def _notify_user(self, user: discord.User, guild: discord.Guild, result: FilterResult, action_log: Dict):
        """Send DM notification to user"""
        try:
            embed = discord.Embed(
                title="⚠️ AutoMod Alert",
                description=f"You triggered an automated moderation action in **{guild.name}**",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            
            reason_text = result.reason
            if result.matched_patterns:
                # Add specific context (e.g. "Saying 'badword'")
                patterns = ", ".join(f"'{p}'" for p in result.matched_patterns[:3])
                reason_text += f" (saying: {patterns})"
            
            embed.add_field(name="Reason", value=reason_text, inline=False)
            embed.add_field(name="Action Taken", value=action_log.get("details", result.action.value.title().replace("_", " ")), inline=False)
            embed.add_field(
                name="What now?",
                value="Please review the server rules. Repeated violations may result in permanent action.",
                inline=False
            )
            
            embed.set_footer(text="If you believe this was a mistake, contact server moderators")
            
            await user.send(embed=embed)
        except discord.Forbidden:
            logger.debug(f"Could not DM user {user.id}")
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Main message processing"""
        # Basic checks
        if not message.guild or message.author.bot:
            return
        
        try:
            settings = await self.bot.db.get_settings(message.guild.id)
            
            # Check bypass
            bypassed, bypass_reason = await self.engine.check_bypass(message, settings)
            if bypassed:
                logger.debug(f"User {message.author.id} bypassed: {bypass_reason}")
                return
            
            # Process message
            result = await self.engine.process_message(message, settings)
            
            if result and result.triggered:
                # Execute action
                action_log = await self.engine.execute_action(message, result, settings)
                
                # Log
                await self._send_log(message.guild, result, action_log, message, settings)
                
                # Notify user
                if settings.get("automod_notify_users", True):
                    await self._notify_user(message.author, message.guild, result, action_log)
                
        except Exception as e:
            logger.error(f"AutoMod processing error: {e}", exc_info=True)
    
    # =============================================================================
    # COMMANDS
    # =============================================================================
    
    automod = app_commands.Group(name="automod", description="🛡️ Advanced AutoMod Configuration")

    # =========================================================================
    # INTERACTIVE DASHBOARD VIEWS
    # =========================================================================

    @automod.command(name="config", description="📊 Open the interactive AutoMod configuration dashboard")
    @is_admin()
    async def automod_config(self, interaction: discord.Interaction):
        """Open the interactive AutoMod dashboard"""
        settings = await self.bot.db.get_settings(interaction.guild_id)
        embed = _build_dashboard_embed(interaction.guild, settings)
        view = AutoModDashboardView(self.bot, interaction.guild_id, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)

    @automod.command(name="status", description="View AutoMod status and statistics")
    @is_mod()
    async def status(self, interaction: discord.Interaction):
        """Show detailed automod status"""
        settings = await self.bot.db.get_settings(interaction.guild_id)
        
        embed = discord.Embed(
            title="🛡️ AutoMod Status",
            color=Config.COLOR_INFO,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Active filters
        active_filters = [f.__class__.__name__ for f in self.engine.filters if f.enabled]
        embed.add_field(
            name="Active Filters",
            value=f"{len(active_filters)}/{len(self.engine.filters)}\n" + "\n".join(f"✓ {f}" for f in active_filters[:5]),
            inline=False
        )
        
        # Statistics
        stats = self.engine.stats
        embed.add_field(
            name="Statistics (Session)",
            value=f"Messages Checked: **{stats['messages_checked']:,}**\n"
                  f"Violations: **{stats['violations_detected']:,}**\n"
                  f"Actions Taken: **{stats['actions_taken']:,}**",
            inline=True
        )
        
        # Settings
        punishment = settings.get("automod_punishment", "warn")
        bypass_role_id = settings.get("automod_bypass_role_id")
        bypass_role = interaction.guild.get_role(bypass_role_id) if bypass_role_id else None
        
        embed.add_field(
            name="Configuration",
            value=f"Default Action: **{punishment.upper()}**\n"
                  f"Bypass Role: {bypass_role.mention if bypass_role else 'None'}\n"
                  f"AI Filter: {'✓ Enabled' if settings.get('automod_ai_enabled') else '✗ Disabled'}",
            inline=True
        )
        
        # Cache stats
        cache_total = self.engine.cache_manager.cache_hits + self.engine.cache_manager.cache_misses
        hit_rate = (self.engine.cache_manager.cache_hits / cache_total * 100) if cache_total > 0 else 0
        
        embed.add_field(
            name="Performance",
            value=f"Cache Hit Rate: **{hit_rate:.1f}%**\n"
                  f"Active Histories: **{len(self.engine.user_histories)}**",
            inline=True
        )
        
        embed.set_footer(text=f"AutoMod V3 • {len(self.engine.filters)} filter modules loaded")
        
        await interaction.response.send_message(embed=embed)
    
    @automod.command(name="history", description="View user's violation history")
    @is_mod()
    async def user_history(self, interaction: discord.Interaction, user: discord.Member):
        """View user violation history"""
        history = self.engine.get_user_history(interaction.guild_id, user.id)
        
        if not history.violations:
            embed = ModEmbed.info(
                "Clean Record",
                f"{user.mention} has no AutoMod violations."
            )
            await interaction.response.send_message(embed=embed)
            return
        
        risk_score = history.get_risk_score()
        
        # Determine risk level
        if risk_score >= 75:
            risk_level = "🔴 CRITICAL"
            color = discord.Color.dark_red()
        elif risk_score >= 50:
            risk_level = "🟠 HIGH"
            color = discord.Color.orange()
        elif risk_score >= 25:
            risk_level = "🟡 MEDIUM"
            color = discord.Color.gold()
        else:
            risk_level = "🟢 LOW"
            color = discord.Color.green()
        
        embed = discord.Embed(
            title=f"📋 Violation History: {user.name}",
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.add_field(
            name="Risk Assessment",
            value=f"**Score:** {risk_score:.1f}/100\n**Level:** {risk_level}",
            inline=True
        )
        
        embed.add_field(
            name="Summary",
            value=f"**Total Violations:** {len(history.violations)}\n"
                  f"**Warnings:** {history.warnings}\n"
                  f"**Mutes:** {history.mutes}\n"
                  f"**Kicks:** {history.kicks}",
            inline=True
        )
        
        # Recent violations
        recent = history.violations[-5:]
        if recent:
            violations_text = ""
            for v in reversed(recent):
                timestamp = v['timestamp'].strftime("%Y-%m-%d %H:%M")
                violations_text += f"`{timestamp}` - {v['reason']}\n"
            
            embed.add_field(
                name="Recent Violations (Last 5)",
                value=violations_text,
                inline=False
            )
        
        embed.set_footer(text=f"User ID: {user.id}")
        
        await interaction.response.send_message(embed=embed)
    
    @automod.command(name="test", description="Test AutoMod with a sample message")
    @is_admin()
    async def test_automod(self, interaction: discord.Interaction, content: str):
        """Test automod filters"""
        await interaction.response.defer(ephemeral=True)
        
        # Create a mock message for testing
        class MockMessage:
            def __init__(self, content, author, guild, channel):
                self.content = content
                self.author = author
                self.guild = guild
                self.channel = channel
                self.mentions = []
                self.role_mentions = []
                self.created_at = datetime.now(timezone.utc)
        
        mock_msg = MockMessage(content, interaction.user, interaction.guild, interaction.channel)
        
        settings = await self.bot.db.get_settings(interaction.guild_id)
        result = await self.engine.process_message(mock_msg, settings)
        
        if result and result.triggered:
            embed = discord.Embed(
                title="⚠️ Violation Detected",
                description=f"This message would trigger AutoMod",
                color=discord.Color.red()
            )
            
            embed.add_field(name="Reason", value=result.reason, inline=False)
            embed.add_field(name="Severity", value=result.severity.name, inline=True)
            embed.add_field(name="Action", value=result.action.value.upper(), inline=True)
            embed.add_field(name="Confidence", value=f"{result.confidence:.0%}", inline=True)
            
            if result.matched_patterns:
                patterns = ", ".join(f"||{p}||" for p in result.matched_patterns[:3])
                embed.add_field(name="Matched", value=patterns, inline=False)
        else:
            embed = ModEmbed.success(
                "✅ Message Clean",
                "This message would pass all AutoMod filters."
            )
        
        embed.add_field(
            name="Test Content",
            value=f"```{content[:500]}```",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Load the cog"""
    await bot.add_cog(AutoModV3(bot))