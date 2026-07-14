"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { Home, Loader2, Plus } from "lucide-react";
import { useState } from "react";
import { Logo } from "@/components/logo";
import { NAV_ITEMS, type NavItem } from "@/lib/nav";
import type { Permission } from "@/lib/rbac";
import { cn } from "@/lib/utils";
import type { ManagedGuild } from "@/lib/discord";
import { useToast } from "@/components/ui/toast";

const SECTION_LABELS: Record<string, string> = {
  main: "Moderation",
  account: "Workspace",
};

const SECTIONS = ["main", "account"] as const;

const BADGE_STYLES: Record<NonNullable<NavItem["badge"]>, string> = {
  NEW: "bg-success-soft text-success",
  UPDATE: "bg-info-soft text-info",
  PLUS: "bg-accent-soft text-accent",
};

function NavBadge({ badge }: { badge: NonNullable<NavItem["badge"]> }) {
  return (
    <span
      className={cn(
        "ml-auto rounded-full px-1.5 py-0.5 font-mono text-[0.5625rem] font-bold uppercase tracking-[0.08em]",
        BADGE_STYLES[badge],
      )}
    >
      {badge}
    </span>
  );
}

function NavigationLink({ item }: { item: NavItem }) {
  const pathname = usePathname();
  const Icon = item.icon;
  const isActive =
    item.href === "/dashboard"
      ? pathname === item.href
      : pathname.startsWith(item.href);

  return (
    <Link
      href={item.href}
      className={cn(
        "group relative flex h-10 items-center gap-3 rounded-xl border px-3 text-sm font-medium transition-all duration-200",
        isActive
          ? "border-accent-line bg-accent-soft text-foreground shadow-[0_14px_30px_-24px_var(--accent)]"
          : "border-transparent text-muted hover:border-border hover:bg-surface-2/70 hover:text-foreground",
      )}
    >
      <Icon
        size={16}
        strokeWidth={1.8}
        className={cn(
          "shrink-0 transition-colors",
          isActive ? "text-accent" : "text-muted-2 group-hover:text-foreground",
        )}
      />
      <span className="truncate">{item.label}</span>
      {item.badge && !isActive && <NavBadge badge={item.badge} />}
    </Link>
  );
}

function ServerRail({
  guilds,
  current,
}: {
  guilds: ManagedGuild[];
  current: ManagedGuild;
}) {
  const router = useRouter();
  const toast = useToast();
  const [loading, setLoading] = useState<string | null>(null);

  async function selectGuild(guildId: string) {
    if (guildId === current.id) return;
    setLoading(guildId);
    try {
      const response = await fetch("/api/guilds/select", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guildId }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok)
        throw new Error(body.error || "Could not switch servers");
      router.refresh();
    } catch (reason) {
      toast.error(
        "Server was not changed",
        reason instanceof Error ? reason.message : "Try again.",
      );
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="flex w-[72px] shrink-0 flex-col items-center border-r border-border bg-paper/65 py-4 backdrop-blur-xl">
      <Link
        href="/servers"
        aria-label="All servers"
        className="focus-ring grid size-11 place-items-center rounded-2xl border border-border bg-surface-2/80 text-muted transition-colors hover:border-accent-line hover:text-accent"
      >
        <Home className="size-4" />
      </Link>
      <div className="my-3 h-px w-8 bg-border" />
      <div className="flex flex-1 flex-col gap-2 overflow-y-auto px-2">
        {guilds
          .filter((guild) => guild.installed)
          .map((guild) => {
            const active = guild.id === current.id;
            return (
              <button
                key={guild.id}
                type="button"
                title={guild.name}
                aria-label={`Open ${guild.name}`}
                aria-current={active ? "page" : undefined}
                onClick={() => void selectGuild(guild.id)}
                className={cn(
                  "focus-ring group relative grid size-11 shrink-0 place-items-center overflow-visible rounded-2xl border transition-all duration-200",
                  active
                    ? "border-accent bg-accent-soft shadow-[0_0_28px_-10px_var(--accent)]"
                    : "border-border bg-surface hover:scale-[1.04] hover:border-accent-line",
                )}
              >
                {active ? (
                  <span className="absolute -left-[9px] h-7 w-1 rounded-r-full bg-accent" />
                ) : null}
                {loading === guild.id ? (
                  <Loader2 className="size-4 animate-spin text-accent" />
                ) : guild.iconUrl ? (
                  <Image
                    src={guild.iconUrl}
                    alt=""
                    width={44}
                    height={44}
                    unoptimized
                    className="size-full rounded-[inherit] object-cover"
                  />
                ) : (
                  <span className="font-display text-xs font-bold text-accent">
                    {guild.name.slice(0, 2).toUpperCase()}
                  </span>
                )}
              </button>
            );
          })}
        <Link
          href="/servers"
          aria-label="Add or manage servers"
          className="focus-ring grid size-11 shrink-0 place-items-center rounded-xl border border-dashed border-border-strong text-muted transition-colors hover:border-accent hover:bg-accent-soft hover:text-accent"
        >
          <Plus className="size-4" />
        </Link>
      </div>
    </div>
  );
}

export function Sidebar({
  permissions = [],
  guilds,
  currentGuild,
}: {
  permissions?: readonly Permission[];
  guilds: ManagedGuild[];
  currentGuild: ManagedGuild;
}) {
  const visible = NAV_ITEMS.filter((i) => permissions.includes(i.permission));

  return (
    <aside className="hidden h-screen w-[304px] shrink-0 border-r border-border bg-surface/82 shadow-[18px_0_60px_-40px_rgba(0,0,0,.8)] backdrop-blur-xl lg:flex">
      <ServerRail guilds={guilds} current={currentGuild} />
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Logo */}
        <div className="flex h-[72px] items-center border-b border-border px-5">
          <Link
            href="/dashboard"
            aria-label="Dashboard home"
            className="flex items-center"
          >
            <Logo />
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-6">
          {SECTIONS.map((section) => {
            const items = visible.filter((i) => i.section === section);
            if (!items.length) return null;
            return (
              <div key={section}>
                <p className="mb-2 px-3 font-mono text-[0.625rem] font-semibold uppercase tracking-[0.16em] text-muted-2">
                  {SECTION_LABELS[section]}
                </p>
                <div className="space-y-1">
                  {items.map((item) => (
                    <NavigationLink key={item.href} item={item} />
                  ))}
                </div>
              </div>
            );
          })}
        </nav>

        {/* Footer signal — live/online marker echoing Nova's green pip */}
        <div className="m-3 flex h-11 items-center gap-2 rounded-xl border border-border bg-surface-2/55 px-4">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-60" />
            <span className="relative inline-flex size-2 rounded-full bg-success" />
          </span>
          <span className="text-xs font-medium text-muted">
            All systems online
          </span>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
