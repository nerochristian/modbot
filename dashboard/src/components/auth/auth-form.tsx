import Link from 'next/link'
import { ArrowRight, Fingerprint, Server, ShieldCheck } from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'

type Mode = 'login' | 'register'

export function AuthForm({
  mode,
  next,
  error,
}: {
  mode: Mode
  next: string
  error?: string
}) {
  const authorizeUrl = `/api/auth/discord/authorize?next=${encodeURIComponent(next)}`

  return (
    <div>
      <div className="mb-7 inline-flex items-center gap-2 rounded-sm border border-border bg-surface px-3 py-1.5 font-mono text-[0.6875rem] font-medium uppercase tracking-[0.12em] text-muted">
        <span className="size-1.5 rounded-full bg-success" />
        Shift handover · badge check
      </div>
      <h1 className="font-display text-3xl font-semibold tracking-tight text-foreground">
        {mode === 'login' ? 'Back on shift.' : 'Join the desk.'}
      </h1>
      <p className="mt-3 text-sm leading-6 text-muted">
        Sign in with the Discord account your servers already trust. The dashboard only lists servers
        where your live permission is Administrator.
      </p>

      {error && (
        <div className="mt-5 rounded-md border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      <Link
        href={authorizeUrl}
        className={buttonVariants({ size: 'lg', className: 'mt-7 w-full justify-between' })}
      >
        <span className="inline-flex items-center gap-2">
          <svg viewBox="0 0 24 24" className="size-5" fill="currentColor" aria-hidden>
            <path d="M19.5 5.34A17.3 17.3 0 0 0 15.44 4l-.5 1.02a15.8 15.8 0 0 0-5.86 0L8.56 4A17.4 17.4 0 0 0 4.5 5.35C1.93 9.16 1.24 12.88 1.59 16.54a16.4 16.4 0 0 0 4.98 2.51l1.2-1.63a10.7 10.7 0 0 1-1.89-.91l.46-.36a12.4 12.4 0 0 0 11.32 0l.46.36c-.6.36-1.23.66-1.89.91l1.2 1.63a16.4 16.4 0 0 0 4.98-2.51c.41-4.24-.7-7.93-2.91-11.2ZM8.5 14.35c-1.09 0-1.99-1-1.99-2.22s.88-2.23 1.99-2.23c1.12 0 2.01 1.01 1.99 2.23 0 1.22-.88 2.22-1.99 2.22Zm7 0c-1.09 0-1.99-1-1.99-2.22s.88-2.23 1.99-2.23c1.12 0 2.01 1.01 1.99 2.23 0 1.22-.87 2.22-1.99 2.22Z" />
          </svg>
          Continue with Discord
        </span>
        <ArrowRight className="size-4" />
      </Link>

      <p className="mt-3 text-center text-xs leading-5 text-muted-2">
        We never see or store your Discord password.
      </p>

      <div className="mt-6 grid grid-cols-3 gap-2 border-t border-border pt-6 text-center text-[11px] text-muted-2">
        <span className="flex flex-col items-center gap-2">
          <Fingerprint className="size-4 text-muted" />
          OAuth only
        </span>
        <span className="flex flex-col items-center gap-2">
          <Server className="size-4 text-muted" />
          Multi-server
        </span>
        <span className="flex flex-col items-center gap-2">
          <ShieldCheck className="size-4 text-muted" />
          Admin-gated
        </span>
      </div>
    </div>
  )
}
