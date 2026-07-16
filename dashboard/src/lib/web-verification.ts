import 'server-only'

import { createHmac, timingSafeEqual } from 'node:crypto'

export type VerificationCapability = {
  e: number
  g: string
  n: string
  u: string
}

function signingSecret(): string {
  const value = process.env.VERIFICATION_LINK_SECRET?.trim() || process.env.SESSION_SECRET?.trim()
  if (!value) throw new Error('VERIFICATION_LINK_SECRET or SESSION_SECRET is required')
  return value
}

export function verifyVerificationCapability(token: string): VerificationCapability {
  const [encodedPayload, encodedSignature, extra] = token.split('.')
  if (!encodedPayload || !encodedSignature || extra || token.length > 1200) throw new Error('Invalid verification link')
  const expected = createHmac('sha256', signingSecret()).update(encodedPayload).digest()
  const supplied = Buffer.from(encodedSignature, 'base64url')
  if (supplied.length !== expected.length || !timingSafeEqual(supplied, expected)) throw new Error('Invalid verification link')
  const payload = JSON.parse(Buffer.from(encodedPayload, 'base64url').toString('utf8')) as Partial<VerificationCapability>
  if (
    !Number.isInteger(payload.e)
    || Number(payload.e) <= Math.floor(Date.now() / 1000)
    || Number(payload.e) > Math.floor(Date.now() / 1000) + 15 * 60
    || typeof payload.g !== 'string'
    || typeof payload.u !== 'string'
    || typeof payload.n !== 'string'
    || !/^\d{15,22}$/.test(payload.g)
    || !/^\d{15,22}$/.test(payload.u)
    || !/^[a-f0-9]{32}$/.test(payload.n)
  ) {
    throw new Error('Verification link is expired or malformed')
  }
  return payload as VerificationCapability
}
