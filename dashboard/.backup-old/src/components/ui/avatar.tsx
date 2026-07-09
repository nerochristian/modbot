import { cn, initials } from '@/lib/utils'

export function Avatar({
  name,
  color,
  size = 'md',
  className,
}: {
  name: string
  color?: string | null
  size?: 'xs' | 'sm' | 'md' | 'lg'
  className?: string
}) {
  const sizes = {
    xs: 'size-6 text-[10px]',
    sm: 'size-8 text-xs',
    md: 'size-9 text-sm',
    lg: 'size-11 text-base',
  }
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white',
        sizes[size],
        className,
      )}
      style={{ backgroundColor: color ?? '#6366f1' }}
      aria-hidden
    >
      {initials(name)}
    </span>
  )
}
