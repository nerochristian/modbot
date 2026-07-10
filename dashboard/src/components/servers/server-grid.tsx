'use client'

import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { ArrowUpRight, Check, Loader2, LogOut, Plus, RefreshCw, Server } from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import type { ManagedGuild } from '@/lib/discord'
import { cn, initials } from '@/lib/utils'

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
  const [loading, setLoading] = useState(false)
  return (
    <button
      type="button"
      disabled={loading}
      onClick={async () => {
        setLoading(true)
        await fetch('/api/auth/logout', { method: 'POST' }).catch(() => undefined)
        router.push('/login')
        router.refresh()
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
  const [opening, setOpening] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const installed = guilds.filter((guild) => guild.installed).length

  async function openGuild(guildId: string) {
    setOpening(guildId)
    try {
      const response = await fetch('/api/guilds/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ guildId }),
      })
      if (!response.ok) throw new Error('Server selection failed')
      router.push('/dashboard')
      router.refresh()
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
            await fetch('/api/guilds?refresh=1', { cache: 'no-store' }).catch(() => undefined)
            router.refresh()
            setRefreshing(false)
          }}
          className={buttonVariants({ variant: 'outline', size: 'sm' })}
        >
          <RefreshCw className={cn('size-4', refreshing && 'animate-spin')} />
          Refresh servers
        </button>
      </div>

      {guilds.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border-strong bg-surface p-10 text-center">
          <Server className="mx-auto size-7 text-muted-2" />
          <h2 className="mt-4 font-semibold text-foreground">No manageable servers found</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted">
            Discord only returns servers where you are the owner or have Manage Server access.
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
                    {guild.installed ? 'Aegis connected' : 'Aegis not installed'}
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
                    Open
                  </button>
                ) : (
                  <a
                    href={guild.inviteUrl}
                    target="_blank"
                    rel="noreferrer"
                    className={buttonVariants({ variant: 'secondary', size: 'sm' })}
                  >
                    <Plus className="size-4" />
                    Add Aegis
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
