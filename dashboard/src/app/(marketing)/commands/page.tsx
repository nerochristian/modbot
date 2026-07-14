import type { Metadata } from 'next'
import { Suspense } from 'react'
import { CommandsDirectory } from '@/components/marketing/commands-directory'

export const metadata: Metadata = { title: 'Commands', description: 'Search Docket Discord moderation commands.' }

export default function CommandsPage() {
  return <Suspense fallback={<div className="min-h-[70vh]" />}><CommandsDirectory /></Suspense>
}
