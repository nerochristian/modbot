import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'

import { safeReturnPath } from '../src/lib/auth'
import { parseListQuery } from '../src/lib/list-query'
import { updateUserSchema } from '../src/lib/validation'
import {
  dashboardConfigPatchSchema,
  DEFAULT_DASHBOARD_CONFIG,
  DEFAULT_TABLE_COLUMNS,
  mergeConfig,
} from '../src/lib/dashboard-config'
import {
  automodDefinition,
  displayAutomodAction,
  normalizeAutomodRuleId,
  parseAutomodPattern,
  parseAutomodPolicy,
  serializeAutomodPattern,
} from '../src/lib/automod-contract'
import {
  buildReportArtifact,
  neutralizeSpreadsheetFormula,
  reportRowsToCsv,
} from '../src/lib/report-formatters'
import { isDiscordSnowflake, moduleDefinition, moduleEnabled } from '../src/lib/modules-contract'
import {
  legacyThresholdSnapshot,
  moderationAutopunishRulesFromSettings,
  parseModerationAutopunishRules,
} from '../src/lib/moderation-contract'
import { DEFAULT_ROLE_MATRIX } from '../src/lib/rbac'

test('safeReturnPath preserves local paths and rejects open-redirect forms', () => {
  assert.equal(safeReturnPath('/dashboard/cases?page=2#open'), '/dashboard/cases?page=2#open')
  assert.equal(safeReturnPath('https://attacker.example/steal'), '/servers')
  assert.equal(safeReturnPath('//attacker.example/steal'), '/servers')
  assert.equal(safeReturnPath('/\\attacker.example/steal'), '/servers')
  assert.equal(safeReturnPath('/dashboard\nLocation: https://attacker.example'), '/servers')
  assert.equal(safeReturnPath(null, '/dashboard'), '/dashboard')
})

test('dashboard access requires live Discord Administrator authority', () => {
  const root = path.resolve(import.meta.dirname, '..')
  const discord = readFileSync(path.join(root, 'src/lib/discord.ts'), 'utf8')
  const session = readFileSync(path.join(root, 'src/lib/session.ts'), 'utf8')
  const callback = readFileSync(path.join(root, 'src/app/api/auth/discord/callback/route.ts'), 'utf8')
  const nav = readFileSync(path.join(root, 'src/lib/nav.ts'), 'utf8')
  const userRoute = readFileSync(path.join(root, 'src/app/api/users/route.ts'), 'utf8')
  const overview = readFileSync(path.join(root, 'src/components/dashboard/overview-client.tsx'), 'utf8')

  assert.match(discord, /function hasAdministratorAccess/)
  assert.match(discord, /\(permissions & ADMINISTRATOR\) === ADMINISTRATOR/)
  assert.doesNotMatch(discord, /MANAGE_GUILD|isSystemOwner|discordGuildRole/)
  assert.match(discord, /role: 'admin',[\s\S]{0,100}source: 'discord'/)
  assert.match(discord, /where: \{ userId, source: 'invite' \},[\s\S]{0,80}status: 'revoked'/)
  assert.doesNotMatch(session, /systemAdmin && selectedGuildId/)
  assert.match(session, /membership\.role !== 'admin'/)
  assert.match(session, /membership\.source !== 'discord'/)
  assert.match(callback, /administrableGuilds\.length === 0/)
  assert.match(callback, /Discord Administrator permission is required/)
  assert.doesNotMatch(nav, /\/dashboard\/admin|section: 'admin'/)
  assert.doesNotMatch(userRoute, /export async function POST/)
  assert.match(userRoute, /role: 'admin',[\s\S]{0,80}source: 'discord',[\s\S]{0,80}status: 'active'/)
  assert.match(overview, /Workspace controls/)
  assert.equal(existsSync(path.join(root, 'src/app/dashboard/admin')), false)
  assert.equal(existsSync(path.join(root, 'src/app/api/admin')), false)
})

