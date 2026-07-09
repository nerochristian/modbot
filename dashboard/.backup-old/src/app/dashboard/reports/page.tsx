import type { Metadata } from 'next'
import { ReportsClient } from '@/components/dashboard/reports-client'

export const metadata: Metadata = { title: 'Reports' }

export default function ReportsPage() {
  return <ReportsClient />
}
