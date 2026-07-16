import { z } from 'zod'
import { apiError, created, handleError, ok } from '@/lib/api'
import { getAppealPortalCase, submitAppealWithToken } from '@/lib/appeal-portal-service'

const submissionSchema = z.object({
  answers: z.record(z.string(), z.string().max(2000)).refine((value) => Object.keys(value).length <= 5, 'Too many answers'),
})

function portalError(kind: 'not_found' | 'expired' | 'used' | 'closed') {
  if (kind === 'closed') return apiError('This server is not accepting appeals right now.', 403)
  if (kind === 'expired') return apiError('This appeal link has expired.', 410)
  if (kind === 'used') return apiError('This appeal link has already been used.', 409)
  return apiError('Appeal link not found.', 404)
}

type PortalContext = { params: Promise<{ token: string }> }

export async function GET(_request: Request, ctx: PortalContext) {
  try {
    const { token } = await ctx.params
    const result = await getAppealPortalCase(token)
    if (result.kind !== 'ok') return portalError(result.kind)
    return ok(result)
  } catch (error) {
    return handleError(error)
  }
}

export async function POST(request: Request, ctx: PortalContext) {
  try {
    const { token } = await ctx.params
    const data = submissionSchema.parse(await request.json())
    const result = await submitAppealWithToken(token, data.answers)
    if (result.kind !== 'ok') return portalError(result.kind)
    return created(result.appeal)
  } catch (error) {
    return handleError(error)
  }
}
