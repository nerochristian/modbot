'use client'

import { ExternalLink, LogOut, Monitor, ShieldCheck } from 'lucide-react'
import { SettingsCard } from '@/components/dashboard/setting-section'
import { Button, buttonVariants } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { EmptyState, ErrorState } from '@/components/ui/empty-state'
import { Spinner } from '@/components/ui/spinner'
import { useToast } from '@/components/ui/toast'
import { useApi } from '@/lib/use-api'
import { formatDistanceToNow } from 'date-fns'

type Session = {
  id: string
  userAgent: string | null
  ip: string | null
  createdAt: string
  current: boolean
}

type SessionsPayload = { sessions: Session[] }

export default function SecuritySettingsPage() {
  const toast = useToast()
  const { data, loading, error, refetch } = useApi<SessionsPayload>('/api/account/sessions')

  async function signOutOthers() {
    try {
      const response = await fetch('/api/account/sessions', { method: 'DELETE' })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(body.error ?? 'Could not sign out the other sessions')
      }
      toast.success('Other dashboard sessions signed out')
      refetch()
    } catch (reason) {
      toast.error(
        'Sessions were not changed',
        reason instanceof Error ? reason.message : 'Try again in a moment.',
      )
    }
  }

  const sessions = data?.sessions ?? []

  return (
    <>
      <SettingsCard
        title="Discord account security"
        description="Docket uses your Discord account for identity. Passwords and two-step verification are managed by Discord."
        footer={
          <a
            href="https://support.discord.com/hc/en-us/sections/360009072571-Account-Security"
            target="_blank"
            rel="noreferrer"
            className={buttonVariants({ variant: 'outline' })}
          >
            <ShieldCheck className="size-4" />
            Open Discord security
            <ExternalLink className="size-3.5" />
          </a>
        }
      >
        <p className="text-sm leading-6 text-muted">
          Review your Discord password, authenticator, and recovery codes there. Docket never displays or changes those credentials.
        </p>
      </SettingsCard>

      <SettingsCard
        title="Dashboard sessions"
        description="Browsers currently signed in to this Docket account."
        footer={
          sessions.length > 1 ? (
            <Button variant="outline" onClick={signOutOthers}>
              <LogOut className="size-4" />
              Sign out other sessions
            </Button>
          ) : undefined
        }
      >
        {error && !data ? (
          <ErrorState
            title="Sessions could not be loaded"
            description={error}
            onRetry={refetch}
            className="py-10"
          />
        ) : loading && !data ? (
          <div className="flex justify-center py-12">
            <Spinner />
          </div>
        ) : sessions.length === 0 ? (
          <EmptyState
            icon={Monitor}
            title="No active sessions found"
            description="Sign in with Discord again to create a dashboard session."
            className="py-10"
          />
        ) : (
          <ul className="divide-y divide-border">
            {sessions.map((session) => (
              <li key={session.id} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
                <span className="flex size-9 items-center justify-center rounded-lg bg-surface-2 text-muted">
                  <Monitor className="size-4.5" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">
                    {session.userAgent?.split(')')[0]?.replace('Mozilla/5.0 (', '') ?? 'Unknown browser'}
                  </p>
                  <p className="text-xs text-muted">
                    {session.ip ?? 'unknown IP'} · started{' '}
                    {formatDistanceToNow(new Date(session.createdAt), { addSuffix: true })}
                  </p>
                </div>
                {session.current && (
                  <Badge tone="success" dot>
                    This session
                  </Badge>
                )}
              </li>
            ))}
          </ul>
        )}
      </SettingsCard>
    </>
  )
}
