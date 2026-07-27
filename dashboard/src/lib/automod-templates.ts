/**
 * AutoMod templates — curated starting points that map 1:1 onto the flat
 * `automod_*` keys in the bot's guild_settings blob. Applying a template
 * writes the whole settings map; everything remains editable afterwards.
 */

export type AutomodTemplate = {
  id: string
  name: string
  tagline: string
  description: string
  settings: Record<string, unknown>
}

/** Default dangerous-domain list mirrored from cogs/automod/config.py. */
export const DEFAULT_LINK_BLOCKLIST: string[] = [
  'grabify.link', 'grabify.org', 'iplogger.org', 'iplogger.com', 'iplogger.net',
  'iplogger.ru', 'ipgrabber.ru', 'ipgraber.ru', '2no.co', 'blasze.tk', 'yip.su',
  'webresolver.nl', 'gyazo.in', 'limes.media',
  'bit.ly', 'tinyurl.com', 'tiny.one', 'tiny.cc', 'cutt.ly', 'rb.gy', 'is.gd',
  'v.gd', 'goo.gl', 'adf.ly', 'bc.vc', 'shorte.st', 'shorturl.at', 'bit.do',
  'soo.gd', 'clck.ru', 't.ly', 'ow.ly',
  'discrodapp.com', 'discrod.net', 'discordgift.site', 'steamcommunuty.com',
  'steamcomunity.com', 'steamcornmunity.com', 'steamncomunity.com',
]

const STARTER_BADWORDS = [
  'nigger', 'nigga', 'faggot', 'kys', 'kill yourself', 'rape', 'retard',
]

const EVERY_RULE_ON: Record<string, boolean> = {
  automod_badwords_enabled: true,
  automod_scam_protection: true,
  automod_spam_enabled: true,
  automod_links_enabled: true,
  automod_invites_enabled: true,
  automod_mentions_enabled: true,
  automod_caps_enabled: true,
  automod_duplicates_enabled: true,
  automod_fast_messages_enabled: true,
  automod_emoji_spam_enabled: true,
  automod_wall_spam_enabled: true,
  automod_attachments_enabled: true,
  automod_unicode_spam_enabled: true,
  automod_newaccount_enabled: true,
  automod_raid_enabled: true,
}

