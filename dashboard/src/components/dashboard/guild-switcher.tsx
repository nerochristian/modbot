'use client'

import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { ChevronsUpDown, Loader2, ServerCog } from 'lucide-react'
import { useState } from 'react'
import type { ManagedGuild } from '@/lib/discord'

export function GuildSwitcher({ guilds, current }: { guilds: ManagedGuild[]; current: ManagedGuild }) {
  const router = useRouter()
  const [loading, setLoading] = useState(false)

  return (
    <div className="relative flex h-9 items-center rounded-lg border border-border bg-surface shadow-sm">
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
          const response = await fetch('/api/guilds/select', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ guildId: event.target.value }),
          })
          if (response.ok) router.refresh()
          setLoading(false)
        }}
        className="h-full max-w-44 appearance-none bg-transparent py-0 pl-2 pr-8 text-sm font-medium text-foreground outline-none disabled:opacity-60"
      >
        {guilds.filter((guild) => guild.installed).map((guild) => (
          <option key={guild.id} value={guild.id}>{guild.name}</option>
        ))}
      </select>
      {loading ? <Loader2 className="pointer-events-none absolute right-2 size-4 animate-spin text-muted" /> : <ChevronsUpDown className="pointer-events-none absolute right-2 size-4 text-muted" />}
    </div>
  )
}
