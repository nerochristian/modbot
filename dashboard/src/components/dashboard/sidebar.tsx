"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Server,
  Headphones,
  Sparkles,
  Settings,
  UserRoundCog,
  BadgeCheck,
  MessageSquareCode,
  Clock3,
  ShieldCheck,
  Bot,
  ScrollText,
} from "lucide-react";

const primaryNavigation = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    label: "Servers",
    href: "/dashboard/servers",
    icon: Server,
  },
  {
    label: "Support",
    href: "/dashboard/support",
    icon: Headphones,
  },
  {
    label: "Premium",
    href: "/dashboard/premium",
    icon: Sparkles,
  },
];

const botSettingsNavigation = [
  {
    label: "Button Roles",
    href: "/dashboard/button-roles",
    icon: UserRoundCog,
  },
  {
    label: "Verification / Greetings",
    href: "/dashboard/verification",
    icon: BadgeCheck,
  },
  {
    label: "Custom Commands",
    href: "/dashboard/custom-commands",
    icon: MessageSquareCode,
  },
  {
    label: "Timed Messages",
    href: "/dashboard/timed-messages",
    icon: Clock3,
  },
  {
    label: "Command Moderation",
    href: "/dashboard/command-moderation",
    icon: ShieldCheck,
  },
  {
    label: "Auto Moderation",
    href: "/dashboard/auto-moderation",
    icon: Bot,
  },
  {
    label: "Audit Logging",
    href: "/dashboard/audit-logging",
    icon: ScrollText,
  },
];

type NavigationItem = {
  label: string;
  href: string;
  icon: React.ElementType;
};

function NavigationLink({ item }: { item: NavigationItem }) {
  const pathname = usePathname();
  const Icon = item.icon;

  const isActive =
    pathname === item.href ||
    (item.href !== "/dashboard" && pathname.startsWith(item.href));

  return (
    <Link
      href={item.href}
      className={[
        "group flex h-10 items-center gap-3 rounded-lg px-3",
        "text-sm font-medium transition-all duration-200",
        isActive
          ? "bg-violet-600 text-white shadow-[0_8px_25px_rgba(124,58,237,0.28)]"
          : "text-zinc-500 hover:bg-white/[0.04] hover:text-zinc-200",
      ].join(" ")}
    >
      <Icon
        size={16}
        strokeWidth={1.8}
        className={
          isActive
            ? "text-white"
            : "text-zinc-600 transition-colors group-hover:text-zinc-300"
        }
      />

      <span className="truncate">{item.label}</span>
    </Link>
  );
}

export function Sidebar({ permissions }: { permissions?: readonly string[] }) {
  void permissions;
  return (
    <aside className="flex h-screen w-[250px] shrink-0 flex-col border-r border-white/[0.06] bg-[#111019]">
      {/* Logo */}
      <div className="flex h-24 items-center px-6">
        <Link
          href="/dashboard"
          aria-label="Dashboard home"
          className="flex items-center gap-3"
        >
          <div className="relative grid size-11 place-items-center rounded-full border border-violet-500/20 bg-[#181622] shadow-lg">
            <Bot
              size={24}
              strokeWidth={1.7}
              className="text-cyan-300"
            />

            <span className="absolute -right-0.5 -top-0.5 size-2.5 rounded-full bg-violet-500 ring-2 ring-[#111019]" />
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 pb-6">
        <div className="space-y-1">
          {primaryNavigation.map((item) => (
            <NavigationLink key={item.href} item={item} />
          ))}
        </div>

        <div className="-mx-3 my-5 border-t border-white/[0.06]" />

        <div>
          <div className="mb-2 flex items-center gap-2 px-3">
            <Settings size={15} className="text-zinc-600" />

            <p className="text-xs font-semibold text-zinc-500">
              Bot Settings
            </p>
          </div>

          <div className="space-y-1">
            {botSettingsNavigation.map((item) => (
              <NavigationLink key={item.href} item={item} />
            ))}
          </div>
        </div>
      </nav>

      {/* Empty footer area */}
      <div className="h-12 border-t border-white/[0.06]" />
    </aside>
  );
}

export default Sidebar
