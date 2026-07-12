import Image from 'next/image'
import { cn } from '@/lib/utils'

/**
 * The Docket logo — the real brand glyph (electric-blue "D" built from a
 * checklist/docket) next to the wordmark. Used across marketing chrome and
 * the dashboard shell. The glyph lives in /public/brand.
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
  const glyphPx = { sm: 22, md: 26, lg: 34 }[size]
  const text = { sm: 'text-base', md: 'text-lg', lg: 'text-2xl' }[size]
  return (
    <span className={cn('inline-flex items-center gap-2.5 font-display font-semibold text-foreground', className)}>
      <Image
        src="/brand/docket-glyph.png"
        alt="Docket"
        width={glyphPx}
        height={glyphPx}
        priority
        className="rounded-[5px]"
        style={{ width: glyphPx, height: glyphPx, objectFit: 'contain' }}
      />
      {showWordmark && <span className={cn('tracking-tight', text)}>Docket</span>}
    </span>
  )
}
