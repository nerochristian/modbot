'use client'

import { useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { ErrorState } from '@/components/ui/empty-state'

export default function DashboardError({
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
    <Card>
      <ErrorState
        title="This page failed to load"
        description="An unexpected error occurred while rendering this page."
        onRetry={reset}
      />
    </Card>
  )
}
