import type { Metadata } from 'next'
import { AppealsClient } from '@/components/dashboard/appeals-client'

export const metadata: Metadata = { title: 'Appeals' }

export default function AppealsPage() {
  return <AppealsClient />
}
