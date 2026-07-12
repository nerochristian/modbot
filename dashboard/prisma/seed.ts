import { PrismaClient } from '@prisma/client'
import { PrismaLibSql } from '@prisma/adapter-libsql'
import { hashPassword } from '../src/lib/auth'
import { DEFAULT_ROLE_MATRIX, ROLES } from '../src/lib/rbac'
import { WIDGET_CATALOG, DEFAULT_DASHBOARD_CONFIG } from '../src/lib/dashboard-config'

const adapter = new PrismaLibSql({ url: process.env.DATABASE_URL ?? 'file:./dev.db' })
const prisma = new PrismaClient({ adapter })

// Deterministic PRNG so seeded data is stable across runs (mulberry32).
function makeRng(seed: number) {
  let a = seed
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
const rng = makeRng(20260708)
const pick = <T>(arr: T[]): T => arr[Math.floor(rng() * arr.length)]
const between = (min: number, max: number) => min + rng() * (max - min)
const intBetween = (min: number, max: number) => Math.floor(between(min, max + 1))
const daysAgo = (n: number) => new Date(Date.now() - n * 86_400_000)
const hoursFromNow = (n: number) => new Date(Date.now() + n * 3_600_000)
const weighted = <T>(items: [T, number][]): T => {
  const total = items.reduce((s, [, w]) => s + w, 0)
  let r = rng() * total
  for (const [item, w] of items) {
    if ((r -= w) <= 0) return item
  }
  return items[0][0]
}

// Team (moderator) names.
const FIRST = ['Ava', 'Marcus', 'Priya', 'Liam', 'Sofia', 'Noah', 'Emma', 'Kai', 'Zara', 'Diego', 'Yuki', 'Omar', 'Lena', 'Theo', 'Nina', 'Ravi', 'Clara', 'Mateo', 'Ivy', 'Hugo']
const LAST = ['Thompson', 'Lee', 'Nair', 'Walker', 'Garcia', 'Chen', 'Novak', 'Okafor', 'Rossi', 'Haddad', 'Kim', 'Silva', 'Meyer', 'Patel', 'Dubois', 'Ivanov', 'Costa', 'Nguyen', 'Schmidt', 'Ahmed']

// Discord-style member handles.
const HANDLE_ADJ = ['shadow', 'crimson', 'frost', 'neon', 'lunar', 'toxic', 'silent', 'rapid', 'cosmic', 'void', 'pixel', 'turbo', 'ghost', 'ember', 'cyber', 'hyper', 'mystic', 'rogue', 'zen', 'atomic', 'velvet', 'iron', 'salty', 'based', 'grim']
const HANDLE_NOUN = ['fox', 'wolf', 'byte', 'raven', 'blade', 'ninja', 'reaper', 'phoenix', 'gamer', 'wizard', 'knight', 'dragon', 'sniper', 'panda', 'goblin', 'hydra', 'falcon', 'titan', 'specter', 'yeti', 'otter', 'moth', 'crab', 'lynx', 'orca']
const SERVER_ROLES = ['@everyone', 'Member', 'Regular', 'Active', 'Nitro Booster', 'Verified', 'Level 10', 'Level 30', 'Artist', 'Event Team', 'Muted']
const CHANNELS = ['#general', '#off-topic', '#memes', '#help', '#gaming', '#music', '#art-share', '#introductions', '#voice-chat', '#trades', '#clips', '#spam-hell']
const AVATAR_COLORS = ['#5865f2', '#3ddc97', '#f5a524', '#f0476b', '#38bdf8', '#8b5cf6', '#fb923c', '#14b8a6']

function fullName() {
  return `${pick(FIRST)} ${pick(LAST)}`
}
function emailFor(name: string, domain: string, i: number) {
  return `${name.toLowerCase().replace(/[^a-z]+/g, '.')}.${i}@${domain}`
}
function handle() {
  return `${pick(HANDLE_ADJ)}${pick(HANDLE_NOUN)}${rng() < 0.4 ? intBetween(1, 99) : ''}`
}
function snowflake() {
  // 17–19 digit Discord-style ID.
  return String(intBetween(1, 9)) + Array.from({ length: intBetween(16, 18) }, () => intBetween(0, 9)).join('')
}

async function reset() {
  // Order respects FK dependencies.
  await prisma.session.deleteMany()
  await prisma.notification.deleteMany()
  await prisma.activityLog.deleteMany()
  await prisma.auditLog.deleteMany()
  await prisma.invoice.deleteMany()
  await prisma.subscription.deleteMany()
  await prisma.report.deleteMany()
  await prisma.savedView.deleteMany()
  await prisma.dashboardConfig.deleteMany()
  await prisma.metricPoint.deleteMany()
  await prisma.appeal.deleteMany()
  await prisma.case.deleteMany()
  await prisma.automodRule.deleteMany()
  await prisma.member.deleteMany()
  await prisma.rolePermission.deleteMany()
  await prisma.widget.deleteMany()
  await prisma.featureToggle.deleteMany()
  await prisma.appSetting.deleteMany()
  await prisma.user.deleteMany()
}

async function seedRolesAndCatalog() {
  for (const role of ROLES) {
    for (const permission of DEFAULT_ROLE_MATRIX[role]) {
      await prisma.rolePermission.create({ data: { role, permission, allowed: true } })
    }
  }

  for (let i = 0; i < WIDGET_CATALOG.length; i++) {
    const w = WIDGET_CATALOG[i]
    await prisma.widget.create({
      data: {
        key: w.key,
        name: w.name,
        description: w.description,
        category: w.category,
        defaultVisible: w.defaultVisible,
        enabled: true,
        order: i,
      },
    })
  }

  const toggles = [
    { key: 'automod.ai', name: 'AI content scoring', description: 'Score messages for toxicity with an ML model before actioning.', enabled: true, rolloutRole: 'all' },
    { key: 'export.pdf', name: 'PDF export', description: 'Allow exporting reports and case logs as PDF.', enabled: true, rolloutRole: 'all' },
    { key: 'appeals.selfService', name: 'Self-service appeals', description: 'Let banned members submit appeals via a web form.', enabled: true, rolloutRole: 'all' },
    { key: 'raid.shield', name: 'Raid shield', description: 'Auto-lockdown on join spikes.', enabled: false, rolloutRole: 'admin' },
    { key: 'beta.layouts', name: 'Beta layouts', description: 'Experimental dashboard layouts.', enabled: false, rolloutRole: 'manager' },
    { key: 'sso.saml', name: 'SAML SSO', description: 'Enterprise single sign-on for the mod team.', enabled: false, rolloutRole: 'admin' },
  ]
  for (const t of toggles) await prisma.featureToggle.create({ data: t })

  const settings: Record<string, unknown> = {
    'app.name': 'Aegis',
    'app.supportEmail': 'support@aegisbot.gg',
    'app.signupsEnabled': true,
    'app.defaultRole': 'viewer',
    'app.maintenanceMode': false,
    'security.enforce2fa': false,
    'security.sessionTtlDays': 7,
    'branding.primaryColor': '#2743e6',
    'guild.name': 'The Nexus',
    'guild.id': '984157203847561216',
  }
  for (const [key, value] of Object.entries(settings)) {
    await prisma.appSetting.create({ data: { key, value: JSON.stringify(value) } })
  }
}

type SeededUser = { id: string; name: string; role: string }

async function seedUsers(): Promise<SeededUser[]> {
  const passwordHash = await hashPassword('password123')
  const core = [
    { email: 'admin@aegisbot.gg', name: 'Ava Thompson', role: 'admin', title: 'Server Owner' },
    { email: 'manager@aegisbot.gg', name: 'Marcus Lee', role: 'manager', title: 'Head Moderator' },
    { email: 'viewer@aegisbot.gg', name: 'Priya Nair', role: 'viewer', title: 'Trial Helper' },
  ]

  const users: SeededUser[] = []
  for (let i = 0; i < core.length; i++) {
    const c = core[i]
    const u = await prisma.user.create({
      data: {
        email: c.email,
        name: c.name,
        passwordHash,
        role: c.role,
        title: c.title,
        status: 'active',
        emailVerified: true,
        avatarColor: AVATAR_COLORS[i % AVATAR_COLORS.length],
        timezone: pick(['UTC', 'America/New_York', 'Europe/London', 'Asia/Kolkata']),
        twoFactorEnabled: i === 0,
        createdAt: daysAgo(intBetween(200, 400)),
        lastLoginAt: daysAgo(intBetween(0, 3)),
      },
    })
    users.push({ id: u.id, name: u.name, role: u.role })
  }

  // Additional moderators / helpers.
  for (let i = 0; i < 9; i++) {
    const name = fullName()
    const role = weighted([['viewer', 5], ['manager', 3], ['admin', 1]])
    const status = weighted([['active', 8], ['invited', 2], ['suspended', 1]])
    const u = await prisma.user.create({
      data: {
        email: emailFor(name, 'aegisbot.gg', i),
        name,
        passwordHash,
        role,
        status,
        title: pick(['Moderator', 'Helper', 'Admin', 'Community Manager', 'Event Host', 'Automod Engineer']),
        emailVerified: status === 'active',
        avatarColor: pick(AVATAR_COLORS),
        timezone: pick(['UTC', 'America/Los_Angeles', 'Europe/Berlin', 'Australia/Sydney']),
        createdAt: daysAgo(intBetween(10, 300)),
        lastLoginAt: status === 'invited' ? null : daysAgo(intBetween(0, 30)),
      },
    })
    users.push({ id: u.id, name: u.name, role: u.role })
  }
  return users
}

type SeededMember = { id: string; displayName: string; standing: string }

async function seedMembers(): Promise<SeededMember[]> {
  const created: SeededMember[] = []
  const usedIds = new Set<string>()
  for (let i = 0; i < 200; i++) {
    const username = handle()
    const displayName = rng() < 0.5 ? username : `${pick(FIRST)}`
    let discordId = snowflake()
    while (usedIds.has(discordId)) discordId = snowflake()
    usedIds.add(discordId)

    const standing = weighted([
      ['good', 68],
      ['watchlist', 12],
      ['muted', 6],
      ['banned', 8],
      ['left', 6],
    ])
    const riskLevel =
      standing === 'banned'
        ? weighted([['high', 4], ['critical', 6]])
        : standing === 'muted'
          ? weighted([['medium', 5], ['high', 5]])
          : standing === 'watchlist'
            ? weighted([['medium', 6], ['high', 3], ['low', 1]])
            : weighted([['low', 8], ['medium', 2]])
    const warnings =
      standing === 'good' ? intBetween(0, 1) : standing === 'watchlist' ? intBetween(1, 3) : intBetween(2, 6)
    const roleCount = intBetween(1, 4)
    const roles = Array.from(new Set(Array.from({ length: roleCount }, () => pick(SERVER_ROLES))))

    const m = await prisma.member.create({
      data: {
        username,
        displayName,
        discordId,
        avatarColor: pick(AVATAR_COLORS),
        standing,
        riskLevel,
        warnings,
        messages: standing === 'left' ? intBetween(5, 400) : intBetween(20, 24000),
        roles: JSON.stringify(roles),
        note: rng() < 0.15 ? pick(['Repeat offender — watch closely.', 'Alt of a banned user (suspected).', 'Good contributor, one bad day.', 'Ticket opened re: harassment.']) : null,
        joinedAt: daysAgo(intBetween(1, 720)),
        lastActiveAt: daysAgo(standing === 'left' || standing === 'banned' ? intBetween(10, 200) : intBetween(0, 14)),
      },
    })
    created.push({ id: m.id, displayName: m.displayName, standing: m.standing })
  }
  return created
}

const CASE_REASONS: Record<string, string[]> = {
  note: ['Flagged for monitoring after heated argument.', 'Verbal reminder about channel rules.', 'Context note: friend of reported user.'],
  warn: ['Spamming emotes in #general.', 'Mild insult toward another member.', 'Off-topic posting after reminder.', 'Backseat moderating repeatedly.', 'Posting NSFW-adjacent memes.'],
  mute: ['Continued spam after warning.', 'Argument escalated, needs cooldown.', 'Mic spam in voice channels.', 'Repeated pings to staff.'],
  timeout: ['Flooding chat during event.', 'Caps-lock ranting after warning.', 'Ignoring mod instructions.'],
  kick: ['Advertising another server.', 'Ban evasion attempt (first).', 'Refused to follow rules after multiple warnings.'],
  ban: ['Posting scam / phishing links.', 'Targeted harassment of a member.', 'Hate speech, zero tolerance.', 'Raid participation.', 'Doxxing threat.', 'NSFW content in SFW channel.'],
  unban: ['Appeal approved — genuine apology.', 'Ban was a mistake / mistaken identity.', 'Served time, second chance granted.'],
}

async function seedCases(members: SeededMember[], users: SeededUser[]) {
  const mods = users.filter((u) => u.role !== 'viewer')
  // Weight cases toward flagged members.
  const flagged = members.filter((m) => m.standing !== 'good')
  const pool = [...flagged, ...flagged, ...members] // over-represent flagged

  const created: { id: string; ref: number; memberId: string; type: string; severity: string; status: string }[] = []
  let ref = 1000
  const total = 210
  for (let i = 0; i < total; i++) {
    ref += 1
    const member = pick(pool)
    const type = weighted([
      ['note', 2],
      ['warn', 8],
      ['mute', 4],
      ['timeout', 3],
      ['kick', 2],
      ['ban', 3],
      ['unban', 1],
    ])
    const severity =
      type === 'ban'
        ? weighted([['high', 4], ['critical', 6]])
        : type === 'kick'
          ? weighted([['medium', 5], ['high', 5]])
          : type === 'mute' || type === 'timeout'
            ? weighted([['low', 3], ['medium', 6], ['high', 1]])
            : type === 'note'
              ? 'low'
              : weighted([['low', 6], ['medium', 4]])
    const createdAt = daysAgo(intBetween(0, 180))
    const isTemporary = type === 'mute' || type === 'timeout'
    const status = weighted([
      ['resolved', 6],
      ['open', 3],
      ['expired', type === 'mute' || type === 'timeout' ? 3 : 0],
      ['appealed', type === 'ban' ? 2 : 0],
    ])
    const mod = pick(mods)

    const c = await prisma.case.create({
      data: {
        ref,
        memberId: member.id,
        type,
        severity,
        status,
        reason: pick(CASE_REASONS[type]),
        moderator: mod.name,
        moderatorId: mod.id,
        channel: pick(CHANNELS),
        evidence: rng() < 0.4 ? JSON.stringify([`https://discord.com/channels/984157203847561216/${intBetween(1, 9)}${'0'.repeat(17)}`]) : null,
        expiresAt: isTemporary ? hoursFromNow(intBetween(-72, 168)) : null,
        createdAt,
        updatedAt: createdAt,
      },
    })
    created.push({ id: c.id, ref, memberId: member.id, type, severity, status })
  }
  return created
}

const TRIGGER_DEFS: { name: string; description: string; trigger: string; pattern: string | null; action: string; severity: string; exempt: string[] }[] = [
  { name: 'Blocked slurs', description: 'Instant removal of slurs and hate terms.', trigger: 'keyword', pattern: 'slur1, slur2, hate-term', action: 'ban', severity: 'critical', exempt: [] },
  { name: 'Scam link filter', description: 'Catches free-nitro and steal-gift phishing domains.', trigger: 'regex', pattern: '(?i)(free\\s*nitro|steam?community\\.ru|dlscord\\.gift)', action: 'ban', severity: 'critical', exempt: ['Nitro Booster'] },
  { name: 'Invite advertising', description: 'Removes third-party server invites.', trigger: 'invite', pattern: null, action: 'delete', severity: 'medium', exempt: ['Event Team', 'Verified'] },
  { name: 'Mass mention guard', description: 'Mutes users pinging too many members at once.', trigger: 'mention_spam', pattern: '5', action: 'mute', severity: 'high', exempt: ['Event Team'] },
  { name: 'Message flood', description: 'Timeouts rapid-fire message flooding.', trigger: 'spam', pattern: '6', action: 'timeout', severity: 'medium', exempt: ['Nitro Booster'] },
  { name: 'Excessive caps', description: 'Warns on messages that are mostly uppercase.', trigger: 'caps', pattern: '75', action: 'warn', severity: 'low', exempt: [] },
  { name: 'Suspicious links', description: 'Flags shortened / unknown links for review.', trigger: 'link', pattern: null, action: 'flag', severity: 'low', exempt: ['Verified', 'Regular'] },
  { name: 'Sketchy attachments', description: 'Deletes executable and script attachments.', trigger: 'attachment', pattern: '.exe, .scr, .bat, .js', action: 'delete', severity: 'high', exempt: [] },
  { name: 'Zalgo / spam text', description: 'Removes zalgo and unicode spam.', trigger: 'regex', pattern: '[\\u0300-\\u036f]{4,}', action: 'delete', severity: 'low', exempt: [] },
  { name: 'Discord token grabber', description: 'Bans on known token-grabber payload domains.', trigger: 'keyword', pattern: 'grabify, iplogger, token-grab', action: 'ban', severity: 'critical', exempt: [] },
]

async function seedAutomod() {
  for (const d of TRIGGER_DEFS) {
    const enabled = rng() < 0.85
    await prisma.automodRule.create({
      data: {
        name: d.name,
        description: d.description,
        trigger: d.trigger,
        pattern: d.pattern,
        action: d.action,
        severity: d.severity,
        exemptRoles: JSON.stringify(d.exempt),
        enabled,
        hits: enabled ? intBetween(12, 4200) : intBetween(0, 40),
        lastTriggeredAt: enabled ? daysAgo(intBetween(0, 6)) : null,
        createdAt: daysAgo(intBetween(30, 400)),
        updatedAt: daysAgo(intBetween(0, 20)),
      },
    })
  }
}

const APPEAL_MESSAGES = [
  'I was hacked and my account sent those links. I have 2FA on now — please give me another chance.',
  "Honestly I didn't know that channel was SFW only. Won't happen again, I love this community.",
  'The mute was a misunderstanding, I was quoting someone else. Can you review the context?',
  "I know I broke the rules and I'm genuinely sorry. I've been here two years and this was a one-off.",
  'That was my little brother on my PC. I take full responsibility and will keep it locked from now on.',
  'I think this was mistaken identity — I never posted in that channel. Happy to show my message history.',
]

async function seedAppeals(cases: { id: string; ref: number; memberId: string; type: string; status: string }[], users: SeededUser[]) {
  const mods = users.filter((u) => u.role !== 'viewer')
  // Appeals target bans/kicks/mutes.
  const appealable = cases.filter((c) => ['ban', 'kick', 'mute', 'timeout'].includes(c.type))
  let ref = 1000
  const count = Math.min(32, appealable.length)
  const shuffled = [...appealable].sort(() => rng() - 0.5).slice(0, count)
  for (let i = 0; i < shuffled.length; i++) {
    ref += 1
    const c = shuffled[i]
    const status = weighted([['pending', 4], ['approved', 2], ['denied', 3]])
    const submittedAt = daysAgo(intBetween(0, 60))
    const reviewed = status !== 'pending'
    const reviewer = reviewed ? pick(mods) : null
    await prisma.appeal.create({
      data: {
        ref,
        memberId: c.memberId,
        caseId: c.id,
        status,
        message: pick(APPEAL_MESSAGES),
        decision: reviewed
          ? status === 'approved'
            ? pick(['Appeal accepted, action reversed. Welcome back.', 'Verified the context, this was a mistake on our end.'])
            : pick(['Evidence is clear, appeal denied.', 'Pattern of behavior, denied. May reapply in 90 days.'])
          : null,
        reviewedBy: reviewer?.name ?? null,
        reviewedAt: reviewed ? new Date(submittedAt.getTime() + intBetween(2, 72) * 3_600_000) : null,
        submittedAt,
      },
    })
  }
}

async function seedMetrics() {
  const days = 365
  // Flow metrics accumulate per day; point-in-time metrics are gauges.
  const metrics: { name: string; base: number; growth: number; noise: number; min?: number; max?: number; decimals?: boolean }[] = [
    { name: 'actions', base: 34, growth: 0.0012, noise: 0.35 },
    { name: 'warns', base: 18, growth: 0.001, noise: 0.4 },
    { name: 'mutes', base: 7, growth: 0.0008, noise: 0.5 },
    { name: 'timeouts', base: 5, growth: 0.0008, noise: 0.5 },
    { name: 'kicks', base: 2.2, growth: 0.0004, noise: 0.7, min: 0 },
    { name: 'bans', base: 3.1, growth: 0.0006, noise: 0.6, min: 0 },
    { name: 'automodBlocks', base: 410, growth: 0.0018, noise: 0.25 },
    { name: 'joins', base: 120, growth: 0.0009, noise: 0.3 },
    { name: 'leaves', base: 74, growth: 0.0007, noise: 0.3 },
    { name: 'messages', base: 48000, growth: 0.0015, noise: 0.12 },
    // Gauges (point-in-time)
    { name: 'members', base: 24000, growth: 0.0011, noise: 0.01 },
    { name: 'online', base: 3400, growth: 0.001, noise: 0.08 },
    { name: 'openCases', base: 22, growth: 0.0003, noise: 0.25, min: 3 },
    { name: 'pendingAppeals', base: 9, growth: 0.0002, noise: 0.4, min: 0 },
  ]
  const rows: { metric: string; date: Date; value: number }[] = []
  for (const m of metrics) {
    for (let d = days; d >= 0; d--) {
      const t = days - d
      const weekly = 1 + 0.08 * Math.sin((t / 7) * Math.PI * 2)
      const trend = m.base * Math.pow(1 + m.growth, t)
      let value = trend * weekly * (1 + (rng() - 0.5) * 2 * m.noise)
      if (m.min !== undefined) value = Math.max(m.min, value)
      if (m.max !== undefined) value = Math.min(m.max, value)
      value = Math.round(value)
      rows.push({ metric: m.name, date: daysAgo(d), value })
    }
  }
  for (let i = 0; i < rows.length; i += 500) {
    await prisma.metricPoint.createMany({ data: rows.slice(i, i + 500) })
  }
}

async function seedBillingFor(users: SeededUser[]) {
  const admin = users[0]
  // "Server Premium" plans instead of SaaS billing.
  await prisma.subscription.create({
    data: {
      userId: admin.id,
      plan: 'enterprise',
      status: 'active',
      seats: 1,
      interval: 'month',
      amount: 2999,
      currentPeriodEnd: daysAgo(-18),
    },
  })
  await prisma.subscription.create({
    data: {
      userId: users[1].id,
      plan: 'pro',
      status: 'active',
      seats: 1,
      interval: 'month',
      amount: 999,
      currentPeriodEnd: daysAgo(-11),
    },
  })
  for (let m = 12; m >= 1; m--) {
    await prisma.invoice.create({
      data: {
        userId: admin.id,
        number: `AEG-2026-${String(13 - m).padStart(4, '0')}`,
        amount: 2999,
        status: m === 1 ? 'open' : 'paid',
        issuedAt: daysAgo(m * 30),
        periodStart: daysAgo(m * 30),
        periodEnd: daysAgo((m - 1) * 30),
      },
    })
  }
}

async function seedActivityAndAudit(users: SeededUser[], members: SeededMember[]) {
  const mods = users.filter((u) => u.role !== 'viewer')
  const actionTemplates: [string, () => string][] = [
    ['banned_member', () => pick(members).displayName],
    ['warned_member', () => pick(members).displayName],
    ['muted_member', () => pick(members).displayName],
    ['created_case', () => `#CASE-${String(intBetween(1001, 1210)).padStart(4, '0')}`],
    ['resolved_case', () => `#CASE-${String(intBetween(1001, 1210)).padStart(4, '0')}`],
    ['approved_appeal', () => `#APL-${String(intBetween(1001, 1032)).padStart(4, '0')}`],
    ['denied_appeal', () => `#APL-${String(intBetween(1001, 1032)).padStart(4, '0')}`],
    ['updated_automod_rule', () => pick(TRIGGER_DEFS).name],
    ['exported_data', () => 'cases.csv'],
    ['saved_view', () => 'Watchlist — critical'],
  ]
  for (let i = 0; i < 70; i++) {
    const u = pick(mods)
    const [action, target] = pick(actionTemplates)
    await prisma.activityLog.create({
      data: {
        userId: u.id,
        actorName: u.name,
        action,
        target: target(),
        metadata: JSON.stringify({ ip: `192.168.${intBetween(0, 255)}.${intBetween(0, 255)}` }),
        createdAt: daysAgo(intBetween(0, 30)),
      },
    })
  }

  const auditActions = [
    ['member.ban', 'Member'],
    ['automod.rule.update', 'AutomodRule'],
    ['setting.update', 'AppSetting'],
    ['user.role.update', 'User'],
    ['permission.update', 'RolePermission'],
    ['appeal.review', 'Appeal'],
  ]
  const admins = users.filter((u) => u.role === 'admin')
  for (let i = 0; i < 44; i++) {
    const u = pick(admins.length ? admins : users)
    const [action, entity] = pick(auditActions)
    await prisma.auditLog.create({
      data: {
        userId: u.id,
        actorName: u.name,
        action,
        entity,
        entityId: `id_${intBetween(1000, 9999)}`,
        ip: `10.0.${intBetween(0, 255)}.${intBetween(0, 255)}`,
        userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        metadata: JSON.stringify({ before: 'good', after: 'banned' }),
        createdAt: daysAgo(intBetween(0, 60)),
      },
    })
  }
}

async function seedNotificationsAndReports(users: SeededUser[]) {
  const admin = users[0]
  const notes = [
    { type: 'security', level: 'error', title: 'Raid detected', body: '38 accounts joined in 60s — raid shield engaged.', href: '/dashboard/activity' },
    { type: 'report', level: 'warning', title: 'Appeal awaiting review', body: 'Appeal #APL-1007 has been pending for 3 days.', href: '/dashboard/appeals' },
    { type: 'system', level: 'info', title: 'Automod updated', body: 'Rule "Scam link filter" blocked 214 messages today.', href: '/dashboard/automod' },
    { type: 'report', level: 'success', title: 'Report ready', body: 'Your "Weekly Moderation Digest" finished generating.', href: '/dashboard/reports' },
    { type: 'mention', level: 'info', title: 'You were mentioned', body: 'Marcus mentioned you on case #CASE-1194.', href: '/dashboard/cases' },
    { type: 'billing', level: 'success', title: 'Premium renewed', body: 'Server Premium renewed — thanks for supporting Aegis.', href: '/dashboard/billing' },
    { type: 'security', level: 'warning', title: 'Enable 2FA', body: 'Protect the mod team — require two-factor authentication.', href: '/dashboard/settings/security' },
    { type: 'system', level: 'info', title: 'New member spike', body: 'Joins are up 42% week-over-week.', href: '/dashboard/analytics' },
  ]
  for (let i = 0; i < notes.length; i++) {
    const n = notes[i]
    await prisma.notification.create({
      data: {
        userId: admin.id,
        type: n.type,
        level: n.level,
        title: n.title,
        body: n.body,
        href: n.href,
        read: i > 4,
        createdAt: daysAgo(i),
      },
    })
  }

  const reportDefs = [
    ['Weekly Moderation Digest', 'actions', 'ready', 'pdf'],
    ['Automod Hit Report', 'automod', 'ready', 'csv'],
    ['New Member Audit', 'members', 'ready', 'xlsx'],
    ['Daily Activity Digest', 'activity', 'scheduled', 'csv'],
    ['Ban Wave Analysis', 'custom', 'ready', 'json'],
    ['Appeal Outcomes Q3', 'custom', 'generating', 'pdf'],
    ['Top Flagged Channels', 'actions', 'ready', 'csv'],
    ['Annual Safety Summary', 'actions', 'ready', 'pdf'],
  ]
  for (let i = 0; i < reportDefs.length; i++) {
    const [name, type, status, format] = reportDefs[i]
    await prisma.report.create({
      data: {
        name,
        type,
        status,
        format,
        params: JSON.stringify({ range: '90d' }),
        createdById: pick(users).id,
        createdAt: daysAgo(intBetween(0, 45)),
      },
    })
  }
}

async function seedConfigsAndViews(users: SeededUser[]) {
  for (const u of users.slice(0, 3)) {
    await prisma.dashboardConfig.create({
      data: { userId: u.id, config: JSON.stringify(DEFAULT_DASHBOARD_CONFIG) },
    })
  }
  await prisma.savedView.create({
    data: {
      userId: users[0].id,
      name: 'Critical watchlist',
      page: 'members',
      state: JSON.stringify({ filters: { standing: 'watchlist', riskLevel: 'critical' }, sort: 'warnings', order: 'desc', pageSize: 25 }),
    },
  })
  await prisma.savedView.create({
    data: {
      userId: users[0].id,
      name: 'Open bans',
      page: 'cases',
      state: JSON.stringify({ filters: { type: 'ban', status: 'open' }, sort: 'createdAt', order: 'desc', pageSize: 10 }),
    },
  })
}

async function main() {
  console.log('Seeding database…')
  await reset()
  await seedRolesAndCatalog()
  const users = await seedUsers()
  const members = await seedMembers()
  const cases = await seedCases(members, users)
  await seedAutomod()
  await seedAppeals(cases, users)
  await seedMetrics()
  await seedBillingFor(users)
  await seedActivityAndAudit(users, members)
  await seedNotificationsAndReports(users)
  await seedConfigsAndViews(users)
  console.log('Seed complete.')
  console.log('Demo logins (password: password123):')
  console.log('  admin@aegisbot.gg    (Admin / Server Owner)')
  console.log('  manager@aegisbot.gg  (Moderator)')
  console.log('  viewer@aegisbot.gg   (Helper / read-only)')
}

main()
  .then(async () => {
    await prisma.$disconnect()
  })
  .catch(async (e) => {
    console.error(e)
    await prisma.$disconnect()
    process.exit(1)
  })
