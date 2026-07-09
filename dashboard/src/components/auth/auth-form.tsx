'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Field, Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/toast'

type Mode = 'login' | 'register'

const DEMO_ACCOUNTS = [
  { label: 'Admin', email: 'admin@aegisbot.gg' },
  { label: 'Manager', email: 'manager@aegisbot.gg' },
  { label: 'Viewer', email: 'viewer@aegisbot.gg' },
]

export function AuthForm({ mode, next }: { mode: Mode; next: string }) {
  const router = useRouter()
  const toast = useToast()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [errors, setErrors] = useState<Record<string, string>>({})

  async function submit(payload: { name?: string; email: string; password: string }) {
    setLoading(true)
    setErrors({})
    try {
      const res = await fetch(`/api/auth/${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      if (!res.ok) {
        if (data.issues) {
          const fieldErrors: Record<string, string> = {}
          for (const issue of data.issues) fieldErrors[issue.path[0]] = issue.message
          setErrors(fieldErrors)
        } else {
          setErrors({ form: data.error ?? 'Something went wrong' })
        }
        return
      }
      toast.success(mode === 'login' ? 'Welcome back!' : 'Account created!')
      // Honor the user's configured default landing page unless a specific
      // protected destination was requested.
      const target =
        mode === 'login' && next === '/dashboard' && typeof data.landingPage === 'string'
          ? data.landingPage
          : next
      router.push(target)
      router.refresh()
    } catch {
      setErrors({ form: 'Network error. Please try again.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight text-foreground">
        {mode === 'login' ? 'Sign in to Aegis' : 'Create your account'}
      </h1>
      <p className="mt-1.5 text-sm text-muted">
        {mode === 'login' ? (
          <>
            New here?{' '}
            <Link href="/register" className="font-medium text-accent hover:underline">
              Create an account
            </Link>
          </>
        ) : (
          <>
            Already have an account?{' '}
            <Link href="/login" className="font-medium text-accent hover:underline">
              Sign in
            </Link>
          </>
        )}
      </p>

      <form
        className="mt-7 space-y-4"
        onSubmit={(e) => {
          e.preventDefault()
          submit(mode === 'register' ? form : { email: form.email, password: form.password })
        }}
      >
        {errors.form && (
          <div className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
            {errors.form}
          </div>
        )}

        {mode === 'register' && (
          <Field label="Full name" htmlFor="name" error={errors.name}>
            <Input
              id="name"
              autoComplete="name"
              placeholder="Ada Lovelace"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </Field>
        )}

        <Field label="Email" htmlFor="email" error={errors.email}>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </Field>

        <Field
          label="Password"
          htmlFor="password"
          error={errors.password}
          hint={mode === 'register' ? 'At least 8 characters.' : undefined}
        >
          <Input
            id="password"
            type="password"
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            placeholder="••••••••"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </Field>

        <Button type="submit" size="lg" loading={loading} className="w-full">
          {mode === 'login' ? 'Sign in' : 'Create account'}
        </Button>
      </form>

      {mode === 'login' && (
        <div className="mt-6">
          <div className="relative flex items-center">
            <span className="h-px flex-1 bg-border" />
            <span className="px-3 text-xs text-muted-2">or try a demo account</span>
            <span className="h-px flex-1 bg-border" />
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2">
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc.email}
                type="button"
                disabled={loading}
                onClick={() => {
                  setForm({ name: '', email: acc.email, password: 'password123' })
                  submit({ email: acc.email, password: 'password123' })
                }}
                className="focus-ring rounded-lg border border-border bg-surface px-2 py-2 text-sm font-medium text-foreground transition-colors hover:bg-surface-2 disabled:opacity-50"
              >
                {acc.label}
              </button>
            ))}
          </div>
          <p className="mt-3 text-center text-xs text-muted-2">
            Demo password: <code className="font-mono">password123</code>
          </p>
        </div>
      )}
    </div>
  )
}
