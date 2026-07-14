'use client'

import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { ArrowUpRight, Check, Loader2, LogOut, Plus, RefreshCw, Server } from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import type { ManagedGuild } from '@/lib/discord'
import { cn, initials } from '@/lib/utils'
import { useToast } from '@/components/ui/toast'

function ServerMark({ guild }: { guild: ManagedGuild }) {
  if (guild.iconUrl) {
    return (
      <Image
        src={guild.iconUrl}
        alt=""
        width={56}
        height={56}
        unoptimized
        className="size-14 rounded-2xl object-cover ring-1 ring-white/10"
      />
    )
  }
  return (
    <span className="grid size-14 place-items-center rounded-2xl bg-surface-2 text-base font-bold text-foreground ring-1 ring-border">
      {initials(guild.name)}
    </span>
  )
}

export function SignOutButton() {
  const router = useRouter()
  const toast = useToast()
  const [loading, setLoading] = useState(false)
  return (
    <button
      type="button"
      disabled={loading}
      onClick={async () => {
        setLoading(true)
        try {
          const response = await fetch('/api/auth/logout', { method: 'POST' })
          const body = await response.json().catch(() => ({}))
          if (!response.ok) throw new Error(body.error ?? 'Could not sign out')
          router.push('/login')
          router.refresh()
        } catch (reason) {
          toast.error(
            'You are still signed in',
            reason instanceof Error ? reason.message : 'Try again in a moment.',
          )
          setLoading(false)
        }
      }}
      className={buttonVariants({ variant: 'ghost', size: 'sm' })}
    >
      {loading ? <Loader2 className="size-4 animate-spin" /> : <LogOut className="size-4" />}
      Sign out
    </button>
  )
}

export function ServerGrid({ guilds }: { guilds: ManagedGuild[] }) {
  const router = useRouter()
  const toast = useToast()
  const [opening, setOpening] = useState<string | null>(null)
  const [openError, setOpenError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const installed = guilds.filter((guild) => guild.installed).length

  async function openGuild(guildId: string) {
    setOpening(guildId)
    setOpenError(null)
    try {
      const response = await fetch('/api/guilds/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ guildId }),
      })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(body.error ?? 'Server selection failed')
      window.location.assign('/dashboard/modules')
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Try again in a moment.'
      setOpenError(message)
      toast.error(
        'Server could not be opened',
        message,
      )
    } finally {
      setOpening(null)
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">
          <span className="font-semibold text-foreground">{installed}</span> connected ·{' '}
          <span className="font-semibold text-foreground">{guilds.length - installed}</span> available to add
        </p>
        <button
          type="button"
          disabled={refreshing}
          onClick={async () => {
            setRefreshing(true)
            try {
              const response = await fetch('/api/guilds?refresh=1', { cache: 'no-store' })
              const body = await response.json().catch(() => ({}))
              if (!response.ok) throw new Error(body.error ?? 'Could not refresh servers')
              router.refresh()
            } catch (reason) {
              toast.error(
                'Servers were not refreshed',
                reason instanceof Error ? reason.message : 'Try again in a moment.',
              )
            } finally {
              setRefreshing(false)
            }
          }}
          className={buttonVariants({ variant: 'outline', size: 'sm' })}
        >
          <RefreshCw className={cn('size-4', refreshing && 'animate-spin')} />
          Refresh servers
        </button>
      </div>

      {openError && (
        <div className="mb-5 flex items-start justify-between gap-3 border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger" role="alert">
          <span>Server could not be opened: {openError}</span>
          <button
            type="button"
            onClick={() => setOpenError(null)}
            className="focus-ring shrink-0 rounded-sm px-1 font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {guilds.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border-strong bg-surface p-10 text-center">
          <Server className="mx-auto size-7 text-muted-2" />
          <h2 className="mt-4 font-semibold text-foreground">Administrator permission required</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted">
            Docket only shows servers you own or where your Discord account has Administrator permission.
          </p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {guilds.map((guild) => (
            <article
              key={guild.id}
              className={cn(
                'group relative overflow-hidden rounded-2xl border bg-surface p-5 transition-all hover:-translate-y-0.5 hover:border-border-strong hover:shadow-xl hover:shadow-black/5',
                guild.installed ? 'border-mint/25' : 'border-border',
              )}
            >
              <div className={cn('absolute inset-x-0 top-0 h-px', guild.installed ? 'bg-mint' : 'bg-border')} />
              <div className="flex items-start gap-4">
                <ServerMark guild={guild} />
                <div className="min-w-0 flex-1">
                  <h2 className="truncate font-semibold text-foreground">{guild.name}</h2>
                  <p className="mt-1 flex items-center gap-1.5 text-xs text-muted">
                    <span className={cn('size-1.5 rounded-full', guild.installed ? 'bg-mint' : 'bg-muted-2')} />
                    {guild.installed ? 'Docket connected' : 'Docket not installed'}
                  </p>
                </div>
                {guild.owner && (
                  <span className="rounded-md bg-accent-soft px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-accent">
                    Owner
                  </span>
                )}
              </div>
              <div className="mt-5 flex items-center justify-between border-t border-border pt-4">
                <span className="text-xs text-muted-2">
                  {guild.memberCount != null ? `${guild.memberCount.toLocaleString()} members` : 'Manage server'}
                </span>
                {guild.installed ? (
                  <button
                    type="button"
                    disabled={opening === guild.id}
                    onClick={() => openGuild(guild.id)}
                    className={buttonVariants({ size: 'sm' })}
                  >
                    {opening === guild.id ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />}
                    {opening === guild.id ? 'Opening…' : 'Open'}
                  </button>
                ) : (
                  <a
                    href={guild.inviteUrl}
                    target="_blank"
                    rel="noreferrer"
                    className={buttonVariants({ variant: 'secondary', size: 'sm' })}
                  >
                    <Plus className="size-4" />
                    Add Docket
                    <ArrowUpRight className="size-3.5" />
                  </a>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
