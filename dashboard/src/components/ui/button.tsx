import { forwardRef } from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

type Variant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'subtle'
type Size = 'sm' | 'md' | 'lg' | 'icon'

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-accent text-accent-foreground shadow-[0_12px_30px_-18px_var(--accent)] hover:-translate-y-px hover:brightness-110 active:translate-y-0 active:brightness-95',
  secondary:
    'bg-surface-2 text-foreground hover:bg-border/60 border border-border',
  outline:
    'border border-border-strong text-foreground hover:bg-surface-2',
  ghost: 'text-foreground hover:bg-surface-2',
  subtle: 'bg-accent-soft text-accent border border-accent-line hover:brightness-105',
  danger: 'bg-danger text-white hover:brightness-110 active:brightness-95',
}

const SIZES: Record<Size, string> = {
  sm: 'h-9 px-3.5 text-sm gap-1.5 rounded-lg',
  md: 'h-10 px-4 text-sm gap-2 rounded-xl',
  lg: 'h-12 px-6 text-base gap-2 rounded-xl',
  icon: 'h-10 w-10 rounded-xl',
}

export function buttonVariants({
  variant = 'primary',
  size = 'md',
  className,
}: { variant?: Variant; size?: Size; className?: string } = {}) {
  return cn(
    'focus-ring inline-flex items-center justify-center font-medium whitespace-nowrap transition-all disabled:pointer-events-none disabled:opacity-50 select-none',
    VARIANTS[variant],
    SIZES[size],
    className,
  )
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', loading, className, children, disabled, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      className={buttonVariants({ variant, size, className })}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="size-4 animate-spin" />}
      {children}
    </button>
  )
})
