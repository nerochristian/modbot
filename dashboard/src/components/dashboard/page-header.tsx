export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
}: {
  title: React.ReactNode
  description?: string
  /** Optional mono records-marker shown above the title (e.g. "CASELOAD"). */
  eyebrow?: string
  actions?: React.ReactNode
}) {
  return (
    <div className="mb-6 border-b border-border pb-5">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div className="min-w-0">
          {eyebrow && (
            <p className="mb-1.5 font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">
              {eyebrow}
            </p>
          )}
          <h1 className="font-display text-[1.75rem] font-semibold leading-none tracking-tight text-foreground">
            {title}
          </h1>
          {description && <p className="mt-2 max-w-2xl text-sm text-muted">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  )
}
