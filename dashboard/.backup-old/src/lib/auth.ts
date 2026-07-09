import { SignJWT, jwtVerify } from 'jose'
import bcrypt from 'bcryptjs'

/**
 * Stateless session tokens.
 *
 * We sign a compact JWT with the user id, role, and a token id (jti). The jti
 * ties the token to a Session row so tokens can be revoked (logout / logout all
 * devices). This file is crypto-only (no DB, no Node-specific APIs beyond what
 * jose/bcrypt need) so the token can be verified inside proxy.ts too.
 */

export const SESSION_COOKIE = 'nebula_session'

export type SessionPayload = {
  sub: string // user id
  role: string
  jti: string
  name: string
  email: string
}

function secret(): Uint8Array {
  const value = process.env.AUTH_SECRET
  if (!value) {
    throw new Error('AUTH_SECRET is not set. Add it to your .env file.')
  }
  return new TextEncoder().encode(value)
}

function ttlSeconds(): number {
  const raw = Number(process.env.AUTH_SESSION_TTL)
  return Number.isFinite(raw) && raw > 0 ? raw : 60 * 60 * 24 * 7
}

export async function signSession(payload: SessionPayload): Promise<string> {
  const now = Math.floor(Date.now() / 1000)
  return new SignJWT({ ...payload })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt(now)
    .setExpirationTime(now + ttlSeconds())
    .setSubject(payload.sub)
    .sign(secret())
}

export async function verifySession(token: string): Promise<SessionPayload | null> {
  try {
    const { payload } = await jwtVerify(token, secret())
    if (
      typeof payload.sub === 'string' &&
      typeof payload.jti === 'string' &&
      typeof payload.role === 'string'
    ) {
      return {
        sub: payload.sub,
        role: payload.role as string,
        jti: payload.jti as string,
        name: (payload.name as string) ?? '',
        email: (payload.email as string) ?? '',
      }
    }
    return null
  } catch {
    return null
  }
}

export function sessionExpiryDate(): Date {
  return new Date(Date.now() + ttlSeconds() * 1000)
}

export function sessionMaxAge(): number {
  return ttlSeconds()
}

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, 10)
}

export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash)
}
