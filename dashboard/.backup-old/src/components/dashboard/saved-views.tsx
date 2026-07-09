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

  async function load() {
    try {
      const res = await fetch(`/api/saved-views?page=${page}`)
      const data = await res.json()
      setViews(data.views ?? [])
    } catch {
      setViews([])
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
      if (!res.ok) throw new Error()
      toast.success('View saved')
      setSaving(false)
      setName('')
      load()
    } catch {
      toast.error('Could not save view')
    } finally {
      setBusy(false)
    }
  }

  async function remove(id: string) {
    setViews((prev) => prev.filter((v) => v.id !== id))
    await fetch(`/api/saved-views/${id}`, { method: 'DELETE' }).catch(() => undefined)
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
          {views.length === 0 ? (
            <p className="px-2.5 py-2 text-sm text-muted">No saved views yet.</p>
          ) : (
            views.map((v) => (
              <div key={v.id} className="group flex items-center gap-1">
                <button
                  onClick={() => {
                    try {
                      onApply(JSON.parse(v.state))
                    } catch {
                      /* ignore malformed */
                    }
                  }}
                  className="focus-ring flex-1 rounded-lg px-2.5 py-2 text-left text-sm text-foreground hover:bg-surface-2"
                >
                  {v.name}
                </button>
                {canWrite && (
                  <button
                    onClick={() => remove(v.id)}
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
            placeholder="e.g. Enterprise churn risk"
            onKeyDown={(e) => e.key === 'Enter' && save()}
          />
        </Field>
      </Modal>
    </>
  )
}
