import { redirect } from 'next/navigation'
import { Logo } from '@/components/logo'
import { ServerGrid, SignOutButton } from '@/components/servers/server-grid'
import { getCurrentUser } from '@/lib/session'
import { getManageableGuilds } from '@/lib/discord'

export const metadata = { title: 'Your servers' }

export default async function ServersPage() {
  const user = await getCurrentUser()
  if (!user) redirect('/login?next=/servers')
  const guilds = await getManageableGuilds(user.id)

  return (
    <div className="relative min-h-full overflow-hidden bg-bg">
      <div className="grid-texture pointer-events-none absolute inset-0 opacity-40 [mask-image:linear-gradient(to_bottom,black,transparent_75%)]" />
      <header className="relative border-b border-border bg-bg/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Logo />
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-muted sm:block">{user.name}</span>
            <SignOutButton />
          </div>
        </div>
      </header>
      <main className="relative mx-auto max-w-7xl px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <div className="mb-10 max-w-2xl">
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-mint">Server switchboard</p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">Where are you moderating?</h1>
          <p className="mt-3 text-base leading-7 text-muted">
            Open a connected server or install Aegis in another server you manage. Every dashboard view stays scoped to the server you choose.
          </p>
        </div>
        <ServerGrid guilds={guilds} />
      </main>
    </div>
  )
}
