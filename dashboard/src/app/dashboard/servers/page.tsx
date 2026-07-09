'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Plus, ExternalLink, Shield } from 'lucide-react'

interface Guild {
  id: string
  name: string
  icon: string | null
  memberCount: number | null
  botInGuild: boolean
  isOwner: boolean
}

export default function ServersPage() {
  const router = useRouter()
  const [guilds, setGuilds] = useState<Guild[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadGuilds() {
      try {
        const res = await fetch('/api/guilds')
        if (!res.ok) {
          if (res.status === 401) {
            router.push('/login')
            return
          }
          throw new Error('Failed to load servers')
        }
        const data = await res.json()
        setGuilds(data)
      } catch (e: any) {
        setError(e.message || 'Failed to load servers')
      } finally {
        setLoading(false)
      }
    }
    loadGuilds()
  }, [router])

  const handleAddBot = (guildId: string) => {
    const clientId = process.env.NEXT_PUBLIC_DISCORD_CLIENT_ID || ''
    const inviteUrl = `https://discord.com/api/oauth2/authorize?client_id=${clientId}&permissions=8&scope=bot%20applications.commands&guild_id=${guildId}`
    window.open(inviteUrl, '_blank')
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-accent border-t-transparent" />
          <p className="mt-4 text-sm text-muted">Loading your servers…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-md py-12 text-center">
        <Shield className="mx-auto mb-4 size-12 text-danger" />
        <h1 className="text-xl font-semibold">Unable to load servers</h1>
        <p className="mt-2 text-sm text-muted">{error}</p>
        <Button onClick={() => window.location.reload()} className="mt-6">
          Try again
        </Button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Your Servers</h1>
          <p className="mt-1 text-muted">Select a server to manage or add the bot where you have admin access.</p>
        </div>
        <div className="text-xs text-muted-2">
          {guilds.length} server{guilds.length === 1 ? '' : 's'} with admin access
        </div>
      </div>

      {guilds.length === 0 && (
        <Card className="p-10 text-center">
          <p className="text-muted">You don’t have admin access to any Discord servers yet.</p>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {guilds.map((guild) => (
          <Card key={guild.id} className="group flex items-center gap-4 p-5 transition hover:border-accent/50">
            <div className="flex size-14 shrink-0 items-center justify-center overflow-hidden rounded-xl border bg-surface">
              {guild.icon ? (
                <img src={guild.icon} alt="" className="size-full object-cover" />
              ) : (
                <span className="text-2xl font-semibold text-muted-2">
                  {guild.name.slice(0, 2).toUpperCase()}
                </span>
              )}
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <div className="truncate font-semibold">{guild.name}</div>
                {guild.isOwner && (
                  <span className="rounded bg-accent/10 px-1.5 py-px text-[10px] font-medium text-accent">Owner</span>
                )}
              </div>
              <div className="text-xs text-muted">
                {guild.memberCount ? `${guild.memberCount.toLocaleString()} members` : '—'}
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-2">
              {guild.botInGuild ? (
                <Button
                  variant="primary"
                  onClick={() => router.push(`/dashboard?guild=${guild.id}`)}
                >
                  Manage
                  <ExternalLink className="size-4" />
                </Button>
              ) : (
                <Button
                  variant="outline"
                  onClick={() => handleAddBot(guild.id)}
                  className="gap-2 border-accent/60 text-accent hover:bg-accent hover:text-white"
                >
                  <Plus className="size-4" />
                  Add Bot
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>

      <p className="mt-8 text-center text-xs text-muted-2">
        Only servers where you have the Administrator permission or are the owner are shown.
      </p>
    </div>
  )
}
