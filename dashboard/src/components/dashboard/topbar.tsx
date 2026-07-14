"use client";

import { Menu } from "lucide-react";
import { CommandSearch } from "./command-search";
import { ThemeMenu } from "./theme-menu";
import { NotificationsMenu } from "./notifications-menu";
import { UserMenu } from "./user-menu";
import { GuildSwitcher } from "./guild-switcher";
import type { ManagedGuild } from "@/lib/discord";

export function Topbar({
  onOpenMobile,
  guilds,
  currentGuild,
}: {
  onOpenMobile: () => void;
  guilds: ManagedGuild[];
  currentGuild: ManagedGuild;
}) {
  return (
    <header className="sticky top-0 z-30 min-w-0 px-3 pt-3 sm:px-5">
      <div className="glass-panel flex h-14 min-w-0 items-center gap-2 rounded-2xl px-3 sm:gap-3 sm:px-4">
        <button
          onClick={onOpenMobile}
          className="focus-ring inline-flex size-9 items-center justify-center rounded-xl text-muted hover:bg-surface-2 lg:hidden"
          aria-label="Open menu"
        >
          <Menu className="size-5" />
        </button>

        <div className="lg:hidden">
          <GuildSwitcher guilds={guilds} current={currentGuild} />
        </div>
        <div className="hidden min-w-0 items-center gap-2 lg:flex">
          <span className="grid size-8 place-items-center rounded-xl border border-accent-line bg-accent-soft text-accent">
            <span className="font-display text-[0.625rem] font-bold">
              {currentGuild.name.slice(0, 2).toUpperCase()}
            </span>
          </span>
          <span className="max-w-40 truncate text-sm font-semibold text-foreground">
            {currentGuild.name}
          </span>
        </div>
        <div className="hidden min-w-0 md:block">
          <CommandSearch />
        </div>

        <div className="ml-auto flex shrink-0 items-center justify-end gap-1">
          <div className="hidden sm:block">
            <ThemeMenu />
          </div>
          <NotificationsMenu />
          <div className="mx-1 hidden h-6 w-px bg-border sm:block" />
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
