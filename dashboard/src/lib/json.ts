/**
 * Typed (de)serialization for JSON-shaped columns stored as TEXT.
 *
 * We store structured config/metadata as strings so the schema stays portable
 * across SQLite and Postgres. These helpers centralize parsing so callers get a
 * typed value and never crash on malformed data.
 */
export function parseJson<T>(value: string | null | undefined, fallback: T): T {
  if (!value) return fallback
  try {
    return JSON.parse(value) as T
  } catch {
    return fallback
  }
}

export function stringifyJson(value: unknown): string {
  return JSON.stringify(value)
}
