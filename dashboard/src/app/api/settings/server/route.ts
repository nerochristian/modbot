import { apiError, handleError, ok, requireMutation, requireUser } from '@/lib/api'
import { recordGuildAudit } from '@/lib/bot-audit'
import { getBotGuildSettings, patchBotGuildSettings } from '@/lib/bot-settings'

type ServerSettings = {
  prefix: string
  deleteCommandMessages: boolean
  // Warning escalation
  warnEnabled: boolean
  warnMuteAt: number
  warnKickAt: number
  warnBanAt: number
  warnMuteDuration: number
  // Moderation behavior
  dmUsers: boolean
  respondWithReason: boolean
  preserveBanMessages: boolean
  useTimeouts: boolean
}

const DEFAULT_PREFIX = ','

function readBool(raw: unknown, fallback: boolean): boolean {
  if (typeof raw === 'boolean') return raw
  if (typeof raw === 'number' && (raw === 0 || raw === 1)) return raw === 1
  if (typeof raw === 'string') {
    const v = raw.trim().toLowerCase()
    if (['true', '1', 'yes', 'on', 'enabled'].includes(v)) return true
    if (['false', '0', 'no', 'off', 'disabled'].includes(v)) return false
  }
  return fallback
}

function readInt(raw: unknown, fallback: number, min: number, max: number): number {
  if (typeof raw === 'number' && Number.isFinite(raw)) {
    const v = Math.floor(raw)
    return v < min ? min : v > max ? max : v
  }
  if (typeof raw === 'string') {
    const n = parseInt(raw.trim(), 10)
    if (!Number.isNaN(n)) return readInt(n, fallback, min, max)
  }
  return fallback
}

function extractServerSettings(settings: Record<string, unknown>): ServerSettings {
  const rawPrefix = settings['prefix']
  const prefix =
    typeof rawPrefix === 'string' && rawPrefix.length > 0
      ? rawPrefix
      : typeof rawPrefix === 'number' || typeof rawPrefix === 'boolean'
        ? String(rawPrefix)
        : DEFAULT_PREFIX

  const legacy = readBool(settings['moderation_delete_command_messages'], false)
  const deleteCommandMessages = readBool(settings['moderation_delete_commands'], legacy)

  return {
    prefix,
    deleteCommandMessages,
    warnEnabled: readBool(settings['warn_thresholds_enabled'], true),
    warnMuteAt: readInt(settings['warn_threshold_mute'], 3, 1, 20),
    warnKickAt: readInt(settings['warn_threshold_kick'], 5, 1, 20),
    warnBanAt: readInt(settings['warn_threshold_ban'], 7, 1, 20),
    warnMuteDuration: readInt(settings['warn_mute_duration'], 3600, 60, 2592000),
    dmUsers: readBool(settings['moderation_dm_users'], true),
    respondWithReason: readBool(settings['moderation_respond_with_reason'], true),
    preserveBanMessages: readBool(settings['moderation_preserve_ban_messages'], true),
    useTimeouts: readBool(settings['moderation_use_timeouts'], true),
  }
}