test('member directory uses Discord identity and real moderation records without standing', () => {
  const root = path.resolve(import.meta.dirname, '..')
  const membersRoute = readFileSync(path.join(root, 'src/app/api/members/route.ts'), 'utf8')
  const memberRoute = readFileSync(path.join(root, 'src/app/api/members/[id]/route.ts'), 'utf8')
  const membersClient = readFileSync(path.join(root, 'src/components/dashboard/members-client.tsx'), 'utf8')
  const avatar = readFileSync(path.join(root, 'src/components/ui/avatar.tsx'), 'utf8')
  const userMenu = readFileSync(path.join(root, 'src/components/dashboard/user-menu.tsx'), 'utf8')
  const casesClient = readFileSync(path.join(root, 'src/components/dashboard/cases-client.tsx'), 'utf8')
  const schema = readFileSync(path.join(root, 'prisma/schema.prisma'), 'utf8')
  const marketing = readFileSync(path.join(root, 'src/app/(marketing)/page.tsx'), 'utf8')

  assert.match(membersRoute, /discordMemberAvatarUrl\(guild\.id, member\)/)
  assert.match(memberRoute, /getBotGuildMemberRoles\(guild\.id\)/)
  assert.match(memberRoute, /FROM cases[\s\S]{0,160}guild_id = \$1::bigint AND user_id = \$2::bigint/)
  assert.match(membersClient, /function MemberCaseFile/)
  assert.match(membersClient, /\/dashboard\/cases\?member=\$\{member\.id\}&new=1&type=\$\{action\}/)
  assert.match(membersClient, /Past moderation records/)
  assert.match(avatar, /import Image from 'next\/image'/)
  assert.match(avatar, /src=\{src\}/)
  assert.match(userMenu, /src=\{user\.avatarUrl\}/)
  assert.match(casesClient, /searchParams\.get\('type'\)/)
  assert.ok(DEFAULT_TABLE_COLUMNS.members.includes('status'))
  assert.equal(DEFAULT_TABLE_COLUMNS.members.includes('standing'), false)
  assert.doesNotMatch(membersRoute, /\bstanding\b/i)
  assert.doesNotMatch(membersClient, /\bstanding\b/i)
  assert.doesNotMatch(schema, /\bstanding\b/i)
  assert.doesNotMatch(marketing, /\bstanding\b/i)
})

test('parseListQuery accepts only finite positive integers and caps page size', () => {
  const valid = parseListQuery(new URL('https://dashboard.test/api?page=4&pageSize=250'), {
    maxPageSize: 100,
  })
  assert.equal(valid.page, 4)
  assert.equal(valid.pageSize, 100)

  for (const value of ['0', '-2', '1.5', 'NaN', 'Infinity', '1e309', '']) {
    const parsed = parseListQuery(
      new URL(`https://dashboard.test/api?page=${encodeURIComponent(value)}&pageSize=${encodeURIComponent(value)}`),
    )
    assert.equal(parsed.page, 1, `page should reject ${JSON.stringify(value)}`)
    assert.equal(parsed.pageSize, 10, `pageSize should reject ${JSON.stringify(value)}`)
  }
})

test('dashboard config input is strict and nested preferences merge onto defaults', () => {
  assert.throws(() => dashboardConfigPatchSchema.parse({ theme: 'dark', unexpected: true }))
  assert.throws(() => dashboardConfigPatchSchema.parse({
    notifications: { security: { push: false, unexpected: true } },
  }))
  assert.throws(() => dashboardConfigPatchSchema.parse({
    defaultLandingPage: '//attacker.example',
  }))

  const patch = dashboardConfigPatchSchema.parse({
    theme: 'dark',
    tableColumns: { reports: ['name', 'status'] },
    notifications: { security: { push: false } },
  })
  const merged = mergeConfig(patch)

  assert.equal(merged.theme, 'dark')
  assert.deepEqual(merged.tableColumns.reports, ['name', 'status'])
  assert.deepEqual(merged.tableColumns.members, DEFAULT_TABLE_COLUMNS.members)
  assert.deepEqual(merged.notifications.security, {
    ...DEFAULT_DASHBOARD_CONFIG.notifications.security,
    push: false,
  })
  assert.deepEqual(merged.notifications.billing, DEFAULT_DASHBOARD_CONFIG.notifications.billing)
})

