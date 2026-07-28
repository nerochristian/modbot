"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { Logo } from "@/components/logo";
import { MotionRoot } from "@/components/motion/primitives";
import { Topbar } from "./topbar";
import { Sidebar } from "./sidebar";
import { NAV_ITEMS } from "@/lib/nav";
import type { Permission } from "@/lib/rbac";
import { cn } from "@/lib/utils";
import type { ManagedGuild } from "@/lib/discord";

const SECTION_LABELS: Record<string, string> = {
  main: "Moderation",
  account: "Workspace",
};

function MobileDrawer({
  open,
  onClose,
  permissions,
}: {
  open: boolean;
  onClose: () => void;
  permissions: Permission[];
}) {
  const pathname = usePathname();
  if (!open || typeof document === "undefined") return null;
  const visible = NAV_ITEMS.filter((i) => permissions.includes(i.permission));
  const sections = ["main", "account"] as const;

  return createPortal(
    <div className="fixed inset-0 z-[80] lg:hidden">
      <div
        className="absolute inset-0"
        style={{ background: "var(--overlay)" }}
        onClick={onClose}
      />
      <div className="animate-fade-in absolute inset-y-0 left-0 flex w-72 flex-col border-r border-border bg-surface">
        <div className="flex h-16 items-center justify-between border-b border-border px-4">
          <Logo />
          <button
            onClick={onClose}
            className="focus-ring inline-flex size-8 items-center justify-center rounded-md text-muted hover:bg-surface-2"
            aria-label="Close menu"
          >
            <X className="size-5" />
          </button>
        </div>
        <nav className="flex-1 space-y-5 overflow-y-auto p-3">
          {sections.map((section) => {
            const items = visible.filter((i) => i.section === section);
            if (!items.length) return null;
            return (
              <div key={section}>
                <p className="mb-2 px-2 font-mono text-[0.625rem] font-semibold uppercase tracking-[0.16em] text-muted-2">
                  {SECTION_LABELS[section]}
                </p>
                <ul className="space-y-0.5">
                  {items.map((item) => {
                    const active =
                      item.href === "/dashboard"
                        ? pathname === item.href
                        : pathname.startsWith(item.href);
                    return (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          onClick={onClose}
                          className={cn(
                            "flex items-center gap-3 rounded-md px-2.5 py-2 text-sm font-medium",
                            active
                              ? "bg-accent-soft text-accent"
                              : "text-muted hover:bg-surface-2 hover:text-foreground",
                          )}
                        >
                          <item.icon className="size-4.5" />
                          {item.label}
                          {item.badge && (
                            <span className="ml-auto rounded-full bg-accent-soft px-1.5 py-0.5 font-mono text-[0.5625rem] font-bold uppercase tracking-[0.08em] text-accent">
                              {item.badge}
                            </span>
                          )}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </nav>
      </div>
    </div>,
    document.body,
  );
}

export function DashboardShell({
  permissions,
  guilds,
  currentGuild,
  children,
}: {
  permissions: Permission[];
  guilds: ManagedGuild[];
  currentGuild: ManagedGuild;
  children: React.ReactNode;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <MotionRoot>
    <div className="modern-shell flex min-h-screen">
      <Sidebar
        permissions={permissions}
        guilds={guilds}
        currentGuild={currentGuild}
      />
      <MobileDrawer
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        permissions={permissions}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          onOpenMobile={() => setMobileOpen(true)}
          guilds={guilds}
          currentGuild={currentGuild}
        />
        <main className="flex-1 px-4 pb-10 pt-7 sm:px-6 lg:px-8 lg:pt-9">
          <div className="dashboard-stage mx-auto w-full max-w-[1440px]">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
