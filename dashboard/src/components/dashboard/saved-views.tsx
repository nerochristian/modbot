'use client'

import { useEffect, useState } from 'react'
import { Bookmark, Plus, Trash2 } from 'lucide-react'
import {
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownLabel,
  DropdownSeparator,
} from '@/components/ui/dropdown'
import { Modal } from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/input'
import { useToast } from '@/components/ui/toast'
import { useConfigStore } from '@/lib/store'

type SavedView = { id: string; name: string; page: string; state: string }

export function SavedViews({
  page,
  currentState,
  onApply,
}: {
  page: string
  currentState: Record<string, unknown>
  onApply: (state: Record<string, unknown>) => void
}) {
  const toast = useToast()
  const canWrite = useConfigStore((s) => s.can('config.write'))
  const [views, setViews] = useState<SavedView[]>([])
  const [saving, setSaving] = useState(false)
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [removing, setRemoving] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    try {
      const res = await fetch(`/api/saved-views?page=${page}`)
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.error ?? 'Could not load saved views')
      setViews(data.views ?? [])
      setLoadError(null)
    } catch (reason) {
      setLoadError(reason instanceof Error ? reason.message : 'Could not load saved views')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page])

  async function save() {
    if (!name.trim()) return
    setBusy(true)
    try {
      const res = await fetch('/api/saved-views', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), page, state: currentState }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.error ?? 'Could not save view')
      toast.success('View saved')
      setSaving(false)
      setName('')
      await load()
    } catch (reason) {
      toast.error(
        'View was not saved',
        reason instanceof Error ? reason.message : 'Try again in a moment.',
      )
    } finally {
      setBusy(false)
    }
  }

  async function remove(id: string) {
    setRemoving(id)
    try {
      const response = await fetch(`/api/saved-views/${id}`, { method: 'DELETE' })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(body.error ?? 'Could not delete saved view')
      setViews((prev) => prev.filter((view) => view.id !== id))
      toast.success('Saved view deleted')
    } catch (reason) {
      toast.error(
        'View was not deleted',
        reason instanceof Error ? reason.message : 'Try again in a moment.',
      )
    } finally {
      setRemoving(null)
    }
  }

  return (
    <>
      <Dropdown>
        <DropdownTrigger>
          <span className="focus-ring inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-surface px-3 text-sm font-medium text-foreground hover:bg-surface-2">
            <Bookmark className="size-4" />
            <span className="hidden sm:inline">Views</span>
          </span>
        </DropdownTrigger>
        <DropdownMenu>
          <DropdownLabel>Saved views</DropdownLabel>
          {loading ? (
            <p className="px-2.5 py-2 text-sm text-muted">Loading saved views…</p>
          ) : loadError ? (
            <div className="space-y-2 px-2.5 py-2">
              <p className="text-sm text-danger">{loadError}</p>
              <button className="text-xs font-medium text-accent hover:underline" onClick={load}>
                Try again
              </button>
            </div>
          ) : views.length === 0 ? (
            <p className="px-2.5 py-2 text-sm text-muted">No saved views yet.</p>
          ) : (
            views.map((v) => (
              <div key={v.id} className="group flex items-center gap-1">
                  <button
                    onClick={() => {
                      try {
                        onApply(JSON.parse(v.state))
                      } catch {
                        toast.error('This saved view is invalid')
                      }
                  }}
                  className="focus-ring flex-1 rounded-lg px-2.5 py-2 text-left text-sm text-foreground hover:bg-surface-2"
                >
                  {v.name}
                </button>
                {canWrite && (
                  <button
                    onClick={() => remove(v.id)}
                    disabled={removing === v.id}
                    className="focus-ring rounded-md p-1.5 text-muted-2 opacity-0 transition-opacity hover:text-danger group-hover:opacity-100"
                    aria-label={`Delete ${v.name}`}
                  >
                    <Trash2 className="size-4" />
                  </button>
                )}
              </div>
            ))
          )}
          {canWrite && (
            <>
              <DropdownSeparator />
              <button
                onClick={() => setSaving(true)}
                className="focus-ring flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm font-medium text-accent hover:bg-surface-2"
              >
                <Plus className="size-4" />
                Save current view
              </button>
            </>
          )}
        </DropdownMenu>
      </Dropdown>

      <Modal
        open={saving}
        onClose={() => setSaving(false)}
        title="Save view"
        description="Save the current filters, sort, and search as a reusable view."
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setSaving(false)}>
              Cancel
            </Button>
            <Button onClick={save} loading={busy}>
              Save view
            </Button>
          </>
        }
      >
        <Field label="View name" htmlFor="view-name">
          <Input
            id="view-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Critical watchlist"
            onKeyDown={(e) => e.key === 'Enter' && save()}
          />
        </Field>
      </Modal>
    </>
  )
}
