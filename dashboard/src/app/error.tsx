'use client'

import { useEffect } from 'react'
import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <span className="flex size-14 items-center justify-center rounded-2xl bg-danger-soft text-danger">
        <AlertTriangle className="size-7" />
      </span>
      <h1 className="mt-6 text-2xl font-bold tracking-tight text-foreground">Something went wrong</h1>
      <p className="mt-2 max-w-md text-muted">
        An unexpected error occurred. You can try again, and if the problem persists, contact support.
      </p>
      {error.digest && <code className="mt-3 text-xs text-muted-2">Error ID: {error.digest}</code>}
      <div className="mt-8">
        <Button onClick={reset}>Try again</Button>
      </div>
    </div>
  )
}
