import { apiError, handleError, ok, requireMutation, requireUser } from '@/lib/api'
import { recordGuildAudit } from '@/lib/bot-audit'
import { ModuleValidationError, addWhitelist, listWhitelist, removeWhitelist } from '@/lib/modules-service'

export async function GET() {
  try {
    const guard = await requireUser('settings.read')
    if (guard instanceof Response) return guard
    return ok({ data: await listWhitelist(guard.selectedGuildId!) })
  } catch (error) {
    return handleError(error)
  }
}

export async function POST(request: Request) {
  try {
    const guard = await requireMutation(request, 'config.write')
    if (guard instanceof Response) return guard
    const body: unknown = await request.json()
    if (!body || typeof body !== 'object' || Array.isArray(body)) return apiError('Invalid request body.', 400)
    const { userId } = body as { userId?: string }
    if (Object.keys(body).some((key) => key !== 'userId')) return apiError('Unsupported request field.', 400)
    if (typeof userId !== 'string' || !userId.trim()) return apiError('A user ID string is required.', 400)
    if (!guard.discordId) return apiError('Your Discord identity is unavailable. Sign in again.', 401)
    const added = await addWhitelist(guard.selectedGuildId!, String(userId).trim(), guard.discordId)
    if (!added) return apiError('That user is already whitelisted.', 409)
    await recordGuildAudit(guard.selectedGuildId!, guard, 'whitelist.added', String(userId).trim())
    return ok({ data: await listWhitelist(guard.selectedGuildId!) })
  } catch (error) {
    if (error instanceof SyntaxError) return apiError('Request body must be valid JSON.', 400)
    if (error instanceof ModuleValidationError) return apiError(error.message, 400)
    if (error instanceof Error && /must be a Discord ID/i.test(error.message)) return apiError(error.message, 400)
    return handleError(error)
  }
}

export async function DELETE(request: Request) {
  try {
    const guard = await requireMutation(request, 'config.write')
    if (guard instanceof Response) return guard
    const body: unknown = await request.json()
    if (!body || typeof body !== 'object' || Array.isArray(body)) return apiError('Invalid request body.', 400)
    const { userId } = body as { userId?: string }
    if (Object.keys(body).some((key) => key !== 'userId')) return apiError('Unsupported request field.', 400)
    if (typeof userId !== 'string' || !userId.trim()) return apiError('A user ID string is required.', 400)
    const removed = await removeWhitelist(guard.selectedGuildId!, String(userId).trim())
    if (!removed) return apiError('That user is not on the whitelist.', 404)
    await recordGuildAudit(guard.selectedGuildId!, guard, 'whitelist.removed', String(userId).trim())
    return ok({ data: await listWhitelist(guard.selectedGuildId!) })
  } catch (error) {
    if (error instanceof SyntaxError) return apiError('Request body must be valid JSON.', 400)
    if (error instanceof ModuleValidationError) return apiError(error.message, 400)
    if (error instanceof Error && /must be a Discord ID/i.test(error.message)) return apiError(error.message, 400)
    return handleError(error)
  }
}
