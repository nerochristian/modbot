'use client'

import { useState } from 'react'
import { Check, Download, CreditCard } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Table, THead, TBody, TR, TH, TD } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge, statusTone } from '@/components/ui/badge'
import { SegmentedControl } from '@/components/ui/segmented'
import { ConfirmDialog } from '@/components/ui/modal'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, ErrorState } from '@/components/ui/empty-state'
import { useToast } from '@/components/ui/toast'
import { useConfigStore } from '@/lib/store'
import { useApi } from '@/lib/use-api'
import { downloadFile } from '@/lib/export-client'
import { formatCurrency } from '@/lib/utils'
import { format } from 'date-fns'
import { cn } from '@/lib/utils'

type Subscription = {
  plan: string
  status: string
  seats: number
  interval: string
  amount: number
  currentPeriodEnd: string
  cancelAtPeriodEnd: boolean
}
type Invoice = { id: string; number: string; amount: number; status: string; issuedAt: string }
type BillingData = { subscription: Subscription | null; invoices: Invoice[] }

const PLANS = [
  { key: 'starter', name: 'Free', price: 0, features: ['1 server', 'Core automod', 'Basic cases', 'Community support'] },
  { key: 'pro', name: 'Pro', price: 999, features: ['Unlimited automod rules', 'Full case system', 'Appeals workflow', 'Roles & permissions'] },
  { key: 'enterprise', name: 'Premium', price: 2999, features: ['Everything in Pro', 'Multi-server', 'Raid shield & AI scoring', 'SSO & audit exports'] },
]

