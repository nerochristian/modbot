'use client'

import { Menu } from 'lucide-react'
import { CommandSearch } from './command-search'
import { ThemeMenu } from './theme-menu'
import { NotificationsMenu } from './notifications-menu'
import { UserMenu } from './user-menu'
import { GuildSwitcher } from './guild-switcher'
import type { ManagedGuild } from '@/lib/discord'

export function Topbar({
  onOpenMobile,
  guilds,
  currentGuild,
}: {
  onOpenMobile: () => void
  guilds: ManagedGuild[]
  currentGuild: ManagedGuild
}) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-bg/80 px-4 backdrop-blur-md sm:px-6">
      <button
        onClick={onOpenMobile}
        className="focus-ring inline-flex size-9 items-center justify-center rounded-lg text-muted hover:bg-surface-2 lg:hidden"
        aria-label="Open menu"
      >
        <Menu className="size-5" />
      </button>

      <GuildSwitcher guilds={guilds} current={currentGuild} />
      <CommandSearch />

      <div className="flex flex-1 items-center justify-end gap-1">
        <ThemeMenu />
        <NotificationsMenu />
        <div className="mx-1 hidden h-6 w-px bg-border sm:block" />
        <UserMenu />
      </div>
    </header>
  )
}
