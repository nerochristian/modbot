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
const weighted = <T>(items: [T, number][]): T => {
  const total = items.reduce((s, [, w]) => s + w, 0)
  let r = rng() * total
  for (const [item, w] of items) {
    if ((r -= w) <= 0) return item
  }
  return items[0][0]
}

const FIRST = ['Ava', 'Marcus', 'Priya', 'Liam', 'Sofia', 'Noah', 'Emma', 'Kai', 'Zara', 'Diego', 'Yuki', 'Omar', 'Lena', 'Theo', 'Nina', 'Ravi', 'Clara', 'Mateo', 'Ivy', 'Hugo', 'Aria', 'Felix', 'Maya', 'Leon', 'Ruby', 'Elias', 'Nora', 'Amir', 'Isla', 'Oscar']
const LAST = ['Thompson', 'Lee', 'Nair', 'Walker', 'Garcia', 'Chen', 'Novak', 'Okafor', 'Rossi', 'Haddad', 'Kim', 'Silva', 'Meyer', 'Patel', 'Dubois', 'Ivanov', 'Costa', 'Nguyen', 'Schmidt', 'Ahmed', 'Reyes', 'Berg', 'Fischer', 'Moreau', 'Santos', 'Wagner', 'Romano', 'Larsen', 'Yamada', 'Flores']
const COMPANIES = ['Acme Corp', 'Globex', 'Initech', 'Umbrella', 'Hooli', 'Stark Industries', 'Wayne Enterprises', 'Cyberdyne', 'Soylent', 'Wonka Labs', 'Massive Dynamic', 'Pied Piper', 'Aperture', 'Tyrell Corp', 'Nakatomi', 'Vandelay', 'Gekko & Co', 'Duff', 'Prestige Worldwide', 'Bluth Company']
const COUNTRIES = ['US', 'GB', 'DE', 'FR', 'CA', 'AU', 'IN', 'BR', 'JP', 'NL', 'SE', 'ES']
const AVATAR_COLORS = ['#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#f43f5e', '#8b5cf6', '#ec4899', '#14b8a6']
const PLAN_MRR: Record<string, number> = { free: 0, starter: 2900, pro: 9900, enterprise: 49900 }

function fullName() {
  return `${pick(FIRST)} ${pick(LAST)}`
}
function emailFor(name: string, domain: string, i: number) {
  return `${name.toLowerCase().replace(/[^a-z]+/g, '.')}.${i}@${domain}`
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
  await prisma.customer.deleteMany()
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
    { key: 'analytics.v2', name: 'Analytics v2', description: 'New analytics engine with cohort breakdowns.', enabled: true, rolloutRole: 'all' },
    { key: 'export.pdf', name: 'PDF export', description: 'Allow exporting reports as PDF.', enabled: true, rolloutRole: 'all' },
    { key: 'billing.invoices', name: 'Self-serve invoices', description: 'Customers can download invoices.', enabled: true, rolloutRole: 'all' },
    { key: 'ai.insights', name: 'AI insights', description: 'Automated anomaly detection on metrics.', enabled: false, rolloutRole: 'admin' },
    { key: 'beta.layouts', name: 'Beta layouts', description: 'Experimental dashboard layouts.', enabled: false, rolloutRole: 'manager' },
    { key: 'sso.saml', name: 'SAML SSO', description: 'Enterprise single sign-on.', enabled: false, rolloutRole: 'admin' },
  ]
  for (const t of toggles) await prisma.featureToggle.create({ data: t })

  const settings: Record<string, unknown> = {
    'app.name': 'Nebula',
    'app.supportEmail': 'support@nebula.dev',
    'app.signupsEnabled': true,
    'app.defaultRole': 'viewer',
    'app.maintenanceMode': false,
    'security.enforce2fa': false,
    'security.sessionTtlDays': 7,
    'branding.primaryColor': '#6366f1',
  }
  for (const [key, value] of Object.entries(settings)) {
    await prisma.appSetting.create({ data: { key, value: JSON.stringify(value) } })
  }
}

type SeededUser = { id: string; name: string; role: string }

