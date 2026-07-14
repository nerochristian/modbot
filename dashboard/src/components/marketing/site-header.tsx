"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  CircleHelp,
  Command,
  LayoutDashboard,
  LogOut,
  Menu,
  X,
} from "lucide-react";
import { Logo } from "@/components/logo";
import { buttonVariants } from "@/components/ui/button";
import { Avatar } from "@/components/ui/avatar";
import {
  Dropdown,
  DropdownItem,
  DropdownLabel,
  DropdownMenu,
  DropdownSeparator,
  DropdownTrigger,
} from "@/components/ui/dropdown";
import { cn } from "@/lib/utils";

const NAV = [
  { label: "How it works", href: "/#pipeline" },
  { label: "Commands", href: "/commands" },
  { label: "Support", href: "/commands#support" },
];

type HeaderUser = {
  name: string;
  email: string;
  avatarUrl: string | null;
  avatarColor: string;
};

export function SiteHeader({ user }: { user: HeaderUser | null }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  async function logout() {
    const response = await fetch("/api/auth/logout", { method: "POST" });
    if (response.ok) {
      router.push("/");
      router.refresh();
    }
  }

  return (
    <header
      className={cn(
        "sticky top-0 z-50 px-3 pt-3 transition-all sm:px-5",
        scrolled ? "pb-2" : "pb-0",
      )}
    >
      <div
        className={cn(
          "mx-auto flex h-16 max-w-7xl items-center justify-between rounded-2xl border px-4 transition-all sm:px-5",
          scrolled
            ? "border-border bg-surface/88 shadow-2xl shadow-black/20 backdrop-blur-xl"
            : "border-white/8 bg-surface/45 backdrop-blur-md",
        )}
      >
        <Link href="/" className="focus-ring rounded-lg">
          <Logo />
        </Link>

        <nav className="hidden items-center gap-1 rounded-xl border border-border bg-surface-2/55 p-1 md:flex">
          {NAV.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="focus-ring rounded-lg px-3.5 py-2 text-sm font-medium text-muted transition-colors hover:bg-surface hover:text-foreground"
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {user ? (
            <Dropdown>
              <DropdownTrigger>
                <span className="focus-ring flex items-center gap-2 rounded-xl border border-border bg-surface-2/70 p-1.5 pr-3 transition-colors hover:border-accent-line hover:bg-accent-soft">
                  <Avatar
                    name={user.name}
                    src={user.avatarUrl}
                    color={user.avatarColor}
                    size="sm"
                  />
                  <span className="hidden max-w-28 truncate text-sm font-semibold text-foreground sm:block">
                    {user.name}
                  </span>
                </span>
              </DropdownTrigger>
              <DropdownMenu align="end" className="w-64">
                <DropdownLabel>
                  <span className="block truncate text-foreground">
                    {user.name}
                  </span>
                  <span className="block truncate font-normal text-muted-2">
                    {user.email}
                  </span>
                </DropdownLabel>
                <DropdownSeparator />
                <Link href="/dashboard">
                  <DropdownItem icon={LayoutDashboard}>Dashboard</DropdownItem>
                </Link>
                <Link href="/commands">
                  <DropdownItem icon={Command}>Commands</DropdownItem>
                </Link>
                <Link href="/commands#support">
                  <DropdownItem icon={CircleHelp}>Support</DropdownItem>
                </Link>
                <DropdownSeparator />
                <DropdownItem
                  icon={LogOut}
                  destructive
                  onClick={() => void logout()}
                >
                  Sign out
                </DropdownItem>
              </DropdownMenu>
            </Dropdown>
          ) : (
            <>
              <Link
                href="/login"
                className={cn(
                  buttonVariants({ variant: "ghost", size: "sm" }),
                  "hidden sm:inline-flex",
                )}
              >
                Sign in
              </Link>
              <Link
                href="/register"
                className={buttonVariants({ variant: "primary", size: "sm" })}
              >
                Open console
              </Link>
            </>
          )}
          <button
            onClick={() => setOpen((v) => !v)}
            className="focus-ring inline-flex size-9 items-center justify-center rounded-md border border-border text-foreground md:hidden"
            aria-label="Toggle menu"
            aria-expanded={open}
          >
            {open ? <X className="size-5" /> : <Menu className="size-5" />}
          </button>
        </div>
      </div>

      {open && (
        <div className="mx-auto mt-2 max-w-7xl rounded-2xl border border-border bg-surface/95 shadow-2xl backdrop-blur-xl md:hidden">
          <nav className="mx-auto flex max-w-6xl flex-col gap-1 p-4">
            {NAV.map((item) => (
              <a
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className="rounded-lg px-3 py-2.5 text-sm font-medium text-foreground hover:bg-surface-2"
              >
                {item.label}
              </a>
            ))}
            {!user && (
              <Link
                href="/login"
                className="rounded-lg px-3 py-2.5 text-sm font-medium text-foreground hover:bg-surface-2"
              >
                Sign in
              </Link>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