test('AutoMod aliases resolve to canonical rules and policies normalize actions', () => {
  assert.equal(normalizeAutomodRuleId(' Keywords '), 'badwords')
  assert.equal(normalizeAutomodRuleId('MENTION_SPAM'), 'mentions')
  assert.equal(normalizeAutomodRuleId('fast_message'), 'fast_messages')
  assert.equal(normalizeAutomodRuleId('phishing'), 'scams')
  assert.equal(normalizeAutomodRuleId('not-a-rule'), null)

  const timeout = parseAutomodPolicy({ action: 'mute', duration: 20, delete: false })
  assert.deepEqual(timeout, { action: 'timeout', delete: false, duration: 60 })
  assert.equal(displayAutomodAction(timeout), 'timeout')

  // Legacy stored {action:'delete'} still parses safely, but deletion is an
  // independent toggle — the displayed action is 'log', never a synthetic 'delete'.
  const deletePolicy = parseAutomodPolicy('delete')
  assert.deepEqual(deletePolicy, { action: 'log', delete: true })
  assert.equal(displayAutomodAction(deletePolicy), 'log')
  assert.deepEqual(parseAutomodPolicy('none'), { action: 'none', delete: false })
  assert.deepEqual(parseAutomodPolicy('unsupported'), { action: 'warn', delete: true })
})

test('workspace role updates cannot mutate a shared global identity', () => {
  assert.deepEqual(updateUserSchema.parse({ role: 'manager', status: 'active' }), {
    role: 'manager',
    status: 'active',
  })
  assert.throws(() => updateUserSchema.parse({ name: 'Cross-tenant rename' }))
  assert.throws(() => updateUserSchema.parse({ title: 'Cross-tenant title' }))
})

test('AutoMod patterns parse canonical list and bounded integer values', () => {
  const blockedWords = automodDefinition('blocked_words')
  const spam = automodDefinition('spam')
  assert.ok(blockedWords)
  assert.ok(spam)

  const words = parseAutomodPattern(blockedWords, ' scam, phishing, , @everyone ')
  assert.deepEqual(words, ['scam', 'phishing', '@everyone'])
  assert.equal(serializeAutomodPattern(blockedWords, words), 'scam, phishing, @everyone')

  assert.equal(parseAutomodPattern(spam, '7'), 7)
  assert.throws(() => parseAutomodPattern(spam, '1'))
  assert.throws(() => parseAutomodPattern(spam, '2.5'))
  assert.throws(() => parseAutomodPattern(spam, '9007199254740992'))
})

test('CSV output neutralizes spreadsheet formulas without changing ordinary values', () => {
  const dangerous = ['=2+2', '+SUM(A1:A2)', '-1+2', '@cmd', ' \t=hidden']
  for (const value of dangerous) {
    assert.equal(neutralizeSpreadsheetFormula(value), `'${value}`)
  }
  assert.equal(neutralizeSpreadsheetFormula('safe value'), 'safe value')
  assert.equal(neutralizeSpreadsheetFormula(42), 42)

  const csv = reportRowsToCsv([
    { member: '=2+2', note: 'safe value' },
    { member: 'ordinary', note: '+SUM(A1:A2)' },
  ])
  assert.equal(csv, "member,note\r\n'=2+2,safe value\r\nordinary,'+SUM(A1:A2)\r\n")
})

