import { cn } from '@/lib/utils'

/**
 * The Docket wordmark + glyph. The mark is a docket page — stacked ruled
 * entries with the top line "active" in the accent-foreground, and a cobalt
 * corner tab like a filed record. Squared to match the records-desk radius.
 */
export function Logo({
  className,
  showWordmark = true,
  size = 'md',
}: {
  className?: string
  showWordmark?: boolean
  size?: 'sm' | 'md' | 'lg'
}) {
  const glyph = { sm: 'size-6', md: 'size-7', lg: 'size-9' }[size]
  const text = { sm: 'text-base', md: 'text-lg', lg: 'text-2xl' }[size]
  return (
    <span className={cn('inline-flex items-center gap-2.5 font-display font-semibold text-foreground', className)}>
      <span
        className={cn('relative grid place-items-center rounded-md text-accent-foreground', glyph)}
        style={{ background: 'var(--accent)' }}
        aria-hidden
      >
        <svg viewBox="0 0 24 24" className="size-[62%]" fill="none">
          {/* Docket entries — ruled lines, top line active/full width */}
          <rect x="3" y="5" width="18" height="2.4" rx="1" fill="currentColor" />
          <rect x="3" y="10.4" width="13" height="2.2" rx="1" fill="currentColor" fillOpacity="0.7" />
          <rect x="3" y="15.4" width="15" height="2.2" rx="1" fill="currentColor" fillOpacity="0.45" />
        </svg>
        {/* Filed-corner tab */}
        <span
          className="absolute -right-1 -top-1 size-2 rounded-[2px] border-2"
          style={{ borderColor: 'var(--accent)', background: 'var(--surface)' }}
        />
      </span>
      {showWordmark && <span className={cn('tracking-tight', text)}>Docket</span>}
    </span>
  )
}
