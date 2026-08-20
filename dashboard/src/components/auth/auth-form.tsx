import Link from 'next/link'
import { ArrowRight, Hash } from 'lucide-react'

/**
 * The sign-in card. Reads like the Discord OAuth prompt it leads to: a
 * channel-style header, one plain sentence, one decisive button.
 */
export function AuthForm({
  mode,
  next,
  error,
}: {
  mode: 'login' | 'register'
  next: string
  error?: string
}) {
  const authorizeUrl = `/api/auth/discord/authorize?next=${encodeURIComponent(next)}`

  return (
    <div className="glass-panel overflow-hidden rounded-2xl">
      <div className="flex items-center gap-2 border-b border-border px-6 py-4">
        <Hash className="size-4 text-muted-2" />
        <span className="font-mono text-[0.6875rem] uppercase tracking-[0.16em] text-muted-2">sign-in</span>
      </div>
      <div className="px-6 py-7">
        <h1 className="font-display text-[1.6rem] font-semibold leading-[1.1] tracking-[-0.02em] text-foreground">
          {mode === 'login' ? 'Sign in to Docket.' : 'Get started with Docket.'}
        </h1>
        <p className="mt-3 text-[0.8125rem] leading-6 text-muted">
          Use the Discord account your servers already trust. The dashboard only lists servers
          where your live permission is Administrator.
        </p>

        {error && (
          <div className="mt-5 rounded-md border-l-2 border-threat bg-threat-soft/50 px-4 py-3 text-[0.8125rem] text-threat">
            {error}
          </div>
        )}

        <Link
          href={authorizeUrl}
          className="focus-ring group mt-7 flex w-full items-center justify-between rounded-lg bg-accent px-5 py-3.5 text-[0.9375rem] font-semibold text-accent-foreground shadow-[0_18px_42px_-20px_var(--accent)] transition-all hover:-translate-y-px hover:brightness-110 active:translate-y-0"
        >
          <span className="inline-flex items-center gap-2.5">
            <svg viewBox="0 0 24 24" className="size-5" fill="currentColor" aria-hidden>
              <path d="M19.5 5.34A17.3 17.3 0 0 0 15.44 4l-.5 1.02a15.8 15.8 0 0 0-5.86 0L8.56 4A17.4 17.4 0 0 0 4.5 5.35C1.93 9.16 1.24 12.88 1.59 16.54a16.4 16.4 0 0 0 4.98 2.51l1.2-1.63a10.7 10.7 0 0 1-1.89-.91l.46-.36a12.4 12.4 0 0 0 11.32 0l.46.36c-.6.36-1.23.66-1.89.91l1.2 1.63a16.4 16.4 0 0 0 4.98-2.51c.41-4.24-.7-7.93-2.91-11.2ZM8.5 14.35c-1.09 0-1.99-1-1.99-2.22s.88-2.23 1.99-2.23c1.12 0 2.01 1.01 1.99 2.23 0 1.22-.88 2.22-1.99 2.22Zm7 0c-1.09 0-1.99-1-1.99-2.22s.88-2.23 1.99-2.23c1.12 0 2.01 1.01 1.99 2.23 0 1.22-.87 2.22-1.99 2.22Z" />
            </svg>
            Continue with Discord
          </span>
          <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
        </Link>

        <p className="mt-4 text-center font-mono text-[0.5625rem] uppercase tracking-[0.16em] text-muted-2">
          OAuth only · your password never touches Docket
        </p>
      </div>
    </div>
  )
}
