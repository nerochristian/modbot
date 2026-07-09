import { cn } from '@/lib/utils'

/** The Nebula wordmark + glyph. Uses the current accent color. */
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
    <span className={cn('inline-flex items-center gap-2 font-semibold text-foreground', className)}>
      <span
        className={cn('grid place-items-center rounded-xl text-accent-foreground', glyph)}
        style={{
          background:
            'linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent) 55%, #000))',
        }}
        aria-hidden
      >
        <svg viewBox="0 0 24 24" className="size-[62%]" fill="none">
          <path
            d="M12 2c1.6 3.9 4.1 6.4 8 8-3.9 1.6-6.4 4.1-8 8-1.6-3.9-4.1-6.4-8-8 3.9-1.6 6.4-4.1 8-8Z"
            fill="currentColor"
          />
        </svg>
      </span>
      {showWordmark && <span className={cn('tracking-tight', text)}>Nebula</span>}
    </span>
  )
}