export const AUTOMOD_TEMPLATES: readonly AutomodTemplate[] = [
  {
    id: 'recommended',
    name: 'Recommended',
    tagline: 'Balanced cover for most servers',
    description: 'Scam, link, invite, spam, and mention protection with warn-first actions. Nothing exotic — the set we would run ourselves.',
    settings: {
      automod_badwords_enabled: false,
      automod_scam_protection: true,
      automod_spam_enabled: true,
      automod_links_enabled: true,
      automod_invites_enabled: true,
      automod_mentions_enabled: true,
      automod_caps_enabled: false,
      automod_duplicates_enabled: true,
      automod_fast_messages_enabled: false,
      automod_emoji_spam_enabled: true,
      automod_wall_spam_enabled: false,
      automod_attachments_enabled: false,
      automod_unicode_spam_enabled: true,
      automod_newaccount_enabled: true,
      automod_raid_enabled: true,
      automod_links_mode: 'dangerous',
      automod_links_blocklist: DEFAULT_LINK_BLOCKLIST,
      automod_rule_actions: {
        scams: { action: 'timeout', delete: true, duration: 3600 },
        links: { action: 'timeout', delete: true, duration: 1800 },
        raid: { action: 'timeout', delete: false, duration: 3600 },
      },
    },
  },
  {
    id: 'relaxed',
    name: 'Relaxed',
    tagline: 'Only the dangerous stuff',
    description: 'Just scams and dangerous links. Chat stays free — only genuinely harmful posts get removed.',
    settings: {
      automod_scam_protection: true,
      automod_links_enabled: true,
      automod_links_mode: 'dangerous',
      automod_links_blocklist: DEFAULT_LINK_BLOCKLIST,
      automod_rule_actions: {
        scams: { action: 'timeout', delete: true, duration: 3600 },
        links: { action: 'warn', delete: true },
      },
    },
  },
  {
    id: 'community',
    name: 'Community',
    tagline: 'Conversation-first with a word wall',
    description: 'Everything in Recommended plus a starter blocklist of slurs and attacks, duplicate-spam and caps control.',
    settings: {
      ...EVERY_RULE_ON,
      automod_fast_messages_enabled: false,
      automod_wall_spam_enabled: false,
      automod_attachments_enabled: false,
      automod_badwords: STARTER_BADWORDS,
      automod_links_mode: 'dangerous',
      automod_links_blocklist: DEFAULT_LINK_BLOCKLIST,
      automod_rule_actions: {
        badwords: { action: 'warn', delete: true },
        scams: { action: 'timeout', delete: true, duration: 3600 },
        links: { action: 'timeout', delete: true, duration: 1800 },
        invites: { action: 'warn', delete: true },
        raid: { action: 'timeout', delete: false, duration: 3600 },
      },
    },
  },
  {
    id: 'gaming',
    name: 'Gaming',
    tagline: 'Tolerant of hype, hard on scams',
    description: 'Caps, emoji, and walls stay legal (hype happens). Scams, links, invites, mention spam, and raids get punished.',
    settings: {
      ...EVERY_RULE_ON,
      automod_caps_enabled: false,
      automod_emoji_spam_enabled: false,
      automod_wall_spam_enabled: false,
      automod_links_mode: 'dangerous',
      automod_links_blocklist: DEFAULT_LINK_BLOCKLIST,
      automod_rule_actions: {
        scams: { action: 'timeout', delete: true, duration: 7200 },
        links: { action: 'timeout', delete: true, duration: 3600 },
        mentions: { action: 'timeout', delete: true, duration: 1800 },
        raid: { action: 'kick', delete: false },
      },
    },
  },
  {
    id: 'strict',
    name: 'Strict',
    tagline: 'Every rule on, tight thresholds',
    description: 'All fifteen detectors armed with harsher actions. Good for large public servers that attract drive-by spam.',
    settings: {
      ...EVERY_RULE_ON,
      automod_max_mentions: 4,
      automod_caps_percentage: 60,
      automod_emoji_spam_threshold: 10,
      automod_duplicate_threshold: 2,
      automod_badwords: STARTER_BADWORDS,
      automod_links_mode: 'dangerous',
      automod_links_blocklist: DEFAULT_LINK_BLOCKLIST,
      automod_rule_actions: {
        badwords: { action: 'timeout', delete: true, duration: 1800 },
        scams: { action: 'kick', delete: true },
        links: { action: 'timeout', delete: true, duration: 3600 },
        invites: { action: 'timeout', delete: true, duration: 1800 },
        spam: { action: 'timeout', delete: true, duration: 1800 },
        raid: { action: 'ban', delete: false },
      },
    },
  },
  {
    id: 'lockdown',
    name: 'Lockdown',
    tagline: 'Under active attack — maximum denial',
    description: 'Allowlist-only links, every detector on, kick/ban actions, new accounts rejected under 30 days. Use while repelling a raid wave.',
    settings: {
      ...EVERY_RULE_ON,
      automod_links_mode: 'allowlist',
      automod_links_blocklist: DEFAULT_LINK_BLOCKLIST,
      automod_links_whitelist: ['discord.com', 'discordapp.com', 'youtube.com', 'youtu.be', 'github.com'],
      automod_newaccount_days: 30,
      automod_newaccount_join_action: 'kick',
      automod_badwords: STARTER_BADWORDS,
      automod_rule_actions: {
        badwords: { action: 'timeout', delete: true, duration: 3600 },
        scams: { action: 'ban', delete: true },
        links: { action: 'kick', delete: true },
        invites: { action: 'timeout', delete: true, duration: 3600 },
        spam: { action: 'timeout', delete: true, duration: 3600 },
        mentions: { action: 'timeout', delete: true, duration: 3600 },
        raid: { action: 'ban', delete: false },
      },
    },
  },
] as const

export function automodTemplate(id: string): AutomodTemplate | null {
  return AUTOMOD_TEMPLATES.find((template) => template.id === id) ?? null
}

/**
 * Keys a template apply may write. Built from the rule contract plus the
 * extra policy/list keys the templates legitimately touch — anything else
 * in the payload is rejected.
 */
export const TEMPLATE_ALLOWED_KEYS: ReadonlySet<string> = new Set([
  'automod_links_mode',
  'automod_links_blocklist',
  'automod_links_whitelist',
  'automod_whitelisted_domains',
  'automod_badwords',
  'automod_allowed_invites',
  'automod_rule_actions',
  'automod_newaccount_join_action',
  'automod_raid_punishment',
  'automod_max_mentions',
  'automod_caps_percentage',
  'automod_caps_min_length',
  'automod_duplicate_threshold',
  'automod_emoji_spam_threshold',
  'automod_spam_threshold',
  'automod_fast_message_threshold',
  'automod_newaccount_days',
  'automod_delete_violations',
])
