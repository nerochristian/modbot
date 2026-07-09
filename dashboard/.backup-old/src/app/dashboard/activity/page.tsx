import type { Metadata } from 'next'
import { ActivityClient } from '@/components/dashboard/activity-client'

export const metadata: Metadata = { title: 'Activity' }

export default function ActivityPage() {
  return <ActivityClient />
}