export function BillingClient() {
  const toast = useToast()
  const canWrite = useConfigStore((s) => s.can('billing.write'))
  const { data, loading, error, refetch } = useApi<BillingData>('/api/billing')
  const [interval, setInterval] = useState<'month' | 'year'>('month')
  const [busy, setBusy] = useState<string | null>(null)
  const [cancelOpen, setCancelOpen] = useState(false)

  async function mutate(payload: Record<string, unknown>, successMsg: string, key: string) {
    setBusy(key)
    try {
      const res = await fetch('/api/billing', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error()
      toast.success(successMsg)
      setCancelOpen(false)
      refetch()
    } catch {
      toast.error('Something went wrong')
    } finally {
      setBusy(null)
    }
  }

  function downloadInvoice(inv: Invoice) {
    const receipt = [
      'NEBULA, INC. — RECEIPT',
      '========================',
      `Invoice:   ${inv.number}`,
      `Date:      ${format(new Date(inv.issuedAt), 'PPP')}`,
      `Status:    ${inv.status.toUpperCase()}`,
      `Amount:    ${formatCurrency(inv.amount)}`,
      '',
      'Thank you for your business.',
    ].join('\n')
    downloadFile(`${inv.number}.txt`, receipt, 'text/plain')
  }

  if (error && !data) {
    return (
      <>
        <PageHeader title="Billing" />
        <Card>
          <ErrorState onRetry={refetch} description={error} />
        </Card>
      </>
    )
  }

  if (loading && !data) {
    return (
      <>
        <PageHeader title="Billing" description="Manage your subscription, payment method, and invoices." />
        <div className="space-y-4">
          <Card className="p-5">
            <Skeleton className="h-24 w-full" />
          </Card>
          <Card className="p-5">
            <Skeleton className="h-48 w-full" />
          </Card>
        </div>
      </>
    )
  }

  const sub = data?.subscription ?? null

  return (
    <>
      <PageHeader title="Billing" description="Manage your subscription, payment method, and invoices." />

      {!sub ? (
        <Card>
          <EmptyState
            icon={CreditCard}
            title="No active subscription"
            description={canWrite ? 'Choose a plan below to get started.' : 'Ask an admin to set up a subscription.'}
          />
        </Card>
      ) : (
        <Card className="mb-4">
          <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold capitalize text-foreground">{sub.plan} plan</h2>
                <Badge tone={statusTone(sub.status)} dot>
                  {sub.status}
                </Badge>
                {sub.cancelAtPeriodEnd && <Badge tone="warning">Cancels at period end</Badge>}
              </div>
              <p className="mt-1 text-sm text-muted">
                {formatCurrency(sub.amount)} / month · {sub.seats} seats ·{' '}
                {sub.cancelAtPeriodEnd ? 'Ends' : 'Renews'} {format(new Date(sub.currentPeriodEnd), 'MMM d, yyyy')}
              </p>
            </div>
            {canWrite && (
              <div className="flex items-center gap-2">
                {sub.cancelAtPeriodEnd ? (
                  <Button variant="outline" loading={busy === 'reactivate'} onClick={() => mutate({ cancelAtPeriodEnd: false }, 'Subscription reactivated', 'reactivate')}>
                    Reactivate
                  </Button>
                ) : (
                  <Button variant="outline" onClick={() => setCancelOpen(true)}>
                    Cancel plan
                  </Button>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Usage */}
      {sub && (
        <Card className="mb-4">
          <CardHeader>
            <CardTitle>Usage this period</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-5 pt-4 sm:grid-cols-3">
            <UsageMeter label="Seats" used={18} total={sub.seats} />
            <UsageMeter label="Events" used={612000} total={1000000} format={(n) => `${(n / 1000).toFixed(0)}k`} />
            <UsageMeter label="API requests" used={284000} total={500000} format={(n) => `${(n / 1000).toFixed(0)}k`} />
          </CardContent>
        </Card>
      )}

      {/* Plans */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Plans</CardTitle>
          <SegmentedControl
            size="sm"
            aria-label="Billing interval"
            value={interval}
            onChange={setInterval}
            options={[
              { label: 'Monthly', value: 'month' },
              { label: 'Annual −20%', value: 'year' },
            ]}
          />
        </CardHeader>
        <CardContent className="grid gap-4 pt-4 lg:grid-cols-3">
          {PLANS.map((p) => {
            const current = sub?.plan === p.key
            const price = interval === 'year' ? Math.round(p.price * 0.8) : p.price
            return (
              <div
                key={p.key}
                className={cn(
                  'flex flex-col rounded-xl border p-5',
                  current ? 'border-accent ring-1 ring-accent' : 'border-border',
                )}
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-foreground">{p.name}</h3>
                  {current && <Badge tone="accent">Current</Badge>}
                </div>
                <p className="mt-3 text-2xl font-bold text-foreground">
                  {formatCurrency(price)}
                  <span className="text-sm font-normal text-muted">/mo</span>
                </p>
                <ul className="mt-4 flex-1 space-y-2">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-muted">
                      <Check className="size-4 text-success" />
                      {f}
                    </li>
                  ))}
                </ul>
                {canWrite && (
                  <Button
                    variant={current ? 'secondary' : 'primary'}
                    className="mt-5 w-full"
                    disabled={current}
                    loading={busy === p.key}
                    onClick={() => mutate({ plan: p.key, interval }, `Switched to ${p.name}`, p.key)}
                  >
                    {current ? 'Current plan' : 'Switch plan'}
                  </Button>
                )}
              </div>
            )
          })}
        </CardContent>
      </Card>

      {/* Payment method */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Payment method</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between pt-4">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-12 items-center justify-center rounded-md bg-surface-2 text-xs font-bold text-foreground">
              VISA
            </span>
            <div>
              <p className="text-sm font-medium text-foreground">•••• •••• •••• 4242</p>
              <p className="text-xs text-muted">Expires 08 / 2028</p>
            </div>
          </div>
          {canWrite && (
            <Button variant="outline" size="sm" onClick={() => toast.info('Payment method', 'This is a demo — no real card is stored.')}>
              Update
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Invoices */}
      <Card>
        <CardHeader>
          <CardTitle>Invoices</CardTitle>
        </CardHeader>
        {data && data.invoices.length > 0 ? (
          <Table>
            <THead>
              <TR>
                <TH>Invoice</TH>
                <TH>Date</TH>
                <TH>Amount</TH>
                <TH>Status</TH>
                <TH className="text-right">Receipt</TH>
              </TR>
            </THead>
            <TBody>
              {data.invoices.map((inv) => (
                <TR key={inv.id} className="hover:bg-surface-2/50">
                  <TD className="font-medium text-foreground">{inv.number}</TD>
                  <TD className="text-muted">{format(new Date(inv.issuedAt), 'MMM d, yyyy')}</TD>
                  <TD className="tabular-nums">{formatCurrency(inv.amount)}</TD>
                  <TD>
                    <Badge tone={statusTone(inv.status)}>{inv.status}</Badge>
                  </TD>
                  <TD className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => downloadInvoice(inv)}>
                      <Download className="size-4" />
                    </Button>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        ) : (
          <EmptyState title="No invoices yet" description="Invoices will appear here after your first payment." />
        )}
      </Card>

      <ConfirmDialog
        open={cancelOpen}
        onClose={() => setCancelOpen(false)}
        onConfirm={() => mutate({ cancelAtPeriodEnd: true }, 'Subscription will cancel at period end', 'cancel')}
        title="Cancel subscription?"
        description="Your plan stays active until the end of the current billing period, then it won't renew."
        confirmLabel="Cancel subscription"
        destructive
        loading={busy === 'cancel'}
      />
    </>
  )
}

function UsageMeter({
  label,
  used,
  total,
  format: fmt = (n: number) => String(n),
}: {
  label: string
  used: number
  total: number
  format?: (n: number) => string
}) {
  const pct = Math.min(100, Math.round((used / total) * 100))
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-sm">
        <span className="text-muted">{label}</span>
        <span className="font-medium text-foreground">
          {fmt(used)} / {fmt(total)}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-surface-2">
        <div
          className={cn('h-full rounded-full', pct > 90 ? 'bg-danger' : pct > 75 ? 'bg-warning' : 'bg-accent')}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
