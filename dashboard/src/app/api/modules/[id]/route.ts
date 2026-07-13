import { apiError, handleError, ok, requireMutation } from '@/lib/api'
import { recordGuildAudit } from '@/lib/bot-audit'
import { ModuleValidationError, setModuleEnabled, updateModuleSettings } from '@/lib/modules-service'

export async function PATCH(request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireMutation(request, 'config.write')
    if (guard instanceof Response) return guard
    const { id } = await ctx.params
    const rawBody: unknown = await request.json()
    if (!rawBody || typeof rawBody !== 'object' || Array.isArray(rawBody)) {
      return apiError('Invalid request body.', 400)
    }
    const body = rawBody as { enabled?: boolean; settings?: Record<string, unknown> }
    const unknownBodyKeys = Object.keys(body).filter((key) => key !== 'enabled' && key !== 'settings')
    if (unknownBodyKeys.length > 0) return apiError(`Unsupported field: ${unknownBodyKeys.join(', ')}`, 400)
    if (body.settings !== undefined && (
      !body.settings || typeof body.settings !== 'object' || Array.isArray(body.settings)
    )) {
      return apiError('`settings` must be an object.', 400)
    }
    if (body.settings && Object.keys(body.settings).length === 0) {
      return apiError('Provide at least one setting to update.', 400)
    }
    if (body.enabled !== undefined && typeof body.enabled !== 'boolean') {
      return apiError('`enabled` must be true or false.', 400)
    }
    if (typeof body.enabled === 'boolean' && body.settings !== undefined) {
      return apiError('Update the module state and settings in separate requests.', 400)
    }

    // A toggle-only patch flips the module's enable flag; a settings patch
    // writes its customizable fields. Either may be present.
    let result
    if (typeof body.enabled === 'boolean') {
      result = await setModuleEnabled(guard.selectedGuildId!, id, body.enabled)
      await recordGuildAudit(guard.selectedGuildId!, guard, 'module.toggled', id, { enabled: body.enabled })
    }
    if (body.settings && typeof body.settings === 'object') {
      result = await updateModuleSettings(guard.selectedGuildId!, id, body.settings)
      await recordGuildAudit(guard.selectedGuildId!, guard, 'module.updated', id, result.values)
    }
    if (!result) return apiError('Nothing to update: provide `enabled` or `settings`.', 400)
    return ok(result)
  } catch (error) {
    if (error instanceof SyntaxError) return apiError('Request body must be valid JSON.', 400)
    if (error instanceof ModuleValidationError) return apiError(error.message, 400)
    if (error instanceof Error && /not found/i.test(error.message)) return apiError(error.message, 404)
    if (error instanceof Error && /(must be|cannot be toggled|not initialized)/i.test(error.message)) {
      return apiError(error.message, 400)
    }
    return handleError(error)
  }
}