async function seedUsers(): Promise<SeededUser[]> {
  const passwordHash = await hashPassword('password123')
  const core = [
    { email: 'admin@nebula.dev', name: 'Ava Thompson', role: 'admin', title: 'Founder & CEO' },
    { email: 'manager@nebula.dev', name: 'Marcus Lee', role: 'manager', title: 'Head of Growth' },
    { email: 'viewer@nebula.dev', name: 'Priya Nair', role: 'viewer', title: 'Data Analyst' },
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

  // Additional team members.
  for (let i = 0; i < 11; i++) {
    const name = fullName()
    const role = weighted([['viewer', 5], ['manager', 3], ['admin', 1]])
    const status = weighted([['active', 8], ['invited', 2], ['suspended', 1]])
    const u = await prisma.user.create({
      data: {
        email: emailFor(name, 'nebula.dev', i),
        name,
        passwordHash,
        role,
        status,
        title: pick(['Engineer', 'Designer', 'Support Lead', 'Account Manager', 'Marketer', 'Ops']),
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

async function seedCustomers() {
  const rows = []
  for (let i = 0; i < 160; i++) {
    const name = fullName()
    const plan = weighted([['free', 4], ['starter', 3], ['pro', 2], ['enterprise', 1]])
    const status = weighted([['active', 7], ['trialing', 2], ['past_due', 1], ['churned', 2]])
    const baseMrr = PLAN_MRR[plan]
    rows.push({
      name,
      email: emailFor(name, pick(['acme.co', 'globex.com', 'initech.io', 'hooli.com', 'stark.io']), i),
      company: pick(COMPANIES),
      plan,
      status,
      country: pick(COUNTRIES),
      mrr: status === 'churned' || plan === 'free' ? 0 : Math.round(baseMrr * between(0.9, 1.2)),
      avatarColor: pick(AVATAR_COLORS),
      createdAt: daysAgo(intBetween(1, 365)),
      lastActiveAt: daysAgo(intBetween(0, status === 'churned' ? 120 : 14)),
    })
  }
  await prisma.customer.createMany({ data: rows })
}

async function seedMetrics() {
  const days = 365
  const metrics: { name: string; base: number; growth: number; noise: number; min?: number; max?: number }[] = [
    { name: 'revenue', base: 42000, growth: 0.0028, noise: 0.06 },
    { name: 'mrr', base: 128000, growth: 0.0022, noise: 0.03 },
    { name: 'users', base: 8600, growth: 0.0035, noise: 0.02 },
    { name: 'active', base: 5200, growth: 0.003, noise: 0.05 },
    { name: 'sessions', base: 18500, growth: 0.0025, noise: 0.09 },
    { name: 'conversion', base: 3.4, growth: 0.0006, noise: 0.08, min: 1.5, max: 7 },
    { name: 'retention', base: 88, growth: 0.0002, noise: 0.02, min: 70, max: 98 },
    { name: 'churn', base: 3.1, growth: -0.0004, noise: 0.06, min: 0.8, max: 6 },
  ]
  const rows: { metric: string; date: Date; value: number }[] = []
  for (const m of metrics) {
    for (let d = days; d >= 0; d--) {
      const t = days - d
      const weekly = 1 + 0.05 * Math.sin((t / 7) * Math.PI * 2)
      const trend = m.base * Math.pow(1 + m.growth, t)
      let value = trend * weekly * (1 + (rng() - 0.5) * 2 * m.noise)
      if (m.min !== undefined) value = Math.max(m.min, value)
      if (m.max !== undefined) value = Math.min(m.max, value)
      value = m.name === 'conversion' || m.name === 'retention' || m.name === 'churn'
        ? Math.round(value * 10) / 10
        : Math.round(value)
      rows.push({ metric: m.name, date: daysAgo(d), value })
    }
  }
  // createMany in chunks to stay well within SQLite variable limits.
  for (let i = 0; i < rows.length; i += 500) {
    await prisma.metricPoint.createMany({ data: rows.slice(i, i + 500) })
  }
}

async function seedBillingFor(users: SeededUser[]) {
  const admin = users[0]
  await prisma.subscription.create({
    data: {
      userId: admin.id,
      plan: 'enterprise',
      status: 'active',
      seats: 25,
      interval: 'month',
      amount: 49900,
      currentPeriodEnd: daysAgo(-18),
    },
  })
  await prisma.subscription.create({
    data: {
      userId: users[1].id,
      plan: 'pro',
      status: 'active',
      seats: 5,
      interval: 'month',
      amount: 9900,
      currentPeriodEnd: daysAgo(-11),
    },
  })
  // 12 months of invoices for the admin account.
  for (let m = 12; m >= 1; m--) {
    await prisma.invoice.create({
      data: {
        userId: admin.id,
        number: `INV-2026-${String(13 - m).padStart(4, '0')}`,
        amount: 49900,
        status: m === 1 ? 'open' : 'paid',
        issuedAt: daysAgo(m * 30),
        periodStart: daysAgo(m * 30),
        periodEnd: daysAgo((m - 1) * 30),
      },
    })
  }
}

async function seedActivityAndAudit(users: SeededUser[]) {
  const actions = [
    ['created_report', 'Q3 Revenue report'],
    ['invited_user', 'new teammate'],
    ['updated_settings', 'notification preferences'],
    ['exported_data', 'customers.csv'],
    ['changed_role', 'Marcus Lee → manager'],
    ['closed_ticket', '#4821'],
    ['upgraded_plan', 'Acme Corp → enterprise'],
    ['archived_customer', 'Globex'],
    ['saved_view', 'Churned customers'],
    ['toggled_feature', 'AI insights'],
  ]
  for (let i = 0; i < 60; i++) {
    const u = pick(users)
    const [action, target] = pick(actions)
    await prisma.activityLog.create({
      data: {
        userId: u.id,
        actorName: u.name,
        action,
        target,
        metadata: JSON.stringify({ ip: `192.168.${intBetween(0, 255)}.${intBetween(0, 255)}` }),
        createdAt: daysAgo(intBetween(0, 30)),
      },
    })
  }

  const auditActions = [
    ['user.role.update', 'User'],
    ['feature.toggle', 'FeatureToggle'],
    ['setting.update', 'AppSetting'],
    ['user.suspend', 'User'],
    ['permission.update', 'RolePermission'],
    ['widget.disable', 'Widget'],
  ]
  const admins = users.filter((u) => u.role === 'admin')
  for (let i = 0; i < 40; i++) {
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
        metadata: JSON.stringify({ before: 'viewer', after: 'manager' }),
        createdAt: daysAgo(intBetween(0, 60)),
      },
    })
  }
}

async function seedNotificationsAndReports(users: SeededUser[]) {
  const admin = users[0]
  const notes = [
    { type: 'billing', level: 'warning', title: 'Invoice due soon', body: 'Invoice INV-2026-0012 is due in 3 days.', href: '/dashboard/billing' },
    { type: 'security', level: 'error', title: 'New sign-in detected', body: 'A new device signed in from London, UK.', href: '/dashboard/settings/security' },
    { type: 'system', level: 'info', title: 'Scheduled maintenance', body: 'Planned maintenance this Sunday 02:00 UTC.', href: null },
    { type: 'report', level: 'success', title: 'Report ready', body: 'Your "Q3 Revenue" report finished generating.', href: '/dashboard/reports' },
    { type: 'mention', level: 'info', title: 'You were mentioned', body: 'Marcus mentioned you in Churn analysis.', href: '/dashboard/activity' },
    { type: 'billing', level: 'success', title: 'Payment received', body: 'We received your payment of $499.00.', href: '/dashboard/billing' },
    { type: 'system', level: 'info', title: 'New feature: AI insights', body: 'Anomaly detection is now available in analytics.', href: '/dashboard/analytics' },
    { type: 'security', level: 'warning', title: 'Enable 2FA', body: 'Protect your account with two-factor authentication.', href: '/dashboard/settings/security' },
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
    ['Q3 Revenue Breakdown', 'revenue', 'ready', 'pdf'],
    ['Monthly Active Users', 'users', 'ready', 'csv'],
    ['Cohort Retention 2026', 'retention', 'ready', 'xlsx'],
    ['Weekly Activity Digest', 'activity', 'scheduled', 'csv'],
    ['Enterprise Accounts', 'custom', 'ready', 'json'],
    ['Churn Deep Dive', 'users', 'generating', 'pdf'],
    ['Conversion Funnel', 'custom', 'ready', 'csv'],
    ['Annual Revenue Summary', 'revenue', 'ready', 'pdf'],
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
      name: 'Churned enterprise',
      page: 'customers',
      state: JSON.stringify({ filters: { status: 'churned', plan: 'enterprise' }, sort: 'mrr', order: 'desc', pageSize: 25 }),
    },
  })
  await prisma.savedView.create({
    data: {
      userId: users[0].id,
      name: 'Active trials',
      page: 'customers',
      state: JSON.stringify({ filters: { status: 'trialing' }, sort: 'createdAt', order: 'desc', pageSize: 10 }),
    },
  })
}

async function main() {
  console.log('Seeding database…')
  await reset()
  await seedRolesAndCatalog()
  const users = await seedUsers()
  await seedCustomers()
  await seedMetrics()
  await seedBillingFor(users)
  await seedActivityAndAudit(users)
  await seedNotificationsAndReports(users)
  await seedConfigsAndViews(users)
  console.log('Seed complete.')
  console.log('Demo logins (password: password123):')
  console.log('  admin@nebula.dev    (Admin)')
  console.log('  manager@nebula.dev  (Manager)')
  console.log('  viewer@nebula.dev   (Viewer)')
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
