'use client'

import { useMemo, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { ChevronDown, Search, ShieldCheck, TerminalSquare } from 'lucide-react'
import { COMMAND_CATEGORIES, COMMANDS } from '@/lib/commands-catalog'
import { cn } from '@/lib/utils'

export function CommandsDirectory() {
  const searchParams = useSearchParams()
  const [category, setCategory] = useState<(typeof COMMAND_CATEGORIES)[number]>('All')
  const [query, setQuery] = useState(() => searchParams.get('q') || '')
  const [open, setOpen] = useState<string | null>(null)
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return COMMANDS.filter((command) => (
      (category === 'All' || command.category === category)
      && (!needle || `${command.name} ${command.description} ${command.usage}`.toLowerCase().includes(needle))
    ))
  }, [category, query])

  return (
    <div className="mx-auto w-full max-w-6xl px-4 pb-24 pt-16 sm:px-6 sm:pt-24">
      <header className="commands-reveal max-w-3xl">
        <p className="font-mono text-[0.6875rem] font-bold uppercase tracking-[0.18em] text-accent">Docket field manual</p>
        <h1 className="mt-4 font-display text-4xl font-semibold tracking-[-0.04em] text-foreground sm:text-6xl">One command directory.<br />No guessing.</h1>
        <p className="mt-5 max-w-2xl text-base leading-7 text-muted sm:text-lg">Search the commands that run Docket’s moderation, member reports, tickets, and server safety systems.</p>
      </header>

      <div className="commands-reveal mt-12 border-y border-border py-4 [animation-delay:80ms]">
        <div className="flex gap-2 overflow-x-auto pb-1">
          {COMMAND_CATEGORIES.map((item) => (
            <button key={item} type="button" onClick={() => setCategory(item)} className={cn('focus-ring shrink-0 rounded-md px-3 py-2 font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.08em] transition-colors', category === item ? 'bg-accent text-accent-foreground' : 'text-muted hover:bg-surface-2 hover:text-foreground')}>{item}</button>
          ))}
        </div>
      </div>

      <label className="commands-reveal mt-6 flex h-12 max-w-md items-center gap-3 rounded-lg border border-border-strong bg-surface px-4 [animation-delay:140ms] focus-within:border-accent-line">
        <Search className="size-4 text-muted-2" />
        <span className="sr-only">Search commands</span>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search commands…" className="min-w-0 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-2" />
        <span className="font-mono text-[0.625rem] text-muted-2">{filtered.length}</span>
      </label>

      <div className="commands-reveal mt-6 overflow-hidden rounded-xl border border-border bg-surface [animation-delay:200ms]">
        {filtered.length === 0 ? (
          <div className="px-6 py-16 text-center"><TerminalSquare className="mx-auto size-8 text-muted-2" /><p className="mt-4 font-medium text-foreground">No command matches that search.</p><button type="button" onClick={() => { setQuery(''); setCategory('All') }} className="mt-2 text-sm text-accent">Clear filters</button></div>
        ) : (
          <ul className="divide-y divide-border">
            {filtered.map((command) => {
              const key = `${command.category}:${command.name}`
              const expanded = open === key
              return (
                <li key={key}>
                  <button type="button" className="focus-ring flex w-full items-center gap-4 px-4 py-5 text-left transition-colors hover:bg-surface-2/60 sm:px-6" onClick={() => setOpen(expanded ? null : key)} aria-expanded={expanded}>
                    <span className="flex size-9 shrink-0 items-center justify-center rounded-md border border-accent-line bg-accent-soft text-accent"><TerminalSquare className="size-4" /></span>
                    <span className="min-w-0 flex-1"><span className="block font-display text-base font-semibold text-foreground">{command.name}</span><span className="mt-1 block truncate text-sm text-muted">{command.description}</span></span>
                    <span className="hidden rounded-md border border-border px-2 py-1 font-mono text-[0.625rem] uppercase tracking-[0.08em] text-muted sm:inline-flex">{command.category}</span>
                    <ChevronDown className={cn('size-4 shrink-0 text-muted transition-transform duration-200', expanded && 'rotate-180 text-accent')} />
                  </button>
                  {expanded ? (
                    <div className="command-detail grid gap-4 border-t border-border bg-surface-2/50 px-4 py-5 sm:grid-cols-[minmax(0,1fr)_15rem] sm:px-6">
                      <div><p className="text-sm leading-6 text-foreground">{command.description}</p><code className="mt-3 block overflow-x-auto rounded-md border border-border bg-bg px-3 py-2 font-mono text-xs text-accent">{command.usage}</code></div>
                      <div className="flex items-start gap-2 text-xs text-muted"><ShieldCheck className="mt-0.5 size-4 text-accent" /><span><strong className="block font-medium text-foreground">Who can use it</strong>{command.permission}</span></div>
                    </div>
                  ) : null}
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <section id="support" className="commands-reveal mt-10 flex flex-col gap-3 rounded-xl border border-accent-line bg-accent-soft p-6 [animation-delay:260ms] sm:flex-row sm:items-center sm:justify-between">
        <div><p className="font-display text-lg font-semibold text-foreground">Still not sure which command fits?</p><p className="mt-1 text-sm text-muted">Open the dashboard and use the command search, or run /help in Discord to return here.</p></div>
        <a href="/servers" className="focus-ring inline-flex h-10 shrink-0 items-center justify-center rounded-md bg-accent px-4 text-sm font-semibold text-accent-foreground">Open Docket</a>
      </section>
    </div>
  )
}
