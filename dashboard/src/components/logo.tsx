import { cn } from '@/lib/utils'

/**
 * The Aegis wordmark + shield glyph. Uses the current accent color, with a
 * mint "active" notch that ties into the protected-state signal channel.
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
    <span className={cn('inline-flex items-center gap-2 font-semibold text-foreground', className)}>
      <span
        className={cn('relative grid place-items-center rounded-lg text-accent-foreground', glyph)}
        style={{
          background:
            'linear-gradient(150deg, var(--accent), color-mix(in srgb, var(--accent) 55%, #000))',
        }}
        aria-hidden
      >
        <svg viewBox="0 0 24 24" className="size-[64%]" fill="none">
          {/* Shield outline */}
          <path
            d="M12 2.5 4.5 5.2v6.1c0 4.6 3.1 8.3 7.5 9.9 4.4-1.6 7.5-5.3 7.5-9.9V5.2L12 2.5Z"
            fill="currentColor"
            fillOpacity="0.95"
          />
          {/* Check / active mark */}
          <path
            d="M8.4 12.1l2.5 2.5 4.6-4.9"
            stroke="var(--accent)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span
          className="absolute -right-0.5 -top-0.5 size-1.5 rounded-full"
          style={{ background: 'var(--mint)' }}
        />
      </span>
      {showWordmark && <span className={cn('tracking-tight', text)}>Aegis</span>}
    </span>
  )
}