test('report artifacts expose the expected signatures, extensions, and content types', async () => {
  const rows = [{ member: '=2+2', action: 'warn', count: 3 }]

  const csv = await buildReportArtifact('csv', 'Moderation report', rows)
  assert.equal(csv.extension, 'csv')
  assert.equal(csv.contentType, 'text/csv; charset=utf-8')
  assert.match(csv.body.toString('utf8'), /^member,action,count\r\n'=2\+2,warn,3\r\n$/)

  const json = await buildReportArtifact('json', 'Moderation report', rows)
  assert.equal(json.extension, 'json')
  assert.equal(json.contentType, 'application/json; charset=utf-8')
  assert.deepEqual(JSON.parse(json.body.toString('utf8')), rows)

  const pdf = await buildReportArtifact('pdf', 'Moderation report', rows)
  assert.equal(pdf.extension, 'pdf')
  assert.equal(pdf.contentType, 'application/pdf')
  assert.equal(pdf.body.subarray(0, 5).toString('ascii'), '%PDF-')

  const xlsx = await buildReportArtifact('xlsx', 'Moderation report', rows)
  assert.equal(xlsx.extension, 'xlsx')
  assert.equal(
    xlsx.contentType,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  )
  assert.deepEqual([...xlsx.body.subarray(0, 4)], [0x50, 0x4b, 0x03, 0x04])
})

test('module defaults and configured keyless states match bot runtime behavior', () => {
  const automod = moduleDefinition('automod')
  const moderation = moduleDefinition('moderation')
  const verification = moduleDefinition('verification')
  const logging = moduleDefinition('logging')
  const welcome = moduleDefinition('welcome')
  const autoroles = moduleDefinition('autoroles')
  assert.ok(automod && moderation && verification && logging && welcome && autoroles)

  assert.equal(moduleEnabled({}, automod), true)
  assert.equal(moduleEnabled({}, moderation), true)
  assert.equal(moduleEnabled({}, verification), false)
  assert.equal(moduleEnabled({}, logging), true)
  assert.equal(moduleEnabled({}, welcome), false)
  assert.equal(moduleEnabled({ welcome_channel: '123456789012345' }, welcome), true)
  assert.equal(moduleEnabled({}, autoroles), false)
  assert.equal(moduleEnabled({ auto_role: '123456789012345' }, autoroles), true)
  assert.equal(moduleEnabled({ auto_role: '123456789012345', autoroles_enabled: false }, autoroles), false)
  assert.equal(moduleEnabled({ automod_enabled: false }, automod), false)
  assert.equal(moduleEnabled({ modules: { automod: { enabled: false } } }, automod), false)
  assert.equal(moduleDefinition('afk_detection'), null)
  assert.equal(moduleDefinition('warn_thresholds'), null)
  assert.equal(moderation.special, 'moderation')
  assert.ok(moderation.fields.some((field) => field.key === 'moderation_autopunish_rules'))
  assert.equal(isDiscordSnowflake('123456789012345678'), true)
  assert.equal(isDiscordSnowflake(123456789012345678), false)
  assert.equal(isDiscordSnowflake('9223372036854775808'), false)
  assert.equal(isDiscordSnowflake('12345678901234'), false)
})

test('every configurable module declares a purpose-built operational contract', () => {
  const expected = {
    aimod: 'aimod',
    antiraid: 'antiraid',
    verification: 'verification',
    whitelist: 'whitelist',
    tickets: 'tickets',
    logging: 'logging',
    welcome: 'welcome_card',
    autoroles: 'autoroles',
  } as const
  for (const [id, special] of Object.entries(expected)) {
    const definition = moduleDefinition(id)
    assert.ok(definition, `${id} must exist`)
    assert.equal(definition.special, special)
    assert.ok(definition.fields.length > 0, `${id} must expose runtime-backed settings`)
  }

  const aimod = moduleDefinition('aimod')!
  const confirmActions = aimod.fields.find((field) => field.key === 'aimod_confirm_actions')
  assert.equal(confirmActions?.type, 'multiSelect')
  assert.ok(confirmActions?.options?.some((option) => option.value === 'ban_member'))

  const antiraid = moduleDefinition('antiraid')!
  assert.equal(antiraid.fields.find((field) => field.key === 'antiraid_join_threshold')?.min, 3)
  assert.deepEqual(antiraid.fields.find((field) => field.key === 'lockdown_channels')?.channelTypes, [0, 5])

  const verification = moduleDefinition('verification')!
  assert.deepEqual(verification.fields.find((field) => field.key === 'waiting_verify_voice_channel')?.channelTypes, [2, 13])

  const tickets = moduleDefinition('tickets')!
  assert.deepEqual(tickets.fields.find((field) => field.key === 'ticket_category')?.channelTypes, [4])

  const logging = moduleDefinition('logging')!
  assert.deepEqual(logging.fields.map((field) => field.key), [
    'audit_log_channel',
    'message_log_channel',
    'voice_log_channel',
    'automod_log_channel',
    'report_log_channel',
    'ticket_log_channel',
  ])
})

test('read-only workspace roles cannot mutate module configuration', () => {
  assert.equal(DEFAULT_ROLE_MATRIX.viewer.includes('settings.read'), true)
  assert.equal(DEFAULT_ROLE_MATRIX.viewer.includes('config.write'), false)
  assert.equal(DEFAULT_ROLE_MATRIX.manager.includes('config.write'), true)
  assert.equal(DEFAULT_ROLE_MATRIX.admin.includes('config.write'), true)
})

test('moderation autopunish rules are strict, sorted, and legacy compatible', () => {
  assert.deepEqual(parseModerationAutopunishRules([
    { warnings: 7, action: 'ban', durationMinutes: null },
    { warnings: 3, action: 'mute', durationMinutes: 30 },
    { warnings: 5, action: 'kick', durationMinutes: null },
  ]), [
    { warnings: 3, action: 'timeout', durationMinutes: 30 },
    { warnings: 5, action: 'kick', durationMinutes: null },
    { warnings: 7, action: 'ban', durationMinutes: null },
  ])
  assert.throws(() => parseModerationAutopunishRules([
    { warnings: 3, action: 'timeout', durationMinutes: 0 },
  ]), /duration/)
  assert.throws(() => parseModerationAutopunishRules([
    { warnings: 3, action: 'timeout', durationMinutes: 30 },
    { warnings: 3, action: 'kick', durationMinutes: null },
  ]), /unique/)
  assert.throws(() => parseModerationAutopunishRules([
    { warnings: 3, action: 'ban', durationMinutes: null },
    { warnings: 5, action: 'kick', durationMinutes: null },
  ]), /less severe/)

  const legacy = moderationAutopunishRulesFromSettings({
    warn_threshold_mute: 2,
    warn_mute_duration: 1800,
    warn_threshold_kick: 4,
    warn_threshold_ban: 6,
  })
  assert.deepEqual(legacy, [
    { warnings: 2, action: 'timeout', durationMinutes: 30 },
    { warnings: 4, action: 'kick', durationMinutes: null },
    { warnings: 6, action: 'ban', durationMinutes: null },
  ])
  assert.deepEqual(legacyThresholdSnapshot(legacy), {
    warn_thresholds_enabled: true,
    warn_threshold_mute: 2,
    warn_mute_duration: 1800,
    warn_threshold_kick: 4,
    warn_threshold_ban: 6,
  })
  assert.deepEqual(moderationAutopunishRulesFromSettings({ moderation_autopunish_rules: [] }), [])
  assert.deepEqual(moderationAutopunishRulesFromSettings({
    warn_thresholds_enabled: false,
    warn_threshold_mute: 3,
    warn_threshold_kick: 5,
    warn_threshold_ban: 7,
  }), [])

  const logging = moduleDefinition('logging')
  assert.ok(logging)
  assert.equal(logging.fields.some((field) => field.key === 'log_channel_mod'), false)
})

test('production SQL and standalone deployment match the bot runtime contracts', () => {
  const repo = path.resolve(process.cwd(), '..')
  const moderation = readFileSync(path.join(process.cwd(), 'src/lib/moderation-service.ts'), 'utf8')
  const appealPortal = readFileSync(path.join(process.cwd(), 'src/lib/appeal-portal-service.ts'), 'utf8')
  const appeals = readFileSync(path.join(process.cwd(), 'src/lib/appeals-service.ts'), 'utf8')
  const cases = readFileSync(path.join(process.cwd(), 'src/app/api/cases/route.ts'), 'utf8')
  const botSettings = readFileSync(path.join(process.cwd(), 'src/lib/bot-settings.ts'), 'utf8')
  const botDb = readFileSync(path.join(process.cwd(), 'src/lib/bot-db.ts'), 'utf8')
  const memberReports = readFileSync(path.join(process.cwd(), 'src/app/api/member-reports/route.ts'), 'utf8')
  const memberReport = readFileSync(path.join(process.cwd(), 'src/app/api/member-reports/[id]/route.ts'), 'utf8')
  const discord = readFileSync(path.join(process.cwd(), 'src/lib/discord.ts'), 'utf8')
  const guildResources = readFileSync(path.join(process.cwd(), 'src/app/api/guilds/resources/route.ts'), 'utf8')
  const modulesService = readFileSync(path.join(process.cwd(), 'src/lib/modules-service.ts'), 'utf8')
  const automodService = readFileSync(path.join(process.cwd(), 'src/lib/automod-service.ts'), 'utf8')
  const verificationSetup = readFileSync(path.join(process.cwd(), 'src/lib/verification-setup-service.ts'), 'utf8')
  const automodRoute = readFileSync(path.join(process.cwd(), 'src/app/api/automod/route.ts'), 'utf8')
  const useApi = readFileSync(path.join(process.cwd(), 'src/lib/use-api.ts'), 'utf8')
  const modulesClient = readFileSync(path.join(process.cwd(), 'src/components/dashboard/modules-client.tsx'), 'utf8')
  const serverGrid = readFileSync(path.join(process.cwd(), 'src/components/servers/server-grid.tsx'), 'utf8')
  const toast = readFileSync(path.join(process.cwd(), 'src/components/ui/toast.tsx'), 'utf8')
  const deploy = readFileSync(path.join(repo, 'scripts/vps_deploy.sh'), 'utf8')
  const ecosystem = readFileSync(path.join(repo, 'ecosystem.config.cjs'), 'utf8')
  const dockerfile = readFileSync(path.join(repo, 'Dockerfile'), 'utf8')

  assert.doesNotMatch(moderation, /\b(?:TRUE|FALSE)\b/)
  assert.doesNotMatch(appeals, /active\s*=\s*(?:TRUE|FALSE)/)
  assert.doesNotMatch(cases, /active\s*=\s*(?:TRUE|FALSE)/)
  assert.match(deploy, /cp -a \.next\/static \.next\/standalone\/\.next\//)
  assert.match(deploy, /cp -a public \.next\/standalone\//)
  assert.match(deploy, /rm -f \.next\/standalone\/\.env/)
  assert.doesNotMatch(ecosystem, /dashboard\/node_modules\/dotenv/)
  assert.match(dockerfile, /npx prisma migrate deploy/)
  assert.match(botSettings, /jsonb_typeof\(entry\.value\) = 'number'/)
  assert.match(botSettings, /to_jsonb\(entry\.value #>> '\{\}'\)/)
  assert.match(botSettings, /'verification_panel_message_id'/)
  assert.match(botDb, /pg_advisory_lock\(hashtextextended/)
  assert.match(botDb, /pg_advisory_unlock\(hashtextextended/)
  assert.doesNotMatch(memberReports, /resolved = (?:TRUE|FALSE)/)
  assert.match(memberReports, /resolved = 0/)
  assert.match(memberReports, /resolved = 1/)
  assert.match(memberReport, /resolved = \$3::bigint/)
  assert.match(memberReport, /CASE WHEN \$3::bigint = 1/)
  assert.match(discord, /TRANSIENT_AUTHORITY_GRACE_MS = 2 \* 60_000/)
  assert.match(discord, /error instanceof DiscordTemporaryError/)
  assert.match(discord, /verifiedAt: \{ gte:/)
  assert.match(discord, /\/guilds\/\$\{guildId\}\/roles/)
  assert.match(discord, /\/guilds\/\$\{guildId\}\/channels/)
  assert.match(discord, /channel\.type === 2/)
  assert.match(discord, /channel\.type === 4/)
  assert.match(discord, /channel\.type === 13/)
  assert.match(discord, /\/users\/@me\/channels/)
  const appealDelivery = moderation.indexOf('const appeal = shouldPrepareDm')
  const moderationExecution = moderation.indexOf('await executeModerationAction', appealDelivery)
  assert.ok(appealDelivery >= 0 && moderationExecution > appealDelivery)
  assert.doesNotMatch(cases, /issueAppealToken/)
  assert.match(appealPortal, /type: 17/)
  assert.match(appealPortal, /flags: 1 << 15/)
  assert.match(appealPortal, /Available again <t:/)
  assert.match(appealPortal, /Reason :/)
  assert.match(appealPortal, /type: 14/)
  assert.match(appealPortal, /statusEmoji\('id'\)/)
  assert.match(appealPortal, /statusEmoji\(emojiKind\)/)
  assert.match(appealPortal, /`CASE-/)
  assert.doesNotMatch(appealPortal, /footer: \{ text: `CASE-/)
  assert.match(discord, /preserveBanMessages === false \? 86_400 : 0/)
  assert.match(guildResources, /requireUser\('settings\.read'\)/)
  assert.match(guildResources, /guard\.selectedGuildId!/)
  assert.match(modulesService, /parseModerationAutopunishRules/)
  assert.match(modulesService, /legacyThresholdSnapshot/)
  assert.match(modulesService, /LEGACY_MODERATION_ROLE_KEYS/)
  assert.match(modulesService, /changes\.log_channel_mod = changes\.mod_log_channel/)
  assert.match(modulesService, /getBotGuildResources\(guildId\)/)
  assert.match(modulesService, /SETTING_ALIASES/)
  assert.match(automodService, /AutoMod settings were not persisted/)
  assert.match(verificationSetup, /flags: IS_COMPONENTS_V2/)
  assert.match(verificationSetup, /queueExistingMembers/)
  assert.match(verificationSetup, /assertPersistedSetup/)
  assert.match(verificationSetup, /withBotAdvisoryLock/)
  assert.match(verificationSetup, /removeDuplicateVerificationPanels/)
  assert.match(verificationSetup, /custom_id: 'verification:start'/)
  assert.match(verificationSetup, /setOverwrite\(verifyChannel\.id, verified\.id, 0, BigInt\(0\), VIEW_CHANNEL\)/)
  assert.match(verificationSetup, /existingMembersAssigned: memberQueue\.assigned/)
  assert.match(verificationSetup, /autoroles_enabled: false/)
  assert.match(verificationSetup, /assertVerificationMethodReady/)
  assert.match(modulesService, /def\.id === 'verification'\) changes\.autoroles_enabled = false/)
  assert.match(modulesService, /def\.id === 'autoroles'\) changes\.verification_enabled = false/)
  assert.match(modulesClient, /JSON\.stringify\(\{ method: verificationMethod \}\)/)
  assert.match(modulesClient, /Website checkpoint/)
  assert.match(modulesClient, /Discord CAPTCHA/)
  assert.match(automodRoute, /private, no-store, no-cache, must-revalidate/)
  assert.match(useApi, /cache: 'no-store'/)
  assert.match(modulesService, /case 'multiSelect'/)
  assert.match(modulesClient, /function OperationalModuleSheet/)
  assert.match(modulesClient, /Event routing matrix/)
  assert.match(modulesClient, /Voice gate/)
  assert.match(modulesClient, /function OperationalField/)
  assert.match(serverGrid, /window\.location\.assign\('\/dashboard\/modules'\)/)
  assert.doesNotMatch(serverGrid, /router\.push\('\/dashboard'\)[\s\S]{0,80}router\.refresh\(\)/)
  assert.match(toast, /createClientId\('toast'\)/)
})

test('public verification uses an explicit Cloudflare Turnstile flow', () => {
  const verificationPage = readFileSync(path.join(process.cwd(), 'src/app/verify/[token]/page.tsx'), 'utf8')
  const verificationForm = readFileSync(path.join(process.cwd(), 'src/components/verification/verification-form.tsx'), 'utf8')
  const verificationRoute = readFileSync(path.join(process.cwd(), 'src/app/api/verify/[token]/route.ts'), 'utf8')
  assert.match(verificationPage, /Prove you&amp;apos;re human|Prove you&apos;re human/)
  assert.match(verificationPage, /docket-glyph\.png/)
  assert.match(verificationPage, /items-center justify-center/)
  assert.match(verificationPage, /TURNSTILE_SITE_KEY/)
  assert.match(verificationForm, /turnstile\/v0\/api\.js\?render=explicit/)
  assert.match(verificationForm, /window\.turnstile/)
  assert.match(verificationForm, /api\.render\(container/)
  assert.match(verificationForm, /action: TURNSTILE_ACTION/)
  assert.match(verificationForm, /appearance: 'interaction-only'/)
  assert.match(verificationForm, /Cloudflare Turnstile human check/)
  assert.match(verificationForm, /Cloudflare(?:&apos;|')s\{' '\}/)
  assert.match(verificationForm, /cloudflare\.com\/privacypolicy/)
  assert.doesNotMatch(verificationForm, /grecaptcha|RECAPTCHA/)
  assert.doesNotMatch(verificationForm, /verify-diag/)
  assert.match(verificationRoute, /turnstile\/v0\/siteverify/)
  assert.match(verificationRoute, /MAX_TURNSTILE_TOKEN_LENGTH = 2_048/)
  assert.match(verificationRoute, /MAX_REQUEST_BYTES = 16_384/)
  assert.match(verificationRoute, /idempotency_key/)
  assert.match(verificationRoute, /AbortSignal\.timeout\(8_000\)/)
  assert.match(verificationRoute, /turnstile\.action === TURNSTILE_ACTION/)
  assert.match(verificationRoute, /turnstile\.hostname === expectedHostname/)
  assert.doesNotMatch(verificationRoute, /recaptcha|RECAPTCHA/)
  assert.doesNotMatch(verificationRoute, /verify-diag/)
})
