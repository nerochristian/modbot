'use client'

import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { ChevronsUpDown, Loader2, ServerCog } from 'lucide-react'
import { useState } from 'react'
import type { ManagedGuild } from '@/lib/discord'
import { useToast } from '@/components/ui/toast'

export function GuildSwitcher({ guilds, current }: { guilds: ManagedGuild[]; current: ManagedGuild }) {
  const router = useRouter()
  const toast = useToast()
  const [loading, setLoading] = useState(false)

  return (
    <div className="relative flex h-9 min-w-0 max-w-40 items-center rounded-lg border border-border bg-surface shadow-sm sm:max-w-none">
      {current.iconUrl ? (
        <Image src={current.iconUrl} alt="" width={24} height={24} unoptimized className="ml-1.5 size-6 rounded-md object-cover" />
      ) : (
        <span className="ml-1.5 grid size-6 place-items-center rounded-md bg-accent-soft text-accent"><ServerCog className="size-3.5" /></span>
      )}
      <select
        aria-label="Active Discord server"
        value={current.id}
        disabled={loading}
        onChange={async (event) => {
          setLoading(true)
          try {
            const response = await fetch('/api/guilds/select', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ guildId: event.target.value }),
            })
            const body = await response.json().catch(() => ({}))
            if (!response.ok) throw new Error(body.error ?? 'Could not switch servers')
            router.refresh()
          } catch (reason) {
            toast.error(
              'Server was not changed',
              reason instanceof Error ? reason.message : 'Try again in a moment.',
            )
          } finally {
            setLoading(false)
          }
        }}
        className="h-full min-w-0 max-w-28 appearance-none truncate bg-transparent py-0 pl-2 pr-7 text-sm font-medium text-foreground outline-none disabled:opacity-60 sm:max-w-44 sm:pr-8"
      >
        {guilds.filter((guild) => guild.installed).map((guild) => (
          <option key={guild.id} value={guild.id}>{guild.name}</option>
        ))}
      </select>
      {loading ? <Loader2 className="pointer-events-none absolute right-2 size-4 animate-spin text-muted" /> : <ChevronsUpDown className="pointer-events-none absolute right-2 size-4 text-muted" />}
    </div>
  )
}
