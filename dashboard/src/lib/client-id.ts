let fallbackSequence = 0

/**
 * Generates non-secret browser identifiers in secure and insecure contexts.
 * `crypto.randomUUID()` is unavailable on remote HTTP pages, so UI keys and
 * idempotency keys need a collision-resistant fallback that cannot throw.
 */
export function createClientId(prefix = 'client'): string {
  const browserCrypto = globalThis.crypto
  if (typeof browserCrypto?.randomUUID === 'function') {
    return browserCrypto.randomUUID()
  }

  fallbackSequence = (fallbackSequence + 1) % Number.MAX_SAFE_INTEGER
  const bytes = new Uint32Array(2)
  if (typeof browserCrypto?.getRandomValues === 'function') {
    browserCrypto.getRandomValues(bytes)
  } else {
    bytes[0] = Math.floor(Math.random() * 0x1_0000_0000)
    bytes[1] = Math.floor(Math.random() * 0x1_0000_0000)
  }
  const entropy = Array.from(bytes, (value) => value.toString(36)).join('')
  return `${prefix}-${Date.now().toString(36)}-${fallbackSequence.toString(36)}-${entropy}`
}
