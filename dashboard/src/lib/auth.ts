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

export const SESSION_COOKIE = 'aegis_session'
export const SELECTED_GUILD_COOKIE = 'aegis_guild'

export function isSystemOwner(discordId: string | null | undefined): boolean {
  if (!discordId) return false
  return (process.env.OWNER_IDS ?? '')
    .split(',')
    .some((value) => value.trim() === discordId)
}

export function secureCookies(): boolean {
  const configured = process.env.SESSION_COOKIE_SECURE?.trim().toLowerCase()
  if (configured === 'true') return true
  if (configured === 'false') return false
  return process.env.NODE_ENV === 'production'
}

export type SessionPayload = {
  sub: string // user id
  jti: string
}

const RETURN_PATH_BASE = 'https://dashboard.invalid'

/** Accept only an application-local path. Never pass user input directly to new URL(). */
export function safeReturnPath(value: string | null | undefined, fallback = '/servers'): string {
  if (!value || !value.startsWith('/') || value.startsWith('//')) return fallback
  if (value.includes('\\') || /[\u0000-\u001f\u007f]/.test(value)) return fallback
  try {
    const parsed = new URL(value, RETURN_PATH_BASE)
    if (parsed.origin !== RETURN_PATH_BASE || !parsed.pathname.startsWith('/')) return fallback
    return `${parsed.pathname}${parsed.search}${parsed.hash}`
  } catch {
    return fallback
  }
}

function secret(): Uint8Array {
  const value = process.env.AUTH_SECRET || process.env.SESSION_SECRET
  if (!value) {
    throw new Error('AUTH_SECRET or SESSION_SECRET is not set. Add one to the project .env file.')
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
    const { payload } = await jwtVerify(token, secret(), { algorithms: ['HS256'] })
    if (
      typeof payload.sub === 'string' &&
      typeof payload.jti === 'string'
    ) {
      return {
        sub: payload.sub,
        jti: payload.jti as string,
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
