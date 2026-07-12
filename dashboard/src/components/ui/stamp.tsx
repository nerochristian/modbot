import { cn } from '@/lib/utils'

/**
 * Stamp — the signature records mark. Sets an identifier and an optional
 * UTC timestamp like an official ledger stamp, in mono with tabular figures.
 * Repeated across cases, appeals, members, and log rows; it is the product's
 * visual fingerprint.
 *
 * Example: <Stamp id="CASE-2847" at={createdAt} />  ->  CASE-2847 · 07·12 14:22Z
 */
export function Stamp({
  id,
  at,
  accent = false,
  className,
}: {
  id: string
  at?: string | number | Date | null
  accent?: boolean
  className?: string
}) {
  return (
    <span className={cn('stamp', accent && 'stamp-accent', className)}>
      <span>{id}</span>
      {at != null && (
        <>
          <span className="stamp-dot" aria-hidden />
          <span>{formatStampTime(at)}</span>
        </>
      )}
    </span>
  )
}

/** MM·DD HH:MMZ in UTC — the compact records-stamp timestamp. */
export function formatStampTime(value: string | number | Date): string {
  const d = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const mm = String(d.getUTCMonth() + 1).padStart(2, '0')
  const dd = String(d.getUTCDate()).padStart(2, '0')
  const hh = String(d.getUTCHours()).padStart(2, '0')
  const mi = String(d.getUTCMinutes()).padStart(2, '0')
  return `${mm}·${dd} ${hh}:${mi}Z`
}