function validatePrefix(value: unknown): string | null {
  if (typeof value !== 'string') return 'Prefix must be text.'
  const trimmed = value.trim()
  if (trimmed.length === 0) return 'Prefix cannot be empty.'
  if (trimmed.length > 5) return 'Prefix must be 5 characters or fewer.'
  if (/\s/.test(trimmed)) return 'Prefix cannot contain spaces.'
  if (/^<[@#&!]/.test(trimmed)) return 'Prefix cannot be a Discord mention or emoji format.'
  return null
}

export async function GET() {
  try {
    const guard = await requireUser('settings.read')
    if (guard instanceof Response) return guard
    const settings = await getBotGuildSettings(guard.selectedGuildId!)
    return ok({ settings: extractServerSettings(settings) })
  } catch (error) {
    return handleError(error)
  }
}

export async function PATCH(request: Request) {
  try {
    const guard = await requireMutation(request, 'config.write')
    if (guard instanceof Response) return guard
    const rawBody: unknown = await request.json()
    if (!rawBody || typeof rawBody !== 'object' || Array.isArray(rawBody)) {
      return apiError('Invalid request body.', 400)
    }
    const body = rawBody as {
      prefix?: unknown
      deleteCommandMessages?: unknown
      warnEnabled?: unknown
      warnMuteAt?: unknown
      warnKickAt?: unknown
      warnBanAt?: unknown
      warnMuteDuration?: unknown
      dmUsers?: unknown
      respondWithReason?: unknown
      preserveBanMessages?: unknown
      useTimeouts?: unknown
    }
    const allowedKeys = [
      'prefix',
      'deleteCommandMessages',
      'warnEnabled',
      'warnMuteAt',
      'warnKickAt',
      'warnBanAt',
      'warnMuteDuration',
      'dmUsers',
      'respondWithReason',
      'preserveBanMessages',
      'useTimeouts',
    ]
    const unknownKeys = Object.keys(body).filter((k) => !allowedKeys.includes(k))
    if (unknownKeys.length > 0) return apiError(`Unsupported field: ${unknownKeys.join(', ')}`, 400)

    const changes: Record<string, unknown> = {}
    const audit: Record<string, unknown> = {}
    const before = extractServerSettings(await getBotGuildSettings(guard.selectedGuildId!))

    if (body.prefix !== undefined) {
      const error = validatePrefix(body.prefix)
      if (error) return apiError(error, 400)
      const prefix = (body.prefix as string).trim()
      changes['prefix'] = prefix
      audit['prefix'] = { from: before.prefix, to: prefix }
    }

    if (body.deleteCommandMessages !== undefined) {
      if (typeof body.deleteCommandMessages !== 'boolean') {
        return apiError('deleteCommandMessages must be true or false.', 400)
      }
      changes['moderation_delete_commands'] = body.deleteCommandMessages
      audit['deleteCommandMessages'] = {
        from: before.deleteCommandMessages,
        to: body.deleteCommandMessages,
      }
    }

    if (body.warnEnabled !== undefined) {
      if (typeof body.warnEnabled !== 'boolean') return apiError('warnEnabled must be true or false.', 400)
      changes['warn_thresholds_enabled'] = body.warnEnabled
      audit['warnEnabled'] = { from: before.warnEnabled, to: body.warnEnabled }
    }

    if (body.warnMuteAt !== undefined) {
      const v = readInt(body.warnMuteAt, before.warnMuteAt, 1, 20)
      changes['warn_threshold_mute'] = v
      audit['warnMuteAt'] = { from: before.warnMuteAt, to: v }
    }

    if (body.warnKickAt !== undefined) {
      const v = readInt(body.warnKickAt, before.warnKickAt, 1, 20)
      changes['warn_threshold_kick'] = v
      audit['warnKickAt'] = { from: before.warnKickAt, to: v }
    }

    if (body.warnBanAt !== undefined) {
      const v = readInt(body.warnBanAt, before.warnBanAt, 1, 20)
      changes['warn_threshold_ban'] = v
      audit['warnBanAt'] = { from: before.warnBanAt, to: v }
    }

    if (body.warnMuteDuration !== undefined) {
      const v = readInt(body.warnMuteDuration, before.warnMuteDuration, 60, 2592000)
      changes['warn_mute_duration'] = v
      audit['warnMuteDuration'] = { from: before.warnMuteDuration, to: v }
    }

    if (body.dmUsers !== undefined) {
      if (typeof body.dmUsers !== 'boolean') return apiError('dmUsers must be true or false.', 400)
      changes['moderation_dm_users'] = body.dmUsers
      audit['dmUsers'] = { from: before.dmUsers, to: body.dmUsers }
    }

    if (body.respondWithReason !== undefined) {
      if (typeof body.respondWithReason !== 'boolean') return apiError('respondWithReason must be true or false.', 400)
      changes['moderation_respond_with_reason'] = body.respondWithReason
      audit['respondWithReason'] = { from: before.respondWithReason, to: body.respondWithReason }
    }

    if (body.preserveBanMessages !== undefined) {
      if (typeof body.preserveBanMessages !== 'boolean') return apiError('preserveBanMessages must be true or false.', 400)
      changes['moderation_preserve_ban_messages'] = body.preserveBanMessages
      audit['preserveBanMessages'] = { from: before.preserveBanMessages, to: body.preserveBanMessages }
    }

    if (body.useTimeouts !== undefined) {
      if (typeof body.useTimeouts !== 'boolean') return apiError('useTimeouts must be true or false.', 400)
      changes['moderation_use_timeouts'] = body.useTimeouts
      audit['useTimeouts'] = { from: before.useTimeouts, to: body.useTimeouts }
    }

    if (Object.keys(changes).length === 0) {
      return apiError('Nothing to update.', 400)
    }

    const updated = await patchBotGuildSettings(guard.selectedGuildId!, changes)
    await recordGuildAudit(guard.selectedGuildId!, guard, 'server_settings.updated', 'server', audit)
    return ok({ settings: extractServerSettings(updated) })
  } catch (error) {
    if (error instanceof SyntaxError) return apiError('Request body must be valid JSON.', 400)
    return handleError(error)
  }
}