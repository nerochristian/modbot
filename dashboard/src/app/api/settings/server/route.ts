import { apiError, handleError, ok, requireMutation, requireUser } from '@/lib/api'
import { recordGuildAudit } from '@/lib/bot-audit'
import { getBotGuildSettings, patchBotGuildSettings } from '@/lib/bot-settings'

type ServerSettings = {
  prefix: string
  deleteCommandMessages: boolean
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

  return { prefix, deleteCommandMessages }
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
    const body = rawBody as { prefix?: unknown; deleteCommandMessages?: unknown }
    const unknownKeys = Object.keys(body).filter(
      (k) => k !== 'prefix' && k !== 'deleteCommandMessages',
    )
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

    if (Object.keys(changes).length === 0) {
      return apiError('Nothing to update: provide `prefix` or `deleteCommandMessages`.', 400)
    }

    const updated = await patchBotGuildSettings(guard.selectedGuildId!, changes)
    await recordGuildAudit(guard.selectedGuildId!, guard, 'server_settings.updated', 'server', audit)
    return ok({ settings: extractServerSettings(updated) })
  } catch (error) {
    if (error instanceof SyntaxError) return apiError('Request body must be valid JSON.', 400)
    return handleError(error)
  }
}
