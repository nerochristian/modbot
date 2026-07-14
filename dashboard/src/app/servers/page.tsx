import { redirect } from "next/navigation";
import { Logo } from "@/components/logo";
import { ServerGrid, SignOutButton } from "@/components/servers/server-grid";
import { getCurrentUser } from "@/lib/session";
import { getManageableGuilds } from "@/lib/discord";

export const metadata = { title: "Your servers" };

export default async function ServersPage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login?next=/servers");
  const guilds = await getManageableGuilds(user.id);

  return (
    <div className="relative min-h-full overflow-hidden bg-bg">
      <div className="soft-grid pointer-events-none absolute inset-0 opacity-35 [mask-image:linear-gradient(to_bottom,black,transparent_72%)]" />
      <div className="blue-orb pointer-events-none absolute -right-40 -top-40 size-[32rem] rounded-full opacity-40" />
      <header className="relative px-3 pt-3 sm:px-5">
        <div className="glass-panel mx-auto flex h-16 max-w-7xl items-center justify-between rounded-2xl px-4 sm:px-5">
          <Logo />
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-muted sm:block">
              {user.name}
            </span>
            <SignOutButton />
          </div>
        </div>
      </header>
      <main className="relative mx-auto max-w-7xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
        <div className="mb-12 max-w-3xl">
          <p className="text-sm font-semibold text-accent">Your workspaces</p>
          <h1 className="mt-3 font-display text-4xl font-semibold tracking-[-0.04em] text-foreground sm:text-5xl">
            Choose a server to manage.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-muted sm:text-lg">
            Open a connected server or install Docket in another server you
            manage. Every dashboard view stays scoped to the server you choose.
          </p>
        </div>
        <ServerGrid guilds={guilds} />
      </main>
    </div>
  );
}
